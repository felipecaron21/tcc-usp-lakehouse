{{ config(
    materialized='external',
    location='../../data/gold/gold_tempo_entrega_estado.parquet'
) }}

WITH orders AS (
    SELECT *
    FROM {{ ref('silver_orders') }}
    WHERE order_status = 'delivered'
    AND entrega_inconsistente = FALSE
),

customers AS (
    SELECT *
    FROM {{ ref('silver_customers') }}
    WHERE dado_incompleto = FALSE
)

SELECT
    c.customer_state AS estado,
    ROUND(AVG(
        DATEDIFF('day',
            orders.order_purchase_timestamp,
            orders.order_delivered_customer_date)
    ), 1) AS tempo_medio_dias,
    COUNT(*) AS total_pedidos
FROM orders
INNER JOIN customers c
    ON orders.customer_id = c.customer_id
GROUP BY c.customer_state
ORDER BY tempo_medio_dias DESC