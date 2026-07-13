import pandas as pd
import time
import subprocess
import csv
import os
from datetime import datetime

# Caminhos
BASE_PATH = "/Users/felipe-caron/Documents/git-github/tcc-usp-lakehouse"
DATA_PATH = f"{BASE_PATH}/data"
METRICS_PATH = f"{BASE_PATH}/metrics"

def coletar_integridade():
    """Coleta métricas de integridade por tabela na camada silver."""
    resultados = []

    # Customers
    df = pd.read_parquet(f"{DATA_PATH}/silver/silver_customers.parquet")
    total = len(df)
    invalidos = df['dado_incompleto'].sum()
    resultados.append({
        'tabela': 'silver_customers',
        'total_registros': total,
        'registros_invalidos': int(invalidos),
        'percentual_invalidos': round(invalidos / total * 100, 2),
        'percentual_validos': round((total - invalidos) / total * 100, 2)
    })

    # Orders
    df = pd.read_parquet(f"{DATA_PATH}/silver/silver_orders.parquet")
    total = len(df)
    status_invalido = (~df['status_valido']).sum()
    entrega_inconsistente = df['entrega_inconsistente'].sum()
    invalidos = status_invalido + entrega_inconsistente
    resultados.append({
        'tabela': 'silver_orders',
        'total_registros': total,
        'registros_invalidos': int(invalidos),
        'percentual_invalidos': round(invalidos / total * 100, 2),
        'percentual_validos': round((total - invalidos) / total * 100, 2)
    })

    # Products
    df = pd.read_parquet(f"{DATA_PATH}/silver/silver_products.parquet")
    total = len(df)
    invalidos = df['dado_incompleto'].sum()
    resultados.append({
        'tabela': 'silver_products',
        'total_registros': total,
        'registros_invalidos': int(invalidos),
        'percentual_invalidos': round(invalidos / total * 100, 2),
        'percentual_validos': round((total - invalidos) / total * 100, 2)
    })

    # Sellers
    df = pd.read_parquet(f"{DATA_PATH}/silver/silver_sellers.parquet")
    total = len(df)
    invalidos = (~df['estado_valido']).sum()
    resultados.append({
        'tabela': 'silver_sellers',
        'total_registros': total,
        'registros_invalidos': int(invalidos),
        'percentual_invalidos': round(invalidos / total * 100, 2),
        'percentual_validos': round((total - invalidos) / total * 100, 2)
    })

    # Order Items
    df = pd.read_parquet(f"{DATA_PATH}/silver/silver_order_items.parquet")
    total = len(df)
    invalidos = df['pedido_orfao'].sum() + df['preco_invalido'].sum()
    resultados.append({
        'tabela': 'silver_order_items',
        'total_registros': total,
        'registros_invalidos': int(invalidos),
        'percentual_invalidos': round(invalidos / total * 100, 2),
        'percentual_validos': round((total - invalidos) / total * 100, 2)
    })

    return resultados


def coletar_escalabilidade(volumes=[10000, 50000, 100000]):
    """Mede tempo de processamento nos dois cenários para diferentes volumes."""
    resultados = []
    generator_script = f"{BASE_PATH}/generator/generator_data.py"
    before_script = f"{BASE_PATH}/before/analise_manual.py"

    for n in volumes:
        print(f"\nTestando volume: {n} pedidos...")

        # Ajusta o volume no gerador temporariamente
        with open(generator_script, 'r') as f:
            conteudo = f.read()
        conteudo_ajustado = conteudo.replace(
            'gerar_base(n_orders=10000)',
            f'gerar_base(n_orders={n})'
        )
        with open(generator_script, 'w') as f:
            f.write(conteudo_ajustado)

        # Gera os dados
        subprocess.run(['python', generator_script], capture_output=True)

        # Cenário A — mede tempo do script manual
        inicio_a = time.time()
        subprocess.run(['python', before_script], capture_output=True)
        tempo_a = round(time.time() - inicio_a, 2)

        # Cenário B — mede tempo do dbt
        inicio_b = time.time()
        subprocess.run([
            'dbt', 'run',
            '--project-dir', f"{BASE_PATH}/dbt_project/lakehouse",
            '--profiles-dir', f"{os.path.expanduser('~')}/.dbt",
            '--vars', f'{{"data_path": "{DATA_PATH}"}}'
        ], capture_output=True, cwd=f"{BASE_PATH}/dbt_project/lakehouse")
        tempo_b = round(time.time() - inicio_b, 2)

        resultados.append({
            'volume_pedidos': n,
            'tempo_cenario_a_segundos': tempo_a,
            'tempo_cenario_b_segundos': tempo_b,
            'diferenca_segundos': round(tempo_b - tempo_a, 2)
        })

        # Restaura o volume original
        conteudo_restaurado = conteudo_ajustado.replace(
            f'gerar_base(n_orders={n})',
            'gerar_base(n_orders=10000)'
        )
        with open(generator_script, 'w') as f:
            f.write(conteudo_restaurado)

    return resultados


