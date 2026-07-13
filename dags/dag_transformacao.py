from airflow import DAG
from airflow.operators.bash import BashOperator
from datetime import datetime

DBT_PROJECT_DIR = "/opt/tcc/dbt_project/lakehouse"
DBT_PROFILES_DIR = "/opt/tcc/dbt_project/lakehouse"

with DAG(
    dag_id="dag_transformacao",
    description="Transformação: modelos dbt silver e gold",
    start_date=datetime(2025, 1, 1),
    schedule=None,
    catchup=False,
    tags=["tcc", "lakehouse", "transformacao"],
) as dag:

    rodar_silver = BashOperator(
        task_id="rodar_modelos_silver",
        bash_command=(
            f"dbt run --select silver.* "
            f"--project-dir {DBT_PROJECT_DIR} "
            f"--profiles-dir {DBT_PROFILES_DIR}"
        ),
    )

    rodar_gold = BashOperator(
        task_id="rodar_modelos_gold",
        bash_command=(
            f"dbt run --select gold.* "
            f"--project-dir {DBT_PROJECT_DIR} "
            f"--profiles-dir {DBT_PROFILES_DIR}"
        ),
    )

    rodar_silver >> rodar_gold