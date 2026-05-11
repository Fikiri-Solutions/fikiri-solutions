"""
Fikiri Solutions - Subscription API Endpoints
Flask API endpoints for subscription management and billing
"""

from flask import Blueprint, request, jsonify, current_app
import logging
import os
import time
import hmac
from functools import wraps

# JWT integration - use custom JWT auth from core
from core.jwt_auth import jwt_required as jwt_required_decorator, get_current_user

# Create a decorator factory that supports @jwt_required() syntax
def jwt_required(fresh=False, optional=False):
    """JWT required decorator factory - supports @jwt_required() syntax"""
    if callable(fresh):  # Called without parentheses: @jwt_required
        return jwt_required_decorator(fresh)
    # Called with parentheses: @jwt_required()
    def decorator(func):
        return jwt_required_decorator(func)
    return decorator

def get_jwt_identity():
    """Get user ID from JWT token"""
    try:
        user = get_current_user()
        if user and 'user_id' in user:
            return user['user_id']
        return None
    except Exception:
        return None
from config import Config
from core.database_optimization import query_row_scalar
from core.fikiri_stripe_manager import FikiriStripeManager
from core.stripe_webhooks import StripeWebhookHandler

try:
    import stripe
    STRIPE_AVAILABLE = True
except ImportError:
    # Keep a module-level symbol so tests can patch `core.billing_api.stripe`
    # even when Stripe is not installed in the runtime.
    stripe = None
    STRIPE_AVAILABLE = False

# Import timeout utilities and circuit breaker
try:
    from core.api_timeouts import stripe_call_with_timeout, DEFAULT_STRIPE_TIMEOUT
    from core.circuit_breaker import get_circuit_breaker
    TIMEOUT_AVAILABLE = True
except ImportError:
    TIMEOUT_AVAILABLE = False

logger = logging.getLogger(__name__)

# Create Blueprint
billing_bp = Blueprint('billing', __name__, url_prefix='/api/billing')

# Initialize managers
stripe_manager = FikiriStripeManager()
webhook_handler = StripeWebhookHandler()

