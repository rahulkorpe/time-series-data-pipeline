from pathlib import Path
import psycopg2
from datetime import datetime, timedelta
from airflow import DAG
from transform import process_file, send_file_influxdb
from airflow.hooks.base_hook import BaseHook
from airflow.operators.python_operator import PythonOperator
from airflow.operators.dummy_operator import DummyOperator
from airflow.operators.python_operator import BranchPythonOperator
import re


def files_names():
    fs_conn = BaseHook.get_connection('fs_default')
    directory = Path(fs_conn.extra_dejson['path'])
    files = directory.glob('*.csv')
    files_list = [str(file) for file in files]  # Convert PosixPath objects to strings
    print("Files Found:", files_list)
    return files_list


def check_if_file_exists(file_path):
    # Extract file name from a file path
    file_name = Path(file_path).name

    # Connect to PostgreSQL database
    conn = psycopg2.connect(
        user="airflow",
        password="airflow",
        host="postgres",
        port="5432",
        database="GasData"
    )

    # Check if the file name already exists in table
    cur = conn.cursor()
    cur.execute("""SELECT COUNT(*) FROM gas_name WHERE file_name = %s""", (file_name,))
    count = cur.fetchone()[0]

    # Print the file name being checked
    print("Checking file:", file_name)

    if count > 0:
        cur.close()
        conn.close()
        print("File already exists in PostgreSQL:", file_name)
        return True  # File already exists, skip dummy_task
    else:
        # Insert the file name into the table
        cur.execute("""INSERT INTO gas_name (file_name) VALUES (%s)""", (file_name,))
        conn.commit()
        cur.close()
        conn.close()
        print("File inserted into PostgreSQL:", file_name)
        return False  # File does not exist, execute process_file_task


with DAG(
    dag_id='ETL-Gas',
    schedule_interval=None,
    start_date=datetime(2019, 4, 4),
    dagrun_timeout=timedelta(minutes=10),
) as dag:
    file_sensor_task = PythonOperator(
        task_id='file_sensor_task',
        python_callable=files_names,
        provide_context=True,
    )

    file_list = file_sensor_task.execute(context={})  # Execute file_sensor_task to get the file list

    for file_path in file_list:
        task_id = re.sub(r'[^a-zA-Z0-9-_.]', '_', str(file_path))

        check_existence_task = PythonOperator(
            task_id='check_existence_task_' + task_id,
            python_callable=check_if_file_exists,
            op_kwargs={'file_path': str(file_path)},
            provide_context=True,
        )

        process_file_task = PythonOperator(
            task_id='process_file_task_' + task_id,
            python_callable=process_file,
            op_kwargs={'csv_file': str(file_path)},  # Pass the file_path as 'csv_file' argument
            provide_context=True,
        )

        send_file_influxdb_task = PythonOperator(
            task_id='send_file_influxdb_task_' + task_id,
            python_callable=send_file_influxdb,
            op_kwargs={'processed_file': process_file_task.output},  # Pass the output of process_file_task
            provide_context=True,
        )

        dummy_task = DummyOperator(
            task_id='dummy_task_' + task_id
        )

        branching_task = BranchPythonOperator(
            task_id='branching_task_' + task_id,
            python_callable=lambda task_id=task_id, **kwargs: 'process_file_task_' + task_id if not kwargs[
                'ti'].xcom_pull(task_ids='check_existence_task_' + task_id) else 'dummy_task_' + task_id,
            provide_context=True,
        )

        file_sensor_task >> check_existence_task >> branching_task
        branching_task >> [process_file_task, dummy_task]
        process_file_task >> send_file_influxdb_task
