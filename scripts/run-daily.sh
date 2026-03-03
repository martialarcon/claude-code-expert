#!/bin/bash
# AI Architect v2 - Daily Cycle Runner
# Ejecuta el ciclo daily a través de Docker

set -e

PROJECT_DIR="/home/jetson/developer/projects/claude-code-expert"
LOG_FILE="$PROJECT_DIR/logs/daily-$(date +%Y-%m-%d).log"
LOCKFILE="/tmp/ai-architect-daily.lock"

# Crear directorio de logs si no existe
mkdir -p "$PROJECT_DIR/logs"

# Adquirir lock para prevenir ejecuciones paralelas (timeout 5 segundos)
exec 200>"$LOCKFILE"
if ! flock -n 200; then
    echo "[$(date)] Another instance is already running, exiting." >> "$LOG_FILE"
    exit 0
fi

# Guardar PID en el lockfile
echo $$ > "$LOCKFILE"

cd "$PROJECT_DIR"

# Verificar si el contenedor ya está corriendo y saludable
if docker compose ps app 2>/dev/null | grep -q "Up.*healthy"; then
    echo "[$(date)] Container already running and healthy" >> "$LOG_FILE"
else
    # Iniciar contenedor SIN reconstruir (--no-build previene reconstrucciones accidentales)
    echo "[$(date)] Starting container..." >> "$LOG_FILE"
    docker compose up -d --no-build

    # Esperar a que esté listo
    sleep 5
fi

# Ejecutar ciclo daily
echo "=== AI Architect Daily Cycle - $(date) ===" >> "$LOG_FILE"
docker compose exec -T app python main.py --mode daily 2>&1 | tee -a "$LOG_FILE"

echo "=== Completed at $(date) ===" >> "$LOG_FILE"

# Lock se libera automáticamente al terminar
