"""
Population data — served from a bundled local dataset (population_data.py).
No external API, so it always works, instantly and offline.

`world_live` lets the frontend show a Worldometer-style ticking counter:
extrapolate from a base value at a known instant using an annual growth rate.
"""
import population_data as pd


def get_countries():
    countries = [
        {"name": n, "code": c, "population": p, "region": r, "capital": cap}
        for (n, c, p, r, cap) in pd.COUNTRIES
    ]
    countries.sort(key=lambda x: x["population"], reverse=True)
    return {
        "world_total": pd.WORLD_TOTAL,
        "world_live": {
            "base": pd.WORLD_BASE,
            "base_epoch_ms": pd.WORLD_BASE_EPOCH_MS,
            "per_second": pd.WORLD_ANNUAL_GROWTH / (365.25 * 24 * 3600),
        },
        "countries": countries,
    }
