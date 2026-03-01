#!/usr/bin/env python3
"""
Autoría: Alejandro Paredero - alejandro.paredero@cunef.edu
"""

import os
import time
import subprocess
import shutil
from pathlib import Path

import cv2


class CapturaConProceso:
    def __init__(self, cap, proc=None):
        self.cap = cap
        self.proc = proc

    def read(self):
        return self.cap.read()

    def release(self):
        try:
            self.cap.release()
        finally:
            if self.proc is not None:
                try:
                    self.proc.terminate()
                    self.proc.wait(timeout=2)
                except Exception:
                    try:
                        self.proc.kill()
                    except Exception:
                        pass


class CapturaPicamera2:
    def __init__(self, picam):
        self.picam = picam

    def read(self):
        try:
            frame_rgb = self.picam.capture_array()
            if frame_rgb is None or frame_rgb.size == 0:
                return False, None
            frame_bgr = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)
            return True, frame_bgr
        except Exception:
            return False, None

    def release(self):
        try:
            self.picam.stop()
        except Exception:
            pass
        try:
            self.picam.close()
        except Exception:
            pass


def listar_dispositivos_video():
    dispositivos = sorted(Path('/dev').glob('video*'))
    return [str(d) for d in dispositivos]


def abrir_csi_libcamera(ancho=640, alto=480, fps=30):
    pipeline = (
        f"libcamerasrc ! video/x-raw,width={ancho},height={alto},framerate={fps}/1 "
        "! videoconvert ! appsink drop=true max-buffers=1 sync=false"
    )
    cap = cv2.VideoCapture(pipeline, cv2.CAP_GSTREAMER)
    if not cap.isOpened():
        cap.release()
        return None

    ok, frame = cap.read()
    if ok and frame is not None and frame.size > 0:
        return cap

    cap.release()
    return None


def abrir_csi_picamera2(ancho=640, alto=480, fps=30):
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
        frame = picam.capture_array()
        if frame is None or frame.size == 0:
            picam.stop()
            picam.close()
            return None
        return CapturaPicamera2(picam)
    except Exception:
        return None


def abrir_csi_rpicam(ancho=640, alto=480, fps=30):
    if shutil.which("rpicam-vid") is None:
        return None

    puerto = 5600
    base_cmd = [
        "rpicam-vid",
        "-n",
        "-t", "0",
        "--width", str(ancho),
        "--height", str(alto),
        "--framerate", str(fps),
        "--codec", "mjpeg",
    ]

    try:
        proc = subprocess.Popen(
            base_cmd + ["-o", f"udp://127.0.0.1:{puerto}"],
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
            ok, frame = cap.read()
            if ok and frame is not None and frame.size > 0:
                return CapturaConProceso(cap, proc)
            if proc.poll() is not None:
                break
            time.sleep(0.03)

        cap.release()
        proc.terminate()
    except Exception:
        return None

    return None


def abrir_v4l2_por_indice(idx, ancho=640, alto=480):
    cap = cv2.VideoCapture(idx, cv2.CAP_V4L2)
    if not cap.isOpened():
        cap.release()
        return None

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, ancho)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, alto)

    ok, frame = cap.read()
    if ok and frame is not None and frame.size > 0:
        return cap

    cap.release()
    return None


def abrir_camara():
    print('[INFO] Buscando cámara...')
    dispositivos = listar_dispositivos_video()
    if dispositivos:
        print('[INFO] Dispositivos detectados:', ', '.join(dispositivos))
    else:
        print('[WARN] No se detectaron nodos /dev/video*')

    print('[INFO] Intentando primero cámara CSI (Picamera2)...')
    cap_csi = abrir_csi_picamera2()
    if cap_csi is not None:
        print('[OK] Cámara CSI operativa vía Picamera2')
        return cap_csi, 'CSI/Picamera2'

    print('[INFO] Picamera2 no disponible. Intentando cámara CSI (rpicam-vid)...')
    cap_csi = abrir_csi_rpicam()
    if cap_csi is not None:
        print('[OK] Cámara CSI operativa vía rpicam-vid (UDP)')
        return cap_csi, 'CSI/rpicam-vid'

    print('[INFO] rpicam-vid no disponible. Intentando CSI por libcamerasrc...')
    cap_csi = abrir_csi_libcamera()
    if cap_csi is not None:
        print('[OK] Cámara CSI operativa vía libcamerasrc')
        return CapturaConProceso(cap_csi), 'CSI/libcamerasrc'

    print('[INFO] CSI no disponible. Probando fallback USB/V4L2...')
    candidatos = []
    for dev in dispositivos:
        try:
            candidatos.append(int(dev.replace('/dev/video', '')))
        except ValueError:
            continue

    for idx in sorted(set(candidatos)):
        cap = abrir_v4l2_por_indice(idx)
        if cap is not None:
            print(f'[OK] Cámara funcional en /dev/video{idx}')
            return cap, f'/dev/video{idx}'

    return None, None


def main():
    has_gui = bool(os.environ.get('DISPLAY'))
    cap, idx = abrir_camara()

    if cap is None:
        print('[ERROR] No se pudo abrir ninguna cámara.')
        print('[INFO] Comprueba conexión, permisos y dispositivo con: ls /dev/video*')
        raise SystemExit(1)

    if not has_gui:
        print('[INFO] Modo headless detectado (sin DISPLAY).')
        print('[INFO] Leyendo frames durante 10 segundos...')
        start = time.time()
        frames = 0

        while time.time() - start < 10:
            ok, frame = cap.read()
            if ok and frame is not None and frame.size > 0:
                frames += 1
            time.sleep(0.03)

        cap.release()
        print(f'[OK] Cámara /dev/video{idx} funcionando. Frames leídos: {frames}')
        return

    print("[INFO] Ventana de prueba abierta. Pulsa 'q' o ESC para salir.")
    print(f'[INFO] Usando {idx}')

    while True:
        ok, frame = cap.read()
        if not ok or frame is None or frame.size == 0:
            print('[WARN] Error leyendo frame de la cámara')
            break

        cv2.imshow('Prueba de Camara - q o ESC para salir', frame)
        key = cv2.waitKey(1) & 0xFF
        if key in (ord('q'), ord('Q'), 27):
            break

    cap.release()
    cv2.destroyAllWindows()
    print('[OK] Prueba de cámara finalizada.')


if __name__ == '__main__':
    main()
