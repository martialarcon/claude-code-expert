# Pruebas de Notificaciones - AI Architect v2

Este documento describe cómo probar y usar el sistema de notificaciones basado en **ntfy.sh**.

## Índice
1. [Resumen rápido](#resumen-rápido)
2. [Configuración](#configuración)
3. [Suscripción a notificaciones](#suscripción-a-notificaciones)
4. [Tipos de notificaciones](#tipos-de-notificaciones)
5. [Script de prueba](#script-de-prueba)
6. [Ejemplos de uso](#ejemplos-de-uso)
7. [Solución de problemas](#solución-de-problemas)

---

## Resumen rápido

El sistema de notificaciones envía mensajes a **ntfy.sh** (servicio gratuito, sin dependencias, push nativo):

```bash
# Ver configuración
python scripts/test_notifications.py --config

# Enviar notificación de prueba
python scripts/test_notifications.py --test daily

# Enviar mensaje personalizado
python scripts/test_notifications.py --send "Mi mensaje"
```

---

## Configuración

### Archivo de configuración: `config.yaml`

```yaml
notifications:
  ntfy:
    enabled: true              # Habilitar/deshabilitar notificaciones
    topic: "ai-architect"      # Nombre del topic (canal)
    url: "https://ntfy.sh"     # URL del servidor ntfy.sh
```

### Variables de entorno (opcional)

Puedes sobrescribir el topic usando:

```bash
export NTFY_TOPIC="mi-topic-personalizado"
python scripts/test_notifications.py --config
```

---

## Suscripción a notificaciones

### Opción 1: Web UI (Recomendado para pruebas rápidas)

1. Abre en tu navegador:
   ```
   https://ntfy.sh/ai-architect
   ```

2. Verás las notificaciones en tiempo real mientras las envías

3. Puedes copiar la URL para compartir con otros

### Opción 2: Aplicación móvil (Push nativo)

**iOS:**
- Descarga "ntfy" en App Store
- Abre la app y haz clic en "+"
- Ingresa: `ai-architect`
- Recibe notificaciones push en tu teléfono

**Android:**
- Descarga "ntfy" en Google Play
- Abre la app y haz clic en "+"
- Ingresa: `ai-architect`
- Recibe notificaciones push en tu teléfono

### Opción 3: Terminal (curl)

```bash
# Suscribirse y escuchar en tiempo real
curl -s https://ntfy.sh/ai-architect/sse

# En otra terminal, enviar:
curl -X POST -H "Title: Test" https://ntfy.sh/ai-architect -d "Hola!"
```

### Opción 4: Webhook/Integración programática

```python
import httpx

# Escuchar notificaciones via webhook
response = httpx.get("https://ntfy.sh/ai-architect/json", stream=True)
for line in response.iter_lines():
    print(line)
```

---

## Tipos de notificaciones

El sistema envía **7 tipos de notificaciones automáticas**:

### 1. Ciclo diario completado ✅

**Cuándo:** Después de un ciclo diario exitoso

**Ejemplo:**
```
✅ Daily cycle complete
Items: 42 analyzed, 15 discarded
Relevance: 8/10
Highlight: New test notification system
```

**Cómo probar:**
```bash
python scripts/test_notifications.py --test daily
```

---

### 2. Ciclo diario con errores ⚠️

**Cuándo:** Ciclo diario completado pero con fallos en colectores

**Ejemplo:**
```
⚠️ Daily cycle with errors
Items: 35 analyzed
Errors in: github, arxiv
```

**Cómo probar:**
```bash
python scripts/test_notifications.py --test errors
```

---

### 3. Ciclo completamente fallido 🔴

**Cuándo:** Error crítico que detiene la ejecución

**Ejemplo:**
```
🔴 Connection timeout to API
```

**Prioridad:** URGENT (máxima)

**Cómo probar:**
```bash
python scripts/test_notifications.py --test failed
```

---

### 4. Síntesis semanal 📊

**Cuándo:** Fin del ciclo semanal

**Ejemplo:**
```
📊 Weekly synthesis
Relevance: 7/10

Patterns:
- Increased AI adoption in enterprise
- New CUDA optimization techniques
- Edge AI acceleration frameworks
```

**Cómo probar:**
```bash
python scripts/test_notifications.py --test weekly
```

---

### 5. Reporte mensual 📈

**Cuándo:** Fin del ciclo mensual

**Ejemplo:**
```
📈 Monthly report
Relevance: 8/10
```

**Cómo probar:**
```bash
python scripts/test_notifications.py --test monthly
```

---

### 6. Señal crítica detectada 🚨

**Cuándo:** Item detectado con signal_score = 10 (máximo relevancia)

**Ejemplo:**
```
🚨 Revolutionary AI Architecture Announced
GitHub — https://github.com/example/repo
```

**Prioridad:** HIGH

**Cómo probar:**
```bash
python scripts/test_notifications.py --test critical
```

---

### 7. Mensaje personalizado

**Cuándo:** Envío manual de notificaciones

**Ejemplo:**
```bash
python scripts/test_notifications.py --send "Mi mensaje personalizado"
```

---

## Script de prueba

Ubicación: `scripts/test_notifications.py`

### Ayuda del script

```bash
python scripts/test_notifications.py --help
```

### Sintaxis general

```bash
python scripts/test_notifications.py [OPCIÓN]
```

### Opciones disponibles

| Opción | Descripción |
|--------|------------|
| `--config` | Mostrar configuración actual |
| `--test daily` | Enviar notificación de ciclo diario |
| `--test errors` | Enviar notificación de errores |
| `--test failed` | Enviar notificación de fallo crítico |
| `--test weekly` | Enviar notificación de síntesis semanal |
| `--test monthly` | Enviar notificación de reporte mensual |
| `--test critical` | Enviar notificación de señal crítica |
| `--send "MENSAJE"` | Enviar mensaje personalizado |
| `--title "TÍTULO"` | Título para mensaje personalizado |
| `--priority [default\|low\|high\|urgent]` | Prioridad del mensaje |

---

## Ejemplos de uso

### Paso 1: Verificar configuración

```bash
$ python scripts/test_notifications.py --config

📋 Notification Configuration:
   Topic: ai-architect
   Base URL: https://ntfy.sh
   Enabled: True

📲 Subscribe to notifications at:
   https://ntfy.sh/ai-architect
```

### Paso 2: Abrir la web UI

Abre en tu navegador:
```
https://ntfy.sh/ai-architect
```

### Paso 3: Enviar notificaciones de prueba

En otra terminal:

```bash
# Notificación de ciclo completado
python scripts/test_notifications.py --test daily

# Notificación de errores
python scripts/test_notifications.py --test errors

# Mensaje personalizado con alta prioridad
python scripts/test_notifications.py --send "Sistema completó análisis" --priority high
```

### Paso 4: Ver notificaciones

Las notificaciones aparecerán instantáneamente en:
- Web UI: https://ntfy.sh/ai-architect
- Aplicación móvil (si tienes notificaciones push activas)
- Curl: `curl -s https://ntfy.sh/ai-architect/sse`

---

## Ejemplos avanzados

### Enviar notificación con título personalizado

```bash
python scripts/test_notifications.py \
  --send "Análisis completado con 42 items nuevos" \
  --title "AI Architect - 2026-02-18" \
  --priority high
```

### Usar en scripts automatizados

```bash
#!/bin/bash

# Ejecutar ciclo diario
python main.py --mode daily

# Enviar notificación manual si necesario
if [ $? -eq 0 ]; then
  python scripts/test_notifications.py --test daily
else
  python scripts/test_notifications.py --test failed
fi
```

### Enviar desde Python

```python
from src.utils.notifier import get_notifier

notifier = get_notifier()

# Notificación simple
notifier.send(
    message="Procesamiento completado",
    title="AI Architect",
    priority="high"
)

# Notificación con tags y URL clickeable
notifier.send(
    message="Ver análisis completo",
    title="Nuevo reporte disponible",
    tags=["star", "robot"],
    click_url="https://github.com/..."
)
```

---

## Configuración avanzada

### Cambiar topic (canal)

Editar `config.yaml`:

```yaml
notifications:
  ntfy:
    enabled: true
    topic: "mi-proyecto-especial"  # Cambiar este valor
    url: "https://ntfy.sh"
```

### Deshabilitar notificaciones temporalmente

```yaml
notifications:
  ntfy:
    enabled: false  # Cambiar a false
    topic: "ai-architect"
    url: "https://ntfy.sh"
```

### Usar servidor ntfy.sh auto-alojado

```yaml
notifications:
  ntfy:
    enabled: true
    topic: "ai-architect"
    url: "https://tu-servidor-ntfy.sh"  # Cambiar URL
```

---

## Solución de problemas

### Error: "notifications_disabled"

**Causa:** Las notificaciones están deshabilitadas en `config.yaml`

**Solución:**
```yaml
notifications:
  ntfy:
    enabled: true  # Debe ser true
```

---

### Error: "ModuleNotFoundError: No module named 'httpx'"

**Causa:** Dependencias no instaladas

**Solución:**
```bash
pip install httpx pydantic pydantic-settings python-dotenv structlog pyyaml
```

---

### Error: "Connection timeout" o "403 Forbidden"

**Causa:**
- Sin conexión a internet o ntfy.sh no disponible
- Proxy en la red bloqueando el acceso a ntfy.sh
- Cortafuegos impide conexión a ntfy.sh:443

**Solución:**
1. Verificar conexión: `ping ntfy.sh`
2. Verificar firewall permite conexión a ntfy.sh:443
3. Intentar con curl: `curl -I https://ntfy.sh`
4. Si ves error `403 Forbidden` con `host_not_allowed`:
   - El proxy de tu red no permite acceso a ntfy.sh
   - Contacta al administrador de red para añadir ntfy.sh a la whitelist
   - Alternativa: Usa un servidor ntfy auto-alojado en tu red privada

---

### No recibo notificaciones en la web UI

**Solución:**
1. Asegúrate de haber abierto: `https://ntfy.sh/ai-architect`
2. Actualiza la página (F5)
3. Abre en pestaña privada si tienes problemas de caché
4. Verifica que el topic sea el correcto

---

### Las notificaciones no llegan a mi teléfono

**Para iOS:**
1. App ntfy instalada
2. Añadiste el topic `ai-architect`
3. Notificaciones habilitadas en ajustes iOS
4. WiFi/datos habilitados

**Para Android:**
1. App ntfy instalada
2. Añadiste el topic `ai-architect`
3. Notificaciones habilitadas en ajustes Android
4. WiFi/datos habilitados
5. App ntfy tiene permisos de notificación

---

### ¿Cuáles son los límites de ntfy.sh?

ntfy.sh es **100% gratuito y sin límites prácticos**:

- ✅ Sin límite de notificaciones
- ✅ Sin límite de suscriptores
- ✅ Sin límite de tópics
- ✅ Sin registro requerido
- ✅ Gratis para siempre
- ✅ Open source (puedes auto-alojarlo)

---

## Integración con cron jobs

El proyecto ejecuta ciclos automáticos vía cron. Las notificaciones se envían automáticamente:

**Daily (00:00 medianoche):**
```bash
0 0 * * * cd /home/user/claude-code-expert && python main.py --mode daily
```

**Weekly (lunes 01:00):**
```bash
0 1 * * 1 cd /home/user/claude-code-expert && python main.py --mode weekly
```

**Monthly (1º del mes 02:00):**
```bash
0 2 1 * * cd /home/user/claude-code-expert && python main.py --mode monthly
```

Después de cada ejecución, el sistema envía automáticamente notificaciones.

---

## Referencias

- **ntfy.sh Official:** https://ntfy.sh
- **Documentación ntfy:** https://docs.ntfy.sh
- **GitHub ntfy:** https://github.com/binwiederhake/ntfy
- **API Reference:** https://docs.ntfy.sh/publish

---

## Soporte

Para problemas o preguntas:
1. Verifica la sección [Solución de problemas](#solución-de-problemas)
2. Revisa los logs: `tail -f /var/log/ai-architect/*.log`
3. Consulta: https://github.com/anthropics/claude-code/issues