def retry_stripe_api(max_retries=3, delay=1, backoff=2):
    """Decorator for retrying Stripe API calls with exponential backoff"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            current_delay = delay
            
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except stripe.error.RateLimitError as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        logger.warning(f"Rate limit hit, retrying in {current_delay}s (attempt {attempt + 1}/{max_retries})")
                        time.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        logger.error(f"Rate limit exceeded after {max_retries} attempts")
                except stripe.error.APIConnectionError as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        logger.warning(f"API connection error, retrying in {current_delay}s (attempt {attempt + 1}/{max_retries})")
                        time.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        logger.error(f"API connection failed after {max_retries} attempts")
                except stripe.error.StripeError as e:
                    # Don't retry on other Stripe errors (auth, invalid request, etc.)
                    raise e
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        logger.warning(f"Unexpected error, retrying in {current_delay}s (attempt {attempt + 1}/{max_retries}): {e}")
                        time.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        logger.error(f"Failed after {max_retries} attempts: {e}")
            
            if last_exception:
                raise last_exception
        return wrapper
    return decorator


def get_user_email(user_id):
    """Get user email from database"""
    from core.database_optimization import DatabaseOptimizer
    db = DatabaseOptimizer()
    user_data = db.execute_query("SELECT email FROM users WHERE id = ?", (user_id,))
    if not user_data:
        return None
    return query_row_scalar(user_data[0], "email")


def get_user_name(user_id):
    """Get user name from database"""
    from core.database_optimization import DatabaseOptimizer
    db = DatabaseOptimizer()
    user_data = db.execute_query("SELECT name FROM users WHERE id = ?", (user_id,))
    if not user_data:
        return None
    return query_row_scalar(user_data[0], "name")


def _stripe_dashboard_message(exc: BaseException) -> str:
    """User-safe copy when Stripe calls fail (misconfigured keys, outages, circuit breaker)."""
    text = str(exc).lower()
    if "invalid api key" in text:
        return (
            "Stripe rejected the API key. Set STRIPE_SECRET_KEY to a secret key "
            "(sk_test_... or sk_live_...), not a publishable or restricted key."
        )
    if "circuit breaker" in text and "open" in text:
        return "Billing is temporarily unavailable after repeated Stripe errors. Try again in a few minutes."
    return "Billing profile could not be loaded. Check Stripe configuration or try again later."


def _stripe_customer_display_name(user_id, user_email):
    """Stripe Customer `name` — use profile name or email local-part; avoid `User <id>` in production."""
    n = get_user_name(user_id)
    if n and str(n).strip():
        return str(n).strip()
    if user_email and '@' in user_email:
        local = user_email.split('@', 1)[0].strip()
        if local:
            return local
    return 'Customer'


def _get_current_user_customer_id():
    """Return (stripe_customer_id, user_id) for the current JWT user, or (None, None)."""
    user_id = get_jwt_identity()
    if not user_id:
        return None, None
    user_email = get_user_email(user_id)
    if not user_email:
        return None, user_id
    customer_id = get_stripe_customer_id(user_email, user_id)
    return customer_id, user_id


def _verify_customer_owned_by_user(customer_id):
    """Return True if customer_id belongs to the current JWT user."""
    if not customer_id:
        return False
    our_customer_id, _ = _get_current_user_customer_id()
    return our_customer_id == customer_id


def _verify_subscription_owned_by_user(subscription_id):
    """Return True if subscription_id belongs to the current JWT user (DB or Stripe)."""
    if not subscription_id or not STRIPE_AVAILABLE:
        return False
    user_id = get_jwt_identity()
    if not user_id:
        return False
    from core.database_optimization import DatabaseOptimizer
    db = DatabaseOptimizer()
    try:
        row = db.execute_query(
            "SELECT 1 FROM subscriptions WHERE stripe_subscription_id = ? AND user_id = ?",
            (subscription_id, user_id)
        )
        if row and len(row) > 0:
            return True
    except Exception as e:
        logger.warning(f"DB check for subscription ownership: {e}")
    try:
        def _retrieve():
            return stripe.Subscription.retrieve(subscription_id)
        
        if TIMEOUT_AVAILABLE:
            breaker = get_circuit_breaker("stripe", failure_threshold=5, timeout_seconds=60, fail_open=False)
            sub = breaker.call(lambda: stripe_call_with_timeout(_retrieve, timeout=DEFAULT_STRIPE_TIMEOUT))
        else:
            sub = _retrieve()
        
        our_customer_id, _ = _get_current_user_customer_id()
        return our_customer_id and sub.customer == our_customer_id
    except stripe.error.StripeError:
        return False
    except Exception as e:
        logger.warning(f"Stripe check for subscription ownership: {e}")
        return False


def _test_access_enabled() -> bool:
    """Gate test-access code flow behind explicit env toggle."""
    return os.getenv('ENABLE_TEST_ACCESS_CODES', 'false').strip().lower() in ('1', 'true', 'yes', 'on')


def _allowed_test_access_codes():
    """
    Return configured test access codes from env.
    Comma-separated string in TEST_ACCESS_CODES.
    """
    raw = os.getenv('TEST_ACCESS_CODES', '')
    return [code.strip() for code in raw.split(',') if code and code.strip()]


def _test_access_code_matches(candidate_code: str) -> bool:
    """Constant-time comparison against configured codes."""
    candidate = (candidate_code or '').strip()
    if not candidate:
        return False
    for expected in _allowed_test_access_codes():
        if hmac.compare_digest(candidate, expected):
            return True
    return False


def _test_access_duration_days() -> int:
    """Clamp grant lifetime to a safe range."""
    try:
        days = int(os.getenv('TEST_ACCESS_DURATION_DAYS', '14'))
    except ValueError:
        days = 14
    return max(1, min(days, 90))


def _ensure_test_access_grants_table(db):
    db.execute_query("""
        CREATE TABLE IF NOT EXISTS test_access_grants (
            id BIGSERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL UNIQUE,
            code_hint TEXT,
            status TEXT NOT NULL DEFAULT 'active',
            granted_at INTEGER NOT NULL,
            expires_at INTEGER NOT NULL,
            revoked_at INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )
    """, fetch=False)
    db.execute_query("""
        CREATE TABLE IF NOT EXISTS test_access_redemptions (
            id BIGSERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL,
            code_hint TEXT,
            redeemed_at INTEGER NOT NULL,
            expires_at INTEGER NOT NULL,
            source TEXT NOT NULL DEFAULT 'self_serve',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )
    """, fetch=False)
    db.execute_query("""
        CREATE INDEX IF NOT EXISTS idx_test_access_redemptions_redeemed_at
        ON test_access_redemptions (redeemed_at DESC)
    """, fetch=False)


def _get_user_role(user_id):
    """Get role for a user id from local database."""
    if not user_id:
        return None
    from core.database_optimization import DatabaseOptimizer
    db = DatabaseOptimizer()
    rows = db.execute_query("SELECT role FROM users WHERE id = ? LIMIT 1", (user_id,))
    if not rows:
        return None
    row = rows[0]
    return (row.get('role') if hasattr(row, 'keys') else row[0]) or None


def _is_admin_user(user_id):
    """Admin check: env allow-list OR role=admin."""
    admin_ids = [x.strip() for x in (os.getenv('ADMIN_USER_IDS') or '').split(',') if x.strip()]
    if admin_ids and str(user_id) in admin_ids:
        return True
    role = str(_get_user_role(user_id) or '').strip().lower()
    return role == 'admin'

def _fetch_customer_from_stripe(user_email):
    """Fetch customer ID from Stripe API with timeout protection"""
    def _list():
        return stripe.Customer.list(email=user_email, limit=1)
    
    if TIMEOUT_AVAILABLE:
        breaker = get_circuit_breaker("stripe", failure_threshold=5, timeout_seconds=60, fail_open=False)
        customers = breaker.call(lambda: stripe_call_with_timeout(_list, timeout=DEFAULT_STRIPE_TIMEOUT))
    else:
        customers = _list()
    
    if customers.data and len(customers.data) > 0:
        return customers.data[0].id
    return None

def get_stripe_customer_id(user_email, user_id=None):
    """Get Stripe customer ID - cached in database for performance"""
    from core.database_optimization import DatabaseOptimizer
    db = DatabaseOptimizer()
    
    # First check database cache (FAST - no API call)
    if user_id:
        try:
            cached = db.execute_query(
                "SELECT stripe_customer_id FROM users WHERE id = ? AND stripe_customer_id IS NOT NULL",
                (user_id,)
            )
            if cached and len(cached) > 0 and cached[0]:
                cid = query_row_scalar(cached[0], "stripe_customer_id")
                if cid:
                    return cid
        except Exception as e:
            logger.warning(f"Failed to get cached customer ID: {e}")
    
    # Fallback to Stripe API (one-time lookup)
    if not STRIPE_AVAILABLE:
        return None
    
    # Retry logic for Stripe API call
    for attempt in range(3):
        try:
            customer_id = _fetch_customer_from_stripe(user_email)
            if customer_id:
                # Cache it in database for future requests
                if user_id:
                    try:
                        db.execute_query(
                            "UPDATE users SET stripe_customer_id = ? WHERE id = ?",
                            (customer_id, user_id),
                            fetch=False
                        )
                        logger.info(f"Cached Stripe customer ID for user {user_id}")
                    except Exception as e:
                        logger.warning(f"Failed to cache customer ID: {e}")
                return customer_id
            return None
        except stripe.error.RateLimitError as e:
            if attempt < 2:
                wait_time = (2 ** attempt) * 1
                logger.warning(f"Rate limit hit, retrying in {wait_time}s (attempt {attempt + 1}/3)")
                time.sleep(wait_time)
                continue
            logger.error(f"Rate limit exceeded after 3 attempts: {e}")
            return None
        except stripe.error.APIConnectionError as e:
            if attempt < 2:
                wait_time = (2 ** attempt) * 1
                logger.warning(f"API connection error, retrying in {wait_time}s (attempt {attempt + 1}/3)")
                time.sleep(wait_time)
                continue
            logger.error(f"API connection failed after 3 attempts: {e}")
            return None
        except stripe.error.StripeError as e:
            logger.error(f"Stripe API error getting customer ID: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error getting customer ID: {e}")
            return None
    return None

@billing_bp.route('/pricing', methods=['GET'])
def get_pricing_tiers():
    """Get all available pricing tiers"""
    try:
        pricing_tiers = stripe_manager.get_pricing_tiers()
        return jsonify({
            'success': True,
            'pricing_tiers': pricing_tiers
        })
    except Exception as e:
        logger.error(f"Failed to get pricing tiers: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@billing_bp.route('/checkout', methods=['POST'])
@jwt_required()
def create_checkout_session():
    """Create Stripe Checkout session for subscription"""
    try:
        data = request.get_json() or {}
        tier_name = data.get('tier_name')
        price_id = data.get('price_id')
        billing_period = data.get('billing_period', 'monthly')
        use_trial = data.get('trial', True)
        requested_types = data.get('payment_method_types', ['card', 'us_bank_account'])
        if not isinstance(requested_types, list):
            requested_types = ['card', 'us_bank_account']
        payment_method_types = [pm for pm in requested_types if pm in ('card', 'us_bank_account')]
        if not payment_method_types:
            payment_method_types = ['card']
        
        if tier_name and not price_id:
            price_id = stripe_manager.get_price_id(tier_name, billing_period)
            if not price_id:
                return jsonify({'success': False, 'error': f'Price ID not found for tier {tier_name}'}), 400
        
        if not price_id:
            return jsonify({'success': False, 'error': 'Either price_id or tier_name is required'}), 400
        
        frontend_url = (current_app.config.get('FRONTEND_URL') or Config.FRONTEND_URL).rstrip('/')
        session = stripe_manager.create_checkout_session(
            price_id=price_id,
            success_url=f"{frontend_url}/dashboard?success=true",
            cancel_url=f"{frontend_url}/pricing?canceled=true",
            trial_days=14 if use_trial else 0,
            payment_method_types=payment_method_types,
        )
        
        return jsonify({'success': True, 'checkout_url': session['url'], 'session_id': session['session_id']})
        
    except Exception as e:
        logger.error(f"Failed to create checkout session: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@billing_bp.route('/subscription', methods=['POST'])
@jwt_required()
def create_subscription():
    """Create subscription directly (for testing)"""
    try:
        data = request.get_json()
        price_id = data.get('price_id')
        trial_days = data.get('trial_days', 14)
        
        if not price_id:
            return jsonify({
                'success': False,
                'error': 'Price ID is required'
            }), 400
        
        # Get user info from JWT
        user_id = get_jwt_identity()
        user_email = get_user_email(user_id) or f"user_{user_id}@fikiri.com"
        user_name = _stripe_customer_display_name(user_id, user_email)

        # Create customer if doesn't exist
        customer = stripe_manager.create_customer(
            email=user_email,
            name=user_name,
            metadata={'user_id': str(user_id)}
        )
        
        # Create subscription
        subscription = stripe_manager.create_subscription(
            customer_id=customer['id'],
            price_id=price_id,
            trial_days=trial_days
        )
        
        return jsonify({
            'success': True,
            'subscription': subscription
        })
        
    except Exception as e:
        logger.error(f"Failed to create subscription: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@billing_bp.route('/subscription/current', methods=['GET'])
@jwt_required()
def get_current_subscription():
    """Get current user's subscription - optimized with database cache"""
    from core.database_optimization import DatabaseOptimizer
    db = DatabaseOptimizer()
    
    try:
        user_id = get_jwt_identity()
        if not user_id:
            return jsonify({'success': False, 'error': 'User not found'}), 404
        
        # First check database cache (FAST - 0 API calls)
        try:
            cached_sub = db.execute_query("""
                SELECT stripe_subscription_id, status, tier, billing_period,
                       current_period_start, current_period_end, trial_end,
                       cancel_at_period_end
                FROM subscriptions 
                WHERE user_id = ? AND status IN ('active', 'trialing')
                ORDER BY created_at DESC LIMIT 1
            """, (user_id,))
            
            if cached_sub and len(cached_sub) > 0 and cached_sub[0]:
                sub_data = cached_sub[0]
                if len(sub_data) >= 8:  # Ensure we have all 8 fields
                    # Return cached subscription data (FAST - no API calls)
                    return jsonify({
                        'success': True,
                        'subscription': {
                            'id': sub_data[0],
                            'status': sub_data[1],
                            'tier': sub_data[2],
                            'billing_period': sub_data[3],
                            'current_period_start': sub_data[4],
                            'current_period_end': sub_data[5],
                            'trial_end': sub_data[6],
                            'cancel_at_period_end': bool(sub_data[7]) if sub_data[7] else False
                        },
                        'cached': True
                    })
        except Exception as e:
            logger.warning(f"Failed to get cached subscription: {e}")
        
        # Fallback to Stripe API if not in cache
        user_email = get_user_email(user_id)
        if not user_email:
            return jsonify({'success': False, 'error': 'User not found'}), 404
        
        customer_id = get_stripe_customer_id(user_email, user_id)
        if customer_id:
            try:
                # Stripe status filters are exclusive: `trialing` is not included in `active`.
                # List recent subscriptions and pick the first active or trialing (matches DB cache query).
                def _fetch_billable_subscription_from_stripe():
                    subs = stripe.Subscription.list(
                        customer=customer_id,
                        limit=20,
                    )
                    for sub in subs.data:
                        if sub.status in ('active', 'trialing'):
                            return stripe_manager.get_subscription(sub.id)
                    return None

                if TIMEOUT_AVAILABLE:
                    breaker = get_circuit_breaker("stripe", failure_threshold=5, timeout_seconds=60, fail_open=False)
                    subscription_payload = breaker.call(
                        lambda: stripe_call_with_timeout(
                            _fetch_billable_subscription_from_stripe,
                            timeout=DEFAULT_STRIPE_TIMEOUT,
                        )
                    )
                else:
                    subscription_payload = _fetch_billable_subscription_from_stripe()

                if subscription_payload:
                    return jsonify({'success': True, 'subscription': subscription_payload, 'cached': False})
            except stripe.error.StripeError as e:
                logger.error(f"Stripe API error: {e}")
                return jsonify({
                    'success': False, 
                    'error': 'Unable to fetch subscription. Please try again later.'
                }), 503
        
        # Final fallback: local test-access grants (time-limited, env-gated).
        if _test_access_enabled():
            try:
                _ensure_test_access_grants_table(db)
                now_ts = int(time.time())
                grant_rows = db.execute_query("""
                    SELECT expires_at
                    FROM test_access_grants
                    WHERE user_id = ?
                      AND status = 'active'
                      AND revoked_at IS NULL
                      AND expires_at > ?
                    ORDER BY updated_at DESC
                    LIMIT 1
                """, (user_id, now_ts))
                if grant_rows and len(grant_rows) > 0 and grant_rows[0]:
                    grant = grant_rows[0]
                    expires_at = grant['expires_at'] if hasattr(grant, 'keys') else grant[0]
                    return jsonify({
                        'success': True,
                        'subscription': {
                            'id': f"test_access_user_{user_id}",
                            'status': 'trialing',
                            'tier': 'test_access',
                            'billing_period': 'test',
                            'current_period_start': now_ts,
                            'current_period_end': expires_at,
                            'trial_end': expires_at,
                            'cancel_at_period_end': True,
                            'source': 'test_access_code'
                        },
                        'cached': True
                    })
            except Exception as e:
                logger.warning(f"Failed to evaluate test access grant for user {user_id}: {e}")

        return jsonify({'success': True, 'subscription': None, 'message': 'No active subscription'})
    except Exception as e:
        logger.error(f"Failed to get current subscription: {e}")
        return jsonify({'success': False, 'error': 'An error occurred. Please try again.'}), 500


