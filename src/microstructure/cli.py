"""Print the flagship layer table."""

from __future__ import annotations

import argparse

from microstructure.layers import LayerConfig, layer_table, simulate_layers


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Flagship mid-to-executable peel")
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--n", type=int, default=4000)
    args = parser.parse_args(argv)
    cfg = LayerConfig(seed=args.seed, n_events=args.n)
    table = layer_table(cfg)
    df = simulate_layers(cfg)
    hit = float(((df["causal_side"] * df["eps"]) > 0).mean())
    print("mean P&L per event (qty = %d)" % cfg.qty)
    print(table.to_string(float_format=lambda x: f"{x: .6f}"))
    print()
    print("mean half-spread:", float(df["half_spread"].mean()))
    print("mean |eps|:", float(df["eps"].abs().mean()))
    print("P(causal side matches eps):", hit)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
