#!/bin/bash
# Script para probar la cámara

echo "================================"
echo "  Prueba de Cámara Web"
echo "================================"
echo ""

# Verificar entorno virtual
if [ -d "venv" ]; then
    source venv/bin/activate
    python3 test_camera.py
    deactivate
else
    echo "[ERROR] No se encontró el entorno virtual"
    echo "Ejecuta primero: ./install.sh"
    exit 1
fi
