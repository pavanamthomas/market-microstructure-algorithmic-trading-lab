"""Replay the flagship table without plotting."""

from __future__ import annotations

from microstructure.layers import LayerConfig, layer_table, simulate_layers


def main() -> None:
    cfg = LayerConfig()
    table = layer_table(cfg)
    df = simulate_layers(cfg)
    print(table.to_string(float_format=lambda x: f"{x: .6f}"))
    hit = float(((df["causal_side"] * df["eps"]) > 0).mean())
    print(f"hit_rate={hit:.4f} mean_abs_eps={float(df['eps'].abs().mean()):.5f}")


if __name__ == "__main__":
    main()
