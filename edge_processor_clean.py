"""
edge_processor_clean.py
--------------------------------
Subscribes to RAW sensor data on AWS IoT Core, validates/transforms it with
`process(...)`, and republishes a CLEAN payload for downstream dashboards/storage.

REPLACE the ALL-CAPS placeholders below before running.
"""

import json
import time

from awscrt import io, mqtt
from awsiot import mqtt_connection_builder

# Your own processor function:
#   def process(raw_str: str) -> tuple[bool, Any]
# Should return (True, cleaned_model) or (False, error_info)
from models_and_processor import process


# ===========================
# AWS IoT / MQTT CONFIG (REPLACE)
# ===========================
ENDPOINT     = "<YOUR_AWS_IOT_ENDPOINT>"   # e.g. "a1xxxx-ats.iot.us-east-1.amazonaws.com"
                                            # Find it in AWS IoT Core → Security → Certificate → Certificate ARN
CLIENT_ID    = "<UNIQUE_CLIENT_ID>"        # e.g. "rpi-sensor-001" — name of THIS MQTT connection; must be unique
PATH_TO_CERT = "<PATH_TO_DEVICE_CERT.crt>" # e.g. "/home/pi/certs/deviceCert.crt" — device X.509 certificate
                                            # these files are provided to you in the intial steps in creating your AWS IoT core
PATH_TO_KEY  = "<PATH_TO_PRIVATE_KEY.key>" # e.g. "/home/pi/certs/privateKey.key" — matching private key (keep secret), Never share with anyone!
PATH_TO_ROOT = "<PATH_TO_ROOT_CA.pem>"     # e.g. "/home/pi/certs/AmazonRootCA1.pem" — Amazon Root CA

RAW_TOPIC    = "<RAW_TOPIC>"                      # Raw Data Topic coming out for the DHT11 Sensor eg sensors/raw
CLEAN_TOPIC  = "<CLEAN_TOPIC>"                    # Proceessed Data Topic. eg sensors/clean

QOS_LEVEL    = mqtt.QoS.AT_LEAST_ONCE             # Ensures ACK Flag is recieved at least once before sending another message(TCP Protocol)
# ===========================



# ===========================
# Build secure MQTT connection (mTLS)
# ===========================
elg = io.EventLoopGroup(1)                        # One background thread to handle all MQTT/TLS networking
hr  = io.DefaultHostResolver(elg)                 # DNS resolver to turn the AWS endpoint hostname into an IP
cb  = io.ClientBootstrap(elg, hr)                # Bootstrap = uses our event threat + DNS for MQTT/TLS

conn_kwargs = dict(
    endpoint=ENDPOINT,                 # My AWS IoT device data endpoint
    cert_filepath=PATH_TO_CERT,        # Device certificate (.crt)
    pri_key_filepath=PATH_TO_KEY,      # Matching private key (.key) — keep secret all the time!
    ca_filepath=PATH_TO_ROOT,          # AmazonRootCA1.pem
    client_bootstrap=cb,
    client_id=CLIENT_ID,               # Unique client ID
    clean_session=True,                # Fresh MQTT session
    keep_alive_secs=30,                # Ping interval to keep connection alive
)

conn = mqtt_connection_builder.mtls_from_path(**conn_kwargs) # Builds a connection with TLS Certificates provided


# ===========================
# Message handler (RAW → CLEAN)
# Keep it lightweight; heavy work should be offloaded to a worker thread/queue.
# ===========================
def on_msg(topic, payload, dup, qos, retain, **kwargs):
    """
    MQTT message callback: handle RAW messages, clean them, and republish to CLEAN.

    Parameters
    ----------
    topic : str
        Topic the message arrived on (e.g., "sensors/raw").
    payload : bytes
        Message body in bytes (JSON text encoded as UTF-8).
        MQTT Format.
    dup : bool
        Duplicate delivery flag (MQTT QoS1 may deliver twice).
        Tells us if this might be a re-delivery(QoS1)
    qos : int
        MQTT Quality of Service level for the incoming message.
        The value for qos for this project is equal to 1 (Needs 1 ACK Flag to ensure the MQTT message has been recieved)
    retain : bool
        True if this was a retained message.
        When set equal to true, the MQTT broker keeps that message for new connections.
    **kwargs :
        Extra fields provided by the SDK (e.g., properties, packet_id). Ignored here.

    Behavior
    --------
    - Decode the payload, validate/transform via `process()`.
    - If valid, convert to JSON and publish to CLEAN_TOPIC with QOS_LEVEL.
    - If invalid, log the reason and skip publishing.
    - Any unexpected exception is caught so the network thread stays alive.
    """
    try:
        # Preview first 80 bytes to avoid noisy logs
        print("RX on", topic, ":", payload[:80], "…") #Small Preview for the raw topic + the first 80 bytes of our payload(MQTT message in bytes)

        ok, res = process(payload.decode("utf-8")) # Decoding the payload back to JSON Format Using JFT-8 
                                                    # then passing it to the process function for smoothing and validation

       # Goal: turn `res` into a normal Python dict we can json.dumps()

        if ok:
            body = res.model_dump() #converts pydantic model back to a plain dictonary for MQTT publishing format
            payload_out = json.dumps(body) #converts the python dictonary into a JSON 
            conn.publish(topic=CLEAN_TOPIC, payload=payload_out, qos=QOS_LEVEL) # publishes the JSON into the new Topic
            print("→ CLEAN:", body)
        else:
            # Validation failed; log why and drop the message
            print("DROP:", res)

    except Exception as e:
        # Never let a bad message crash the networking callback thread
        print("Process error:", repr(e))



# ===========================
# Connect, subscribe, and idle (callbacks do the work)
# ===========================
print("Connecting to AWS IoT…") 
conn.connect().result() #creates a secure connection to the AWS IoT
print("Connected. Subscribing to", RAW_TOPIC)

sub_future, _ = conn.subscribe(       #Ignoring the second variable which is packetID not relevant for our project
    topic=RAW_TOPIC,  #the raw Topic you want to listen to, in our case sensors/raw
    qos=QOS_LEVEL,    #delievery level for the incoming message (I have set QoS equal to 1 )
    callback=on_msg   #function to run everytime a message arrives from the sensors/raw (raw topic) to process and publishes it to sensors/clean(clean topic)
)
sub_result = sub_future.result()  # blocks until SUBACK arrives, confirms that the you have subscribed on the topic
print("Subscribed OK to", RAW_TOPIC, "with qos", sub_result.get('qos')) 

try:
    while True:
        time.sleep(1)  # keep process alive; all work happens in callbacks
except KeyboardInterrupt:
    print("\nDisconnecting…")
    conn.disconnect().result()
    print("Disconnected.")
