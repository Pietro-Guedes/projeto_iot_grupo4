WIFI_SSID = "WIFI_IOT"
WIFI_PASS = "Ac1ce2ss5@IOT"
 
# ── Broker MQTT ───────────────────────────────────────────────────
BROKER_IP   = "10.132.112.5"
BROKER_PORT = 1883
 
# ── Identificação ─────────────────────────────────────────────────
MEU_NOME  = "Grupo4"
CLIENT_ID = f"pico_{MEU_NOME.lower()}"
 
# ── Tópico MQTT ───────────────────────────────────────────────────
# Formato publicado: "presenca:1,ldr:72.3,led:on"
TOPIC_SENSORES = f"senai/{MEU_NOME.lower()}/sensores"
 
# ── Pinos ─────────────────────────────────────────────────────────
PIN_LDR    = 26
PIN_PIR    = 18
PIN_LED    = 16
PIN_BUZZER = 17
PIN_BOTAO  = 19
PIN_SERVO  = 20
 
# ── Limiar de escuridão (raw ADC 0–65535) ─────────────────────────
LDR_ESCURO = 30000
 
# ── Intervalo mínimo de publicação MQTT (ms) ──────────────────────
INTERVALO_PUB_MS = 500