{{ config(
    materialized='external',
    location= var('data_path') + '/gold/gold_top_sellers.parquet'
) }}

WITH order_items AS (
    SELECT *
    FROM {{ ref('silver_order_items') }}
    WHERE pedido_orfao = FALSE
    AND preco_invalido = FALSE
),

sellers AS (
    SELECT *
    FROM {{ ref('silver_sellers') }}
    WHERE estado_valido = TRUE
)

SELECT
    s.seller_name,
    ROUND(SUM(oi.price), 2) AS volume_vendas,
    COUNT(*) AS total_itens
FROM order_items oi
INNER JOIN sellers s
    ON oi.seller_id = s.seller_id
GROUP BY s.seller_name
ORDER BY volume_vendas DESC
LIMIT 5