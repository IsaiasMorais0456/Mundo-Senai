#include <WiFi.h>
#include <WebServer.h>

// Dados da rede Wi-Fi3
const char* ssid = "MundoSENAI"; //MundoSENAI
const char* password = "senai@2025"; //senai@2025

// Cria o servidor web na porta 80
WebServer server(80);

// Pinos dos motores
int IN1 = 27;
int IN2 = 26;
int IN3 = 33;
int IN4 = 32;

// Pino do LED e buzzer (mesmo pino)
const int ALERTA_PIN = 13;

// Variáveis de controle
bool alertaOlhosFechados = false;
bool modoCircular = false;
bool testeAlertaAtivo = false;
unsigned long ultimoTempoAlerta = 0;
const unsigned long TEMPO_ALERTA = 500; // 0.5 segundos em milissegundos
bool estadoAlerta = false;

// Variáveis para frenagem gradual
int velocidadeAtual = 255;
unsigned long ultimoTempoFreio = 0;
const unsigned long INTERVALO_FREIO = 500; // 0.5 segundos
bool frenagemAtiva = false;
int ultimaDirecao = 0; // 0=parado, 1=frente, 2=tras, 3=esquerda, 4=direita, 5=circular

// Variáveis para o modo circular
const int VELOCIDADE_RODA_DIREITA = 255;
const int VELOCIDADE_RODA_ESQUERDA = 160;

// Página HTML com botões de controle
const char* html = R"rawliteral(
<!DOCTYPE html>
<html>
<head>
  <title>Controle de Robô ESP32</title>
  <style>
    button {
      width: 120px; height: 50px; margin: 5px;
      font-size: 18px;
    }
  </style>
</head>
<body>
  <h1>Controle do Robô</h1>
  <button onclick="fetch('/frente')">Frente</button><br>
  <button onclick="fetch('/esquerda')">Esquerda</button>
  <button onclick="fetch('/parar')">Parar</button>
  <button onclick="fetch('/direita')">Direita</button><br>
  <button onclick="fetch('/tras')">Trás</button><br>
  <button onclick="fetch('/circular')">Modo Circular</button><br><br>

  <h2>Testes</h2>
  <button onclick="fetch('/teste_alerta')">Testar Alerta</button>
</body>
</html>
)rawliteral";

// Funções de movimento com controle de velocidade
void frente(int velocidade = 255) {
  if (frenagemAtiva) return;
  velocidadeAtual = velocidade;
  ultimaDirecao = 1;
  analogWrite(IN1, velocidade);
  analogWrite(IN2, 0);
  analogWrite(IN3, velocidade);
  analogWrite(IN4, 0);
}

void tras(int velocidade = 255) {
  if (frenagemAtiva) return;
  velocidadeAtual = velocidade;
  ultimaDirecao = 2;
  analogWrite(IN1, 0);
  analogWrite(IN2, velocidade);
  analogWrite(IN3, 0);
  analogWrite(IN4, velocidade);
}

void esquerda(int velocidade = 100) {
  if (frenagemAtiva) return;
  velocidadeAtual = velocidade;
  ultimaDirecao = 3;
  analogWrite(IN1, 0);
  analogWrite(IN2, velocidade);
  analogWrite(IN3, velocidade);
  analogWrite(IN4, 0);
}

void direita(int velocidade = 100) {
  if (frenagemAtiva) return;
  velocidadeAtual = velocidade;
  ultimaDirecao = 4;
  analogWrite(IN1, velocidade);
  analogWrite(IN2, 0);
  analogWrite(IN3, 0);
  analogWrite(IN4, velocidade);
}

void parado() {
  velocidadeAtual = 0;
  ultimaDirecao = 0;
  frenagemAtiva = false;
  analogWrite(IN1, 0);
  analogWrite(IN2, 0);
  analogWrite(IN3, 0);
  analogWrite(IN4, 0);
}

void controlarAlerta(bool ativar) {
  if (ativar) {
    digitalWrite(ALERTA_PIN, !digitalRead(ALERTA_PIN)); // Inverte o estado do alerta
  } else {
    digitalWrite(ALERTA_PIN, LOW); // Desliga o alerta
  }
}

// Função para controlar o circuito oval com velocidade ajustável
void controlarCircuito(int velocidade = 255) {
  if (frenagemAtiva) return;
  
  velocidadeAtual = velocidade;
  ultimaDirecao = 5; // modo circular
  
  int velDireita = (VELOCIDADE_RODA_DIREITA * velocidade) / 255;
  int velEsquerda = (VELOCIDADE_RODA_ESQUERDA * velocidade) / 255;
  
  analogWrite(IN1, velDireita);
  analogWrite(IN2, 0);
  analogWrite(IN3, velEsquerda);
  analogWrite(IN4, 0);
}

