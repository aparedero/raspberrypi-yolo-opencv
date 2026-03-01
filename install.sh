#!/bin/bash
# Script de instalación para Raspberry Pi 4
# Detector de objetos YOLO con síntesis de voz
# Alejandro Paredero - alejandro.paredero@cunef.edu

echo "=============================================="
echo "  Instalador - Detector YOLO Raspberry Pi"
echo "=============================================="
echo ""

# Actualizar sistema
echo "[1/8] Actualizando sistema..."
sudo apt-get update

# Instalar dependencias del sistema
echo "[2/8] Instalando dependencias del sistema..."
sudo apt-get install -y python3-pip python3-dev python3-venv python3-full
sudo apt-get install -y libportaudio2 portaudio19-dev
sudo apt-get install -y espeak espeak-data
sudo apt-get install -y libatlas-base-dev libopenblas-dev gfortran
sudo apt-get install -y libhdf5-dev libhdf5-serial-dev
sudo apt-get install -y libharfbuzz0b libwebp6
sudo apt-get install -y libilmbase25 libopenexr25 libgstreamer1.0-0
sudo apt-get install -y python3-picamera2 2>/dev/null || true
sudo apt-get install -y rpicam-apps 2>/dev/null || true
sudo apt-get install -y gstreamer1.0-libcamera libcamera-apps 2>/dev/null || echo "libcamera/gstreamer plugin no disponible en este repositorio"
sudo apt-get install -y libavcodec-dev libavformat-dev libswscale-dev
sudo apt-get install -y libopencv-dev python3-opencv 2>/dev/null || echo "OpenCV desde apt no disponible, se instalará con pip"

# Crear entorno virtual
echo "[3/8] Creando entorno virtual Python..."
if [ -d "venv" ]; then
    echo "  Eliminando entorno virtual existente..."
    rm -rf venv
fi
python3 -m venv venv
echo "  Entorno virtual creado"

# Activar entorno virtual y actualizar pip
echo "[4/7] Actualizando pip en entorno virtual..."
source venv/bin/activate
pip install --upgrade pip

# Instalar dependencias Python en el entorno virtual
echo "[5/7] Instalando dependencias..."
pip install numpy opencv-python pyttsx3 pillow pyyaml requests psutil

# Dar permisos de ejecución
echo "[6/7] Configurando permisos..."
chmod +x yolo_detector_opencv.py
chmod +x run_gui.sh run_headless.sh test_camera.sh install.sh uninstall.sh

# Probar instalación
echo "[7/7] Verificando instalación..."
python3 -c "import cv2; print('OK OpenCV:', cv2.__version__)" 2>/dev/null || echo "ERROR OpenCV"
python3 -c "import pyttsx3; print('OK pyttsx3')" 2>/dev/null || echo "ERROR pyttsx3"
python3 -c "import numpy; print('OK NumPy')" 2>/dev/null || echo "ERROR NumPy"

# Desactivar entorno virtual
deactivate

echo ""
echo "=============================================="
echo "  Instalación completada"
echo "=============================================="
echo ""
echo "Para ejecutar el programa:"
echo "  Con GUI:         ./run_gui.sh"
echo "  Sin GUI (SSH):   ./run_headless.sh"
echo "  Prueba cámara:   ./test_camera.sh"
echo ""
echo "O manualmente:"
echo "  source venv/bin/activate"
echo "  python3 yolo_detector_opencv.py"
echo ""
echo "Para salir del programa:"
echo "  Con GUI:      Presiona 'q' o ESC"
echo "  Sin GUI:      Presiona Ctrl+C"
echo ""
