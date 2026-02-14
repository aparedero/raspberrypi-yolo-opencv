#!/bin/bash
# Script de ejecución rápida - Modo Headless (sin GUI)

echo "Iniciando detector YOLO (OpenCV DNN) en modo HEADLESS..."
echo "Presiona Ctrl+C para salir"
echo ""

# Activar entorno virtual
if [ -d "venv" ]; then
    source venv/bin/activate
    DISPLAY= python3 yolo_detector_opencv.py
    deactivate
else
    echo "[ERROR] No se encontró el entorno virtual"
    echo "Ejecuta primero: ./install.sh"
    exit 1
fi
