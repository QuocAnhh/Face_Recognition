import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import subprocess
import os
import sqlite3
import pandas as pd
import datetime
from tkinter import scrolledtext
import sys
import signal
import threading


def initialize_database():
    try:    
        db_path = os.path.abspath("data/FaceBase.db")
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
        conn.close()
        return True
    except Exception as e:
        print(f"Lỗi khi khởi tạo cơ sở dữ liệu: {e}")
        return False

def generate_attendance_report(date_str=None):
    "Hàm tạo báo cáo điểm danh"
    try:
        if date_str is None:
            date_str = datetime.datetime.now().strftime("%Y-%m-%d")
        
        conn = sqlite3.connect("data/FaceBase.db")
        all_people = pd.read_sql_query("SELECT ID, Name FROM People", conn)
        query = "SELECT UserID, RecognitionTime, Status FROM Attendance WHERE DATE(RecognitionTime) = ?"
        attendance = pd.read_sql_query(query, conn, params=(date_str,))
        conn.close()
        
        attended = attendance.merge(all_people, left_on="UserID", right_on="ID", how="inner")
        attended = attended[["Name", "RecognitionTime", "Status"]]
        
        not_attended = all_people[~all_people["ID"].isin(attendance["UserID"])][["Name"]]
        not_attended["Status"] = "Not Attended"
        
        report = pd.concat([attended, not_attended.rename(columns={"Name": "Name"})])
        report["Date"] = date_str
        
        report_file = f"Attendance_Report_{date_str}.xlsx"
        report.to_excel(report_file, index=False)
        print(f"Đã tạo báo cáo tại: {report_file}")
        return report_file
    except Exception as e:
        print(f"Lỗi khi tạo báo cáo: {e}")
        return None

# Biến để theo dõi quá trình nhận diện
recognition_process = None

def show_capture_input(root):
    "Hàm hiển thị cửa sổ nhập"
    capture_window = tk.Toplevel(root)
    capture_window.title("Thu thập dữ liệu khuôn mặt")
    capture_window.geometry("500x400")
    capture_window.configure(bg="#f0f0f0")

    tk.Label(capture_window, text="Nhập thông tin người dùng:", font=("Arial", 12, "bold"), bg="#f0f0f0").pack(pady=10)

    form_frame = tk.Frame(capture_window, bg="#f0f0f0")
    form_frame.pack(pady=10, fill="both", expand=True)

    tk.Label(form_frame, text="ID:", bg="#f0f0f0", font=("Arial", 10)).grid(row=0, column=0, sticky="e", padx=5, pady=5)
    user_id_entry = tk.Entry(form_frame, width=30)
    user_id_entry.grid(row=0, column=1, sticky="w", padx=5, pady=5)

    tk.Label(form_frame, text="Tên:", bg="#f0f0f0", font=("Arial", 10)).grid(row=1, column=0, sticky="e", padx=5, pady=5)
    name_entry = tk.Entry(form_frame, width=30)
    name_entry.grid(row=1, column=1, sticky="w", padx=5, pady=5)
    
    tk.Label(form_frame, text="Giới tính:", bg="#f0f0f0", font=("Arial", 10)).grid(row=2, column=0, sticky="e", padx=5, pady=5)
    gender_var = tk.StringVar(value="Nam")
    tk.Radiobutton(form_frame, text="Nam", variable=gender_var, value="Nam", bg="#f0f0f0").grid(row=2, column=1, sticky="w", padx=5, pady=5)
    tk.Radiobutton(form_frame, text="Nữ", variable=gender_var, value="Nữ", bg="#f0f0f0").grid(row=2, column=1, sticky="e", padx=5, pady=5)
    
    tk.Label(form_frame, text="Tuổi:", bg="#f0f0f0", font=("Arial", 10)).grid(row=3, column=0, sticky="e", padx=5, pady=5)
    age_entry = tk.Entry(form_frame, width=30)
    age_entry.grid(row=3, column=1, sticky="w", padx=5, pady=5)
    
    tk.Label(form_frame, text="Số lượng ảnh:", bg="#f0f0f0", font=("Arial", 10)).grid(row=4, column=0, sticky="e", padx=5, pady=5)
    img_count_var = tk.IntVar(value=50)
    img_count_slider = ttk.Scale(form_frame, from_=20, to=100, orient="horizontal", variable=img_count_var, length=200)
    img_count_slider.grid(row=4, column=1, sticky="w", padx=5, pady=5)
    img_count_label = tk.Label(form_frame, textvariable=img_count_var, bg="#f0f0f0")
    img_count_label.grid(row=4, column=1, sticky="e", padx=5, pady=5)
    
    def update_count_label(*args):
        img_count_label.config(text=str(int(img_count_var.get())))
    
    img_count_var.trace("w", update_count_label)

    def check_id_exists(id):
        try:
            conn = sqlite3.connect("data/FaceBase.db")
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM People WHERE ID = ?", (id,))
            count = cursor.fetchone()[0]
            conn.close()
            return count > 0
        except Exception as e:
            print(f"Lỗi khi kiểm tra ID: {e}")
            return False

    def submit_capture():
        user_id = user_id_entry.get()
        name = name_entry.get()
        gender = gender_var.get()
        age = age_entry.get()
        img_count = int(img_count_var.get())
        
        if not user_id or not name or not age:
            messagebox.showwarning("Cảnh báo", "Vui lòng nhập đầy đủ ID, Tên và Tuổi!")
            return
            
        # check ID đã tồn tại chưa
        if check_id_exists(user_id):
            messagebox.showerror("Lỗi", f"ID {user_id} đã tồn tại trong cơ sở dữ liệu. Vui lòng chọn ID khác.")
            return
            
        log_text.insert(tk.END, f"Đang thu thập dữ liệu cho ID: {user_id}, Tên: {name}, Giới tính: {gender}, Tuổi: {age}\n")
        log_text.see(tk.END)
        
        try:
            # thêm người dùng vào cơ sở dữ liệu
            conn = sqlite3.connect("data/FaceBase.db")
            cursor = conn.cursor()
            cursor.execute("INSERT INTO People (ID, Name, Gender, Age) VALUES (?, ?, ?, ?)", 
                           (user_id, name, gender, age))
            conn.commit()
            conn.close()
            
            # chạy script thu thập dữ liệu
            script_path = os.path.abspath("src/dataset.py")
            subprocess.run([sys.executable, script_path, user_id, name, str(img_count)])
            
            messagebox.showinfo("Thành công", "Thu thập dữ liệu khuôn mặt hoàn tất!")
            log_text.insert(tk.END, "Thu thập dữ liệu hoàn tất!\n")
            log_text.see(tk.END)
            
            capture_window.destroy()
        except Exception as e:
            messagebox.showerror("Lỗi", f"Lỗi khi thu thập dữ liệu: {e}")
            log_text.insert(tk.END, f"Lỗi: {e}\n")
            log_text.see(tk.END)

    button_frame = tk.Frame(capture_window, bg="#f0f0f0")
    button_frame.pack(pady=20)
    
    ttk.Button(button_frame, text="Xác nhận", command=submit_capture).pack(side="left", padx=10)
    ttk.Button(button_frame, text="Hủy", command=capture_window.destroy).pack(side="left", padx=10)
    
    capture_window.transient(root)
    capture_window.grab_set()

