# Secure Criminal Data Management System

A high-security web application designed for criminal record management, featuring DNA-based authentication and a "Honey Encryption" decoy mechanism to protect sensitive forensic data.

## 🌟 Key Features

- **DNA-Based Authentication**: Custom DNA-style encoding for passwords and sensitive information.
- **Honey Encryption Decoy Mechanism**: Serves plausible but fake "honey" data to unauthorized users or those using incorrect keys.
- **Secure Image Processing**: Automatic image tiling and decoy image generation for enhanced security.
- **Multi-Channel Key Delivery**: Verification keys are sent to officials via SMS (Twilio) or Email (SMTP).
- **Admin Dashboard**: Comprehensive management of criminal records, access keys, and system logs.
- **Verifier Portal**: Secure portal for field officers to verify records using time-limited secret keys.

## 🛠️ Technologies Used

- **Backend**: Python 3.x, Flask (Web Framework)
- **Database**: SQLite3 (Secure relational storage)
- **Security**: 
  - `DNA-Encoding`: Custom logic for biometric-style data protection.
  - `Honey Encryption`: Psychologically-driven deception mechanism.
  - `PBKDF2`: Password hashing with salt.
- **Image Processing**: Pillow (PIL) for image tiling and processing.
- **Communication**: 
  - Twilio API: For secure SMS key delivery.
  - SMTPLIB: For secure Email notifications.
- **Frontend**: HTML5, Vanilla CSS3 (Premium Dark-themed UI).

## 📂 Project Structure

```text
crime/
├── crime/
│   ├── app.py              # Main Flask application & route definitions
│   ├── database/           # Database storage directory
│   │   └── records.db      # SQLite database file
│   ├── static/             # Static assets folder
│   │   ├── css/            # UI stylesheets
│   │   ├── honey_data/     # Decoy/Honey data storage
│   │   ├── images/         # System static images
│   │   ├── tiles/          # Processed image fragments (tiles)
│   │   └── uploads/        # Original criminal record photos
│   ├── templates/          # HTML templates for the UI
│   ├── utils/              # Internal logic and security modules
│   │   ├── dna_logic.py    # DNA encoding/decoding utilities
│   │   ├── honey_logic.py  # Honey data generation logic
│   │   └── image_processor.py # Image tiling and fragment management
│   └── origional data/     # Source assets for processing
├── requirements.txt        # Python dependencies
└── README.md               # Project documentation
```

## 🚀 How to Run

### 1. Prerequisites
Ensure you have Python 3.8+ installed on your system.

### 2. Environment Setup
Create a virtual environment (optional but recommended):
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### 3. Install Dependencies
Install the required Python packages:
```bash
pip install Flask==2.3.3 Pillow==10.0.1 Werkzeug==2.3.7 twilio pytz
```

### 4. Configuration
Open `crime/app.py` and configure the following:
- **Twilio Credentials**: `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_PHONE_NUMBER`.
- **Email Credentials**: `sender_email`, `sender_password` in the `send_email_key` function.
- **Secret Key**: Update `app.config["SECRET_KEY"]` for production.

