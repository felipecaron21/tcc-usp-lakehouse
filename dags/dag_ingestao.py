from airflow import DAG
from airflow.operators.bash import BashOperator
from datetime import datetime

GENERATOR_DIR = "/opt/tcc"

with DAG(
    dag_id="dag_ingestao",
    description="Ingestão: geração de dados sintéticos na camada bronze",
    start_date=datetime(2025, 1, 1),
    schedule=None,
    catchup=False,
    tags=["tcc", "lakehouse", "ingestao"],
) as dag:

    gerar_dados = BashOperator(
        task_id="gerar_dados_bronze",
        bash_command=f"cd {GENERATOR_DIR} && python generator/generate_data.py",
    )