// Função para aplicar velocidade aos motores mantendo a direção
void aplicarVelocidade(int velocidade) {
  if (velocidade < 0) velocidade = 0;
  if (velocidade > 255) velocidade = 255;
  
  // Declara as variáveis antes do switch
  int velDireita = 0;
  int velEsquerda = 0;
  
  // Aplica a velocidade baseada na última direção
  switch (ultimaDirecao) {
    case 1: // frente
      analogWrite(IN1, velocidade);
      analogWrite(IN2, 0);
      analogWrite(IN3, velocidade);
      analogWrite(IN4, 0);
      break;
    case 2: // tras
      analogWrite(IN1, 0);
      analogWrite(IN2, velocidade);
      analogWrite(IN3, 0);
      analogWrite(IN4, velocidade);
      break;
    case 3: // esquerda
      analogWrite(IN1, 0);
      analogWrite(IN2, velocidade);
      analogWrite(IN3, velocidade);
      analogWrite(IN4, 0);
      break;
    case 4: // direita
      analogWrite(IN1, velocidade);
      analogWrite(IN2, 0);
      analogWrite(IN3, 0);
      analogWrite(IN4, velocidade);
      break;
    case 5: // circular
      velDireita = (VELOCIDADE_RODA_DIREITA * velocidade) / 255;
      velEsquerda = (VELOCIDADE_RODA_ESQUERDA * velocidade) / 180;
      analogWrite(IN1, velDireita);
      analogWrite(IN2, 0);
      analogWrite(IN3, velEsquerda);
      analogWrite(IN4, 0);
      break;
    default: // parado
      analogWrite(IN1, 0);
      analogWrite(IN2, 0);
      analogWrite(IN3, 0);
      analogWrite(IN4, 0);
  }
}

// Função para frenagem gradual
void frenagemGradual() {
  if (!frenagemAtiva) return;
  
  unsigned long tempoAtual = millis();
  if (tempoAtual - ultimoTempoFreio >= INTERVALO_FREIO) {
    velocidadeAtual = velocidadeAtual * 0.75; // Reduz 25% da velocidade
    
    if (velocidadeAtual < 10) {
      velocidadeAtual = 0;
      frenagemAtiva = false;
      ultimaDirecao = 0;
    }
    
    aplicarVelocidade(velocidadeAtual);
    ultimoTempoFreio = tempoAtual;
  }
}

void setup() {
  Serial.begin(115200);

  // Configura os pinos
  pinMode(IN1, OUTPUT);
  pinMode(IN2, OUTPUT);
  pinMode(IN3, OUTPUT);
  pinMode(IN4, OUTPUT);
  pinMode(ALERTA_PIN, OUTPUT);
  digitalWrite(ALERTA_PIN, LOW);

  // Conecta ao Wi-Fi
  WiFi.begin(ssid, password);
  Serial.print("Conectando ao Wi-Fi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nConectado!");
  Serial.println(WiFi.localIP());

  // Define as rotas da página web
  server.on("/", HTTP_GET, []() {
    server.send(200, "text/html", html);
  });

  server.on("/frente", HTTP_GET, []() {
    if (!alertaOlhosFechados) {
      modoCircular = false;
      frente(255);
    }
    server.send(200, "text/plain", "Frente");
  });

  server.on("/tras", HTTP_GET, []() {
    if (!alertaOlhosFechados) {
      modoCircular = false;
      tras(255);
    }
    server.send(200, "text/plain", "Trás");
  });

  server.on("/esquerda", HTTP_GET, []() {
    if (!alertaOlhosFechados) {
      modoCircular = false;
      esquerda(255);
    }
    server.send(200, "text/plain", "Esquerda");
  });

  server.on("/direita", HTTP_GET, []() {
    if (!alertaOlhosFechados) {
      modoCircular = false;
      direita(255);
    }
    server.send(200, "text/plain", "Direita");
  });

  server.on("/parar", HTTP_GET, []() {
    modoCircular = false;
    parado();
    server.send(200, "text/plain", "Parado");
  });

  server.on("/circular", HTTP_GET, []() {
    if (!alertaOlhosFechados && !frenagemAtiva) {
      modoCircular = !modoCircular;
      if (modoCircular) {
        controlarCircuito(255);
      } else {
        parado();
      }
    }
    server.send(200, "text/plain", modoCircular ? "Modo Circular Ativado" : "Modo Circular Desativado");
  });

  server.on("/alerta_olhos", HTTP_GET, []() {
    Serial.println("Alerta de olhos fechados recebido!");
    alertaOlhosFechados = true;
    if (!frenagemAtiva) {
      frenagemAtiva = true;
      ultimoTempoFreio = millis();
    }
    server.send(200, "text/plain", "Alerta Recebido");
  });

  server.on("/olhos_abertos", HTTP_GET, []() {
    Serial.println("Sinal de olhos abertos recebido!");
    alertaOlhosFechados = false;
    digitalWrite(ALERTA_PIN, LOW);
    // Não reinicia o movimento automaticamente
    server.send(200, "text/plain", "Olhos Abertos Recebido");
  });

  server.on("/teste_alerta", HTTP_GET, []() {
    testeAlertaAtivo = !testeAlertaAtivo;
    controlarAlerta(testeAlertaAtivo);
    server.send(200, "text/plain", testeAlertaAtivo ? "Alerta Ligado" : "Alerta Desligado");
  });

  server.begin();
}

void loop() {
  server.handleClient();

  // Controle do pulso do alerta quando os olhos estão fechados
  if (alertaOlhosFechados) {
    if (!frenagemAtiva) {
      frenagemAtiva = true;
      ultimoTempoFreio = millis();
    }
    
    unsigned long tempoAtual = millis();
    if (tempoAtual - ultimoTempoAlerta >= TEMPO_ALERTA) {
      estadoAlerta = !estadoAlerta;
      digitalWrite(ALERTA_PIN, estadoAlerta);
      ultimoTempoAlerta = tempoAtual;
    }
  }
  
  // Sempre chama a frenagem gradual se estiver ativa
  if (frenagemAtiva) {
    frenagemGradual();
  }
  // Aplica o modo circular apenas se não estiver em frenagem
  else if (modoCircular && !alertaOlhosFechados) {
    controlarCircuito(velocidadeAtual);
  }
}