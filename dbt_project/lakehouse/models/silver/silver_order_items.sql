{{ config(
    materialized='external',
    location='../../data/silver/silver_order_items.parquet'
) }}

WITH bronze AS (
    SELECT *
    FROM read_parquet('../../data/bronze/order_items.parquet')
),

orders_validos AS (
    SELECT order_id
    FROM {{ ref('silver_orders') }}
),

tratado AS (
    SELECT
        b.order_item_id,
        b.order_id,
        CASE
            WHEN o.order_id IS NULL THEN TRUE
            ELSE FALSE
        END AS pedido_orfao,
        b.product_id,
        b.seller_id,
        b.price AS price_original,
        CASE
            WHEN b.price <= 0 THEN NULL
            ELSE b.price
        END AS price,
        CASE
            WHEN b.price <= 0 THEN TRUE
            ELSE FALSE
        END AS preco_invalido,
        b.freight_value
    FROM bronze b
    LEFT JOIN orders_validos o
        ON b.order_id = o.order_id
)

SELECT *
FROM tratado