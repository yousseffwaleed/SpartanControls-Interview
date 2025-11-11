"""
publisher_dht11_to_aws_iot.py
--------------------------------
Reads temperature and humidity from a DHT11 sensor on a Raspberry Pi
and publishes the raw JSON data to AWS IoT Core over MQTT (mutual TLS).

👉 This script generates the **RAW sensor stream** on topic `sensors/raw`.
That raw stream is then subscribed to by another edge-processing script
(which cleans, validates, and enriches the data before republishing it to
`sensors/clean` for visualization and analytics).

REPLACE the ALL-CAPS placeholders below before running.
"""
# =============================================================================

# All libraries needed are imported here.
# 0) Libraries
# =============================================================================

from awscrt.io import ClientBootstrap


from awscrt.io import ClientBootstrap


import time
import json
import board
import adafruit_dht
from awscrt import io, mqtt
from awsiot import mqtt_connection_builder

# =============================================================================
# 1) CONFIGURATION (REPLACE THESE VALUES)
# =============================================================================
# ===========================
# AWS IoT / MQTT CONFIG
# Replace ALL placeholders before running
# Make sure you fill them all before running!
# ===========================
ENDPOINT     = "<YOUR_AWS_IOT_ENDPOINT>"   # e.g. "a1xxxx-ats.iot.us-east-1.amazonaws.com"
                                            # Find it in AWS IoT Core → Security → Certificate → Certificate ARN
CLIENT_ID    = "<UNIQUE_CLIENT_ID>"        # e.g. "rpi-sensor-001" — name of THIS MQTT connection; must be unique
PATH_TO_CERT = "<PATH_TO_DEVICE_CERT.crt>" # e.g. "/home/pi/certs/deviceCert.crt" — device X.509 certificate
                                            # these files are provided to you in the intial steps in creating your AWS IoT core
PATH_TO_KEY  = "<PATH_TO_PRIVATE_KEY.key>" # e.g. "/home/pi/certs/privateKey.key" — matching private key (keep secret), Never share with anyone!
PATH_TO_ROOT = "<PATH_TO_ROOT_CA.pem>"     # e.g. "/home/pi/certs/AmazonRootCA1.pem" — Amazon Root CA
TOPIC        = "<RAW_TOPIC>"               # e.g. "sensors/raw" — where this script publishes raw readings

# Network path: use 443 for HTTPS
USE_PORT_443_ALPN = True   #To ensure data is encrypted and protected through TLS Certificate.

# =============================================================================

# DHT11 setup (GPIO4 = board.D4)
dht = adafruit_dht.DHT11(board.D4)  # Initialize DHT11 sensor on GPIO4 (Pin 7)
READ_PERIOD_SEC = 2                # Wait 2 seconds between each DHT11 reading

# MQTT setup
elg = io.EventLoopGroup(1) # One background thread to handle all MQTT/TLS networking
hr = io.DefaultHostResolver(elg)  # DNS resolver to turn the AWS endpoint hostname into an IP
cb  = io.ClientBootstrap(elg, hr) # Bootstrap = uses our event threat + DNS for MQTT/TLS

conn_kwargs = dict[str, str | ClientBootstrap | bool | int]  (
    endpoint=ENDPOINT,                 
    cert_filepath=PATH_TO_CERT,        
    pri_key_filepath=PATH_TO_KEY,      
    ca_filepath=PATH_TO_ROOT,         
    client_bootstrap=cb,               
    client_id=CLIENT_ID,               
    clean_session=True,                # Start a fresh MQTT session each connect
    keep_alive_secs=30,                # MQTT keepalive ping interval 
)



conn = mqtt_connection_builder.mtls_from_path(**conn_kwargs) # Builds a connection with TLS Certificates provided

print("Connecting to AWS IoT…")
conn.connect().result()
print(f"Connected. Publishing DHT11 data to topic: {TOPIC}")

# Main loop for data collection
try:
    while True:
        try:
            temp_c = dht.temperature #Temp Data
            hum = dht.humidity       #Humidity Data
            if temp_c is None or hum is None:
                time.sleep(READ_PERIOD_SEC)
                continue

            msg = {
                "device_id": CLIENT_ID,
                "ts": int(time.time()),    
                "temperature": float(temp_c),
                "humidity": float(hum)
            }
            conn.publish(topic=TOPIC, payload=json.dumps(msg), qos=mqtt.QoS.AT_LEAST_ONCE) #Publishes to MQTT Topic
            print("pub:", msg)

        except RuntimeError as e:
            print("sensor transient:", e)
        except Exception as e:
            print("unexpected error:", e)

        time.sleep(READ_PERIOD_SEC)

except KeyboardInterrupt:
    print("\nDisconnecting…")
    try:
        conn.disconnect().result()
    finally:
        print("Disconnected. Bye!")
