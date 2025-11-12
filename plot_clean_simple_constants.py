# plot_clean_simple_constants.py
# Minimal AWS IoT subscriber that live-plots temperature_c and humidity_pct.
# Uses fixed constants for endpoint, cert paths, topic, and window.

import json, time
from collections import deque
from awscrt import io, mqtt
from awsiot import mqtt_connection_builder
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

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
TOPIC        = "<RAW_TOPIC>"               # e.g. "sensors/raw" — ensure you have the clean topic not the raw one for better sensor visulization of the data.
WINDOW_SEC   = 180                        # show last ~N seconds on the plot, have it here as 3 mintues as a default.
# ============================================================================

# ---- Build secure MQTT connection (mTLS) ------------------------------------
elg = io.EventLoopGroup(1)                         # One background thread to handle all MQTT/TLS networking
hr  = io.DefaultHostResolver(elg)                 # DNS resolver to turn the AWS endpoint hostname into an IP
cb  = io.ClientBootstrap(elg, hr)                  # networking bootstrap
conn = mqtt_connection_builder.mtls_from_path(     # construct MQTT client w/ certs
    endpoint=ENDPOINT,
    cert_filepath=PATH_TO_CERT,
    pri_key_filepath=PATH_TO_KEY,
    ca_filepath=PATH_TO_ROOT,
    client_bootstrap=cb,
    client_id=CLIENT_ID,
    clean_session=True,        # Start a fresh MQTT session each connect
    keep_alive_secs=30,        # MQTT keepalive ping interval 
)

print("Connecting to AWS IoT…")
conn.connect().result()                             # block until connected (TLS + MQTT)
print("Connected.")

# ---- Rolling buffers (ring buffers) ------------------------------------------
tbuf = deque()  # timestamps (storing time of the temp and humidity reading was recieved)
T    = deque()  # temperature (°C)
H    = deque()  # humidity (%)

def _trim(now: float) -> None:
    """
    Drop points older than WINDOW_SEC from the left side of each deque.

    now: current absolute time (same units as values in tbuf, i.e., time.time()).
    cutoff = now - WINDOW_SEC means we **keep only** points with t >= cutoff.
    """
    cutoff = now - WINDOW_SEC       
    while tbuf and tbuf[0] < cutoff:
        tbuf.popleft()
        T.popleft()
        H.popleft()


def on_msg(topic, payload, dup, qos, retain, **kwargs):
    """
    MQTT callback: decode JSON payload, extract temp/humidity, append to buffers.
    - payload: bytes → decode('utf-8') because MQTT bodies are binary by spec.
    - dup/qos/retain: metadata (QoS1 may redeliver; retain means broker-cached msg).
    """
    try:
        d = json.loads(payload.decode("utf-8"))  # decodes the payload MQTT Message using UTF-8 to a String then transform it to a dict
        temp = d.get("temperature_c", d.get("temp_c", d.get("temperature"))) # Accept multiple key names so this works with CLEAN or RAW payloads:
        hum  = d.get("humidity_pct", d.get("humidity")) # Accept multiple key names so this works with CLEAN or RAW payloads:
        if temp is None or hum is None:
            return  # ignore messages missing the fields we plot, connection is stopeed
        now = time.time()
        tbuf.append(now); T.append(float(temp)); H.append(float(hum)) 
        _trim(now)   # remove any OLD points so we only keep the last WINDOW_SEC seconds
    except Exception as e:
        print("bad payload:", e)  # never crash the callback


print(f"Subscribing to {TOPIC}")
conn.subscribe(       
    topic=TOPIC,  
    qqos=mqtt.QoS.AT_LEAST_ONCE,    #delievery level for the incoming message (I have set QoS equal to 1 )
    callback=on_msg   
)[0].result()        #blocks until SUBACK arrives, confirms that the you have subscribed on the topic
print("Subscribed.")

# ---- Matplotlib live plot ----------------------------------------------------
fig, ax = plt.subplots()       #Intalizing new figures
(line_t,) = ax.plot([], [], label="temperature (°C)")  # empty line axis for temp Data
(line_h,) = ax.plot([], [], label="humidity (%)") #empty line axis for Humidity Data
ax.legend(loc="upper left")
ax.set_title(f"AWS IoT: {TOPIC}")
ax.set_xlabel(f"Time (last ~{WINDOW_SEC}s)")

def update(_):
    """Animation step: convert absolute timestamps to relative seconds and redraw."""
    if not tbuf:
        return line_t, line_h
    t0 = tbuf[0]                           # the oldest (leftmost) timestamp we kept
    x  = [ti - t0 for ti in tbuf]          # seconds since first visible point
    line_t.set_data(x, list(T))       # put x vs temperature points into the temp line    
    line_h.set_data(x, list(H))       # put x vs humidity points into the humidity line
    ax.relim(); ax.autoscale_view()        # rescan data limits and rescale axes to fit
    return line_t, line_h                  #Updated data

ani = FuncAnimation(fig, update, interval=500, cache_frame_data=False)  # Calls Update Function to update it constantly
plt.tight_layout()
try:
    plt.show()                              # blocks until the window is closed
finally:
    try:
        conn.disconnect().result()          # cleanly close MQTT conn on exit
    except:
        pass
