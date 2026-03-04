# DNA Forensic & Deception System (Crime Project)

A sophisticated full-stack web application designed for secure criminal record management using **DNA-based encoding**, **image tiling**, and **honey-pot deception techniques**.

## 🚀 Project Overview
This system provides a highly secure platform for Law Enforcement Agencies to store and verify criminal records. It uses "deception technology" to mislead unauthorized users by serving them "Honey Data" (decoy information) if they attempt to access records with incorrect keys.

---

## 🛠️ Technology Stack
- **Backend:** Python (Flask)
- **Database:** SQLite3
- **Frontend:** HTML5, CSS3 (Glassmorphism & Responsive Design), Jinja2
- **Security:** DNA-based Encoding, Password Hashing (Werkzeug)
- **Image Processing:** Pillow (PIL) for tiling and obfuscation
- **Communication:** Gmail SMTP (Emails), Twilio (SMS/WhatsApp)
- **Timezone:** Asia/Kolkata (Indian Standard Time)

---

## 📂 Project Structure
```text
crime/
├── app.py                # Main Application Logic & Routes
├── .env                  # Environment Variables (Credentials)
├── database/
│   └── records.db        # SQLite Database File
├── static/
│   ├── css/style.css     # Premium UI Styling
│   ├── uploads/          # Original Criminal Photos
│   ├── tiles/            # Split Image Tiles
│   └── honey_data/       # Generated Decoy Images
├── templates/            # HTML Layouts & Views
└── utils/
    ├── dna_logic.py      # DNA Encoding Algorithms
    ├── honey_logic.py    # Decoy Image Generation
    └── image_processor.py # Image Tiling Logic
```

---

## 🔄 Project Flow (Step-by-Step)

### 1. Admin Module (Management)
- **Login:** Secure admin authentication with hashed passwords.
- **Add Record:** Admin uploads a criminal's photo and details.
  - **Tiling:** The system splits the photo into multiple "tiles" so the full image isn't stored in one piece.
  - **DNA Encoding:** Sensitive data is encoded into DNA sequences.
  - **Honey Generation:** A "decoy" (obfuscated) version of the record is created automatically.
- **Key Generation:** A unique 128-bit **Access Key (UUID)** is generated for the record.
- **Communication:** The Access Key is automatically sent to the Verifier's email address using **Gmail SMTP**.

### 2. Verifier Module (Verification)
- **Login/Registration:** Verifiers can create accounts to access the system.
- **Record Retrieval:** The verifier enters the Access Key they received.
- **The Deception Logic:**
  - **Correct Key:** The system reconstructs the data and shows the **Original Record**.
  - **Incorrect Key:** Instead of showing an error, the system serves the **Honey Data** (Decoy). This makes hackers believe they have found data, while they are actually looking at fake information.

### 3. Monitoring (Audit Logs)
- Every action (Login, Key Generation, Honey Triggered) is recorded in the **Access Logs** for security auditing.

---

## 🔒 Key Security Features
- **Honey Pots:** Active deception to mislead unauthorized access.
- **Fixed Navigation:** Premium UI with a static sidebar for efficiency.
- **Encrypted Storage:** Passwords and keys are never stored in plain text.
- **Input Validation:** Error handling for invalid file types or missing data.

---

## 🔧 Installation & Setup
1. **Clone the project** to your local machine.
2. **Install dependencies:**
   ```bash
   pip install flask pillow pytz twilio python-dotenv
   ```
3. **Configure .env:**
   Add your `GMAIL_USER` and `GMAIL_APP_PASSWORD`.
4. **Run the app:**
   ```bash
   python app.py
   ```
5. **Access:** Open `http://127.0.0.1:5000` in your browser.

---
**Project Status:** ✅ Completed & Robust
**Developer Note:** This system is built for high-security environments where data integrity and secrecy are paramount.
