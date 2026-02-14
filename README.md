# Detector de Objetos YOLO para Raspberry Pi 4

Sistema de detección de objetos en tiempo real usando YOLO con síntesis de voz en español para Raspberry Pi 4.

## Tecnología

- OpenCV DNN con YOLOv4-tiny
- Arquitectura ARM64 de Raspberry Pi 4
- Rendimiento optimizado sobre implementaciones alternativas
- Compatibilidad con Python 3.7 a 3.13

---

## Características

- Detección de objetos en tiempo real mediante YOLO v4-tiny
- Síntesis de voz en español mediante pyttsx3/espeak
- Sistema de traducción de etiquetas COCO al español
- Modos de operación GUI y headless
- Detección automática de dispositivos de captura con sistema de reintentos
- Implementación optimizada para hardware Raspberry Pi 4
- Dependencias mínimas basadas en OpenCV

## Requisitos del Sistema

- Raspberry Pi 4 con 4GB u 8GB de RAM
- Raspberry Pi OS de 32 o 64 bits
- Python 3.7 o versiones posteriores
- Dispositivo de captura USB compatible con V4L2
- Sistema de salida de audio (altavoces o auriculares)

## Instalación

Existen dos métodos de instalación disponibles:

### Instalación Automática con `install.sh`

El proyecto incluye un script de instalación que automatiza el proceso completo:

```bash
chmod +x install.sh
./install.sh
```

Este script realiza las siguientes operaciones:
- Actualización del sistema
- Instalación de dependencias del sistema
- Creación de entorno virtual Python (`venv`)
- Instalación de dependencias de Python mediante pip
- Configuración de permisos de ejecución
- Verificación de la instalación

### Instalación Manual

Para instalaciones personalizadas o cuando se requiere control sobre cada paso:

1. Actualizar el sistema:
```bash
sudo apt-get update
sudo apt-get upgrade
```

2. Instalar dependencias del sistema:
```bash
sudo apt-get install -y python3-pip python3-dev python3-venv python3-full
sudo apt-get install -y libportaudio2 portaudio19-dev
sudo apt-get install -y espeak espeak-data
sudo apt-get install -y libatlas-base-dev libopenblas-dev
sudo apt-get install -y libavcodec-dev libavformat-dev libswscale-dev
```

3. Crear entorno virtual:
```bash
python3 -m venv venv
source venv/bin/activate
```

4. Instalar dependencias de Python:
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

5. Asignar permisos de ejecución:
```bash
chmod +x yolo_detector_opencv.py
```

## Uso

### Modo GUI (Con Interfaz Gráfica)

Ejecución mediante script:

```bash
./run_gui.sh
```

Alternativamente, activando el entorno virtual:

```bash
source venv/bin/activate
python3 yolo_detector_opencv.py
deactivate
```

Para finalizar la ejecución, presionar la tecla **'q'** en la ventana de video.

### Modo Headless (Sin Interfaz Gráfica)

Ejecución sin servidor gráfico:

```bash
./run_headless.sh
```

Para detener el proceso, usar **Ctrl+C**.

### Verificación de Cámara

Antes de ejecutar el detector, se puede verificar el funcionamiento de la cámara:

```bash
./test_camera.sh
```

### Primera Ejecución

En la primera ejecución, el script descarga automáticamente los archivos del modelo YOLO:
- `yolov4-tiny.cfg` (~6 KB)
- `yolov4-tiny.weights` (~23 MB)
- `coco.names` (~1 KB)

Estos archivos se almacenan en `~/.yolo_opencv/` para su reutilización posterior.

## Funcionalidades

### Detección de Cámara

El sistema implementa detección automática de dispositivos de video con mecanismo de reintento (hasta 30 intentos por defecto).

### Detección de Objetos

Utiliza el modelo YOLOv4-tiny optimizado para plataformas ARM. Soporta las 80 clases del dataset COCO con umbral de confianza configurable (por defecto 0.5).

### Síntesis de Voz

Generación de anuncios de voz en español mediante pyttsx3, con respaldo a espeak en caso de indisponibilidad.

### Traducción de Etiquetas

Incluye mapeo completo de las 80 clases COCO a sus equivalentes en español.

## Configuración

### Archivo de Configuración (config.ini)

Los parámetros del sistema se definen en el archivo `config.ini`:

