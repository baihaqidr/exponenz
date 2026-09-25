import os
from PIL import Image, ImageEnhance, ImageFilter

src_img_path = r"C:\Users\Baihaqi\.gemini\antigravity-ide\brain\b7a7b608-4e11-4389-a4c5-3c4973e28a39\.user_uploaded\media_1789469854616.jpg"
out_img_path = r"C:\Users\Baihaqi\.gemini\antigravity-ide\scratch\binance-futures-bot\dashboard\exponenz_logo.png"

# Load image
img = Image.open(src_img_path).convert("RGBA")

# Let's create a dark-theme optimized transparent logo:
# In the original, background is off-white (#f4f0ec), letter 'E' is dark (#111111), and the flare is bright orange-yellow (#ffaa33 to #ffffff).
# In dark mode:
# Letter 'E' should be pure white/silver (#ffffff or #f3fff9)
# Flare should remain vivid glowing orange/gold (#ff7a00 / #ffbe3b / #ffffff flare)
# Background should be transparent.

width, height = img.size
datas = img.getdata()

new_data = []
for item in datas:
    r, g, b, a = item
    
    # Detect background (light off-white/beige)
    # Background has high lightness and low saturation
    brightness = (r + g + b) / 3.0
    
    # Check if this pixel is part of the golden/orange flare
    # Flare has high Red, medium/high Green, lower Blue (r > 200, g > 100, r - b > 40)
    is_flare = (r > 180 and g > 80 and (r - b) > 30) or (brightness > 240 and abs(r - g) < 20 and (r - b) > 20)
    
    if brightness > 225 and not is_flare:
        # Background -> transparent
        new_data.append((0, 0, 0, 0))
    elif is_flare:
        # Keep flare vibrant
        new_data.append((r, g, b, 255))
    else:
        # It's the dark 'E' body -> invert to sleek glowing white/silver (#F3FFF9)
        darkness = 255 - brightness
        alpha = min(255, int(darkness * 1.5))
        new_data.append((243, 255, 249, alpha))

img.putdata(new_data)
img.save(out_img_path, "PNG")
print("Saved transparent dark-mode Exponenz logo:", out_img_path)
