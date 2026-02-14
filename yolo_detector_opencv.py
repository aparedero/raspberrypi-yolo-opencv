#!/usr/bin/env python3
"""
Detector de objetos YOLO con OpenCV DNN para Raspberry Pi 4.
Soporta modo GUI y headless con síntesis de voz en español.
"""

import os
import sys
import time
import threading
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
    
    @staticmethod
    def listar_dispositivos_video():
        """Lista los dispositivos de video disponibles en /dev"""
        import glob
        dispositivos = glob.glob('/dev/video*')
        if dispositivos:
            print(f"[INFO] Dispositivos de video encontrados: {', '.join(dispositivos)}")
            return True
        else:
            print("[WARN] No se encontraron dispositivos /dev/video*")
            return False
    
    @staticmethod
    def detectar_camara():
        """Detecta si hay una cámara disponible"""
        # Primero verificar si existen dispositivos de video
        if not DetectorCamara.listar_dispositivos_video():
            return None
        
        # Intenta abrir la cámara
        print("[INFO] Probando dispositivos de cámara...")
        for i in range(5):  # Prueba hasta 5 índices
            try:
                print(f"[INFO] Intentando /dev/video{i}...", end="", flush=True)
                cap = cv2.VideoCapture(i)
                if cap.isOpened():
                    # Intentar leer un frame para verificar que realmente funciona
                    ret, frame = cap.read()
                    cap.release()
                    if ret and frame is not None and frame.size > 0:
                        print(" [OK] FUNCIONANDO")
                        return i
                    else:
                        print(" ✗ No devuelve frames")
                else:
                    cap.release()
                    print(" ✗ No se abre")
            except Exception as e:
                print(f" ✗ Error: {e}")
                try:
                    cap.release()
                except:
                    pass
                continue
        return None
    
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
    
    def procesar_frame(self, frame):
        """Procesa un frame y retorna (frame con anotaciones, lista de objetos con confianzas)"""
        if self.net is None:
            return frame, []
        
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
        
        if len(indices) > 0:
            for i in indices.flatten():
                x, y, w, h = cajas[i]
                etiqueta = self.clases[ids_clases[i]]
                confianza = confianzas[i]
                
                # Traducir al español
                etiqueta_espanol = self.traducir_objeto(etiqueta)
                objetos_con_confianza.append((etiqueta_espanol, confianza))
                
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
        
        return frame, objetos_con_confianza
    
    def ejecutar(self):
        """Ejecuta el bucle principal de detección"""
        global HAS_GUI
        camara_idx = None
        intentos = 0
        max_intentos = 30  # Máximo 30 intentos (5 minutos)
        mostrar_popup = True  # Solo mostrar popup la primera vez
        
        # Bucle de detección de cámara
        while camara_idx is None and intentos < max_intentos:
            print("[INFO] Buscando cámara web...")
            camara_idx = DetectorCamara.detectar_camara()
            
            if camara_idx is None:
                DetectorCamara.mostrar_error_camara(self.sintesis_voz, HAS_GUI, mostrar_popup)
                mostrar_popup = False  # No mostrar popup en siguientes intentos
                intentos += 1
                print(f"[INFO] Reintentando en 10 segundos... (Intento {intentos}/{max_intentos})")
                print("[INFO] Presiona Ctrl+C para cancelar")
                time.sleep(10)
        
        # Si no se encontró cámara después de todos los intentos
        if camara_idx is None:
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
        
        # Abrir cámara
        cap = cv2.VideoCapture(camara_idx)
        
        # Configurar resolución más baja para mejor rendimiento
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
        
        print(f"[INFO] Cámara funcionando correctamente - Resolución: {test_frame.shape[1]}x{test_frame.shape[0]}")
        print("[INFO] Iniciando detección de objetos...")
        print("[INFO] Presiona 'q' o ESC para salir")
        
        frames_procesados = 0
        fps_start_time = time.time()
        fps_counter = 0
        
        try:
            while True:
                ret, frame = cap.read()
                
                if not ret or frame is None or frame.size == 0:
                    print("[WARN] No se pudo leer frame de la cámara")
                    time.sleep(0.1)
                    continue
                
                frames_procesados += 1
                fps_counter += 1
                
                # Procesar cada frame para no perder detecciones
                frame_procesado, objetos_detectados = self.procesar_frame(frame)
                
                # Mostrar objetos detectados en consola con timestamp
                if objetos_detectados:
                    objetos_str = ", ".join([f"{obj[0]} ({obj[1]*100:.0f}%)" for obj in objetos_detectados])
                    print_detection(f"[DETECCIÓN] {objetos_str}")
                
                # Calcular y mostrar FPS cada 10 frames
                if fps_counter >= 10:
                    fps = fps_counter / (time.time() - fps_start_time)
                    print(f"[INFO] FPS: {fps:.1f}")
                    fps_counter = 0
                    fps_start_time = time.time()
                
                # Mostrar frame si hay GUI
                if HAS_GUI:
                    try:
                        # Nombre simple de ventana
                        cv2.imshow('YOLO Detector - Presiona q o ESC', frame_procesado)
                        
                        # Delay basado en fps_objetivo desde config
                        delay_ms = max(1, 1000 // self.fps_objetivo) if self.fps_objetivo > 0 else 1000
                        key = cv2.waitKey(delay_ms) & 0xFF
                        if key == ord('q') or key == ord('Q') or key == 27:  # q, Q o ESC
                            print("[INFO] Saliendo...")
                            break
                    except Exception as e:
                        print(f"[ERROR] Error mostrando frame: {e}")
                        HAS_GUI = False
                        print("[INFO] Cambiando a modo headless")
                else:
                    # Modo headless: esperar según fps_objetivo
                    sleep_time = (1.0 / self.fps_objetivo) if self.fps_objetivo > 0 else 1.0
                    time.sleep(sleep_time)
        
        except KeyboardInterrupt:
            print("\n[INFO] Interrupción del usuario. Saliendo...")
        
        finally:
            # Liberar recursos
            cap.release()
            if HAS_GUI:
                cv2.destroyAllWindows()
            print("[INFO] Recursos liberados. Programa terminado.")


def verificar_dependencias():
    """Verifica las dependencias necesarias"""
    print("[INFO] Verificando dependencias...")
    
    dependencias = [
        ('cv2', 'opencv-python'),
        ('pyttsx3', 'pyttsx3')
    ]
    
    faltantes = []
    for modulo, paquete in dependencias:
        try:
            __import__(modulo)
            print(f"[OK] {modulo} está instalado")
        except ImportError:
            print(f"[WARN] {modulo} no está instalado")
            faltantes.append(paquete)
    
    if faltantes:
        print(f"\n[ERROR] Faltan dependencias: {', '.join(faltantes)}")
        print("Instálalas con: pip install opencv-python pyttsx3")
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
