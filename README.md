# Detector de Objetos YOLO para Raspberry Pi 4

Sistema de detección de objetos en tiempo real usando YOLO con síntesis de voz en español para Raspberry Pi 4.
_Alejandro Paredero de Dios - alejandro.paredero@cunef.edu_

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
- Cámara CSI compatible con libcamera o cámara USB compatible con V4L2
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
sudo apt-get install -y python3-picamera2
sudo apt-get install -y rpicam-apps
sudo apt-get install -y gstreamer1.0-libcamera libcamera-apps
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

Todos los scripts de ejecución siguen el mismo comportamiento:
- No requieren `sudo` (si se usa, re-ejecutan como usuario normal)
- Activan automáticamente el entorno virtual `venv`
- Para cámara: prioridad CSI (libcamera) y fallback automático a USB (V4L2)

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

`run_headless.sh` ejecuta el mismo flujo interno que `run_gui.sh` (mismo detector, misma lógica de fallback de cámara y misma configuración), cambiando únicamente la visualización por pantalla.

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

El sistema usa el siguiente orden para cámara CSI:
1. `Picamera2` (preferente, más estable en Raspberry Pi)
2. `rpicam-vid` por UDP
3. `libcamerasrc`

Si la cámara CSI no está disponible, realiza fallback automático a cámaras USB por V4L2 (`/dev/video*`).
Incluye mecanismo de reintento (hasta 30 intentos por defecto).
En modo Picamera2 la captura se hace de forma asíncrona (buffer de último frame) para evitar bloqueos y congelaciones de la ventana.

Este comportamiento se aplica tanto en el detector principal (`yolo_detector_opencv.py`) como en la prueba de cámara (`test_camera.py`).

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

# Detectar con YOLO en todos los frames (true/false)
detectar_todos_los_fps = true

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

# Intervalo mínimo entre mensajes de consola [INFO]/[DETECCIÓN]
intervalo_logs_info = 3.0
```

### Modificación de Parámetros

Los parámetros se configuran mediante el archivo `config.ini`:

**FPS de procesamiento:**
- `fps_objetivo = 1` detección una vez por segundo con visualización fluida
- `fps_objetivo = 5` detección cinco veces por segundo
- La ventana GUI se refresca de forma continua para evitar imagen congelada

**Recuadros en todos los FPS:**
- `detectar_todos_los_fps = true` aplica YOLO en cada frame para mantener recuadros continuamente
- `detectar_todos_los_fps = false` usa `fps_objetivo` para detección y mantiene recuadros con la última detección

**Frecuencia de logs en consola:**
- `intervalo_logs_info = 3.0` limita mensajes `[INFO]` y `[DETECCIÓN]` a un máximo de uno cada 3 segundos

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
5. Probar cámara CSI directamente: `rpicam-hello`
6. Verificar app de CSI: `rpicam-vid --help`

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

### Aviso: "Circular buffer overrun" en CSI

Si aparece este aviso en captura CSI:
- El sistema aplica opciones de mitigación en UDP (`fifo_size` y `overrun_nonfatal`)
- Se reduce automáticamente la tasa de stream de CSI según `fps_objetivo`
- La detección se limita por frecuencia, pero la vista sigue en tiempo real
- Si persiste, instalar y usar `python3-picamera2` para evitar ruta FFmpeg/GStreamer

### Error: "externally-managed-environment"

Este problema se resuelve mediante el uso de entornos virtuales implementado en el script de instalación:
1. Utilizar `./install.sh` para la instalación
2. Ejecutar mediante `./run_gui.sh` o `./run_headless.sh`
3. No ejecutar scripts con `sudo`, ya que puede omitir el entorno virtual del usuario

## Estructura del Proyecto

```
.
├── .gitignore                 Exclusiones de control de versiones
├── README.md                  Esta documentación
├── config.ini                 Configuración
├── install.sh                 Script de instalación
├── install_log.txt            Registro de instalación
├── requirements.txt           Dependencias Python
├── run_gui.sh                 Ejecución con GUI
├── run_headless.sh            Ejecución sin GUI
├── test_camera.py             Lógica de prueba CSI/USB
├── test_camera.sh             Script de prueba de cámara
├── uninstall.sh               Script de desinstalación
├── yolo_detector_opencv.py    Script principal
├── venv/                      Entorno virtual local (generado)
├── __pycache__/               Caché de bytecode (generado)
└── .git/                      Metadatos del repositorio
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
