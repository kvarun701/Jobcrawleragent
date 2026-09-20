#!/bin/bash
# Script to launch Streamlit and create a free Cloudflare Tunnel

echo "🚀 Starting Job Crawler with Public Cloudflare Tunnel..."

# Locate streamlit executable
if [ -f "./venv/bin/streamlit" ]; then
    STREAMLIT_BIN="./venv/bin/streamlit"
else
    STREAMLIT_BIN="streamlit"
fi

# Check if port 8501 is already running
if ! lsof -i :8501 > /dev/null 2>&1; then
    echo "▶️ Launching Streamlit on port 8501..."
    $STREAMLIT_BIN run app.py --server.headless true --server.port 8501 &
    STREAMLIT_PID=$!
    trap "kill $STREAMLIT_PID 2>/dev/null; exit" INT TERM EXIT
    sleep 3
else
    echo "✅ Streamlit is already running on port 8501."
fi

echo "🌐 Connecting to Cloudflare using HTTP/2 protocol (avoids UDP/QUIC ISP block)..."
echo "Look for the https://*.trycloudflare.com link below:"
echo "--------------------------------------------------------"

cloudflared tunnel --protocol http2 --url http://localhost:8501
