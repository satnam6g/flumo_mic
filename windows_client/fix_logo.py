import os
import shutil
from PIL import Image, ImageChops, ImageDraw

def fix_icon():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    img_path = os.path.join(base_dir, "assets", "icon.png")
    src_img_path = r"C:\Users\LENOVO\.gemini\antigravity\brain\64a01fdc-2fe3-4481-a9d0-a50036a67593\wireless_mic_icon_sq_1778848181831.png"
    
    # 1. Restore the original uncorrupted image first
    if os.path.exists(src_img_path):
        shutil.copy(src_img_path, img_path)
        print("Restored original image.")
    elif not os.path.exists(img_path):
        print(f"Error: {img_path} not found.")
        return
        
    print(f"Processing {img_path}...")
    img = Image.open(img_path).convert("RGBA")
    
    # 2. Use FloodFill from the corners to remove ONLY the exterior white border 
    # without touching any interior white graphics (like the microphone).
    ImageDraw.floodfill(img, (0, 0), (255, 255, 255, 0), thresh=20)
    width, height = img.size
    ImageDraw.floodfill(img, (width - 1, 0), (255, 255, 255, 0), thresh=20)
    ImageDraw.floodfill(img, (0, height - 1), (255, 255, 255, 0), thresh=20)
    ImageDraw.floodfill(img, (width - 1, height - 1), (255, 255, 255, 0), thresh=20)
    
    # 3. Crop empty/transparent borders tightly around the logo
    bg = Image.new("RGBA", img.size, (255,255,255,0))
    diff = ImageChops.difference(img, bg)
    bbox = diff.getbbox()
    if bbox:
        img = img.crop(bbox)
        
    # 4. Make it a perfect square again with a small margin so it looks good as an icon
    width, height = img.size
    max_dim = max(width, height)
    # Add a 5% margin
    margin = int(max_dim * 0.05)
    square_size = max_dim + (margin * 2)
    
    square_img = Image.new("RGBA", (square_size, square_size), (255, 255, 255, 0))
    # Paste centered
    square_img.paste(img, ((square_size - width) // 2, (square_size - height) // 2))
    
    # 5. Resize to high quality 256x256
    try:
        resample_filter = Image.Resampling.LANCZOS
    except AttributeError:
        resample_filter = Image.LANCZOS
        
    square_img = square_img.resize((256, 256), resample_filter)
    
    # Save the cleaned up PNG back
    square_img.save(img_path, "PNG")
    print(f"✓ Fixed PNG saved with transparent background (interior preserved!)")
    
    # 6. Generate high-quality ICO
    ico_path = os.path.join(base_dir, "assets", "icon.ico")
    sizes = [(256,256), (128,128), (64,64), (48,48), (32,32), (24,24), (16,16)]
    imgs = [square_img.resize(s, resample_filter) for s in sizes]
    
    imgs[0].save(ico_path, format="ICO", sizes=sizes, append_images=imgs[1:])
    print(f"✓ High-quality ICO created successfully at {ico_path}")
    print("Run `python build.py` again to apply the new icon.")

if __name__ == "__main__":
    fix_icon()
