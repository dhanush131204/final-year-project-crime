import os
import sqlite3
import uuid
import datetime
from pathlib import Path
import pytz
from twilio.rest import Client
from dotenv import load_dotenv

# Load environment variables
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / '.env')

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
    send_file,
)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

# Utils
from utils.dna_logic import encode_to_dna
from utils.image_processor import split_image_into_tiles
from utils.honey_logic import generate_honey_image

# Indian timezone
INDIAN_TZ = pytz.timezone('Asia/Kolkata')

# Email Configuration
GMAIL_USER = os.getenv('GMAIL_USER')
GMAIL_APP_PASSWORD = os.getenv('GMAIL_APP_PASSWORD')

# Twilio Configuration
TWILIO_ACCOUNT_SID = 'AC735251d90f22acc649958033ca19aaf8'
TWILIO_AUTH_TOKEN = 'e6a6608971cbd33c9da4142060c27397'
TWILIO_PHONE_NUMBER = '+16402274175'

def get_indian_time():
    return datetime.datetime.now(INDIAN_TZ)

# -------------------------------------------------
# Paths & Config
# -------------------------------------------------
DB_DIR = BASE_DIR / "database"
DB_PATH = DB_DIR / "records.db"

STATIC_DIR = BASE_DIR / "static"
UPLOAD_DIR = STATIC_DIR / "uploads"
TILES_DIR = STATIC_DIR / "tiles"
HONEY_DIR = STATIC_DIR / "honey_data"

TEMPLATES_DIR = BASE_DIR / "templates"

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg"}

# Create required folders
for d in [DB_DIR, UPLOAD_DIR, TILES_DIR, HONEY_DIR]:
    d.mkdir(parents=True, exist_ok=True)

app = Flask(
    __name__,
    static_folder=str(STATIC_DIR),
    template_folder=str(TEMPLATES_DIR),
)

app.config["SECRET_KEY"] = "dev-secret-change-me"
app.config["UPLOAD_FOLDER"] = str(UPLOAD_DIR)

# -------------------------------------------------
# Helpers
# -------------------------------------------------

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def to_static_filename(path_value):
    """Normalize DB path values like 'static/uploads/a.jpg' for url_for('static', ...)."""
    if not path_value:
        return None
    normalized = str(path_value).replace("\\", "/").lstrip("/")
    if normalized.startswith("static/"):
        return normalized[len("static/"):]
    return normalized


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# -------------------------------------------------
# Database Init
# -------------------------------------------------

def init_db():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        role TEXT,
        username TEXT UNIQUE,
        password_dna TEXT,
        password_hash TEXT,
        created_at TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS criminals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        mobile TEXT,
        crime_type TEXT,
        photo_path TEXT,
        tile_dir TEXT,
        honey_path TEXT,
        created_at TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS keys (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        record_id INTEGER,
        secret_key TEXT UNIQUE,
        valid INTEGER DEFAULT 1,
        created_at TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        actor TEXT,
        action TEXT,
        details TEXT,
        ip TEXT,
        timestamp TEXT
    )
    """)

    # Default Admin
    cur.execute("SELECT id FROM users WHERE role='admin'")
    if not cur.fetchone():
        cur.execute(
            "INSERT INTO users(role, username, password_hash, created_at) VALUES (?,?,?,?)",
            ("admin", "admin", generate_password_hash("Admin123"), get_indian_time().isoformat()),
        )

    conn.commit()
    conn.close()


init_db()

# -------------------------------------------------
# Logging
# -------------------------------------------------

def log_event(actor, action, details=None):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO logs(actor, action, details, ip, timestamp) VALUES (?,?,?,?,?)",
        (
            actor,
            action,
            details,
            request.remote_addr,
            get_indian_time().isoformat(),
        ),
    )
    conn.commit()
    conn.close()


def send_email_key(email, name, key):
    """Send access key via email to verifier"""
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    
    if not GMAIL_USER or not GMAIL_APP_PASSWORD:
        error_msg = f"Email credentials not configured. GMAIL_USER: {GMAIL_USER}, GMAIL_APP_PASSWORD: {'***' if GMAIL_APP_PASSWORD else 'NOT SET'}"
        print(error_msg)
        print(f"Access Key for {name}: {key}")
        flash(f"Email not configured. Access Key: {key}", "warning")
        return False
    
    try:
        msg = MIMEMultipart()
        msg['From'] = GMAIL_USER
        msg['To'] = email
        msg['Subject'] = "DNA Forensic System - Access Key"
        
        body = f"""Dear Verifier,

