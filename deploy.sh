#!/usr/bin/env bash
set -e

echo "=== Pulling latest changes from GitHub ==="
git pull origin main

if command -v docker &> /dev/null && command -v docker-compose &> /dev/null || docker compose version &> /dev/null; then
    echo "=== Deploying with Docker Compose ==="
    if docker compose version &> /dev/null; then
        docker compose up -d --build
    else
        docker-compose up -d --build
    fi
    echo "=== Deployment Complete! Container status: ==="
    docker ps | grep job_crawler
else
    echo "=== Docker not found, falling back to local Python venv ==="
    if [ ! -d ".venv" ]; then
        python3 -m venv .venv
    fi
    source .venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
    playwright install --with-deps chromium
    echo "Restarting service if systemd unit exists..."
    sudo systemctl restart job_crawler || echo "Please start manually or configure systemd service."
fi