@billing_bp.route('/test-access/redeem', methods=['POST'])
@jwt_required()
def redeem_test_access_code():
    """
    Redeem a temporary access code to grant test access in production.
    Requires:
      - ENABLE_TEST_ACCESS_CODES=true
      - TEST_ACCESS_CODES=comma,separated,codes
    """
    if not _test_access_enabled():
        return jsonify({'success': False, 'error': 'Test access codes are disabled'}), 404

    try:
        user_id = get_jwt_identity()
        if not user_id:
            return jsonify({'success': False, 'error': 'User not found'}), 404

        payload = request.get_json(silent=True) or {}
        submitted_code = str(payload.get('code') or '').strip()
        if not submitted_code:
            return jsonify({'success': False, 'error': 'Access code is required'}), 400
        if not _test_access_code_matches(submitted_code):
            return jsonify({'success': False, 'error': 'Invalid access code'}), 403

        from core.database_optimization import DatabaseOptimizer
        db = DatabaseOptimizer()
        _ensure_test_access_grants_table(db)

        now_ts = int(time.time())
        expires_at = now_ts + (_test_access_duration_days() * 24 * 60 * 60)
        code_hint = submitted_code[:3] + '***'

        # One active grant per user; redemption refreshes expiry.
        db.execute_query("""
            INSERT INTO test_access_redemptions (user_id, code_hint, redeemed_at, expires_at, source)
            VALUES (?, ?, ?, ?, 'self_serve')
        """, (user_id, code_hint, now_ts, expires_at), fetch=False)
        db.execute_query("""
            INSERT INTO test_access_grants (user_id, code_hint, status, granted_at, expires_at, revoked_at, updated_at)
            VALUES (?, ?, 'active', ?, ?, NULL, CURRENT_TIMESTAMP)
            ON CONFLICT(user_id) DO UPDATE SET
                code_hint = excluded.code_hint,
                status = 'active',
                granted_at = excluded.granted_at,
                expires_at = excluded.expires_at,
                revoked_at = NULL,
                updated_at = CURRENT_TIMESTAMP
        """, (user_id, code_hint, now_ts, expires_at), fetch=False)

        logger.info(f"Test access granted for user_id={user_id} until {expires_at}")
        return jsonify({
            'success': True,
            'message': 'Test access granted',
            'access': {
                'status': 'trialing',
                'tier': 'test_access',
                'expires_at': expires_at
            }
        })
    except Exception as e:
        logger.error(f"Failed to redeem test access code: {e}")
        return jsonify({'success': False, 'error': 'Failed to redeem access code'}), 500


