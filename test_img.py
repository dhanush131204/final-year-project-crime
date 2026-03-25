from PIL import Image
import os

path = r"e:\final year project\crime\static\uploads\mug_20260309_161240_sample_data.jpg"
try:
    with Image.open(path) as img:
        print(f"Format: {img.format}, Size: {img.size}")
except Exception as e:
    print(f"Error: {e}")
