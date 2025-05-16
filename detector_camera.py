import cv2
import mediapipe as mp
import numpy as np
from ear_utils import calcular_ear
# import serial  # Comentado temporariamente
import time

try:
    arduino = serial.Serial('COM4 (lily-go t-display)', 9600, timeout=1)
    time.sleep(2)  
except:
    print("Erro ao conectar com o Arduino")

EAR_LIMIAR = 0.12

mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(
    static_image_mode=False,
    max_num_faces=1,
    refine_landmarks=True,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
)

olho_esquerdo_idx = [362, 385, 387, 263, 373, 380]
olho_direito_idx = [33, 160, 158, 133, 153, 144]

cap = cv2.VideoCapture(0)

while True:
    ret, frame = cap.read()
    if not ret:
        break

    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    resultado = face_mesh.process(rgb)

    if resultado.multi_face_landmarks:
        for face_landmarks in resultado.multi_face_landmarks:
            h, w, _ = frame.shape
            olho_esquerdo = []
            olho_direito = []

            for idx in olho_esquerdo_idx:
                x = int(face_landmarks.landmark[idx].x * w)
                y = int(face_landmarks.landmark[idx].y * h)
                olho_esquerdo.append((x, y))

            for idx in olho_direito_idx:
                x = int(face_landmarks.landmark[idx].x * w)
                y = int(face_landmarks.landmark[idx].y * h)
                olho_direito.append((x, y))

            for (x, y) in olho_esquerdo + olho_direito:
                cv2.circle(frame, (x, y), 2, (0, 255, 0), -1)

            ear_esquerdo = calcular_ear(olho_esquerdo)
            ear_direito = calcular_ear(olho_direito)
            ear_medio = (ear_esquerdo + ear_direito) / 2.0

            status = "Olhos Abertos" if ear_medio > EAR_LIMIAR else "Olhos Fechados"
            cor = (0, 255, 0) if status == "Olhos Abertos" else (0, 0, 255)
            cor = (0, 255, 255) if ear_medio > (EAR_LIMIAR - 0.03) and ear_medio < (EAR_LIMIAR + 0.03) else cor

            # Comentando temporariamente o controle do Arduino
            # if arduino:
            #     if ear_medio <= EAR_LIMIAR:
            #         arduino.write(b'1')  # Olhos fechados - Liga LED
            #     else:
            #         arduino.write(b'0')  # Olhos abertos - Desliga LED

            cv2.putText(frame, f"EAR: {ear_medio:.2f}", (30, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, cor, 2)
            cv2.putText(frame, status, (30, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.9, cor, 2)

    cv2.imshow("Detecção de Olhos - EAR + MediaPipe", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
if arduino:
    arduino.close()