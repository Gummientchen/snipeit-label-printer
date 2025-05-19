# config.py

SNIPEIT_URL = "YOURSNIPEITURL"  # Replace with your Snipe-IT instance URL (e.g., "https://assets.example.com")
SNIPEIT_API_KEY = "YOURSNIPEITKEY"  # Replace with your Snipe-IT API Bearer Token

# Label dimensions in centimeters
LABEL_WIDTH_CM = 7.62
LABEL_HEIGHT_CM = 5.08

# Name of the printer as it appears in your system's printer list
PRINTER_NAME = "ZDesigner ZD420-300dpi ZPL"

# The internal/API name of the custom field to fetch from Snipe-IT
# (e.g., "_snipeit_klasse_3", "_snipeit_department_5")
TARGET_CUSTOM_FIELD_API_NAME = "_snipeit_klasse_3"
TARGET_CUSTOM_FIELD_LABEL_DISPLAY_NAME = "Klasse" # The name you want to see on the label

# Optional: Set to True to attempt to automatically open the PDF for review instead of printing.
# Set to False to attempt direct printing.
DEBUG_OPEN_PDF_INSTEAD_OF_PRINTING = False # Set to True for testing PDF layout

# --- Ghostscript Configuration (if using Ghostscript for printing) ---
GHOSTSCRIPT_PATH = r"C:\Program Files\gs\gs10.05.1\bin\gswin64c.exe" # CHANGE THIS to your actual Ghostscript executable path

# --- Print Offset Adjustments (in millimeters) ---
# These offsets adjust the position of the *entire* label content on the physical label.
# You may need different offsets for different label sizes or printers.
# Positive X shifts content to the RIGHT. Positive Y shifts content UP.

PRINT_X_OFFSET_MM_NORMAL = 21  # X offset for Normal size (100%) labels
PRINT_Y_OFFSET_MM_NORMAL = 0   # Y offset for Normal size (100%) labels
PRINT_X_OFFSET_MM_SMALL = 21    # X offset for Small size (50%) labels. Adjust this if cut off on the left.
PRINT_Y_OFFSET_MM_SMALL = 0    # Y offset for Small size (50%) labels. Adjust as needed.

# --- Label Size Scaling ---
SMALL_LABEL_SCALE_FACTOR = 0.7 # The scale factor (e.g., 0.5 for 50%) to apply when 'Small' size is selected.

# --- General Debugging ---
VERBOSE_OUTPUT = False # Set to True for more detailed console output, False for quieter operation