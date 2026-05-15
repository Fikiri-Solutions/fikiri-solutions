#!/usr/bin/env python3
"""
Generate MRR + investor payout (12%) charts for 25–100 clients, by plan tier.

Uses the same list prices as core/billing_manager (monthly).
Requires: pip install matplotlib

Usage:
  python3 scripts/plot_revenue_investor_projection.py
  python3 scripts/plot_revenue_investor_projection.py -o docs/plots/revenue_payout_25_100.png
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np

try:
    import matplotlib.pyplot as plt
except ImportError as e:
    raise SystemExit(
        "matplotlib is required: pip install matplotlib"
    ) from e

# Monthly list prices (USD) — aligned with core/billing_manager.get_pricing_tiers
TIERS: tuple[tuple[str, float, str], ...] = (
    ("Starter", 49.0, "#0f766e"),      # teal
    ("Growth", 99.0, "#c2410c"),       # orange
    ("Business", 199.0, "#1d4ed8"),   # blue
    ("Enterprise", 499.0, "#6d28d9"), # violet
)

INVESTOR_RATE = 0.12


def _setup_style() -> None:
    plt.rcParams.update(
        {
            "figure.facecolor": "#fafafa",
            "axes.facecolor": "#ffffff",
            "axes.edgecolor": "#e5e7eb",
            "axes.linewidth": 1.0,
            "axes.labelcolor": "#374151",
            "axes.titlecolor": "#111827",
            "text.color": "#111827",
            "xtick.color": "#4b5563",
            "ytick.color": "#4b5563",
            "grid.color": "#e5e7eb",
            "grid.linewidth": 0.8,
            "font.family": "sans-serif",
            "font.sans-serif": ["Inter", "Helvetica Neue", "Helvetica", "Arial", "DejaVu Sans"],
            "font.size": 10,
            "axes.titlesize": 12,
            "axes.labelsize": 10,
            "legend.fontsize": 9,
        }
    )


def plot_small_multiples(
    clients: np.ndarray,
    out_path: Path,
    dpi: int = 150,
) -> None:
    """2×2 panels: each tier gets its own y-scale so revenue and payout stay readable."""
    _setup_style()

    fig, axes = plt.subplots(2, 2, figsize=(11, 8), dpi=dpi, constrained_layout=True)
    fig.suptitle(
        "Fikiri — Monthly revenue vs. investor payout (12%)\n"
        "Assumes one price tier per scenario · Clients 25 to 100",
        fontsize=13,
        fontweight="600",
        color="#111827",
    )

    for ax, (name, price, color) in zip(np.array(axes).flat, TIERS):
        mrr = clients * price
        payout = mrr * INVESTOR_RATE

        ax.fill_between(clients, 0, mrr, color=color, alpha=0.12, linewidth=0)
        ax.plot(clients, mrr, color=color, linewidth=2.6, solid_capstyle="round", label="MRR")
        ax.plot(
            clients,
            payout,
            color=color,
            linewidth=2.0,
            linestyle=(0, (5, 4)),
            alpha=0.95,
            label="Payout (12%)",
        )

        ax.set_title(f"{name} · ${price:,.0f}/mo per client", fontweight="600", pad=8)
        ax.set_xlim(22, 102)
        ax.yaxis.set_major_formatter(
            plt.FuncFormatter(lambda v, _: f"${v:,.0f}" if v >= 1000 else f"${v:,.0f}")
        )
        ax.grid(True, alpha=1.0, linestyle="-", linewidth=0.6)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

        # Reference markers at 25, 50, 75, 100
        for xc in (25, 50, 75, 100):
            ax.axvline(xc, color="#f3f4f6", linewidth=1.0, zorder=0)

    for ax in axes[1, :]:
        ax.set_xlabel("Number of clients", fontsize=10, fontweight="500")
    for ax in axes[:, 0]:
        ax.set_ylabel("Monthly ($)", fontsize=10, fontweight="500")

    handles = [
        plt.Line2D([0], [0], color="#374151", linewidth=2.6, label="MRR"),
        plt.Line2D(
            [0],
            [0],
            color="#6b7280",
            linewidth=2.0,
            linestyle=(0, (5, 4)),
            label=f"Investor payout ({INVESTOR_RATE:.0%})",
        ),
    ]
    fig.legend(
        handles=handles,
        loc="upper right",
        bbox_to_anchor=(0.99, 0.99),
        frameon=True,
        fancybox=False,
        edgecolor="#e5e7eb",
        fontsize=9,
    )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)


def plot_combined_log_view(clients: np.ndarray, out_path: Path, dpi: int = 150) -> None:
    """Optional: single chart, log Y — all tiers comparable without squashing lower tiers."""
    _setup_style()
    fig, ax = plt.subplots(figsize=(10.5, 6), dpi=dpi, constrained_layout=True)

    for name, price, color in TIERS:
        mrr = clients * price
        payout = mrr * INVESTOR_RATE
        ax.plot(clients, mrr, color=color, linewidth=2.4, label=f"{name} MRR (${price:,.0f}/seat)")
        ax.plot(
            clients,
            payout,
            color=color,
            linewidth=1.8,
            linestyle=(0, (4, 3)),
            alpha=0.85,
            label=f"{name} payout ({INVESTOR_RATE:.0%})",
        )

    ax.set_yscale("log")
    ax.set_xlabel("Number of clients", fontsize=11, fontweight="500")
    ax.set_ylabel("Monthly ($, log scale)", fontsize=11, fontweight="500")
    ax.set_title(
        "Fikiri — All tiers: MRR and investor payout vs. clients (log scale)",
        fontsize=13,
        fontweight="600",
        pad=12,
    )
    ax.set_xlim(22, 102)
    ax.grid(True, which="both", alpha=0.45)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.legend(
        ncol=2,
        frameon=True,
        edgecolor="#e5e7eb",
        fontsize=8,
        loc="upper left",
        bbox_to_anchor=(0.02, 0.98),
    )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("docs/plots/fikiri_revenue_vs_investor_payout_25_100.png"),
        help="Output PNG path (primary 2×2 chart)",
    )
    parser.add_argument(
        "--also-log",
        type=Path,
        nargs="?",
        const=Path("docs/plots/fikiri_revenue_payout_log_scale.png"),
        default=None,
        help="Also write a log-scale combined chart (optional path)",
    )
    parser.add_argument("--dpi", type=int, default=150)
    args = parser.parse_args()

    clients = np.linspace(25, 100, 200)

    plot_small_multiples(clients, args.output, dpi=args.dpi)
    print(f"Wrote {args.output.resolve()}")

    if args.also_log is not None:
        plot_combined_log_view(clients, args.also_log, dpi=args.dpi)
        print(f"Wrote {args.also_log.resolve()}")


if __name__ == "__main__":
    main()
