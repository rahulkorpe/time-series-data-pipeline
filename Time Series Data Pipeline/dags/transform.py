import os
import re
import datetime
from numpy import float64
import pandas as pd
import influxdb_client
from dask import dataframe as df1
from influxdb_client.client.write_api import SYNCHRONOUS


def process_file(csv_file):
    print("Processing file:", csv_file)
    file_name = csv_file.split(".")[0]
    dask_df = df1.read_csv(str(csv_file))
    dask_df = dask_df.persist()

    # extract date from file name
    date_str = re.search(r"\d{8}", file_name).group()
    date_obj = datetime.datetime.strptime(date_str, "%Y%m%d")

    # Keep only 24h of records
    mask = dask_df["Time (s)"] <= 86400
    filter_df = dask_df[mask]

    # Convert second to hour-minute-second
    filter_df['Time (s)'] = filter_df['Time (s)'].apply(lambda x: str(datetime.timedelta(seconds=x)),
                                                        meta=('Time (s)', 'object'))

    # Concat file name with time, Time will be in this format ('%Y-%m-%d %H:%M:%S')
    filter_df['Time (s)'] = date_obj.strftime("%Y-%m-%d ") + filter_df['Time (s)']

    # Reformat Time to influxdb format('%Y-%m-%dT%H:%M:%SZ')
    meta = ('Time (s)', 'object')
    filter_df['Time (s)'] = filter_df['Time (s)'].astype(str).apply(lambda x: x.replace(' ', 'T') + 'Z', meta=meta)

    # Make Time as index
    filter_df = filter_df.set_index('Time (s)')

    # Make all columns in float type
    filter_df = filter_df.astype({'CO (ppm)': float64, 'Humidity (%r.h.)': float64, 'Temperature (C)': float64,
                                  'Flow rate (mL/min)': float64, 'Heater voltage (V)': float64, 'R1 (MOhm)': float64,
                                  'R2 (MOhm)': float64, 'R3 (MOhm)': float64, 'R4 (MOhm)': float64,
                                  'R5 (MOhm)': float64, 'R6 (MOhm)': float64, 'R7 (MOhm)': float64,
                                  'R8 (MOhm)': float64, 'R9 (MOhm)': float64, 'R10 (MOhm)': float64,
                                  'R11 (MOhm)': float64, 'R12 (MOhm)': float64, 'R13 (MOhm)': float64,
                                  'R14 (MOhm)': float64})

    # Convert Dask DataFrame to Pandas DataFrame
    pandas_df = filter_df.compute()

    print(pandas_df.head(5))

    # Serialize the DataFrame as an Apache Arrow binary file
    pandas_df.to_parquet(f'{file_name}.parquet')

    return f'{file_name}.parquet'


def send_file_influxdb(processed_file):
    # Deserialize the DataFrame from the Apache Arrow binary file
    df = pd.read_parquet(processed_file)
    print("Index of DataFrame: ", df.index)  # Print the index of the DataFrame

    tag_columns = ['Temperature']

    token_influxdb = 'J536G5RnRvJCSxLkJuEzRt-EhAAcukollYEOg74wz6y--XIucAqYC1jfpX_Jugl6yeB8FYctwVjefaDdpQE1LQ=='
    client = influxdb_client.InfluxDBClient(url='http://influxdb:8086', token=token_influxdb, org='my-org')

    # write the data into measurement
    write_api = client.write_api(write_options=SYNCHRONOUS, timeout=1000)

    message = write_api.write(bucket='gas-quality', org='my-org', record=df,
                              data_frame_measurement_name='gas', data_frame_tag_columns=tag_columns)
    print("Message: ", message)

    write_api.flush()

    # Delete the intermediate parquet file
    os.remove(processed_file)

    return True
