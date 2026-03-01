#!/bin/bash
# Script para probar la cámara
# Alejandro Paredero - alejandro.paredero@cunef.edu

set -e

# Si se ejecuta con sudo, re-ejecutar como usuario normal para usar su venv y DISPLAY
if [ "${EUID}" -eq 0 ] && [ -n "${SUDO_USER}" ]; then
    echo "[WARN] No es necesario usar sudo. Re-ejecutando como ${SUDO_USER}..."
    exec sudo -u "${SUDO_USER}" DISPLAY="${DISPLAY:-:0}" XAUTHORITY="${XAUTHORITY:-/home/${SUDO_USER}/.Xauthority}" bash "$(readlink -f "$0")" "$@"
fi

cd "$(dirname "$0")"

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
