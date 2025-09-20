"""
API Documentation for Fikiri Solutions
Auto-generated Swagger/OpenAPI documentation
"""

# Optional imports with fallbacks
try:
    from flask import Flask, Blueprint
    from flask_restx import Api, Resource, fields, Namespace
    FLASK_RESTX_AVAILABLE = True
except ImportError:
    FLASK_RESTX_AVAILABLE = False
    print("Warning: Flask-RESTX not available. Install with: pip install flask-restx")

try:
    from core.error_handling import create_success_response, ValidationError, AuthenticationError
    CORE_AVAILABLE = True
except ImportError:
    CORE_AVAILABLE = False
    print("Warning: Core modules not available")

# Create API blueprint
api_bp = Blueprint('api', __name__, url_prefix='/api')
api = Api(
    api_bp,
    version='1.0',
    title='Fikiri Solutions API',
    description='AI-powered business automation platform API',
    doc='/docs/',
    contact='support@fikirisolutions.com',
    license='Proprietary',
    license_url='https://fikirisolutions.com/terms'
)

# Namespaces
auth_ns = Namespace('auth', description='Authentication operations')
email_ns = Namespace('email', description='Email management operations')
crm_ns = Namespace('crm', description='CRM operations')
ai_ns = Namespace('ai', description='AI and automation operations')
analytics_ns = Namespace('analytics', description='Analytics and reporting operations')

# Add namespaces to API
api.add_namespace(auth_ns)
api.add_namespace(email_ns)
api.add_namespace(crm_ns)
api.add_namespace(ai_ns)
api.add_namespace(analytics_ns)

# Common Models
error_model = api.model('Error', {
    'status': fields.String(required=True, description='Error status'),
    'error_code': fields.String(required=True, description='Error code'),
    'message': fields.String(required=True, description='Error message'),
    'timestamp': fields.String(required=True, description='Error timestamp'),
    'error_id': fields.String(required=True, description='Unique error ID')
})

success_model = api.model('Success', {
    'status': fields.String(required=True, description='Success status'),
    'message': fields.String(required=True, description='Success message'),
    'timestamp': fields.String(required=True, description='Response timestamp'),
    'data': fields.Raw(description='Response data')
})

# Authentication Models
login_model = api.model('Login', {
    'email': fields.String(required=True, description='User email address'),
    'password': fields.String(required=True, description='User password')
})

register_model = api.model('Register', {
    'name': fields.String(required=True, description='User full name'),
    'email': fields.String(required=True, description='User email address'),
    'password': fields.String(required=True, description='User password'),
    'business_name': fields.String(description='Business name'),
    'industry': fields.String(description='Industry type'),
    'team_size': fields.String(description='Team size')
})

token_model = api.model('Token', {
    'access_token': fields.String(required=True, description='JWT access token'),
    'refresh_token': fields.String(required=True, description='JWT refresh token'),
    'expires_in': fields.Integer(required=True, description='Token expiration time in seconds'),
    'token_type': fields.String(required=True, description='Token type')
})

user_model = api.model('User', {
    'id': fields.Integer(required=True, description='User ID'),
    'name': fields.String(required=True, description='User name'),
    'email': fields.String(required=True, description='User email'),
    'business_name': fields.String(description='Business name'),
    'industry': fields.String(description='Industry'),
    'team_size': fields.String(description='Team size'),
    'created_at': fields.String(description='Account creation date'),
    'last_login': fields.String(description='Last login date')
})

# Email Models
email_model = api.model('Email', {
    'id': fields.String(required=True, description='Email ID'),
    'subject': fields.String(description='Email subject'),
    'sender': fields.String(description='Sender email'),
    'recipient': fields.String(description='Recipient email'),
    'body': fields.String(description='Email body'),
    'date': fields.String(description='Email date'),
    'read': fields.Boolean(description='Read status'),
    'important': fields.Boolean(description='Important flag'),
    'labels': fields.List(fields.String, description='Email labels')
})

email_list_model = api.model('EmailList', {
    'emails': fields.List(fields.Nested(email_model), description='List of emails'),
    'total': fields.Integer(description='Total number of emails'),
    'page': fields.Integer(description='Current page'),
    'per_page': fields.Integer(description='Emails per page')
})

email_action_model = api.model('EmailAction', {
    'action': fields.String(required=True, description='Action type (reply, forward, delete, archive)'),
    'email_id': fields.String(required=True, description='Email ID'),
    'content': fields.String(description='Action content (for reply/forward)'),
    'recipients': fields.List(fields.String, description='Recipients (for forward)')
})

