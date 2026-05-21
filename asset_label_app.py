# asset_label_app.py
import requests
import json
import sys
import os
import tempfile
import subprocess

# Import from our modules
from qr_generator import generate_qr_code_image
from label_generator import create_label_pdf

# For Windows printing, win32print is only imported if on Windows
if os.name == 'nt':
    try:
        import win32print
        import win32api
    except ImportError:
        pass

try:
    import config_loader
except ImportError:
    print("CRITICAL ERROR: config_loader.py not found. Please ensure it is in the same directory.")
    sys.exit(1)

# --- Helper Functions for Console Output ---
def _print_verbose(message):
    """Prints a message if VERBOSE_OUTPUT is True in config."""
    if config_loader.VERBOSE_OUTPUT:
        print(f"VERBOSE: {message}")

def _print_error(message, details=""):
    """Prints a structured, clear error message."""
    print(f"ERROR: {message}{' - ' + details if details else ''}")

def _print_warning(message):
    """Prints a warning message."""
    print(f"WARNING: {message}")

def _print_status(message):
    """Prints a status message (always prints)."""
    print(message)

def verify_printer_exists(printer_name):
    """
    Checks if the configured printer exists in the Windows system printer list.
    Only applicable on Windows.
    """
    if os.name != 'nt':
        return True
    try:
        printers_info = win32print.EnumPrinters(win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS)
        printers = [p[2] for p in printers_info]
        if printer_name not in printers:
            print("*" * 60)
            print(f"CRITICAL ERROR: The configured printer '{printer_name}' was not found.")
            print("Available printers on this system are:")
            for p in sorted(printers):
                print(f"  - {p}")
            print("\nPlease check your printer's connection or update 'PRINTER_NAME' in '.env'.")
            print("*" * 60)
            return False
        return True
    except Exception as e:
        _print_warning(f"Could not query system printers to verify '{printer_name}'. Detail: {e}")
        return True  # Proceed anyway to avoid blocking unnecessarily

def _parse_snipeit_api_response(response_data, identifier_for_logging):
    """
    Parses the JSON response data from the Snipe-IT API.

    Args:
        response_data (dict or list): The JSON data from the API response.
        identifier_for_logging (str): The identifier (serial or ID) used in the API request, for logging.

    Returns:
        dict: A dictionary containing the asset data if found and valid, None otherwise.
    """
    if isinstance(response_data, dict) and 'total' in response_data and 'rows' in response_data:
        if response_data['total'] == 1:
            return response_data['rows'][0]
        elif response_data['total'] > 1:
            _print_warning(f"Multiple assets found for {identifier_for_logging}. Returning the first.")
            return response_data['rows'][0]
        elif response_data['total'] == 0:
            _print_status(f"Asset with {identifier_for_logging} not found (API returned total: 0).")
            return None
        else:
            _print_error(f"Unexpected 'total' count: {response_data['total']} in response.", f"Snippet: {str(response_data)[:200]}...")
            return None
    elif isinstance(response_data, dict) and 'id' in response_data:  # Direct asset object
        return response_data
    else:
        _print_error(f"Unexpected response format from Snipe-IT API for {identifier_for_logging}.", f"Snippet: {str(response_data)[:200]}...")
        return None

