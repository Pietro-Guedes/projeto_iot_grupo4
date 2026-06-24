import cv2
import serial
import serial.tools.list_ports
import time
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

# ─── CONFIGURAÇÃO ─────────────────────────────────────────────────
PORTA_SERIAL   = "COM3"
BAUD_RATE      = 115200
INDICE_CAMERA  = 0
ANGULO_MIN     = 20
ANGULO_MAX     = 160
INTERVALO_ENV  = 0.1
STREAM_PORT    = 5000   # acesse http://<IP_DO_PC>:5000 no dashboard
# ──────────────────────────────────────────────────────────────────

# Frame compartilhado entre thread da câmera e servidor HTTP
frame_atual = None
frame_lock  = threading.Lock()

# ─── SERVIDOR MJPEG ───────────────────────────────────────────────
class MJPEGHandler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass  # silencia logs do servidor

    def do_GET(self):
        if self.path == "/stream":
            self.send_response(200)
            self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            try:
                while True:
                    with frame_lock:
                        f = frame_atual
                    if f is None:
                        time.sleep(0.05)
                        continue
                    _, jpg = cv2.imencode(".jpg", f, [cv2.IMWRITE_JPEG_QUALITY, 70])
                    data = jpg.tobytes()
                    self.wfile.write(
                        b"--frame\r\nContent-Type: image/jpeg\r\n"
                        b"Content-Length: " + str(len(data)).encode() + b"\r\n\r\n"
                        + data + b"\r\n"
                    )
            except:
                pass
        else:
            self.send_response(404)
            self.end_headers()

def iniciar_servidor():
    srv = HTTPServer(("0.0.0.0", STREAM_PORT), MJPEGHandler)
    print(f"[STREAM] Servidor MJPEG em http://0.0.0.0:{STREAM_PORT}/stream")
    srv.serve_forever()

threading.Thread(target=iniciar_servidor, daemon=True).start()

# ─── SERIAL ───────────────────────────────────────────────────────
def descobrir_porta_pico():
    for p in serial.tools.list_ports.comports():
        desc = p.description.lower()
        if "pico" in desc or "usb serial" in desc or "uart" in desc:
            return p.device
    return None

def conectar_serial(porta):
    try:
        s = serial.Serial(porta, BAUD_RATE, timeout=1)
        print(f"[SERIAL] Conectado em {porta}")
        return s
    except serial.SerialException as e:
        print(f"[SERIAL] Erro ao conectar em {porta}: {e}")
        return None

porta_auto = descobrir_porta_pico()
if porta_auto:
    print(f"[SERIAL] Pico detectado automaticamente: {porta_auto}")
    PORTA_SERIAL = porta_auto

serial_pico = conectar_serial(PORTA_SERIAL)
sem_serial  = serial_pico is None
if sem_serial:
    print("[AVISO] Rodando SEM serial — só visualização, servo não vai mover.")

# ─── CÂMERA E DETECTOR ────────────────────────────────────────────
def posicao_para_angulo(centro_x, largura_frame):
    angulo = ANGULO_MAX - int((centro_x / largura_frame) * (ANGULO_MAX - ANGULO_MIN))
    return max(ANGULO_MIN, min(ANGULO_MAX, angulo))

camera   = cv2.VideoCapture(INDICE_CAMERA)
detector = cv2.CascadeClassifier(
    cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
)

if not camera.isOpened():
    print("[CÂMERA] Erro: não foi possível acessar a câmera.")
    exit(1)

print("[CÂMERA] Iniciada. Pressione 'q' para encerrar.")
print(f"[STREAM] URL para o dashboard: http://<SEU_IP>:{STREAM_PORT}/stream")

ultimo_envio  = 0
ultimo_angulo = -1

try:
    while True:
        ret, frame = camera.read()
        if not ret:
            print("[CÂMERA] Erro ao ler frame.")
            break

        altura, largura = frame.shape[:2]
        cinza = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        rostos = detector.detectMultiScale(
            cinza,
            scaleFactor=1.2,
            minNeighbors=5,
            minSize=(60, 60)
        )

        rosto_detectado = len(rostos) > 0
        agora = time.time()

        if rosto_detectado:
            maior = max(rostos, key=lambda r: r[2] * r[3])
            x, y, w, h = maior

            centro_x = x + w // 2
            centro_y = y + h // 2
            angulo   = posicao_para_angulo(centro_x, largura)

            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 255), 2)
            cv2.circle(frame,  (centro_x, centro_y), 5, (0, 255, 255), -1)
            cv2.line(frame,    (largura//2, 0), (largura//2, altura), (100, 100, 100), 1)
            cv2.putText(frame, f"Servo: {angulo}°",
                        (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX,
                        0.6, (0, 255, 255), 2)

            if not sem_serial and (agora - ultimo_envio >= INTERVALO_ENV):
                try:
                    serial_pico.write(f"SERVO:{angulo}\n".encode())
                    serial_pico.write(b"MOVIMENTO\n")
                    ultimo_envio  = agora
                    ultimo_angulo = angulo
                    print(f"[SERVO] {angulo}°  X={centro_x}")
                except serial.SerialException as e:
                    print(f"[SERIAL] Erro ao enviar: {e}")

            cv2.putText(frame, "ROSTO DETECTADO", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 100), 2)
            cv2.putText(frame, f"X: {centro_x}/{largura}  Angulo: {angulo}°",
                        (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (200, 200, 200), 1)
        else:
            cv2.putText(frame, "Aguardando rosto...", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (100, 100, 255), 2)
            cv2.line(frame, (largura//2, 0), (largura//2, altura), (60, 60, 60), 1)

        # Atualiza frame compartilhado com o servidor MJPEG
        with frame_lock:
            frame_atual = frame.copy()

        cv2.imshow("Reconhecimento Facial + Servo", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

except KeyboardInterrupt:
    print("\n[INFO] Encerrado pelo usuário.")

finally:
    camera.release()
    cv2.destroyAllWindows()
    if serial_pico and serial_pico.is_open:
        serial_pico.close()
        print("[SERIAL] Porta fechada.")
    print("[INFO] Encerrado.")