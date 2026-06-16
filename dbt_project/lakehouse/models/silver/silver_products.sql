{{ config(
    materialized='external',
    location='../../data/silver/silver_products.parquet'
) }}

WITH bronze AS (
    SELECT *
    FROM read_parquet('../../data/bronze/products.parquet')
),

tratado AS (
    SELECT
        product_id,
        product_name,
        COALESCE(product_category, 'Não identificado') AS product_category,
        product_weight_g,
        CASE
            WHEN product_category IS NULL THEN TRUE
            ELSE FALSE
        END AS dado_incompleto
    FROM bronze
)

SELECT *
FROM tratado