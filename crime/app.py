import os
import sqlite3
import uuid
import datetime
from pathlib import Path
import pytz
from twilio.rest import Client

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

# Twilio Configuration - Replace with your actual credentials
TWILIO_ACCOUNT_SID = 'AC6c4eca36316731f07ad8424325d957a4'
TWILIO_AUTH_TOKEN = '881c8152f57d186e427484285200fc5f'
TWILIO_PHONE_NUMBER = '+12345678901'  # Replace with your Twilio phone number

def get_indian_time():
    return datetime.datetime.now(INDIAN_TZ)

# -------------------------------------------------
# Paths & Config
# -------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent
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
    try:
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        
        # Gmail SMTP configuration
        smtp_server = "smtp.gmail.com"
        smtp_port = 587
        sender_email = "your_email@gmail.com"  # Replace with your Gmail
        sender_password = "your_app_password"   # Replace with your Gmail app password
        
        # Create message
        msg = MIMEMultipart()
        msg['From'] = sender_email
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
        
        # Send email
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender_email, sender_password)
        text = msg.as_string()
        server.sendmail(sender_email, email, text)
        server.quit()
        
        log_event("system", "email_sent", f"Verification key sent to {email} for {name}")
        print(f"Email sent successfully to {email}")
        return True
        
    except Exception as e:
        print(f"Failed to send email to {email}: {str(e)}")
        log_event("system", "email_failed", f"Failed to send email to {email}: {str(e)}")
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
                (record_id, secret_key, 1, datetime.datetime.utcnow().isoformat()),
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
            (record_id, secret_key, 1, datetime.datetime.utcnow().isoformat()),
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
            
            # Process image into tiles (placeholder - implement actual tiling)
            # split_image_into_tiles(str(file_path), str(tile_path))
            
            # Generate honey data (placeholder)
            honey_filename = f"honey_{timestamp}.png"
            honey_path = HONEY_DIR / honey_filename
            # generate_honey_image(str(honey_path))
            
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
                    f"static/honey_data/{honey_filename}",
                    get_indian_time().isoformat(),
                ),
            )
            record_id = cur.lastrowid
            
            # Auto-generate access key for this record
            secret_key = str(uuid.uuid4())
            cur.execute(
                "INSERT INTO keys(record_id, secret_key, valid, created_at) VALUES (?,?,?,?)",
                (record_id, secret_key, 1, datetime.datetime.utcnow().isoformat()),
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
    app.run(debug=True)
