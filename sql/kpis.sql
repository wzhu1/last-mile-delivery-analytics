-- Regional KPI rollup (SQLite). Loaded from data/daily_ops.csv by src/kpis.py.

-- name: region_kpis
SELECT
    region,
    COUNT(DISTINCT station_id)                                   AS stations,
    SUM(parcels)                                                 AS parcels,
    ROUND(1.0 * SUM(on_time_parcels) / SUM(parcels), 4)          AS on_time_rate,
    ROUND(1.0 * SUM(parcels) / SUM(courier_hours), 2)            AS parcels_per_courier_hour,
    ROUND((SUM(fuel_cost) + SUM(labor_cost)) / SUM(parcels), 3)  AS cost_per_parcel,
    ROUND(1.0 * SUM(route_km) / SUM(parcels), 3)                 AS km_per_parcel,
    ROUND(1.0 * SUM(failed_attempts) / SUM(parcels), 4)          AS failed_attempt_rate
FROM daily_ops
GROUP BY region
ORDER BY cost_per_parcel DESC;

-- name: station_scorecard
WITH s AS (
    SELECT
        station_id,
        region,
        1.0 * SUM(on_time_parcels) / SUM(parcels)              AS on_time_rate,
        (SUM(fuel_cost) + SUM(labor_cost)) / SUM(parcels)      AS cost_per_parcel,
        1.0 * SUM(parcels) / SUM(courier_hours)                AS productivity
    FROM daily_ops
    GROUP BY station_id, region
)
SELECT
    s.*,
    RANK() OVER (ORDER BY on_time_rate DESC)    AS on_time_rank,
    RANK() OVER (ORDER BY cost_per_parcel ASC)  AS cost_rank
FROM s
ORDER BY cost_per_parcel DESC;

-- name: weekly_trend
SELECT
    region,
    strftime('%Y-%W', date)                                   AS week,
    SUM(parcels)                                              AS parcels,
    ROUND(1.0 * SUM(on_time_parcels) / SUM(parcels), 4)       AS on_time_rate
FROM daily_ops
GROUP BY region, week
ORDER BY region, week;
