#!/bin/bash
# Script de desinstalación
# Alejandro Paredero - alejandro.paredero@cunef.edu

echo "=============================================="
echo "  Desinstalador - Detector YOLO"
echo "=============================================="
echo ""

read -p "¿Deseas eliminar el entorno virtual y las dependencias? (s/n): " respuesta

if [ "$respuesta" = "s" ] || [ "$respuesta" = "S" ]; then
    echo "[INFO] Eliminando entorno virtual..."
    rm -rf venv
    echo "[INFO] Entorno virtual eliminado"
fi

echo ""
echo "[INFO] Limpiando caché de modelos YOLO..."
rm -rf ~/.yolo_opencv/

echo ""
echo "[INFO] Los archivos del proyecto no se han eliminado"
echo "[INFO] Puedes eliminarlos manualmente si lo deseas"
echo ""
echo "[OK] Desinstalación completada"
