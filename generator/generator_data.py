import pandas as pd
from faker import Faker
import random
import os

# Configurações
fake = Faker('pt_BR')
random.seed(42)
Faker.seed(42)

# Pasta de destino
OUTPUT_PATH = 'data/bronze'

def gerar_customers(n):
    customers = []
    nulos = 0
    for i in range(n):
        # Planta defeito: 5% com cidade e estado nulos
        if random.random() < 0.05:
            cidade = None
            estado = None
            nulos += 1
        else:
            cidade = fake.city()
            estado = fake.state_abbr()

        customers.append({
            'customer_id': fake.uuid4(),
            'customer_name': fake.name(),
            'customer_email': fake.email(),
            'customer_city': cidade,
            'customer_state': estado,
        })

    # Planta defeito: 3% de duplicatas
    total_duplicatas = int(n * 0.03)
    duplicatas = random.choices(customers, k=total_duplicatas)
    customers.extend(duplicatas)

    return pd.DataFrame(customers), {'nulos_geograficos': nulos, 'duplicatas': total_duplicatas}


def gerar_products(n):
    categorias_validas = [
        'eletronicos', 'moveis', 'roupas', 'esportes', 'brinquedos'
    ]
    products = []
    nulos = 0
    for i in range(n):
        # Planta defeito: 6% com categoria nula
        if random.random() < 0.06:
            categoria = None
            nulos += 1
        else:
            categoria = random.choice(categorias_validas)

        products.append({
            'product_id': fake.uuid4(),
            'product_name': fake.word(),
            'product_category': categoria,
            'product_weight_g': random.randint(100, 5000),
        })

    return pd.DataFrame(products), {'categorias_nulas': nulos}


def gerar_sellers(n):
    estados_validos = [
        'SP', 'RJ', 'MG', 'RS', 'PR', 'SC', 'BA', 'CE'
    ]
    estados_invalidos = ['XX', 'ZZ', 'QQ']

    sellers = []
    estados_inv = 0
    for i in range(n):
        # Planta defeito: 3% com estado inválido
        if random.random() < 0.03:
            estado = random.choice(estados_invalidos)
            estados_inv += 1
        else:
            estado = random.choice(estados_validos)

        sellers.append({
            'seller_id': fake.uuid4(),
            'seller_name': fake.company(),
            'seller_city': fake.city(),
            'seller_state': estado,
        })

    return pd.DataFrame(sellers), {'estados_invalidos': estados_inv}


def gerar_orders(n, customer_ids):
    status_validos = [
        'delivered', 'shipped', 'canceled', 'processing'
    ]
    status_invalidos = ['unknown', 'error']

    orders = []
    status_inv = 0
    entrega_sem_data = 0
    for i in range(n):
        status = random.choice(status_validos)

        # Planta defeito: 2% com status inválido
        if random.random() < 0.02:
            status = random.choice(status_invalidos)
            status_inv += 1

        data_compra = fake.date_time_between(
            start_date='-1y', end_date='now'
        )

        # Planta defeito: 4% de pedidos "delivered" sem data de entrega
        if status == 'delivered' and random.random() < 0.04:
            data_entrega = None
            entrega_sem_data += 1
        elif status == 'delivered':
            data_entrega = fake.date_time_between(
                start_date=data_compra, end_date='now'
            )
        else:
            data_entrega = None

        orders.append({
            'order_id': fake.uuid4(),
            'customer_id': random.choice(customer_ids),
            'order_status': status,
            'order_purchase_timestamp': data_compra,
            'order_delivered_customer_date': data_entrega,
        })

    return pd.DataFrame(orders), {'status_invalidos': status_inv, 'entrega_sem_data': entrega_sem_data}


def gerar_order_items(n, order_ids, product_ids, seller_ids):
    # Planta defeito: 3% de order_ids órfãos
    ids_falsos = [fake.uuid4() for _ in range(int(n * 0.03))]

    items = []
    precos_invalidos = 0
    orfaos = 0
    for i in range(n):
        # Planta defeito: preço negativo ou zero em 2%
        if random.random() < 0.02:
            preco = random.choice([0, -10, -50])
            precos_invalidos += 1
        else:
            preco = round(random.uniform(10, 500), 2)

        # Usa order_id órfão em 3% dos casos
        if random.random() < 0.03:
            order_id = random.choice(ids_falsos)
            orfaos += 1
        else:
            order_id = random.choice(order_ids)

        items.append({
            'order_item_id': fake.uuid4(),
            'order_id': order_id,
            'product_id': random.choice(product_ids),
            'seller_id': random.choice(seller_ids),
            'price': preco,
            'freight_value': round(random.uniform(5, 50), 2),
        })

    return pd.DataFrame(items), {'precos_invalidos': precos_invalidos, 'orfaos': orfaos}