# CRM Models
contact_model = api.model('Contact', {
    'id': fields.Integer(required=True, description='Contact ID'),
    'name': fields.String(required=True, description='Contact name'),
    'email': fields.String(description='Contact email'),
    'phone': fields.String(description='Contact phone'),
    'company': fields.String(description='Company name'),
    'title': fields.String(description='Job title'),
    'status': fields.String(description='Contact status'),
    'source': fields.String(description='Contact source'),
    'notes': fields.String(description='Contact notes'),
    'created_at': fields.String(description='Creation date'),
    'updated_at': fields.String(description='Last update date')
})

lead_model = api.model('Lead', {
    'id': fields.Integer(required=True, description='Lead ID'),
    'name': fields.String(required=True, description='Lead name'),
    'email': fields.String(description='Lead email'),
    'phone': fields.String(description='Lead phone'),
    'company': fields.String(description='Company name'),
    'status': fields.String(description='Lead status'),
    'score': fields.Integer(description='Lead score'),
    'source': fields.String(description='Lead source'),
    'notes': fields.String(description='Lead notes'),
    'created_at': fields.String(description='Creation date'),
    'updated_at': fields.String(description='Last update date')
})

# AI Models
automation_model = api.model('Automation', {
    'id': fields.Integer(required=True, description='Automation ID'),
    'name': fields.String(required=True, description='Automation name'),
    'description': fields.String(description='Automation description'),
    'trigger': fields.String(description='Automation trigger'),
    'action': fields.String(description='Automation action'),
    'status': fields.String(description='Automation status'),
    'created_at': fields.String(description='Creation date'),
    'updated_at': fields.String(description='Last update date')
})

ai_request_model = api.model('AIRequest', {
    'prompt': fields.String(required=True, description='AI prompt'),
    'context': fields.String(description='Additional context'),
    'model': fields.String(description='AI model to use'),
    'max_tokens': fields.Integer(description='Maximum tokens'),
    'temperature': fields.Float(description='Temperature setting')
})

ai_response_model = api.model('AIResponse', {
    'response': fields.String(required=True, description='AI response'),
    'model': fields.String(description='Model used'),
    'tokens_used': fields.Integer(description='Tokens consumed'),
    'processing_time': fields.Float(description='Processing time in seconds')
})

# Analytics Models
metric_model = api.model('Metric', {
    'name': fields.String(required=True, description='Metric name'),
    'value': fields.Float(required=True, description='Metric value'),
    'unit': fields.String(description='Metric unit'),
    'timestamp': fields.String(description='Metric timestamp'),
    'category': fields.String(description='Metric category')
})

dashboard_model = api.model('Dashboard', {
    'metrics': fields.List(fields.Nested(metric_model), description='Dashboard metrics'),
    'charts': fields.Raw(description='Chart data'),
    'summary': fields.Raw(description='Dashboard summary')
})

# Authentication Endpoints
@auth_ns.route('/login')
class Login(Resource):
    @auth_ns.expect(login_model)
    @auth_ns.marshal_with(token_model, code=200)
    @auth_ns.marshal_with(error_model, code=400)
    @auth_ns.marshal_with(error_model, code=401)
    def post(self):
        """User login"""
        try:
            # Implementation here
            return create_success_response({
                'access_token': 'jwt_token_here',
                'refresh_token': 'refresh_token_here',
                'expires_in': 3600,
                'token_type': 'Bearer'
            }, 'Login successful')
        except ValidationError as e:
            api.abort(400, str(e))
        except AuthenticationError as e:
            api.abort(401, str(e))

@auth_ns.route('/register')
class Register(Resource):
    @auth_ns.expect(register_model)
    @auth_ns.marshal_with(user_model, code=201)
    @auth_ns.marshal_with(error_model, code=400)
    def post(self):
        """User registration"""
        try:
            # Implementation here
            return create_success_response({
                'id': 1,
                'name': 'John Doe',
                'email': 'john@example.com',
                'business_name': 'Acme Corp',
                'industry': 'Technology',
                'team_size': '10-50',
                'created_at': '2024-01-01T00:00:00Z',
                'last_login': None
            }, 'Registration successful', 201)
        except ValidationError as e:
            api.abort(400, str(e))

@auth_ns.route('/refresh')
class RefreshToken(Resource):
    @auth_ns.marshal_with(token_model, code=200)
    @auth_ns.marshal_with(error_model, code=401)
    def post(self):
        """Refresh access token"""
        try:
            # Implementation here
            return create_success_response({
                'access_token': 'new_jwt_token_here',
                'refresh_token': 'new_refresh_token_here',
                'expires_in': 3600,
                'token_type': 'Bearer'
            }, 'Token refreshed successfully')
        except AuthenticationError as e:
            api.abort(401, str(e))

