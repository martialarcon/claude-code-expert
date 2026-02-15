---
name: jetson-context
description: >
  Contexto técnico de Jetson Orin Nano para decisiones arquitectónicas.
  Usar antes de diseñar features, elegir dependencias, optimizar
  rendimiento, o tomar decisiones sobre uso de GPU/CUDA/TensorRT.
  Aplica a brainstorming, writing-plans, y cualquier decisión técnica.
user-invocable: false
---

# Jetson Orin Nano - Contexto Técnico

## Hardware

| Componente | Especificación |
|------------|---------------|
| CPU | 6-core ARM Cortex-A78AE (ARMv8.2) |
| GPU | 1024-core NVIDIA Ampere, CUDA Compute 8.7 |
| Memoria | 8GB LPDDR5 compartida CPU/GPU |
| Almacenamiento | microSD + NVMe SSD |
| Power | 15W nominal, 25W peak |
| Cooling | Pasivo (throttling ~60°C) |

## Software Stack

| Capa | Versión |
|------|---------|
| JetPack | 6.0+ |
| Ubuntu | 22.04 ARM64 |
| CUDA | 12.2+ (Jetson-specific) |
| cuDNN | 8.9+ |
| TensorRT | 8.6+ |
| OpenCV | 4.8+ con CUDA |
| GStreamer | 1.20+ |

## Patterns de Optimización

### Camera Pipeline (GStreamer)
```python
# CORRECTO - GStreamer acelerado
pipeline = (
    "nvarguscamerasrc sensor-id=0 ! "
    "video/x-raw(memory:NVMM), width=1920, height=1080, framerate=30/1 ! "
    "nvvidconv ! video/x-raw, format=BGRx ! "
    "videoconvert ! appsink"
)
cap = cv2.VideoCapture(pipeline, cv2.CAP_GSTREAMER)
```

### Image Processing (cv2.cuda)
```python
# CORRECTO - GPU CUDA
gpu_frame = cv2.cuda_GpuMat()
gpu_frame.upload(frame)
gpu_gray = cv2.cuda.cvtColor(gpu_frame, cv2.COLOR_BGR2GRAY)
```

### Inferencia (TensorRT)
```python
# CORRECTO - TensorRT optimizado FP16
from torch2trt import torch2trt
trt_model = torch2trt(model, [example_input], fp16_mode=True)
```

### Memory Management
```python
# CORRECTO - Reusar buffers
class FrameProcessor:
    def __init__(self):
        self.gpu_frame = cv2.cuda_GpuMat()  # Reusar, no recrear
```

## Restricciones

### Contenedor orquestador
- Sin GPU (NVIDIA_VISIBLE_DEVICES=none)
- Sin root, sin privilegios
- Solo escribe en /workspace

### Contenedor runtime
- Con GPU (runtime: nvidia)
- Cámara CSI (/dev/video0)
- CUDA + TensorRT

### Dependencias
- Solo wheels con soporte ARM64/aarch64
- Evitar PyTorch completo (usar torch2trt)
- Evitar TensorFlow >= 2.13
- Máximo razonable: ~500MB por dependencia

## Decisiones Pre-aprobadas (sin consultar)

1. Usar GStreamer para pipelines de cámara
2. Usar cv2.cuda para operaciones de imagen
3. Convertir modelos a TensorRT
4. Usar FP16 para inferencia
5. Implementar object pooling para buffers GPU
6. Logging estructurado JSON para métricas
7. Frame dropping si FPS < 30

## Decisiones que REQUIEREN consulta

1. Frameworks > 500MB
2. Cambios en arquitectura de contenedores
3. Exponer servicios en red
4. Acceso a hardware no especificado (I2C, GPIO)
5. Modificar políticas de seguridad
