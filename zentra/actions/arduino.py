import json
import re
import subprocess
import time
import threading
from pathlib import Path
from collections import deque

from zentra.config import BASE_FOLDER
from zentra.logger import log
from zentra.ollama import ollama_raw_sync

try:
    import serial
    import serial.tools.list_ports
    SERIAL_AVAILABLE = True
except ImportError:
    SERIAL_AVAILABLE = False


ARDUINO_FOLDER = str(Path(BASE_FOLDER) / "arduino")


BOARD_SPECS = {
    "uno": {
        "name": "Arduino Uno R3",
        "mcu": "ATmega328P",
        "clock": "16 MHz",
        "flash": "32 KB",
        "ram": "2 KB",
        "eeprom": "1 KB",
        "digital_pins": 14,
        "analog_pins": 6,
        "pwm_pins": [3, 5, 6, 9, 10, 11],
        "interrupt_pins": [2, 3],
        "i2c": {"sda": "A4", "scl": "A5"},
        "spi": {"mosi": 11, "miso": 12, "sck": 13, "ss": 10},
        "uart": {"rx": 0, "tx": 1},
        "builtin_led": 13,
        "voltage": "5V",
        "fqbn": "arduino:avr:uno",
    },
    "nano": {
        "name": "Arduino Nano",
        "mcu": "ATmega328P",
        "clock": "16 MHz",
        "flash": "32 KB",
        "ram": "2 KB",
        "digital_pins": 14,
        "analog_pins": 8,
        "pwm_pins": [3, 5, 6, 9, 10, 11],
        "interrupt_pins": [2, 3],
        "i2c": {"sda": "A4", "scl": "A5"},
        "spi": {"mosi": 11, "miso": 12, "sck": 13, "ss": 10},
        "builtin_led": 13,
        "voltage": "5V",
        "fqbn": "arduino:avr:nano",
    },
    "mega": {
        "name": "Arduino Mega 2560",
        "mcu": "ATmega2560",
        "clock": "16 MHz",
        "flash": "256 KB",
        "ram": "8 KB",
        "eeprom": "4 KB",
        "digital_pins": 54,
        "analog_pins": 16,
        "pwm_pins": list(range(2, 14)) + [44, 45, 46],
        "interrupt_pins": [2, 3, 18, 19, 20, 21],
        "i2c": {"sda": 20, "scl": 21},
        "spi": {"mosi": 51, "miso": 50, "sck": 52, "ss": 53},
        "uart": {"rx": 0, "tx": 1},
        "builtin_led": 13,
        "voltage": "5V",
        "fqbn": "arduino:avr:mega",
    },
    "esp32": {
        "name": "ESP32 DevKit",
        "mcu": "ESP32",
        "clock": "240 MHz (dual core)",
        "flash": "4 MB",
        "ram": "520 KB",
        "digital_pins": 34,
        "analog_pins": 18,
        "pwm_pins": "all GPIO",
        "interrupt_pins": "all GPIO",
        "i2c": {"sda": 21, "scl": 22},
        "spi": {"mosi": 23, "miso": 19, "sck": 18, "ss": 5},
        "wifi": True,
        "bluetooth": True,
        "builtin_led": 2,
        "voltage": "3.3V",
        "avoid_pins": "GPIO 6-11 (connected to flash)",
        "fqbn": "esp32:esp32:esp32",
    },
    "esp8266": {
        "name": "ESP8266 NodeMCU",
        "mcu": "ESP8266",
        "clock": "80 MHz",
        "flash": "4 MB",
        "ram": "80 KB",
        "digital_pins": 17,
        "analog_pins": 1,
        "pwm_pins": "all except GPIO 16",
        "i2c": {"sda": "D2 (GPIO 4)", "scl": "D1 (GPIO 5)"},
        "spi": {"mosi": "D7 (GPIO 13)", "miso": "D6 (GPIO 12)", "sck": "D5 (GPIO 14)"},
        "wifi": True,
        "builtin_led": 2,
        "voltage": "3.3V",
        "fqbn": "esp8266:esp8266:nodemcuv2",
    },
    "pi_pico": {
        "name": "Raspberry Pi Pico",
        "mcu": "RP2040",
        "clock": "133 MHz (dual core)",
        "flash": "2 MB",
        "ram": "264 KB",
        "digital_pins": 26,
        "analog_pins": 3,
        "pwm_pins": "all GPIO (16 channels)",
        "i2c": {"sda": "GP0/GP2/...", "scl": "GP1/GP3/..."},
        "builtin_led": 25,
        "voltage": "3.3V",
        "fqbn": "rp2040:rp2040:rpipico",
    },
}


