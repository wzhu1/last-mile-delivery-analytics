import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from generate_data import build_daily_ops, build_stations  # noqa: E402
from kpis import flag_underperformers, run_kpis  # noqa: E402
from route_optimizer import distance_matrix, nearest_neighbor, route_length, two_opt  # noqa: E402


def small_ops():
    rng = np.random.default_rng(0)
    return build_daily_ops(build_stations(rng), days=14, rng=rng)


def test_generated_data_is_consistent():
    ops = small_ops()
    assert (ops.on_time_parcels <= ops.parcels).all()
    assert (ops.failed_attempts <= ops.parcels).all()
    assert ops.region.nunique() == 6


def test_region_kpis_match_pandas():
    ops = small_ops()
    region = run_kpis(ops)["region_kpis"].set_index("region")
    expected = ops.groupby("region").on_time_parcels.sum() / ops.groupby("region").parcels.sum()
    assert np.allclose(region.on_time_rate.sort_index(), expected.sort_index().round(4))


def test_flag_underperformers_threshold():
    sc = pd.DataFrame({"station_id": list("abcde"), "cost_per_parcel": [1, 1, 1, 1, 5]})
    assert list(flag_underperformers(sc).station_id) == ["e"]


def test_two_opt_never_worse_and_visits_all_stops():
    rng = np.random.default_rng(1)
    pts = rng.normal(size=(25, 2))
    dist = distance_matrix(pts)
    nn = nearest_neighbor(dist)
    opt = two_opt(nn, dist)
    assert sorted(opt) == list(range(25))
    assert opt[0] == 0
    assert route_length(opt, dist) <= route_length(nn, dist) + 1e-9


def test_two_opt_solves_square():
    pts = np.array([[0, 0], [1, 1], [1, 0], [0, 1]], dtype=float)
    dist = distance_matrix(pts)
    assert np.isclose(route_length(two_opt([0, 1, 2, 3], dist), dist), 4.0)