@billing_bp.route('/test-access/audit', methods=['GET'])
@jwt_required()
def get_test_access_audit():
    """Admin-only audit log of test-access code redemptions."""
    if not _test_access_enabled():
        return jsonify({'success': False, 'error': 'Test access codes are disabled'}), 404

    try:
        user_id = get_jwt_identity()
        if not user_id:
            return jsonify({'success': False, 'error': 'User not found'}), 404
        if not _is_admin_user(user_id):
            return jsonify({'success': False, 'error': 'Admin access required'}), 403

        from core.database_optimization import DatabaseOptimizer
        db = DatabaseOptimizer()
        _ensure_test_access_grants_table(db)

        try:
            limit = int(request.args.get('limit', 50))
        except ValueError:
            limit = 50
        limit = max(1, min(limit, 200))

        rows = db.execute_query("""
            SELECT
                r.id,
                r.user_id,
                COALESCE(u.email, '') AS email,
                r.code_hint,
                r.redeemed_at,
                r.expires_at,
                CASE
                    WHEN g.status = 'active' AND g.revoked_at IS NULL AND g.expires_at > ? THEN 1
                    ELSE 0
                END AS currently_active
            FROM test_access_redemptions r
            LEFT JOIN users u ON u.id = r.user_id
            LEFT JOIN test_access_grants g ON g.user_id = r.user_id
            ORDER BY r.redeemed_at DESC
            LIMIT ?
        """, (int(time.time()), limit))

        audit = []
        for row in rows or []:
            as_map = row if hasattr(row, 'keys') else {
                'id': row[0],
                'user_id': row[1],
                'email': row[2],
                'code_hint': row[3],
                'redeemed_at': row[4],
                'expires_at': row[5],
                'currently_active': row[6],
            }
            audit.append({
                'id': as_map.get('id'),
                'user_id': as_map.get('user_id'),
                'email': as_map.get('email') or None,
                'code_hint': as_map.get('code_hint') or None,
                'redeemed_at': as_map.get('redeemed_at'),
                'expires_at': as_map.get('expires_at'),
                'currently_active': bool(as_map.get('currently_active')),
            })

        return jsonify({'success': True, 'audit': audit})
    except Exception as e:
        logger.error(f"Failed to load test access audit: {e}")
        return jsonify({'success': False, 'error': 'Failed to load audit'}), 500

