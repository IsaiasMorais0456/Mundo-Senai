#include <Arduino.h>  // Biblioteca principal do Arduino

#define LED_PIN 2  // GPIO2 é um pino comum para LED no ESP32 (LED azul embutido)
// Se estiver usando outro pino na protoboard, mude o número aqui

void setup() {
  Serial.begin(9600);  // Inicia comunicação serial
  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, LOW);
}

void loop() {
  if (Serial.available() > 0) {
    char estado = Serial.read();
    if (estado == '1') {  // Olhos fechados
      digitalWrite(LED_PIN, HIGH);
    } else if (estado == '0') {  // Olhos abertos
      digitalWrite(LED_PIN, LOW);
    }
  }
} 