# Email Endpoints
@email_ns.route('/emails')
class EmailList(Resource):
    @auth_ns.marshal_with(email_list_model, code=200)
    @auth_ns.marshal_with(error_model, code=401)
    def get(self):
        """Get list of emails"""
        try:
            # Implementation here
            return create_success_response({
                'emails': [],
                'total': 0,
                'page': 1,
                'per_page': 20
            }, 'Emails retrieved successfully')
        except AuthenticationError as e:
            api.abort(401, str(e))

@email_ns.route('/emails/<string:email_id>')
class EmailDetail(Resource):
    @auth_ns.marshal_with(email_model, code=200)
    @auth_ns.marshal_with(error_model, code=404)
    def get(self, email_id):
        """Get email details"""
        try:
            # Implementation here
            return create_success_response({
                'id': email_id,
                'subject': 'Sample Email',
                'sender': 'sender@example.com',
                'recipient': 'recipient@example.com',
                'body': 'Email body content',
                'date': '2024-01-01T00:00:00Z',
                'read': False,
                'important': False,
                'labels': ['inbox']
            }, 'Email retrieved successfully')
        except Exception as e:
            api.abort(404, 'Email not found')

@email_ns.route('/emails/<string:email_id>/action')
class EmailAction(Resource):
    @auth_ns.expect(email_action_model)
    @auth_ns.marshal_with(success_model, code=200)
    @auth_ns.marshal_with(error_model, code=400)
    def post(self, email_id):
        """Perform action on email"""
        try:
            # Implementation here
            return create_success_response(None, 'Email action completed successfully')
        except ValidationError as e:
            api.abort(400, str(e))

# CRM Endpoints
@crm_ns.route('/contacts')
class ContactList(Resource):
    @auth_ns.marshal_with(contact_model, code=200)
    def get(self):
        """Get list of contacts"""
        try:
            # Implementation here
            return create_success_response([], 'Contacts retrieved successfully')
        except Exception as e:
            api.abort(500, str(e))

@crm_ns.route('/leads')
class LeadList(Resource):
    @auth_ns.marshal_with(lead_model, code=200)
    def get(self):
        """Get list of leads"""
        try:
            # Implementation here
            return create_success_response([], 'Leads retrieved successfully')
        except Exception as e:
            api.abort(500, str(e))

# AI Endpoints
@ai_ns.route('/automations')
class AutomationList(Resource):
    @auth_ns.marshal_with(automation_model, code=200)
    def get(self):
        """Get list of automations"""
        try:
            # Implementation here
            return create_success_response([], 'Automations retrieved successfully')
        except Exception as e:
            api.abort(500, str(e))

@ai_ns.route('/generate')
class AIGenerate(Resource):
    @auth_ns.expect(ai_request_model)
    @auth_ns.marshal_with(ai_response_model, code=200)
    @auth_ns.marshal_with(error_model, code=400)
    def post(self):
        """Generate AI response"""
        try:
            # Implementation here
            return create_success_response({
                'response': 'AI generated response',
                'model': 'gpt-4',
                'tokens_used': 150,
                'processing_time': 1.5
            }, 'AI response generated successfully')
        except ValidationError as e:
            api.abort(400, str(e))

# Analytics Endpoints
@analytics_ns.route('/dashboard')
class Dashboard(Resource):
    @auth_ns.marshal_with(dashboard_model, code=200)
    def get(self):
        """Get dashboard data"""
        try:
            # Implementation here
            return create_success_response({
                'metrics': [],
                'charts': {},
                'summary': {}
            }, 'Dashboard data retrieved successfully')
        except Exception as e:
            api.abort(500, str(e))

@analytics_ns.route('/metrics')
class Metrics(Resource):
    @auth_ns.marshal_with(metric_model, code=200)
    def get(self):
        """Get system metrics"""
        try:
            # Implementation here
            return create_success_response([], 'Metrics retrieved successfully')
        except Exception as e:
            api.abort(500, str(e))

# Health Check
@api.route('/health')
class Health(Resource):
    def get(self):
        """Health check endpoint"""
        return {
            'status': 'healthy',
            'timestamp': '2024-01-01T00:00:00Z',
            'version': '1.0.0',
            'services': {
                'database': 'healthy',
                'redis': 'healthy',
                'email_service': 'healthy'
            }
        }

def init_api_docs(app: Flask):
    """Initialize API documentation"""
    app.register_blueprint(api_bp)
    
    # Add CORS support for API docs
    from flask_cors import CORS
    CORS(app, resources={
        r"/api/*": {
            "origins": ["http://localhost:3000", "https://fikirisolutions.com"],
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"]
        }
    })