COMPONENT_LIBRARY = {
    "dht11": {"library": "DHT sensor library", "include": "DHT.h", "purpose": "temperature + humidity"},
    "dht22": {"library": "DHT sensor library", "include": "DHT.h", "purpose": "temperature + humidity (higher precision)"},
    "ds18b20": {"library": "OneWire + DallasTemperature", "include": "OneWire.h, DallasTemperature.h", "purpose": "waterproof temperature"},
    "bmp280": {"library": "Adafruit BMP280", "include": "Adafruit_BMP280.h", "purpose": "temperature + pressure"},
    "bme280": {"library": "Adafruit BME280", "include": "Adafruit_BME280.h", "purpose": "temp + pressure + humidity"},
    "mpu6050": {"library": "MPU6050", "include": "MPU6050.h", "purpose": "accelerometer + gyroscope"},
    "hc-sr04": {"library": "NewPing (optional)", "include": "NewPing.h", "purpose": "ultrasonic distance"},
    "ultrasonic": {"library": "NewPing", "include": "NewPing.h", "purpose": "ultrasonic distance"},
    "lcd": {"library": "LiquidCrystal_I2C", "include": "LiquidCrystal_I2C.h", "purpose": "I2C LCD display"},
    "oled": {"library": "Adafruit SSD1306 + Adafruit GFX", "include": "Adafruit_SSD1306.h", "purpose": "OLED display"},
    "ssd1306": {"library": "Adafruit SSD1306 + Adafruit GFX", "include": "Adafruit_SSD1306.h", "purpose": "OLED display"},
    "tft": {"library": "TFT_eSPI or Adafruit ILI9341", "include": "TFT_eSPI.h", "purpose": "TFT display"},
    "sd": {"library": "SD", "include": "SD.h", "purpose": "SD card storage"},
    "rtc": {"library": "RTClib", "include": "RTClib.h", "purpose": "real-time clock"},
    "ds3231": {"library": "RTClib", "include": "RTClib.h", "purpose": "precise RTC"},
    "servo": {"library": "Servo", "include": "Servo.h", "purpose": "servo motor control"},
    "stepper": {"library": "AccelStepper", "include": "AccelStepper.h", "purpose": "stepper motor with acceleration"},
    "28byj-48": {"library": "AccelStepper or Stepper", "include": "Stepper.h", "purpose": "small stepper motor"},
    "nrf24": {"library": "RF24", "include": "RF24.h", "purpose": "2.4GHz wireless"},
    "esp-now": {"library": "builtin (ESP32/ESP8266)", "include": "esp_now.h", "purpose": "peer-to-peer wireless"},
    "wifi": {"library": "WiFi (ESP32) or ESP8266WiFi", "include": "WiFi.h", "purpose": "wifi connection"},
    "bluetooth": {"library": "BluetoothSerial (ESP32)", "include": "BluetoothSerial.h", "purpose": "bluetooth classic"},
    "ble": {"library": "BLEDevice (ESP32)", "include": "BLEDevice.h", "purpose": "bluetooth low energy"},
    "rfid": {"library": "MFRC522", "include": "MFRC522.h", "purpose": "RFID reader"},
    "mfrc522": {"library": "MFRC522", "include": "MFRC522.h", "purpose": "RFID reader"},
    "neopixel": {"library": "Adafruit NeoPixel or FastLED", "include": "Adafruit_NeoPixel.h", "purpose": "WS2812 LED strips"},
    "ws2812": {"library": "FastLED", "include": "FastLED.h", "purpose": "addressable LED strip"},
    "ir": {"library": "IRremote", "include": "IRremote.h", "purpose": "infrared remote"},
    "keypad": {"library": "Keypad", "include": "Keypad.h", "purpose": "matrix keypad input"},
    "buzzer": {"library": "none (use tone())", "include": "", "purpose": "piezo buzzer"},
    "joystick": {"library": "none", "include": "", "purpose": "analog joystick (use analogRead)"},
    "potentiometer": {"library": "none", "include": "", "purpose": "variable resistor (use analogRead)"},
    "relay": {"library": "none", "include": "", "purpose": "high-voltage switching"},
    "button": {"library": "none (or Bounce2)", "include": "", "purpose": "digital input"},
    "led": {"library": "none", "include": "", "purpose": "use digitalWrite or analogWrite"},
}


