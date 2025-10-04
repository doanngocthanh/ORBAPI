from PIL import Image

# Đọc ảnh gốc
img = Image.open(r"C:\Users\dntdo\Downloads\DataSetSource\OCR_CCCD.v4i.yolov8 (1)\train\images\20021580_01JARERNB2WRRB85DQ1P0J2XQE379632_front_jpg.rf.256550f5746de8388b874036a3949639.jpg")

# Chuyển sang grayscale
gray_img = img.convert('L')

# Đọc ảnh tham chiếu để lấy kích thước
ref_img = Image.open(r'C:\Workspace\ORBAPI\lockup\base_qr_cccd.png')
target_size = ref_img.size

# Resize ảnh grayscale theo kích thước ảnh tham chiếu
resized_gray = gray_img.resize(target_size, Image.LANCZOS)

# Lưu ảnh kết quả
resized_gray.save(r'C:\Workspace\ORBAPI\lockup\gray.scale.png')

print(f"Đã chuyển ảnh sang grayscale và resize về kích thước {target_size}")