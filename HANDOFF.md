# Fridge Project Handoff

## Current Goal

Use Raspberry Pi 5 as the camera bridge for the fridge app:

1. Detect fridge door open through a reed switch.
2. Turn on the camera.
3. Find ingredient candidates dynamically instead of requiring a fixed center box.
4. Classify the detected crops.
5. Send the image, crops, labels, and confidences to the backend database through the backend `/upload` endpoint.

## Repository

GitHub repository:

```text
https://github.com/Young265/fridge
```

Main branch:

```text
main
```

## Important Files

- `backend/app.py`
  - Flask backend.
  - Exposes `/upload`.
  - Stores recognized items in MySQL table `fridge_items`.

- `backend/pi_fridge_camera.py`
  - Raspberry Pi camera bridge.
  - Supports continuous camera mode and reed-switch-triggered mode.
  - In reed mode, waits for door open, starts the camera, uploads the first stable group of predictions, then stops the camera.
  - Uses YOLO detection boxes plus contour proposals so the ingredient does not need to fit inside a fixed center box.
  - Uses trusted detector labels directly for common foods such as apples and bananas.
  - Adds padding around the remaining candidate crops before running the grocery classifier.
  - Uses the old center crop only as a final fallback.
  - Configures the Pi and PC camera paths at the same `640x480`, `30 FPS` defaults.
  - Uploads the full frame and each recognized crop to the backend.

- `backend/requirements-pi.txt`
  - Minimal pip requirements for Raspberry Pi.

- `RASPBERRY_PI.md`
  - Raspberry Pi setup, test, continuous run, and optional systemd service instructions.

- `backend/runs/classify/grocery-classifier-public4/weights/best.pt`
  - Grocery classifier model used by the Pi bridge.

- `backend/yolov8n.pt`
  - Dynamic object detector used to propose crop boxes.

## Raspberry Pi Setup

On the Raspberry Pi:

```bash
git clone https://github.com/Young265/fridge.git
cd fridge
sudo apt update
sudo apt install -y python3-venv python3-opencv python3-picamera2 python3-gpiozero
python3 -m venv --system-site-packages .venv
source .venv/bin/activate
pip install -r backend/requirements-pi.txt
```

## Backend Requirement

The backend must be running somewhere reachable from the Pi:

```bash
cd backend
python app.py
```

The Pi should use the backend machine's LAN/Tailscale IP, not `127.0.0.1`, unless the backend is running on the Pi itself.

## Test Command

Run once:

```bash
source .venv/bin/activate
python backend/pi_fridge_camera.py \
  --backend-url http://BACKEND_IP:5000 \
  --once
```

Dry-run without uploading:

```bash
python backend/pi_fridge_camera.py --dry-run
```

Local preview with dynamic boxes:

```bash
python backend/classify_camera.py
```

In the preview, press `s` to upload recognized boxes and `q` to quit.

Useful tuning options:

```bash
python backend/pi_fridge_camera.py \
  --dry-run \
  --fps 30 \
  --detection-confidence 0.25 \
  --crop-padding-ratio 0.20 \
  --max-candidates 4
```

Continuous run:

```bash
BACKEND_URL=http://BACKEND_IP:5000 \
FRIDGE_ID=1 \
python backend/pi_fridge_camera.py
```

## Reed Switch Mode

Recommended wiring:

- Reed switch wire 1 -> Raspberry Pi `GND`
- Reed switch wire 2 -> `GPIO17`, physical pin 11
- Magnet close to reed switch when fridge door is closed

Default expected signal:

- door closed: GPIO low
- door open: GPIO high

One door-open event test:

```bash
BACKEND_URL=http://BACKEND_IP:5000 \
python backend/pi_fridge_camera.py \
  --trigger reed \
  --reed-pin 17 \
  --reed-open-level high \
  --once
```

Continuous reed mode:

```bash
BACKEND_URL=http://BACKEND_IP:5000 \
FRIDGE_ID=1 \
python backend/pi_fridge_camera.py \
  --trigger reed \
  --reed-pin 17 \
  --reed-open-level high
```

If the trigger is backwards, use:

```bash
--reed-open-level low
```

## Notes

- The local PC currently has IP `172.29.139.148` on the school network.
- The Raspberry Pi has a `192.168.x.x` address, so direct SSH from the PC may not work unless both devices are on the same network.
- If the networks stay separate, use GitHub as the transfer path or install Tailscale on both devices.
- Codex on the Raspberry Pi does not automatically know this chat history. Start Codex in the cloned repo and tell it to read `HANDOFF.md` and `RASPBERRY_PI.md`.