_serial_connections: dict = {}
_serial_buffers: dict = {}
_serial_lock = threading.Lock()


def handle_arduino_boards(data: dict) -> str:
    lines = ["**Supported Boards:**\n"]
    for key, spec in BOARD_SPECS.items():
        lines.append(f"  **{key}** - {spec['name']}")
        lines.append(f"    {spec['mcu']} @ {spec['clock']}, {spec.get('flash', '?')} flash, {spec.get('ram', '?')} ram")
        lines.append(f"    {spec['digital_pins']} digital, {spec['analog_pins']} analog, {spec['voltage']}")
        lines.append("")
    lines.append("Use: 'show board info for esp32' or 'what pins does the uno have'")
    return "\n".join(lines).strip()


def handle_arduino_board_info(data: dict) -> str:
    board = (data.get("app") or data.get("reply") or "").strip().lower()
    board = board.replace("arduino ", "").replace(" ", "_")

    aliases = {"r3": "uno", "2560": "mega", "dev": "esp32", "devkit": "esp32", "nodemcu": "esp8266", "pico": "pi_pico"}
    board = aliases.get(board, board)

    if board not in BOARD_SPECS:
        available = ", ".join(BOARD_SPECS.keys())
        return f"Unknown board '{board}'. Available: {available}"

    spec = BOARD_SPECS[board]
    lines = [f"**{spec['name']}**\n"]
    lines.append(f"  **Microcontroller:** {spec['mcu']}")
    lines.append(f"  **Clock:** {spec['clock']}")
    lines.append(f"  **Flash:** {spec.get('flash', 'N/A')}")
    lines.append(f"  **RAM:** {spec.get('ram', 'N/A')}")
    if "eeprom" in spec:
        lines.append(f"  **EEPROM:** {spec['eeprom']}")
    lines.append(f"  **Voltage:** {spec['voltage']}")
    lines.append("")
    lines.append(f"  **Digital pins:** {spec['digital_pins']}")
    lines.append(f"  **Analog pins:** {spec['analog_pins']}")
    lines.append(f"  **PWM pins:** {spec['pwm_pins']}")
    if "interrupt_pins" in spec:
        lines.append(f"  **Interrupt pins:** {spec['interrupt_pins']}")
    lines.append(f"  **Built-in LED:** pin {spec['builtin_led']}")
    lines.append("")
    lines.append(f"  **I2C:** SDA={spec['i2c']['sda']}, SCL={spec['i2c']['scl']}")
    if "spi" in spec:
        spi = spec['spi']
        lines.append(f"  **SPI:** MOSI={spi['mosi']}, MISO={spi['miso']}, SCK={spi['sck']}, SS={spi.get('ss', '-')}")
    if "uart" in spec:
        lines.append(f"  **UART:** RX={spec['uart']['rx']}, TX={spec['uart']['tx']}")
    if spec.get("wifi"):
        lines.append(f"  **WiFi:** yes")
    if spec.get("bluetooth"):
        lines.append(f"  **Bluetooth:** yes")
    if "avoid_pins" in spec:
        lines.append(f"  **WARNING:** {spec['avoid_pins']}")
    lines.append("")
    lines.append(f"  **FQBN:** `{spec['fqbn']}`")
    return "\n".join(lines)


