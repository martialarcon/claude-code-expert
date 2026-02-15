---
name: runtime-test
description: >
  Ejecuta código Python en el contenedor project-runtime con acceso a
  GPU/CUDA y reporta métricas de rendimiento Jetson. Usar cuando se
  necesite probar código de visión, inferencia, o procesamiento de
  video. Invocado con /runtime-test.
---

# Runtime Test

Ejecuta código del workspace en el contenedor `project-runtime` que tiene
acceso a GPU CUDA, cámara CSI, y TensorRT.

## Uso

```
/runtime-test src/camera_capture.py
/runtime-test src/speed_detector.py --benchmark
```

## Proceso

1. Verificar que el contenedor `project-runtime` está corriendo:
   ```bash
   docker ps --filter name=project-runtime --format "{{.Status}}"
   ```

2. Si no está corriendo, levantarlo:
   ```bash
   docker compose up -d project-runtime
   ```

3. Ejecutar el archivo en el contenedor:
   ```bash
   docker exec project-runtime python3 /workspace/<archivo>
   ```

4. Si se pide `--benchmark`, ejecutar con captura de métricas:
   ```bash
   docker exec project-runtime bash -c "
     python3 /workspace/<archivo> 2>&1
     echo '---METRICS---'
     python3 -c \"
import subprocess
result = subprocess.run(['tegrastats', '--interval', '100', '--count', '5'],
                       capture_output=True, text=True, timeout=10)
print(result.stdout)
\" 2>/dev/null || echo 'tegrastats no disponible'
   "
   ```

5. Reportar resultados al usuario con formato:
   ```
   Resultado de /runtime-test:
   - Archivo: <path>
   - Status: OK/ERROR
   - Output: <stdout>
   - Métricas (si benchmark):
     - FPS estimados
     - Uso GPU
     - Temperatura
   ```

## Importante
- NUNCA ejecutar el archivo directamente en el host
- Si el contenedor no existe, indicar al usuario que ejecute
  `docker compose up -d`
- Los archivos deben estar en /workspace/ para ser accesibles
