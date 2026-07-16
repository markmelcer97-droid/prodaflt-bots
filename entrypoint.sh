#!/bin/bash
set -e

# PRODAFLT — Fly.io Entrypoint
# Starts all 3 services in parallel within one container

echo "=========================================="
echo "PRODAFLT Starting on Fly.io"
echo "=========================================="

# Start FastAPI in background
uvicorn prodaflt.api.app.main:app --host 0.0.0.0 --port 8080 &
API_PID=$!
echo "[+] FastAPI started (PID $API_PID)"

# Start Parser Bot in background
python -m prodaflt.bots.parser.bot &
PARSER_PID=$!
echo "[+] Parser Bot started (PID $PARSER_PID)"

# Start Alert Engine in background
python -m prodaflt.bots.alert_engine.main &
ALERTS_PID=$!
echo "[+] Alert Engine started (PID $ALERTS_PID)"

# Health check loop
check_services() {
    while true; do
        sleep 30
        # Check if API is responding
        if ! curl -sf http://localhost:8080/health >/dev/null 2>&1; then
            echo "[!] API health check failed, restarting..."
            kill $API_PID 2>/dev/null || true
            uvicorn prodaflt.api.app.main:app --host 0.0.0.0 --port 8080 &
            API_PID=$!
        fi
        
        # Check if parser is running
        if ! kill -0 $PARSER_PID 2>/dev/null; then
            echo "[!] Parser Bot crashed, restarting..."
            python -m prodaflt.bots.parser.bot &
            PARSER_PID=$!
        fi
        
        # Check if alerts is running
        if ! kill -0 $ALERTS_PID 2>/dev/null; then
            echo "[!] Alert Engine crashed, restarting..."
            python -m prodaflt.bots.alert_engine.main &
            ALERTS_PID=$!
        fi
    done
}

# Start health check in background
check_services &
CHECK_PID=$!

# Wait for any child to exit
wait -n

# If we get here, something died — exit with error
echo "[!] A critical service exited. Shutting down."
kill $API_PID $PARSER_PID $ALERTS_PID $CHECK_PID 2>/dev/null || true
exit 1
