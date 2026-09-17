"""
Coleta de KPIs do experimento Lakehouse com múltiplas rodagens.

- Tempos (Cenário A, Cenário B e escalabilidade): 10 rodagens cada, para
  construir distribuição e estatísticas (média, desvio, mín, máx, mediana).
- Integridade: coletada uma vez (determinística, seed fixa).
- Governança e eficiência: valores fixos.

Gera dois CSVs por bloco: um bruto (todas as rodadas) e um resumo (estatísticas).
Ao final, restaura a base no volume padrão (10k).
"""

import pandas as pd
import numpy as np
import time
import subprocess
import os
import re

# ------------------------------------------------------------------
# Configuração
# ------------------------------------------------------------------
BASE_PATH = "/Users/felipe-caron/Documents/git-github/tcc-usp-lakehouse"
DATA_PATH = f"{BASE_PATH}/data"
METRICS_PATH = f"{BASE_PATH}/metrics"
DBT_DIR = f"{BASE_PATH}/dbt_project/lakehouse"
PROFILES_DIR = os.path.expanduser("~/.dbt")
GENERATOR = f"{BASE_PATH}/generator/generator_data.py"
CENARIO_A = f"{BASE_PATH}/before/analise_manual.py"

VARS = f'{{"data_path": "{DATA_PATH}"}}'
N_RODADAS = 10
VOLUME_PADRAO = 10000
VOLUMES_ESCALA = [10000, 50000, 100000]

os.makedirs(METRICS_PATH, exist_ok=True)


# ------------------------------------------------------------------
# Utilidades de execução
# ------------------------------------------------------------------
def cronometrar(func):
    """Executa func e devolve o tempo em segundos (perf_counter)."""
    inicio = time.perf_counter()
    func()
    return round(time.perf_counter() - inicio, 4)


def rodar_gerador(n_orders):
    """Regenera a base com o volume informado, ajustando a chamada no gerador."""
    with open(GENERATOR, "r") as f:
        conteudo = f.read()
    novo = re.sub(r"gerar_base\(n_orders=\d+\)",
                  f"gerar_base(n_orders={n_orders})", conteudo)
    with open(GENERATOR, "w") as f:
        f.write(novo)
    subprocess.run(["python", GENERATOR], capture_output=True, cwd=BASE_PATH)


def rodar_cenario_a():
    subprocess.run(["python", CENARIO_A], capture_output=True, cwd=BASE_PATH)


def rodar_cenario_b():
    """Replica a dag_transformacao: dbt run silver + gold, depois dbt test."""
    subprocess.run(["dbt", "run", "--select", "silver", "--project-dir", DBT_DIR,
                    "--profiles-dir", PROFILES_DIR, "--vars", VARS],
                   capture_output=True, cwd=DBT_DIR)
    subprocess.run(["dbt", "run", "--select", "gold", "--project-dir", DBT_DIR,
                    "--profiles-dir", PROFILES_DIR, "--vars", VARS],
                   capture_output=True, cwd=DBT_DIR)
    subprocess.run(["dbt", "test", "--project-dir", DBT_DIR,
                    "--profiles-dir", PROFILES_DIR, "--vars", VARS],
                   capture_output=True, cwd=DBT_DIR)


def estatisticas(valores):
    arr = np.array(valores)
    return {
        "media": round(arr.mean(), 4),
        "desvio_padrao": round(arr.std(ddof=1), 4),
        "minimo": round(arr.min(), 4),
        "maximo": round(arr.max(), 4),
        "mediana": round(np.median(arr), 4),
    }


# ------------------------------------------------------------------
# 1. Tempos principais (Cenário A e Cenário B) — 10 rodagens em 10k
# ------------------------------------------------------------------
def medir_tempos_principais():
    print("\n=== 1. Tempos principais (10 rodagens, volume 10k) ===")
    print("Regenerando base padrão (10k) antes de iniciar...")
    rodar_gerador(VOLUME_PADRAO)

    linhas_brutas = []
    tempos_a, tempos_b = [], []

    for i in range(1, N_RODADAS + 1):
        t_a = cronometrar(rodar_cenario_a)
        t_b = cronometrar(rodar_cenario_b)
        tempos_a.append(t_a)
        tempos_b.append(t_b)
        linhas_brutas.append({"rodada": i, "cenario_a_s": t_a, "cenario_b_s": t_b})
        print(f"  Rodada {i:2d}: A={t_a:.4f}s | B={t_b:.4f}s")

    pd.DataFrame(linhas_brutas).to_csv(
        f"{METRICS_PATH}/tempos_bruto.csv", index=False)

    est_a = estatisticas(tempos_a)
    est_b = estatisticas(tempos_b)
    resumo = pd.DataFrame([
        {"cenario": "A (manual)", **est_a},
        {"cenario": "B (transformacao)", **est_b},
    ])
    resumo.to_csv(f"{METRICS_PATH}/tempos_resumo.csv", index=False)
    print("\nResumo dos tempos:")
    print(resumo.to_string(index=False))
    return est_a, est_b


