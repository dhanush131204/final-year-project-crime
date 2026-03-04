from pathlib import Path
from PIL import Image, ImageFilter, ImageOps, ImageDraw, ImageFont
import random


def generate_honey_image(src_path: str, out_dir: str) -> str:
    """
    Generate a plausible decoy image from the source by applying obfuscations
    so that a wrong key still yields seemingly valid content.
    Returns the saved honey image path.
    """
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    honey_path = out / "honey_decoy.png"

    try:
        with Image.open(src_path) as img:
            img = img.convert("RGBA")
            # Randomized obfuscation pipeline
            ops = [
                lambda im: im.filter(ImageFilter.GaussianBlur(radius=random.uniform(1.5, 3.0))),
                lambda im: ImageOps.colorize(ImageOps.grayscale(im), black="#222", white="#ddd").convert("RGBA"),
                lambda im: ImageOps.posterize(im.convert("RGB"), bits=random.choice([2, 3])).convert("RGBA"),
                lambda im: ImageOps.autocontrast(im),
            ]
            random.shuffle(ops)
            honey = img
            for op in ops[:2]:
                honey = op(honey)

            # Add faint watermark 'HONEY'
            draw = ImageDraw.Draw(honey)
            w, h = honey.size
            text = "CASE FILE"
            sub = "ID: " + str(random.randint(100000, 999999))
            try:
                font = ImageFont.truetype("arial.ttf", size=max(16, w // 25))
                font2 = ImageFont.truetype("arial.ttf", size=max(12, w // 30))
            except Exception:
                font = ImageFont.load_default()
                font2 = ImageFont.load_default()
            tw, th = draw.textsize(text, font=font)
            draw.text(((w - tw) / 2, h * 0.08), text, fill=(255, 0, 0, 90), font=font)
            draw.text((w * 0.05, h * 0.88), sub, fill=(255, 255, 0, 120), font=font2)

            honey.save(honey_path)
            return str(honey_path)
    except Exception:
        # If anything fails, create a blank decoy
        img = Image.new("RGB", (400, 300), color=(30, 30, 30))
        draw = ImageDraw.Draw(img)
        draw.text((10, 10), "Decoy Data", fill=(200, 200, 200))
        img.save(honey_path)
        return str(honey_path)
