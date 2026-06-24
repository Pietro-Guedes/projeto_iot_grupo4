from config import *
from wifi_connect import conectar_wifi
from umqtt.simple import MQTTClient
from machine import Pin, PWM, ADC
import utime
import sys

# Hardware
ldr    = ADC(PIN_LDR)
pir    = Pin(PIN_PIR,   Pin.IN)
led    = Pin(PIN_LED,   Pin.OUT)
buzzer = PWM(Pin(PIN_BUZZER))
botao  = Pin(PIN_BOTAO, Pin.IN, Pin.PULL_DOWN)
servo  = PWM(Pin(PIN_SERVO))
servo.freq(50)

# Servo
def mover_servo(angulo):
    angulo = max(0, min(180, int(angulo)))
    servo.duty_u16(int(1800 + (angulo / 180) * 6200))

mover_servo(90)

# Buzzer
def ligar_alarme():
    buzzer.freq(2500)
    buzzer.duty_u16(30000)

def desligar_alarme():
    buzzer.duty_u16(0)


def ldr_pct(raw):
    return round((raw / 65535) * 100, 1)

# Varredura NÃO bloqueante
_passo_varredura   = 0
_angulos_varredura = [0, 90, 180, 90]
_ultimo_varredura  = 0
PASSO_MS = 2000

def varrer_passo():
    global _passo_varredura, _ultimo_varredura
    agora = utime.ticks_ms()
    if utime.ticks_diff(agora, _ultimo_varredura) >= PASSO_MS:
        mover_servo(_angulos_varredura[_passo_varredura])
        _passo_varredura = (_passo_varredura + 1) % len(_angulos_varredura)
        _ultimo_varredura = agora

def resetar_varredura():
    global _passo_varredura
    _passo_varredura = 0
    mover_servo(90)

# PIR com debounce por tempo (evita falsos positivos / paradas repentinas)
# Só confirma presença se PIR ficar HIGH por PIR_DEBOUNCE_MS consecutivos.
# Só limpa presença se PIR ficar LOW por PIR_CLEAR_MS consecutivos.
_pir_alto_desde  = None   # ms quando subiu para HIGH
_pir_baixo_desde = None   # ms quando caiu para LOW
_pir_confirmado  = False  # estado estável atual

PIR_DEBOUNCE_MS = 300     # tempo mínimo HIGH para confirmar presença
PIR_CLEAR_MS    = 2000    # tempo mínimo LOW para limpar presença

def checar_pir():
    global _pir_alto_desde, _pir_baixo_desde, _pir_confirmado
    agora = utime.ticks_ms()
    if pir.value() == 1:
        _pir_baixo_desde = None
        if _pir_alto_desde is None:
            _pir_alto_desde = agora
        elif utime.ticks_diff(agora, _pir_alto_desde) >= PIR_DEBOUNCE_MS:
            _pir_confirmado = True
    else:
        _pir_alto_desde = None
        if _pir_baixo_desde is None:
            _pir_baixo_desde = agora
        elif utime.ticks_diff(agora, _pir_baixo_desde) >= PIR_CLEAR_MS:
            _pir_confirmado = False
    return _pir_confirmado

# Leitura serial sem bloquear
_buf = []

def ler_serial():
    try:
        import select
        if not select.select([sys.stdin], [], [], 0)[0]:
            return None
    except:
        pass
    try:
        c = sys.stdin.read(1)
        if c == "\n":
            linha = "".join(_buf).strip()
            _buf.clear()
            return linha or None
        _buf.append(c)
    except:
        pass
    return None


print("PIR regulando...")
utime.sleep(10)
print("Pronto.")

# Estado global
sistema_ativo       = False
ultimo_estado_botao = 0
estado_led          = False
ultimo_pisca        = 0
ultimo_pub          = 0

# Seguimento de rosto
seguindo_rosto   = False
ultimo_cmd_rosto = 0
TEMPO_ROSTO_MS   = 1000

# Presença pela câmera (persiste enquanto reconhecimento.py confirmar)
presenca_camera        = False
ultimo_presenca_camera = 0
TEMPO_PRESENCA_MS      = 1000

# WiFi + MQTT
if not conectar_wifi(WIFI_SSID, WIFI_PASS):
    print("[MAIN] Sem WiFi — reinicie o dispositivo.")