# ------------------------------------------------------------------
# 2. Escalabilidade — 10 rodagens por volume
# ------------------------------------------------------------------
def medir_escalabilidade():
    print("\n=== 2. Escalabilidade (10 rodagens por volume) ===")
    linhas_brutas = []
    resumo = []

    for vol in VOLUMES_ESCALA:
        print(f"\n  Volume: {vol} pedidos")
        tempos_a, tempos_b = [], []
        for i in range(1, N_RODADAS + 1):
            rodar_gerador(vol)          # regenera a base nesse volume
            t_a = cronometrar(rodar_cenario_a)
            t_b = cronometrar(rodar_cenario_b)
            tempos_a.append(t_a)
            tempos_b.append(t_b)
            linhas_brutas.append({
                "volume": vol, "rodada": i,
                "cenario_a_s": t_a, "cenario_b_s": t_b})
            print(f"    Rodada {i:2d}: A={t_a:.4f}s | B={t_b:.4f}s")

        est_a = estatisticas(tempos_a)
        est_b = estatisticas(tempos_b)
        resumo.append({"volume": vol, "cenario": "A", **est_a})
        resumo.append({"volume": vol, "cenario": "B", **est_b})

    pd.DataFrame(linhas_brutas).to_csv(
        f"{METRICS_PATH}/escalabilidade_bruto.csv", index=False)
    pd.DataFrame(resumo).to_csv(
        f"{METRICS_PATH}/escalabilidade_resumo.csv", index=False)
    print("\nResumo da escalabilidade:")
    print(pd.DataFrame(resumo).to_string(index=False))
    return resumo


# ------------------------------------------------------------------
# 3. Integridade — coleta única (determinística)
# ------------------------------------------------------------------
def coletar_integridade():
    print("\n=== 3. Integridade (coleta única, base 10k) ===")
    print("Restaurando base padrão (10k) e rodando pipeline...")
    rodar_gerador(VOLUME_PADRAO)
    rodar_cenario_b()   # garante silver/gold atualizados em 10k

    s = f"{DATA_PATH}/silver"
    defs = [
        ("silver_customers", lambda df: df["dado_incompleto"].sum()),
        ("silver_orders", lambda df: (~df["status_valido"]).sum() + df["entrega_inconsistente"].sum()),
        ("silver_products", lambda df: df["dado_incompleto"].sum()),
        ("silver_sellers", lambda df: (~df["estado_valido"]).sum()),
        ("silver_order_items", lambda df: df["pedido_orfao"].sum() + df["preco_invalido"].sum()),
    ]
    linhas, tot, tot_inv = [], 0, 0
    for nome, regra in defs:
        df = pd.read_parquet(f"{s}/{nome}.parquet")
        n = len(df)
        inval = int(regra(df))
        tot += n
        tot_inv += inval
        linhas.append({
            "tabela": nome, "total_registros": n,
            "registros_invalidos": inval,
            "percentual_invalidos": round(inval / n * 100, 2),
            "percentual_validos": round((n - inval) / n * 100, 2),
        })
        print(f"  {nome}: {n} registros, {inval} inconsistências")

    linhas.append({
        "tabela": "TOTAL", "total_registros": tot,
        "registros_invalidos": tot_inv,
        "percentual_invalidos": round(tot_inv / tot * 100, 2),
        "percentual_validos": round((tot - tot_inv) / tot * 100, 2),
    })
    pd.DataFrame(linhas).to_csv(
        f"{METRICS_PATH}/integridade.csv", index=False)
    print(f"\n  TOTAL: {tot} registros, {tot_inv} inconsistências "
          f"({round((tot - tot_inv) / tot * 100, 2)}% válidos)")
    return linhas


