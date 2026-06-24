import network
from utime import sleep
 
def conectar_wifi(ssid, senha, timeout=15):
    """
    Conecta o Pico 2W à rede WiFi.
    Retorna True se conectou, False se falhou.
    """
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
 
    if wlan.isconnected():
        print(f"[WiFi] Já conectado. IP: {wlan.ifconfig()[0]}")
        return True
 
    print(f"[WiFi] Conectando em '{ssid}'", end="")
    wlan.connect(ssid, senha)
 
    while not wlan.isconnected() and timeout > 0:
        sleep(1)
        timeout -= 1
        print(".", end="")
 
    print()
 
    if wlan.isconnected():
        ip = wlan.ifconfig()[0]
        print(f"[WiFi] Conectado! IP do Pico: {ip}")
        return True
    else:
        print("[WiFi] ERRO: não conectou. Verifique SSID e senha.")
        return False