def gerar_base(n_orders):
    print(f'Gerando base com {n_orders} pedidos...')

    n_customers = int(n_orders * 0.8)
    n_products = int(n_orders * 0.3)
    n_sellers = int(n_orders * 0.1)
    n_items = int(n_orders * 1.5)

    df_customers, def_customers = gerar_customers(n_customers)
    df_products, def_products = gerar_products(n_products)
    df_sellers, def_sellers = gerar_sellers(n_sellers)
    df_orders, def_orders = gerar_orders(
        n_orders,
        df_customers['customer_id'].tolist()
    )
    df_order_items, def_items = gerar_order_items(
        n_items,
        df_orders['order_id'].tolist(),
        df_products['product_id'].tolist(),
        df_sellers['seller_id'].tolist()
    )

    os.makedirs(OUTPUT_PATH, exist_ok=True)

    df_customers.to_parquet(f'{OUTPUT_PATH}/customers.parquet', index=False)
    df_products.to_parquet(f'{OUTPUT_PATH}/products.parquet', index=False)
    df_sellers.to_parquet(f'{OUTPUT_PATH}/sellers.parquet', index=False)
    df_orders.to_parquet(f'{OUTPUT_PATH}/orders.parquet', index=False)
    df_order_items.to_parquet(f'{OUTPUT_PATH}/order_items.parquet', index=False)

    print('\nBase gerada com sucesso!')
    print(f'  customers:   {len(df_customers)} registros')
    print(f'  products:    {len(df_products)} registros')
    print(f'  sellers:     {len(df_sellers)} registros')
    print(f'  orders:      {len(df_orders)} registros')
    print(f'  order_items: {len(df_order_items)} registros')

    # Report de defeitos inseridos
    total_defeitos = (
        def_customers['nulos_geograficos'] +
        def_customers['duplicatas'] +
        def_products['categorias_nulas'] +
        def_sellers['estados_invalidos'] +
        def_orders['status_invalidos'] +
        def_orders['entrega_sem_data'] +
        def_items['precos_invalidos'] +
        def_items['orfaos']
    )

    print('\n--- RELATÓRIO DE DEFEITOS INSERIDOS ---')
    print(f'  customers   | nulos geográficos:        {def_customers["nulos_geograficos"]:>6} '
          f'({def_customers["nulos_geograficos"]/n_customers*100:.2f}%)')
    print(f'  customers   | duplicatas:               {def_customers["duplicatas"]:>6} '
          f'({def_customers["duplicatas"]/n_customers*100:.2f}%)')
    print(f'  products    | categorias nulas:         {def_products["categorias_nulas"]:>6} '
          f'({def_products["categorias_nulas"]/n_products*100:.2f}%)')
    print(f'  sellers     | estados inválidos:        {def_sellers["estados_invalidos"]:>6} '
          f'({def_sellers["estados_invalidos"]/n_sellers*100:.2f}%)')
    print(f'  orders      | status inválidos:         {def_orders["status_invalidos"]:>6} '
          f'({def_orders["status_invalidos"]/n_orders*100:.2f}%)')
    print(f'  orders      | entrega sem data:         {def_orders["entrega_sem_data"]:>6} '
          f'({def_orders["entrega_sem_data"]/n_orders*100:.2f}%)')
    print(f'  order_items | preços inválidos:         {def_items["precos_invalidos"]:>6} '
          f'({def_items["precos_invalidos"]/n_items*100:.2f}%)')
    print(f'  order_items | itens órfãos:             {def_items["orfaos"]:>6} '
          f'({def_items["orfaos"]/n_items*100:.2f}%)')
    print(f'  TOTAL defeitos inseridos:              {total_defeitos:>6}')
    print('---------------------------------------')


if __name__ == '__main__':
    gerar_base(n_orders=10000)