```ini
[Deteccion]
# Umbral de confianza (0.0 a 1.0) - Mayor valor = menos detecciones pero más precisas
confianza_minima = 0.5

# FPS objetivo: velocidad de procesamiento (1, 2, 5, 10, 30, etc)
fps_objetivo = 1

[Voz]
# Intervalo mínimo entre anuncios en segundos (evita ruido)
intervalo_anuncio = 4.0

# Velocidad de habla en palabras por minuto
velocidad_habla = 150

[Camara]
# Resolución de captura (640x480 recomendado para Raspberry Pi)
ancho = 640
alto = 480

# Máximo número de intentos para detectar cámara
max_intentos_camara = 30

[Sistema]
# Mostrar timestamp en cada mensaje de detección
mostrar_timestamp = true
```

### Modificación de Parámetros

Los parámetros se configuran mediante el archivo `config.ini`:

**FPS de procesamiento:**
- `fps_objetivo = 1` procesamiento a baja velocidad
- `fps_objetivo = 30` procesamiento a máxima velocidad

**Umbral de detección:**
- `confianza_minima = 0.5` valor predeterminado
- `confianza_minima = 0.7` mayor precisión, menos detecciones
- `confianza_minima = 0.3` menor precisión, más detecciones

**Intervalo de voz:**
- `intervalo_anuncio = 4.0` segundos entre anuncios

## Especificaciones Técnicas

Rendimiento en Raspberry Pi 4 (8GB):
- Tasa de procesamiento: 5-15 FPS con YOLOv4-tiny
- Resolución de entrada: 640x480 píxeles
- Latencia promedio: 100-200ms por frame
- Consumo de memoria: 200-400 MB

## Solución de Problemas

### Error: "No module named 'cv2'"

El entorno virtual no está activado. Utilizar los scripts de ejecución:
```bash
./run_gui.sh  # o ./run_headless.sh
```

O activar el entorno virtual manualmente:
```bash
source venv/bin/activate
```

### Error: "No se encontró el entorno virtual"

Ejecutar el script de instalación:
```bash
./install.sh
```

### Error: "No se detectó cámara web"

1. Verificar conexión física de la cámara
2. Comprobar dispositivos disponibles: `ls /dev/video*`
3. Verificar permisos de grupo: `sudo usermod -a -G video $USER`
4. Reiniciar sesión tras modificar permisos

### Sin salida de audio

1. Verificar instalación de espeak: `espeak -v es "prueba"`
2. Comprobar configuración de volumen del sistema
3. Instalar controladores de audio: `sudo apt-get install alsa-utils`

### Fallo en descarga del modelo YOLO

1. Verificar conectividad de red
2. La descarga se realiza automáticamente en la primera ejecución
3. Los archivos se almacenan en `~/.yolo_opencv/`

### Rendimiento degradado

Opciones de optimización:
1. Reducir valor de `fps_objetivo` en config.ini
2. Disminuir resolución de captura
3. Finalizar procesos innecesarios en segundo plano

### Error: "externally-managed-environment"

Este problema se resuelve mediante el uso de entornos virtuales implementado en el script de instalación:
1. Utilizar `./install.sh` para la instalación
2. Ejecutar mediante `./run_gui.sh` o `./run_headless.sh`

## Estructura del Proyecto

```
.
├── yolo_detector_opencv.py    Script principal
├── config.ini                 Configuración
├── requirements.txt           Dependencias Python
├── install.sh                 Script de instalación
├── run_gui.sh                 Ejecución con GUI
├── run_headless.sh            Ejecución sin GUI
├── test_camera.sh             Prueba de cámara
└── README.md                  Esta documentación
```

## Objetos Detectables

El sistema soporta la detección de 80 clases del dataset COCO:

**Personas y animales**: persona, perro, gato, caballo, pájaro, oveja, vaca, elefante, oso, cebra, jirafa

**Vehículos**: coche, motocicleta, autobús, camión, bicicleta, avión, tren, barco

**Mobiliario**: silla, sofá, cama, mesa de comedor, inodoro

**Electrónica**: televisor, portátil, ratón, teclado, teléfono móvil, microondas, horno, tostadora, refrigerador

**Accesorios**: mochila, paraguas, bolso, corbata, maleta

**Deportes**: pelota, raqueta de tenis, tabla de surf, monopatín

**Alimentos**: plátano, manzana, sándwich, naranja, brócoli, zanahoria, pizza, dona, pastel

Lista completa disponible en el archivo `coco.names`.

## Licencia

Proyecto de código abierto disponible para uso personal y educativo.

## Créditos

- YOLO: Ultralytics
- OpenCV: Biblioteca de visión por computadora
- pyttsx3: Motor de síntesis de voz
- eSpeak: Motor de voz alternativo

## Contacto y Soporte

Para información adicional consultar las documentaciones oficiales:
- OpenCV: https://docs.opencv.org/
- Raspberry Pi: https://www.raspberrypi.org/documentation/
