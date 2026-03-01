#!/usr/bin/env python3
"""
Detector de objetos YOLO con OpenCV DNN para Raspberry Pi 4.
Soporta modo GUI y headless con síntesis de voz en español.
Autoría: Alejandro Paredero - alejandro.paredero@cunef.edu
"""

import os
import sys
import time
import threading
import subprocess
import shutil
from pathlib import Path
from datetime import datetime
import configparser
import cv2
import numpy as np
import urllib.request
from PIL import Image, ImageDraw, ImageFont

# Cargar configuración
config = configparser.ConfigParser()
config_path = Path(__file__).parent / 'config.ini'
if config_path.exists():
    config.read(config_path)
else:
    print("[WARN] config.ini no encontrado, usando valores por defecto")

# Función para obtener timestamps
def get_timestamp():
    """Retorna timestamp formateado"""
    return datetime.now().strftime("%H:%M:%S")

# Función auxiliar para imprimir con timestamp
def print_detection(mensaje):
    """Imprime mensaje de detección con timestamp"""
    if config.getboolean('Sistema', 'mostrar_timestamp', fallback=True):
        print(f"[{get_timestamp()}] - {mensaje}")
    else:
        print(mensaje)

# Detección de disponibilidad de GUI
HAS_GUI = bool(os.environ.get('DISPLAY'))
if HAS_GUI:
    timestamp = get_timestamp()
    print(f"[{timestamp}] [INFO] GUI disponible: DISPLAY={os.environ.get('DISPLAY')}")
else:
    timestamp = get_timestamp()
    print(f"[{timestamp}] [WARN] GUI NO disponible: Sin DISPLAY")


# Diccionario de traducción de objetos COCO al español
TRADUCCIONES_COCO = {
    'person': 'persona',
    'bicycle': 'bicicleta',
    'car': 'coche',
    'motorbike': 'motocicleta',
    'aeroplane': 'avión',
    'bus': 'autobús',
    'train': 'tren',
    'truck': 'camión',
    'boat': 'barco',
    'traffic light': 'semáforo',
    'fire hydrant': 'boca de incendios',
    'stop sign': 'señal de stop',
    'parking meter': 'parquímetro',
    'bench': 'banco',
    'bird': 'pájaro',
    'cat': 'gato',
    'dog': 'perro',
    'horse': 'caballo',
    'sheep': 'oveja',
    'cow': 'vaca',
    'elephant': 'elefante',
    'bear': 'oso',
    'zebra': 'cebra',
    'giraffe': 'jirafa',
    'backpack': 'mochila',
    'umbrella': 'paraguas',
    'handbag': 'bolso',
    'tie': 'corbata',
    'suitcase': 'maleta',
    'frisbee': 'frisbee',
    'skis': 'esquís',
    'snowboard': 'tabla de snowboard',
    'sports ball': 'pelota',
    'kite': 'cometa',
    'baseball bat': 'bate de béisbol',
    'baseball glove': 'guante de béisbol',
    'skateboard': 'monopatín',
    'surfboard': 'tabla de surf',
    'tennis racket': 'raqueta de tenis',
    'bottle': 'botella',
    'wine glass': 'copa de vino',
    'cup': 'taza',
    'fork': 'tenedor',
    'knife': 'cuchillo',
    'spoon': 'cuchara',
    'bowl': 'tazón',
    'banana': 'plátano',
    'apple': 'manzana',
    'sandwich': 'sándwich',
    'orange': 'naranja',
    'broccoli': 'brócoli',
    'carrot': 'zanahoria',
    'hot dog': 'perrito caliente',
    'pizza': 'pizza',
    'donut': 'dona',
    'cake': 'pastel',
    'chair': 'silla',
    'sofa': 'sofá',
    'pottedplant': 'planta en maceta',
    'bed': 'cama',
    'diningtable': 'mesa de comedor',
    'toilet': 'inodoro',
    'tvmonitor': 'televisor',
    'laptop': 'portátil',
    'mouse': 'ratón',
    'remote': 'control remoto',
    'keyboard': 'teclado',
    'cell phone': 'teléfono móvil',
    'microwave': 'microondas',
    'oven': 'horno',
    'toaster': 'tostadora',
    'sink': 'lavabo',
    'refrigerator': 'refrigerador',
    'book': 'libro',
    'clock': 'reloj',
    'vase': 'jarrón',
    'scissors': 'tijeras',
    'teddy bear': 'oso de peluche',
    'hair drier': 'secador de pelo',
    'toothbrush': 'cepillo de dientes'
}


