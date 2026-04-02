#!/bin/bash
# install_service.sh
# Sets up the Collatz coordinator AND nightly uploader as systemd services.
# Run once with: bash install_service.sh
# Requires sudo.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
USERNAME="$(whoami)"
GUNICORN_PATH="$(which gunicorn 2>/dev/null || echo '')"
PYTHON_PATH="$(which python3)"

echo ""
echo "============================================================"
echo " Collatz Frontier — Service Installer"
echo "============================================================"
echo " User        : $USERNAME"
echo " Working dir : $SCRIPT_DIR"
echo " Gunicorn    : ${GUNICORN_PATH:-NOT FOUND}"
echo " Python      : $PYTHON_PATH"
echo ""

# ── Preflight checks ──────────────────────────────────────────
ERRORS=0

if [ -z "$GUNICORN_PATH" ]; then
    echo " ERROR: gunicorn not found. Run: pip install gunicorn"
    echo "        Then fix PATH (see docs) and re-run this script."
    ERRORS=1
fi

if [ ! -f "$SCRIPT_DIR/collatz_coordinator.py" ]; then
    echo " ERROR: collatz_coordinator.py not found in $SCRIPT_DIR"
    ERRORS=1
fi

if [ ! -f "$SCRIPT_DIR/collatz_upload_frontier.py" ]; then
    echo " WARNING: collatz_upload_frontier.py not found — uploader service will be skipped."
    INSTALL_UPLOADER=0
else
    INSTALL_UPLOADER=1
fi

[ $ERRORS -ne 0 ] && exit 1

# ── GitHub token (shared by both services) ────────────────────
echo ""
echo " How is HTTPS configured? (certbot must already be installed)"
echo "   1) No HTTPS — plain HTTP on port 5555 (default)"
echo "   2) Direct TLS — Gunicorn uses certbot certs directly (port 443)"
echo "   3) nginx reverse proxy — nginx handles TLS, forwards to port 5555"
read -p " Choose [1]: " HTTPS_MODE
HTTPS_MODE=${HTTPS_MODE:-1}

CERTFILE=""
KEYFILE=""
DOMAIN=""
BIND_ADDR="0.0.0.0:5555"
PROXY_ENV=""

if [ "$HTTPS_MODE" = "2" ]; then
    read -p " Domain name (e.g. collatz.example.com): " DOMAIN
    CERTFILE="/etc/letsencrypt/live/$DOMAIN/fullchain.pem"
    KEYFILE="/etc/letsencrypt/live/$DOMAIN/privkey.pem"
    if [ ! -f "$CERTFILE" ]; then
        echo " WARNING: $CERTFILE not found. Check your certbot domain name."
    fi
    BIND_ADDR="0.0.0.0:443"
    echo " Direct TLS configured on port 443."
elif [ "$HTTPS_MODE" = "3" ]; then
    read -p " Domain name (for banner display, e.g. collatz.example.com): " DOMAIN
    PROXY_ENV='Environment="COLLATZ_PROXY=1"'
    BIND_ADDR="127.0.0.1:5555"
    echo " nginx reverse proxy mode. Binding to 127.0.0.1:5555."
    echo " Make sure nginx is configured to proxy to http://127.0.0.1:5555"
    echo " with X-Forwarded-Proto and X-Forwarded-For headers."
fi
echo ""

# ── Write coordinator service ─────────────────────────────────
COORD_SERVICE="/etc/systemd/system/collatz.service"
echo " Writing $COORD_SERVICE ..."

# Build ExecStart based on HTTPS mode
if [ "$HTTPS_MODE" = "2" ] && [ -n "$CERTFILE" ]; then
    EXEC_START_LINES="$GUNICORN_PATH \\
          -w 1 \\
          --threads 32 \\
          --certfile $CERTFILE \\
          --keyfile $KEYFILE \\
          -b $BIND_ADDR \\
          collatz_coordinator:app"
else
    EXEC_START_LINES="$GUNICORN_PATH \\
          -w 1 \\
          --threads 32 \\
          -b $BIND_ADDR \\
          collatz_coordinator:app"
fi

sudo tee "$COORD_SERVICE" > /dev/null << EOF
[Unit]
Description=Collatz Frontier Coordinator
Documentation=https://github.com/huggablehacker/Collatz-Frontier
After=network.target
Wants=network-online.target

[Service]
User=$USERNAME
WorkingDirectory=$SCRIPT_DIR
ExecStart=$EXEC_START_LINES
Restart=always
RestartSec=5
TimeoutStartSec=30
TimeoutStopSec=30
KillMode=mixed
StandardOutput=journal
StandardError=journal
SyslogIdentifier=collatz
EOF

# Add HTTPS proxy env var for nginx mode
if [ -n "$PROXY_ENV" ]; then
    sudo sed -i "/SyslogIdentifier=collatz$/a $PROXY_ENV" "$COORD_SERVICE"
fi

# Add domain env var if provided
if [ -n "$DOMAIN" ]; then
    sudo sed -i "/SyslogIdentifier=collatz$/a Environment=\"COLLATZ_DOMAIN=$DOMAIN\"" "$COORD_SERVICE"
fi

# Add GitHub token if provided
if [ -n "$GH_TOKEN" ]; then
    sudo sed -i "/SyslogIdentifier=collatz$/a Environment=\"GITHUB_TOKEN=$GH_TOKEN\"" "$COORD_SERVICE"
