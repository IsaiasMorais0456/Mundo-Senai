const int LED_PIN = 13;  // Pino do LED vermelho

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