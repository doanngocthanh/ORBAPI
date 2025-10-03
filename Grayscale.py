from PIL import Image

# Load the image
img = Image.open(r"C:\Users\0100644068\Downloads\z7075867857074_ca14d35caab4f4acedcc119f7b1d8b0a.jpg")

# Convert to grayscale
gray_img = img.convert("L")

# Save the grayscale image
gray_img.save(r"C:\Users\0100644068\Downloads\z7075867857074_ca14d35caab4f4acedcc119f7b1d8b0a_grayscale.jpg")