def show_train_input(root):
    "Hàm hiển thị cửa sổ nhập để train model"
    train_window = tk.Toplevel(root)
    train_window.title("Huấn luyện mô hình")
    train_window.geometry("400x300")
    train_window.configure(bg="#f0f0f0")

    tk.Label(train_window, text="Huấn luyện mô hình từ thư mục dữ liệu:", font=("Arial", 12, "bold"), bg="#f0f0f0").pack(pady=10)

    options_frame = tk.Frame(train_window, bg="#f0f0f0")
    options_frame.pack(pady=10, fill="both", expand=True)
    
    tk.Label(options_frame, text="Số epoch:", bg="#f0f0f0", font=("Arial", 10)).grid(row=0, column=0, sticky="e", padx=5, pady=5)
    epoch_var = tk.IntVar(value=50)
    epoch_slider = ttk.Scale(options_frame, from_=10, to=100, orient="horizontal", variable=epoch_var, length=200)
    epoch_slider.grid(row=0, column=1, sticky="w", padx=5, pady=5)
    epoch_label = tk.Label(options_frame, textvariable=epoch_var, bg="#f0f0f0")
    epoch_label.grid(row=0, column=1, sticky="e", padx=5, pady=5)
    
    def update_epoch_label(*args):
        epoch_label.config(text=str(int(epoch_var.get())))
    
    epoch_var.trace("w", update_epoch_label)
    
    tk.Label(options_frame, text="Batch size:", bg="#f0f0f0", font=("Arial", 10)).grid(row=1, column=0, sticky="e", padx=5, pady=5)
    batch_var = tk.IntVar(value=32)
    batch_sizes = [8, 16, 32, 64, 128]
    batch_combo = ttk.Combobox(options_frame, textvariable=batch_var, values=batch_sizes, width=10)
    batch_combo.grid(row=1, column=1, sticky="w", padx=5, pady=5)
    
    progress_frame = tk.Frame(train_window, bg="#f0f0f0")
    progress_frame.pack(pady=10, fill="x", padx=20)
    
    progress_label = tk.Label(progress_frame, text="Tiến trình:", bg="#f0f0f0")
    progress_label.pack(side="left", padx=5)
    
    progress_bar = ttk.Progressbar(progress_frame, orient="horizontal", length=250, mode="indeterminate")
    progress_bar.pack(side="left", padx=5)
    
    def start_training():
        epochs = int(epoch_var.get())
        batch_size = int(batch_var.get())
        
        log_text.insert(tk.END, f"Bắt đầu huấn luyện mô hình với {epochs} epochs, batch size {batch_size}...\n")
        log_text.see(tk.END)
        
        progress_bar.start()
        
        # chạy script train model trong một thread riêng
        def training_thread():
            try:
                script_path = os.path.abspath("src/train.py")
                subprocess.run([sys.executable, script_path, str(epochs), str(batch_size)])
                
                train_window.after(0, training_complete)
            except Exception as e:
                train_window.after(0, lambda: training_error(str(e)))
        
        threading.Thread(target=training_thread, daemon=True).start()
    
    def training_complete():
        progress_bar.stop()
        messagebox.showinfo("Thành công", "Huấn luyện mô hình hoàn tất!")
        log_text.insert(tk.END, "Huấn luyện mô hình hoàn tất!\n")
        log_text.see(tk.END)
        train_window.destroy()
    
    def training_error(error):
        progress_bar.stop()
        messagebox.showerror("Lỗi", f"Lỗi khi huấn luyện mô hình: {error}")
        log_text.insert(tk.END, f"Lỗi: {error}\n")
        log_text.see(tk.END)
    
    button_frame = tk.Frame(train_window, bg="#f0f0f0")
    button_frame.pack(pady=20)
    
    ttk.Button(button_frame, text="Bắt đầu huấn luyện", command=start_training).pack(side="left", padx=10)
    ttk.Button(button_frame, text="Hủy", command=train_window.destroy).pack(side="left", padx=10)
    
    train_window.transient(root)
    train_window.grab_set()

