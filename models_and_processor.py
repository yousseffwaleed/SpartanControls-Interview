"""
models_and_processor.py
-----------------------
Validate RAW sensor JSON, apply a tiny smoothing window,
and emit a clean, uniform message ready for dashboards and data storage.

"""

from pydantic import BaseModel, Field           # Pydantic is a library used to check if the data is in the right shape and type.yes
from typing import Literal, Tuple, Union
from collections import deque

# -----------------------------
# 1) Schemas (Pydantic models)
# -----------------------------

class SensorIn(BaseModel):
    """
    Defines the expected RAW input schema for sensor data.

    Using BaseModel:
    - Ensures all fields have correct types and value ranges.
    - Automatically validates JSON input when creating the model.
    """
    device_id: str
    ts: int                                   # epoch time 
    temperature: float = Field(ge=-40, le=125)  # °C — DHT11 Tempretaure Range from -40 to 125 °C
    humidity: float = Field(ge=0, le=100)       # Humidity Range from 0 to 100

class SensorOut(BaseModel):
    """
    CLEAN message format published to 'sensors/clean'. 
    """
    device_id: str
    ts: int                                    # keep numeric timestamp for easy sorting/analytics
    temperature_c: float
    temperature_avg5_c: float                  # Average tempretaure for 5 samples
    humidity_pct: float
    quality: Literal["WARMUP", "OK"]           # keep only the last 5 temperature readings for the moving average
    schema_version: str = "1.0"                # Lets dashboard/ETL in the cloud know which schema/version they are using

# -----------------------------
# 2) Rolling window (5 samples)
# -----------------------------
_window = deque(maxlen=5)  # keep only the last 5 temperature readings for the moving average, 


# -----------------------------
# 3) Processor function
# -----------------------------
def process(msg_json: str) -> Tuple[bool, Union[SensorOut, str]]:
    """
    Validate, smooth, and reformat a raw DHT11 reading.

    Args:
        msg_json: RAW payload as a JSON string, e.g.
                  '{"device_id":"rpi-sensor-001","ts":1762817460,"temperature":26.7,"humidity":9.0}'

    Returns:
        (True, SensorOut) on success
        (False, "schema_error:...") on validation/parse errors

    """
    # 1) Parse & validate input against SensorIn
    try:
        raw = SensorIn.model_validate_json(msg_json)   #Validates Input to match the required, returns raw.variablename
    except Exception as e:
        # If it does not match the correct type specified at the beginning of the file throw an error .
        return False, f"schema_error:{e}"

    # 2) Update rolling temperature window and compute average
    _window.append(raw.temperature)   #Passed from the model_validate_json
    avg = sum(_window) / len(_window) #computes the average of the last 5 readings


    # 3) Emit the CLEAN model (keeps ts as-is to match the publisher)
    out = SensorOut(
        device_id=raw.device_id,
        ts=raw.ts,                              
        temperature_c=raw.temperature,
        temperature_avg5_c=round(avg, 2),       # round for nicer dashboards in Amazon Cloud Dashboards (will be used later on in the project)
        humidity_pct=raw.humidity,
        quality="OK" if len(_window) == _window.maxlen else "WARMUP",
    )

    return True, out
