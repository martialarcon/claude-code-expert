#!/bin/bash
# AI Architect v2 - Monthly Cycle Runner
# Ejecuta el ciclo monthly a través de Docker

set -e

PROJECT_DIR="/home/jetson/developer/projects/claude-code-expert"
LOG_FILE="$PROJECT_DIR/logs/monthly-$(date +%Y-%m).log"
LOCKFILE="/tmp/ai-architect-monthly.lock"

# Crear directorio de logs si no existe
mkdir -p "$PROJECT_DIR/logs"

# Adquirir lock para prevenir ejecuciones paralelas
exec 200>"$LOCKFILE"
if ! flock -n 200; then
    echo "[$(date)] Another instance is already running, exiting." >> "$LOG_FILE"
    exit 0
fi

echo $$ > "$LOCKFILE"

cd "$PROJECT_DIR"

# Verificar si el contenedor ya está corriendo y saludable
if docker compose ps app 2>/dev/null | grep -q "Up.*healthy"; then
    echo "[$(date)] Container already running and healthy" >> "$LOG_FILE"
else
    echo "[$(date)] Starting container..." >> "$LOG_FILE"
    docker compose up -d --no-build
    sleep 5
fi

# Ejecutar ciclo monthly
echo "=== AI Architect Monthly Cycle - $(date) ===" >> "$LOG_FILE"
docker compose exec -T app python main.py --mode monthly 2>&1 | tee -a "$LOG_FILE"

echo "=== Completed at $(date) ===" >> "$LOG_FILE"