@billing_bp.route('/subscription/<subscription_id>', methods=['GET'])
@jwt_required()
def get_subscription(subscription_id):
    """Get subscription details (only for subscription owned by current user)"""
    try:
        if not _verify_subscription_owned_by_user(subscription_id):
            return jsonify({'success': False, 'error': 'Subscription not found'}), 404
        subscription = stripe_manager.get_subscription(subscription_id)
        if not subscription:
            return jsonify({'success': False, 'error': 'Subscription not found'}), 404
        return jsonify({'success': True, 'subscription': subscription})
    except Exception as e:
        logger.error(f"Failed to get subscription: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@billing_bp.route('/subscription/<subscription_id>/cancel', methods=['POST'])
@jwt_required()
def cancel_subscription(subscription_id):
    """Cancel subscription (only if owned by current user)"""
    try:
        if not _verify_subscription_owned_by_user(subscription_id):
            return jsonify({'success': False, 'error': 'Subscription not found'}), 404
        data = request.get_json() or {}
        at_period_end = data.get('at_period_end', True)
        result = stripe_manager.cancel_subscription(subscription_id, at_period_end)
        return jsonify({'success': True, 'result': result})
    except Exception as e:
        logger.error(f"Failed to cancel subscription: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@billing_bp.route('/subscription/<subscription_id>/upgrade', methods=['POST'])
@jwt_required()
def upgrade_subscription(subscription_id):
    """Upgrade subscription to higher tier (only if owned by current user)"""
    try:
        if not _verify_subscription_owned_by_user(subscription_id):
            return jsonify({'success': False, 'error': 'Subscription not found'}), 404
        data = request.get_json() or {}
        new_price_id = data.get('new_price_id')
        if not new_price_id:
            return jsonify({'success': False, 'error': 'New price ID is required'}), 400
        result = stripe_manager.upgrade_subscription(subscription_id, new_price_id)
        return jsonify({'success': True, 'result': result})
    except Exception as e:
        logger.error(f"Failed to upgrade subscription: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@billing_bp.route('/invoices', methods=['GET'])
@jwt_required()
def get_invoices():
    """Get user's invoices"""
    try:
        user_id = get_jwt_identity()
        user_email = get_user_email(user_id)
        if not user_email:
            return jsonify({'success': False, 'error': 'User not found'}), 404
        
        customer_id = get_stripe_customer_id(user_email)
        if customer_id:
            invoices = stripe_manager.get_customer_invoices(customer_id)
            return jsonify({'success': True, 'invoices': invoices})
        
        return jsonify({'success': True, 'invoices': []})
    except Exception as e:
        logger.error(f"Failed to get invoices: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@billing_bp.route('/portal', methods=['POST'])
@jwt_required()
def create_portal_session():
    """Create Stripe Customer Portal session"""
    try:
        user_id = get_jwt_identity()
        user_email = get_user_email(user_id)
        if not user_email:
            return jsonify({'success': False, 'error': 'User not found'}), 404
        
        customer_id = get_stripe_customer_id(user_email)
        if not customer_id:
            return jsonify({'success': False, 'error': 'No customer found. Please create a subscription first.'}), 400
        
        frontend_url = (current_app.config.get('FRONTEND_URL') or Config.FRONTEND_URL).rstrip('/')
        session = stripe_manager.create_customer_portal_session(customer_id, f"{frontend_url}/billing")
        return jsonify({'success': True, 'url': session['url']})
    except Exception as e:
        logger.error(f"Failed to create portal session: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@billing_bp.route('/payment-methods', methods=['GET'])
@jwt_required()
def get_payment_methods():
    """Get user's payment methods"""
    try:
        user_id = get_jwt_identity()
        user_email = get_user_email(user_id)
        if not user_email:
            return jsonify({'success': False, 'error': 'User not found'}), 404
        
        customer_id = get_stripe_customer_id(user_email)
        if not customer_id:
            return jsonify({'success': True, 'payment_methods': []})
        
        methods = stripe_manager.get_customer_payment_methods(customer_id)
        return jsonify({'success': True, 'payment_methods': methods})
    except Exception as e:
        logger.error(f"Failed to get payment methods: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@billing_bp.route('/payment-methods/<payment_method_id>', methods=['DELETE'])
@jwt_required()
def remove_payment_method(payment_method_id):
    """Remove a payment method (only if it belongs to current user's customer)"""
    try:
        if STRIPE_AVAILABLE:
            try:
                pm = stripe.PaymentMethod.retrieve(payment_method_id)
                customer_id = getattr(pm, 'customer', None) or (pm.get('customer') if isinstance(pm, dict) else None)
                if customer_id and not _verify_customer_owned_by_user(customer_id):
                    return jsonify({'success': False, 'error': 'Payment method not found'}), 404
            except stripe.error.StripeError as e:
                logger.warning(f"Could not verify payment method ownership: {e}")
        result = stripe_manager.detach_payment_method(payment_method_id)
        return jsonify({'success': True, 'result': result})
    except Exception as e:
        logger.error(f"Failed to remove payment method: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@billing_bp.route('/payment-methods/<payment_method_id>/default', methods=['POST'])
@jwt_required()
def set_default_payment_method(payment_method_id):
    """Set default payment method"""
    try:
        user_id = get_jwt_identity()
        user_email = get_user_email(user_id)
        if not user_email:
            return jsonify({'success': False, 'error': 'User not found'}), 404
        
        customer_id = get_stripe_customer_id(user_email)
        if not customer_id:
            return jsonify({'success': False, 'error': 'No customer found'}), 400
        
        result = stripe_manager.set_default_payment_method(customer_id, payment_method_id)
        return jsonify({'success': True, 'result': result})
    except Exception as e:
        logger.error(f"Failed to set default payment method: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@billing_bp.route('/customer/details', methods=['GET'])
@jwt_required()
def get_customer_details():
    """Get detailed customer account information"""
    try:
        user_id = get_jwt_identity()
        user_email = get_user_email(user_id)
        if not user_email:
            return jsonify({'success': False, 'error': 'User not found'}), 404
        
        customer_id = get_stripe_customer_id(user_email, user_id)
        if not customer_id:
            try:
                customer = stripe_manager.create_customer(
                    email=user_email,
                    name=_stripe_customer_display_name(user_id, user_email),
                    metadata={'user_id': str(user_id)}
                )
                customer_id = customer['id']
            except Exception as e:
                logger.warning("Failed to create customer for details: %s", e)
                return jsonify({
                    'success': True,
                    'customer': None,
                    'billing_unavailable': True,
                    'message': _stripe_dashboard_message(e),
                })
        
        details = stripe_manager.get_customer_details(customer_id)
        if not details:
            return jsonify({
                'success': True,
                'customer': None,
                'billing_unavailable': True,
                'message': 'Could not load billing details from Stripe.',
            })
        return jsonify({'success': True, 'customer': details})
    except Exception:
        # Avoid 500 + opaque KeyError('0') from DB row shapes or Stripe SDK edge cases;
        # clients treat billing_unavailable as soft-empty (BillingPage).
        logger.exception("Unexpected error in get_customer_details")
        return jsonify({
            'success': True,
            'customer': None,
            'billing_unavailable': True,
            'message': 'Could not load billing profile.',
        })

@billing_bp.route('/setup-intent', methods=['POST'])
@jwt_required()
def create_setup_intent():
    """Create Stripe SetupIntent for adding payment methods"""
    try:
        user_id = get_jwt_identity()
        user_email = get_user_email(user_id)
        if not user_email:
            return jsonify({'success': False, 'error': 'User not found'}), 404
        
        if stripe is None:
            return jsonify({
                'success': False,
                'error': 'Stripe is not configured on this server.',
                'error_code': 'STRIPE_UNAVAILABLE',
            }), 200
        
        data = request.get_json() or {}
        requested_types = data.get('payment_method_types', ['card', 'us_bank_account'])
        if not isinstance(requested_types, list):
            requested_types = ['card', 'us_bank_account']
        payment_method_types = [pm for pm in requested_types if pm in ('card', 'us_bank_account')]
        if not payment_method_types:
            payment_method_types = ['card']
        
        try:
            customer_id = get_stripe_customer_id(user_email, user_id)
            if not customer_id:
                customer = stripe_manager.create_customer(
                    email=user_email,
                    name=_stripe_customer_display_name(user_id, user_email),
                    metadata={'user_id': str(user_id)}
                )
                customer_id = customer['id']

            setup_intent = stripe.SetupIntent.create(
                customer=customer_id,
                payment_method_types=payment_method_types,
                usage='off_session'
            )
            return jsonify({
                'success': True,
                'client_secret': setup_intent.client_secret,
                'setup_intent_id': setup_intent.id
            })
        except Exception as e:
            logger.warning("SetupIntent / customer creation failed: %s", e)
            msg = _stripe_dashboard_message(e)
            return jsonify({
                'success': False,
                'error': msg,
                'error_code': 'STRIPE_ERROR',
            }), 200
    except Exception as e:
        logger.error(f"Failed to create setup intent: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@billing_bp.route('/setup-checkout', methods=['POST'])
@jwt_required()
def create_setup_checkout_session():
    """Create Stripe Checkout setup-mode session for card or ACH collection."""
    try:
        user_id = get_jwt_identity()
        user_email = get_user_email(user_id)
        if not user_email:
            return jsonify({'success': False, 'error': 'User not found'}), 404

        if stripe is None:
            return jsonify({
                'success': False,
                'error': 'Stripe is not configured on this server.',
                'error_code': 'STRIPE_UNAVAILABLE',
            }), 200

        data = request.get_json() or {}
        requested_types = data.get('payment_method_types', ['card'])
        if not isinstance(requested_types, list):
            requested_types = ['card']
        payment_method_types = [pm for pm in requested_types if pm in ('card', 'us_bank_account')]
        if not payment_method_types:
            payment_method_types = ['card']

        customer_id = get_stripe_customer_id(user_email, user_id)
        if not customer_id:
            customer = stripe_manager.create_customer(
                email=user_email,
                name=_stripe_customer_display_name(user_id, user_email),
                metadata={'user_id': str(user_id)}
            )
            customer_id = customer['id']

        frontend_url = (current_app.config.get('FRONTEND_URL') or Config.FRONTEND_URL).rstrip('/')
        success_url = f"{frontend_url}/billing?setup=success"
        cancel_url = f"{frontend_url}/billing?setup=cancelled"
        session = stripe_manager.create_setup_checkout_session(
            customer_id=customer_id,
            payment_method_types=payment_method_types,
            success_url=success_url,
            cancel_url=cancel_url,
        )
        return jsonify({'success': True, 'url': session.get('url'), 'session_id': session.get('session_id')})
    except Exception as e:
        logger.error(f"Failed to create setup checkout session: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@billing_bp.route('/customer/<customer_id>/entitlements', methods=['GET'])
@jwt_required()
def get_customer_entitlements(customer_id):
    """Get customer's active entitlements (only for current user's customer)"""
    try:
        if not _verify_customer_owned_by_user(customer_id):
            return jsonify({'success': False, 'error': 'Customer not found'}), 404
        entitlements = stripe_manager.get_customer_entitlements(customer_id)
        
        return jsonify({
            'success': True,
            'entitlements': entitlements
        })
        
    except Exception as e:
        logger.error(f"Failed to get customer entitlements: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@billing_bp.route('/customer/<customer_id>/limits', methods=['GET'])
@jwt_required()
def get_customer_limits(customer_id):
    """Get customer's usage limits (only for current user's customer)"""
    try:
        if not _verify_customer_owned_by_user(customer_id):
            return jsonify({'success': False, 'error': 'Customer not found'}), 404
        limits = stripe_manager.get_customer_limits(customer_id)
        
        return jsonify({
            'success': True,
            'limits': limits
        })
        
    except Exception as e:
        logger.error(f"Failed to get customer limits: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@billing_bp.route('/check-feature-access', methods=['POST'])
@jwt_required()
def check_feature_access():
    """Check if customer has access to a specific feature"""
    try:
        data = request.get_json()
        customer_id = data.get('customer_id')
        feature_name = data.get('feature_name')
        
        if not customer_id or not feature_name:
            return jsonify({
                'success': False,
                'error': 'Customer ID and feature name are required'
            }), 400
        
        if not _verify_customer_owned_by_user(customer_id):
            return jsonify({'success': False, 'error': 'Customer not found'}), 404
        has_access = stripe_manager.check_feature_access(customer_id, feature_name)
        
        return jsonify({
            'success': True,
            'has_access': has_access,
            'feature_name': feature_name
        })
        
    except Exception as e:
        logger.error(f"Failed to check feature access: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@billing_bp.route('/webhook', methods=['POST'])
def handle_stripe_webhook():
    """Handle Stripe webhook events"""
    try:
        payload = request.get_data()
        sig_header = request.headers.get('Stripe-Signature')
        
        # Verify webhook signature
        event = webhook_handler.verify_webhook_signature(payload, sig_header)
        
        # Handle the event
        result = webhook_handler.handle_event(event)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Failed to handle webhook: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400

@billing_bp.route('/setup', methods=['POST'])
@jwt_required()
def setup_billing_system():
    """Set up the complete billing system (admin only)"""
    try:
        admin_ids = [x.strip() for x in (os.environ.get('ADMIN_USER_IDS') or '').split(',') if x.strip()]
        user_id = get_jwt_identity()
        if admin_ids and (not user_id or str(user_id) not in admin_ids):
            return jsonify({'success': False, 'error': 'Admin access required'}), 403
        result = stripe_manager.setup_complete_billing_system()
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Failed to setup billing system: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# Usage tracking endpoints
@billing_bp.route('/usage/track', methods=['POST'])
@jwt_required()
def track_usage():
    """Track usage for overage billing (persisted to billing_usage table)"""
    try:
        user_id = get_jwt_identity()
        if not user_id:
            return jsonify({'success': False, 'error': 'User not found'}), 404
        data = request.get_json() or {}
        usage_type = data.get('usage_type')  # email_processing, lead_storage, ai_responses
        quantity = int(data.get('quantity', 1))
        if quantity < 0:
            quantity = 0
        if not usage_type or not isinstance(usage_type, str):
            return jsonify({'success': False, 'error': 'Usage type is required'}), 400
        month = time.strftime('%Y-%m')
        from core.database_optimization import DatabaseOptimizer
        db = DatabaseOptimizer()
        db.execute_query(
            "INSERT INTO billing_usage (user_id, month, usage_type, quantity) VALUES (?, ?, ?, ?)",
            (user_id, month, usage_type.strip(), quantity),
            fetch=False
        )
        return jsonify({'success': True, 'message': f'Tracked {quantity} {usage_type} usage'})
    except Exception as e:
        logger.error(f"Failed to track usage: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@billing_bp.route('/usage/current', methods=['GET'])
@jwt_required()
def get_current_usage():
    """Get current usage for the month from billing_usage table"""
    try:
        user_id = get_jwt_identity()
        if not user_id:
            return jsonify({'success': False, 'error': 'User not found'}), 404
        month = time.strftime('%Y-%m')
        from core.database_optimization import DatabaseOptimizer
        db = DatabaseOptimizer()
        rows = db.execute_query(
            "SELECT usage_type, SUM(quantity) as total FROM billing_usage WHERE user_id = ? AND month = ? GROUP BY usage_type",
            (user_id, month)
        )
        usage = {}
        if rows:
            for row in rows:
                if hasattr(row, 'keys'):
                    usage[row['usage_type']] = int(row['total'] or 0)
                else:
                    usage[row[0]] = int(row[1] or 0)
        return jsonify({
            'success': True,
            'usage': {
                'emails_processed': usage.get('email_processing', 0),
                'leads_created': usage.get('lead_storage', 0),
                'ai_responses_generated': usage.get('ai_responses', 0),
                **{k: v for k, v in usage.items() if k not in ('email_processing', 'lead_storage', 'ai_responses')}
            },
            'month_year': month
        })
    except Exception as e:
        logger.error(f"Failed to get current usage: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
