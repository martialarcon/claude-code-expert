#!/usr/bin/env bash
# PostToolUse hook para Write|Edit: advierte cuando se modifican
# archivos Docker para recordar revisión de seguridad.

set -euo pipefail

INPUT=$(cat)
TOOL_INPUT=$(echo "$INPUT" | python3 -c "
import sys, json
data = json.load(sys.stdin)
path = data.get('tool_input', {}).get('file_path', '')
print(path)
" 2>/dev/null || echo "")

# Solo advertir para archivos Docker
if echo "$TOOL_INPUT" | grep -qiE "Dockerfile|docker-compose"; then
    echo '{"hookSpecificOutput":{"hookEventName":"PostToolUse","additionalContext":"RECORDATORIO: Se modificó un archivo Docker. Verificar: (1) No se usa root como usuario final (2) cap_drop: ALL está presente (3) no-new-privileges: true (4) Solo se exponen dispositivos necesarios. Ejecuta /security-check antes de continuar."}}'
    exit 0
fi

exit 0