def _query_snipeit_api(api_url, identifier_label):
    """
    Common helper to query the Snipe-IT API and handle HTTP/network errors.
    """
    headers = {
        "Authorization": f"Bearer {config_loader.SNIPEIT_API_KEY}",
        "Accept": "application/json",
        "Content-Type": "application/json"
    }

    try:
        _print_verbose(f"Querying API: {api_url}")
        response = requests.get(api_url, headers=headers, timeout=15)
        response.raise_for_status()
        
        asset_data_raw = response.json()
        return _parse_snipeit_api_response(asset_data_raw, identifier_label)

    except requests.exceptions.HTTPError as errh:
        status_code = response.status_code
        if status_code == 401:
            _print_error(
                "Authentication Failed (401 Unauthorized)",
                "The SNIPEIT_API_KEY in your .env file is invalid or has expired. Please verify your token."
            )
        elif status_code == 403:
            _print_error(
                "Access Forbidden (403 Forbidden)",
                "You do not have permission to access this asset or API endpoint. Check your Snipe-IT account permissions."
            )
        elif status_code == 404:
            _print_status(f"Asset with {identifier_label} was not found (404).")
        elif status_code >= 500:
            _print_error(
                f"Server Error ({status_code})",
                "The Snipe-IT server encountered an internal error. Please try again later or contact the server administrator."
            )
        else:
            _print_error(f"HTTP Error ({status_code})", str(errh))
            try:
                error_details = response.json()
                messages = error_details.get('messages', error_details.get('message', ''))
                if messages:
                    _print_error(f"Snipe-IT message details: {messages}")
            except (json.JSONDecodeError, ValueError):
                pass
        return None

    except requests.exceptions.ConnectionError:
        _print_error(
            "Network Connection Failed",
            f"Could not connect to Snipe-IT at '{config_loader.SNIPEIT_URL}'.\n"
            f"Please verify your SNIPEIT_URL in '.env', check your internet connection, or verify the server status."
        )
        return None

    except requests.exceptions.Timeout:
        _print_error(
            "Request Timeout",
            "The request to Snipe-IT timed out. The server might be busy or slow to respond."
        )
        return None

    except requests.exceptions.RequestException as err:
        _print_error("Unexpected network error occurred during API request", str(err))
        return None

    except json.JSONDecodeError:
        _print_error(
            "Invalid Response Format",
            f"Could not decode the response from Snipe-IT as JSON.\n"
            f"Status code: {response.status_code}. Response snippet: {response.text[:200]}"
        )
        return None

def get_asset_by_serial(serial_number):
    """Fetches and parses asset details from Snipe-IT API by serial number."""
    base_url = config_loader.SNIPEIT_URL.rstrip('/')
    api_url = f"{base_url}/api/v1/hardware/byserial/{serial_number}"
    return _query_snipeit_api(api_url, f"serial number '{serial_number}'")

def get_asset_by_id(asset_id):
    """Fetches and parses asset details from Snipe-IT API by asset ID."""
    base_url = config_loader.SNIPEIT_URL.rstrip('/')
    api_url = f"{base_url}/api/v1/hardware/{asset_id}"
    return _query_snipeit_api(api_url, f"asset ID '{asset_id}'")

def get_custom_field_value(asset_details, target_display_name):
    """
    Extracts the value of a specific custom field from asset details
    by its display name.
    """
    if 'custom_fields' in asset_details and asset_details['custom_fields'] and isinstance(asset_details['custom_fields'], dict):
        for internal_key, field_data in asset_details['custom_fields'].items():
            if isinstance(field_data, dict) and 'field' in field_data:
                current_display_name = field_data.get('field')
                if current_display_name == target_display_name:
                    return field_data.get('value')
    elif 'custom_fields' not in asset_details or not asset_details['custom_fields']:
        _print_verbose(f"No 'custom_fields' data in asset_details or it's empty when searching for '{target_display_name}'.")
    
    return None

def _open_file_os_agnostic(filepath):
    """Opens a file using the default OS application."""
    try:
        if os.name == 'nt':  # Windows
            os.startfile(filepath)
        elif sys.platform == 'darwin':  # macOS
            subprocess.run(['open', filepath], check=True)
        else:  # Linux and other POSIX
            subprocess.run(['xdg-open', filepath], check=True)
        _print_status(f"Opened PDF for review: {filepath}")
    except Exception as e:
        _print_error(f"Could not automatically open PDF: {filepath}", str(e))

