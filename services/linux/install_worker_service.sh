#!/bin/bash
# install_worker_service.sh
# Sets up the Collatz worker as a headless systemd service.
#
# Run on any machine you want to contribute compute:
#   bash install_worker_service.sh
#
# Requires sudo. Python 3.8+ and the requests package must be installed.
# To run MULTIPLE workers on one machine, answer yes when prompted.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
USERNAME="$(whoami)"
PYTHON_PATH="$(which python3)"
CPU_COUNT=$(python3 -c "import multiprocessing; print(multiprocessing.cpu_count())" 2>/dev/null || echo "?")

echo ""
echo "============================================================"
echo " Collatz Frontier — Worker Service Installer"
echo "============================================================"
echo " User        : $USERNAME"
echo " Working dir : $SCRIPT_DIR"
echo " Python      : $PYTHON_PATH"
echo " CPU cores   : $CPU_COUNT"
echo ""

# ── Preflight checks ──────────────────────────────────────────
if [ ! -f "$SCRIPT_DIR/collatz_worker.py" ]; then
    echo " ERROR: collatz_worker.py not found in $SCRIPT_DIR"
    echo " Run this script from the same folder as collatz_worker.py"
    exit 1
fi

python3 -c "import requests" 2>/dev/null || {
    echo " ERROR: requests package not installed."
    echo " Run: pip install requests"
    exit 1
}

# ── Get coordinator URL ───────────────────────────────────────
echo ""
read -p " Coordinator IP address (e.g. 192.168.1.100): " COORD_IP

if [ -z "$COORD_IP" ]; then
    echo " ERROR: Coordinator IP is required."
    exit 1
fi

COORDINATOR="http://$COORD_IP:5555"

# Test connectivity
echo ""
echo " Testing connection to $COORDINATOR ..."
if curl -sf "$COORDINATOR/status" > /dev/null 2>&1; then
    echo " Coordinator reachable."
else
    echo " WARNING: Could not reach $COORDINATOR right now."
    echo " The service will keep retrying — this is fine if the"
    echo " coordinator is not running yet."
fi

# ── Worker name ───────────────────────────────────────────────
HOSTNAME_DEFAULT=$(hostname)
echo ""
read -p " Worker name [$HOSTNAME_DEFAULT]: " WORKER_NAME
[ -z "$WORKER_NAME" ] && WORKER_NAME="$HOSTNAME_DEFAULT"

# ── Core count ────────────────────────────────────────────────
echo ""
read -p " CPU cores to use [$CPU_COUNT / all, enter 0 for all]: " CORES
[ -z "$CORES" ] && CORES=0

# ── Multiple workers on one machine? ─────────────────────────
echo ""
read -p " Run multiple workers on this machine? (y/N): " MULTI
MULTI=$(echo "$MULTI" | tr '[:upper:]' '[:lower:]')

if [ "$MULTI" = "y" ] || [ "$MULTI" = "yes" ]; then
    echo ""
    read -p " How many worker services? [2]: " NUM_WORKERS
    [ -z "$NUM_WORKERS" ] && NUM_WORKERS=2

    # Split cores evenly if using all
    if [ "$CORES" = "0" ] && [ "$CPU_COUNT" != "?" ]; then
        CORES_EACH=$(( CPU_COUNT / NUM_WORKERS ))
        [ "$CORES_EACH" -lt 1 ] && CORES_EACH=1
        echo " Assigning $CORES_EACH cores per worker."
    else
        CORES_EACH=$CORES
    fi
else
    NUM_WORKERS=1
    CORES_EACH=$CORES
fi

# ── Write and install service(s) ──────────────────────────────
echo ""
INSTALLED=()

