# Sistema de Detecção de Sonolência - Versão Web

Este é um sistema de detecção de sonolência em tempo real que funciona através do navegador web. O sistema utiliza visão computacional para monitorar os olhos do motorista e detectar sinais de sonolência.

## Requisitos

- Python 3.11 ou superior
- Webcam
- Navegador web moderno
- Arduino (opcional, para alertas LED)

## Instalação

1. Clone este repositório
2. Instale as dependências:
```bash
pip install -r requirements.txt
```

## Como Usar

1. Inicie o servidor Flask:
```bash
python app.py
```

2. Abra seu navegador e acesse:
```
http://localhost:5000
```

## Funcionalidades

- Detecção de sonolência em tempo real
- Interface web responsiva
- Dois níveis de alerta:
  - Nível 1 (Atenção): Piscadas frequentes ou olhos fechados por mais de 1 segundo
  - Nível 2 (Perigo): Micro-sono detectado (olhos fechados por mais de 2 segundos)
- Integração com Arduino para alertas LED (opcional)
- Registro de eventos de sonolência

## Notas

- Certifique-se de ter uma boa iluminação para melhor detecção
- Se estiver usando Arduino, verifique se está conectado na porta COM correta
- O sistema funciona melhor quando o rosto está bem visível e centralizado 