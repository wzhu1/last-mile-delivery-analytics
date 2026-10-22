"""Load the synthetic ops data into SQLite, run the KPI queries and chart them."""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def load_queries(path: Path) -> dict[str, str]:
    """Split a .sql file into named queries using `-- name: <query>` markers."""
    text = path.read_text()
    parts = re.split(r"^-- name: (\w+)\s*$", text, flags=re.MULTILINE)
    return {name: sql.strip() for name, sql in zip(parts[1::2], parts[2::2])}


def run_kpis(ops: pd.DataFrame) -> dict[str, pd.DataFrame]:
    con = sqlite3.connect(":memory:")
    ops.to_sql("daily_ops", con, index=False)
    queries = load_queries(ROOT / "sql" / "kpis.sql")
    return {name: pd.read_sql_query(sql, con) for name, sql in queries.items()}


def flag_underperformers(scorecard: pd.DataFrame, z: float = 1.0) -> pd.DataFrame:
    """Stations whose cost per parcel is more than `z` std devs above the network mean."""
    mu, sd = scorecard.cost_per_parcel.mean(), scorecard.cost_per_parcel.std()
    out = scorecard.assign(cost_z=(scorecard.cost_per_parcel - mu) / sd)
    return out[out.cost_z > z].sort_values("cost_z", ascending=False)


def plot(results: dict[str, pd.DataFrame], out_dir: Path) -> None:
    out_dir.mkdir(exist_ok=True)
    region = results["region_kpis"]

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.scatter(region.on_time_rate * 100, region.cost_per_parcel, s=region.parcels / 2000, alpha=0.7)
    for _, r in region.iterrows():
        ax.annotate(r.region, (r.on_time_rate * 100, r.cost_per_parcel), xytext=(6, 4), textcoords="offset points")
    ax.set_xlabel("On-time delivery rate (%)")
    ax.set_ylabel("Cost per parcel")
    ax.set_title("Regional service vs. cost (bubble size = parcel volume)")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(out_dir / "region_service_vs_cost.png", dpi=150)
    plt.close(fig)

    trend = results["weekly_trend"]
    fig, ax = plt.subplots(figsize=(9, 5))
    for name, g in trend.groupby("region"):
        ax.plot(g.week, g.on_time_rate * 100, marker="o", ms=3, label=name)
    ax.set_ylabel("On-time rate (%)")
    ax.set_title("Weekly on-time rate by region")
    ax.tick_params(axis="x", rotation=60)
    ax.legend(fontsize=8, ncol=2)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(out_dir / "weekly_on_time_trend.png", dpi=150)
    plt.close(fig)


def main() -> None:
    ops = pd.read_csv(ROOT / "data" / "daily_ops.csv")
    results = run_kpis(ops)
    plot(results, ROOT / "figures")
    flagged = flag_underperformers(results["station_scorecard"])

    reports = ROOT / "reports"
    reports.mkdir(exist_ok=True)
    results["region_kpis"].to_csv(reports / "region_kpis.csv", index=False)
    flagged.to_csv(reports / "flagged_stations.csv", index=False)
    print(results["region_kpis"].to_string(index=False))
    print(f"\n{len(flagged)} stations flagged for high cost per parcel:")
    print(flagged[["station_id", "region", "cost_per_parcel", "on_time_rate", "cost_z"]].round(3).to_string(index=False))


if __name__ == "__main__":
    main()