class SintesisVoz:
    """Clase para manejar la síntesis de voz en español"""
    
    def __init__(self):
        self.engine = None
        self.speaking = False
        self.lock = threading.Lock()
        
        try:
            import pyttsx3
            self.engine = pyttsx3.init()
            # Configurar voz en español
            voices = self.engine.getProperty('voices')
            for voice in voices:
                if 'spanish' in voice.name.lower() or 'español' in voice.name.lower():
                    self.engine.setProperty('voice', voice.id)
                    break
            self.engine.setProperty('rate', 150)  # Velocidad de habla
            print("[INFO] Motor de voz pyttsx3 inicializado")
        except Exception as e:
            print(f"[WARN] No se pudo inicializar pyttsx3: {e}")
            print("[INFO] Intentando con espeak...")
            self.engine = None
    
    def hablar(self, texto):
        """Habla el texto de forma asíncrona para no bloquear"""
        if self.speaking:
            return  # Ya está hablando, no interrumpir
        
        thread = threading.Thread(target=self._hablar_sync, args=(texto,))
        thread.daemon = True
        thread.start()
    
    def _hablar_sync(self, texto):
        """Síntesis de voz sincrónica"""
        with self.lock:
            self.speaking = True
            try:
                if self.engine:
                    # Usar pyttsx3
                    self.engine.say(texto)
                    self.engine.runAndWait()
                else:
                    # Fallback a espeak si está disponible
                    os.system(f'espeak -v es -s 150 "{texto}" 2>/dev/null')
            except Exception as e:
                print(f"[WARN] Error en síntesis de voz: {e}")
            finally:
                self.speaking = False


