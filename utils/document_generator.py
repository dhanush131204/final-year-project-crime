import os
import random
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

def generate_official_document(data, mugshot_path, output_path):
    """
    Generates a professional-looking 'Criminal Record' image.
    data: dict containing the 12 fields
    mugshot_path: path to the uploaded face photo
    output_path: where to save the final document image
    """
    width, height = 900, 1100
    bg_color = (255, 255, 255)
    img = Image.new("RGB", (width, height), bg_color)
    draw = ImageDraw.Draw(img)

    # Try to load high-end serif fonts for that 'strong' legal look
    try:
        if os.name == 'nt':
            font_bold_path = "timesbd.ttf" # Times New Roman Bold
            font_reg_path  = "times.ttf"   # Times New Roman Regular
        else:
            font_bold_path = "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf"
            font_reg_path  = "/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf"
            
        font_title  = ImageFont.truetype(font_bold_path, 42) # Stronger title
        font_annex  = ImageFont.truetype(font_bold_path, 15)
        font_label  = ImageFont.truetype(font_bold_path, 19) # Large labels
        font_value  = ImageFont.truetype(font_reg_path,  18)
    except Exception:
        font_title  = ImageFont.load_default()
        font_annex  = ImageFont.load_default()
        font_label  = ImageFont.load_default()
        font_value  = ImageFont.load_default()

    margin_x   = 45
    text_left  = margin_x + 10
    value_x    = text_left + 215 # Balanced spacing based on reference

    # ── 1. Photo box dimensions (top-right corner) ────────────────────
    photo_w, photo_h = 210, 255
    photo_x = width - margin_x - photo_w
    photo_y = 115

    # max x that text (value) should NOT exceed
    text_right_limit = photo_x - 20

    # ── 2. Header ─────────────────────────────────────────────────────
    draw.text((width // 2, 45), "CRIMINAL RECORD",
              fill="black", font=font_title, anchor="mm")
    draw.text((width - margin_x, 72), "ANNEXURE",
              fill="black", font=font_annex, anchor="rm")

    draw.line([(margin_x, 88),  (width - margin_x, 88)],  fill="black", width=2)
    draw.line([(margin_x, 96),  (width - margin_x, 96)],  fill="black", width=2)

    # ── 3. Mugshot ────────────────────────────────────────────────────
    try:
        mug = Image.open(mugshot_path).convert("RGB")
        mug = mug.resize((photo_w, photo_h), Image.LANCZOS)
        img.paste(mug, (photo_x, photo_y))
    except Exception as e:
        print(f"Mugshot error: {e}")
        draw.rectangle([photo_x, photo_y,
                         photo_x + photo_w, photo_y + photo_h],
                        outline="black", width=1)
        draw.text((photo_x + photo_w // 2, photo_y + photo_h // 2),
                  "PHOTO\nNOT AVAIL", fill="gray", font=font_label, anchor="mm")

    # Frame around photo
    draw.rectangle([photo_x - 2, photo_y - 2,
                     photo_x + photo_w + 2, photo_y + photo_h + 2],
                    outline="black", width=2)

    # Helper for wrapping text
    def draw_wrapped_text(draw, text, font, x, y, max_w, line_spacing=22):
        words = str(text).split()
        lines = []
        if not words: return y
        
        curr_line = words[0]
        for word in words[1:]:
            test_line = curr_line + " " + word
            # Use textlength for newer PIL, fallback to textsize
            try:
                w = draw.textlength(test_line, font=font)
            except:
                w, _ = draw.textsize(test_line, font=font)
                
            if w <= max_w:
                curr_line = test_line
            else:
                lines.append(curr_line)
                curr_line = word
        lines.append(curr_line)
        
        for line in lines:
            draw.text((x, y), line, fill=(0, 0, 0), font=font)
            y += line_spacing
        return y

    # ── 4. Fields ─────────────────────────────────────────────────────
    fields = [
        ("1. Full Name:",              data.get("name",        "")),
        ("2. Age / Gender:",           data.get("age_gender",  "")),
        ("3. Address:",                data.get("address",     "")),
        ("4. Police Station (Primary):", data.get("ps1",       "")),
        ("5. FIR No. 1:",              data.get("fir1",        "")),
        ("6. P.S. (Associated):",      data.get("ps2",         "")),
        ("7. FIR No. 2:",              data.get("fir2",        "")),
        ("8. P.S. (Archive):",         data.get("ps3",         "")),
        ("9. Date of Arrest:",         data.get("arrest_date", "")),
        ("10. Case No. 1:",            data.get("case1",       "")),
        ("11. P.S. / IPC Sections:",   data.get("ps4_section", "")),
        ("12. Case No. 2:",            data.get("case2",       "")),
        ("13. ID Marks:",              data.get("id_marks",    "")),
    ]

    curr_y    = 118
    row_h     = 68 # Slightly smaller rows to fit 13 fields
    split_row = 5
    value_x   = text_left + 265 # Increased indentation for better label spacing

    for i, (label, value) in enumerate(fields):
        # Determine max width for the value
        if i < split_row:
            max_w = photo_x - value_x - 15
        else:
            max_w = width - margin_x - value_x - 10

        # Draw Label (Pure Black for High Contrast)
        draw.text((text_left, curr_y), label, fill=(0, 0, 0), font=font_label)

        # Draw Value (Wrapped & Perfectly Aligned)
        draw_wrapped_text(draw, value, font_value, value_x, curr_y, max_w)

        # Draw underline Separator (Slightly darker for better definition)
        line_y = curr_y + row_h - 18
        line_end = (photo_x - 10) if i < split_row else (width - margin_x)
        draw.line([(text_left, line_y), (line_end, line_y)], fill=(210, 210, 210), width=1)

        curr_y += row_h

    # ── 5. Footer ─────────────────────────────────────────────────────
    footer_y = height - 55
    draw.line([(margin_x, footer_y), (width - margin_x, footer_y)],
              fill=(180, 180, 180), width=1)
    draw.text((width // 2, footer_y + 18),
              "Generated by SENTINEL FORENSIC HUB  |  Secured via Multi-Layer Encryption",
              fill=(160, 160, 160), font=font_annex, anchor="mm")

    img.save(output_path)
    return output_path


def get_random_honey_data(original_name=""):
    """Generates professional-looking fake data for the Honey document with gender consistency"""
    # 1. First, pick a gender
    target_gender = random.choice(["Male", "Female"])
    
    # 2. Pick a name matching that gender
    male_names = ["Kiran Kumar", "Amir Khan", "Suresh Raina", "Rahul Sharma", "Vikram Rathore", "Sanjay Dutt"]
    female_names = ["Priya Singh", "Anjali Devi", "Sneha Kapoor", "Ritu Phogat", "Meera Nair", "Deepika Iyer"]
    
    if target_gender == "Male":
        name = random.choice([n for n in male_names if n != original_name])
    else:
        name = random.choice([n for n in female_names if n != original_name])

    addrs    = ["12, Main Road, Bangalore", "Sector 4, Rohini, Delhi",
                "Block B, Salt Lake, Kolkata", "45, Marine Drive, Mumbai"]
    stations = ["City Police Station", "Central Police Station",
                "Cyber Crime Branch", "Highway Patrol", "Harbor Station"]

    return {
        "name":          name,
        "age_gender":    f"{random.randint(22, 55)} / {target_gender}",
        "address":       random.choice(addrs),
        "crime_type":    random.choice(["Assault", "Theft", "Cyber Crime", "Official Record", "Fraud", "Narcotics"]),
        "ps1":           random.choice(stations),
        "fir1":          f"{random.randint(100, 999)}/{random.randint(2018, 2024)}",
        "ps2":           random.choice(stations),
        "fir2":          f"{random.randint(100, 999)}/{random.randint(2018, 2024)}",
        "ps3":           random.choice(stations),
        "arrest_date":   f"{random.randint(1,28):02d}/{random.randint(1,12):02d}/{random.randint(2019,2024)}",
        "case1":         f"CR/{random.randint(1000, 9999)}/{random.randint(2018, 2024)}",
        "ps4_section":   f"IPC {random.randint(300, 500)}, {random.randint(30, 80)} IT Act",
        "case2":         f"IND No. {random.randint(100, 900)}, {random.randint(10, 99)} BNS",
        "id_marks":      random.choice(["Mole on right cheek", "Scar on forehead", "Tattoo on left arm", "None", "Burn mark on shoulder", "Scar on chin"]),
        "target_gender": target_gender # EXTREMELY IMPORTANT: Used for picking the proxy photo
    }
