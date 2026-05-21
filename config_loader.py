# config_loader.py
import os
import sys
from dotenv import load_dotenv

# Path to the .env file in the workspace root
ENV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')

# Check if .env file exists. If it doesn't, print a clear message.
if not os.path.exists(ENV_PATH):
    print("*" * 60)
    print("CRITICAL ERROR: Configuration file '.env' not found.")
    print("Please follow these steps to configure the application:")
    print("1. Copy '.env.sample' to a new file named '.env' in the project directory.")
    print("2. Open '.env' and fill in your Snipe-IT URL and API credentials.")
    print("*" * 60)
    sys.exit(1)

# Load the environment variables from the .env file
load_dotenv(ENV_PATH)

def _critical_error(field_name, message):
    print("*" * 60)
    print(f"CRITICAL CONFIGURATION ERROR: Invalid setting '{field_name}'")
    print(f"  {message}")
    print("*" * 60)
    print("\nPlease check your '.env' file and verify the configuration.")
    sys.exit(1)

def _parse_bool(val, default):
    if val is None:
        return default
    val_str = str(val).strip().lower()
    if val_str in ('true', '1', 'yes', 'on'):
        return True
    if val_str in ('false', '0', 'no', 'off'):
        return False
    return default

def _parse_float(val, name, default):
    if val is None or str(val).strip() == "":
        return default
    try:
        return float(val)
    except ValueError:
        print(f"WARNING: Configuration option '{name}' should be a number. Got '{val}'. Using default: {default}")
        return default

def _parse_int(val, name, default):
    if val is None or str(val).strip() == "":
        return default
    try:
        return int(val)
    except ValueError:
        print(f"WARNING: Configuration option '{name}' should be an integer. Got '{val}'. Using default: {default}")
        return default

# 1. Snipe-IT Base URL Validation
SNIPEIT_URL = os.getenv("SNIPEIT_URL")
if not SNIPEIT_URL or SNIPEIT_URL.strip() == "" or SNIPEIT_URL.strip() == "YOUR_SNIPEIT_URL":
    _critical_error(
        "SNIPEIT_URL",
        "The Snipe-IT URL is missing or set to the default placeholder.\n"
        "Configure 'SNIPEIT_URL' to point to your Snipe-IT instance (e.g., https://assets.example.com)."
    )

SNIPEIT_URL = SNIPEIT_URL.strip()
if not (SNIPEIT_URL.startswith("http://") or SNIPEIT_URL.startswith("https://")):
    _critical_error(
        "SNIPEIT_URL",
        f"The URL '{SNIPEIT_URL}' is invalid.\n"
        "It must begin with 'http://' or 'https://'."
    )

# 2. Snipe-IT API Token Validation
SNIPEIT_API_KEY = os.getenv("SNIPEIT_API_KEY")
if not SNIPEIT_API_KEY or SNIPEIT_API_KEY.strip() == "" or SNIPEIT_API_KEY.strip() == "YOUR_SNIPEIT_API_KEY":
    _critical_error(
        "SNIPEIT_API_KEY",
        "The API Bearer Token is missing or set to the default placeholder.\n"
        "Configure 'SNIPEIT_API_KEY' with a valid API key from Snipe-IT (Admin > API Tokens)."
    )
SNIPEIT_API_KEY = SNIPEIT_API_KEY.strip()

# 3. Debug Preferences
DEBUG_OPEN_PDF_INSTEAD_OF_PRINTING = _parse_bool(os.getenv("DEBUG_OPEN_PDF_INSTEAD_OF_PRINTING"), False)
VERBOSE_OUTPUT = _parse_bool(os.getenv("VERBOSE_OUTPUT"), False)

# 4. Printer Configuration Validation
PRINTER_NAME = os.getenv("PRINTER_NAME")
if PRINTER_NAME:
    PRINTER_NAME = PRINTER_NAME.strip()

# On Windows, if we are actually printing (not debugging by opening PDF) and a printer is set,
# we validate that Ghostscript is configured and the executable exists.
GHOSTSCRIPT_PATH = os.getenv("GHOSTSCRIPT_PATH")
if GHOSTSCRIPT_PATH:
    GHOSTSCRIPT_PATH = GHOSTSCRIPT_PATH.strip()

if os.name == 'nt' and not DEBUG_OPEN_PDF_INSTEAD_OF_PRINTING:
    if PRINTER_NAME:
        if not GHOSTSCRIPT_PATH or GHOSTSCRIPT_PATH.strip() == "":
            _critical_error(
                "GHOSTSCRIPT_PATH",
                "Ghostscript executable path is missing in '.env'.\n"
                "Ghostscript is required on Windows for direct printing to your Zebra label printer.\n"
                "Please install Ghostscript (64-bit) and set 'GHOSTSCRIPT_PATH' to point to 'gswin64c.exe'."
            )
        elif not os.path.exists(GHOSTSCRIPT_PATH):
            _critical_error(
                "GHOSTSCRIPT_PATH",
                f"The Ghostscript executable was not found at the specified path:\n"
                f"  '{GHOSTSCRIPT_PATH}'\n"
                f"Please verify that Ghostscript is installed and update the path in your '.env' file."
            )

# 5. Label Dimensions (parsed as float, default to standard dimensions if missing/invalid)
LABEL_WIDTH_CM = _parse_float(os.getenv("LABEL_WIDTH_CM"), "LABEL_WIDTH_CM", 7.0)
LABEL_HEIGHT_CM = _parse_float(os.getenv("LABEL_HEIGHT_CM"), "LABEL_HEIGHT_CM", 3.2)

# 6. Custom Field Configurations
TARGET_CUSTOM_FIELD_API_NAME = os.getenv("TARGET_CUSTOM_FIELD_API_NAME", "_snipeit_klasse_3")
TARGET_CUSTOM_FIELD_LABEL_DISPLAY_NAME = os.getenv("TARGET_CUSTOM_FIELD_LABEL_DISPLAY_NAME", "Klasse")

# 7. Scale & Offset Settings
SMALL_LABEL_SCALE_FACTOR = _parse_float(os.getenv("SMALL_LABEL_SCALE_FACTOR"), "SMALL_LABEL_SCALE_FACTOR", 0.7)

PRINT_X_OFFSET_MM_NORMAL = _parse_int(os.getenv("PRINT_X_OFFSET_MM_NORMAL"), "PRINT_X_OFFSET_MM_NORMAL", 24)
PRINT_Y_OFFSET_MM_NORMAL = _parse_int(os.getenv("PRINT_Y_OFFSET_MM_NORMAL"), "PRINT_Y_OFFSET_MM_NORMAL", 0)
PRINT_X_OFFSET_MM_SMALL = _parse_int(os.getenv("PRINT_X_OFFSET_MM_SMALL"), "PRINT_X_OFFSET_MM_SMALL", 24)
PRINT_Y_OFFSET_MM_SMALL = _parse_int(os.getenv("PRINT_Y_OFFSET_MM_SMALL"), "PRINT_Y_OFFSET_MM_SMALL", 0)
QR_CODE_DOWN_OFFSET_MM = _parse_float(os.getenv("QR_CODE_DOWN_OFFSET_MM"), "QR_CODE_DOWN_OFFSET_MM", 0.0)