def print_pdf_windows(pdf_path, printer_name):
    """Sends a PDF file to the specified printer on Windows using Ghostscript."""
    if os.name != 'nt':
        _print_warning("Direct printing via Ghostscript is currently only supported on Windows.")
        _print_status(f"Your PDF is saved at: {pdf_path}")
        return False

    gs_path = config_loader.GHOSTSCRIPT_PATH
    if not gs_path or not os.path.exists(gs_path):
        _print_error(
            "Ghostscript path not configured or file not found",
            f"Path: '{gs_path if gs_path else 'Not Set'}'. Please install Ghostscript and set GHOSTSCRIPT_PATH in your .env file."
        )
        return False

    _print_verbose(f"Attempting to print PDF '{pdf_path}' to printer '{printer_name}' using Ghostscript: {gs_path}")

    gs_command = [
        gs_path,
        "-dNOPAUSE",
        "-dBATCH",
        "-sDEVICE=mswinpr2",
        f"-sOutputFile=%printer%{printer_name}",
        "-dPrinted",
        "-q", 
        pdf_path 
    ]
    
    try:
        _print_verbose(f"Executing Ghostscript command: {' '.join(gs_command)}")
        _print_status(f"Sending PDF to printer '{printer_name}'...")

        process = subprocess.run(gs_command, capture_output=True, text=True, check=False)

        if process.returncode == 0:
            _print_verbose(f"Ghostscript printing command executed successfully for {pdf_path} to {printer_name}.")
            return True
        else:
            _print_error(f"Printing PDF with Ghostscript failed. Return code: {process.returncode}")
            if process.stdout:
                _print_verbose(f"Ghostscript stdout:\n{process.stdout}")
            if process.stderr:
                _print_verbose(f"Ghostscript stderr:\n{process.stderr}")
            _print_status("  Printing failed. Check printer status and Ghostscript configuration.")
            return False

    except Exception as e:
        _print_error(f"An unexpected error occurred during Ghostscript printing process: {e}")
        _print_status(f"  The generated PDF is available for manual printing at: {pdf_path}")
        return False