def start_recognition():
    global recognition_process
    
    if recognition_process is not None and recognition_process.poll() is None:
        messagebox.showinfo("Thông báo", "Quá trình nhận diện đang chạy!")
        return
    
    try:
        script_path = os.path.abspath("src/recognize.py")
        log_text.insert(tk.END, f"Đang thử mở file: {script_path}\n")
        log_text.see(tk.END)
        
        recognition_process = subprocess.Popen([sys.executable, script_path], 
                                             stdout=subprocess.PIPE, 
                                             stderr=subprocess.PIPE,
                                             universal_newlines=True)
        
        stderr_output = ""
        while recognition_process.poll() is None:
            stderr_line = recognition_process.stderr.readline()
            if stderr_line:
                stderr_output += stderr_line
                log_text.insert(tk.END, f"Lỗi: {stderr_line}")
                log_text.see(tk.END)
            else:
                break
        
        if stderr_output:
            messagebox.showerror("Lỗi khi khởi động", stderr_output)
            return
        
        log_text.insert(tk.END, "Đã bắt đầu quá trình nhận diện khuôn mặt...\n")
        log_text.see(tk.END)
        
        def read_output():
            while recognition_process and recognition_process.poll() is None:
                output = recognition_process.stdout.readline()
                if output:
                    log_text.insert(tk.END, output)
                    log_text.see(tk.END)
        
        threading.Thread(target=read_output, daemon=True).start()
        
    except Exception as e:
        messagebox.showerror("Lỗi", f"Lỗi khi bắt đầu nhận diện: {e}")
        log_text.insert(tk.END, f"Lỗi chi tiết: {str(e)}\n")
        log_text.see(tk.END)

def stop_recognition():
    global recognition_process
    
    if recognition_process is not None and recognition_process.poll() is None:
        try:
            if sys.platform == "win32":
                recognition_process.terminate()
            else:
                os.kill(recognition_process.pid, signal.SIGTERM)
                
            log_text.insert(tk.END, "Đã dừng quá trình nhận diện khuôn mặt.\n")
            log_text.see(tk.END)
            recognition_process = None
        except Exception as e:
            messagebox.showerror("Lỗi", f"Lỗi khi dừng nhận diện: {e}")
            log_text.insert(tk.END, f"Lỗi: {e}\n")
            log_text.see(tk.END)
    else:
        messagebox.showinfo("Thông báo", "Không có quá trình nhận diện nào đang chạy!")

