import cv2
import mediapipe as mp
import numpy as np
from ear_utils import calcular_ear
import serial
import time
from datetime import datetime
import json
import os
from collections import deque
import pygame  # Para alertas sonoros

class DetectorSonolencia:
    def __init__(self, porta_serial='COM3', ear_limiar=0.2):
        self.ear_limiar = ear_limiar
        self.esp32 = self._conectar_esp32(porta_serial)
        print("🔍 Iniciando sistema de detecção facial...")
        self.configurar_face_mesh()
        self.configurar_indices_olhos()
        
        # Configurações para detecção de sonolência
        self.tempo_olhos_fechados = 0
        self.inicio_olhos_fechados = None
        self.piscadas_consecutivas = 0
        self.ultima_piscada = time.time()
        self.alerta_ativo = False
        self.nivel_alerta = 0  # 0: Normal, 1: Atenção, 2: Perigo
        
        # Novos parâmetros para detecção de fadiga
        self.ear_anterior = None
        self.tempo_olhos_estaticos = 0
        self.inicio_olhos_estaticos = None
        self.historico_piscadas = []
        self.ultima_variacao = time.time()
        
        # Limites de tempo para alertas (em segundos)
        self.TEMPO_ALERTA = 1.0      # Mantido em 1.0 segundo
        self.TEMPO_PERIGO = 2.0      # Mantido em 2.0 segundos
        self.TEMPO_ESTATICO_MAX = 5.0  # Aumentado para 5.0 segundos
        self.LIMIAR_VARIACAO_EAR = 0.02  # Diminuido para 0.02
        self.MAX_PISCADAS_INTERVALO = 6  # Mantido em 6 piscadas
        self.INTERVALO_ANALISE_PISCADAS = 3.0  # Mantido em 3 segundos
        
        # Inicializa sistema de som
        pygame.init()
        pygame.mixer.init()
        self.som_alerta = pygame.mixer.Sound("alerta.wav") if os.path.exists("alerta.wav") else None
        
        # Histórico para análise
        self.historico_ear = deque(maxlen=300)
        self.eventos_sonolencia = []
        print("✅ Sistema iniciado com sucesso!")
        
    def _conectar_esp32(self, porta):
        try:
            print(f"Tentando conectar ao ESP32 na porta {porta}...")
            esp32 = serial.Serial(porta, 115200, timeout=1)
            time.sleep(2)  # Aguarda inicialização do ESP32
            
            # Limpa o buffer de entrada
            while esp32.in_waiting:
                esp32.readline()
            
            # Envia comando de teste
            esp32.write(b'0\n')
            esp32.flush()
            time.sleep(0.1)
            
            # Lê resposta usando ascii e ignorando erros
            if esp32.in_waiting:
                resposta = esp32.readline().decode('ascii', errors='ignore').strip()
                print(f"Resposta do ESP32: {resposta}")
            
            print(f"✅ ESP32 conectado na porta {porta}")
            return esp32
        except Exception as e:
            print(f"❌ Erro ao conectar ESP32: {str(e)}")
            print("ℹ️ ESP32 não detectado - sistema funcionará sem LED")
            return None

    def configurar_face_mesh(self):
        self.mp_face_mesh = mp.solutions.face_mesh
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            static_image_mode=False,
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )

    def configurar_indices_olhos(self):
        self.olho_esquerdo_idx = [362, 385, 387, 263, 373, 380]
        self.olho_direito_idx = [33, 160, 158, 133, 153, 144]

    def _detectar_sonolencia(self, ear_medio):
        tempo_atual = time.time()
        self.historico_ear.append(ear_medio)
        
        # Detecção de olhos fechados
        if ear_medio <= self.ear_limiar:
            if self.inicio_olhos_fechados is None:
                self.inicio_olhos_fechados = tempo_atual
            
            self.tempo_olhos_fechados = tempo_atual - self.inicio_olhos_fechados
            
            # Verifica diferentes níveis de alerta
            if self.tempo_olhos_fechados >= self.TEMPO_PERIGO:
                self.nivel_alerta = 2  # Perigo - LED piscando
                self._registrar_evento("perigo_olhos_fechados")
            elif self.tempo_olhos_fechados >= self.TEMPO_ALERTA:
                self.nivel_alerta = 1  # Atenção - LED aceso
                self._registrar_evento("alerta_olhos_fechados")
            
            # Registra piscada
            if self.ear_anterior is not None and self.ear_anterior > self.ear_limiar:
                self.historico_piscadas.append(tempo_atual)
                # Remove piscadas antigas do histórico
                self.historico_piscadas = [t for t in self.historico_piscadas 
                                         if tempo_atual - t <= self.INTERVALO_ANALISE_PISCADAS]
        else:
            self.inicio_olhos_fechados = None
            self.tempo_olhos_fechados = 0
            
            # Detecção de olhos estáticos
            if self.ear_anterior is not None:
                variacao = abs(ear_medio - self.ear_anterior)
                if variacao < self.LIMIAR_VARIACAO_EAR:
                    if self.inicio_olhos_estaticos is None:
                        self.inicio_olhos_estaticos = tempo_atual
                    self.tempo_olhos_estaticos = tempo_atual - self.inicio_olhos_estaticos
                    
                    if self.tempo_olhos_estaticos >= self.TEMPO_ESTATICO_MAX:
                        self.nivel_alerta = 1  # Atenção - olhos estáticos
                        self._registrar_evento("alerta_olhos_estaticos")
                else:
                    self.inicio_olhos_estaticos = None
                    self.tempo_olhos_estaticos = 0
                    self.ultima_variacao = tempo_atual
            
            # Verifica frequência de piscadas
            if len(self.historico_piscadas) >= self.MAX_PISCADAS_INTERVALO:
                self.nivel_alerta = max(1, self.nivel_alerta)  # Pelo menos nível 1
                self._registrar_evento("alerta_piscadas_frequentes")
            
            # Reset do nível de alerta se não houver condições de alerta
            if (self.nivel_alerta > 0 and 
                self.tempo_olhos_estaticos < self.TEMPO_ESTATICO_MAX and 
                len(self.historico_piscadas) < self.MAX_PISCADAS_INTERVALO):
                self.nivel_alerta = 0
        
        self.ear_anterior = ear_medio
        return self.nivel_alerta

    def _registrar_evento(self, tipo_evento):
        self.eventos_sonolencia.append({
            "tipo": tipo_evento,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "ear_medio": np.mean(self.historico_ear),
            "nivel_alerta": self.nivel_alerta
        })

    def _emitir_alerta(self, frame, nivel_alerta):
        if nivel_alerta > 0:
            # Configurações de fonte e estilo
            fonte = cv2.FONT_HERSHEY_SIMPLEX
            cor_texto = (255, 255, 255)  # Branco
            espessura_texto = 2
            altura, largura = frame.shape[:2]

            # Cria uma cópia do frame para os efeitos
            overlay = frame.copy()
            
            if nivel_alerta == 2:  # Perigo
                # Borda vermelha pulsante em toda a tela
                espessura_borda = 20
                cv2.rectangle(frame, (0, 0), (largura, altura), (0, 0, 255), espessura_borda)
                
                # Barra de alerta vermelha com transparência
                y_pos = 30
                altura_barra = 80  # Aumentada
                cv2.rectangle(overlay, (0, y_pos), (largura, y_pos + altura_barra), (0, 0, 200), -1)
                mensagem = "⚠️ PERIGO! MICRO-SONO DETECTADO ⚠️"
                
                # Adiciona efeito de flash vermelho
                alpha = 0.3 * (1 + np.sin(time.time() * 5)) / 2  # Efeito pulsante
                cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0, frame)
                
            else:  # Atenção
                # Barra de alerta amarela com transparência
                y_pos = 30
                altura_barra = 60
                cv2.rectangle(overlay, (0, y_pos), (largura, y_pos + altura_barra), (0, 165, 255), -1)
                
                # Determina a mensagem baseada no tipo de alerta
                if self.tempo_olhos_estaticos >= self.TEMPO_ESTATICO_MAX:
                    mensagem = "⚠️ ATENÇÃO! OLHOS FIXOS POR MUITO TEMPO"
                elif len(self.historico_piscadas) >= self.MAX_PISCADAS_INTERVALO:
                    mensagem = "⚠️ ATENÇÃO! PISCADAS MUITO FREQUENTES"
                else:
                    mensagem = "⚠️ ATENÇÃO! SINAIS DE SONOLÊNCIA"

            # Aplica transparência à barra de alerta
            cv2.addWeighted(overlay, 0.5, frame, 0.5, 0, frame)

            # Adiciona o texto centralizado
            tamanho_texto = cv2.getTextSize(mensagem, fonte, 1.2, espessura_texto)[0]
            x_pos = (largura - tamanho_texto[0]) // 2
            cv2.putText(frame, mensagem, (x_pos, y_pos + 45), 
                       fonte, 1.2, cor_texto, espessura_texto)

            # Adiciona informações adicionais em uma barra inferior
            info_barra_y = altura - 40
            cv2.rectangle(overlay, (0, info_barra_y - 30), (largura, altura), (0, 0, 0), -1)
            cv2.addWeighted(overlay, 0.5, frame, 0.5, 0, frame)

            # Adiciona métricas na barra inferior
            info_texto = f"EAR: {np.mean(self.historico_ear):.2f} | Piscadas: {len(self.historico_piscadas)} | Tempo Olhos Fechados: {self.tempo_olhos_fechados:.1f}s"
            cv2.putText(frame, info_texto, (10, info_barra_y), 
                       fonte, 0.7, cor_texto, 1)

        else:
            self.alerta_ativo = False
            if self.esp32:
                print("Enviando comando NORMAL (0)")
                self.esp32.write(b'0\n')
                self.esp32.flush()
                time.sleep(0.1)
                while self.esp32.in_waiting:
                    resposta = self.esp32.readline().decode('ascii', errors='ignore').strip()
                    print(f"Resposta ESP32: {resposta}")

        return frame

    def processar_frame(self, frame):
        if frame is None:
            return None
        
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        resultado = self.face_mesh.process(rgb)
        
        if not resultado.multi_face_landmarks:
            # Se não detectar rosto, considera como potencial distração/sono
            if self.inicio_olhos_fechados is None:
                self.inicio_olhos_fechados = time.time()
            return frame
        
        frame_processado = frame.copy()
        h, w, _ = frame.shape
        
        for face_landmarks in resultado.multi_face_landmarks:
            olho_esquerdo = self._extrair_pontos_olho(face_landmarks, self.olho_esquerdo_idx, w, h)
            olho_direito = self._extrair_pontos_olho(face_landmarks, self.olho_direito_idx, w, h)
            
            ear_medio = self._calcular_ear_medio(olho_esquerdo, olho_direito)
            
            # Detecta sonolência e obtém nível de alerta
            nivel_alerta = self._detectar_sonolencia(ear_medio)
            
            # Desenha apenas os pontos dos olhos para referência
            for ponto in olho_esquerdo + olho_direito:
                cv2.circle(frame_processado, ponto, 2, (0, 255, 0), -1)
            
        return frame_processado

    def _extrair_pontos_olho(self, landmarks, indices, w, h):
        return [(int(landmarks.landmark[idx].x * w), int(landmarks.landmark[idx].y * h)) for idx in indices]

    def _calcular_ear_medio(self, olho_esquerdo, olho_direito):
        ear_esquerdo = calcular_ear(olho_esquerdo)
        ear_direito = calcular_ear(olho_direito)
        return (ear_esquerdo + ear_direito) / 2.0

    def salvar_estatisticas(self):
        stats = {
            "eventos_sonolencia": self.eventos_sonolencia,
            "data": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        
        nome_arquivo = "registro_sonolencia.json"
        modo = 'a' if os.path.exists(nome_arquivo) else 'w'
        
        with open(nome_arquivo, modo) as f:
            if modo == 'a':
                f.write(',\n')
            json.dump(stats, f, indent=4)
            
    def finalizar(self):
        if self.esp32:
            self.esp32.close()
        self.salvar_estatisticas()
        pygame.quit()

def main():
    print("Sistema de Detecção de Sonolência para Motoristas")
    print("Alertas:")
    print("- Nível 1 (Atenção):")
    print("  * Olhos fechados por mais de 2 segundos")
    print("  * Olhos estáticos por mais de 3 segundos")
    print("  * Mais de 5 piscadas em 3 segundos")
    print("- Nível 2 (Perigo):")
    print("  * Olhos fechados por mais de 4 segundos")
    print("\nControles:")
    print("q - Sair e salvar registro")
    
    detector = DetectorSonolencia()
    cap = cv2.VideoCapture(0)
    
    cv2.namedWindow('Detector de Sonolência', cv2.WINDOW_NORMAL)
    
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("Erro ao capturar frame da câmera")
                break
                
            frame_processado = detector.processar_frame(frame)
            cv2.imshow('Detector de Sonolência', frame_processado)
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
                
    except Exception as e:
        print(f"Erro durante execução: {str(e)}")
    finally:
        cap.release()
        cv2.destroyAllWindows()
        detector.finalizar()

if __name__ == "__main__":
    main() 