### 5. Running the Application
Start the development server:
```bash
python crime/app.py
```
The application will be accessible at [http://127.0.0.1:5000](http://127.0.0.1:5000).

## 🛡️ Security Workflow

1. **Admin** adds a criminal record and uploads a photo.
2. The system **encodes** metadata using DNA logic and **tiles** the image.
3. A **secret key** is generated and sent to the Verifier's phone/email.
4. **Verifier** enters the key in the system:
   - **Correct Key**: Official record is reconstructed and displayed.
   - **Incorrect Key**: The system serves "Honey Data" (fake but realistic records) to mislead the intruder.

## 📝 License
Proprietary / Research Project for Final Year.



venv\Scripts\activate 
python -m venv venv 
venv\Scripts\activate
 pip install -r requirements.txt 
 python app.py




 📦 Example 2: Narcotics & Organized Crime
Use this for a standard "Narcotics" enforcement record.

FULL LEGAL NAME: Sameer Z. Mansoori
AGE / GENDER: 42 / Male
RESIDENTIAL ADDRESS: Flat 901, Royal Residency, Bandra West, Mumbai, MH - 400050
PRIMARY P.S.: Narcotics Control Bureau (Zonal Unit)
PRIMARY FIR NO.: FIR/NCB/BOM/0091-24
SECONDARY P.S.: Santacruz East P.S.
SECONDARY FIR NO.: FIR/SCE/2022/1004
ARREST DATE: 05/01/2024
CRIME CLASSIFICATION: NDPS POSSESSION & TRAFFICKING
CASE NO. 01: SPL/NDPS/2024/12
IPC SECTIONS: Sec 8(C), 21(C), 29 NDPS Act
VERIFIER EMAIL: 

mumbai_ops@narcotics_dept.org
BIOMETRIC PHOTO: (Upload the 

static/sample_mugshot.png
 file)
📄 Example 3: Identity Theft & Forgery
Use this for a sophisticated "White Collar" crime record.

FULL LEGAL NAME: Ananya R. Deshmukh
AGE / GENDER: 28 / Female
RESIDENTIAL ADDRESS: Plot No. 15, Green Park Estate, Sector 12, Pune, MH - 411001
PRIMARY P.S.: Crime Branch (Economic Offences Wing)
PRIMARY FIR NO.: FIR/EOW-P/2024/015
SECONDARY P.S.: Shivaji Nagar P.S.
SECONDARY FIR NO.: FIR/SN/0045-23
ARREST DATE: 22/02/2024
CRIME CLASSIFICATION: CORPORATE IDENTITY THEFT & FORGERY
CASE NO. 01: MS/C-CR/PUNE/24
IPC SECTIONS: 419, 467, 471, 120-B
VERIFIER EMAIL: 

eow_inspector@pune_police.gov
BIOMETRIC PHOTO: (Upload the 

static/sample_mugshot.png
 file)

 📋 Forensic Sample Data (Copy-Paste Ready)
🏢 Case 01: The "Digital Ghost" (Cyber Extraction)
FULL LEGAL NAME: Ishaan V. Malhotra
AGE / GENDER: 29 / Male
RESIDENTIAL ADDRESS: H-Block, Crystal Towers, Sector 44, Gurgaon, HR - 122003
IDENTIFICATION MARKS: Surgical scar on left wrist, "A" tattoo on neck.
PRIMARY P.S.: Cyber Crime Cell (Nodal Unit)
PRIMARY FIR NO.: FIR/CYB-G/2024/0088
SECONDARY P.S.: Sushant Lok - 1 P.S.
SECONDARY FIR NO.: FIR/SL/2023/1045
ARREST DATE: 12/01/2024
CRIME CLASSIFICATION: RANSOMWARE EXFILTRATION
ARCHIVE P.S.: State Data Repository
CASE NO. 01: SPC/CR/2024-991
IPC SECTIONS: 420, 468, 66C IT Act, 66D IT Act
CASE NO. 02: ND/CASE/REF/101
VERIFIER EMAIL: 

cyber_node@haryana_police.gov
🏛️ Case 02: "Blue Collar Forgery" (Document Fraud)
FULL LEGAL NAME: Sanya R. Chatterjee
AGE / GENDER: 34 / Female
RESIDENTIAL ADDRESS: Flat 202, Alipore Heights, Kolkata, WB - 700027
IDENTIFICATION MARKS: Birthmark on right cheek, Piercing on left eyebrow.
PRIMARY P.S.: EOW (Economic Offences Wing)
PRIMARY FIR NO.: FIR/EOW-K/2024/015
SECONDARY P.S.: Park Street P.S.
SECONDARY FIR NO.: FIR/PS/0045-23
ARREST DATE: 22/02/2024
CRIME CLASSIFICATION: CORPORATE IDENTITY THEFT & FORGERY
ARCHIVE P.S.: Bengal Crime Bureau
CASE NO. 01: MS/C-CR/PUNE/24
IPC SECTIONS: 419, 467, 471, 120-B
CASE NO. 02: WB/SEC/DOC/202
VERIFIER EMAIL: 

eow_inspector@wb_police.gov
💊 Case 03: "The Vault-Breaker" (Financial Laundering)
FULL LEGAL NAME: Rahul Z. Siddiqui
AGE / GENDER: 45 / Male
RESIDENTIAL ADDRESS: Plot 9, Galaxy Apartment, Bandra West, Mumbai - 400050
IDENTIFICATION MARKS: Missing tip of index finger (Left), Tribal tattoo on right forearm.
PRIMARY P.S.: Anti-Money Laundering Unit
PRIMARY FIR NO.: FIR/ED/MUM/091
SECONDARY P.S.: Santacruz West P.S.
SECONDARY FIR NO.: FIR/SCW/2022/1004
ARREST DATE: 05/01/2024
CRIME CLASSIFICATION: PMLA VIOLATION & MONEY LAUNDERING
ARCHIVE P.S.: Central Intelligence Hub
CASE NO. 01: SPL/PMLA/2024/12
IPC SECTIONS: Sec 3, 4 PMLA Act, 420 IPC
CASE NO. 02: MAHA/FIN/2024/C-01
VERIFIER EMAIL: 

fin_ops@mumbai_police.org
🛰️ Case 04: "System Overdrive" (Advanced Phishing)
FULL LEGAL NAME: Kavita N. Sharma
AGE / GENDER: 27 / Female
RESIDENTIAL ADDRESS: House No. 12, Indiranagar 2nd Stage, Bangalore - 560038
IDENTIFICATION MARKS: Small mole near left eye, Star tattoo on right wrist.
PRIMARY P.S.: IT Corridor Cyber Cell
PRIMARY FIR NO.: FIR/BLR-C/2024/512
SECONDARY P.S.: HAL Police Station
SECONDARY FIR NO.: FIR/HAL/0122/2023
ARREST DATE: 15/03/2024
CRIME CLASSIFICATION: CRYPTO-ASSET MISAPPROPRIATION
ARCHIVE P.S.: Regional Forensic Lab
CASE NO. 01: KA/CYB/CR-590/24
IPC SECTIONS: 406, 420, 66 IT ACT
CASE NO. 02: KA/ND/CASE/99
VERIFIER EMAIL: 

it_inspector@karnataka_police.gov
🧪 Case 05: "The Architect" (Criminal Logistics)
FULL LEGAL NAME: Arvind K. Deshpande
AGE / GENDER: 51 / Male
RESIDENTIAL ADDRESS: Shivajinagar Cooperative Society, Pune - 411005
IDENTIFICATION MARKS: Extensive burn scar on left shoulder, Gray beard.
PRIMARY P.S.: CID (Special Ops)
PRIMARY FIR NO.: FIR/CID-P/2024/002
SECONDARY P.S.: Deccan Gymkhana P.S.
SECONDARY FIR NO.: FIR/DG/2021/404
ARREST DATE: 01/02/2024
CRIME CLASSIFICATION: CRIMINAL CONSPIRACY & ASSET HIDEOUT
ARCHIVE P.S.: National Archive Center
CASE NO. 01: MS/SPEC-CR/24/01
IPC SECTIONS: 120B, 212, 216 IPC
CASE NO. 02: ND/LOG/CASE/B-4
VERIFIER EMAIL: cid_desk@pune_police.gov


Flask==2.3.3
Pillow==10.0.1
Werkzeug==2.3.7
twilio==8.5.0