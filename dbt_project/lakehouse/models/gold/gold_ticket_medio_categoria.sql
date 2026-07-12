{{ config(
    materialized='external',
    location='../../data/gold/gold_ticket_medio_categoria.parquet'
) }}

WITH order_items AS (
    SELECT *
    FROM {{ ref('silver_order_items') }}
    WHERE pedido_orfao = FALSE
    AND preco_invalido = FALSE
),

products AS (
    SELECT *
    FROM {{ ref('silver_products') }}
)

SELECT
    p.product_category AS categoria,
    ROUND(AVG(oi.price), 2) AS ticket_medio,
    COUNT(*) AS total_itens
FROM order_items oi
INNER JOIN products p
    ON oi.product_id = p.product_id
GROUP BY p.product_category
ORDER BY ticket_medio DESC