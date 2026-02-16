# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **Claude Code configuration project** for Jetson Orin Nano development. It contains:
- Custom agents, skills, and hooks tailored for edge AI development
- Planning documents for "AI Architect v2" - an automated technical intelligence system

## Target Environment

| Component | Specification |
|-----------|---------------|
| Device | NVIDIA Jetson Orin Nano |
| Architecture | ARM64 (aarch64) |
| CPU | 6-core ARM Cortex-A78AE |
| GPU | 1024-core NVIDIA Ampere, CUDA 8.7 |
| Memory | 8GB LPDDR5 (shared CPU/GPU) |
| Software | JetPack 6.0+, Ubuntu 22.04, CUDA 12.2+, TensorRT 8.6+ |

## Skills

| Skill | Invocation | Purpose |
|-------|------------|---------|
| `runtime-test` | `/runtime-test <file.py>` | Execute Python in `project-runtime` container with GPU/CUDA access |
| `security-check` | `/security-check` | Validate security policies before commits/PRs |
| `jetson-context` | Automatic | Provides Jetson technical context for architectural decisions |

## Execution Model

**Two-container architecture:**
- `claude-orchestrator`: No GPU, read-only filesystem, no privileges (where Claude runs)
- `project-runtime`: Full GPU access via NVIDIA runtime, CSI camera, CUDA/TensorRT

**Code with GPU/CUDA/vision libraries must run in `project-runtime`:**
```bash
docker exec project-runtime python3 /workspace/<file>
```

The `block-host-python.sh` hook enforces this by blocking direct Python execution with cv2/cuda/torch imports.

## Optimization Patterns

**Camera (GStreamer required):**
```python
pipeline = (
    "nvarguscamerasrc sensor-id=0 ! "
    "video/x-raw(memory:NVMM), width=1920, height=1080, framerate=30/1 ! "
    "nvvidconv ! video/x-raw, format=BGRx ! "
    "videoconvert ! appsink"
)
cap = cv2.VideoCapture(pipeline, cv2.CAP_GSTREAMER)
```

**Image Processing (cv2.cuda):**
```python
gpu_frame = cv2.cuda_GpuMat()
gpu_frame.upload(frame)
gpu_gray = cv2.cuda.cvtColor(gpu_frame, cv2.COLOR_BGR2GRAY)
```

**Inference (TensorRT FP16):**
```python
from torch2trt import torch2trt
trt_model = torch2trt(model, [example_input], fp16_mode=True)
```

## Pre-Approved Decisions (no consultation needed)

1. GStreamer for camera pipelines
2. cv2.cuda for image operations
3. TensorRT model conversion
4. FP16 for inference
5. Object pooling for GPU buffers
6. Structured JSON logging for metrics
7. Frame dropping if FPS < 30

## Decisions Requiring User Consultation

1. Dependencies > 500MB
2. Container architecture changes
3. Network service exposure
4. Access to unspecified hardware (I2C, GPIO)
5. Security policy modifications

## Performance Thresholds

| Metric | OK | Warning | Critical |
|--------|-------|---------|----------|
| FPS | >=30 | 20-29 | <20 |
| GPU Memory | <=3GB | 3-4GB | >4GB |
| CPU | <=50% | 50-75% | >75% |
| Temperature | <=55C | 55-60C | >60C |

## AI Architect v2

The `docs/plans/` directory contains comprehensive planning for an automated technical intelligence system that collects, analyzes, and synthesizes information about Claude Code and AI-assisted development ecosystems. Key documents:
- `2026-02-14-ai-architect-design.md` - Initial v1 design
- `AI_Architect_v2_Marco_Estrategico.md` - Strategic framework
- `ai-architect-v2-planificacion-tecnica.md` - Technical planning (~105KB)
- `ai-architect-v2-arquitectura-subagentes.md` - Subagent architecture

Target: Sequential execution (8GB RAM constraint), zero API cost policy, ChromaDB + Markdown outputs.
