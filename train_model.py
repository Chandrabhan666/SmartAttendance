import cv2
import numpy as np
import os

dataset_path = "dataset"
recognizer = cv2.face.LBPHFaceRecognizer_create()

faces = []
labels = []

for student_id in os.listdir(dataset_path):
    for img in os.listdir(f"{dataset_path}/{student_id}"):
        img_path = f"{dataset_path}/{student_id}/{img}"
        gray = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
        faces.append(gray)
        labels.append(int(student_id))

recognizer.train(faces, np.array(labels))
recognizer.save("model/face_model.xml")

print("Model trained & saved successfully!")