def gerar_relatorio_kpis(integridade, escalabilidade):
    """Gera os arquivos CSV com os resultados."""
    os.makedirs(METRICS_PATH, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # CSV de integridade detalhado
    path_integridade = f"{METRICS_PATH}/kpis_integridade_detalhado.csv"
    with open(path_integridade, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=integridade[0].keys())
        writer.writeheader()
        writer.writerows(integridade)
    print(f"\nIntegridade salva em: {path_integridade}")

    # CSV de escalabilidade
    path_escalabilidade = f"{METRICS_PATH}/kpis_escalabilidade.csv"
    with open(path_escalabilidade, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=escalabilidade[0].keys())
        writer.writeheader()
        writer.writerows(escalabilidade)
    print(f"Escalabilidade salva em: {path_escalabilidade}")

    # CSV consolidado de KPIs
    total_registros = sum(r['total_registros'] for r in integridade)
    total_invalidos = sum(r['registros_invalidos'] for r in integridade)
    pct_validos = round((total_registros - total_invalidos) / total_registros * 100, 2)

    kpis_consolidado = [
        {
            'kpi': 'Velocidade',
            'dimensao': 'Tempo de execução (segundos)',
            'cenario_a': 0.39,
            'cenario_b': 6.29,
            'unidade': 'segundos',
            'observacao': 'Cenário A exige execução manual a cada análise; Cenário B é automatizado via Airflow'
        },
        {
            'kpi': 'Integridade',
            'dimensao': '% registros que passam em testes de qualidade',
            'cenario_a': 0.0,
            'cenario_b': pct_validos,
            'unidade': '%',
            'observacao': f'{total_invalidos} inconsistências detectadas e tratadas automaticamente na camada silver'
        },
        {
            'kpi': 'Governança',
            'dimensao': 'Testes automatizados implementados',
            'cenario_a': 0,
            'cenario_b': 51,
            'unidade': 'testes',
            'observacao': 'Cenário B possui 51 testes dbt + lineage via ref() + documentação via schema.yml'
        },
        {
            'kpi': 'Eficiência operacional',
            'dimensao': 'Passos manuais por execução',
            'cenario_a': 4,
            'cenario_b': 0,
            'unidade': 'passos',
            'observacao': 'Cenário B com schedule diário automático — zero intervenção humana necessária'
        },
    ]

    path_consolidado = f"{METRICS_PATH}/kpis_resultado.csv"
    with open(path_consolidado, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=kpis_consolidado[0].keys())
        writer.writeheader()
        writer.writerows(kpis_consolidado)
    print(f"KPIs consolidados salvos em: {path_consolidado}")


if __name__ == '__main__':
    print("=== Coletando KPIs ===")

    print("\n1. Coletando métricas de integridade...")
    integridade = coletar_integridade()
    for r in integridade:
        print(f"  {r['tabela']}: {r['percentual_validos']}% válidos ({r['registros_invalidos']} inconsistências)")

    print("\n2. Medindo escalabilidade (volumes: 10k, 50k, 100k)...")
    print("   Isso pode levar alguns minutos...")
    escalabilidade = coletar_escalabilidade()
    for r in escalabilidade:
        print(f"  {r['volume_pedidos']} pedidos — A: {r['tempo_cenario_a_segundos']}s | B: {r['tempo_cenario_b_segundos']}s")

    print("\n3. Gerando relatórios CSV...")
    gerar_relatorio_kpis(integridade, escalabilidade)

    print("\n=== Coleta concluída! ===")