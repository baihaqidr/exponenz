import shutil
import os

src = r"C:\Users\Baihaqi\.gemini\antigravity-ide\brain\b7a7b608-4e11-4389-a4c5-3c4973e28a39\.user_uploaded\media_1789471459276.png"
dest1 = r"C:\Users\Baihaqi\.gemini\antigravity-ide\scratch\binance-futures-bot\dashboard\exponenz_light_clear.png"
dest2 = r"C:\Users\Baihaqi\.gemini\antigravity-ide\scratch\binance-futures-bot\dashboard\exponenz_logo.png"

shutil.copyfile(src, dest1)
shutil.copyfile(src, dest2)
print("Copied Exponenz_Light_Clear logo to dashboard:", os.path.exists(dest1))