class DetectorCamara:
    """Maneja la detección y verificación de la cámara web"""

    class CapturaConProceso:
        """Wrapper para gestionar una captura OpenCV asociada a un proceso externo."""

        def __init__(self, cap, proc=None, descripcion=""):
            self._cap = cap
            self._proc = proc
            self.descripcion = descripcion

        def isOpened(self):
            return self._cap is not None and self._cap.isOpened()

        def read(self):
            return self._cap.read()

        def set(self, prop_id, value):
            try:
                return self._cap.set(prop_id, value)
            except Exception:
                return False

        def release(self):
            try:
                if self._cap is not None:
                    self._cap.release()
            finally:
                if self._proc is not None:
                    try:
                        self._proc.terminate()
                        self._proc.wait(timeout=2)
                    except Exception:
                        try:
                            self._proc.kill()
                        except Exception:
                            pass

    class CapturaPicamera2:
        """Wrapper para captura CSI usando Picamera2."""

        def __init__(self, picam):
            self._picam = picam
            self.descripcion = "CSI/Picamera2"
            self._lock = threading.Lock()
            self._running = True
            self._latest_frame = None
            self._last_frame_time = 0.0
            self._reader_thread = threading.Thread(target=self._reader_loop, daemon=True)
            self._reader_thread.start()

        def _reader_loop(self):
            while self._running:
                try:
                    frame_rgb = self._picam.capture_array()
                    if frame_rgb is None or frame_rgb.size == 0:
                        time.sleep(0.005)
                        continue

                    frame_bgr = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)
                    with self._lock:
                        self._latest_frame = frame_bgr
                        self._last_frame_time = time.time()
                except Exception:
                    time.sleep(0.01)

        def isOpened(self):
            return self._picam is not None and self._running

        def read(self):
            timeout = 0.25
            inicio = time.time()
            while self._running and (time.time() - inicio) < timeout:
                with self._lock:
                    if self._latest_frame is not None:
                        return True, self._latest_frame.copy()
                time.sleep(0.005)
            return False, None

        def set(self, prop_id, value):
            return False

        def release(self):
            self._running = False
            try:
                if self._reader_thread.is_alive():
                    self._reader_thread.join(timeout=1.0)
            except Exception:
                pass
            if self._picam is not None:
                try:
                    self._picam.stop()
                except Exception:
                    pass
                try:
                    self._picam.close()
                except Exception:
                    pass
    
    @staticmethod
    def listar_dispositivos_video():
        """Lista los dispositivos de video disponibles en /dev"""
        import glob
        dispositivos = glob.glob('/dev/video*')
        if dispositivos:
            print(f"[INFO] Dispositivos de video encontrados: {', '.join(dispositivos)}")
            return dispositivos
        else:
            print("[WARN] No se encontraron dispositivos /dev/video*")
            return []

    @staticmethod
    def _abrir_csi_libcamera(ancho=640, alto=480, fps=30):
        """Intenta abrir la cámara CSI mediante libcamerasrc (GStreamer)."""
        pipeline = (
            f"libcamerasrc ! video/x-raw,width={ancho},height={alto},framerate={fps}/1 "
            "! videoconvert ! appsink drop=true max-buffers=1 sync=false"
        )
        try:
            cap = cv2.VideoCapture(pipeline, cv2.CAP_GSTREAMER)
            if not cap.isOpened():
                cap.release()
                return None

            ret, frame = cap.read()
            if ret and frame is not None and frame.size > 0:
                print("[INFO] Cámara CSI detectada y abierta por libcamera")
                return cap

            cap.release()
        except Exception as e:
            print(f"[WARN] Falló apertura CSI con libcamera: {e}")

        return None

    @staticmethod
    def _abrir_csi_picamera2(ancho=640, alto=480, fps=30):
        """Intenta abrir la cámara CSI con Picamera2 (backend recomendado en Raspberry Pi)."""
        try:
            from picamera2 import Picamera2
        except Exception:
            return None

        try:
            picam = Picamera2()
            config_video = picam.create_video_configuration(
                main={"size": (ancho, alto), "format": "RGB888"},
                controls={"FrameRate": float(fps)}
            )
            picam.configure(config_video)
            picam.start()
            time.sleep(0.3)

            captura = DetectorCamara.CapturaPicamera2(picam)
            ok, test = captura.read()
            if not ok or test is None or test.size == 0:
                captura.release()
                return None
            print("[INFO] Cámara CSI detectada y abierta por Picamera2")
            return captura
        except Exception as e:
            print(f"[WARN] Falló apertura CSI con Picamera2: {e}")
            return None

    @staticmethod
    def _abrir_csi_rpicam(ancho=640, alto=480, fps=30):
        """Intenta abrir la cámara CSI usando rpicam-vid y recepción UDP en OpenCV."""
        if shutil.which("rpicam-vid") is None:
            return None

        # Evitar saturación del buffer: emitir a una tasa moderada según FPS de detección
        fps_detect = config.getint('Deteccion', 'fps_objetivo', fallback=1)
        fps_stream = max(2, min(10, fps_detect * 2))

        puerto = 5600
        cmd = [
            "rpicam-vid",
            "-n",
            "-t", "0",
            "--width", str(ancho),
            "--height", str(alto),
            "--framerate", str(fps_stream),
            "--codec", "mjpeg",
            "-o", f"udp://127.0.0.1:{puerto}",
        ]
        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            time.sleep(0.8)

            cap_url = f"udp://127.0.0.1:{puerto}?fifo_size=1000000&overrun_nonfatal=1"
            cap = cv2.VideoCapture(cap_url, cv2.CAP_FFMPEG)
            if not cap.isOpened():
                cap.release()
                proc.terminate()
                return None

            try:
                cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            except Exception:
                pass

            for _ in range(60):
                ret, frame = cap.read()
                if ret and frame is not None and frame.size > 0:
                    print("[INFO] Cámara CSI detectada y abierta por rpicam-vid (UDP)")
                    return DetectorCamara.CapturaConProceso(cap, proc, "CSI/rpicam-vid-UDP")
                if proc.poll() is not None:
                    break
                time.sleep(0.03)

            cap.release()
            proc.terminate()
        except Exception as e:
            print(f"[WARN] Falló apertura CSI con rpicam-vid (UDP): {e}")

        return None

    @staticmethod
    def _abrir_v4l2_por_indice(indice, ancho=640, alto=480):
        """Abre cámara por V4L2 forzando backend para evitar fallos del backend por defecto."""
        try:
            cap = cv2.VideoCapture(indice, cv2.CAP_V4L2)
            if not cap.isOpened():
                cap.release()
                return None

            cap.set(cv2.CAP_PROP_FRAME_WIDTH, ancho)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, alto)

            ret, frame = cap.read()
            if ret and frame is not None and frame.size > 0:
                return cap

            cap.release()
        except Exception:
            try:
                cap.release()
            except Exception:
                pass
        return None
    
    @staticmethod
    def detectar_camara():
        """Detecta cámara priorizando CSI y retornando captura abierta + descripción."""
        dispositivos = DetectorCamara.listar_dispositivos_video()

        print("[INFO] Probando cámara CSI con Picamera2 primero...")
        cap_picamera2 = DetectorCamara._abrir_csi_picamera2()
        if cap_picamera2 is not None:
            return cap_picamera2, "CSI/Picamera2"

        print("[INFO] Picamera2 no disponible. Probando cámara CSI con rpicam-vid...")
        cap_rpicam = DetectorCamara._abrir_csi_rpicam()
        if cap_rpicam is not None:
            return cap_rpicam, "CSI/rpicam-vid"

        print("[INFO] rpicam-vid no disponible o no funcional. Probando libcamerasrc...")
        cap_csi = DetectorCamara._abrir_csi_libcamera()
        if cap_csi is not None:
            return DetectorCamara.CapturaConProceso(cap_csi, None, "CSI/libcamerasrc"), "CSI/libcamerasrc"

        if not dispositivos:
            return None, None

        print("[INFO] Fallback a cámaras USB/V4L2...")
        candidatos = []
        for path_dev in dispositivos:
            try:
                idx = int(path_dev.replace('/dev/video', ''))
                candidatos.append(idx)
            except ValueError:
                continue
        candidatos = sorted(set(candidatos))

        for i in candidatos:
            print(f"[INFO] Intentando /dev/video{i} (V4L2)...", end="", flush=True)
            cap_usb = DetectorCamara._abrir_v4l2_por_indice(i)
            if cap_usb is not None:
                print(" [OK] FUNCIONANDO")
                return DetectorCamara.CapturaConProceso(cap_usb, None, f"/dev/video{i}"), f"/dev/video{i}"
            print(" [WARN] no usable")

        return None, None
    
    @staticmethod
    def mostrar_error_camara(sintesis_voz, has_gui, mostrar_popup=True):
        """Muestra error cuando no se detecta cámara"""
        mensaje = "No se detectó cámara web"
        print(f"[ERROR] {mensaje}")
        
        # Hablar el mensaje solo la primera vez
        if mostrar_popup and sintesis_voz:
            try:
                sintesis_voz.hablar(mensaje)
            except:
                pass


