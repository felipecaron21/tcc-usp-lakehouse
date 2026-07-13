{{ config(
    materialized='external',
    location= var('data_path') + '/gold/gold_pedidos_por_status.parquet'
) }}

WITH silver_orders AS (
    SELECT *
    FROM {{ ref('silver_orders') }}
)

SELECT
    order_status AS status,
    COUNT(*) AS total_pedidos
FROM silver_orders
GROUP BY order_status
ORDER BY total_pedidos DESC