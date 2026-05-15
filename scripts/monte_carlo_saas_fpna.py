#!/usr/bin/env python3
"""
Fikiri Monte Carlo — hybrid automation consultancy + recurring SaaS (default).

Each path is a 36-month monthly episode. Hybrid mode models:
  • Segmented clients (solo / team / mid-market) with setup-fee cash on close,
    tier-mapped MRR (Starter / Growth / Business), and tier-specific churn.
  • Optional lumpy custom-work / SOW revenue (sparse, non-recurring).
  • Recurring MRR, variable COGS (Stripe + AI high case), fixed overhead,
    investor % of MRR, optional CASA loan.

Pure low-MRR SaaS only: pass --pure-saas (legacy tier-mix + single churn band).

Sources: docs/FINANCIAL_MODEL_AND_RATE_LIMITING.md, core/billing_manager.py,
  docs/archive/business/FAMILY_HELP_LOAN_TEMPLATE.md (optional loan).

Examples:
  python3 scripts/monte_carlo_saas_fpna.py --n 20000
  python3 scripts/monte_carlo_saas_fpna.py --pure-saas --compare --n 15000
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, replace
from typing import Sequence

import numpy as np


# --- Subscription MRR (monthly) ---
PRICE_STARTER = 49.00
PRICE_GROWTH = 99.00
PRICE_BUSINESS = 199.00
PRICE_ENTERPRISE = 499.00
TIER_PRICES = np.array([PRICE_STARTER, PRICE_GROWTH, PRICE_BUSINESS, PRICE_ENTERPRISE])
TIER_NAMES = ("Starter", "Growth", "Business", "Enterprise")

# Legacy pure-SaaS tier mix (pessimistic).
MIX_STARTER = 0.70
MIX_GROWTH = 0.25
MIX_BUSINESS = 0.05
MIX_ENTERPRISE = 0.00
PURE_SAAS_MIX = np.array([MIX_STARTER, MIX_GROWTH, MIX_BUSINESS, MIX_ENTERPRISE])


def stripe_fee_on_charge(amount: float) -> float:
    return 0.029 * float(amount) + 0.30


OPENAI_HIGH = np.array([0.40, 1.60, 8.00, 50.00])


def variable_cost_per_customer_month() -> np.ndarray:
    return np.array([stripe_fee_on_charge(p) + o for p, o in zip(TIER_PRICES, OPENAI_HIGH)])


VARIABLE_COST_PER_CUSTOMER = variable_cost_per_customer_month()

# Extra monthly delivery / support load by tier (hybrid ops), beyond VARIABLE_COST_PER_CUSTOMER.
EXTRA_OPS_COST_BY_TIER = np.array([5.0, 18.0, 55.0, 120.0])

LOAN_TOTAL_USD = 3850.00
LOAN_MONTHS = 8
LOAN_PAYMENT_MONTHLY = LOAN_TOTAL_USD / LOAN_MONTHS

HORIZON_MONTHS = 36
RNG_SEED_DEFAULT = 42


@dataclass(frozen=True)
class SegmentSpec:
    """One client class: setup fee range (card/Stripe), maps to subscription tier index."""

    name: str
    setup_low: float
    setup_high: float
    tier_index: int
    churn_low: float
    churn_high: float


# Solo / micro | Small LLC–team | Mid-market (maps to Business tier MRR).
SEGMENTS: tuple[SegmentSpec, ...] = (
    SegmentSpec("solo_micro", 250.0, 450.0, 0, 0.06, 0.10),
    SegmentSpec("small_team", 500.0, 1000.0, 1, 0.04, 0.07),
    SegmentSpec("mid_market", 2500.0, 5000.0, 2, 0.02, 0.05),
)


@dataclass(frozen=True)
class ScenarioParams:
    trials_low: float = 2.0
    trials_high: float = 12.0
    conv_low: float = 0.02
    conv_high: float = 0.06
    churn_low: float = 0.05
    churn_high: float = 0.09
    fixed_overhead_usd: float = 450.0
    investor_rate: float = 0.12
    ramp_months: int = 3
    ramp_scale: float = 0.35
    use_hybrid_model: bool = True
    weight_solo: float = 0.48
    weight_team: float = 0.37
    weight_mid: float = 0.15
    lumpy_sow_prob: float = 0.06
    lumpy_sow_low: float = 1500.0
    lumpy_sow_high: float = 12000.0


DEFAULT_SCENARIO = ScenarioParams()


def segment_weights_array(p: ScenarioParams) -> np.ndarray:
    w = np.array([p.weight_solo, p.weight_team, p.weight_mid], dtype=float)
    s = w.sum()
    if s <= 0:
        raise ValueError("segment weights must sum > 0")
    return w / s


@dataclass
class SimResult:
    mrr_end: float
    customers_end: int
    min_monthly_net: float
    cumulative_contribution: np.ndarray
    mrr_path: np.ndarray
    net_monthly_path: np.ndarray
    nonrecurring_cash_36: float


def _churn_rate_for_tier(
    rng: np.random.Generator, tier_index: int, params: ScenarioParams, hybrid: bool
) -> float:
    if not hybrid:
        return float(rng.uniform(params.churn_low, params.churn_high))
    if tier_index <= 2:
        seg = SEGMENTS[tier_index]
        return float(rng.uniform(seg.churn_low, seg.churn_high))
    return float(rng.uniform(SEGMENTS[2].churn_low, SEGMENTS[2].churn_high))


def simulate_one(
    rng: np.random.Generator,
    *,
    params: ScenarioParams,
    include_casa_loan: bool,
) -> SimResult:
    cust = np.zeros(4, dtype=np.int64)
    mrr_path = np.zeros(HORIZON_MONTHS)
    net_monthly = np.zeros(HORIZON_MONTHS)

    loan_payment = LOAN_PAYMENT_MONTHLY if include_casa_loan else 0.0
    loan_months = LOAN_MONTHS if include_casa_loan else 0
    hybrid = params.use_hybrid_model
    seg_w = segment_weights_array(params) if hybrid else PURE_SAAS_MIX

    nonrecurring_total = 0.0

    for t in range(HORIZON_MONTHS):
        trials = rng.uniform(params.trials_low, params.trials_high)
        if t < params.ramp_months:
            trials *= params.ramp_scale
        conv = rng.uniform(params.conv_low, params.conv_high)
        new_logos = int(max(0, round(trials * conv)))

        month_nonrecurring = 0.0

        if new_logos > 0:
            if hybrid:
                alloc = rng.multinomial(new_logos, seg_w)
                for seg_idx, n_new in enumerate(alloc):
                    if n_new <= 0:
                        continue
                    seg = SEGMENTS[seg_idx]
                    gross = rng.uniform(seg.setup_low, seg.setup_high, size=n_new)
                    stripe_on_setups = 0.029 * gross + 0.30
                    net_setup = float(np.sum(gross - stripe_on_setups))
                    month_nonrecurring += net_setup
                    cust[seg.tier_index] += n_new
            else:
                alloc = rng.multinomial(new_logos, PURE_SAAS_MIX)
                cust += alloc

        if hybrid and params.lumpy_sow_prob > 0 and rng.random() < params.lumpy_sow_prob:
            lump = rng.uniform(params.lumpy_sow_low, params.lumpy_sow_high)
            fee = stripe_fee_on_charge(lump)
            month_nonrecurring += lump - fee

        nonrecurring_total += month_nonrecurring

        for i in range(4):
            if cust[i] <= 0:
                continue
            cr = _churn_rate_for_tier(rng, i, params, hybrid)
            lost = rng.binomial(int(cust[i]), cr)
            cust[i] = max(0, cust[i] - lost)

        mrr = float(np.dot(cust, TIER_PRICES))
        mrr_path[t] = mrr

        var_stack = VARIABLE_COST_PER_CUSTOMER + EXTRA_OPS_COST_BY_TIER
        variable = float(np.dot(cust, var_stack))
        investor = params.investor_rate * mrr
        loan = loan_payment if t < loan_months else 0.0

        net = (
            mrr
            + month_nonrecurring
            - params.fixed_overhead_usd
            - variable
            - investor
            - loan
        )
        net_monthly[t] = net

    cumulative = np.cumsum(net_monthly)
    return SimResult(
        mrr_end=float(mrr_path[-1]),
        customers_end=int(cust.sum()),
        min_monthly_net=float(net_monthly.min()),
        cumulative_contribution=cumulative,
        mrr_path=mrr_path,
        net_monthly_path=net_monthly,
        nonrecurring_cash_36=float(nonrecurring_total),
    )


def run_paths(
    n: int,
    seed: int,
    params: ScenarioParams,
    *,
    include_casa_loan: bool,
) -> dict[str, np.ndarray]:
    rng = np.random.default_rng(seed)
    mrr_end: list[float] = []
    cust_end: list[int] = []
    min_net: list[float] = []
    cum36: list[float] = []
    nonrec: list[float] = []

    for _ in range(n):
        r = simulate_one(rng, params=params, include_casa_loan=include_casa_loan)
        mrr_end.append(r.mrr_end)
        cust_end.append(r.customers_end)
        min_net.append(r.min_monthly_net)
        cum36.append(r.cumulative_contribution[-1])
        nonrec.append(r.nonrecurring_cash_36)

    return {
        "mrr_end": np.array(mrr_end),
        "cust_end": np.array(cust_end),
        "min_net": np.array(min_net),
        "cum36": np.array(cum36),
        "nonrecurring_36": np.array(nonrec),
    }


def percentile_summary(values: np.ndarray, label: str) -> None:
    p10, p50, p90 = np.percentile(values, [10, 50, 90])
    print(f"  {label:<42} P10={p10:>12,.2f}  P50={p50:>12,.2f}  P90={p90:>12,.2f}")


def parse_scenario_from_args(args: argparse.Namespace) -> ScenarioParams:
    return ScenarioParams(
        trials_low=args.trials_low,
        trials_high=args.trials_high,
        conv_low=args.conv_low,
        conv_high=args.conv_high,
        churn_low=args.churn_low,
        churn_high=args.churn_high,
        fixed_overhead_usd=args.fixed_overhead,
        investor_rate=args.investor_rate,
        ramp_months=args.ramp_months,
        ramp_scale=args.ramp_scale,
        use_hybrid_model=not args.pure_saas,
        weight_solo=args.weight_solo,
        weight_team=args.weight_team,
        weight_mid=args.weight_mid,
        lumpy_sow_prob=args.lumpy_sow_prob,
        lumpy_sow_low=args.lumpy_sow_low,
        lumpy_sow_high=args.lumpy_sow_high,
    )


def print_banner(title: str) -> None:
    print()
    print(title)
    print("-" * len(title))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Fikiri Monte Carlo: hybrid consultancy + SaaS (default) or pure SaaS (--pure-saas)."
    )
    parser.add_argument("--n", type=int, default=10_000)
    parser.add_argument("--seed", type=int, default=RNG_SEED_DEFAULT)
    parser.add_argument("--starting-cash", type=float, default=None)
    parser.add_argument("--casa-loan", action="store_true")
    parser.add_argument("--compare", action="store_true")

    parser.add_argument(
        "--pure-saas",
        action="store_true",
        help="Legacy model: tier mix only, single churn band, no setup / SOW revenue.",
    )
    parser.add_argument("--trials-low", type=float, default=DEFAULT_SCENARIO.trials_low)
    parser.add_argument("--trials-high", type=float, default=DEFAULT_SCENARIO.trials_high)
    parser.add_argument("--conv-low", type=float, default=DEFAULT_SCENARIO.conv_low)
    parser.add_argument("--conv-high", type=float, default=DEFAULT_SCENARIO.conv_high)
    parser.add_argument("--churn-low", type=float, default=DEFAULT_SCENARIO.churn_low)
    parser.add_argument("--churn-high", type=float, default=DEFAULT_SCENARIO.churn_high)
    parser.add_argument("--fixed", type=float, default=DEFAULT_SCENARIO.fixed_overhead_usd, dest="fixed_overhead")
    parser.add_argument("--investor-rate", type=float, default=DEFAULT_SCENARIO.investor_rate)
    parser.add_argument("--ramp-months", type=int, default=DEFAULT_SCENARIO.ramp_months)
    parser.add_argument("--ramp-scale", type=float, default=DEFAULT_SCENARIO.ramp_scale)

    parser.add_argument("--weight-solo", type=float, default=DEFAULT_SCENARIO.weight_solo)
    parser.add_argument("--weight-team", type=float, default=DEFAULT_SCENARIO.weight_team)
    parser.add_argument("--weight-mid", type=float, default=DEFAULT_SCENARIO.weight_mid)
    parser.add_argument("--lumpy-sow-prob", type=float, default=DEFAULT_SCENARIO.lumpy_sow_prob)
    parser.add_argument("--lumpy-sow-low", type=float, default=DEFAULT_SCENARIO.lumpy_sow_low)
    parser.add_argument("--lumpy-sow-high", type=float, default=DEFAULT_SCENARIO.lumpy_sow_high)

    args = parser.parse_args()
    params = parse_scenario_from_args(args)

    if args.compare:
        return run_compare_table(args.n, args.seed, args.casa_loan)

    rng = np.random.default_rng(args.seed)

    print_banner("Fikiri Monte Carlo — parameters")
    print(f"  Horizon:           {HORIZON_MONTHS} months")
    print(f"  Mode:                {'HYBRID (setup fees + MRR + optional SOW)' if params.use_hybrid_model else 'PURE SAAS (legacy)'}")
    print(f"  Tier MRR:           {TIER_PRICES}")
    if params.use_hybrid_model:
        sw = segment_weights_array(params)
        print(f"  Segment weights:    solo={sw[0]:.2f}  team={sw[1]:.2f}  mid={sw[2]:.2f}")
        for seg in SEGMENTS:
            print(
                f"    • {seg.name}: setup ${seg.setup_low:,.0f}–${seg.setup_high:,.0f} → "
                f"{TIER_NAMES[seg.tier_index]} (${TIER_PRICES[seg.tier_index]:.0f}/mo), "
                f"churn {seg.churn_low:.0%}–{seg.churn_high:.0%}"
            )
        print(f"  Lumpy SOW/month:    p={params.lumpy_sow_prob:.0%}  "
              f"${params.lumpy_sow_low:,.0f}–${params.lumpy_sow_high:,.0f} (net of Stripe)")
        print(f"  Ops cost / tier-mo: {EXTRA_OPS_COST_BY_TIER}")
    else:
        print(f"  Tier mix (new):     {PURE_SAAS_MIX}")
        print(f"  Churn (uniform):    [{params.churn_low:.0%}, {params.churn_high:.0%}] all tiers")
    print(f"  Trials/month:       [{params.trials_low}, {params.trials_high}] × {params.ramp_scale} for first {params.ramp_months} mo")
    print(f"  Trial→paid:          [{params.conv_low:.0%}, {params.conv_high:.0%}]")
    print(f"  Variable COGS/cust: {VARIABLE_COST_PER_CUSTOMER}")
    print(f"  Fixed overhead:      ${params.fixed_overhead_usd:,.0f}/mo")
    print(f"  Investor:            {params.investor_rate:.0%} of MRR")
    if args.casa_loan:
        print(f"  CASA loan:           ${LOAN_PAYMENT_MONTHLY:,.2f}/mo × {LOAN_MONTHS} (${LOAN_TOTAL_USD:,.0f})")
    else:
        print("  CASA loan:           off")

    mrr_end: list[float] = []
    cust_end: list[int] = []
    min_net: list[float] = []
    cum36: list[float] = []
    nonrec: list[float] = []
    bankrupt_month: list[int | None] = []

    for _ in range(args.n):
        r = simulate_one(rng, params=params, include_casa_loan=args.casa_loan)
        mrr_end.append(r.mrr_end)
        cust_end.append(r.customers_end)
        min_net.append(r.min_monthly_net)
        cum36.append(r.cumulative_contribution[-1])
        nonrec.append(r.nonrecurring_cash_36)
        cum = r.cumulative_contribution
        if args.starting_cash is not None:
            crossed = np.where(cum < -args.starting_cash)[0]
            bankrupt_month.append(int(crossed[0] + 1) if len(crossed) else None)

    print_banner(f"Results (N={args.n:,})")
    percentile_summary(np.array(mrr_end), "Ending MRR ($)")
    percentile_summary(np.array(cust_end), "Ending paying customers (#)")
    percentile_summary(np.array(min_net), "Worst single-month net ($)")
    percentile_summary(np.array(cum36), "36-mo cumulative contribution ($)")
    if params.use_hybrid_model:
        percentile_summary(np.array(nonrec), "36-mo non-recurring cash ($, setup+SOW net)")

    if args.starting_cash is not None:
        months_to_fail = [m for m in bankrupt_month if m is not None]
        if months_to_fail:
            print(
                f"  P(run out of ${args.starting_cash:,.0f} start cash): {len(months_to_fail)/args.n:.1%}"
            )
        else:
            print(f"  No paths exhausted ${args.starting_cash:,.0f} starting cash.")

    print()
    print(
        "Contribution = MRR + non-recurring (net Stripe) − fixed − variable − investor% − loan. "
        "No annual prepay, usage overages, or Postgres step regimes in this build."
    )
    return 0


def run_compare_table(n: int, seed: int, casa_loan: bool) -> int:
    base = DEFAULT_SCENARIO
    pessimist_hybrid = replace(
        base,
        weight_solo=0.62,
        weight_team=0.28,
        weight_mid=0.10,
        lumpy_sow_prob=0.04,
    )
    moderate = replace(
        base,
        trials_low=8.0,
        trials_high=24.0,
        conv_low=0.05,
        conv_high=0.12,
        ramp_months=3,
        ramp_scale=0.35,
    )
    pure = replace(base, use_hybrid_model=False)

    scenarios: Sequence[tuple[str, ScenarioParams]] = (
        ("1. Hybrid (default segment mix + setup + SOW)", base),
        ("2. Hybrid pessimistic (more solo, fewer SOWs)", pessimist_hybrid),
        ("3. Moderate funnel + hybrid revenue", moderate),
        ("4. Pure SaaS only (legacy — no setup/SOW)", pure),
        ("5. Hybrid + no investor cut", replace(base, investor_rate=0.0)),
        ("6. Hybrid + $150/mo fixed", replace(base, fixed_overhead_usd=150.0)),
    )

    loan_note = "  [CASA loan ON]" if casa_loan else ""

    print_banner(f"Sensitivity comparison  N={n:,}  seed={seed}{loan_note}")
    print()

    hdr = f"{'Scenario':<48} {'Contrib P10':>14} {'P50':>14} {'P90':>14} {'NR cash P50':>14}"
    print(hdr)
    print("-" * len(hdr))

    for label, scen in scenarios:
        out = run_paths(n, seed, scen, include_casa_loan=casa_loan)
        p10, p50, p90 = np.percentile(out["cum36"], [10, 50, 90])
        nr50 = float(np.percentile(out["nonrecurring_36"], 50))
        print(f"{label:<48} {p10:>14,.0f} {p50:>14,.0f} {p90:>14,.0f} {nr50:>14,.0f}")

    print()
    print("NR cash P50 = median 36-mo setup + lumpy SOW (after Stripe), hybrid rows only.")
    print("Pure SaaS row has no non-recurring engine — compare survivability vs hybrid.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