class DetectorObjetosOpenCV:
    """Clase principal para detección de objetos con YOLO usando OpenCV DNN"""
    
    def __init__(self):
        self.net = None
        self.clases = []
        self.sintesis_voz = SintesisVoz()
        self.ultimo_objeto = None
        self.tiempo_ultimo_anuncio = 0
        # Leer intervalo de anuncio desde config
        self.intervalo_anuncio = config.getfloat('Voz', 'intervalo_anuncio', fallback=4.0)
        self.confianza_minima = config.getfloat('Deteccion', 'confianza_minima', fallback=0.5)
        self.nms_threshold = config.getfloat('Deteccion', 'nms_threshold', fallback=0.4)
        self.fps_objetivo = config.getint('Deteccion', 'fps_objetivo', fallback=1)
        self.detectar_todos_los_fps = config.getboolean('Deteccion', 'detectar_todos_los_fps', fallback=True)
        self.intervalo_logs_info = config.getfloat('Sistema', 'intervalo_logs_info', fallback=3.0)
        self.modelo_dir = Path.home() / '.yolo_opencv'
        self.modelo_dir.mkdir(exist_ok=True)
        
    def descargar_archivos_modelo(self):
        """Descarga los archivos necesarios del modelo YOLO"""
        print("[INFO] Descargando archivos del modelo YOLO...")
        
        # URLs de los archivos (YOLOv4-tiny - más ligero para Raspberry Pi)
        archivos = {
            'yolov4-tiny.cfg': 'https://raw.githubusercontent.com/AlexeyAB/darknet/master/cfg/yolov4-tiny.cfg',
            'yolov4-tiny.weights': 'https://github.com/AlexeyAB/darknet/releases/download/yolov4/yolov4-tiny.weights',
            'coco.names': 'https://raw.githubusercontent.com/pjreddie/darknet/master/data/coco.names'
        }
        
        for nombre, url in archivos.items():
            ruta_archivo = self.modelo_dir / nombre
            
            if ruta_archivo.exists():
                print(f"  [OK] {nombre} ya existe")
                continue
            
            print(f"  Descargando {nombre}...")
            try:
                urllib.request.urlretrieve(url, ruta_archivo)
                print(f"  [OK] {nombre} descargado")
            except Exception as e:
                print(f"  ✗ Error descargando {nombre}: {e}")
                return False
        
        return True
    
    def cargar_modelo(self):
        """Carga el modelo YOLO en OpenCV DNN"""
        print("[INFO] Cargando modelo YOLO con OpenCV DNN...")
        
        # Descargar archivos si es necesario
        if not self.descargar_archivos_modelo():
            print("[ERROR] No se pudieron descargar los archivos del modelo")
            return False
        
        try:
            # Cargar nombres de clases
            ruta_clases = self.modelo_dir / 'coco.names'
            with open(ruta_clases, 'r') as f:
                self.clases = [line.strip() for line in f.readlines()]
            
            # Cargar red YOLO
            ruta_cfg = str(self.modelo_dir / 'yolov4-tiny.cfg')
            ruta_weights = str(self.modelo_dir / 'yolov4-tiny.weights')
            
            self.net = cv2.dnn.readNetFromDarknet(ruta_cfg, ruta_weights)
            
            # Configurar backend preferido (CPU para Raspberry Pi)
            self.net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
            self.net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)
            
            print("[INFO] Modelo YOLO cargado correctamente con OpenCV DNN")
            print(f"[INFO] Clases detectables: {len(self.clases)}")
            return True
            
        except Exception as e:
            print(f"[ERROR] No se pudo cargar el modelo YOLO: {e}")
            return False
    
    def traducir_objeto(self, nombre_ingles):
        """Traduce el nombre del objeto al español"""
        return TRADUCCIONES_COCO.get(nombre_ingles, nombre_ingles)
    
    def dibujar_texto_utf8(self, frame, texto, posicion, color):
        """Dibuja texto con soporte UTF-8 (acentos) usando PIL"""
        try:
            # Convertir BGR a RGB
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            pil_image = Image.fromarray(frame_rgb)
            draw = ImageDraw.Draw(pil_image)
            
            # Usar una fuente que soporte UTF-8
            try:
                # En Raspberry Pi, típicamente hay esta fuente
                fuente = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 16)
            except:
                # Fallback a fuente por defecto
                fuente = ImageFont.load_default()
            
            # Dibujar fondo para el texto
            x, y = posicion
            bbox = draw.textbbox((x, y), texto, font=fuente)
            draw.rectangle(bbox, fill=(0, 255, 0))  # Fondo verde
            
            # Dibujar texto en negro
            draw.text((x, y), texto, font=fuente, fill=(0, 0, 0))
            
            # Convertir de vuelta a BGR
            frame_resultado = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
            return frame_resultado
        except Exception as e:
            # Fallback a cv2.putText si algo falla
            print(f"[WARN] Error renderizando texto UTF-8: {e}")
            return frame

    def dibujar_detecciones(self, frame, detecciones_detalle):
        """Dibuja recuadros y etiquetas a partir de detecciones guardadas."""
        if not detecciones_detalle:
            return frame

        color = (0, 255, 0)
        for det in detecciones_detalle:
            x = det['x']
            y = det['y']
            w = det['w']
            h = det['h']
            etiqueta_espanol = det['etiqueta']
            confianza = det['confianza']

            cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
            texto = f"{etiqueta_espanol} {confianza:.2f}"
            frame = self.dibujar_texto_utf8(frame, texto, (x, y - 5), color)

        return frame
    
    def procesar_frame(self, frame):
        """Procesa un frame y retorna (frame, objetos_con_confianza, detecciones_detalle)."""
        if self.net is None:
            return frame, [], []
        
        altura, ancho = frame.shape[:2]
        
        # Crear blob desde la imagen (320x320 para mejor rendimiento en RPi)
        blob = cv2.dnn.blobFromImage(frame, 1/255.0, (320, 320), swapRB=True, crop=False)
        self.net.setInput(blob)
        
        # Obtener nombres de las capas de salida
        layer_names = self.net.getLayerNames()
        output_layers = [layer_names[i - 1] for i in self.net.getUnconnectedOutLayers()]
        
        # Realizar detección
        detecciones = self.net.forward(output_layers)
        
        # Procesar detecciones
        cajas = []
        confianzas = []
        ids_clases = []
        
        for salida in detecciones:
            for deteccion in salida:
                scores = deteccion[5:]
                id_clase = np.argmax(scores)
                confianza = scores[id_clase]
                
                if confianza > self.confianza_minima:  # Umbral de confianza
                    # Coordenadas del cuadro delimitador
                    centro_x = int(deteccion[0] * ancho)
                    centro_y = int(deteccion[1] * altura)
                    w = int(deteccion[2] * ancho)
                    h = int(deteccion[3] * altura)
                    
                    # Coordenadas de la esquina superior izquierda
                    x = int(centro_x - w / 2)
                    y = int(centro_y - h / 2)
                    
                    cajas.append([x, y, w, h])
                    confianzas.append(float(confianza))
                    ids_clases.append(id_clase)
        
        # Aplicar Non-Maximum Suppression
        indices = cv2.dnn.NMSBoxes(cajas, confianzas, self.confianza_minima, self.nms_threshold)
        
        objetos_con_confianza = []  # (nombre, confianza)
        detecciones_detalle = []
        
        if len(indices) > 0:
            for i in indices.flatten():
                x, y, w, h = cajas[i]
                etiqueta = self.clases[ids_clases[i]]
                confianza = confianzas[i]
                
                # Traducir al español
                etiqueta_espanol = self.traducir_objeto(etiqueta)
                objetos_con_confianza.append((etiqueta_espanol, confianza))
                detecciones_detalle.append({
                    'x': x,
                    'y': y,
                    'w': w,
                    'h': h,
                    'etiqueta': etiqueta_espanol,
                    'confianza': confianza,
                })
                
                # Dibujar rectángulo
                color = (0, 255, 0)
                cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
                
                # Dibujar etiqueta con soporte UTF-8 (acentos)
                texto = f"{etiqueta_espanol} {confianza:.2f}"
                frame = self.dibujar_texto_utf8(frame, texto, (x, y - 5), color)
        
        # Anunciar solo el nombre del objeto (sin confianza)
        if objetos_con_confianza:
            tiempo_actual = time.time()
            objeto_actual = objetos_con_confianza[0][0]  # Solo el nombre del objeto más prominente
            
            # Solo anunciar si cambió el objeto o pasó suficiente tiempo (4 segundos)
            if (objeto_actual != self.ultimo_objeto or 
                tiempo_actual - self.tiempo_ultimo_anuncio > self.intervalo_anuncio):
                self.sintesis_voz.hablar(objeto_actual)  # Solo el nombre, sin "Detecto"
                self.ultimo_objeto = objeto_actual
                self.tiempo_ultimo_anuncio = tiempo_actual
        
        return frame, objetos_con_confianza, detecciones_detalle
    
    def ejecutar(self):
        """Ejecuta el bucle principal de detección"""
        global HAS_GUI
        cap = None
        camara_desc = None
        intentos = 0
        max_intentos = 30  # Máximo 30 intentos (5 minutos)
        mostrar_popup = True  # Solo mostrar popup la primera vez
        
        # Bucle de detección de cámara
        while cap is None and intentos < max_intentos:
            print("[INFO] Buscando cámara web...")
            cap, camara_desc = DetectorCamara.detectar_camara()
            
            if cap is None:
                DetectorCamara.mostrar_error_camara(self.sintesis_voz, HAS_GUI, mostrar_popup)
                mostrar_popup = False  # No mostrar popup en siguientes intentos
                intentos += 1
                print(f"[INFO] Reintentando en 10 segundos... (Intento {intentos}/{max_intentos})")
                print("[INFO] Presiona Ctrl+C para cancelar")
                time.sleep(10)
        
        # Si no se encontró cámara después de todos los intentos
        if cap is None:
            print("[ERROR] No se pudo detectar ninguna cámara después de múltiples intentos.")
            print("[INFO] Verifica:")
            print("  1. Que la cámara esté conectada")
            print("  2. Ejecuta: ls /dev/video*")
            print("  3. Permisos: sudo usermod -a -G video $USER")
            return
        
        # Cargar modelo YOLO
        if not self.cargar_modelo():
            print("[ERROR] No se pudo cargar el modelo. Saliendo...")
            return
        
        # Configurar resolución para mejor rendimiento
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        
        if not cap.isOpened():
            print("[ERROR] No se pudo abrir la cámara")
            return
        
        # Verificar que la cámara realmente funciona
        print("[INFO] Verificando lectura de cámara...")
        ret, test_frame = cap.read()
        if not ret or test_frame is None or test_frame.size == 0:
            print("[ERROR] La cámara no devuelve frames válidos")
            cap.release()
            return
        
        print(f"[INFO] Cámara activa: {camara_desc} - Resolución: {test_frame.shape[1]}x{test_frame.shape[0]}")
        print("[INFO] Iniciando detección de objetos...")
        print("[INFO] Presiona 'q' o ESC para salir")
        
        frames_procesados = 0
        fps_start_time = time.time()
        fps_counter = 0
        ultimo_tiempo_deteccion = 0.0
        intervalo_deteccion = 0.0 if self.detectar_todos_los_fps else (1.0 / self.fps_objetivo if self.fps_objetivo > 0 else 0.0)
        ultimos_objetos_detectados = []
        ultimas_detecciones_detalle = []
        ultimo_log_info = time.time()
        ultimo_log_deteccion = 0.0
        errores_lectura_consecutivos = 0
        max_errores_lectura = 25
        
        try:
            while True:
                ret, frame = cap.read()
                
                if not ret or frame is None or frame.size == 0:
                    errores_lectura_consecutivos += 1
                    if errores_lectura_consecutivos == 1 or errores_lectura_consecutivos % 10 == 0:
                        print(f"[WARN] No se pudo leer frame de la cámara ({errores_lectura_consecutivos})")

                    if errores_lectura_consecutivos >= max_errores_lectura:
                        print("[WARN] Se perdió el stream de cámara. Intentando reconexión...")
                        try:
                            cap.release()
                        except Exception:
                            pass

                        cap, camara_desc = DetectorCamara.detectar_camara()
                        if cap is None:
                            print("[ERROR] No se pudo reconectar la cámara")
                            break

                        print(f"[INFO] Reconectado a cámara: {camara_desc}")
                        errores_lectura_consecutivos = 0
                        time.sleep(0.2)
                        continue

                    time.sleep(0.02)
                    continue

                errores_lectura_consecutivos = 0
                
                frames_procesados += 1
                fps_counter += 1
                
                # Mostrar vídeo siempre fluido y limitar solo la frecuencia de detección
                frame_procesado = frame.copy()
                objetos_detectados = []
                tiempo_actual = time.time()

                if (intervalo_deteccion == 0.0) or (tiempo_actual - ultimo_tiempo_deteccion >= intervalo_deteccion):
                    frame_procesado, objetos_detectados, detecciones_detalle = self.procesar_frame(frame.copy())
                    ultimo_tiempo_deteccion = tiempo_actual
                    ultimos_objetos_detectados = objetos_detectados
                    ultimas_detecciones_detalle = detecciones_detalle

                    # Mostrar objetos detectados en consola con timestamp (limitado)
                    if objetos_detectados and (tiempo_actual - ultimo_log_deteccion >= self.intervalo_logs_info):
                        objetos_str = ", ".join([f"{obj[0]} ({obj[1]*100:.0f}%)" for obj in objetos_detectados])
                        print_detection(f"[DETECCIÓN] {objetos_str}")
                        ultimo_log_deteccion = tiempo_actual
                elif ultimos_objetos_detectados:
                    # Mantener recuadros y etiquetas en frames intermedios
                    frame_procesado = self.dibujar_detecciones(frame_procesado, ultimas_detecciones_detalle)
                
                # Calcular y mostrar FPS cada N segundos
                if tiempo_actual - ultimo_log_info >= self.intervalo_logs_info:
                    fps = fps_counter / (time.time() - fps_start_time)
                    print(f"[INFO] FPS: {fps:.1f}")
                    fps_counter = 0
                    fps_start_time = time.time()
                    ultimo_log_info = tiempo_actual
                
                # Mostrar frame si hay GUI
                if HAS_GUI:
                    try:
                        # Nombre simple de ventana
                        cv2.imshow('YOLO Detector - Presiona q o ESC', frame_procesado)

                        # Refresco de GUI siempre rápido para evitar congelación visual
                        key = cv2.waitKey(1) & 0xFF
                        if key == ord('q') or key == ord('Q') or key == 27:  # q, Q o ESC
                            print("[INFO] Saliendo...")
                            break
                    except Exception as e:
                        print(f"[ERROR] Error mostrando frame: {e}")
                        HAS_GUI = False
                        print("[INFO] Cambiando a modo headless")
                else:
                    # Modo headless: espera corta para no saturar CPU
                    time.sleep(0.01)
        
        except KeyboardInterrupt:
            print("\n[INFO] Interrupción del usuario. Saliendo...")
        
        finally:
            # Liberar recursos
            try:
                cap.release()
            except KeyboardInterrupt:
                pass
            except Exception:
                pass

            if HAS_GUI:
                try:
                    cv2.destroyAllWindows()
                except Exception:
                    pass
            print("[INFO] Recursos liberados. Programa terminado.")


