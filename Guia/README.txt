SISTEMA DE DETECÇÃO DE SONOLÊNCIA COM ESP32
=========================================

Este sistema detecta sonolência através da câmera e controla um LED no ESP32 para alertas.

Requisitos de Hardware:
---------------------
1. ESP32 (testado na porta COM4)
2. LED conectado ao pino GPIO2
3. Webcam
4. Cabo USB para ESP32

Requisitos de Software:
---------------------
1. Python 3.11
2. Arduino IDE (para ESP32)
3. Bibliotecas Python necessárias:
   - opencv-python
   - mediapipe
   - numpy
   - pyserial

Configuração:
-----------
1. Instalar bibliotecas Python:
   pip install opencv-python mediapipe numpy pyserial

2. Configurar Arduino IDE para ESP32:
   - Instalar suporte ESP32 no Arduino IDE
   - Selecionar placa "ESP32 Dev Module"
   - Velocidade: 115200 baud

3. Carregar código no ESP32:
   - LED_PIN definido como 2
   - Comunicação Serial em 115200 baud
   - Estados: NORMAL(0), ALERTA(1), PERIGO(2)

4. Conexões:
   - LED no pino GPIO2
   - GND do LED no GND do ESP32

Como Usar:
---------
1. Carregar código do ESP32 primeiro
2. Conectar ESP32 na porta USB (COM4)
3. Executar detector_camera_arduino.py
4. Sistema irá:
   - Detectar olhos através da câmera
   - LED desligado = olhos abertos
   - LED aceso = olhos fechados por 2s
   - LED piscando = olhos fechados por 4s

Arquivos do Projeto:
------------------
1. detector_camera_arduino.py - Código principal Python
2. ear_utils.py - Utilitários para cálculo EAR
3. Código ESP32 (no Arduino IDE):
   - LED_PIN = 2
   - Estados e controle do LED
   - Comunicação serial

Solução de Problemas:
-------------------
1. Se LED não piscar:
   - Verificar porta COM (alterar COM4 se necessário)
   - Reconectar ESP32
   - Recompilar código do ESP32
   - Verificar conexão do LED

2. Se câmera não abrir:
   - Verificar se webcam está conectada
   - Testar outra porta USB
   - Verificar se não há outro programa usando a câmera

3. Erros de comunicação:
   - Verificar velocidade (115200 baud)
   - Fechar Arduino IDE
   - Desconectar/reconectar ESP32

Observações:
-----------
- Sistema testado em Windows 10
- Usar cabo USB de qualidade para ESP32
- Manter rosto bem iluminado para detecção
- Ajustar EAR_LIMIAR se necessário (atual = 0.12) 