def show_report_dialog(root):
    report_window = tk.Toplevel(root)
    report_window.title("Tạo báo cáo điểm danh")
    report_window.geometry("400x200")
    report_window.configure(bg="#f0f0f0")

    tk.Label(report_window, text="Chọn ngày tạo báo cáo:", font=("Arial", 12, "bold"), bg="#f0f0f0").pack(pady=10)
    
    date_frame = tk.Frame(report_window, bg="#f0f0f0")
    date_frame.pack(pady=10)
    
    today = datetime.datetime.now()
    
    day_var = tk.StringVar(value=str(today.day).zfill(2))
    month_var = tk.StringVar(value=str(today.month).zfill(2))
    year_var = tk.StringVar(value=str(today.year))
    
    days = [str(i).zfill(2) for i in range(1, 32)]
    months = [str(i).zfill(2) for i in range(1, 13)]
    years = [str(i) for i in range(2020, today.year + 1)]
    
    ttk.Combobox(date_frame, textvariable=day_var, values=days, width=3).pack(side="left", padx=2)
    tk.Label(date_frame, text="/", bg="#f0f0f0").pack(side="left")
    ttk.Combobox(date_frame, textvariable=month_var, values=months, width=3).pack(side="left", padx=2)
    tk.Label(date_frame, text="/", bg="#f0f0f0").pack(side="left")
    ttk.Combobox(date_frame, textvariable=year_var, values=years, width=5).pack(side="left", padx=2)
    
    def generate_report():
        try:
            day = day_var.get()
            month = month_var.get()
            year = year_var.get()
            date_str = f"{year}-{month}-{day}"
            
            log_text.insert(tk.END, f"Đang tạo báo cáo điểm danh cho ngày {date_str}...\n")
            log_text.see(tk.END)
            
            report_file = generate_attendance_report(date_str)
            
            if report_file:
                messagebox.showinfo("Thành công", f"Đã tạo báo cáo điểm danh: {report_file}")
                log_text.insert(tk.END, f"Đã tạo báo cáo điểm danh: {report_file}\n")
                log_text.see(tk.END)
            else:
                messagebox.showerror("Lỗi", "Không thể tạo báo cáo điểm danh!")
            
            report_window.destroy()
        except Exception as e:
            messagebox.showerror("Lỗi", f"Lỗi khi tạo báo cáo: {e}")
            log_text.insert(tk.END, f"Lỗi: {e}\n")
            log_text.see(tk.END)
    
    button_frame = tk.Frame(report_window, bg="#f0f0f0")
    button_frame.pack(pady=20)
    
    ttk.Button(button_frame, text="Tạo báo cáo", command=generate_report).pack(side="left", padx=10)
    ttk.Button(button_frame, text="Hủy", command=report_window.destroy).pack(side="left", padx=10)
    
    report_window.transient(root)
    report_window.grab_set()

def show_user_list(root):
    try:
        conn = sqlite3.connect("data/FaceBase.db")
        users_df = pd.read_sql_query("SELECT ID, Name, Gender, Age FROM People", conn)
        conn.close()
        
        user_window = tk.Toplevel(root)
        user_window.title("Danh sách người dùng")
        user_window.geometry("600x400")
        user_window.configure(bg="#f0f0f0")

        tk.Label(user_window, text="Danh sách người dùng trong hệ thống:", font=("Arial", 12, "bold"), bg="#f0f0f0").pack(pady=10)
        
        table_frame = tk.Frame(user_window)
        table_frame.pack(pady=10, padx=10, fill="both", expand=True)
        
        columns = ("ID", "Name", "Gender", "Age")
        tree = ttk.Treeview(table_frame, columns=columns, show="headings")
        
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=100)
        
        for _, row in users_df.iterrows():
            tree.insert("", "end", values=tuple(row))
        
        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        tree.pack(side="left", fill="both", expand=True)
        
        button_frame = tk.Frame(user_window, bg="#f0f0f0")
        button_frame.pack(pady=10)
        
        def delete_user():
            selected_item = tree.selection()
            if not selected_item:
                messagebox.showwarning("Cảnh báo", "Vui lòng chọn một người dùng để xóa!")
                return
                
            user_id = tree.item(selected_item[0])["values"][0]
            user_name = tree.item(selected_item[0])["values"][1]
            
            confirm = messagebox.askyesno("Xác nhận", f"Bạn có chắc muốn xóa người dùng {user_name} (ID: {user_id})?")
            if not confirm:
                return
                
            try:
                conn = sqlite3.connect("data/FaceBase.db")
                cursor = conn.cursor()
                
                cursor.execute("DELETE FROM Attendance WHERE UserID = ?", (user_id,))
                
                cursor.execute("DELETE FROM People WHERE ID = ?", (user_id,))
                
                conn.commit()
                conn.close()
                
                data_dir = os.path.join("dataset", str(user_id))
                if os.path.exists(data_dir):
                    import shutil
                    shutil.rmtree(data_dir)
                
                tree.delete(selected_item[0])
                
                log_text.insert(tk.END, f"Đã xóa người dùng {user_name} (ID: {user_id})\n")
                log_text.see(tk.END)
                
                messagebox.showinfo("Thành công", f"Đã xóa người dùng {user_name}")
            except Exception as e:
                messagebox.showerror("Lỗi", f"Lỗi khi xóa người dùng: {e}")
                log_text.insert(tk.END, f"Lỗi: {e}\n")
                log_text.see(tk.END)
        
        ttk.Button(button_frame, text="Xóa người dùng", command=delete_user).pack(side="left", padx=10)
        ttk.Button(button_frame, text="Đóng", command=user_window.destroy).pack(side="left", padx=10)
        
        user_window.transient(root)
        user_window.grab_set()
        
    except Exception as e:
        messagebox.showerror("Lỗi", f"Lỗi khi hiển thị danh sách người dùng: {e}")
        log_text.insert(tk.END, f"Lỗi: {e}\n")
        log_text.see(tk.END)

