
# Time Series Data Pipeline and Visualization for Gas Sensor Data Set

# Introduction & Goals

> This project demonstrates how to build a data pipeline for the Gas sensor array temperature modulation Data Set. 
The data set consists of measurements of 14 temperature-modulated metal oxide semiconductor (MOX) gas sensors exposed 
to dynamic mixtures of carbon monoxide (CO) and humid synthetic air. 
By analyzing the time series data from the sensors, researchers can develop models and algorithms to detect and estimate 
the gas (CO) concentration based on the sensor responses.
>
> To achieve this, the project uses Airflow, InfluxDB and Grafana as the main tools and technologies. 
Airflow is used to automate the extraction, transformation and loading **(ETL)** of the CSV files containing the sensor data. 
InfluxDB is used to store the processed time series data in an efficient way. 
Grafana is used to visualize the data and create interactive dashboards that show the sensor signals.
>
> The project demonstrates how to handle, process and visualize dynamic data using various tools and technologies. 
It also shows how to integrate and enrich the data by combining different files into a single database.


# Contents

- [The Data Set](#the-data-set)
- [Used Tools](#used-tools)
  - [Extract](#extract)
  - [Transform](#transform)
  - [Load](#load)
  - [Automation](#automation)
  - [Visualization](#visualization)
- [Setup](#setup)
- [Pipelines](#pipelines)
  - [Load Data](#load-data)
  - [Data Processing](#data-processing)
  - [Storing data in influxDB](#storing-data-in-influxdb)
  - [Visualizations](#visualizations)
- [Demo](#demo)
- [Conclusion](#conclusion)
- [Follow Me On](#follow-me-on)
- [Appendix](#appendix)


# The Data Set
- The dataset is presented in 13 CSV files, where each file corresponds to a different measurement day. The filenames indicate the timestamp (yyyymmdd_HHMMSS) of the start of the measurements.
Each file includes the acquired time series, presented in 20 columns: Time (s), CO concentration (ppm), Humidity (%r.h.), Temperature (ÂºC), Flow rate (mL/min), Heater voltage (V), and the resistance of the 14 gas sensors: R1 (MOhm),R2 (MOhm),R3 (MOhm),R4 (MOhm),R5 (MOhm),R6 (MOhm),R7 (MOhm),R8 (MOhm),R9 (MOhm),R10 (MOhm),R11 (MOhm),R12 (MOhm),R13 (MOhm),R14 (MOhm)
Resistance values R1-R7 correspond to FIGARO TGS 3870 A-04 sensors, whereas R8-R14 correspond to FIS SB-500-12 units.
The time series are sampled at 3.5 Hz.
- Data Source : https://archive.ics.uci.edu/ml/datasets/Gas+sensor+array+temperature+modulation
- Here is an overview of the dataset - 10 Columns:
![dataset](/photo/dataset.png)


# Used Tools
## Extract
- I used Python ingestion code in which I used the dask library to fast read large csv files
## Transform
- I used the same Python ingestion code with the dask library to handle and process the datasets
## Load
- I used Influxdb to store the sensor datasets
## Automation
- I used Apache Airflow to schedule, control tasks and do the ETL (Extract, Transform, Load) work
## Visualization
- I used the Grafana platform to visualize all the data from the gas sensors

# Setup
Since I have all services dockerized, please follow these steps to properly configure all 
the images and then deploy the containers:
- Clone the git repository, create a `Data_input` directory and put the Gas sensor csv files in there,
this way the code will remain unchanged
- Before diving into the deployment of docker-compose, I would like to clarify these points about docker-compose configuration: 

  1.  The `Data_input` folder needs to be mounted in the Airflow volumes so that it can work with the files there. 
      To do this, add this line to `volumes` in the docker-compose: `./Data_input:/usr/local/airflow/data_input`
  2.  To work with python libraries that need to be imported, Airflow allows us to import these libraries from 
      docker-compose into `environment`.
      To do this, add the Pandas, Dask and Influxdb-Client libraries to 
      `_PIP_ADDITIONAL_REQUIREMENTS`: `${_PIP_ADDITIONAL_REQUIREMENTS:- pandas dask influxdb-client}`

- As my folder is mounted and my extra libraries are added, all I need now is to start building docker container from my docker-compose. 
To do this go to the main project directory
and type: `docker-compose up -d`
- Go to `localhost:8081` on the web browser and connect to postgresql using this configuration: 
`System: PostgreSQL`, `Server: postgres:5432` , `Username: airflow`, `Password: airflow`

![server](/photo/server.png)

- Create a database called `GasData` and then a table called `gas_name` with a column called `file_name` of type `text`.
This table `gas_name` should contain the names of the csv files already processed

![table](/photo/table.png)

- Create the `fs_default` connection in Apache Airflow used to access files on the file system. 
To do this, go to `localhost:8080` on the web browser, go to the `Admin` tab in the Airflow UI, 
click on the `Connections` tab, click on the Create Connection button. In the Connection Name field, 
enter `fs_default`. In the Connection Type field, select `File (path)`. 
In Extra, enter `{"path": "/usr/local/airflow/data_input"}`. Click the Save button

![fs_default](/photo/fs_default.png)

- Finally, you need to configure InfluxDB to store the dataset. To do that : 
  1. Go to `localhost:8086` on the web browser and connect to InfluxDB using this configuration:`Username: my-user`, `Password: my-password`
  2. Create a `Bucket` called "**gas-quality**"
  3. Generate an `API token` to use in my **transform.py** code

![Bucket](/photo/Bucket.png)

![token](/photo/token.png)

# Pipelines


![pipline](/photo/pipeline.jpg)

The upcoming posts will consist of writing about:
+ Load data from csv files and see whether they have already been processed
+ Data processing
+ Storing data in the influxdb time series database
+ Visualisation of all gas sensors using a Grafana dashboard


## Load Data

I chose to design the pipeline as follows:

1- I first retrieve all the csv file names from the source directory. 

2- I check whether the csv file names already exist in the metadata base.
If the file name does not exist in the database, 
it will be inserted into the database and the file will be sent for processing.

On the other hand, if the file name already exists in my metadata base, 
then the file will not be reprocessed another time, the processing phase will be skipped, and a dummy task will run.

+ Here is an example where the name of the csv file already exists in my metadata base:
![skipped](/photo/skipped.png)
As you can see,when the name of the csv file already exists in the metadata base,processing is skipped
  and a dummy task is run.


+ Here is an example where the name of the csv file does not exist in my metadata base:
![process](/photo/process.png)

As you can see, when the name of the csv file does not exist in the metadata base, the file will be processed.

Detail of loading data: [loading](dags/ETL.py)

## Data Processing

Initially, all datasets were given a 25-hour recording over a period of 13 working days.
It is not clear from the documentation why this is a 25-hour record rather than a 24-hour record.

Therefore, to simplify the process, I will only take 24 hours per day (24 hours = 86400 seconds),
as the data is recorded in seconds.

The main goal of the process is to transform the time in the dataset
which is originally in seconds into the timestamp format used by influxdb `YYYY-MM-DDTHH:MM:SS.sssZ`. 

To do this, I extracted the day of recording from the name of the csv files (example:
if the name of the csv file is 20161007_210049.csv, the day of recording is 10/07/2016).
I concatenated the date with the time in the dataset after converting the seconds to HH:MM:SS.
The result is a timestamp 'YYYY-MM-DD HH:MM: SS.sss'
and the last step was to convert this timestamp into the format used by influxdb `YYY-MM-DDTHH:MM:SS.sssZ`.

I also chose
to work with the **Dask** library rather than Pandas
because Dask uses parallel processing to handle larger-than-memory datasets
and is better suited for distributed computing on larger datasets

Detail of the processing: [Processing](dags/transform.py)

## Storing data in influxDB

Originally, all the datasets were in the form of time series.
So I chose to store the data in InfluxDB rather than PostgreSQL
because InfluxDB is specifically designed to handle time series.
It uses a custom storage engine that is optimized for high ingest rates and fast query performance on time series data.
PostgreSQL, on the other hand,
is a general-purpose relational database
that does not necessarily offer the same level of performance optimization for time-series workloads.

The big challenge with airflow is sending data between tasks.
I have avoided
using the metadatabase to send the dataset from the processing task to the storage task
because the metadatabase is designed to store crucial information such as the configuration of the Airflow environment,
roles and permissions, etc ...
In addition, this database is limited in terms of size.

As I have designed the ETL pipeline
to work with several csv files at the same time and Airflow alone requires a lot of RAM,
saving the result of the processing task in an in-memory dataframe is a bad idea
because this way I will need a huge amount of RAM.

I have chosen
to save the result of the processing task in an intermediate parquet file which I will delete as soon
as influxDB has received all the data from this parquet file.

Finally, I need to go into InfluxDB, Buckets and make sure the data is there.

![influxdb-result](/photo/Influxdb-result.png)

Detail of storing data: [Storing](dags/transform.py)

## Visualizations

In this section, I'm going to explain how I created a dashboard using grafana.

Firstly, I need to connect to grafana,
I need to go into the web browser to `localhost:3000` and use `Username: admin` and `Password: pw12345`.

Next, I need to connect grafana to my influxDB database.
To do this, I need to go to `Connections` then `Data sources`, choose InfluxDB as the database,
then choose `Query Language: Flux`, `URL: http://influxdb:8086`.
In `Basic Auth Details` I need to provide the InfluxDB user and password: `User: my-user`, `Password: my-password`.


Finally, I need to provide the information required to connect to the InfluxDB Bucket:
`Organisation: my-org`, `Token: <xxxxxxxxxx>`, `Default Bucket: gas-quality`


![grafana-config](/photo/grafana-config.png)


Once I've established a connection between grafana and influxdb,
all I need to do is choose the date and create a graph using the **Flux** query language.
For example, to plot the **CO graph**, I need to use :

`|> filter(fn : (r) => r["_field"] == "CO (ppm)")` 


![voltage](/photo/voltage.png)


I also used a drop-down menu
to choose which resistors to display individually instead of putting all fourteen resistors in the same graph.

To do this, in the dashboard menu, I went to `Settings` then `Variables`,
chose the name `Resistors` as `Custom` and for the value I put the column name `R1 (MOhm), ..., R14 (MOhm)` as follows:


![variable](/photo/variable.png)


To use this variable in my Flux query, I need to use 
`|> filter(fn : (r) => r["_field"] == "${Resistances}")` as follows: 


![use-variable](/photo/use-variable.png)


Here's what the end result of the dashboard looks like:

![grafana-result](/photo/grafana-result.png)

# Demo

+ Here's an example of how the ETL pipeline works. 
I have a csv file **20161005_140846** which has already been processed,
  and I add the following csv files to the mounted folder: **20161006_182224.csv** and **20161007_210049.csv**.
The two new csv files will be processed, but the processing of the oldest csv file will be skipped


![ETL](/photo/ETL.gif)


# Conclusion

I carried out this project using a number of services, from ingestion to visualization.

The most difficult part was mounting the folder containing the csv files in the docker-compose
and then using it in the connection path of the airflow user interface,
to finally have the ability to work with multiple files in the extraction task. 

In addition, I chose to work with branch python operator
and to save the names of the csv files in a table in the metadata base
in order to avoid reprocessing any csv file that had already been processed and its data sent to influxdb.

Very importantly,
make sure to allocate at least **6 GB** of RAM to Docker Desktop
in case of working with multiple files at the same time.
Otherwise, to be on the safe side, work with only one file, or you faced with
`Task received SIGTERM signal and terminated` (The **SIGTERM** related error,
it usually indicates that the task or process is exceeding the available memory resources) 

Overall, I found this to be an exciting project to explore

# Follow Me On
+ Github: [@AdnenMess](https://github.com/AdnenMess)
+ LinkedIn: [@messaoudi-adnen](https://www.linkedin.com/in/messaoudi-adnen-8a513815/)

# Appendix

[Markdown Cheat Sheet](https://github.com/adam-p/markdown-here/wiki/Markdown-Cheatsheet)