def handle_arduino_ports(data: dict) -> str:
    if not SERIAL_AVAILABLE:
        return (
            "`pyserial` not installed. Install with: `pip install pyserial`\n"
            "Needed to detect Arduino boards connected via USB."
        )

    ports = serial.tools.list_ports.comports()
    if not ports:
        return "No serial ports detected. Is your board plugged in?"

    lines = [f"**Detected Ports** ({len(ports)})\n"]
    for p in ports:
        desc = p.description or "Unknown"
        manufacturer = p.manufacturer or ""

        likely_arduino = any(kw in desc.lower() for kw in ["arduino", "ch340", "cp210", "ftdi", "usb serial", "silicon labs"])
        marker = " [ARDUINO?]" if likely_arduino else ""

        lines.append(f"  **{p.device}**{marker}")
        lines.append(f"    {desc}")
        if manufacturer:
            lines.append(f"    Manufacturer: {manufacturer}")
        if p.vid and p.pid:
            lines.append(f"    VID:PID = {p.vid:04X}:{p.pid:04X}")
        lines.append("")

    return "\n".join(lines).strip()


def handle_arduino_library(data: dict) -> str:
    component = (data.get("app") or data.get("reply") or data.get("content") or "").strip().lower()
    if not component:
        return "arduino_library: provide a component name."

    component = component.replace(" ", "").replace("-", "").replace("_", "")

    for key, info in COMPONENT_LIBRARY.items():
        normalized = key.replace("-", "").replace("_", "")
        if normalized == component or normalized in component or component in normalized:
            lines = [f"**{key.upper()}** - {info['purpose']}\n"]
            if info["library"]:
                lines.append(f"  **Library:** {info['library']}")
            if info["include"]:
                lines.append(f"  **Include:** `#include <{info['include']}>`")
            if info["library"] and info["library"] != "none" and "builtin" not in info["library"].lower():
                lib_name = info["library"].split("(")[0].strip()
                lines.append(f"\n  Install via Arduino IDE Library Manager:\n  **Tools > Manage Libraries > search '{lib_name}'**")
            return "\n".join(lines)

    available = ", ".join(sorted(COMPONENT_LIBRARY.keys()))
    return f"Component '{component}' not in database. Known components:\n{available}"


