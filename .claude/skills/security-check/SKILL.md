---
name: security-check
description: >
  Valida políticas de seguridad del proyecto: no secrets hardcoded,
  contenedores sin root, dependencias ARM64 compatibles, Dockerfiles
  seguros. Usar antes de commits, PRs, o después de modificar
  Dockerfiles/docker-compose.
allowed-tools: Read, Grep, Glob, Bash
---

# Security Check

Validación de seguridad específica del proyecto Jetson.

## Proceso

### 1. Buscar secrets hardcoded
```bash
# Buscar en workspace/src/
grep -rn -E "(password|secret|api_key|token|credential)\s*[=:]\s*['\"][^'\"]+['\"]" workspace/src/ || echo "OK: No secrets encontrados"
```

### 2. Verificar Dockerfiles
Para cada Dockerfile, verificar:
- Que el usuario final NO sea root (debe tener `USER` con UID no-root)
- Que no instale herramientas innecesarias (curl, wget, ssh sin justificación)

### 3. Verificar docker-compose.yml
- `claude-orchestrator` debe tener:
  - `user: "1000:1000"` (o similar no-root)
  - `read_only: true`
  - `security_opt: [no-new-privileges:true]`
  - `cap_drop: [ALL]`
  - NO tener `runtime: nvidia` ni acceso a `/dev`
- `project-runtime` debe tener:
  - `runtime: nvidia`
  - Solo dispositivos justificados en `devices:`
  - NO tener acceso al Docker socket

### 4. Verificar requirements.txt / dependencias
- Listar dependencias y verificar que no sean solo x86_64
- Alertar si alguna dependencia conocida no tiene wheel ARM64

### 5. Reportar
```
Resultado /security-check:
- Secrets: OK / X encontrados
- Dockerfiles: OK / X problemas
- docker-compose.yml: OK / X problemas
- Dependencias ARM64: OK / X sin verificar
```
