{{ config(
    materialized='external',
    location='../../data/silver/silver_orders.parquet'
) }}

WITH bronze AS (
    SELECT *
    FROM read_parquet('../../data/bronze/orders.parquet')
),

tratado AS (
    SELECT
        order_id,
        customer_id,
        order_status AS order_status_original,
        CASE
            WHEN order_status IN ('delivered', 'shipped', 'canceled', 'processing')
                THEN order_status
            ELSE 'Não identificado'
        END AS order_status,
        CASE
            WHEN order_status IN ('delivered', 'shipped', 'canceled', 'processing')
                THEN TRUE
            ELSE FALSE
        END AS status_valido,
        order_purchase_timestamp,
        order_delivered_customer_date,
        CASE
            WHEN order_status = 'delivered'
                 AND order_delivered_customer_date IS NULL
                THEN TRUE
            ELSE FALSE
        END AS entrega_inconsistente
    FROM bronze
)

SELECT *
FROM tratado