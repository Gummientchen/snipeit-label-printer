# c:\Users\sbl\Documents\GitHub\snipeit-label-api\asset_label_app.py
import requests
import json
import sys # For sys.exit
import os
import tempfile
import subprocess # For calling Ghostscript
# import time # For adding a delay - Not currently used, can be removed or kept for future use

# Import from our new modules
from qr_generator import generate_qr_code_image
from label_generator import create_label_pdf

# For Printing (Windows specific)
# These imports (win32print, win32api) are not directly used by the Ghostscript method.
# They would be needed if you were using win32print API directly.
# Keeping them for now in case of future changes, but they are not strictly necessary
# for the current Ghostscript-based printing.
if os.name == 'nt':
    import win32print
    import win32api

try:
    import config
except ImportError:
    print("CRITICAL ERROR: config.py not found. Please create it with your SNIPEIT_URL and SNIPEIT_API_KEY.")
    sys.exit(1)

# --- Helper Functions for Console Output ---
def _print_verbose(message):
    """Prints a message if VERBOSE_OUTPUT is True in config."""
    if hasattr(config, 'VERBOSE_OUTPUT') and config.VERBOSE_OUTPUT:
        print(f"VERBOSE: {message}")

def _print_error(message, details=""):
    """Prints an error message."""
    print(f"ERROR: {message}{' - ' + details if details else ''}")

def _print_warning(message):
    """Prints a warning message."""
    print(f"WARNING: {message}")

def _print_status(message):
    """Prints a status message (always prints)."""
    print(message)


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
            _print_warning(f"Multiple assets found for '{identifier_for_logging}'. This endpoint should ideally return one. Returning the first.")
            return response_data['rows'][0]
        elif response_data['total'] == 0:
            # This case is handled by the caller (get_asset_by_serial) if 404,
            # but good to have if API changes to return 200 with total:0
            _print_status(f"Asset with '{identifier_for_logging}' not found (API returned total: 0).")
            return None
        else:
            _print_error(f"Unexpected 'total' count: {response_data['total']} in wrapped response.", f"Full response (first 500 chars): {str(response_data)[:500]}...")
            return None
    # Some API endpoints might return a direct asset object if queried by ID, not by serial.
    # The /hardware/{id} endpoint returns the direct asset object.
    # Keeping this for robustness in case API behavior varies or for other potential API calls.
    elif isinstance(response_data, dict) and 'id' in response_data: # Direct asset object
        return response_data
    else:
        _print_error(f"Unexpected response format from Snipe-IT API for '{identifier_for_logging}'.", f"Type: {type(response_data)}, Content (first 500 chars): {str(response_data)[:500]}...")
        return None

def get_asset_by_serial(serial_number):
    """Fetches and parses asset details from Snipe-IT API by serial number."""
    if not hasattr(config, 'SNIPEIT_URL') or not config.SNIPEIT_URL or config.SNIPEIT_URL == "YOUR_SNIPEIT_URL":
        _print_error("SNIPEIT_URL is not configured correctly in config.py.")
        return None
    if not hasattr(config, 'SNIPEIT_API_KEY') or not config.SNIPEIT_API_KEY or config.SNIPEIT_API_KEY == "YOUR_SNIPEIT_API_KEY":
        _print_error("SNIPEIT_API_KEY is not configured correctly in config.py.")
        return None

    base_url = config.SNIPEIT_URL.rstrip('/')
    api_url = f"{base_url}/api/v1/hardware/byserial/{serial_number}"
    
    headers = {
        "Authorization": f"Bearer {config.SNIPEIT_API_KEY}",
        "Accept": "application/json",
        "Content-Type": "application/json"
    }

    try:
        _print_verbose(f"Querying API: {api_url}")
        response = requests.get(api_url, headers=headers, timeout=15)
        response.raise_for_status()
        
        asset_data_raw = response.json()
        return _parse_snipeit_api_response(asset_data_raw, serial_number) # Pass serial_number as identifier

    except requests.exceptions.HTTPError as errh:
        if response.status_code == 404:
            _print_status(f"Asset with serial number '{serial_number}' not found (404).")
        else:
            _print_error(f"HTTP Error: {errh}")
            try:
                error_details = response.json()
                messages = error_details.get('messages', error_details.get('message', 'No additional error messages.'))
                _print_error(f"Snipe-IT Message: {messages}")
            except json.JSONDecodeError:
                _print_error(f"Response content (non-JSON): {response.text}")
        return None
    except requests.exceptions.ConnectionError as errc:
        _print_error(f"Error Connecting to {config.SNIPEIT_URL}: {errc}")
        return None
    except requests.exceptions.Timeout as errt:
        _print_error(f"Timeout Error: {errt}")
        return None
    except requests.exceptions.RequestException as err:
        _print_error(f"An unexpected error occurred during API request: {err}")
        return None
    except json.JSONDecodeError:
        _print_error(f"Could not decode JSON response from Snipe-IT. URL: {api_url}", f"Status: {response.status_code}, Response text (first 500): {response.text[:500]}...")
        return None

