# Face_Recognition

Dự án này là một hệ thống nhận diện khuôn mặt được phát triển bằng Python. Mục tiêu của dự án là cung cấp một giải pháp đơn giản, dễ sử dụng để nhận diện và xác định danh tính của con người trực tiếp qua camera máy tính

## Tính năng

- Nhận diện khuôn mặt trực tiếp từ camera
- So sánh và xác định danh tính khuôn mặt dựa trên dữ liệu đã lưu.
- Lưu trữ dữ liệu khuôn mặt cho việc nhận diện trong tương lai.
- Hỗ trợ thêm/xóa dữ liệu người dùng.
- Thêm tính năng điểm danh, xuất file excel nếu người dùng có nhu cầu

## Yêu cầu hệ thống

- Python 3.11 trở lên
- Các thư viện Python phổ biến: `opencv-python`, `face_recognition`, `numpy`, ...

## Cài đặt

1. **Clone dự án:**
   ```bash
   git clone https://github.com/QuocAnhh/Face_Recognition.git
   cd Face_Recognition
   ```

2. **Cài đặt các phụ thuộc:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Chạy thử chương trình:**
   ```bash
   python gui.py
   ```

## Hướng dẫn sử dụng

- Chạy lệnh `python gui.py` và trên giao diện này có hiển thị tất cả tính năng, chỉ việc thao tác và sử dụng


## Cấu trúc thư mục

```
Face_Recognition/
├── data/                # Thư mục lưu trữ dữ liệu khuôn mặt
├── main.py              # Tập tin chính chạy chương trình
├── requirements.txt     # Danh sách các thư viện cần thiết
├── utils.py             # Các hàm hỗ trợ
└── ...                  # Các tệp tin khác
```

## Đóng góp

Dự án vẫn đang trong giai đoạn hoàn thiện, vậy nên mọi đóng góp của mọi người đều rất đáng giá và hoan nghênh! Nếu mọi người muốn đóng góp vào dự án, hãy làm theo các bước sau:

1. Fork repository
2. Tạo branch mới (`git checkout -b feature/amazing-feature`)
3. Commit thay đổi của bạn (`git commit -m 'Add some amazing feature'`)
4. Push lên branch (`git push origin feature/amazing-feature`)
5. Mở Pull Request


## Contact

Github - [GitHub](https://github.com/QuocAnhh)

Facebook - https://www.facebook.com/quocanh161004

Telegram - @quoccankk