# ------------------------------------------------------------------
# 4. Consolidado geral — base consultiva com todos os KPIs
# ------------------------------------------------------------------
def gerar_consolidado(est_a, est_b, escala, integridade):
    """Monta um CSV único com todos os KPIs, a partir dos valores medidos."""
    print("\n=== 4. Consolidando todos os KPIs ===")

    total = next(r for r in integridade if r["tabela"] == "TOTAL")
    linhas = []

    # --- Velocidade (média das 10 rodagens, volume 10k) ---
    linhas.append({
        "indicador": "Velocidade",
        "dimensao": "Tempo de processamento (s), média de 10 rodagens em 10k",
        "cenario_a": est_a["media"],
        "cenario_b": est_b["media"],
        "unidade": "segundos",
        "observacao": (f"A: dp={est_a['desvio_padrao']}, min={est_a['minimo']}, "
                       f"max={est_a['maximo']}, mediana={est_a['mediana']} | "
                       f"B: dp={est_b['desvio_padrao']}, min={est_b['minimo']}, "
                       f"max={est_b['maximo']}, mediana={est_b['mediana']} | "
                       f"B inclui dbt run (silver+gold) e dbt test")
    })

    # --- Integridade ---
    linhas.append({
        "indicador": "Integridade",
        "dimensao": "% de registros válidos após processamento",
        "cenario_a": 0.0,
        "cenario_b": total["percentual_validos"],
        "unidade": "%",
        "observacao": (f"{total['registros_invalidos']} inconsistências detectadas "
                       f"e tratadas em {total['total_registros']} registros; "
                       f"Cenário A não detecta inconsistências")
    })

    # --- Governança ---
    linhas.append({
        "indicador": "Governança",
        "dimensao": "Testes automatizados implementados",
        "cenario_a": 0,
        "cenario_b": 51,
        "unidade": "testes",
        "observacao": ("Cenário B: 51 testes dbt (not_null, unique, accepted_values) "
                       "+ lineage via ref() + documentação via schema.yml")
    })

    # --- Eficiência operacional ---
    linhas.append({
        "indicador": "Eficiência operacional",
        "dimensao": "Etapas manuais por execução",
        "cenario_a": 4,
        "cenario_b": 0,
        "unidade": "etapas",
        "observacao": ("A: carregar, cruzar, analisar, compilar | "
                       "B: orquestração agendada, sem intervenção manual")
    })

    # --- Escalabilidade (uma linha por volume, média de B) ---
    for vol in VOLUMES_ESCALA:
        b = next(r for r in escala if r["volume"] == vol and r["cenario"] == "B")
        a = next(r for r in escala if r["volume"] == vol and r["cenario"] == "A")
        linhas.append({
            "indicador": "Escalabilidade",
            "dimensao": f"Tempo médio (s) em {vol} pedidos, 10 rodagens",
            "cenario_a": a["media"],
            "cenario_b": b["media"],
            "unidade": "segundos",
            "observacao": (f"A: dp={a['desvio_padrao']} | B: dp={b['desvio_padrao']}")
        })

    pd.DataFrame(linhas).to_csv(f"{METRICS_PATH}/kpis_consolidado.csv", index=False)
    print("Consolidado salvo em: kpis_consolidado.csv")
    print(pd.DataFrame(linhas).to_string(index=False))


# ------------------------------------------------------------------
# Execução
# ------------------------------------------------------------------
if __name__ == "__main__":
    print("Início da coleta de KPIs com múltiplas rodagens.")
    print("Isso pode levar vários minutos, especialmente na escalabilidade.\n")

    est_a, est_b = medir_tempos_principais()
    escala = medir_escalabilidade()
    integridade = coletar_integridade()   # também restaura a base em 10k ao final
    gerar_consolidado(est_a, est_b, escala, integridade)

    print("\n=== Coleta concluída ===")
    print("Arquivos gerados em metrics/:")
    print("  tempos_bruto.csv / tempos_resumo.csv")
    print("  escalabilidade_bruto.csv / escalabilidade_resumo.csv")
    print("  integridade.csv")
    print("  kpis_consolidado.csv  (base consultiva com todos os KPIs)")
    print("\nA base foi restaurada no volume padrão (10.000 pedidos).")