for i in $(seq 1 $NUM_WORKERS); do
    if [ "$NUM_WORKERS" -gt 1 ]; then
        SVC_NAME="collatz-worker-$i"
        W_NAME="${WORKER_NAME}-$i"
        SVC_DESC="Collatz Frontier Worker $i"
    else
        SVC_NAME="collatz-worker"
        W_NAME="$WORKER_NAME"
        SVC_DESC="Collatz Frontier Worker"
    fi

    SVC_FILE="/etc/systemd/system/${SVC_NAME}.service"
    echo " Writing $SVC_FILE ..."

    sudo tee "$SVC_FILE" > /dev/null << EOF
[Unit]
Description=$SVC_DESC
Documentation=https://github.com/huggablehacker/Collatz-Frontier
After=network.target network-online.target
Wants=network-online.target
StartLimitIntervalSec=0

[Service]
User=$USERNAME
WorkingDirectory=$SCRIPT_DIR
Environment="COLLATZ_COORDINATOR=$COORDINATOR"
Environment="COLLATZ_WORKER_NAME=$W_NAME"
Environment="COLLATZ_CORES=$CORES_EACH"
ExecStart=/bin/bash -c '\
  CORES=\${COLLATZ_CORES:-0}; \
  CORE_ARG=""; \
  [ "\$CORES" != "0" ] && CORE_ARG="--cores \$CORES"; \
  exec $PYTHON_PATH $SCRIPT_DIR/collatz_worker.py \
    --coordinator "\$COLLATZ_COORDINATOR" \
    --name "\$COLLATZ_WORKER_NAME" \
    \$CORE_ARG'
Restart=always
RestartSec=10
TimeoutStopSec=60
KillMode=mixed
KillSignal=SIGTERM
StandardOutput=journal
StandardError=journal
SyslogIdentifier=$SVC_NAME

[Install]
WantedBy=multi-user.target
EOF

    sudo systemctl daemon-reload
    sudo systemctl enable "$SVC_NAME"
    sudo systemctl restart "$SVC_NAME"
    INSTALLED+=("$SVC_NAME")
done

# ── Wait and check ────────────────────────────────────────────
sleep 3

echo ""
echo "============================================================"
echo " RESULTS"
echo "============================================================"
echo ""

ALL_OK=1
for SVC in "${INSTALLED[@]}"; do
    STATUS=$(sudo systemctl is-active "$SVC" 2>/dev/null || echo "failed")
    echo " $SVC : $STATUS"
    [ "$STATUS" != "active" ] && ALL_OK=0
done

echo ""
if [ $ALL_OK -eq 1 ]; then
    echo " All worker(s) running."
else
    echo " One or more workers failed to start."
    echo " Check logs: journalctl -u ${INSTALLED[0]} -n 30"
fi

echo ""
echo "------------------------------------------------------------"
echo " Useful commands"
echo "------------------------------------------------------------"
echo ""

for SVC in "${INSTALLED[@]}"; do
    echo " Status : sudo systemctl status $SVC"
done
echo ""
for SVC in "${INSTALLED[@]}"; do
    echo " Logs   : journalctl -u $SVC -f"
done

if [ "${#INSTALLED[@]}" -gt 1 ]; then
    echo ""
    echo " All logs together:"
    UNITS=$(printf -- "-u %s " "${INSTALLED[@]}")
    echo "   journalctl $UNITS -f"
fi

echo ""
echo " Restart a worker:"
echo "   sudo systemctl restart ${INSTALLED[0]}"
echo ""
echo " Stop all workers:"
for SVC in "${INSTALLED[@]}"; do
    echo "   sudo systemctl stop $SVC"
done
echo ""
echo " Change coordinator URL later:"
echo "   sudo systemctl edit ${INSTALLED[0]}"
echo "   # Add: [Service]"
echo "   # Environment=\"COLLATZ_COORDINATOR=http://NEW_IP:5555\""
echo "   sudo systemctl restart ${INSTALLED[0]}"
echo ""
echo "============================================================"
echo ""
echo " Workers will now:"
echo "   - Survive SSH disconnections"
echo "   - Auto-reconnect if the coordinator restarts (after 10s)"
echo "   - Start automatically on every reboot"
echo "   - Restart automatically if the process crashes"
echo ""
