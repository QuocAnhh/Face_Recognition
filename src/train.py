import cv2
import os
import numpy as np

DATA_DIR = "images"
MODEL_PATH = "data/trainingData.yml"

if not os.path.exists(DATA_DIR):
    print(f"Thư mục '{DATA_DIR}' không tồn tại. Hãy thu thập dữ liệu trước!")
    exit()

recognizer = cv2.face.LBPHFaceRecognizer_create()

faces, ids = [], []

for file in os.listdir(DATA_DIR):
    if file.endswith(".jpg"):
        img_path = os.path.join(DATA_DIR, file)
        face_img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
        
        if face_img is None:
            print(f"Không thể đọc ảnh: {img_path}. Bỏ qua...")
            continue

        try:
            user_id = int(file.split(".")[1])  # lấy ID từ tên file
            faces.append(face_img)
            ids.append(user_id)
        except ValueError:
            print(f"Lỗi xử lý ID từ file {file}. Bỏ qua...")
            continue

#kiểm tra nếu có data hợp lệ để train
if len(faces) == 0:
    print("Không có dữ liệu hợp lệ để huấn luyện! Hãy kiểm tra lại ảnh thu thập.")
    exit()

print(f"Đang huấn luyện với {len(faces)} mẫu dữ liệu...")
recognizer.train(faces, np.array(ids))
recognizer.save(MODEL_PATH)
print(f"Huấn luyện mô hình hoàn tất! Mô hình đã được lưu tại: {MODEL_PATH}")