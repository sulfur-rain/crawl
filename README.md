# Hako Crawler Pro 
**Được phát triển bởi nhóm: Huỷ diệt Hako**

Hako Crawler Pro là một công cụ cào (crawl) dữ liệu tự động mạnh mẽ dành riêng cho website Light Novel **docln.net (Hako)**. Công cụ này giúp bạn dễ dàng tải các bộ truyện yêu thích và tự động đóng gói chúng thành định dạng **EPUB** hoàn chỉnh để đọc offline trên điện thoại, máy tính bảng hoặc máy đọc sách.

## ✨ Tính năng
* 🛡️ **Vượt Cloudflare** Tích hợp `playwright` và `playwright-stealth` giúp mở trình duyệt ẩn danh (headless/stealth) để vượt qua các lớp bảo vệ của Cloudflare một cách mượt mà.
* 📦 **Tạo file EPUB chuẩn:** Tự động tạo file `.epub` với đầy đủ ảnh bìa series, ảnh bìa volume, mục lục (TOC), và trang giới thiệu truyện (Tên, Tác giả, Thể loại, Tóm tắt).
* 🖼️ **Hỗ trợ tải ảnh minh họa:** Tự động tìm, tải và nhúng tất cả các hình ảnh minh họa trong chương truyện vào file EPUB.
* 🧹 **Làm sạch nội dung (Clean HTML):** Tự động loại bỏ các đoạn text rác, banner quảng cáo, thẻ ẩn, và link mxh (Discord, Facebook) để mang lại trải nghiệm đọc sạch nhất. Đồng thời tự động định dạng lại các chú thích (inline-notes).
* ⚡ **Xử lý bất đồng bộ (Async):** Sử dụng `aiohttp` và `asyncio` để tối ưu hóa tốc độ tải nội dung và hình ảnh.
* 🎯 **Tùy chọn tải linh hoạt:** Cho phép bạn xem danh sách các tập (volume) và tùy chọn tải từng tập riêng lẻ hoặc tải toàn bộ (`all`).

## ⚙️ Yêu cầu hệ thống
* **Python:** Phiên bản 3.8 trở lên.
* Hệ điều hành: Windows, macOS, hoặc Linux.

## 🚀 Hướng dẫn cài đặt

**Bước 1:** Clone repo này hoặc tải file `crawlhako.py` về máy.

**Bước 2:** Cài đặt các thư viện Python cần thiết bằng lệnh pip:
```bash
pip install aiohttp beautifulsoup4 EbookLib Pillow playwright playwright-stealth
```

**Bước 3:** Cài đặt trình duyệt Chromium cho Playwright (Bắt buộc để vượt Cloudflare):
```bash
playwright install chromium
```

## 📖 Hướng dẫn sử dụng

1. Mở Terminal hoặc Command Prompt tại thư mục chứa file script.
2. Chạy lệnh:
```bash
python crawlhako.py
```
3. Copy và dán URL của bộ truyện trên Hako (Ví dụ: `https://docln.net/truyen/1234-ten-truyen`) và nhấn Enter.
4. Chờ tool tải thông tin truyện và hiển thị danh sách các tập (volume).
5. Nhập số thứ tự của các tập bạn muốn tải (cách nhau bằng dấu phẩy, ví dụ: `0,1,2`) hoặc nhập `all` để tải toàn bộ.
6. Thư giãn và chờ đợi. File EPUB sẽ được tự động tạo và lưu vào một thư mục có tên của bộ truyện ngay tại thư mục bạn đang chạy script!

## ⚠️ Lưu ý (Disclaimer)
* Tool được tạo ra với mục đích học tập, nghiên cứu và sao lưu cá nhân.
* Vui lòng không lạm dụng công cụ này để spam request gây quá tải cho máy chủ của Hako.
* Nhóm **Huỷ diệt Hako** không chịu trách nhiệm cho bất kỳ vấn đề bản quyền hoặc hành động nào vi phạm điều khoản sử dụng của website docln.net từ phía người dùng cuối.

---
*Made with ❤️ by Huỷ diệt Hako*
