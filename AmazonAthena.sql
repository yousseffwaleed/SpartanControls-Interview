-- Create Athena database
CREATE DATABASE IF NOT EXISTS iot_db;

-- Define external table for IoT data
CREATE EXTERNAL TABLE IF NOT EXISTS iot_db.sensors_v (
  device_id       string,
  ts_utc          timestamp,
  temperature_c   double,
  humidity_pct    double,
  year            string,
  month           string,
  day             string,
  hour            string
)
-- Tell Athena/Presto how to read JSON files (SerDe = serializer/deserializer)
ROW FORMAT SERDE 'org.openx.data.jsonserde.JsonSerDe'

-- Where the data files live in S3 (folder/prefix that contains your JSON/Parquet files)
-- Replace <YOUR_BUCKET> and the prefix to match your layout.
LOCATION 's3://<YOUR_BUCKET>/<YOUR_PREFIX>/'

-
-- Sample query: Get last 100 readings
SELECT * FROM iot_db.sensors_v ORDER BY ts_utc DESC LIMIT 100;