def _process_asset_label_request(identifier, input_type='serial', scale_factor=1.0, selected_x_offset_mm=0, selected_y_offset_mm=0):
    """Handles the complete process for a single asset identifier (serial or ID)."""
    asset_details = None
    if input_type == 'serial':
        _print_status(f"\nProcessing serial: {identifier}...")
        asset_details = get_asset_by_serial(identifier)
    elif input_type == 'id':
        _print_status(f"\nProcessing asset ID: {identifier}...")
        asset_details = get_asset_by_id(identifier)
    else:
        _print_error(f"Invalid input_type '{input_type}' for _process_asset_label_request.")
        return

    if not asset_details:
        return

    _print_status("\n--- Asset Details Found ---")
    _print_status(f"  ID: {asset_details.get('id')}")
    _print_status(f"  Asset Tag: {asset_details.get('asset_tag')}")
    _print_status(f"  Name: {asset_details.get('name')}")
    _print_status(f"  Serial: {asset_details.get('serial')}")
    
    model_info = asset_details.get('model', {})
    _print_status(f"  Model: {model_info.get('name', 'N/A')}")
    
    status_label_info = asset_details.get('status_label', {})
    _print_status(f"  Status: {status_label_info.get('name', 'N/A')}")

    # Check if custom "Owner" field is set and use it instead of Asset Name in the printout
    owner_value = None
    custom_fields = asset_details.get('custom_fields')
    if custom_fields and isinstance(custom_fields, dict):
        # 1. Search by display name "Owner"
        for key, field_data in custom_fields.items():
            if key.strip().lower() == 'owner':
                if isinstance(field_data, dict):
                    val = field_data.get('value')
                    if val is not None and str(val).strip():
                        owner_value = str(val).strip()
                        break
        # 2. Search by internal field name starting with '_snipeit_owner_' or equal to '_snipeit_owner_8'
        if not owner_value:
            for key, field_data in custom_fields.items():
                if isinstance(field_data, dict):
                    field_name = field_data.get('field', '')
                    if field_name.startswith('_snipeit_owner_') or field_name == '_snipeit_owner_8':
                        val = field_data.get('value')
                        if val is not None and str(val).strip():
                            owner_value = str(val).strip()
                            break

    if owner_value:
        _print_status(f"  Owner: {owner_value}")
        _print_status(f"  -> Using Owner instead of Asset Name in the printout.")
        asset_details['name'] = owner_value

    target_custom_field_value = get_custom_field_value(asset_details, config_loader.TARGET_CUSTOM_FIELD_API_NAME)
    
    if target_custom_field_value is not None:
        _print_status("\n========================================")
        _print_status(f"  {config_loader.TARGET_CUSTOM_FIELD_LABEL_DISPLAY_NAME.upper()}: {target_custom_field_value}")
        _print_status("========================================\n")
    else:
        _print_verbose(f"Custom field '{config_loader.TARGET_CUSTOM_FIELD_API_NAME}' not found or empty.")
        _print_status(f"Value for '{config_loader.TARGET_CUSTOM_FIELD_LABEL_DISPLAY_NAME}' not found or is empty for this asset.\n")

    asset_id = asset_details.get('id')
    if not asset_id:
        _print_error("Asset ID not found in details, cannot generate label URL.")
        return

    asset_url = f"{config_loader.SNIPEIT_URL.rstrip('/')}/hardware/{asset_id}"
    qr_image_filename = ""
    pdf_label_filename = ""

    try:
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_qr_file_obj, \
             tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_pdf_file_obj:
            qr_image_filename = tmp_qr_file_obj.name
            pdf_label_filename = tmp_pdf_file_obj.name

        _print_verbose(f"Generating QR code for: {asset_url}")
        generate_qr_code_image(asset_url, qr_image_filename)
        _print_verbose(f"QR code generated successfully at: {qr_image_filename}")

        _print_verbose(f"Generating PDF label at: {pdf_label_filename}")
        create_label_pdf(
            asset_details,
            qr_image_filename,
            pdf_label_filename,
            config_loader.TARGET_CUSTOM_FIELD_LABEL_DISPLAY_NAME,
            target_custom_field_value,
            scale_factor,
            selected_x_offset_mm,
            selected_y_offset_mm,
            label_width_cm=config_loader.LABEL_WIDTH_CM,
            label_height_cm=config_loader.LABEL_HEIGHT_CM,
            qr_code_down_offset_mm=config_loader.QR_CODE_DOWN_OFFSET_MM,
            verbose_output=config_loader.VERBOSE_OUTPUT
        )

        print_attempted = False
        print_successful = False
        pdf_opened_for_review = False

        if config_loader.DEBUG_OPEN_PDF_INSTEAD_OF_PRINTING:
            _print_status(f"DEBUG mode: Opening PDF {pdf_label_filename} for review instead of printing.")
            _open_file_os_agnostic(pdf_label_filename)
            pdf_opened_for_review = True
        elif config_loader.PRINTER_NAME:
            print_attempted = True
            print_successful = print_pdf_windows(pdf_label_filename, config_loader.PRINTER_NAME)
            if print_successful:
                _print_status(f"Label successfully sent to printer: {config_loader.PRINTER_NAME}")
        else:
            _print_warning("Printer name not configured in '.env' and direct printing disabled.")
            _print_status(f"Opening PDF for manual printing/review: {pdf_label_filename}")
            _open_file_os_agnostic(pdf_label_filename)
            pdf_opened_for_review = True

        if pdf_opened_for_review:
            _print_verbose(f"Label PDF (opened for review or saved) is at: {pdf_label_filename}")
        elif print_attempted:
            if not print_successful:
                _print_error(f"Printing failed. Label PDF is available at: {pdf_label_filename}")
            elif config_loader.VERBOSE_OUTPUT:
                _print_verbose(f"Label PDF (successfully printed) is at: {pdf_label_filename}")

    except Exception as e:
        _print_error(f"An unexpected error occurred during label generation or printing for '{identifier}'", str(e))
        if pdf_label_filename and os.path.exists(pdf_label_filename):
             _print_status(f"  A PDF might have been partially generated at: {pdf_label_filename}")
    finally:
        if qr_image_filename and os.path.exists(qr_image_filename):
            try:
                os.remove(qr_image_filename)
                _print_verbose(f"Temporary QR image file removed: {qr_image_filename}")
            except OSError as e_os:
                _print_warning(f"Could not remove temporary QR image file {qr_image_filename}: {e_os}")
        
        delete_pdf = False
        if print_attempted and print_successful and not config_loader.DEBUG_OPEN_PDF_INSTEAD_OF_PRINTING:
            delete_pdf = True
        
        if delete_pdf and pdf_label_filename and os.path.exists(pdf_label_filename):
            try:
                os.remove(pdf_label_filename)
                _print_verbose(f"Temporary PDF label file removed: {pdf_label_filename}")
            except OSError as e_os:
                _print_warning(f"Could not remove temporary PDF label file {pdf_label_filename}: {e_os}")

