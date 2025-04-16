import sys
import cv2
import os
import numpy as np
import sqlite3
import tkinter.simpledialog

def check_database():
    try:
        conn = sqlite3.connect("data/FaceBase.db")
        cursor = conn.cursor()
        cursor.execute("PRAGMA integrity_check;")
        result = cursor.fetchone()
        conn.close()
        if result[0] != "ok":
            print("database bị lỗi, tạo database mới")
            return False
        return True
    except sqlite3.DatabaseError:
        print("database bị hỏng, tạo database mới")
        return False

if not check_database():
    print("Tạo database mới...")
    conn = sqlite3.connect("data/FaceBase.db")
    conn.execute('CREATE TABLE IF NOT EXISTS People (ID INTEGER NOT NULL, Name TEXT NOT NULL, Gender TEXT, Age INTEGER, PRIMARY KEY(ID));')
    conn.close()
    print("Database mới đã được tạo")

def add_user_to_db(user_id, name, gender=None, age=None):
    conn = sqlite3.connect("data/FaceBase.db")
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO People (ID, Name, Gender, Age) VALUES (?, ?, ?, ?)", 
                   (user_id, name, gender, age))
    conn.commit()
    conn.close()

def capture_faces(user_id, name, save_dir="images", num_samples=50):
    # Yêu cầu nhập Age và Gender qua cửa sổ simpledialog
    age = tkinter.simpledialog.askstring("Nhập thông tin", "Nhập tuổi của người dùng:")
    gender = tkinter.simpledialog.askstring("Nhập thông tin", "Nhập giới tính của người dùng (Male/Female):")

    os.makedirs(save_dir, exist_ok=True)
    camera = cv2.VideoCapture(0)
    if not camera.isOpened():
        print("Không thể mở camera. Hãy kiểm tra lại kết nối.")
        return

    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    if face_cascade.empty():
        print("Không thể tải tệp Haar Cascade. hãy kiểm tra lại")
        return

    count = 0
    add_user_to_db(user_id, name, gender, age)

    while count < num_samples:
        ret, frame = camera.read()
        if not ret:
            print("Không thể đọc khung hình từ camera.")
            break

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.3, minNeighbors=5)

        for (x, y, w, h) in faces:
            face_img = gray[y:y+h, x:x+w]
            file_path = os.path.join(save_dir, f"user.{user_id}.{count}.jpg")
            cv2.imwrite(file_path, face_img)
            count += 1

            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
            cv2.putText(frame, f"Capturing {count}/{num_samples}", (x, y-10), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        cv2.imshow("Capture Faces", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    camera.release()
    cv2.destroyAllWindows()
    print(f"Thu thập ảnh hoàn tất! Đã lưu {count} ảnh.")

def train_model(data_dir="images", model_path="data/trainingData.yml"):
    recognizer = cv2.face.LBPHFaceRecognizer_create()
    faces, ids = [], []

    for file in os.listdir(data_dir):
        if file.endswith(".jpg"):
            img_path = os.path.join(data_dir, file)
            face_img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
            if face_img is None:
                print(f"Không thể đọc ảnh: {img_path}. Bỏ qua...")
                continue

            try:
                user_id = int(file.split(".")[1])
                faces.append(face_img)
                ids.append(user_id)
            except ValueError:
                print(f"Lỗi xử lý ID từ file {file}. Bỏ qua...")
                continue

    if len(faces) == 0:
        print("không có dữ liệu để train model. hãy thu thập lại ảnh")
        return

    recognizer.train(faces, np.array(ids))
    recognizer.save(model_path)
    print(f"train model hoàn tất! model đã được lưu tại: {model_path}")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Sử dụng: python dataset.py <user_id> <name>")
    else:
        user_id = sys.argv[1]
        name = sys.argv[2]
        capture_faces(user_id, name)
        train_model()