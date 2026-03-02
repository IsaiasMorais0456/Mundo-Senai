from flask import Flask, render_template, Response, jsonify
import cv2
from detector_sonolencia_motorista import DetectorSonolencia
import threading
import time
import logging
import os
import requests

# Configuração de logging mais limpa
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s: %(message)s',
    datefmt='%H:%M:%S'
)

# Desabilita logs do Flask
logging.getLogger('werkzeug').disabled = True

app = Flask(__name__)
app.logger.disabled = True

# Configurações para desenvolvimento
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
app.config['TEMPLATES_AUTO_RELOAD'] = True

# Variáveis globais para compartilhar estado
estado_atual = {
    'status': 'Normal',
    'blink_count': 0,
    'eyes_closed_time': 0,
    'static_eyes_time': 0,
    'ear_value': 0.3  # Valor inicial do EAR
}

# Inicializa o detector
detector = DetectorSonolencia()
camera = cv2.VideoCapture(0)

# Configurações da câmera
camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
camera.set(cv2.CAP_PROP_FPS, 30)

# Configuração do Carrinho
CARRINHO_IP = "192.168.0.100" # 192.168.0.100

# Variáveis de controle
ultimo_envio = 0
INTERVALO_ENVIO = 500
ultimo_nivel_alerta = 0  # Para controlar mudanças no nível de alerta

def enviar_sinal_esp(nivel_alerta):
    global ultimo_envio, ultimo_nivel_alerta
    
    print("\n=== Status do Alerta ===")
    print(f"Nível de alerta atual: {nivel_alerta}")
    print(f"Último nível de alerta: {ultimo_nivel_alerta}")
    print(f"Tempo desde último envio: {int(time.time() * 1000) - ultimo_envio}ms")
    
    # Só envia se o nível de alerta mudou
    if nivel_alerta == ultimo_nivel_alerta:
        print("➡️ Nível de alerta não mudou, ignorando...")
        return
        
    ultimo_nivel_alerta = nivel_alerta
    tempo_atual = int(time.time() * 1000)
    
    # Só envia se passou tempo suficiente desde o último envio
    if tempo_atual - ultimo_envio < INTERVALO_ENVIO:
        print(f"➡️ Aguardando intervalo mínimo ({INTERVALO_ENVIO}ms)...")
        return
        
    ultimo_envio = tempo_atual
    
    # Headers para evitar problemas de CORS ou cache
    headers = {
        'Cache-Control': 'no-cache',
        'Accept': '*/*'
    }
    
    try:
        # Se o nível de alerta for 2 (Perigo - olhos fechados por mais de 4 segundos)
        if nivel_alerta == 2:
            url = f"http://{CARRINHO_IP}/alerta_olhos"
            print(f"⚠️ Enviando alerta para: {url}")
            try:
                print("Fazendo requisição HTTP...")
                response = requests.get(url, timeout=2.0, headers=headers)  # Aumentado para 2 segundos
                print(f"Status code: {response.status_code}")
                print(f"Resposta: {response.text}")
                if response.status_code == 200:
                    print("✅ Alerta enviado com sucesso para o carrinho!")
                else:
                    print(f"❌ Erro: Status code {response.status_code}")
            except Exception as e:
                print(f"❌ Erro ao enviar alerta: {str(e)}")
                print(f"Tipo de erro: {type(e).__name__}")
        # Se o nível de alerta for 0 (Normal - olhos abertos)
        elif nivel_alerta == 0:
            url = f"http://{CARRINHO_IP}/olhos_abertos"
            print(f"👁️ Enviando sinal de olhos abertos para: {url}")
            try:
                print("Fazendo requisição HTTP...")
                response = requests.get(url, timeout=2.0, headers=headers)  # Aumentado para 2 segundos
                print(f"Status code: {response.status_code}")
                print(f"Resposta: {response.text}")
                if response.status_code == 200:
                    print("✅ Sinal de olhos abertos enviado com sucesso!")
                else:
                    print(f"❌ Erro: Status code {response.status_code}")
            except Exception as e:
                print(f"❌ Erro ao enviar sinal de olhos abertos: {str(e)}")
                print(f"Tipo de erro: {type(e).__name__}")
    except Exception as e:
        print(f"❌ Erro geral ao enviar sinal: {str(e)}")
        print(f"Tipo de erro: {type(e).__name__}")

def gerar_frames():
    frame_count = 0
    while True:
        try:
            success, frame = camera.read()
            if not success:
                print("Erro ao capturar frame da câmera")
                time.sleep(0.1)  # Pequeno delay antes de tentar novamente
                continue
            
            # Processa apenas a cada 2 frames para melhorar desempenho
            frame_count += 1
            if frame_count % 2 != 0:
                continue
            
            # Processa o frame com o detector
            frame_processado = detector.processar_frame(frame)
            
            # Atualiza estado global
            global estado_atual
            ear_medio = 0.3  # Valor padrão
            if hasattr(detector, 'historico_ear') and len(detector.historico_ear) > 0:
                ear_medio = float(detector.historico_ear[-1])
            
            estado_atual.update({
                'status': 'Normal' if detector.nivel_alerta == 0 else 'Atenção' if detector.nivel_alerta == 1 else 'Perigo',
                'blink_count': len(detector.historico_piscadas),
                'eyes_closed_time': round(detector.tempo_olhos_fechados, 1),
                'static_eyes_time': round(detector.tempo_olhos_estaticos, 1),
                'ear_value': round(ear_medio, 3)
            })
            
            # Envia sinal para o carrinho baseado no nível de alerta
            enviar_sinal_esp(detector.nivel_alerta)
            
            # Converte o frame para JPEG
            ret, buffer = cv2.imencode('.jpg', frame_processado, [cv2.IMWRITE_JPEG_QUALITY, 80])
            frame_bytes = buffer.tobytes()
            
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
            
        except Exception as e:
            print(f"Erro ao processar frame: {str(e)}")
            time.sleep(0.1)  # Pequeno delay em caso de erro
            continue

@app.route('/')
def index():
    # Adiciona um timestamp para evitar cache
    return render_template('index.html', timestamp=time.time())

@app.route('/video_feed')
def video_feed():
    return Response(gerar_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/status')
def get_status():
    return jsonify(estado_atual)

def clear_terminal():
    os.system('cls' if os.name == 'nt' else 'clear')

def cleanup():
    print("Limpando recursos...")
    camera.release()
    detector.finalizar()

if __name__ == '__main__':
    try:
        clear_terminal()
        print("\n=== Sistema de Detecção de Sonolência ===")
        print("✨ Iniciando servidor web...")
        print("\n🌐 Acesse o sistema em:")
        print("   http://localhost:5000")
        print("\n⚡ Pressione Ctrl+C para encerrar\n")
        app.run(host='0.0.0.0', port=5000, debug=True)  # Mudado para debug=True
    except KeyboardInterrupt:
        print("\n\n👋 Sistema encerrado pelo usuário")
    finally:
        cleanup() 