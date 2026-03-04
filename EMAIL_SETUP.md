# Email Configuration Setup

## Steps to Enable Email Sending:

### 1. Generate Gmail App Password
1. Go to your Google Account: https://myaccount.google.com/
2. Navigate to Security → 2-Step Verification (enable if not already)
3. Go to Security → App passwords
4. Select "Mail" and "Windows Computer"
5. Click "Generate" and copy the 16-character password

### 2. Set Environment Variables

**Option A: Windows Command Prompt (Temporary)**
```cmd
set GMAIL_USER=your-email@gmail.com
set GMAIL_APP_PASSWORD=your-16-char-app-password
python app.py
```

**Option B: Windows PowerShell (Temporary)**
```powershell
$env:GMAIL_USER="your-email@gmail.com"
$env:GMAIL_APP_PASSWORD="your-16-char-app-password"
python app.py
```

**Option C: Edit app.py directly (Line 28-29)**
Replace:
```python
GMAIL_USER = os.environ.get('GMAIL_USER', 'your-email@gmail.com')
GMAIL_APP_PASSWORD = os.environ.get('GMAIL_APP_PASSWORD', 'your-app-password')
```

With:
```python
GMAIL_USER = 'your-actual-email@gmail.com'
GMAIL_APP_PASSWORD = 'your-actual-app-password'
```

### 3. Restart the Flask App
After setting credentials, restart your Flask application.

## Testing
Send a test key from the admin panel to verify email delivery.