else:
    cliente = MQTTClient(CLIENT_ID, BROKER_IP, port=BROKER_PORT)
    try:
        cliente.connect()
        print(f"[MQTT] Broker: {BROKER_IP} | Tópico: {TOPIC_SENSORES}")

        # LOOP PRINCIPAL
        while True:

            # Botão liga/desliga
            estado_botao = botao.value()
            if estado_botao == 1 and ultimo_estado_botao == 0:
                sistema_ativo = not sistema_ativo
                if sistema_ativo:
                    print("SISTEMA ATIVADO")
                    for _ in range(2):
                        led.high(); utime.sleep_ms(150)
                        led.low();  utime.sleep_ms(150)
                else:
                    print("SISTEMA DESATIVADO")
                    desligar_alarme()
                    led.low()
                    resetar_varredura()
                    seguindo_rosto  = False
                    presenca_camera = False
                    for _ in range(4):
                        led.high(); utime.sleep_ms(100)
                        led.low();  utime.sleep_ms(100)
                utime.sleep_ms(300)
            ultimo_estado_botao = estado_botao

            agora = utime.ticks_ms()

            # Lê serial
            cmd = ler_serial()
            if cmd:
                if cmd.startswith("SERVO:"):
                    try:
                        angulo = int(cmd.split(":")[1])
                        mover_servo(angulo)
                        seguindo_rosto         = True
                        ultimo_cmd_rosto       = agora
                        presenca_camera        = True
                        ultimo_presenca_camera = agora
                    except:
                        pass
                elif cmd == "MOVIMENTO":
                    presenca_camera        = True
                    ultimo_presenca_camera = agora

            # Expira seguimento de rosto
            if seguindo_rosto:
                if utime.ticks_diff(agora, ultimo_cmd_rosto) > TEMPO_ROSTO_MS:
                    seguindo_rosto = False

            # Expira presença da câmera
            if presenca_camera:
                if utime.ticks_diff(agora, ultimo_presenca_camera) > TEMPO_PRESENCA_MS:
                    presenca_camera = False

            # Sistema desligado
            if not sistema_ativo:
                desligar_alarme()
                led.low()
                if utime.ticks_diff(agora, ultimo_pub) >= INTERVALO_PUB_MS:
                    luz_raw = ldr.read_u16()
                    msg = f"presenca:0,ldr:{ldr_pct(luz_raw)},led:off"
                    cliente.publish(TOPIC_SENSORES, msg.encode())
                    ultimo_pub = agora
                utime.sleep_ms(50)
                continue

            # Sensores
            luz_raw       = ldr.read_u16()
            escuro        = luz_raw < LDR_ESCURO
            movimento_pir = checar_pir()

            # Presença: PIR estável OU câmera
            presenca = movimento_pir or presenca_camera

            # Servo: varre sempre; pausa ao seguir rosto
            if not seguindo_rosto:
                varrer_passo()

            # LED: pisca só com presença E escuro
            if presenca and escuro and sistema_ativo:
                if utime.ticks_diff(agora, ultimo_pisca) >= 200:
                    estado_led = not estado_led
                    led.value(estado_led)
                    ultimo_pisca = agora
            else:
                led.low()
                estado_led = False

            # Alarme
            if presenca:
                ligar_alarme()
                if escuro:
                    print("INVASOR DETECTADO")
                else:
                    print("MOVIMENTO DETECTADO")
            else:
                desligar_alarme()

            # Publicação MQTT
            if utime.ticks_diff(agora, ultimo_pub) >= INTERVALO_PUB_MS:
                led_estado   = "on" if estado_led else "off"
                presenca_val = 1 if presenca else 0
                msg = f"presenca:{presenca_val},ldr:{ldr_pct(luz_raw)},led:{led_estado}"
                cliente.publish(TOPIC_SENSORES, msg.encode())
                print(f"[PUB] {msg}")
                ultimo_pub = agora

            utime.sleep_ms(50)

    except Exception as e:
        print(f"[ERRO] {e}")
        led.low()
        desligar_alarme()

    finally:
        try:
            cliente.disconnect()
            print("[MQTT] Desconectado.")
        except:
            pass