import cv2
import numpy as np
import sqlite3
import os
import datetime
import pandas as pd
import tkinter as tk
from tkinter import simpledialog, messagebox
import sys
import argparse

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

def main(args=None):
    if args is None:
        parser = argparse.ArgumentParser(description='Nhận diện khuôn mặt và điểm danh')
        parser.add_argument('--mode', type=str, choices=['auto', 'manual'], default='manual',
                            help='Chế độ nhận diện: tự động hoặc thủ công')
        args = parser.parse_args()
    
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    face_profile_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_profileface.xml')
    if face_cascade.empty() or face_profile_cascade.empty():
        print("Không thể tải tệp Haar Cascade. Hãy kiểm tra đường dẫn.")
        return

    def connect_to_db():
        db_path = os.path.abspath('data/FaceBase.db')
        if not os.path.exists(os.path.dirname(db_path)):
            os.makedirs(os.path.dirname(db_path))
        conn = sqlite3.connect(db_path)
        
        cursor = conn.cursor()
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS People (
            ID TEXT PRIMARY KEY,
            Name TEXT,
            Gender TEXT,
            Age TEXT
        )
        ''')
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS Attendance (
            ID INTEGER PRIMARY KEY AUTOINCREMENT,
            UserID TEXT,
            RecognitionTime TIMESTAMP,
            Status TEXT,
            FOREIGN KEY (UserID) REFERENCES People(ID)
        )
        ''')
        
        conn.commit()
        return conn

    def check_id_exists(id):
        conn = connect_to_db()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM People WHERE ID = ?", (id,))
        count = cursor.fetchone()[0]
        conn.close()
        return count > 0

    def add_new_person(id, name, gender, age):
        conn = connect_to_db()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO People (ID, Name, Gender, Age) VALUES (?, ?, ?, ?)", 
                    (id, name, gender, age))
        conn.commit()
        conn.close()
        print(f"Đã thêm người mới: ID={id}, Name={name}")

    def getProfile(id):
        conn = connect_to_db()
        cmd = "SELECT * FROM People WHERE ID = ?"
        cursor = conn.execute(cmd, (id,))
        profile = cursor.fetchone()
        conn.close()
        return profile

    def log_attendance(user_id, status="Có mặt"):
        try:
            conn = connect_to_db()
            cursor = conn.cursor()
            cursor.execute("INSERT INTO Attendance (UserID, RecognitionTime, Status) VALUES (?, ?, ?)", 
                        (user_id, datetime.datetime.now(), status))
            conn.commit()
            conn.close()
            print(f"Đã lưu điểm danh vào SQLite cho ID: {user_id}")
            return True
        except Exception as e:
            print(f"Lỗi khi lưu vào SQLite: {e}")
            return False

    def save_to_csv(user_id, name, age, gender, confidence, status="Đã điểm danh"):
        try:
            data = {
                "UserID": [user_id],
                "Name": [name],
                "Age": [age],
                "Gender": [gender],
                "Confidence": [confidence],
                "Status": [status],
                "RecognitionTime": [datetime.datetime.now()]
            }
            df = pd.DataFrame(data)
            csv_path = "attendance.csv"
            if not os.path.exists(csv_path):
                df.to_csv(csv_path, index=False)
                print(f"Đã tạo mới file {csv_path} và lưu dữ liệu cho {name}")
            else:
                df.to_csv(csv_path, mode='a', header=False, index=False)
                print(f"Đã thêm dữ liệu vào {csv_path} cho {name}")
            return True
        except Exception as e:
            print(f"Lỗi khi lưu vào CSV: {e}")
            return False

    try:
        rec = cv2.face.LBPHFaceRecognizer_create()
        model_path = os.path.abspath("data/trainingData.yml")
        if os.path.exists(model_path):
            rec.read(model_path)
            use_recognition = True
            print("Đã tải mô hình nhận diện khuôn mặt.")
        else:
            use_recognition = False
            print("Không tìm thấy mô hình nhận diện. Chỉ sử dụng chế độ đăng ký thủ công.")
    except Exception as e:
        use_recognition = False
        print(f"Lỗi khi tải mô hình nhận diện: {e}")

    root = tk.Tk()
    root.withdraw()  # Ẩn cửa sổ chính

    fontface = cv2.FONT_HERSHEY_SIMPLEX
    fontscale = 0.8
    fontcolor = (203, 23, 252)  
    success_color = (0, 255, 0)  
    error_color = (0, 0, 255)  

    recognized_ids = set()
    processed_faces = {}
    current_face_index = None
    registering_new_face = False

    cam = cv2.VideoCapture(0)
    if not cam.isOpened():
        print("Không thể mở camera. Hãy kiểm tra lại kết nối.")
        return

    registration_mode = False
    face_to_register = None
    auto_mode = args.mode == 'auto'

    while True:
        ret, img = cam.read()
        if not ret:
            print("Không thể đọc khung hình từ camera.")
            break

        original_img = img.copy()
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        gray = cv2.equalizeHist(gray)
        
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.3, minNeighbors=5)
        profile_faces = face_profile_cascade.detectMultiScale(gray, scaleFactor=1.3, minNeighbors=5)
        all_faces = list(faces) + list(profile_faces)  # Kết hợp cả hai

        for i, (x, y, w, h) in enumerate(all_faces):
            face_id = f"{x}_{y}_{w}_{h}"
            
            cv2.rectangle(img, (x, y), (x + w, y + h), (255, 0, 0), 2)
            
            cv2.putText(img, f"Face #{i+1}", (x, y - 10), fontface, fontscale, (0, 255, 255), 2)
            
            #kiểm tra xem khuôn mặt đã được xử lý chưa
            if face_id in processed_faces:
                profile = processed_faces[face_id]
                cv2.putText(img, f"ID: {profile['id']}, Name: {profile['name']}", 
                            (x, y + h + 30), fontface, fontscale, success_color, 2)
                cv2.putText(img, f"Age: {profile['age']}, Gender: {profile['gender']}", 
                            (x, y + h + 60), fontface, fontscale, success_color, 2)
            elif auto_mode and use_recognition:
                id, conf = rec.predict(gray[y:y + h, x:x + w])
                print(f"Predicted ID: {id}, Confidence: {conf}")

                if conf < 70:  #ngưỡng nhận diện
                    profile = getProfile(id)
                    if profile:
                        name, gender, age = profile[1], profile[2], profile[3]
                        # kiểm tra xem ID đã được điểm danh chưa
                        if id not in recognized_ids:
                            log_attendance(id)
                            save_to_csv(id, name, age, gender, conf)
                            recognized_ids.add(id)
                            print(f"Da diem danh cho {name} (ID: {id})")

                        processed_faces[face_id] = {
                            'id': id,
                            'name': name,
                            'gender': gender,
                            'age': age
                        }

                        cv2.putText(img, f"Diem danh thanh cong: {name}", 
                                    (x, y - 10), fontface, fontscale, success_color, 2)

                        cv2.putText(img, f"Name: {name}", (x, y + h + 30), fontface, fontscale, fontcolor, 2)
                        cv2.putText(img, f"Age: {age}", (x, y + h + 60), fontface, fontscale, fontcolor, 2)
                        cv2.putText(img, f"Gender: {gender}", (x, y + h + 90), fontface, fontscale, fontcolor, 2)
                        cv2.putText(img, f"Conf: {conf:.2f}", (x, y + h + 120), fontface, fontscale, fontcolor, 2)
                    else:
                        cv2.putText(img, "Not Found", (x, y + h + 30), fontface, fontscale, fontcolor, 2)
                else:
                    cv2.putText(img, "Unknown", (x, y + h + 30), fontface, fontscale, fontcolor, 2)
        
        instructions = [
            "Nhan 'r' de dang ky khuon mat moi",
            "Nhan so (1,2,3...) de chon khuon mat dang ky",
            "Nhan 'c' de huy dang ky",
            "Nhan 'a' de chuyen doi che do tu dong/thu cong",
            "Nhan 'q' de thoat"
        ]
        
        for i, text in enumerate(instructions):
            cv2.putText(img, text, (10, 30 + i * 30), fontface, fontscale, (255, 255, 255), 2)
        
        mode_text = "CHE DO TU DONG" if auto_mode else "CHE DO THU CONG"
        cv2.putText(img, mode_text, (img.shape[1] - 250, 30), fontface, fontscale, (0, 165, 255), 2)
        
        if registration_mode:
            cv2.putText(img, "CHE DO DANG KY: Chon khuon mat (1,2,3...), 'c' de huy", 
                        (10, img.shape[0] - 30), fontface, fontscale, (0, 165, 255), 2)
        elif current_face_index is not None:
            selected_face = all_faces[current_face_index]
            x, y, w, h = selected_face
            cv2.rectangle(img, (x, y), (x + w, y + h), (0, 255, 255), 3)
            cv2.putText(img, f"DANG DANG KY CHO MAT #{current_face_index+1}", 
                        (10, img.shape[0] - 30), fontface, fontscale, (0, 165, 255), 2)
                        
        cv2.imshow('Face Recognition', img)
        key = cv2.waitKey(1) & 0xFF
        
        if key == ord('q'):
            break
        elif key == ord('a'):
            auto_mode = not auto_mode
            print(f"Da chuyen sang che do {'tu dong' if auto_mode else 'thu cong'}")
        elif key == ord('r'):
            if len(all_faces) > 0:
                registration_mode = True
                cv2.putText(img, "Chon khuon mat bang cach nhan so (1,2,3...)", 
                            (10, img.shape[0] - 60), fontface, fontscale, (0, 165, 255), 2)
            else:
                print("Khong phat hien khuon mat nao de dang ky")
        elif key == ord('c'):
            registration_mode = False
            current_face_index = None
            print("Da huy che do dang ky.")
        elif registration_mode and ord('1') <= key <= ord('9'):
            selected_index = key - ord('1')
            if selected_index < len(all_faces):
                current_face_index = selected_index
                registration_mode = False
                
                face_coords = all_faces[current_face_index]
                x, y, w, h = face_coords
                face_id = f"{x}_{y}_{w}_{h}"
                
                if face_id in processed_faces:
                    messagebox.showinfo("Warning", f"Khuon mat nay da duoc dang ky voi ID: {processed_faces[face_id]['id']}")
                    current_face_index = None
                else:
                    id = simpledialog.askstring("Nhap ID", "Nhap ID cho nguoi nay:")
                    if id:
                        if check_id_exists(id):
                            messagebox.showerror("Loi", f"ID {id} da ton tai trong CSDL. Vui long chon ID khac.")
                            current_face_index = None
                        else:
                            name = simpledialog.askstring("Nhap Ten", "Nhap ten cho nguoi nay:")
                            if name:
                                gender = simpledialog.askstring("Nhap gioi tinh", "Nhap gioi tinh (Nam/Nu):")
                                age = simpledialog.askstring("Nhap tuoi", "Nhap tuoi:")
                                
                                add_new_person(id, name, gender, age)
                                
                                processed_faces[face_id] = {
                                    'id': id,
                                    'name': name,
                                    'gender': gender,
                                    'age': age
                                }
                                
                                log_attendance(id)
                                save_to_csv(id, name, age, gender, 0.0)
                                
                                messagebox.showinfo("Success", f"Da dang ky thanh cong {name} voi ID: {id}")
                                current_face_index = None
                            else:
                                current_face_index = None
                    else:
                        current_face_index = None
            else:
                print(f"Khong co khuon mat nao o vi tri {selected_index+1}")

    cam.release()
    cv2.destroyAllWindows()
    root.destroy()
    return 0

if __name__ == "__main__":
    sys.exit(main())