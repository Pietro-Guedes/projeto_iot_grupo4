const CONFIG = {
    broker:    "ws://10.132.112.5:9001",
    topicSub:  "senai/grupo4/sensores",
    clientId:  "dashboard_" + Math.random().toString(16).slice(2, 8),
 
    // ↓ TROQUE pelo IP do seu PC na rede WiFi_IOT, mantenha a porta 5000
    cameraUrl: "http://10.132.112.24:5000/stream"
}
 
let cliente = null
 
const statusDot      = document.getElementById("status-dot")
const statusTexto    = document.getElementById("status-texto")
const ultimaAtu      = document.getElementById("ultima-atualizacao")
const logEl          = document.getElementById("log")
const cardPresenca   = document.querySelector(".card-presenca")
const elPresenca     = document.getElementById("presenca")
const elPresencaSts  = document.getElementById("presenca-status")
const elLuminosidade = document.getElementById("luminosidade")
const cardLed        = document.querySelector(".card-led")
const elLedValor     = document.getElementById("led-card-valor")
const elLedStatus    = document.getElementById("led-card-status")
const ledBulb        = document.getElementById("led-bulb")
const ledBadge       = document.getElementById("led-badge")
const ledDescricao   = document.getElementById("led-descricao")
const cameraFeed     = document.getElementById("camera-feed")
const cameraOffline  = document.getElementById("camera-offline")
 
// ── Câmera MJPEG ──────────────────────────────────────────────────
// O reconhecimento.py já serve o stream — basta apontar a <img> para ele.
// A tag <img> aceita MJPEG nativamente em todos os navegadores modernos.
function iniciarCamera() {
    if (!CONFIG.cameraUrl || CONFIG.cameraUrl.includes("SEU_IP")) {
        log("Configure o IP do PC em CONFIG.cameraUrl no script.js para ver a câmera.", "info")
        return
    }
 
    cameraFeed.src = CONFIG.cameraUrl
    cameraFeed.style.display = "block"
    cameraOffline.style.display = "none"
 
    cameraFeed.onerror = () => {
        cameraFeed.style.display = "none"
        cameraOffline.style.display = "flex"
        log("Câmera offline — certifique-se que o reconhecimento.py está rodando.", "erro")
        // Tenta reconectar a cada 5s
        setTimeout(iniciarCamera, 5000)
    }
}
 
// ── Helpers ───────────────────────────────────────────────────────
function log(mensagem, tipo = "info") {
    const cores = { info:"#8b949e", sucesso:"#00ff88", erro:"#ff4444", recebido:"#ffaa00", enviado:"#00d4ff" }
    const hora = new Date().toLocaleTimeString("pt-BR")
    logEl.innerHTML += `<span style="color:${cores[tipo]}">[${hora}] ${mensagem}</span>\n`
    logEl.scrollTop = logEl.scrollHeight
}
 
function setStatus(conectado, texto) {
    statusDot.className     = "status-dot" + (conectado ? " conectado" : "")
    statusTexto.textContent = texto
}
 
function marcarAtualizacao() {
    ultimaAtu.textContent = "Última leitura: " + new Date().toLocaleTimeString("pt-BR")
}
 
function atualizarLed(ligado) {
    if (ligado) {
        ledBulb.classList.add("ligado")
        ledBadge.classList.add("ligado")
        ledBadge.textContent     = "LIGADO"
        ledDescricao.textContent = "LED aceso — escuridão com presença detectada."
        elLedValor.textContent   = "LIGADO"
        elLedStatus.textContent  = "LED aceso"
        cardLed.classList.add("led-ativo")
    } else {
        ledBulb.classList.remove("ligado")
        ledBadge.classList.remove("ligado")
        ledBadge.textContent     = "DESLIGADO"
        ledDescricao.textContent = "LED apagado — sem presença ou ambiente claro."
        elLedValor.textContent   = "DESLIGADO"
        elLedStatus.textContent  = "LED apagado"
        cardLed.classList.remove("led-ativo")
    }
}
 
function atualizarPresenca(detectada) {
    if (detectada) {
        elPresenca.textContent    = "SIM"
        elPresencaSts.textContent = "Movimento detectado"
        cardPresenca.classList.add("presenca-ativa")
    } else {
        elPresenca.textContent    = "NÃO"
        elPresencaSts.textContent = "Ambiente livre"
        cardPresenca.classList.remove("presenca-ativa")
    }
}
 
// Formato: "presenca:1,ldr:72.3,led:on"
function processarMensagem(mensagem) {
    log(`[REC] ${mensagem}`, "recebido")
    mensagem.split(",").forEach(parte => {
        const [chave, valor] = parte.split(":")
        if (chave === "presenca") atualizarPresenca(valor === "1")
        if (chave === "ldr") {
            elLuminosidade.textContent = valor
            // Alerta abaixo de 45.7% = raw < 30000 (limiar do config.py)
            document.querySelector(".card-ldr").classList.toggle("alerta", parseFloat(valor) < 45.7)
        }
        if (chave === "led") atualizarLed(valor === "on")
    })
    marcarAtualizacao()
}
 
// ── MQTT ──────────────────────────────────────────────────────────
function conectar() {
    log(`Conectando ao broker: ${CONFIG.broker}...`)
    setStatus(false, "Conectando...")
    cliente = mqtt.connect(CONFIG.broker, {
        clientId:        CONFIG.clientId,
        clean:           true,
        connectTimeout:  10000,
        reconnectPeriod: 3000
    })
    cliente.on("connect", () => {
        setStatus(true, `Conectado — ${CONFIG.topicSub}`)
        log("Conectado com sucesso!", "sucesso")
        cliente.subscribe(CONFIG.topicSub, err => {
            if (!err) log(`[SUB] Assinando: ${CONFIG.topicSub}`, "info")
            else      log(`[SUB] Erro: ${err.message}`, "erro")
        })
    })
    cliente.on("message", (_, payload) => processarMensagem(payload.toString()))
    cliente.on("error",   err => { log(`[ERRO] ${err.message}`, "erro"); setStatus(false, "Erro de conexão") })
    cliente.on("close",   ()  => { setStatus(false, "Desconectado — reconectando..."); log("Conexão encerrada.", "erro") })
}
 
iniciarCamera()
conectar()