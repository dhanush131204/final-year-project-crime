from PIL import Image, ImageDraw
import random

def generate_honey_image(output_path):
    """
    Generates a realistic-looking but fake forensic image for the honey-encryption decoy mechanism.
    """
    # Create a base image with a random grayscale "evidence" look
    img = Image.new('RGB', (800, 600), color=(random.randint(200, 240),)*3)
    draw = ImageDraw.Draw(img)
    
    # Add some random technical-looking shapes or lines
    for _ in range(20):
        x1, y1 = random.randint(0, 800), random.randint(0, 600)
        x2, y2 = x1 + random.randint(-100, 100), y1 + random.randint(-100, 100)
        draw.line([x1, y1, x2, y2], fill=(150, 150, 150), width=1)
    
    # Add a watermark to make it look official
    draw.text((350, 550), "FORENSIC SAMPLE DATA", fill=(100, 100, 100))
    
    img.save(output_path)
    return True
