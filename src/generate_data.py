"""Generate a synthetic last-mile delivery dataset.

Everything here is simulated. Region names, stations, couriers and numbers are
invented to mimic the *shape* of express-delivery operations data (parcel
volume, promised vs. actual delivery time, courier hours, route distance) so the
analysis pipeline can be demonstrated end to end without using any real
company's data.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

REGIONS = {
    # region: (stations, base daily parcels per station, congestion factor)
    "North Hub": (4, 1800, 1.00),
    "East Coast": (5, 2200, 1.15),
    "Central City": (6, 2600, 1.35),
    "West Valley": (3, 1200, 0.90),
    "South Port": (4, 2000, 1.10),
    "Mountain Belt": (3, 800, 1.25),
}

DEFAULT_DAYS = 90
SEED = 7


def build_stations(rng: np.random.Generator) -> pd.DataFrame:
    rows = []
    for region, (n_stations, base, congestion) in REGIONS.items():
        for i in range(n_stations):
            rows.append(
                {
                    "station_id": f"{region[:2].upper()}-{i + 1:02d}",
                    "region": region,
                    "base_volume": base * rng.uniform(0.7, 1.3),
                    "congestion": congestion * rng.uniform(0.9, 1.1),
                    "couriers": int(rng.integers(18, 40)),
                }
            )
    return pd.DataFrame(rows)


def build_daily_ops(stations: pd.DataFrame, days: int, rng: np.random.Generator) -> pd.DataFrame:
    dates = pd.date_range("2025-06-01", periods=days, freq="D")
    rows = []
    for _, st in stations.iterrows():
        for d in dates:
            weekday_factor = 1.15 if d.day_of_week in (0, 1) else (0.8 if d.day_of_week == 6 else 1.0)
            promo_factor = 1.6 if d.day in (18, 19) else 1.0  # mid-month shopping peak
            parcels = rng.poisson(st.base_volume * weekday_factor * promo_factor)
            courier_hours = st.couriers * rng.normal(9.0, 0.6)
            load = parcels / (st.couriers * 75)  # >1 means the station is overloaded
            on_time_prob = np.clip(0.97 - 0.18 * max(load - 0.9, 0) - 0.05 * (st.congestion - 1), 0.5, 0.99)
            on_time = rng.binomial(parcels, on_time_prob)
            route_km = parcels * rng.normal(0.42, 0.04) * st.congestion
            rows.append(
                {
                    "date": d.date().isoformat(),
                    "station_id": st.station_id,
                    "region": st.region,
                    "parcels": parcels,
                    "on_time_parcels": on_time,
                    "courier_hours": round(courier_hours, 1),
                    "route_km": round(route_km, 1),
                    "fuel_cost": round(route_km * rng.normal(0.95, 0.05), 2),
                    "labor_cost": round(courier_hours * 28.0, 2),
                    "failed_attempts": rng.binomial(parcels, 0.015 * st.congestion),
                }
            )
    return pd.DataFrame(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--days", type=int, default=DEFAULT_DAYS)
    parser.add_argument("--seed", type=int, default=SEED)
    parser.add_argument("--out", type=Path, default=Path(__file__).resolve().parents[1] / "data")
    args = parser.parse_args()

    rng = np.random.default_rng(args.seed)
    stations = build_stations(rng)
    ops = build_daily_ops(stations, args.days, rng)

    args.out.mkdir(parents=True, exist_ok=True)
    stations.drop(columns=["base_volume", "congestion"]).to_csv(args.out / "stations.csv", index=False)
    ops.to_csv(args.out / "daily_ops.csv", index=False)
    print(f"wrote {len(stations)} stations and {len(ops):,} station-days to {args.out}")


if __name__ == "__main__":
    main()
