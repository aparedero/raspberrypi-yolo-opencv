#!/bin/bash
# Script de ejecución rápida - Modo GUI

echo "Iniciando detector YOLO (OpenCV DNN) en modo GUI..."
echo "Presiona 'q' en la ventana para salir"
echo ""

# Activar entorno virtual
if [ -d "venv" ]; then
    source venv/bin/activate
    python3 yolo_detector_opencv.py
    deactivate
else
    echo "[ERROR] No se encontró el entorno virtual"
    echo "Ejecuta primero: ./install.sh"
    exit 1
fi
