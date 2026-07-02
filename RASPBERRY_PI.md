# Raspberry Pi camera bridge

This project already has a Flask backend endpoint at `/upload`. The Raspberry Pi only needs to run the camera bridge:

```bash
python backend/pi_fridge_camera.py --backend-url http://<PC_OR_SERVER_IP>:5000 --fridge-id <FRIDGE_ID>
```

It captures the camera image, finds ingredient candidates dynamically, classifies the candidates, and uploads the full image plus recognized crops to the backend. The backend writes the results to `fridge_items`. Common food labels already known by the detector, such as apples and bananas, are used directly. Other candidates are passed to the grocery classifier.

Candidate crop priority:

1. YOLO detection boxes from `backend/yolov8n.pt`
2. Contour proposals for ingredients the general detector does not know
3. The old center crop only when the previous steps do not produce a usable prediction

## 1. Backend on the main machine

Start the backend so the Pi can reach it from the same Wi-Fi/LAN:

```bash
cd backend
python app.py
```

Use the machine's LAN IP address for the Pi, not `127.0.0.1`. For example:

```bash
http://192.168.0.25:5000
```

If you leave `--fridge-id` out, the backend uses the current active fridge.

## 2. Raspberry Pi setup

On Raspberry Pi OS 64-bit:

```bash
sudo apt update
sudo apt install -y python3-venv python3-opencv python3-picamera2 python3-gpiozero
python3 -m venv --system-site-packages .venv
source .venv/bin/activate
pip install -r backend/requirements-pi.txt
```

Copy this project folder to the Pi, including:

- `backend/pi_fridge_camera.py`
- `backend/yolov8n.pt`
- `backend/runs/classify/grocery-classifier-public4/weights/best.pt`

## 3. Test once

Put one ingredient in front of the camera and run:

```bash
source .venv/bin/activate
python backend/pi_fridge_camera.py \
  --backend-url http://192.168.0.25:5000 \
  --once
```

Useful test options:

```bash
python backend/pi_fridge_camera.py --dry-run
python backend/pi_fridge_camera.py --camera-backend opencv --camera-index 0
python backend/pi_fridge_camera.py --fps 30 --interval 0.25
python backend/pi_fridge_camera.py --min-confidence 0.75
python backend/pi_fridge_camera.py --detection-confidence 0.25 --crop-padding-ratio 0.20
python backend/pi_fridge_camera.py --detection-imgsz 416
```

The PC preview and Raspberry Pi bridge both default to a `640x480` camera frame at `30 FPS`. The `--interval` option is separate: it controls how often the heavier detection and classification pipeline runs. Lower it from the default `1.0` seconds only if the Pi has enough processing headroom.

For a local PC preview with visible dynamic boxes:

```bash
python backend/classify_camera.py
```

Press `s` to upload the recognized boxes and `q` to quit.

## 4. Run continuously

```bash
BACKEND_URL=http://192.168.0.25:5000 \
FRIDGE_ID=1 \
python backend/pi_fridge_camera.py
```

Default behavior:

- configures the camera at `640x480`, `30 FPS`
- reads a frame every 1 second
- finds up to 4 dynamic crop candidates
- adds padding around detected crops before classification
- waits for the same recognized label group 3 times in a row
- uploads each recognized item in the stable group
- prevents repeat uploads with a 20 second cooldown

## 5. Reed switch trigger

Recommended wiring for a plain two-wire reed switch:

- one wire to Raspberry Pi `GND`
- one wire to `GPIO17` physical pin 11

With this wiring and the magnet near the switch when the fridge door is closed:

- door closed: GPIO is pulled low
- door open: GPIO goes high

Run a one-event test:

```bash
BACKEND_URL=http://192.168.0.25:5000 \
python backend/pi_fridge_camera.py \
  --trigger reed \
  --reed-pin 17 \
  --reed-open-level high \
  --once
```

Continuous reed-triggered mode:

```bash
BACKEND_URL=http://192.168.0.25:5000 \
FRIDGE_ID=1 \
python backend/pi_fridge_camera.py \
  --trigger reed \
  --reed-pin 17 \
  --reed-open-level high
```