def get_asset_by_id(asset_id):
    """Fetches and parses asset details from Snipe-IT API by asset ID."""
    if not hasattr(config, 'SNIPEIT_URL') or not config.SNIPEIT_URL or config.SNIPEIT_URL == "YOUR_SNIPEIT_URL":
        _print_error("SNIPEIT_URL is not configured correctly in config.py.")
        return None
    if not hasattr(config, 'SNIPEIT_API_KEY') or not config.SNIPEIT_API_KEY or config.SNIPEIT_API_KEY == "YOUR_SNIPEIT_API_KEY":
        _print_error("SNIPEIT_API_KEY is not configured correctly in config.py.")
        return None

    base_url = config.SNIPEIT_URL.rstrip('/')
    api_url = f"{base_url}/api/v1/hardware/{asset_id}"
    
    headers = {
        "Authorization": f"Bearer {config.SNIPEIT_API_KEY}",
        "Accept": "application/json",
        "Content-Type": "application/json"
    }

    try:
        _print_verbose(f"Querying API: {api_url}")
        response = requests.get(api_url, headers=headers, timeout=15)
        response.raise_for_status()
        
        asset_data_raw = response.json()
        # For by-ID, the response is the asset object directly.
        return _parse_snipeit_api_response(asset_data_raw, asset_id) # Pass asset_id as identifier

    except requests.exceptions.HTTPError as errh:
        if response.status_code == 404:
            _print_status(f"Asset with ID '{asset_id}' not found (404).")
        else:
            _print_error(f"HTTP Error: {errh}")
            try:
                error_details = response.json()
                messages = error_details.get('messages', error_details.get('message', 'No additional error messages.'))
                _print_error(f"Snipe-IT Message: {messages}")
            except json.JSONDecodeError:
                _print_error(f"Response content (non-JSON): {response.text}")
        return None
    except requests.exceptions.ConnectionError as errc:
        _print_error(f"Error Connecting to {config.SNIPEIT_URL}: {errc}")
        return None
    except requests.exceptions.Timeout as errt:
        _print_error(f"Timeout Error: {errt}")
        return None
    except requests.exceptions.RequestException as err:
        _print_error(f"An unexpected error occurred during API request: {err}")
        return None
    except json.JSONDecodeError:
        _print_error(f"Could not decode JSON response from Snipe-IT. URL: {api_url}", f"Status: {response.status_code}, Response text (first 500): {response.text[:500]}...")
        return None

def get_custom_field_value(asset_details, target_display_name):
    """
    Extracts the value of a specific custom field from asset details
    by its display name.
    IMPORTANT: This function expects `target_display_name` to be the human-readable
    display name of the custom field (e.g., "Klasse"), NOT the internal API name
    (e.g., "_snipeit_klasse_3"). Ensure `config.TARGET_CUSTOM_FIELD_API_NAME` is set
    to the display name if using this function as is.
    
    Args:
        asset_details (dict): The asset data from Snipe-IT.
        target_display_name (str): The display name of the custom field (e.g., "Klasse").

    Returns:
        str: The value of the custom field, or None if not found.
    """
    if 'custom_fields' in asset_details and asset_details['custom_fields'] and isinstance(asset_details['custom_fields'], dict):
        # found_display_names = [] # For debugging, if needed
        for internal_key, field_data in asset_details['custom_fields'].items():
            if isinstance(field_data, dict) and 'field' in field_data:
                current_display_name = field_data.get('field')
                # found_display_names.append(current_display_name) # For debugging
                if current_display_name == target_display_name:
                    return field_data.get('value')
            # else:
                # _print_verbose(f"Skipping custom field with internal key '{internal_key}' due to unexpected format: {field_data}")
        
        # _print_verbose(f"Custom field with display name '{target_display_name}' was NOT found.")
        # if hasattr(config, 'VERBOSE_OUTPUT') and config.VERBOSE_OUTPUT and found_display_names:
        #     _print_verbose(f"Available custom field display names for this asset are: {found_display_names}")
        # elif hasattr(config, 'VERBOSE_OUTPUT') and config.VERBOSE_OUTPUT:
        #     _print_verbose(f"No custom field display names were extracted from the asset's custom_fields data.")

    elif 'custom_fields' not in asset_details or not asset_details['custom_fields']:
        _print_verbose(f"No 'custom_fields' data in asset_details or it's empty when searching for '{target_display_name}'.")
    
    return None