def handle_arduino_generate(data: dict) -> str:
    description = (data.get("reply") or data.get("content") or "").strip()
    board = (data.get("app") or "uno").strip().lower()

    if not description:
        return "arduino_generate: describe what you want to build."

    board_info = ""
    if board in BOARD_SPECS:
        spec = BOARD_SPECS[board]
        board_info = (
            f"Target board: {spec['name']} ({spec['mcu']}, {spec['voltage']})\n"
            f"Digital pins: {spec['digital_pins']}, Analog: {spec['analog_pins']}\n"
            f"PWM pins: {spec['pwm_pins']}\n"
            f"I2C: SDA={spec['i2c']['sda']}, SCL={spec['i2c']['scl']}\n"
            f"Built-in LED: pin {spec['builtin_led']}\n"
        )

    prompt = (
        "You are an Arduino expert. Generate complete, working Arduino sketch code.\n"
        "Reply with ONLY a JSON object, no markdown:\n"
        '{"code": "complete .ino source", "wiring": "pin connections table", '
        '"libraries": ["lib1", "lib2"], "notes": "important notes"}\n\n'
        "Requirements:\n"
        "- Include all necessary #include statements\n"
        "- Add setup() and loop() functions\n"
        "- Add comments explaining each section\n"
        "- Use Serial.begin(9600) and include Serial.println for debugging\n"
        "- Choose appropriate pins based on the board's capabilities\n"
        "- Wiring should be a plaintext table mapping component pins to board pins"
    )

    user_prompt = f"{board_info}\nUser request: {description}"

    raw = ollama_raw_sync(prompt, user_prompt, max_tokens=2000)

    try:
        cleaned = re.sub(r"```(?:json)?\n?", "", raw).replace("```", "").strip()
        parsed = json.loads(cleaned)
    except Exception:
        return f"Could not parse generated code. Raw output:\n```\n{raw[:1000]}\n```"

    code = parsed.get("code", "")
    wiring = parsed.get("wiring", "")
    libraries = parsed.get("libraries", [])
    notes = parsed.get("notes", "")

    Path(ARDUINO_FOLDER).mkdir(parents=True, exist_ok=True)
    sketch_name = re.sub(r"[^a-zA-Z0-9_]", "_", description[:40]).strip("_") or "sketch"
    sketch_path = Path(ARDUINO_FOLDER) / f"{sketch_name}.ino"

    try:
        sketch_path.write_text(code, encoding="utf-8")
    except Exception as exc:
        return f"Could not save sketch: {exc}"

    result = [f"**Arduino Sketch Generated**"]
    result.append(f"Target: {BOARD_SPECS.get(board, {}).get('name', board)}")
    result.append(f"Saved to: `{sketch_path}`\n")

    if wiring:
        result.append(f"**Wiring:**\n```\n{wiring}\n```")
    if libraries:
        result.append(f"**Libraries needed:** {', '.join(libraries)}")
    if notes:
        result.append(f"**Notes:** {notes}")

    result.append(f"\n**Code preview:**\n```cpp\n{code[:800]}{'...' if len(code) > 800 else ''}\n```")
    return "\n".join(result)


def handle_arduino_compile(data: dict) -> str:
    sketch = (data.get("filename") or data.get("app") or "").strip()
    board = (data.get("reply") or "uno").strip().lower()

    if not sketch:
        return "arduino_compile: provide sketch path."

    if not sketch.endswith(".ino"):
        sketch = sketch + ".ino"

    sketch_path = Path(sketch)
    if not sketch_path.exists():
        sketch_path = Path(ARDUINO_FOLDER) / sketch
    if not sketch_path.exists():
        return f"Sketch not found: {sketch}"

    fqbn = BOARD_SPECS.get(board, {}).get("fqbn", "arduino:avr:uno")

    try:
        result = subprocess.run(
            ["arduino-cli", "compile", "--fqbn", fqbn, str(sketch_path.parent)],
            capture_output=True, text=True, timeout=120,
        )
        output = result.stdout.strip()
        errors = result.stderr.strip()

        if result.returncode == 0:
            return f"**Compiled successfully** for {fqbn}\n\n```\n{output[:1000]}\n```"
        else:
            return f"**Compilation failed**\n\n```\n{errors[:1500]}\n```"
    except FileNotFoundError:
        return (
            "`arduino-cli` not found. Install it from:\n"
            "https://arduino.github.io/arduino-cli/latest/installation/\n\n"
            "Then: `arduino-cli core install arduino:avr`"
        )
    except subprocess.TimeoutExpired:
        return "Compilation timed out after 120s"
    except Exception as exc:
        return f"Compile error: {exc}"


def handle_arduino_upload(data: dict) -> str:
    sketch = (data.get("filename") or "").strip()
    port = (data.get("app") or "").strip()
    board = (data.get("reply") or "uno").strip().lower()

    if not sketch:
        return "arduino_upload: provide sketch path."
    if not port:
        return "arduino_upload: provide port (e.g. COM3 or /dev/ttyUSB0). Run arduino_ports to find it."

    sketch_path = Path(sketch)
    if not sketch_path.exists():
        sketch_path = Path(ARDUINO_FOLDER) / sketch
    if not sketch_path.exists():
        return f"Sketch not found: {sketch}"

    fqbn = BOARD_SPECS.get(board, {}).get("fqbn", "arduino:avr:uno")

    try:
        result = subprocess.run(
            ["arduino-cli", "upload", "-p", port, "--fqbn", fqbn, str(sketch_path.parent)],
            capture_output=True, text=True, timeout=60,
        )
        if result.returncode == 0:
            return f"**Uploaded to {port}** ({fqbn})\n\n```\n{result.stdout.strip()[:800]}\n```"
        else:
            return f"**Upload failed**\n\n```\n{result.stderr.strip()[:1000]}\n```"
    except FileNotFoundError:
        return "arduino-cli not found. See arduino_compile for install instructions."
    except Exception as exc:
        return f"Upload error: {exc}"