fi

sudo bash -c "cat >> $COORD_SERVICE" << 'EOF'

[Install]
WantedBy=multi-user.target
EOF

echo " Coordinator service written."

# ── Write uploader service ────────────────────────────────────
if [ $INSTALL_UPLOADER -eq 1 ]; then
    UPLOAD_SERVICE="/etc/systemd/system/collatz-uploader.service"
    echo " Writing $UPLOAD_SERVICE ..."

    sudo tee "$UPLOAD_SERVICE" > /dev/null << EOF
[Unit]
Description=Collatz Frontier Nightly Uploader
Documentation=https://github.com/huggablehacker/Collatz-Frontier
After=network.target collatz.service
Wants=network-online.target

[Service]
User=$USERNAME
WorkingDirectory=$SCRIPT_DIR
ExecStart=$PYTHON_PATH $SCRIPT_DIR/collatz_upload_frontier.py
Restart=always
RestartSec=10
TimeoutStartSec=30
TimeoutStopSec=15
StandardOutput=journal
StandardError=journal
SyslogIdentifier=collatz-uploader
EOF

    # Add GitHub token to uploader — required for it to do anything
    if [ -n "$GH_TOKEN" ]; then
        sudo sed -i "/SyslogIdentifier=collatz-uploader$/a Environment=\"GITHUB_TOKEN=$GH_TOKEN\"" "$UPLOAD_SERVICE"
        echo " GitHub token added to uploader service."
    else
        echo " WARNING: No GitHub token set — uploader will log an error each night."
        echo "          Add it later by editing $UPLOAD_SERVICE and running:"
        echo "          sudo systemctl restart collatz-uploader"
    fi

    sudo bash -c "cat >> $UPLOAD_SERVICE" << 'EOF'

[Install]
WantedBy=multi-user.target
EOF

    echo " Uploader service written."
fi

# ── Enable and start everything ───────────────────────────────
echo ""
echo " Reloading systemd and starting services..."
sudo systemctl daemon-reload

sudo systemctl enable collatz
sudo systemctl restart collatz

if [ $INSTALL_UPLOADER -eq 1 ]; then
    sudo systemctl enable collatz-uploader
    sudo systemctl restart collatz-uploader
fi

sleep 3

# ── Status report ─────────────────────────────────────────────
COORD_STATUS=$(sudo systemctl is-active collatz 2>/dev/null || echo "failed")
UPLOAD_STATUS=""
[ $INSTALL_UPLOADER -eq 1 ] && UPLOAD_STATUS=$(sudo systemctl is-active collatz-uploader 2>/dev/null || echo "failed")

LOCAL_IP=$(hostname -I 2>/dev/null | awk '{print $1}' || echo "YOUR_IP")

echo ""
echo "============================================================"
echo " RESULTS"
echo "============================================================"
echo ""
echo " collatz (coordinator)  : $COORD_STATUS"
[ $INSTALL_UPLOADER -eq 1 ] && echo " collatz-uploader       : $UPLOAD_STATUS"
echo ""

if [ "$COORD_STATUS" = "active" ]; then
    if [ -n "$DOMAIN" ]; then
        SCHEME="https"
        DISPLAY_HOST="$DOMAIN"
    elif [ "$HTTPS_MODE" = "2" ]; then
        SCHEME="https"
        DISPLAY_HOST="$LOCAL_IP"
    else
        SCHEME="http"
        DISPLAY_HOST="$LOCAL_IP:5555"
    fi
    echo " Dashboard  : $SCHEME://$DISPLAY_HOST/status"
    echo " Workers    : $SCHEME://$DISPLAY_HOST/workers"
    echo " Milestones : $SCHEME://$DISPLAY_HOST/milestones"
    echo " Join (QR)  : $SCHEME://$DISPLAY_HOST/join"
fi

echo ""
echo " Both services will now:"
echo "   - Survive SSH disconnections"
echo "   - Auto-restart on crash (coordinator: 5s, uploader: 10s)"
echo "   - Start automatically on every reboot"
echo ""
echo "------------------------------------------------------------"
echo " Useful commands"
echo "------------------------------------------------------------"
echo ""
echo " Status:"
echo "   sudo systemctl status collatz"
[ $INSTALL_UPLOADER -eq 1 ] && echo "   sudo systemctl status collatz-uploader"
echo ""
echo " Live logs:"
echo "   journalctl -u collatz -f"
[ $INSTALL_UPLOADER -eq 1 ] && echo "   journalctl -u collatz-uploader -f"
echo ""
echo " Both logs together:"
[ $INSTALL_UPLOADER -eq 1 ] && echo "   journalctl -u collatz -u collatz-uploader -f"
echo ""
echo " Restart after updating a script:"
echo "   sudo systemctl restart collatz"
[ $INSTALL_UPLOADER -eq 1 ] && echo "   sudo systemctl restart collatz-uploader"
echo ""
echo " Trigger an upload right now (without waiting for 8pm):"
[ $INSTALL_UPLOADER -eq 1 ] && echo "   python3 $SCRIPT_DIR/collatz_upload_frontier.py --now"
echo ""
echo " Update GitHub token later:"
echo "   sudo systemctl edit collatz-uploader"
echo "   # Add: Environment=\"GITHUB_TOKEN=ghp_...\""
echo "   sudo systemctl restart collatz-uploader"
echo ""
echo "============================================================"
echo ""
