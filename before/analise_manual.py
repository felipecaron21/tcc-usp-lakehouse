import pandas as pd
import time
import os

# Cronômetro início
inicio = time.time()

# -----------------------------------------------
# PASSO 1: Carregar os dados brutos manualmente
# -----------------------------------------------
print("Carregando dados...")

customers   = pd.read_parquet('data/bronze/customers.parquet')
orders      = pd.read_parquet('data/bronze/orders.parquet')
order_items = pd.read_parquet('data/bronze/order_items.parquet')
products    = pd.read_parquet('data/bronze/products.parquet')
sellers     = pd.read_parquet('data/bronze/sellers.parquet')

# -----------------------------------------------
# PASSO 2: Joins manuais sem nenhuma validação
# -----------------------------------------------
print("Fazendo joins...")

# Join orders com customers
df = orders.merge(customers, on='customer_id', how='left')

# Join com order_items
df = df.merge(order_items, on='order_id', how='left')

# Join com products
df = df.merge(products, on='product_id', how='left')

# Join com sellers
df = df.merge(sellers, on='seller_id', how='left')

# -----------------------------------------------
# PASSO 3: Análises direto nos dados brutos
# Sem tratamento de nulos, duplicatas ou defeitos
# -----------------------------------------------

print("\n--- ANÁLISE 1: Total de pedidos por status ---")
analise_1 = orders.groupby('order_status')['order_id'].count().reset_index()
analise_1.columns = ['status', 'total_pedidos']
print(analise_1.to_string(index=False))

print("\n--- ANÁLISE 2: Ticket médio por categoria de produto ---")
analise_2 = df.groupby('product_category')['price'].mean().reset_index()
analise_2.columns = ['categoria', 'ticket_medio']
analise_2['ticket_medio'] = analise_2['ticket_medio'].round(2)
print(analise_2.to_string(index=False))

print("\n--- ANÁLISE 3: Top 5 sellers por volume de vendas ---")
analise_3 = df.groupby('seller_name')['price'].sum().reset_index()
analise_3.columns = ['seller', 'volume_vendas']
analise_3 = analise_3.sort_values('volume_vendas', ascending=False).head(5)
print(analise_3.to_string(index=False))

print("\n--- ANÁLISE 4: Tempo médio de entrega por estado ---")
df_entrega = df[df['order_status'] == 'delivered'].copy()
df_entrega['order_purchase_timestamp'] = pd.to_datetime(
    df_entrega['order_purchase_timestamp']
)
df_entrega['order_delivered_customer_date'] = pd.to_datetime(
    df_entrega['order_delivered_customer_date']
)
df_entrega['tempo_entrega_dias'] = (
    df_entrega['order_delivered_customer_date'] -
    df_entrega['order_purchase_timestamp']
).dt.days

analise_4 = df_entrega.groupby('customer_state')['tempo_entrega_dias'].mean().reset_index()
analise_4.columns = ['estado', 'tempo_medio_dias']
analise_4['tempo_medio_dias'] = analise_4['tempo_medio_dias'].round(1)
print(analise_4.to_string(index=False))

# -----------------------------------------------
# PASSO 4: Cronômetro fim
# -----------------------------------------------
fim = time.time()
tempo_total = round(fim - inicio, 2)

print(f"\n Tempo total de execução: {tempo_total} segundos")
print(f" Passos manuais realizados: 4 (carregar, juntar, transformar, analisar)")
print(f" Testes de qualidade executados: 0")
print(f" Defeitos detectados: 0")
print(f" Documentação gerada: 0")