def _serial_reader_thread(port: str, conn):
    buf = _serial_buffers[port]
    while port in _serial_connections:
        try:
            if conn.in_waiting:
                line = conn.readline().decode("utf-8", errors="replace").strip()
                if line:
                    with _serial_lock:
                        buf.append({"time": time.strftime("%H:%M:%S"), "line": line})
        except Exception:
            break
        time.sleep(0.05)


def handle_arduino_monitor_start(data: dict) -> str:
    if not SERIAL_AVAILABLE:
        return "pyserial not installed. Run: pip install pyserial"

    port = (data.get("app") or "").strip()
    baud_str = (data.get("reply") or "9600").strip()

    if not port:
        return "arduino_monitor_start: provide port (e.g. COM3 or /dev/ttyUSB0)"

    try:
        baud = int(baud_str.split()[0]) if baud_str.split() else 9600
    except ValueError:
        baud = 9600

    if port in _serial_connections:
        return f"Already monitoring {port}. Stop it first."

    try:
        conn = serial.Serial(port, baud, timeout=0.5)
        time.sleep(1.5)
        _serial_connections[port] = conn
        _serial_buffers[port] = deque(maxlen=200)

        t = threading.Thread(target=_serial_reader_thread, args=(port, conn), daemon=True)
        t.start()

        return f"**Monitoring {port}** @ {baud} baud\nUse arduino_monitor_read to see output."
    except Exception as exc:
        return f"Failed to open {port}: {exc}"


def handle_arduino_monitor_read(data: dict) -> str:
    port = (data.get("app") or "").strip()

    if not port:
        if len(_serial_connections) == 1:
            port = list(_serial_connections.keys())[0]
        else:
            return "arduino_monitor_read: provide port, or only 1 monitor should be active."

    if port not in _serial_buffers:
        return f"No monitor running on {port}. Start with arduino_monitor_start."

    with _serial_lock:
        lines = list(_serial_buffers[port])

    if not lines:
        return f"No output yet on {port}."

    recent = lines[-30:]
    formatted = "\n".join(f"  [{l['time']}] {l['line']}" for l in recent)
    return f"**Serial output from {port}** (last {len(recent)} lines)\n\n```\n{formatted}\n```"


def handle_arduino_monitor_stop(data: dict) -> str:
    port = (data.get("app") or "").strip()

    if not port:
        if len(_serial_connections) == 1:
            port = list(_serial_connections.keys())[0]
        elif not _serial_connections:
            return "No active monitors."
        else:
            return f"Specify which: {', '.join(_serial_connections.keys())}"

    if port not in _serial_connections:
        return f"No monitor on {port}."

    try:
        conn = _serial_connections.pop(port)
        conn.close()
        _serial_buffers.pop(port, None)
        return f"Stopped monitoring {port}."
    except Exception as exc:
        return f"Error stopping monitor: {exc}"


def handle_arduino_send(data: dict) -> str:
    port = (data.get("app") or "").strip()
    message = (data.get("reply") or data.get("content") or "").strip()

    if not port:
        if len(_serial_connections) == 1:
            port = list(_serial_connections.keys())[0]
        else:
            return "arduino_send: provide port."

    if not message:
        return "arduino_send: provide message to send."

    if port not in _serial_connections:
        return f"No connection on {port}. Start monitor first."

    try:
        conn = _serial_connections[port]
        conn.write((message + "\n").encode("utf-8"))
        return f"Sent to {port}: `{message}`"
    except Exception as exc:
        return f"Send failed: {exc}"