Low-latency reed-triggered mode keeps the camera ready, but runs detection and
classification only when the door opens:

```bash
BACKEND_URL=http://192.168.0.25:5000 \
FRIDGE_ID=1 \
python backend/pi_fridge_camera.py \
  --trigger reed \
  --reed-pin 17 \
  --reed-open-level high \
  --reed-camera-mode warm \
  --stable-frames 2 \
  --interval 0.2 \
  --detection-imgsz 416
```

Arm in/out workflow:

- reed open: scan and add recognized ingredients
- reed close: scan and consume recognized ingredients if they already exist

```bash
BACKEND_URL=http://192.168.0.25:5000 \
FRIDGE_ID=1 \
python backend/pi_fridge_camera.py \
  --trigger reed \
  --reed-pin 17 \
  --reed-open-level high \
  --reed-workflow add-on-open-consume-on-close \
  --reed-camera-mode warm \
  --stable-frames 2 \
  --interval 0.2 \
  --detection-imgsz 416 \
  --preview-stream
```

For this workflow, mount the camera so the ingredient is visible both while the
hand enters and while it leaves. If the scan is too early or too late, tune
`--post-open-delay` or `--post-close-delay`.

With `--preview-stream`, open the Raspberry Pi camera preview from another
device on the same network:

```text
http://<RASPBERRY_PI_IP>:8080
```

The preview shows the latest camera frame and draws detection boxes while a scan
is running. With `--reed-camera-mode warm`, it also updates while waiting for
the reed switch to open or close.

In this workflow, the open-side add scan keeps running until the reed switch
closes. The first stable recognized ingredient group is added once, then the
script keeps updating the camera preview and detection logs until close is
detected. After close, the consume scan still stops after the first stable
consume result or `--scan-timeout`.

If opening the door does nothing but closing it triggers the scan, flip the level:

```bash
python backend/pi_fridge_camera.py --trigger reed --reed-open-level low
```

In reed mode the script waits for the door-open signal, starts the camera, uploads the first stable recognized ingredient group, stops the camera, then waits for the door to close before arming the next scan.
With `--reed-workflow add-on-open-consume-on-close`, the close event calls the
backend `/consume` endpoint. The backend subtracts the most recently updated
matching item by 1, deletes it when the remaining quantity is 0, and skips the
event when no matching item exists.
With `--reed-camera-mode warm`, the script starts the camera once at launch,
keeps it ready between door events, discards a couple of buffered frames when the
door opens, and then scans immediately. This uses more power than on-demand reed
mode, but much less CPU than continuous scanning.

## 6. Performance tuning

Dynamic detection is more accurate than a fixed center box but uses more CPU. If the Raspberry Pi scan is too slow, reduce detector input size:

```bash
python backend/pi_fridge_camera.py --detection-imgsz 416
```

If needed, disable the YOLO detector and keep contour proposals plus the center fallback:

```bash
python backend/pi_fridge_camera.py --disable-detector
```

## 7. Optional systemd service

Create `/etc/systemd/system/fridge-camera.service`:

```ini
[Unit]
Description=Fridge camera bridge
After=network-online.target
Wants=network-online.target

[Service]
WorkingDirectory=/home/pi/fridge
Environment=BACKEND_URL=http://192.168.0.25:5000
Environment=FRIDGE_ID=1
Environment=TRIGGER_MODE=reed
Environment=REED_PIN=17
Environment=REED_OPEN_LEVEL=high
Environment=REED_CAMERA_MODE=warm
Environment=REED_WORKFLOW=add-on-open-consume-on-close
Environment=PREVIEW_STREAM=1
Environment=PREVIEW_STREAM_PORT=8080
Environment=CAMERA_FPS=30
Environment=STABLE_FRAMES=2
Environment=SCAN_INTERVAL_SECONDS=0.2
Environment=DETECTION_IMGSZ=416
ExecStart=/home/pi/fridge/.venv/bin/python /home/pi/fridge/backend/pi_fridge_camera.py
Restart=always
RestartSec=5
User=pi

[Install]
WantedBy=multi-user.target
```

Then:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now fridge-camera
sudo journalctl -u fridge-camera -f
```
