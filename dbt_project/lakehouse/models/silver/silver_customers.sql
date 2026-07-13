{{ config(
    materialized='external',
    location= var('data_path') + '/silver/silver_customers.parquet'
) }}

WITH bronze AS (
    SELECT *
    FROM read_parquet('{{ var("data_path") }}/bronze/customers.parquet')
),

deduplicado AS (
    SELECT DISTINCT *
    FROM bronze
),

tratado AS (
    SELECT
        customer_id,
        customer_name,
        customer_email,
        COALESCE(customer_city, 'Não identificado') AS customer_city,
        COALESCE(customer_state, 'Não identificado') AS customer_state,
        CASE
            WHEN customer_city IS NULL OR customer_state IS NULL THEN TRUE
            ELSE FALSE
        END AS dado_incompleto
    FROM deduplicado
)

SELECT *
FROM tratado