def main():
    """Main application function."""
    _print_status("Welcome to the Snipe-IT Asset Label App!")
    _print_status("----------------------------------------")
    
    if not config_loader.TARGET_CUSTOM_FIELD_API_NAME:
        _print_warning("TARGET_CUSTOM_FIELD_API_NAME is not set in '.env'. Custom field will not be fetched.")
    
    # Check system printers on Windows if direct printing is enabled
    if os.name == 'nt' and not config_loader.DEBUG_OPEN_PDF_INSTEAD_OF_PRINTING:
        if config_loader.PRINTER_NAME:
            if not verify_printer_exists(config_loader.PRINTER_NAME):
                sys.exit(1)
        else:
            _print_warning("No 'PRINTER_NAME' configured in '.env'. Generated PDFs will open in your default viewer.")

    # --- Get Label Size Preference ONCE at the beginning ---
    scale_factor = 1.0
    selected_x_offset_mm = config_loader.PRINT_X_OFFSET_MM_NORMAL
    selected_y_offset_mm = config_loader.PRINT_Y_OFFSET_MM_NORMAL

    small_scale_factor_from_config = config_loader.SMALL_LABEL_SCALE_FACTOR
    small_label_percentage = int(small_scale_factor_from_config * 100)
    size_prompt = f"Choose default label size for this session (N=Normal, S=Small {small_label_percentage}%): "

    while True:
        try:
            size_input = input(size_prompt).strip().upper()
            if size_input == 'N':
                scale_factor = 1.0
                selected_x_offset_mm = config_loader.PRINT_X_OFFSET_MM_NORMAL
                selected_y_offset_mm = config_loader.PRINT_Y_OFFSET_MM_NORMAL
                _print_status("Selected Normal size (100%) for this session.")
                break
            elif size_input == 'S':
                scale_factor = small_scale_factor_from_config
                selected_x_offset_mm = config_loader.PRINT_X_OFFSET_MM_SMALL
                selected_y_offset_mm = config_loader.PRINT_Y_OFFSET_MM_SMALL
                _print_status(f"Selected Small size ({small_label_percentage}%) for this session.")
                break
            else:
                _print_warning("Invalid input. Please enter 'N' for Normal or 'S' for Small.")
        except KeyboardInterrupt:
            _print_status("\nExiting application.")
            sys.exit(0)

    _print_status("\nReady to process assets. Enter a serial number to generate a label.")
    _print_status("Type 'exit', 'quit', or 'cancel' (and press Enter) to end the program.\n")
    _print_status(f"You can also enter a full asset URL like: {config_loader.SNIPEIT_URL.rstrip('/')}/hardware/ASSET_ID\n")

    while True:
        try:
            user_input = input("Enter serial number or asset URL (or type 'exit' to quit): ").strip()

            if user_input.lower() in ['exit', 'quit', 'cancel']:
                _print_status("Exiting application.")
                break

            if not user_input:
                _print_warning("No serial number entered. Please try again or type 'exit' to quit.")
                continue

            # Check if input is a URL for the configured Snipe-IT instance
            normalized_snipeit_url = config_loader.SNIPEIT_URL.rstrip('/')
            asset_url_prefix = f"{normalized_snipeit_url}/hardware/"

            if user_input.lower().startswith(asset_url_prefix.lower()):
                _print_verbose(f"Input detected as a URL: {user_input}")
                path_part = user_input[len(asset_url_prefix):]
                asset_id_str = path_part.split('/')[0]
                
                if asset_id_str.isdigit():
                    _process_asset_label_request(
                        asset_id_str,
                        input_type='id',
                        scale_factor=scale_factor,
                        selected_x_offset_mm=selected_x_offset_mm,
                        selected_y_offset_mm=selected_y_offset_mm
                    )
                else:
                    _print_error(
                        f"Could not extract a valid numeric Asset ID from URL: {user_input}",
                        f"Expected format: {asset_url_prefix}ASSET_ID"
                    )
            else:
                # Assume it's a serial number
                _process_asset_label_request(
                    user_input,
                    input_type='serial',
                    scale_factor=scale_factor,
                    selected_x_offset_mm=selected_x_offset_mm,
                    selected_y_offset_mm=selected_y_offset_mm
                )
        
        except KeyboardInterrupt:
            _print_status("\nProcess interrupted by user. Exiting application.")
            break
        except Exception as e:
            _print_error(f"An unexpected error occurred in the main loop: {e}", "Continuing...")
        finally:
            _print_status("\n----------------------------------------")

if __name__ == "__main__":
    main()