def main():
    #khởi tạo dữ liệu
    if not initialize_database():
        messagebox.showerror("Lỗi", "Không thể khởi tạo cơ sở dữ liệu!")
        return
    
    root = tk.Tk()
    root.title("Hệ thống điểm danh bằng nhận diện khuôn mặt")
    root.geometry("800x600")
    root.configure(bg="#f0f0f0")
    
    title_frame = tk.Frame(root, bg="#007ACC")
    title_frame.pack(fill="x", ipady=10)
    tk.Label(title_frame, text="HỆ THỐNG ĐIỂM DANH BẰNG NHẬN DIỆN KHUÔN MẶT", 
             font=("Arial", 16, "bold"), fg="white", bg="#007ACC").pack()
    
    button_frame = tk.Frame(root, bg="#f0f0f0")
    button_frame.pack(pady=20)
    
    capture_btn = ttk.Button(button_frame, text="Thu thập dữ liệu", width=20,
                             command=lambda: show_capture_input(root))
    capture_btn.grid(row=0, column=0, padx=10, pady=10)
    
    train_btn = ttk.Button(button_frame, text="Huấn luyện mô hình", width=20,
                          command=lambda: show_train_input(root))
    train_btn.grid(row=0, column=1, padx=10, pady=10)
    
    start_btn = ttk.Button(button_frame, text="Bắt đầu nhận diện", width=20,
                          command=start_recognition)
    start_btn.grid(row=1, column=0, padx=10, pady=10)
    
    stop_btn = ttk.Button(button_frame, text="Dừng nhận diện", width=20,
                         command=stop_recognition)
    stop_btn.grid(row=1, column=1, padx=10, pady=10)
    
    report_btn = ttk.Button(button_frame, text="Tạo báo cáo", width=20,
                           command=lambda: show_report_dialog(root))
    report_btn.grid(row=2, column=0, padx=10, pady=10)
    
    user_list_btn = ttk.Button(button_frame, text="Danh sách người dùng", width=20,
                              command=lambda: show_user_list(root))
    user_list_btn.grid(row=2, column=1, padx=10, pady=10)
    
    log_frame = tk.LabelFrame(root, text="Nhật ký hoạt động", bg="#f0f0f0", font=("Arial", 10, "bold"))
    log_frame.pack(pady=10, padx=20, fill="both", expand=True)
    
    global log_text
    log_text = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, width=70, height=12)
    log_text.pack(padx=10, pady=10, fill="both", expand=True)
    log_text.insert(tk.END, "Hệ thống đã khởi động...\n")
    
    info_frame = tk.Frame(root, bg="#f0f0f0")
    info_frame.pack(pady=5, fill="x")
    
    tk.Label(info_frame, text="Phát triển bởi: Quoc Anh ", font=("Arial", 8), bg="#f0f0f0").pack(side="left", padx=20)
    tk.Label(info_frame, text="© 2025", font=("Arial", 8), bg="#f0f0f0").pack(side="right", padx=20)
    
    def on_closing():
        if recognition_process is not None and recognition_process.poll() is None:
            stop_recognition()
        root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", on_closing)
    
    root.mainloop()

if __name__ == "__main__":
    main()