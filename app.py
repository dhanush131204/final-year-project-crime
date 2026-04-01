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
    jsonify
)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

# Utils
from utils.dna_logic import encode_to_dna, decode_from_dna
from utils.image_processor import split_image_into_tiles
from utils.honey_logic import generate_honey_image
from utils.encryption_utils import encrypt_file, decrypt_file_to_bytes
import io

# Indian timezone
INDIAN_TZ = pytz.timezone('Asia/Kolkata')

# Document Generator
from utils.document_generator import generate_official_document, get_random_honey_data

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
LEGACY_BASE_DIR = BASE_DIR / "crime"
LEGACY_DB_PATH = LEGACY_BASE_DIR / "database" / "records.db"


def _get_table_count(db_path, table_name):
    if not db_path.exists():
        return -1
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute(f"SELECT COUNT(*) FROM {table_name}")
        count = cur.fetchone()[0]
        conn.close()
        return count
    except sqlite3.Error:
        return -1


def choose_db_path():
    primary_db = DB_DIR / "records.db"
    primary_count = _get_table_count(primary_db, "criminals")
    legacy_count = _get_table_count(LEGACY_DB_PATH, "criminals")

    # In cloned repos there may be both a new root app and an older nested app.
    # Prefer the database that already has records so the dashboard shows the real data.
    if legacy_count > primary_count:
        return LEGACY_DB_PATH
    return primary_db


DB_PATH = choose_db_path()

STATIC_DIR = BASE_DIR / "static"
UPLOAD_DIR = STATIC_DIR / "records" / "primary_vault"
TILES_DIR = STATIC_DIR / "tiles"
HONEY_DIR = STATIC_DIR / "records" / "decoy_vault"
HONEY_POOL = STATIC_DIR / "honey_pool"

TEMPLATES_DIR = BASE_DIR / "templates"

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg"}

