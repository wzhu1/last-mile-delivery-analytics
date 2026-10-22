"""Single-courier route optimization: nearest-neighbor construction + 2-opt.

Compares an optimized delivery sequence against the naive "order of arrival"
sequence on randomly generated (synthetic) delivery points around a station.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def distance_matrix(points: np.ndarray) -> np.ndarray:
    diff = points[:, None, :] - points[None, :, :]
    return np.sqrt((diff**2).sum(-1))


def route_length(route: list[int], dist: np.ndarray) -> float:
    """Length of a closed tour starting and ending at route[0] (the depot)."""
    return float(sum(dist[a, b] for a, b in zip(route, route[1:] + route[:1])))


def nearest_neighbor(dist: np.ndarray, start: int = 0) -> list[int]:
    n = len(dist)
    route, visited = [start], {start}
    while len(route) < n:
        last = route[-1]
        nxt = min((j for j in range(n) if j not in visited), key=lambda j: dist[last, j])
        route.append(nxt)
        visited.add(nxt)
    return route


def two_opt(route: list[int], dist: np.ndarray) -> list[int]:
    """Repeatedly reverse segments while doing so shortens the tour. Depot stays first."""
    best = route[:]
    n = len(best)
    improved = True
    while improved:
        improved = False
        for i in range(1, n - 1):
            for k in range(i + 1, n):
                a, b = best[i - 1], best[i]
                c, d = best[k], best[(k + 1) % n]
                delta = dist[a, c] + dist[b, d] - dist[a, b] - dist[c, d]
                if delta < -1e-9:
                    best[i : k + 1] = reversed(best[i : k + 1])
                    improved = True
    return best


def simulate(n_routes: int = 50, stops: int = 40, seed: int = 11) -> np.ndarray:
    """Return % distance saved vs. arrival order for `n_routes` synthetic routes."""
    rng = np.random.default_rng(seed)
    savings = []
    for _ in range(n_routes):
        pts = np.vstack([[0, 0], rng.normal(0, 3, size=(stops, 2))])
        dist = distance_matrix(pts)
        baseline = route_length(list(range(len(pts))), dist)
        optimized = route_length(two_opt(nearest_neighbor(dist), dist), dist)
        savings.append(1 - optimized / baseline)
    return np.array(savings)


def plot_example(seed: int = 3, stops: int = 40) -> None:
    rng = np.random.default_rng(seed)
    pts = np.vstack([[0, 0], rng.normal(0, 3, size=(stops, 2))])
    dist = distance_matrix(pts)
    naive = list(range(len(pts)))
    opt = two_opt(nearest_neighbor(dist), dist)

    fig, axes = plt.subplots(1, 2, figsize=(11, 5), sharex=True, sharey=True)
    for ax, route, title in [(axes[0], naive, "Order of arrival"), (axes[1], opt, "Nearest neighbor + 2-opt")]:
        tour = route + route[:1]
        ax.plot(pts[tour, 0], pts[tour, 1], "-", lw=1, color="tab:blue")
        ax.scatter(pts[1:, 0], pts[1:, 1], s=15, color="tab:gray")
        ax.scatter(*pts[0], s=120, marker="s", color="tab:red", label="Station")
        ax.set_title(f"{title}: {route_length(route, dist):.1f} km")
        ax.set_aspect("equal")
        ax.legend(loc="lower right")
    fig.suptitle("Synthetic 40-stop delivery route")
    fig.tight_layout()
    (ROOT / "figures").mkdir(exist_ok=True)
    fig.savefig(ROOT / "figures" / "route_before_after.png", dpi=150)
    plt.close(fig)


def main() -> None:
    savings = simulate()
    plot_example()
    print(f"distance saved vs. arrival order over {len(savings)} synthetic routes: "
          f"mean {savings.mean():.1%}, median {np.median(savings):.1%}, min {savings.min():.1%}")


if __name__ == "__main__":
    main()
