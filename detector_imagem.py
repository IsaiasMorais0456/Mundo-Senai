import cv2
import mediapipe as mp
import numpy as np
import tkinter as tk
from tkinter import filedialog
import mediapipe.python.solutions as solutions
from ear_utils import calcular_ear

EAR_LIMIAR = 0.21

janela = tk.Tk()
janela.withdraw()
caminho_imagem = filedialog.askopenfilename(
    title="Selecione uma imagem",
    filetypes=[("Imagens", "*.jpg *.jpeg *.png *.webp")]
)

if not caminho_imagem:
    raise FileNotFoundError("Nenhuma imagem foi selecionada.")

imagem = cv2.imread(caminho_imagem)
if imagem is None:
    raise FileNotFoundError(f"Imagem não pôde ser carregada: {caminho_imagem}")

mp_face_mesh = mp.solutions.face_mesh
rgb = cv2.cvtColor(imagem, cv2.COLOR_BGR2RGB)

with mp_face_mesh.FaceMesh(static_image_mode=True,
                           max_num_faces=1,
                           refine_landmarks=True,
                           min_detection_confidence=0.5) as face_mesh:

    resultado = face_mesh.process(rgb)

    if resultado.multi_face_landmarks:
        for face_landmarks in resultado.multi_face_landmarks:
            h, w, _ = imagem.shape
            olho_esquerdo = []
            olho_direito = []

            for idx in [362, 385, 387, 263, 373, 380]:
                x = int(face_landmarks.landmark[idx].x * w)
                y = int(face_landmarks.landmark[idx].y * h)
                olho_esquerdo.append((x, y))

            for idx in [33, 160, 158, 133, 153, 144]:
                x = int(face_landmarks.landmark[idx].x * w)
                y = int(face_landmarks.landmark[idx].y * h)
                olho_direito.append((x, y))

            for (x, y) in olho_esquerdo + olho_direito:
                cv2.circle(imagem, (x, y), 2, (0, 255, 0), -1)

            ear_esquerdo = calcular_ear(olho_esquerdo)
            ear_direito = calcular_ear(olho_direito)
            ear_medio = (ear_esquerdo + ear_direito) / 2.0

            status = "Olhos Abertos" if ear_medio > EAR_LIMIAR else "Olhos Fechados"
            cor = (0, 255, 0) if status == "Olhos Abertos" else (0, 0, 255)

            cv2.putText(imagem, f"EAR: {ear_medio:.2f}", (30, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, cor, 2)
            cv2.putText(imagem, status, (30, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.9, cor, 2)
    else:
        cv2.putText(imagem, "Rosto não detectado", (30, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)

cv2.imshow("Resultado", imagem)
cv2.waitKey(0)
cv2.destroyAllWindows()