# Create required folders
for d in [DB_DIR, UPLOAD_DIR, TILES_DIR, HONEY_DIR, HONEY_POOL]:
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
        email TEXT UNIQUE,
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
        age_gender TEXT,
        address TEXT,
        ps1 TEXT,
        fir1 TEXT,
        ps2 TEXT,
        fir2 TEXT,
        ps3 TEXT,
        arrest_date TEXT,
        case1 TEXT,
        ps4_section TEXT,
        case2 TEXT,
        id_marks TEXT,
        honey_name TEXT,
        honey_crime_type TEXT,
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
        user_agent TEXT,
        timestamp TEXT
    )
    """)

    # Migration for logs: Add user_agent if it doesn't exist
    cur.execute("PRAGMA table_info(logs)")
    logs_cols = [row[1] for row in cur.fetchall()]
    if "user_agent" not in logs_cols:
        cur.execute("ALTER TABLE logs ADD COLUMN user_agent TEXT")

    # Migration for users: Add email if it doesn't exist
    cur.execute("PRAGMA table_info(users)")
    user_cols = [row[1] for row in cur.fetchall()]
    if "email" not in user_cols:
        cur.execute("ALTER TABLE users ADD COLUMN email TEXT")

    # Migration for criminals: Add new columns if they don't exist
    cur.execute("PRAGMA table_info(criminals)")
    criminal_cols = [row[1] for row in cur.fetchall()]
    
    needed_cols = [
        "age_gender", "address", "ps1", "fir1", "ps2", "fir2", "ps3", 
        "arrest_date", "case1", "ps4_section", "case2", "id_marks", 
        "honey_name", "honey_crime_type"
    ]
    
    for col in needed_cols:
        if col not in criminal_cols:
            try:
                cur.execute(f"ALTER TABLE criminals ADD COLUMN {col} TEXT")
                print(f"Added missing column: {col}")
            except sqlite3.Error as e:
                print(f"Error adding column {col}: {e}")

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
        "INSERT INTO logs(actor, action, details, ip, user_agent, timestamp) VALUES (?,?,?,?,?,?)",
        (
            actor,
            action,
            details,
            request.remote_addr,
            request.user_agent.string,
            get_indian_time().isoformat(),
        ),
    )
    conn.commit()
    conn.close()


def send_email_key(email, name, key):
    """Send access key via email to verifier using Brevo API"""
    import requests
    
    brevo_api_key = os.getenv('BREVO_API_KEY')
    sender_email = os.getenv('GMAIL_USER') or 'admin@crimesecure.local'
    
    if not brevo_api_key:
        error_msg = f"Brevo API Key not configured. Using fallback log."
        print(error_msg)
        print(f"Access Key for {name}: {key}")
        flash(f"Email not configured. Access Key: {key}", "warning")
        return False
    
    try:
        url = "https://api.brevo.com/v3/smtp/email"
        
        payload = {
            "sender": {"email": sender_email, "name": "DNA Forensic Team"},
            "to": [{"email": email, "name": "Verifier"}],
            "subject": "DNA Forensic System - Access Key",
            "textContent": f"Dear Verifier,\n\nAccess Key for: {name}\nKey: {key}\n\nUse this key in the DNA Forensic System to verify the criminal record.\n\n⚠️ Keep this key confidential!\n\nBest regards,\nDNA Forensic Team"
        }
        
        headers = {
            "accept": "application/json",
            "api-key": brevo_api_key,
            "content-type": "application/json"
        }
        
        response = requests.post(url, json=payload, headers=headers)
        
        if response.status_code in [200, 201, 202]:
            log_event("system", "email_sent", f"Verification key sent to {email} for {name} via Brevo")
            flash(f"Access key sent successfully to {email}", "success")
            return True
        else:
            print(f"Brevo Error: {response.text}")
            log_event("system", "email_failed", f"Brevo API failed: {response.text}")
            flash(f"Email failed to send. Access Key: {key}", "warning")
            return False
            
    except Exception as e:
        print(f"Failed to send email to {email}: {str(e)}")
        log_event("system", "email_failed", f"Exception: {str(e)}")
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
            return redirect(url_for("index", auth_error=1))
            
    return render_template("login_admin.html")
            
@app.route("/admin/verify-action", methods=["POST"])
def admin_verify_action():
    if "admin" not in session:
        return jsonify({"success": False, "message": "Admin session expired. Please login again."}), 401
    
    password = request.form.get("password")
    if not password:
        return jsonify({"success": False, "message": "Password is required."}), 400
        
    username = session["admin"]
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT password_hash FROM users WHERE role='admin' AND username=?", (username,))
    admin = cur.fetchone()
    conn.close()
    
    if admin and check_password_hash(admin["password_hash"], password):
        log_event(f"admin:{username}", "security_verified", "Sensitive action authorized via popup")
        return jsonify({"success": True})
    else:
        log_event(f"admin:{username}", "security_failed", "Failed authorization attempt for sensitive action")
        return jsonify({"success": False, "message": "Invalid password. Access denied."}), 403

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
        username = request.form["username"] # This is the input from Modal (can be Name or Email)
        password = request.form["password"]

        conn = get_conn()
        cur = conn.cursor()
        
        # DNA Protection Search
        encoded_input = encode_to_dna(username)
        
        # Check DNA username OR DNA email
        cur.execute(
            "SELECT * FROM users WHERE (role='verifier' OR role='Verifier') AND (username=? OR email=? OR username=? OR email=?)",
            (username, username, encoded_input, encoded_input),
        )
        user = cur.fetchone()
        conn.close()

        if user and check_password_hash(user["password_hash"], password):
            # Session uses the plain-text name for display
            session["verifier"] = username
            session["role"] = "verifier"
            log_event(f"verifier:{username}", "login", "Authorized via Home Modal (DNA Active)")
            return redirect(url_for("verifier_view"))
        else:
            log_event(f"anonymous", "login_failed", f"Failed verifier login: {username}")
            flash("Invalid Verifier Credentials. Check your name/email and password.", "error")
            return redirect(url_for("index", auth_error=1, role="verifier"))

    return redirect(url_for("index", _anchor="login"))


@app.route("/register/verifier", methods=["GET", "POST"])
def register_verifier():
    if request.method == "POST":
        username = request.form["username"] # Full Name
        email = request.form["email"]       # Email Address
        password = request.form["password"]
        confirm = request.form["confirm"]

        if password != confirm:
            flash("Passwords do not match. Please try again.", "error")
            return redirect(url_for("index", auth_error=1, role="verifier"))

        conn = get_conn()
        cur = conn.cursor()
        try:
            # Phase 3: DNA DNA DNA! (Protect BOTH Name and Email)
            encoded_name = encode_to_dna(username)
            encoded_email = encode_to_dna(email)
            
            cur.execute(
                "INSERT INTO users(role, username, email, password_hash, created_at) VALUES (?,?,?,?,?)",
                (
                    "verifier",
                    encoded_name,
                    encoded_email,
                    generate_password_hash(password),
                    get_indian_time().isoformat(),
                ),
            )
            conn.commit()
            flash("Personnel Enrollment Successful! Please log in below.", "success")
            return redirect(url_for("index", auth_error=1, role="verifier"))
        except sqlite3.IntegrityError:
            flash("Identifier already exists in database.", "error")
            return redirect(url_for("index", auth_error=1, role="verifier"))
        finally:
            conn.close()

    return redirect(url_for("index"))


# -------------------------------------------------
# Admin Dashboard
# -------------------------------------------------

@app.route("/admin/analytics")
def admin_analytics():
    if not require_admin():
        return redirect(url_for("login_admin"))
    
    conn = get_conn()
    cur = conn.cursor()
    
    # Total access logs
    cur.execute("SELECT COUNT(*) FROM logs")
    total_logs = cur.fetchone()[0]
    
    # Honey Pot triggers
    cur.execute("SELECT COUNT(*) FROM logs WHERE action = 'honey_triggered'")
    honey_triggers = cur.fetchone()[0]
    
    # Top 5 Intruder IPs
    cur.execute("SELECT ip, COUNT(*) as count FROM logs WHERE action = 'honey_triggered' GROUP BY ip ORDER BY count DESC LIMIT 5")
    intruder_ips = cur.fetchall()
    
    # Recent Honey Pot activity
    cur.execute("SELECT * FROM logs WHERE action = 'honey_triggered' ORDER BY timestamp DESC LIMIT 10")
    recent_honey = cur.fetchall()
    
    conn.close()
    
    # Calculate interception rate
    rate = 0
    cur_access_attempts = total_logs # Total interactions
    if cur_access_attempts > 0:
        rate = round((honey_triggers / cur_access_attempts) * 100, 1)

    return render_template(
        "admin_analytics.html", 
        total_logs=total_logs, 
        honey_triggers=honey_triggers, 
        intruder_ips=intruder_ips,
        recent_honey=recent_honey,
        rate=rate
    )


@app.route("/admin/users")
def admin_users():
    if not require_admin():
        return redirect(url_for("login_admin"))
    
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, role, username, email, created_at FROM users ORDER BY id DESC")
    users = cur.fetchall()
    conn.close()
    
    return render_template("admin_users.html", users=users)


@app.route("/admin/users/delete/<int:user_id>", methods=["POST"])
def admin_delete_user(user_id):
    if not require_admin():
        return redirect(url_for("login_admin"))
    
    if session.get("admin") == "admin" and user_id == 1:
        flash("Cannot delete the primary admin account.", "error")
        return redirect(url_for("admin_users"))

    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()
        conn.close()
        flash("User deleted successfully.", "success")
    except Exception as e:
        flash(f"Error deleting user: {str(e)}", "error")
        
    return redirect(url_for("admin_users"))


@app.route("/admin")
def admin_dashboard():
    if not require_admin():
        return redirect(url_for("login_admin"))

    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM criminals ORDER BY id DESC")
    encoded_records = cur.fetchall()
    
    # Phase 3: Decode DNA for Admin View
    records = []
    for r in encoded_records:
        r_dict = dict(r)
        try:
            r_dict["name"] = decode_from_dna(r["name"])
            r_dict["crime_type"] = decode_from_dna(r["crime_type"])
        except Exception:
            pass # Keep original if it was not DNA encoded (legacy data)
        records.append(r_dict)
    
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


@app.route("/admin/records/<int:record_id>/original")
def admin_record_original(record_id):
    if not require_admin():
        return redirect(url_for("login_admin"))

    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT name, photo_path FROM criminals WHERE id = ?", (record_id,))
    record = cur.fetchone()
    conn.close()

    if not record:
        flash("Record not found", "error")
        return redirect(url_for("admin_records"))

    # photo_path stores the original doc in the primary vault
    photo_rel = to_static_filename(record["photo_path"])
    if photo_rel:
        photo_path = STATIC_DIR / photo_rel
        if photo_path.exists():
            return redirect(url_for("static", filename=photo_rel))

    flash("Original forensic record not found", "error")
    return redirect(url_for("admin_records"))


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

    flash("Protected image not found and could not be generated", "error")
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
            
            # Phase 1: Key Hashing
            hashed_key = generate_password_hash(secret_key)
            
            cur.execute(
                "INSERT INTO keys(record_id, secret_key, valid, created_at) VALUES (?,?,?,?)",
                (record_id, hashed_key, 1, datetime.datetime.now(datetime.UTC).isoformat()),
            )
            conn.commit()
            conn.close()
            
            # Send the REAL key to the verifier (but only the HASH is in our DB)
            send_email_key(contact, criminal["name"], secret_key)
            
            log_event(f"admin:{session.get('admin')}", "generate_key", f"Generated key for record {record_id} and sent to {contact} via email")
            flash(f"Access key generated and sent to {contact} via SECURE EMAIL!", "success")
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
            flash("Invalid file format. Please upload a real JPG or PNG image.", "error")
            return render_template("admin_add_record.html")
        
        try:
            # Verify if it's a real image content
            from PIL import Image
            try:
                img_test = Image.open(file)
                img_test.verify() # Basic corruption check
                file.seek(0) # Reset file pointer after verify()
                img_test = Image.open(file) # Re-open for actual processing
                img_test.load()
                file.seek(0)
            except Exception:
                flash("The file you uploaded is not a valid image. Please upload a real JPG or PNG.", "error")
                return render_template("admin_add_record.html")

            # 1. Process Real Forensic Data
            filename = secure_filename(file.filename)
            timestamp = get_indian_time().strftime("%Y%m%d_%H%M%S")
            filename = f"forensic_{timestamp}_{filename}"
            file_path = UPLOAD_DIR / filename
            file.save(str(file_path))
            
            # 2. Create tiles directory
            tile_dirname = f"tiles_{timestamp}"
            tile_path = TILES_DIR / tile_dirname
            tile_path.mkdir(exist_ok=True)
            split_image_into_tiles(str(file_path), str(tile_path))
            
            # 3. Process Decoy (Honey) Data with Gender-Matched Proxy Face
            from utils.document_generator import get_random_honey_data, generate_official_document
            h_data = get_random_honey_data(name)
            target_gender = h_data.get("target_gender", "Male").lower()
            
            # Correctly pick from the subfolder matching the generated gender
            gender_folder = HONEY_POOL / target_gender
            pool_files = []
            if gender_folder.exists():
                pool_files = [f for f in os.listdir(gender_folder) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
            
            import random
            if pool_files:
                random_proxy = str(gender_folder / random.choice(pool_files))
            else:
                # Fallback to main pool if subfolder is empty
                main_pool = [f for f in os.listdir(HONEY_POOL) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
                random_proxy = str(HONEY_POOL / random.choice(main_pool)) if main_pool else str(file_path)
            
            honey_filename = f"decoy_{timestamp}.png"
            honey_path_abs = HONEY_DIR / honey_filename
            
            # Generate the decoy document using the gender-matched face
            generate_official_document(h_data, random_proxy, str(honey_path_abs))
            
            # Save to database
            conn = get_conn()
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO criminals(name, mobile, crime_type, photo_path, tile_dir, honey_path, honey_name, honey_crime_type, created_at) VALUES (?,?,?,?,?,?,?,?,?)",
                (
                    name,
                    mobile,
                    crime_type,
                    f"static/records/primary_vault/{filename}",
                    f"static/tiles/{tile_dirname}",
                    f"static/records/decoy_vault/{honey_filename}",
                    h_data["name"],
                    h_data["crime_type"],
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
            return redirect(url_for("admin_records"))
            
        except Exception as e:
            flash(f"Error processing record: {str(e)}", "error")
            return render_template("admin_add_record.html")
    
    return render_template("admin_add_record.html")


@app.route("/admin/records/advanced", methods=["GET", "POST"])
def admin_add_record_advanced():
    if not require_admin():
        return redirect(url_for("login_admin"))
    
    if request.method == "POST":
        # Get all 12 fields
        form_data = {
            "name": request.form.get("name"),
            "age_gender": request.form.get("age_gender"),
            "address": request.form.get("address"),
            "ps1": request.form.get("ps1"),
            "fir1": request.form.get("fir1"),
            "ps2": request.form.get("ps2"),
            "fir2": request.form.get("fir2"),
            "ps3": request.form.get("ps3"),
            "arrest_date": request.form.get("arrest_date"),
            "case1": request.form.get("case1"),
            "ps4_section": request.form.get("ps4_section"),
            "case2": request.form.get("case2"),
            "id_marks": request.form.get("id_marks")
        }
        
        # Validate all fields
        if any(not v for v in form_data.values()):
            flash("All 12 forensic fields are required for advanced entry.", "error")
            return render_template("admin_add_record_advanced.html")
        crime_type = request.form.get("crime_type") or "Official Record"
        mobile = "" # Verifier Email removed from UI; key generated and sent separately
        file = request.files.get("file") # Mugshot
        
        if not file or not allowed_file(file.filename):
            flash("Invalid file format. Please upload a real JPG or PNG image.", "error")
            return render_template("admin_add_record_advanced.html")
            
        try:
            # Verify if it's a real image content
            from PIL import Image
            try:
                img_test = Image.open(file)
                img_test.verify() # Basic corruption check
                file.seek(0) # Reset file pointer
                img_test = Image.open(file)
                img_test.load()
                file.seek(0)
            except Exception:
                flash("The file you uploaded is not a valid image content. Please upload a real JPG or PNG photo.", "error")
                return render_template("admin_add_record_advanced.html")

            # 1. Process Real Forensic Mugshot & Document (PRIMARY VAULT)
            filename = secure_filename(file.filename)
            timestamp = get_indian_time().strftime("%Y%m%d_%H%M%S")
            mugshot_filename = f"forensic_face_{timestamp}_{filename}"
            mugshot_path = UPLOAD_DIR / mugshot_filename
            file.save(str(mugshot_path))
            
            doc_filename = f"forensic_doc_{timestamp}.png"
            doc_path = UPLOAD_DIR / doc_filename
            generate_official_document(form_data, str(mugshot_path), str(doc_path))
            
            # 2. Process Decoy (Honey) Document & Gender-Matched Proxy (DECOY VAULT)
            import random
            honey_data = get_random_honey_data(form_data["name"])
            target_gender = honey_data.get("target_gender", "Male").lower()
            
            # Pick a face matching the generated gender
            gender_folder = HONEY_POOL / target_gender
            pool_files = []
            if gender_folder.exists():
                pool_files = [f for f in os.listdir(gender_folder) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
            
            if pool_files:
                random_proxy = str(gender_folder / random.choice(pool_files))
            else:
                main_pool = [f for f in os.listdir(HONEY_POOL) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
                random_proxy = str(HONEY_POOL / random.choice(main_pool)) if main_pool else str(mugshot_path)
            
            honey_doc_filename = f"decoy_doc_{timestamp}.png"
            honey_doc_path = HONEY_DIR / honey_doc_filename
            
            # Generate honey doc using the GENDER-MATCHED PROXY face
            generate_official_document(honey_data, random_proxy, str(honey_doc_path))
            
            # 3. Tiling (Split Original Doc)
            tile_dirname = f"tiles_{timestamp}"
            tile_path = TILES_DIR / tile_dirname
            tile_path.mkdir(exist_ok=True)
            split_image_into_tiles(str(doc_path), str(tile_path))
            
            # 4. Save to Database with isolated vault paths
            conn = get_conn()
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO criminals(
                    name, mobile, crime_type, photo_path, tile_dir, honey_path, 
                    age_gender, address, ps1, fir1, ps2, fir2, ps3, 
                    arrest_date, case1, ps4_section, case2, id_marks, 
                    honey_name, honey_crime_type, created_at
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    encode_to_dna(form_data["name"]), # Phase 3: DNA DNA DNA!
                    encode_to_dna(mobile),
                    encode_to_dna(crime_type),
                    f"static/records/primary_vault/{doc_filename}",
                    f"static/tiles/{tile_dirname}",
                    f"static/records/decoy_vault/{honey_doc_filename}", 
                    encode_to_dna(form_data["age_gender"]),
                    encode_to_dna(form_data["address"]),
                    encode_to_dna(form_data["ps1"]),
                    encode_to_dna(form_data["fir1"]),
                    encode_to_dna(form_data["ps2"]),
                    encode_to_dna(form_data["fir2"]),
                    encode_to_dna(form_data["ps3"]),
                    encode_to_dna(form_data["arrest_date"]),
                    encode_to_dna(form_data["case1"]),
                    encode_to_dna(form_data["ps4_section"]),
                    encode_to_dna(form_data["case2"]),
                    encode_to_dna(form_data["id_marks"]),
                    encode_to_dna(honey_data["name"]),
                    encode_to_dna(honey_data["crime_type"]),
                    get_indian_time().isoformat(),
                ),
            )
            record_id = cur.lastrowid
            
            # Phase 1: Hash the key
            hashed_key = generate_password_hash(secret_key)
            cur.execute(
                "INSERT INTO keys(record_id, secret_key, valid, created_at) VALUES (?,?,?,?)",
                (record_id, hashed_key, 1, datetime.datetime.now(datetime.UTC).isoformat()),
            )
            
            # Phase 2: Encrypt the Image Files (Primary & Honey)
            encrypt_file(str(doc_path))
            encrypt_file(str(honey_doc_path))
            
            conn.commit()
            conn.close()
            
            # Send Email - Removed since admin does this separately from Access Keys
            
            flash(f"Official Records (Real & Honey) generated and secured for {form_data['name']}. Remember to generate an Access Key.", "success")
            return redirect(url_for("admin_records"))
            
        except Exception as e:
            flash(f"Error: {e}", "error")
            return render_template("admin_add_record_advanced.html")
            
    return render_template("admin_add_record_advanced.html")


@app.route("/admin/records/edit/<int:record_id>", methods=["GET", "POST"])
def admin_edit_record(record_id):
    if not require_admin():
        return redirect(url_for("login_admin"))
    
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM criminals WHERE id = ?", (record_id,))
    record = cur.fetchone()
    
    if not record:
        conn.close()
        flash("Record not found", "error")
        return redirect(url_for("admin_records"))
    
    if request.method == "POST":
        # 1. Collect all 13 fields from form
        form_data = {
            "name": request.form.get("name"),
            "age_gender": request.form.get("age_gender"),
            "address": request.form.get("address"),
            "ps1": request.form.get("ps1"),
            "fir1": request.form.get("fir1"),
            "ps2": request.form.get("ps2"),
            "fir2": request.form.get("fir2"),
            "ps3": request.form.get("ps3"),
            "arrest_date": request.form.get("arrest_date"),
            "case1": request.form.get("case1"),
            "ps4_section": request.form.get("ps4_section"),
            "case2": request.form.get("case2"),
            "id_marks": request.form.get("id_marks")
        }
        mobile = record["mobile"] # Retain existing email, field removed from UI
        crime_type = request.form.get("crime_type")
        file = request.files.get("file") # Optional new Mugshot
        
        try:
            timestamp = get_indian_time().strftime("%Y%m%d_%H%M%S")
            mugshot_path = BASE_DIR / record["photo_path"].replace("static/", "static/") if record["photo_path"] else None
            
            # 2. Handle Photo Update if provided
            if file and allowed_file(file.filename):
                from PIL import Image
                img_test = Image.open(file)
                img_test.verify()
                file.seek(0)
                
                # Save new Mugshot
                filename = secure_filename(file.filename)
                mugshot_filename = f"forensic_face_{timestamp}_{filename}"
                new_mugshot_path = UPLOAD_DIR / mugshot_filename
                file.save(str(new_mugshot_path))
                mugshot_path = new_mugshot_path
            
            # 3. Re-generate Official Document (Primary Vault)
            doc_filename = f"forensic_doc_{timestamp}.png"
            doc_path = UPLOAD_DIR / doc_filename
            generate_official_document(form_data, str(mugshot_path), str(doc_path))
            
            # 4. Re-generate Decoy (Honey) Document (Decoy Vault)
            import random
            honey_data = get_random_honey_data(form_data["name"])
            target_gender = honey_data.get("target_gender", "Male").lower()
            
            gender_folder = HONEY_POOL / target_gender
            pool_files = []
            if gender_folder.exists():
                pool_files = [f for f in os.listdir(gender_folder) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
            
            if pool_files:
                random_proxy = str(gender_folder / random.choice(pool_files))
            else:
                main_pool = [f for f in os.listdir(HONEY_POOL) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
                random_proxy = str(HONEY_POOL / random.choice(main_pool)) if main_pool else str(mugshot_path)
            
            honey_doc_filename = f"decoy_doc_{timestamp}.png"
            honey_doc_path = HONEY_DIR / honey_doc_filename
            generate_official_document(honey_data, random_proxy, str(honey_doc_path))
            
            # 5. Tiling (Split Updated Original Doc)
            tile_dirname = f"tiles_{timestamp}"
            tile_path = TILES_DIR / tile_dirname
            tile_path.mkdir(exist_ok=True)
            split_image_into_tiles(str(doc_path), str(tile_path))
            
            # 6. Cleanup old assets (Optional but recommended for high security)
            # (Skipping for now to avoid accidental data loss if save fails)

            # 7. Update Database
            cur.execute("""
                UPDATE criminals SET 
                    name = ?, mobile = ?, crime_type = ?, photo_path = ?, tile_dir = ?, honey_path = ?, 
                    age_gender = ?, address = ?, ps1 = ?, fir1 = ?, ps2 = ?, fir2 = ?, ps3 = ?, 
                    arrest_date = ?, case1 = ?, ps4_section = ?, case2 = ?, id_marks = ?, 
                    honey_name = ?, honey_crime_type = ?
                WHERE id = ?""",
                (
                    form_data["name"], mobile, crime_type, 
                    f"static/records/primary_vault/{doc_filename}",
                    f"static/tiles/{tile_dirname}",
                    f"static/records/decoy_vault/{honey_doc_filename}",
                    form_data["age_gender"], form_data["address"], form_data["ps1"], form_data["fir1"],
                    form_data["ps2"], form_data["fir2"], form_data["ps3"], form_data["arrest_date"],
                    form_data["case1"], form_data["ps4_section"], form_data["case2"], form_data["id_marks"],
                    honey_data["name"], honey_data["crime_type"], record_id
                )
            )
            conn.commit()
            log_event(f"admin:{session.get('admin')}", "edit_criminal", f"Comprehensive update for record {record_id} ({form_data['name']})")
            flash(f"Forensic record for {form_data['name']} has been updated and re-secured.", "success")
            return redirect(url_for("admin_records"))
            
        except Exception as e:
            conn.rollback()
            flash(f"Error during record update: {str(e)}", "error")
            return redirect(url_for("admin_edit_record", record_id=record_id))
        finally:
            conn.close()

    conn.close()
    return render_template("admin_edit_record.html", record=record, to_static_filename=to_static_filename)
@app.route("/admin/records/<int:record_id>/delete", methods=["POST"])
def admin_delete_record(record_id):
    if not require_admin():
        return redirect(url_for("login_admin"))

    try:
        conn = get_conn()
        cur = conn.cursor()
        
        # 1. Fetch info for file cleanup
        cur.execute("SELECT name, photo_path, tile_dir, honey_path FROM criminals WHERE id = ?", (record_id,))
        record = cur.fetchone()
        
        if not record:
            conn.close()
            flash("Record not found", "error")
            return redirect(url_for("admin_records"))

        # 2. Delete forensic files from hardware storage
        import shutil
        paths_to_delete = []
        if record["photo_path"]: paths_to_delete.append(BASE_DIR / record["photo_path"])
        if record["honey_path"]: paths_to_delete.append(BASE_DIR / record["honey_path"])
        
        # Delete individual files
        for p in paths_to_delete:
            if p.exists() and p.is_file():
                try: os.remove(str(p))
                except: pass
        
        # Delete tile directory
        if record["tile_dir"]:
            t_dir = BASE_DIR / record["tile_dir"]
            if t_dir.exists() and t_dir.is_dir():
                try: shutil.rmtree(str(t_dir))
                except: pass

        # 3. Delete from database (Criminal + Keys)
        cur.execute("DELETE FROM criminals WHERE id = ?", (record_id,))
        cur.execute("DELETE FROM keys WHERE record_id = ?", (record_id,))
        
        conn.commit()
        conn.close()

        log_event(f"admin:{session.get('admin')}", "delete_criminal", f"Permanently removed record ID {record_id} ({record['name']})")
        flash(f"Record for {record['name']} and all associated forensic data have been permanently deleted.", "success")
        
    except Exception as e:
        flash(f"Error during deletion: {str(e)}", "error")

    return redirect(url_for("admin_records"))


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
        return render_template("verifier_view.html", error="Please enter a forensic access key.")
    
    try:
        conn = get_conn()
        cur = conn.cursor()
        
        # Check if key exists and is valid
        cur.execute(
            "SELECT k.*, c.name, c.crime_type, c.photo_path FROM keys k LEFT JOIN criminals c ON k.record_id = c.id WHERE k.valid = 1"
        )
        all_keys = cur.fetchall()
        
        target_key_data = None
        for row in all_keys:
            if check_password_hash(row["secret_key"], key): # Phase 1: Validate Hashed Key
                target_key_data = row
                break
        
        if target_key_data:
            # Valid key - return original data
            log_event(f"verifier:{session.get('verifier')}", "key_used", f"Successfully used key for record {target_key_data['record_id']}")
            conn.close()
            # Phase 3: Decode DNA DNA DNA!
            real_name = decode_from_dna(target_key_data["name"])
            real_crime = decode_from_dna(target_key_data["crime_type"])
            
            return render_template(
                "verifier_result.html",
                record_id=target_key_data["record_id"],
                name=real_name,
                crime_type=real_crime,
                photo_path=to_static_filename(target_key_data["photo_path"]),
                download_url=url_for("download_record", record_id=target_key_data["record_id"]),
                get_indian_time=get_indian_time
            )
        else:
            # Phase 4 (True Honey): Serve Decoy Data
            # Never redirect to login, never say 'invalid key'.
            
            # 1. Try to find a real decoy record
            cur.execute("SELECT id, honey_name, honey_crime_type, honey_path FROM criminals WHERE honey_name IS NOT NULL ORDER BY RANDOM() LIMIT 1")
            decoy_record = cur.fetchone()
            conn.close()
            
            log_event(f"verifier:{session.get('verifier')}", "honey_triggered", f"Invalid key: {key[:8]}... - Served Decoy File")
            
            if decoy_record:
                # Return real database decoy
                return render_template(
                    "verifier_result.html",
                    record_id=f"H{decoy_record['id']}",
                    name=decoy_record["honey_name"],
                    crime_type=decoy_record["honey_crime_type"],
                    photo_path=to_static_filename(decoy_record["honey_path"]),
                    download_url=url_for("download_honey", record_id=decoy_record["id"]),
                    get_indian_time=get_indian_time
                )
            else:
                # 2. Emergency Fallback: If DB is fresh/empty, generate a virtual decoy
                # we don't redirect, we show a 'Virtual Decoy'
                return render_template(
                    "verifier_result.html",
                    record_id="S-00892",
                    name="Rajesh Sharma",
                    crime_type="FINANCIAL FRAUD",
                    photo_path="records/decoy_vault/placeholder_honey.png", # Simulated path
                    download_url="#",
                    get_indian_time=get_indian_time,
                    virtual_honey=True
                )
        
    except Exception as e:
        if 'conn' in locals(): conn.close()
        return render_template("verifier_view.html", error=f"Forensic Engine Error: {str(e)}")


@app.route("/download/honey/<int:record_id>")
def download_honey(record_id):
    if "verifier" not in session:
        return redirect(url_for("login_verifier"))
    
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("SELECT honey_path FROM criminals WHERE id = ?", (record_id,))
        record = cur.fetchone()
        conn.close()
        
        if record and record["honey_path"]:
            photo_path = BASE_DIR / record["honey_path"].replace("static/", "static/")
            if photo_path.exists():
                return send_file(str(photo_path), as_attachment=True, download_name=f"official_record_H{record_id}.png")
        
        flash("Secure file not found", "error")
        return redirect(url_for("verifier_view"))
            
    except Exception as e:
        flash(f"Error downloading secure file: {str(e)}", "error")
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
        
        photo_path = BASE_DIR / record["photo_path"].replace("static/", "static/")
        
        if photo_path.exists():
            # Phase 2: Decrypt encrypted file from disk into RAM (Memory)
            file_bytes = decrypt_file_to_bytes(str(photo_path))
            return send_file(io.BytesIO(file_bytes), as_attachment=True, download_name=f"official_forensic_doc_{record_id}.png")
        else:
            flash("File not found", "error")
            return redirect(url_for("verifier_view"))
            
    except Exception as e:
        flash(f"Error during secure download: {str(e)}", "error")
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
