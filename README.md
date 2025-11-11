# SpartanControls-Interview

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

```text
+------------------+        +---------------------+        +----------------------+
|  Raspberry Pi (Edge) | --> |  AWS IoT Core (MQTT) | --> |  Kinesis Firehose → S3 |
|------------------|        |---------------------|        |----------------------|
| DHT11 Sensor      |        | Topics:              |        | GZIP JSON → Athena SQL |
| read_dht11.py     |        |  sensors/raw         |        +----------------------+
| models_and_processor.py → sensors/clean            |
+----------------------------------------------------+
                        ↓
                 +--------------------+
                 | Amazon Athena / S3 |
                 | Historical Queries |
                 +--------------------+
                        ↓
                 +--------------------+
                 | Live Plot (MQTT)   |
                 | plot_clean_simple_constants.py |
                 +--------------------+
