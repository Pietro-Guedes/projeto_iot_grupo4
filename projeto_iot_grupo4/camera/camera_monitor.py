import serial
import cv2
import os
from datetime import datetime
 
# ─── CONFIGURAÇÃO ─────────────────────────────────────────────────
PORTA_SERIAL  = "COM3"       # ← troque pela porta do seu Pico (use listar_portas.py)
BAUD_RATE     = 115200
PASTA_FOTOS   = "fotos"      # pasta onde as fotos serão salvas
INDICE_CAMERA = 0            # 0 = webcam padrão; troque se tiver mais de uma câmera
# ──────────────────────────────────────────────────────────────────
 
os.makedirs(PASTA_FOTOS, exist_ok=True)
 
def capturar_foto():
    """Abre a câmera, captura um frame, salva com timestamp e exibe por 3s."""
    cam = cv2.VideoCapture(INDICE_CAMERA)
 
    if not cam.isOpened():
        print("[CÂMERA] Erro: não foi possível acessar a câmera.")
        return
 
    ret, frame = cam.read()
 
    if ret:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        nome_arquivo = os.path.join(PASTA_FOTOS, f"invasor_{timestamp}.jpg")
        cv2.imwrite(nome_arquivo, frame)
        print(f"[CÂMERA] Foto salva: {nome_arquivo}")
 
        # Mostra a captura por 3 segundos
        cv2.imshow("Intruso detectado", frame)
        cv2.waitKey(3000)
    else:
        print("[CÂMERA] Erro ao capturar frame.")
 
    cam.release()
    cv2.destroyAllWindows()
 
# ─── LOOP PRINCIPAL ───────────────────────────────────────────────
print(f"[SERIAL] Conectando em {PORTA_SERIAL} @ {BAUD_RATE}...")
 
try:
    porta = serial.Serial(PORTA_SERIAL, BAUD_RATE, timeout=1)
    print(f"[SERIAL] Aguardando mensagens do Pico...")
    print("[SERIAL] Pressione Ctrl+C para encerrar.\n")
 
    while True:
        if porta.in_waiting > 0:
            linha = porta.readline().decode(errors="ignore").strip()
 
            if not linha:
                continue
 
            print(f"[SERIAL] Recebido: {linha}")
 
            if linha == "MOVIMENTO":
                print("[CÂMERA] Movimento detectado — capturando foto...")
                capturar_foto()
 
except serial.SerialException as e:
    print(f"[ERRO] Porta serial: {e}")
    print("       Verifique se o Pico está conectado e se a porta está correta.")
    print("       Use listar_portas.py para descobrir a porta.")
 
except KeyboardInterrupt:
    print("\n[SERIAL] Encerrado pelo usuário.")
 
finally:
    try:
        porta.close()
        print("[SERIAL] Porta fechada.")
    except:
        pass