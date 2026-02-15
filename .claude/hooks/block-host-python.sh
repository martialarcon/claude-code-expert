#!/usr/bin/env bash
# PreToolUse hook para Bash: bloquea ejecución directa de Python con
# librerías de visión/CUDA en el host. Permite scripts auxiliares
# y comandos docker.

set -euo pipefail

INPUT=$(cat)
TOOL_NAME=$(echo "$INPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('tool_name',''))" 2>/dev/null || echo "")
COMMAND=$(echo "$INPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('tool_input',{}).get('command',''))" 2>/dev/null || echo "")

# Solo actuar en comandos Bash
if [ "$TOOL_NAME" != "Bash" ]; then
    exit 0
fi

# Permitir comandos docker (que es como se debe ejecutar el código)
if echo "$COMMAND" | grep -qE "^docker\b"; then
    exit 0
fi

# Permitir scripts de la carpeta .claude (hooks, validadores, etc.)
if echo "$COMMAND" | grep -qE "\.claude/"; then
    exit 0
fi

# Bloquear ejecución directa de Python con librerías de visión
if echo "$COMMAND" | grep -qE "python3?\s+.*\.(py)\b"; then
    # Verificar si usa librerías que requieren GPU
    if echo "$COMMAND" | grep -qiE "cv2|cuda|tensorrt|torch|opencv|gstreamer|jetson"; then
        echo '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"Código con GPU/visión debe ejecutarse en el contenedor project-runtime. Usa: docker exec project-runtime python3 /workspace/src/<archivo> o el skill /runtime-test"}}'
        exit 0
    fi
fi

# Permitir todo lo demás
exit 0