def verificar_dependencias():
    """Verifica las dependencias necesarias"""
    print("[INFO] Verificando dependencias...")

    dependencias_requeridas = [
        ('cv2', 'opencv-python')
    ]
    dependencias_opcionales = [
        ('pyttsx3', 'pyttsx3')
    ]

    faltantes_requeridas = []
    for modulo, paquete in dependencias_requeridas:
        try:
            __import__(modulo)
            print(f"[OK] {modulo} está instalado")
        except ImportError:
            print(f"[WARN] {modulo} no está instalado")
            faltantes_requeridas.append(paquete)

    for modulo, _ in dependencias_opcionales:
        try:
            __import__(modulo)
            print(f"[OK] {modulo} está instalado")
        except ImportError:
            print(f"[WARN] {modulo} no está instalado (modo sin voz disponible)")

    if faltantes_requeridas:
        print(f"\n[ERROR] Faltan dependencias requeridas: {', '.join(faltantes_requeridas)}")
        print("Instálalas en el venv con:")
        print("  source venv/bin/activate && pip install -r requirements.txt")
        sys.exit(1)


def main():
    """Función principal"""
    print("=" * 60)
    print("  Detector de Objetos YOLO - OpenCV DNN")
    print("  Raspberry Pi 4")
    print("=" * 60)
    print()
    
    # Verificar dependencias
    verificar_dependencias()
    
    # Crear y ejecutar detector
    detector = DetectorObjetosOpenCV()
    detector.ejecutar()


if __name__ == "__main__":
    main()