def _open_file_os_agnostic(filepath):
    """Opens a file using the default OS application."""
    try:
        if os.name == 'nt': # Windows
            os.startfile(filepath)
        elif sys.platform == 'darwin': # macOS
            subprocess.run(['open', filepath], check=True)
        else: # Linux and other POSIX
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

    try:
        gs_path = getattr(config, 'GHOSTSCRIPT_PATH', None)
        if not gs_path or not os.path.exists(gs_path):
            _print_error(f"Ghostscript path '{gs_path if gs_path else 'Not Set'}' not found or not configured in config.py.", "Please install Ghostscript and set GHOSTSCRIPT_PATH correctly.")
            return False

        _print_verbose(f"Attempting to print PDF '{pdf_path}' to printer '{printer_name}' using Ghostscript: {gs_path}")

        gs_command = [
            gs_path,
            "-dNOPAUSE",
            "-dBATCH",
            "-sDEVICE=mswinpr2",
            f"-sOutputFile=%printer%{printer_name}",
            # "-dFIXEDMEDIA", # Consider enabling if PDF page size matches physical label exactly
            "-dPrinted",
            "-q", 
            pdf_path 
        ]
        
        _print_verbose(f"Executing Ghostscript command: {' '.join(gs_command)}")
        _print_status(f"Sending PDF to printer '{printer_name}'...")

        process = subprocess.run(gs_command, capture_output=True, text=True, check=False)

        if process.returncode == 0:
            _print_verbose(f"Ghostscript printing command executed successfully for {pdf_path} to {printer_name}.")
            return True
        else:
            _print_error(f"Printing PDF with Ghostscript failed. Return code: {process.returncode}")
            if process.stdout: _print_verbose(f"Ghostscript stdout:\n{process.stdout}")
            if process.stderr: _print_verbose(f"Ghostscript stderr:\n{process.stderr}")
            if not (hasattr(config, 'VERBOSE_OUTPUT') and config.VERBOSE_OUTPUT):
                 _print_status("  Printing failed. Check printer status and Ghostscript configuration. Enable VERBOSE_OUTPUT for more details.")
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
        # get_asset_by_serial/id already prints appropriate messages
        return

    # The size selection logic and determination of scale_factor, selected_x_offset_mm,
    # and selected_y_offset_mm have been moved to main().
    # This function now receives these values as arguments.
    # (The incorrect indentation block below was removed)
    # selected_x_offset_mm = getattr(config, 'PRINT_X_OFFSET_MM_NORMAL', 0)
    # selected_y_offset_mm = getattr(config, 'PRINT_Y_OFFSET_MM_NORMAL', 0)
    # _print_verbose("Selected Normal size (100%).")
    # break

    _print_status("\n--- Asset Details Found ---")
    _print_status(f"  ID: {asset_details.get('id')}")
    _print_status(f"  Asset Tag: {asset_details.get('asset_tag')}")
    _print_status(f"  Name: {asset_details.get('name')}")
    _print_status(f"  Serial: {asset_details.get('serial')}")
    
    model_info = asset_details.get('model', {})
    _print_status(f"  Model: {model_info.get('name', 'N/A')}")
    
    status_label_info = asset_details.get('status_label', {})
    _print_status(f"  Status: {status_label_info.get('name', 'N/A')}")

    # Note: get_custom_field_value expects config.TARGET_CUSTOM_FIELD_API_NAME to be the *display name*.
    # This means config.TARGET_CUSTOM_FIELD_API_NAME should be set to "Klasse" (or similar),
    # not "_snipeit_klasse_3".
    target_custom_field_value = get_custom_field_value(asset_details, config.TARGET_CUSTOM_FIELD_API_NAME)
    
    if target_custom_field_value is not None: # Check for None explicitly, as empty string might be a valid value
        _print_status("\n========================================")
        _print_status(f"  {config.TARGET_CUSTOM_FIELD_LABEL_DISPLAY_NAME.upper()}: {target_custom_field_value}")
        _print_status("========================================\n")
    else:
        _print_verbose(f"Custom field '{config.TARGET_CUSTOM_FIELD_API_NAME}' (searched by display name) not found or has no value for this asset.")
        _print_status(f"Value for '{config.TARGET_CUSTOM_FIELD_LABEL_DISPLAY_NAME}' not found or is empty for this asset.\n")

    asset_id = asset_details.get('id')
    if not asset_id:
        _print_error("Asset ID not found in details, cannot generate label URL.")
        return

    asset_url = f"{config.SNIPEIT_URL.rstrip('/')}/hardware/{asset_id}"
    qr_image_filename = ""
    pdf_label_filename = ""

    try:
        # Create temporary files that are not deleted immediately for easier debugging if needed
        # For production, you might want delete=True for tmp_qr_file if it's reliably cleaned up.
        # pdf_label_filename is kept if printing fails or if DEBUG_OPEN_PDF_INSTEAD_OF_PRINTING is true.
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_qr_file_obj, \
             tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_pdf_file_obj:
            qr_image_filename = tmp_qr_file_obj.name
            pdf_label_filename = tmp_pdf_file_obj.name

        generate_qr_code_image(asset_url, qr_image_filename)
        _print_verbose(f"QR code generated: {qr_image_filename}")

        create_label_pdf(
            asset_details,
            qr_image_filename,
            pdf_label_filename,
            config.TARGET_CUSTOM_FIELD_LABEL_DISPLAY_NAME,
            target_custom_field_value,
            scale_factor, # Pass the determined scale factor
            selected_x_offset_mm, # Pass the selected X offset
            selected_y_offset_mm  # Pass the selected Y offset
        )
        # create_label_pdf prints its own verbose message upon success

        print_attempted = False
        print_successful = False
        pdf_opened_for_review = False

        if hasattr(config, 'DEBUG_OPEN_PDF_INSTEAD_OF_PRINTING') and config.DEBUG_OPEN_PDF_INSTEAD_OF_PRINTING:
            _print_status(f"DEBUG mode: Opening PDF {pdf_label_filename} for review instead of printing.")
            _open_file_os_agnostic(pdf_label_filename)
            pdf_opened_for_review = True
        elif hasattr(config, 'PRINTER_NAME') and config.PRINTER_NAME:
            print_attempted = True
            print_successful = print_pdf_windows(pdf_label_filename, config.PRINTER_NAME)
            if print_successful:
                _print_status(f"Label successfully sent to printer: {config.PRINTER_NAME}")
        else:
            _print_warning("Printer name not configured in config.py or direct printing disabled.")
            _print_status(f"PDF saved for manual printing/review: {pdf_label_filename}")
            _open_file_os_agnostic(pdf_label_filename) # Offer to open if not printing
            pdf_opened_for_review = True


        if pdf_opened_for_review:
            _print_verbose(f"Label PDF (opened for review or saved) is at: {pdf_label_filename}")
        elif print_attempted:
            if not print_successful:
                _print_error(f"Printing failed. Label PDF is available at: {pdf_label_filename}")
            elif hasattr(config, 'VERBOSE_OUTPUT') and config.VERBOSE_OUTPUT:
                _print_verbose(f"Label PDF (successfully printed) is at: {pdf_label_filename}")
        # No specific message if printing was successful and not verbose, as status already printed.

    except Exception as e:
        _print_error(f"An unexpected error occurred during label generation or printing for '{identifier}': {e}")
        if pdf_label_filename and os.path.exists(pdf_label_filename):
             _print_status(f"  A PDF might have been partially generated at: {pdf_label_filename}")
    finally:
        if qr_image_filename and os.path.exists(qr_image_filename):
            try:
                os.remove(qr_image_filename)
                _print_verbose(f"Temporary QR image file removed: {qr_image_filename}")
            except OSError as e_os:
                _print_warning(f"Could not remove temporary QR image file {qr_image_filename}: {e_os}")
        
        # Decide whether to delete PDF:
        # - If DEBUG_OPEN_PDF_INSTEAD_OF_PRINTING is True, user has seen it. Could delete.
        # - If printing failed, keep it.
        # - If printing succeeded, could delete.
        # - If no printer configured and opened, user has seen it. Could delete.
        # Current logic: Keep PDF if DEBUG_OPEN_PDF_INSTEAD_OF_PRINTING is true, or if printing failed/not attempted.
        # Delete PDF only if printing was successful AND DEBUG_OPEN_PDF_INSTEAD_OF_PRINTING is false.
        delete_pdf = False
        if print_attempted and print_successful and not (hasattr(config, 'DEBUG_OPEN_PDF_INSTEAD_OF_PRINTING') and config.DEBUG_OPEN_PDF_INSTEAD_OF_PRINTING):
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
    
    if not hasattr(config, 'SNIPEIT_URL') or config.SNIPEIT_URL == "YOUR_SNIPEIT_URL" or \
       not hasattr(config, 'SNIPEIT_API_KEY') or config.SNIPEIT_API_KEY == "YOUR_SNIPEIT_API_KEY":
        _print_error("\nPlease update your SNIPEIT_URL and SNIPEIT_API_KEY in config.py before running.")
        sys.exit(1)
    
    # Check custom field configuration consistency
    if not hasattr(config, 'TARGET_CUSTOM_FIELD_API_NAME') or not config.TARGET_CUSTOM_FIELD_API_NAME:
        _print_warning("TARGET_CUSTOM_FIELD_API_NAME is not set in config.py. Custom field will not be fetched.")
    # The following warning was removed as per user feedback that the current configuration works as expected.
    # elif config.TARGET_CUSTOM_FIELD_API_NAME.startswith("_snipeit_"):
    #     _print_warning(f"WARNING: config.TARGET_CUSTOM_FIELD_API_NAME ('{config.TARGET_CUSTOM_FIELD_API_NAME}') "
    #                    "looks like an API internal name (e.g., '_snipeit_klasse_3'). "
    #                    "This application currently expects the *display name* of the custom field "
    #                    "(e.g., 'Klasse') for this setting to work correctly with get_custom_field_value(). "
    #                    "Please verify your config.py.")


    # --- Get Label Size Preference ONCE at the beginning ---
    scale_factor = 1.0 # Default scale
    selected_x_offset_mm = getattr(config, 'PRINT_X_OFFSET_MM_NORMAL', 0) # Default offset
    selected_y_offset_mm = getattr(config, 'PRINT_Y_OFFSET_MM_NORMAL', 0) # Default offset

    small_scale_factor_from_config = getattr(config, 'SMALL_LABEL_SCALE_FACTOR', 0.5)
    small_label_percentage = int(small_scale_factor_from_config * 100)
    size_prompt = f"Choose default label size for this session (N=Normal, S=Small {small_label_percentage}%): "

    while True:
        size_input = input(size_prompt).strip().upper()
        if size_input.upper() == 'N':
            scale_factor = 1.0
            selected_x_offset_mm = getattr(config, 'PRINT_X_OFFSET_MM_NORMAL', 0)
            selected_y_offset_mm = getattr(config, 'PRINT_Y_OFFSET_MM_NORMAL', 0)
            _print_status("Selected Normal size (100%) for this session.")
            break
        elif size_input.upper() == 'S':
            scale_factor = small_scale_factor_from_config # Use the value read earlier
            selected_x_offset_mm = getattr(config, 'PRINT_X_OFFSET_MM_SMALL', 0)
            selected_y_offset_mm = getattr(config, 'PRINT_Y_OFFSET_MM_SMALL', 0)
            _print_status(f"Selected Small size ({small_label_percentage}%) for this session.")
            break
        else:
            _print_warning("Invalid input. Please enter 'N' for Normal or 'S' for Small.")

    _print_status("\nReady to process assets. Enter a serial number to generate a label.")
    _print_status("Type 'exit', 'quit', or 'cancel' (and press Enter) to end the program.\n")
    _print_status(f"You can also enter a full asset URL like: {config.SNIPEIT_URL.rstrip('/')}/hardware/ASSET_ID\n")

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
            normalized_snipeit_url = config.SNIPEIT_URL.rstrip('/')
            asset_url_prefix = f"{normalized_snipeit_url}/hardware/"

            if user_input.lower().startswith(asset_url_prefix.lower()): # Case-insensitive check for prefix
                _print_verbose(f"Input detected as a URL: {user_input}")
                # Extract asset ID. Example: https://snipeit.brienznet.ch/hardware/123 or /hardware/123/view
                path_part = user_input[len(asset_url_prefix):] # "123" or "123/view"
                asset_id_str = path_part.split('/')[0]
                
                if asset_id_str.isdigit():
                    _process_asset_label_request(asset_id_str, input_type='id', scale_factor=scale_factor, selected_x_offset_mm=selected_x_offset_mm, selected_y_offset_mm=selected_y_offset_mm)
                else:
                    _print_error(f"Could not extract a valid numeric Asset ID from URL: {user_input}")
                    _print_status(f"  Expected format like: {asset_url_prefix}ASSET_ID")
            else:
                # Assume it's a serial number
                _process_asset_label_request(user_input, input_type='serial', scale_factor=scale_factor, selected_x_offset_mm=selected_x_offset_mm, selected_y_offset_mm=selected_y_offset_mm)
        
        except KeyboardInterrupt:
            _print_status("\nProcess interrupted by user. Exiting application.")
            break
        except Exception as e:
            _print_error(f"An unexpected error occurred in the main loop: {e}", "Continuing...")
        finally:
            _print_status("\n----------------------------------------")

if __name__ == "__main__":
    main()
