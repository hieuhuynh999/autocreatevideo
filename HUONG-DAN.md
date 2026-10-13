# Kids 3D Story Video Creator

Tool chạy trên máy bạn bằng Python (`python app.py` hoặc `chay.bat`). Trình duyệt mở `http://127.0.0.1:7860`.

Yêu cầu React và FastAPI chưa chạy được trên máy này vì chưa có Node và chưa cài FastAPI. Máy chủ hiện tại là Python thư viện chuẩn. Ảnh, giọng, dựng phim và ghép video nằm trong các module `studio/`.

## Phần chạy thật

- Chia kịch bản thành cảnh, kể cả dự án mẫu **Ong Bông và Châu Chấu Lá** (sáu cảnh, lời Anh và Việt, hành động theo giây).
- Sửa từng cảnh, thêm hành động, khóa hồ sơ nhân vật trên giao diện.
- Vẽ ảnh qua Pollinations khi bấm **Tạo ảnh**. Mỗi ảnh cách nhau khoảng 40 giây. Model ảnh thường không giữ đúng hành động và trang phục.
- Giọng đọc edge-tts, phụ đề lấy từ kịch bản, nhạc giai điệu dân gian tool tự đánh (Twinkle Twinkle, Mary Had a Little Lamb, Frère Jacques). Nhạc nhỏ lại khi có lời. Nếu câu dài hơn cảnh, cảnh được kéo đến tối đa 12 giây.
- Bố cục B: tiêu đề trên, hình giữa, câu Anh rồi câu Việt do chương trình vẽ, không nhờ model ảnh viết chữ.
- Xuất MP4 bằng FFmpeg. **Ghép nhiều video** căn khung bằng viền, không kéo méo.

## Cách các cảnh bám nhau

1. **Tạo ảnh cảnh 1.** Đây là mẫu nhân vật và khu vườn.
2. **Cảnh 2, 3…** không vẽ lại từ đầu. Tool gửi đúng ảnh cảnh 1 và chỉ yêu cầu đổi hành động. Màu, trang phục và bối cảnh giữ theo ảnh đó.
3. **Tạo chuyển động** lấy ảnh của từng cảnh làm khung đầu. Engine chỉ làm các con vật đang có trong hình cử động, máy đứng yên, không kéo con vật ra khỏi khung.
4. **Xem trước** ghép lời đọc và phụ đề lên các clip đó.

Bước 2 và 3 gọi Pollinations (sửa ảnh `kontext`, chuyển động `wan-fast`). Cần khóa lưu tại `studio/pollinations.key` hoặc dán vào ô **Lưu khóa** trên giao diện. Khóa không gửi lại cho trình duyệt. Không có khóa thì cảnh 1 vẫn vẽ được bằng ảnh miễn phí, còn cảnh sau và chuyển động dừng lại thay vì vẽ nhân vật khác.

## Phần đang mô phỏng

- Đồng bộ môi. Giọng đọc và hình miệng là hai việc riêng.
- Hiệu ứng bay, bước chân, đặt đồ, uống nước chưa có file âm thanh riêng.
- Chi phí hiển thị 0 đồng. Ảnh cảnh 1 dùng lượt miễn phí. Cảnh sau và chuyển động tính theo khóa Pollinations.
- Khi chưa có khóa, tool không vẽ cảnh 2 bằng một ảnh mới. Việc đó sẽ làm nhân vật khác cảnh 1.

## Mở tool

1. Cài Python 3.
2. Bấm đúp `chay.bat`.
3. Bấm **Kịch bản mẫu** để nạp Ong Bông và Châu Chấu Lá, hoặc dán kịch bản rồi bấm **Tạo storyboard**.
4. Duyệt hành động. Bấm **Tạo ảnh** nếu muốn hình. Bấm **Xem trước** để có file MP4 storyboard.

File giấy phép nhạc: `giay-phep-nhac.txt` cạnh video. Phụ đề: `phu-de.srt`. Mỗi lần xuất thêm một bản trong `xuat/`.

## Phần còn lại của hướng dẫn cũ



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
5. Bấm **Vẽ storyboard** để xem hình chụp chân thật. Mỗi cảnh mất khoảng 40 giây vì dịch vụ ảnh miễn phí giới hạn lượt. Ảnh đôi khi còn watermark nhỏ.
6. Bấm **Dựng video**. Bạn có animatic: ảnh lia chậm, phụ đề, giọng đọc và nhạc nền. Phim tiếng Anh cho trẻ đọc câu tiếng Anh rồi đọc nghĩa tiếng Việt, và có nhạc thiếu nhi tự chơi (Twinkle Twinkle, Mary Had a Little Lamb, Frère Jacques — giai điệu dân gian hết bản quyền, không phải bản thu của ai). Sửa phụ đề rồi dựng lại, không cần vẽ lại ảnh.
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

Giao diện là **AI Kids Video Studio**: kịch bản bên trái, storyboard ở giữa, cảnh đang chọn bên phải, timeline phía dưới. Thể loại gồm truyện giáo dục, học màu và số, động vật, kỹ năng sống, phiêu lưu nhẹ, bài hát và học tiếng Anh. Nhân vật là hoạt hình 3D. Mỗi cảnh hai tư thế nên video thấy được động tác. Nhạc là giai điệu dân gian tool tự đánh, tự nhỏ khi có lời, và có file `giay-phep-nhac.txt`. Phụ đề xuất thêm file `phu-de.srt`. Mỗi lần xuất giữ một bản trong thư mục `xuat`, không ghi đè bản cũ.

Bốn ý để thử ngay trên giao diện: **Mưa và xe ôm**, **Ghế còn ấm**, **Thang máy kẹt**, **Học tiếng Anh**.
