# Fridge Project Handoff

## Current Goal

Use Raspberry Pi 5 as the camera bridge for the fridge app:

1. Turn on the camera.
2. Read/classify the ingredient in front of the camera.
3. Send the image, crop, label, and confidence to the backend database through the backend `/upload` endpoint.

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
  - Captures a frame.
  - Center-crops the image.
  - Runs the YOLO grocery classifier.
  - Uploads the full frame and crop to the backend.

- `backend/requirements-pi.txt`
  - Minimal pip requirements for Raspberry Pi.

- `RASPBERRY_PI.md`
  - Raspberry Pi setup, test, continuous run, and optional systemd service instructions.

- `backend/runs/classify/grocery-classifier-public4/weights/best.pt`
  - Grocery classifier model used by the Pi bridge.

## Raspberry Pi Setup

On the Raspberry Pi:

```bash
git clone https://github.com/Young265/fridge.git
cd fridge
sudo apt update
sudo apt install -y python3-venv python3-opencv python3-picamera2
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

Continuous run:

```bash
BACKEND_URL=http://BACKEND_IP:5000 \
FRIDGE_ID=1 \
python backend/pi_fridge_camera.py
```

## Notes

- The local PC currently has IP `172.29.139.148` on the school network.
- The Raspberry Pi has a `192.168.x.x` address, so direct SSH from the PC may not work unless both devices are on the same network.
- If the networks stay separate, use GitHub as the transfer path or install Tailscale on both devices.
- Codex on the Raspberry Pi does not automatically know this chat history. Start Codex in the cloned repo and tell it to read `HANDOFF.md` and `RASPBERRY_PI.md`.

