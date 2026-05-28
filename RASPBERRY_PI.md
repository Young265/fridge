# Raspberry Pi camera bridge

This project already has a Flask backend endpoint at `/upload`. The Raspberry Pi only needs to run the camera bridge:

```bash
python backend/pi_fridge_camera.py --backend-url http://<PC_OR_SERVER_IP>:5000 --fridge-id <FRIDGE_ID>
```

It captures the camera image, classifies the center crop with the grocery classifier model, and uploads the full image plus crop to the backend. The backend writes the result to `fridge_items`.

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
sudo apt install -y python3-venv python3-opencv python3-picamera2
python3 -m venv --system-site-packages .venv
source .venv/bin/activate
pip install -r backend/requirements-pi.txt
```

Copy this project folder to the Pi, including:

- `backend/pi_fridge_camera.py`
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
python backend/pi_fridge_camera.py --min-confidence 0.75
```

## 4. Run continuously

```bash
BACKEND_URL=http://192.168.0.25:5000 \
FRIDGE_ID=1 \
python backend/pi_fridge_camera.py
```

Default behavior:

- reads a frame every 1 second
- waits for the same label 3 times in a row
- uploads recognized items only
- prevents repeat uploads with a 20 second cooldown

## 5. Optional systemd service

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

