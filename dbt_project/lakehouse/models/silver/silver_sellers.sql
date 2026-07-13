{{ config(
    materialized='external',
    location= var('data_path') + '/silver/silver_sellers.parquet'
) }}

WITH bronze AS (
    SELECT *
    FROM read_parquet('{{ var("data_path") }}/bronze/sellers.parquet')
),

tratado AS (
    SELECT
        seller_id,
        seller_name,
        seller_city,
        seller_state AS seller_state_original,
        CASE
            WHEN seller_state IN (
                'AC','AL','AP','AM','BA','CE','DF','ES','GO',
                'MA','MT','MS','MG','PA','PB','PR','PE','PI',
                'RJ','RN','RS','RO','RR','SC','SP','SE','TO'
            ) THEN seller_state
            ELSE 'Não identificado'
        END AS seller_state,
        CASE
            WHEN seller_state IN (
                'AC','AL','AP','AM','BA','CE','DF','ES','GO',
                'MA','MT','MS','MG','PA','PB','PR','PE','PI',
                'RJ','RN','RS','RO','RR','SC','SP','SE','TO'
            ) THEN TRUE
            ELSE FALSE
        END AS estado_valido
    FROM bronze
)

SELECT *
FROM tratado