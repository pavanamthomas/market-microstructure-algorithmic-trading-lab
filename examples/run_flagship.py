"""Print and plot the flagship layer table."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt

from microstructure.layers import LayerConfig, layer_table, simulate_layers


def main() -> None:
    cfg = LayerConfig()
    table = layer_table(cfg)
    df = simulate_layers(cfg)
    print("mean P&L per event")
    print(table.to_string(float_format=lambda x: f"{x: .6f}"))
    print()
    hit = float(((df["causal_side"] * df["eps"]) > 0).mean())
    print(f"signal hit rate (sign matches ε): {hit:.3f}")
    print(f"mean |ε|: {float(df['eps'].abs().mean()):.5f}")
    print(f"quoted half-spread: {float(df['half_spread'].mean()):.4f}")

    fig, ax = plt.subplots(figsize=(9, 4.2))
    per_unit = table["mean_pnl_per_unit"]
    colors = ["#3b6d11" if v > 0 else "#8b1e1e" for v in per_unit]
    ax.bar(range(len(per_unit)), per_unit.to_numpy(), color=colors)
    ax.axhline(0.0, color="black", linewidth=0.8)
    ax.set_xticks(range(len(per_unit)))
    ax.set_xticklabels(list(per_unit.index), rotation=35, ha="right")
    ax.set_ylabel("mean P&L per unit")
    ax.set_title("Same trades. Different price at which they are assumed to occur.")
    fig.tight_layout()
    out = Path("figures")
    out.mkdir(exist_ok=True)
    fig.savefig(out / "flagship_layers.png", dpi=140)
    print("wrote figures/flagship_layers.png")


if __name__ == "__main__":
    main()