Access Key for: {name}
Key: {key}

Use this key in the DNA Forensic System to verify the criminal record.

⚠️ Keep this key confidential!

Best regards,
DNA Forensic Team"""
        
        msg.attach(MIMEText(body, 'plain'))
        
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
        server.sendmail(GMAIL_USER, email, msg.as_string())
        server.quit()
        
        log_event("system", "email_sent", f"Verification key sent to {email} for {name}")
        flash(f"Access key sent successfully to {email}", "success")
        return True
        
    except Exception as e:
        print(f"Failed to send email to {email}: {str(e)}")
        log_event("system", "email_failed", f"Failed to send email to {email}: {str(e)}")
        flash(f"Email failed. Access Key: {key}", "warning")
        return False


def send_sms_key(phone_number, name, key):
    """Send access key via SMS using Twilio"""
    try:
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        
        message_body = f"DNA Forensic System\n\nAccess Key for: {name}\nKey: {key}\n\nUse this key to verify the criminal record securely.\n\nKeep confidential!"
        
        message = client.messages.create(
            body=message_body,
            from_=TWILIO_PHONE_NUMBER,
            to=phone_number
        )
        
        log_event("system", "sms_sent", f"Verification key sent to {phone_number} for {name}")
        print(f"SMS sent successfully to {phone_number}. Message SID: {message.sid}")
        return True
        
    except Exception as e:
        print(f"Failed to send SMS to {phone_number}: {str(e)}")
        log_event("system", "sms_failed", f"Failed to send SMS to {phone_number}: {str(e)}")
        return False


# -------------------------------------------------
# Public Routes
# -------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


# -------------------------------------------------
# Admin Authentication
# -------------------------------------------------

@app.route("/login/admin", methods=["GET", "POST"])
def login_admin():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = get_conn()
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM users WHERE role='admin' AND username=?",
            (username,),
        )
        admin = cur.fetchone()
        conn.close()

        if admin and admin["password_hash"] and check_password_hash(admin["password_hash"], password):
            session["admin"] = username
            log_event(f"admin:{username}", "login")
            return redirect(url_for("admin_dashboard"))
        else:
            flash("Invalid Admin Credentials", "error")

    return render_template("login_admin.html")


def require_admin():
    if "admin" not in session:
        flash("Admin login required", "error")
        return False
    return True


# -------------------------------------------------
# Verifier Authentication
# -------------------------------------------------

@app.route("/login/verifier", methods=["GET", "POST"])
def login_verifier():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = get_conn()
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM users WHERE role='verifier' AND username=?",
            (username,),
        )
        user = cur.fetchone()
        conn.close()

        if user and user["password_hash"] and check_password_hash(user["password_hash"], password):
            session["verifier"] = username
            log_event(f"verifier:{username}", "login")
            return redirect(url_for("verifier_view"))
        else:
            flash("Invalid Verifier Credentials", "error")

    return render_template("login_verifier.html")


@app.route("/register/verifier", methods=["GET", "POST"])
def register_verifier():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        confirm = request.form["confirm"]

        if password != confirm:
            flash("Passwords do not match", "error")
            return render_template("register_verifier.html")

        conn = get_conn()
        cur = conn.cursor()
        try:
            cur.execute(
                "INSERT INTO users(role, username, password_hash, created_at) VALUES (?,?,?,?)",
                (
                    "verifier",
                    username,
                    generate_password_hash(password),
                    get_indian_time().isoformat(),
                ),
            )
            conn.commit()
            flash("Registration Successful", "success")
            return redirect(url_for("login_verifier"))
        except sqlite3.IntegrityError:
            flash("Username already exists", "error")
        finally:
            conn.close()

    return render_template("register_verifier.html")


# -------------------------------------------------
# Admin Dashboard
# -------------------------------------------------

@app.route("/admin")
def admin_dashboard():
    if not require_admin():
        return redirect(url_for("login_admin"))

    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM criminals ORDER BY id DESC")
    records = cur.fetchall()
    cur.execute("SELECT * FROM logs ORDER BY id DESC LIMIT 20")
    logs = cur.fetchall()
    conn.close()

    return render_template("admin_dashboard.html", records=records, logs=logs)


@app.route("/admin/records")
def admin_records():
    if not require_admin():
        return redirect(url_for("login_admin"))
    
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM criminals ORDER BY id DESC")
    records = cur.fetchall()
    conn.close()
    
    return render_template("admin_records.html", records=records)


@app.route("/admin/records/<int:record_id>/tiles")
def admin_record_tiles(record_id):
    if not require_admin():
        return redirect(url_for("login_admin"))

    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, name, photo_path, tile_dir FROM criminals WHERE id = ?",
        (record_id,),
    )
    record = cur.fetchone()
    conn.close()

    if not record:
        flash("Record not found", "error")
        return redirect(url_for("admin_records"))

    tile_dir_rel = to_static_filename(record["tile_dir"])
    if not tile_dir_rel:
        flash("Tile directory is not configured for this record", "error")
        return redirect(url_for("admin_records"))

    tile_dir_path = STATIC_DIR / tile_dir_rel
    tile_dir_path.mkdir(parents=True, exist_ok=True)

    tile_files = sorted(
        [
            p
            for p in tile_dir_path.iterdir()
            if p.is_file() and p.suffix.lower() in {".png", ".jpg", ".jpeg"}
        ],
        key=lambda p: p.name,
    )

    # If tiles are missing, regenerate from original image so the page is usable.
    if not tile_files:
        photo_rel = to_static_filename(record["photo_path"])
        if photo_rel:
            photo_path = STATIC_DIR / photo_rel
            if photo_path.exists():
                split_image_into_tiles(str(photo_path), str(tile_dir_path))
                tile_files = sorted(
                    [
                        p
                        for p in tile_dir_path.iterdir()
                        if p.is_file() and p.suffix.lower() in {".png", ".jpg", ".jpeg"}
                    ],
                    key=lambda p: p.name,
                )

    tile_urls = [
        url_for(
            "static",
            filename=str(tile_path.relative_to(STATIC_DIR)).replace("\\", "/"),
        )
        for tile_path in tile_files
    ]

    return render_template(
        "admin_tiles.html",
        record=record,
        tile_urls=tile_urls,
    )


@app.route("/admin/records/<int:record_id>/honey")
def admin_record_honey(record_id):
    if not require_admin():
        return redirect(url_for("login_admin"))

    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT name, photo_path, honey_path FROM criminals WHERE id = ?", (record_id,))
    record = cur.fetchone()
    conn.close()

    if not record:
        flash("Record not found", "error")
        return redirect(url_for("admin_records"))

    # Try to find the honey file
    honey_rel = to_static_filename(record["honey_path"])
    if honey_rel:
        honey_path = STATIC_DIR / honey_rel
        if honey_path.exists():
            return redirect(url_for("static", filename=honey_rel))

    # Fallback: check if it's in static/uploads with the timestamp (legacy fix)
    try:
        # Extract timestamp from photo_path if possible
        import re
        photo_name = os.path.basename(record["photo_path"])
        match = re.search(r"(\d{8}_\d{6})", photo_name)
        if match:
            ts = match.group(1)
            legacy_honey = STATIC_DIR / "uploads" / f"{ts}_honey_decoy.png"
            if legacy_honey.exists():
                return redirect(url_for("static", filename=f"uploads/{ts}_honey_decoy.png"))
    except Exception:
        pass

    # If still not found, try to generate it now
    try:
        photo_rel = to_static_filename(record["photo_path"])
        if photo_rel:
            photo_path = STATIC_DIR / photo_rel
            if photo_path.exists():
                h_dirname = f"honey_gen_{record_id}"
                h_dir = HONEY_DIR / h_dirname
                h_dir.mkdir(parents=True, exist_ok=True)
                generate_honey_image(str(photo_path), str(h_dir))
                new_rel = f"honey_data/{h_dirname}/honey_decoy.png"
                
                # Update DB for future
                conn = get_conn()
                cur = conn.cursor()
                cur.execute("UPDATE criminals SET honey_path = ? WHERE id = ?", (f"static/{new_rel}", record_id))
                conn.commit()
                conn.close()
                
                return redirect(url_for("static", filename=new_rel))
    except Exception as e:
        print(f"Failed to generate honey on fly: {e}")

    flash("Honey image not found and could not be generated", "error")
    return redirect(url_for("admin_records"))


@app.route("/admin/keys")
def admin_keys():
    if not require_admin():
        return redirect(url_for("login_admin"))
    
    conn = get_conn()
    cur = conn.cursor()
    
    # Get all keys with record names
    cur.execute("""
        SELECT k.id as key_id, k.record_id, k.secret_key, k.valid, k.created_at, c.name 
        FROM keys k 
        LEFT JOIN criminals c ON k.record_id = c.id 
        ORDER BY k.id DESC
    """)
    keys = cur.fetchall()
    
    # Get all records for the dropdown
    cur.execute("SELECT id, name, mobile FROM criminals ORDER BY name")
    records = cur.fetchall()
    
    conn.close()
    
    return render_template("admin_keys.html", keys=keys, records=records)


@app.route("/admin/keys/send", methods=["GET", "POST"])
def admin_keys_send():
    if not require_admin():
        return redirect(url_for("login_admin"))
    
    if request.method == "POST":
        record_id = request.form.get("record_id")
        contact_type = request.form.get("contact_type")
        contact = request.form.get("contact")
        
        if not record_id or not contact:
            flash("Please select a record and enter contact information", "error")
            return redirect(url_for("admin_keys_send"))
        
        try:
            # Get criminal details
            conn = get_conn()
            cur = conn.cursor()
            cur.execute("SELECT name FROM criminals WHERE id = ?", (record_id,))
            criminal = cur.fetchone()
            
            if not criminal:
                flash("Criminal record not found", "error")
                return redirect(url_for("admin_keys_send"))
            
            # Generate new key
            secret_key = str(uuid.uuid4())
            
            cur.execute(
                "INSERT INTO keys(record_id, secret_key, valid, created_at) VALUES (?,?,?,?)",
                (record_id, secret_key, 1, datetime.datetime.now(datetime.UTC).isoformat()),
            )
            conn.commit()
            conn.close()
            
            # Send key based on contact type
            if contact_type == "email":
                send_email_key(contact, criminal["name"], secret_key)
                method = "email"
            else:
                send_sms_key(contact, criminal["name"], secret_key)
                method = "SMS"
            
            log_event(f"admin:{session.get('admin')}", "generate_key", f"Generated key for record {record_id} and sent to {contact}")
            flash(f"Access key generated and sent to {contact} via {method}!", "success")
            return redirect(url_for("admin_keys"))
            
        except Exception as e:
            flash(f"Error generating key: {str(e)}", "error")
    
    # Get records for dropdown
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, name FROM criminals ORDER BY name")
    records = cur.fetchall()
    conn.close()
    
    return render_template("admin_keys_send.html", records=records)


@app.route("/admin/keys/generate", methods=["POST"])
def admin_keys_generate():
    if not require_admin():
        return redirect(url_for("login_admin"))
    
    record_id = request.form.get("record_id")
    
    if not record_id:
        flash("Please select a record", "error")
        return redirect(url_for("admin_keys"))
    
    try:
        # Get criminal details including mobile number
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("SELECT name, mobile FROM criminals WHERE id = ?", (record_id,))
        criminal = cur.fetchone()
        
        if not criminal:
            flash("Criminal record not found", "error")
            return redirect(url_for("admin_keys"))
        
        if not criminal["mobile"]:
            flash("No mobile number found for this criminal record", "error")
            return redirect(url_for("admin_keys"))
        
        # Generate new key
        secret_key = str(uuid.uuid4())
        
        cur.execute(
            "INSERT INTO keys(record_id, secret_key, valid, created_at) VALUES (?,?,?,?)",
            (record_id, secret_key, 1, datetime.datetime.now(datetime.UTC).isoformat()),
        )
        conn.commit()
        conn.close()
        
        # Send email with the key
        send_email_key(criminal["mobile"], criminal["name"], secret_key)
        
        log_event(f"admin:{session.get('admin')}", "generate_key", f"Generated key for record {record_id} and sent to {criminal['mobile']}")
        flash(f"New access key generated and sent to {criminal['mobile']} via email!", "success")
        
    except Exception as e:
        flash(f"Error generating key: {str(e)}", "error")
    
    return redirect(url_for("admin_keys"))


@app.route("/admin/keys/revoke/<int:key_id>", methods=["POST"])
def admin_keys_revoke(key_id):
    if not require_admin():
        return redirect(url_for("login_admin"))
    
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("UPDATE keys SET valid = 0 WHERE id = ?", (key_id,))
        conn.commit()
        conn.close()
        
        log_event(f"admin:{session.get('admin')}", "revoke_key", f"Revoked key {key_id}")
        flash("Key revoked successfully!", "success")
        
    except Exception as e:
        flash(f"Error revoking key: {str(e)}", "error")
    
    return redirect(url_for("admin_keys"))


@app.route("/admin/records/new", methods=["GET", "POST"])
def admin_add_record_page():
    if not require_admin():
        return redirect(url_for("login_admin"))
    
    if request.method == "POST":
        name = request.form.get("name")
        mobile = request.form.get("mobile")
        crime_type = request.form.get("crime_type")
        file = request.files.get("file")
        
        if not name or not mobile or not crime_type:
            flash("Name, Verifier Email Address and Crime Type are required", "error")
            return render_template("admin_add_record.html")
        
        if not file or not allowed_file(file.filename):
            flash("Please upload a valid image file (PNG, JPG, JPEG)", "error")
            return render_template("admin_add_record.html")
        
        try:
            # Save uploaded file
            filename = secure_filename(file.filename)
            timestamp = get_indian_time().strftime("%Y%m%d_%H%M%S")
            filename = f"{timestamp}_{filename}"
            file_path = UPLOAD_DIR / filename
            file.save(str(file_path))
            
            # Create tiles directory
            tile_dirname = f"tiles_{timestamp}"
            tile_path = TILES_DIR / tile_dirname
            tile_path.mkdir(exist_ok=True)
            
            # Process image into tiles
            split_image_into_tiles(str(file_path), str(tile_path))
            
            # Generate honey data
            honey_dirname = f"honey_{timestamp}"
            honey_dir = HONEY_DIR / honey_dirname
            honey_dir.mkdir(parents=True, exist_ok=True)
            honey_path_abs = generate_honey_image(str(file_path), str(honey_dir))
            honey_rel_path = f"static/honey_data/{honey_dirname}/honey_decoy.png"
            
            # Save to database
            conn = get_conn()
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO criminals(name, mobile, crime_type, photo_path, tile_dir, honey_path, created_at) VALUES (?,?,?,?,?,?,?)",
                (
                    name,
                    mobile,
                    crime_type,
                    f"static/uploads/{filename}",
                    f"static/tiles/{tile_dirname}",
                    honey_rel_path,
                    get_indian_time().isoformat(),
                ),
            )
            record_id = cur.lastrowid
            
            # Auto-generate access key for this record
            secret_key = str(uuid.uuid4())
            cur.execute(
                "INSERT INTO keys(record_id, secret_key, valid, created_at) VALUES (?,?,?,?)",
                (record_id, secret_key, 1, datetime.datetime.now(datetime.UTC).isoformat()),
            )
            
            conn.commit()
            conn.close()
            
            # Send WhatsApp message with the key
            send_email_key(mobile, name, secret_key)
            
            log_event(f"admin:{session.get('admin')}", "add_criminal", f"Added {name} with verification key sent to {mobile}")
            flash(f"Criminal record for {name} added successfully! Verification key sent to verifier at {mobile} via email.", "success")
            return redirect(url_for("admin_dashboard"))
            
        except Exception as e:
            flash(f"Error processing record: {str(e)}", "error")
            return render_template("admin_add_record.html")
    
    return render_template("admin_add_record.html")


@app.route("/admin/records/edit/<int:record_id>", methods=["GET", "POST"])
def admin_edit_record(record_id):
    if not require_admin():
        return redirect(url_for("login_admin"))
    
    conn = get_conn()
    cur = conn.cursor()
    
    if request.method == "POST":
        name = request.form.get("name")
        mobile = request.form.get("mobile")
        crime_type = request.form.get("crime_type")
        
        if not name or not mobile or not crime_type:
            flash("Name, Email and Crime Type are required", "error")
            return redirect(url_for("admin_edit_record", record_id=record_id))
            
        try:
            cur.execute(
                "UPDATE criminals SET name = ?, mobile = ?, crime_type = ? WHERE id = ?",
                (name, mobile, crime_type, record_id)
            )
            conn.commit()
            log_event(f"admin:{session.get('admin')}", "edit_criminal", f"Updated record {record_id} ({name})")
            flash(f"Record for {name} updated successfully!", "success")
            return redirect(url_for("admin_records"))
        except Exception as e:
            flash(f"Error updating record: {str(e)}", "error")
    
    cur.execute("SELECT * FROM criminals WHERE id = ?", (record_id,))
    record = cur.fetchone()
    conn.close()
    
    if not record:
        flash("Record not found", "error")
        return redirect(url_for("admin_records"))
        
    return render_template("admin_edit_record.html", record=record)


# -------------------------------------------------
# Verifier View
# -------------------------------------------------

@app.route("/verifier")
def verifier_view():
    if "verifier" not in session:
        return redirect(url_for("login_verifier"))
    return render_template("verifier_view.html")


@app.route("/verifier/retrieve", methods=["POST"])
def verifier_retrieve():
    if "verifier" not in session:
        return redirect(url_for("login_verifier"))
    
    key = request.form.get("key")
    
    if not key:
        return render_template("verifier_view.html", error="Please enter a key")
    
    try:
        conn = get_conn()
        cur = conn.cursor()
        
        # Check if key exists and is valid
        cur.execute(
            "SELECT k.record_id, k.valid, c.name, c.crime_type, c.photo_path FROM keys k LEFT JOIN criminals c ON k.record_id = c.id WHERE k.secret_key = ?",
            (key,)
        )
        key_data = cur.fetchone()
        
        if key_data and key_data["valid"]:
            # Valid key - return original data
            log_event(f"verifier:{session.get('verifier')}", "key_used", f"Successfully used key for record {key_data['record_id']}")
            
            return render_template(
                "verifier_result.html",
                record_id=key_data["record_id"],
                name=key_data["name"],
                crime_type=key_data["crime_type"],
                download_url=url_for("download_record", record_id=key_data["record_id"]),
                get_indian_time=get_indian_time
            )
        else:
            # Invalid/wrong key - return honey/decoy data from honey_data folder
            import os
            honey_files = []
            honey_path = BASE_DIR / "static" / "honey_data"
            if honey_path.exists():
                honey_files = [f for f in os.listdir(honey_path) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
            
            if honey_files:
                import random
                selected_file = random.choice(honey_files)
                log_event(f"verifier:{session.get('verifier')}", "honey_triggered", f"Invalid key used, served honey data")
                
                return render_template(
                    "verifier_result.html",
                    record_id=f"H{random.randint(100, 999)}",
                    name=f"John Doe",
                    crime_type=f"Sample Case",
                    download_url=url_for("download_honey_file", filename=selected_file),
                    get_indian_time=get_indian_time
                )
            else:
                # Fallback to random criminal record
                cur.execute("SELECT * FROM criminals ORDER BY RANDOM() LIMIT 1")
                decoy_record = cur.fetchone()
                
                if decoy_record:
                    return render_template(
                        "verifier_result.html",
                        record_id=f"S{decoy_record['id']}",
                        name=decoy_record["name"],
                        crime_type=decoy_record["crime_type"],
                        download_url=url_for("download_honey", record_id=decoy_record["id"]),
                        get_indian_time=get_indian_time
                    )
        
        conn.close()
        return render_template("verifier_view.html", error="No data available")
        
    except Exception as e:
        return render_template("verifier_view.html", error=f"Error processing key: {str(e)}")


@app.route("/download/honey/<int:record_id>")
def download_honey(record_id):
    if "verifier" not in session:
        return redirect(url_for("login_verifier"))
    
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("SELECT photo_path FROM criminals WHERE id = ?", (record_id,))
        record = cur.fetchone()
        conn.close()
        
        if record:
            photo_path = BASE_DIR / record["photo_path"].replace("static/", "static/")
            if photo_path.exists():
                return send_file(str(photo_path), as_attachment=True, download_name=f"sample_data_{record_id}.jpg")
        
        flash("Sample file not found", "error")
        return redirect(url_for("verifier_view"))
            
    except Exception as e:
        flash(f"Error downloading sample file: {str(e)}", "error")
        return redirect(url_for("verifier_view"))


@app.route("/download/<int:record_id>")
def download_record(record_id):
    if "verifier" not in session:
        return redirect(url_for("login_verifier"))
    
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("SELECT photo_path FROM criminals WHERE id = ?", (record_id,))
        record = cur.fetchone()
        conn.close()
        
        if not record:
            flash("Record not found", "error")
            return redirect(url_for("verifier_view"))
        
        # Convert relative path to absolute path
        photo_path = BASE_DIR / record["photo_path"].replace("static/", "static/")
        
        if photo_path.exists():
            return send_file(str(photo_path), as_attachment=True, download_name=f"criminal_record_{record_id}.jpg")
        else:
            flash("File not found", "error")
            return redirect(url_for("verifier_view"))
            
    except Exception as e:
        flash(f"Error downloading file: {str(e)}", "error")
        return redirect(url_for("verifier_view"))


# -------------------------------------------------
# Run App
# -------------------------------------------------

@app.route("/download/honey_file/<filename>")
def download_honey_file(filename):
    if "verifier" not in session:
        return redirect(url_for("login_verifier"))
    
    try:
        honey_path = BASE_DIR / "static" / "honey_data" / filename
        if honey_path.exists():
            return send_file(str(honey_path), as_attachment=True, download_name=f"evidence_{filename}")
        else:
            flash("File not found", "error")
            return redirect(url_for("verifier_view"))
    except Exception as e:
        flash(f"Error downloading file: {str(e)}", "error")
        return redirect(url_for("verifier_view"))


if __name__ == "__main__":
    app.run(debug=True,use_reloader=False)
