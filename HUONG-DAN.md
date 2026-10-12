# Xưởng phim ngắn

Tool này chạy trên máy bạn. Nó biến một ý tưởng thành kịch bản, ảnh storyboard, và một video animatic có phụ đề. Cảnh chuyển động thật (người đi, mưa rơi, máy quay lia) tạo tiếp ở Kling, Hailuo, Veo, Luma hoặc Runway bằng file prompt mà tool xuất ra.

## Mở tool

1. Cài Python 3 nếu máy chưa có.
2. Bấm đúp `chay.bat`, hoặc trong thư mục này chạy `python app.py`.
3. Trình duyệt mở `http://127.0.0.1:7860`.
4. Cần mạng để viết kịch bản và vẽ ảnh. Phần ghép video chạy tại máy, không cần card đồ họa.

## Làm một phim 30–60 giây

1. Viết một câu chuyện có đúng một cảm xúc. Gồm nhân vật, việc đang xảy ra, và hình cuối.
2. Chia 4 đến 6 cảnh. Mỗi cảnh chỉ một hành động nhìn thấy được. Nếu phải giải thích bằng lời, cảnh đó chưa rõ.
3. Điền khóa ngoại hình bằng tiếng Anh, ví dụ `woman, 30, hair in a bun, red raincoat, grey backpack`. Câu này đi vào mọi prompt để mặt và quần áo không bị đổi.
4. Bấm **Viết kịch bản**. Tool tách đúng các câu bạn viết, mỗi câu một cảnh. Sửa thoại và phụ đề nếu muốn.
5. Bấm **Vẽ storyboard** để xem hình. Ảnh miễn phí đôi khi còn watermark nhỏ.
6. Bấm **Dựng video**. Bạn có animatic: ảnh lia chậm, phụ đề, card tên phim. Sửa phụ đề rồi dựng lại, không cần vẽ lại ảnh.
7. Mở `prompt-video.txt` trong thư mục video. Dán khối **CHUYỂN ĐỘNG** của từng cảnh vào một web tạo video AI.
8. Ghép các cảnh AI ở CapCut hoặc DaVinci. Thêm giọng đọc tiếng Việt, nhạc, và tiếng động. Animatic chỉ là nhịp, chưa phải bản chiếu.

## Prompt hình và prompt chuyển động

- Prompt hình mô tả một khung đứng yên: ai, ở đâu, ánh sáng, ống kính.
- Prompt chuyển động mô tả máy quay và một hành động trong 4–6 giây. Đừng nhét cả câu chuyện vào một cảnh.
- Giữ cùng phong cách ánh sáng cho mọi cảnh.

## Nhịp đáng giữ

- Cảnh 1: nơi chốn.
- Cảnh giữa: một bước ngoặt nhìn thấy được.
- Cảnh cuối: một hình đứng lại lâu hơn lời nói.

Ba ý để thử ngay trên giao diện: **Mưa và xe ôm**, **Ghế còn ấm**, **Thang máy kẹt**.
