#!/bin/bash
# AI Architect v2 - Monthly Cycle Runner
# Ejecuta el ciclo monthly a través de Docker

set -e

PROJECT_DIR="/home/jetson/developer/projects/claude-code-expert"
LOG_FILE="$PROJECT_DIR/logs/monthly-$(date +%Y-%m).log"

# Crear directorio de logs si no existe
mkdir -p "$PROJECT_DIR/logs"

cd "$PROJECT_DIR"

# Asegurar que el contenedor está corriendo
docker compose up -d

# Esperar a que esté listo
sleep 5

# Ejecutar ciclo monthly
echo "=== AI Architect Monthly Cycle - $(date) ===" >> "$LOG_FILE"
docker compose exec -T app python main.py --mode monthly 2>&1 | tee -a "$LOG_FILE"

echo "=== Completed at $(date) ===" >> "$LOG_FILE"
