
# ⚙️ Industrial IoT Data Pipeline with AWS (Edge → Cloud → Analytics)

This project demonstrates a **secure, end-to-end Industrial IoT data pipeline**, inspired by real-world control-system integration tasks at **Spartan Controls**.  
It shows how edge devices (Raspberry Pi sensors) can stream field data to the cloud, where it is **validated, cleaned, stored, and visualized in real time** using AWS IoT Core, Kinesis Firehose, and Amazon Athena.

---

## 🧭 Motivation (for Spartan Controls)

Spartan Controls helps industrial clients connect control systems, historians, and field devices to the cloud for better insight and decision-making.  
This project mirrors that workflow at lab scale:

- **Edge acquisition** – like a PLC or RTU, a Raspberry Pi collects DHT11 process data (temperature / humidity).  
- **Data cleansing at the edge** – simulates preprocessing before uploading to a historian or cloud.  
- **Secure MQTT transport** – mirrors OPC UA / MQTT architectures used in modern control systems.  
- **Cloud ingestion (AWS IoT Core → Kinesis Firehose)** – shows how plant data flows securely into enterprise storage.  
- **Visualization & analytics** – real-time plotting and SQL analysis in Amazon Athena.

---

## 🧩 Architecture Overview
        ┌────────────────────┐
        │  DHT11 Sensor      │
        │ (Temperature, Hum) │
        └────────┬───────────┘
                 │
                 ▼
     ┌──────────────────────────────┐
     │ Raspberry Pi (Edge Device)   │
     │ - read_dht11.py              │
     │ - models_and_processor.py    │
     │ - edge_cleaner.py            │
     └────────┬─────────────────────┘
              │ MQTT (TLS, QoS1)
              ▼
     ┌──────────────────────────────┐
     │ AWS IoT Core (Message Broker)│
     │ Topics:                      │
     │ - sensors/raw                │
     │ - sensors/clean              │
     └────────┬─────────────────────┘
              │ IoT Rule → Firehose
              ▼
     ┌──────────────────────────────┐
     │ Kinesis Data Firehose        │
     │ Streams data into Amazon S3  │
     └────────┬─────────────────────┘
              ▼
     ┌──────────────────────────────┐
     │ Amazon S3                    │
     │ Stores gzipped sensor files  │
     │ (JSON/Parquet)               │
     └────────┬─────────────────────┘
              ▼
     ┌──────────────────────────────┐
     │ Amazon Athena                │
     │ SQL queries on sensor data   │
     └────────┬─────────────────────┘
              ▼
     ┌──────────────────────────────┐
     │ Laptop Visualization          │
     │ plot_clean_simple_constants.py│
     │ Real-time temperature & hum   │
     └──────────────────────────────┘

