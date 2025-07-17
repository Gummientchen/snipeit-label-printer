# c:\Users\sbl\Documents\GitHub\snipeit-label-api\label_generator.py
import os
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm, cm # Corrected: cm is in reportlab.lib.units
from reportlab.lib.utils import ImageReader

try:
    import config
except ImportError:
    print("Error: config.py not found. Ensure it's in the same directory or Python path.")
    # This will cause a NameError later if config is not loaded, which is acceptable for now.
    # A more robust solution might involve raising a custom exception or exiting.
    pass 
    
# --- Default Layout Constants ---
# These constants define the base layout. Offsets from config.py will be applied to these.
BASE_MARGIN_MM = 3
QR_CODE_MARGIN_FACTOR = 3 # Determines QR code size relative to label height and margins
TEXT_FONT_FAMILY = "Helvetica"
TEXT_FONT_SIZE_PT = 9
TEXT_LINE_HEIGHT_MM = 4
TEXT_ADDITIONAL_TOP_OFFSET_MM = 2 # Additional offset for the first line of text from the top margin

def _calculate_layout_parameters(label_width_cm, label_height_cm, selected_x_offset_mm, selected_y_offset_mm, scale_factor):
    """
    Calculates all necessary layout dimensions and coordinates in ReportLab units (points).
    The incoming label_width_cm, label_height_cm are already scaled.
    The incoming selected_x_offset_mm, selected_y_offset_mm are the chosen offsets based on size.
    This function will use the scale_factor to scale internal constants like font size, margins etc.
    """
    # Scale internal constants
    scaled_base_margin_mm = BASE_MARGIN_MM * scale_factor
    scaled_text_font_size_pt = TEXT_FONT_SIZE_PT * scale_factor
    scaled_text_line_height_mm = TEXT_LINE_HEIGHT_MM * scale_factor
    scaled_text_additional_top_offset_mm = TEXT_ADDITIONAL_TOP_OFFSET_MM * scale_factor

    margin_rl = scaled_base_margin_mm * mm
    # Base label dimensions
    base_label_width_rl = label_width_cm * cm
    label_height_rl = label_height_cm * cm

    # Effective offsets in ReportLab units
    eff_x_offset_rl = selected_x_offset_mm * mm
    eff_y_offset_rl = selected_y_offset_mm * mm

    # PDF page dimensions (as per original logic, width adjusted by positive X offset)
    actual_pdf_page_width_rl = base_label_width_rl + max(0, eff_x_offset_rl)
    actual_pdf_page_height_rl = label_height_rl # Height is not auto-adjusted by offset

    # QR Code layout (original logic)
    # QR size is calculated to fit within label height, considering (QR_CODE_MARGIN_FACTOR * margin_rl) total vertical margin space for QR.
    qr_size_rl = label_height_rl - (QR_CODE_MARGIN_FACTOR * margin_rl)

    # Original X for QR was margin_orig - margin_orig = 0. We'll use margin_rl as a base if needed, but original was 0.
    qr_x_base_rl = 0 # qr_x_orig was effectively 0 (margin_orig - margin_orig)
    # Original Y for QR bottom-left corner, placed near top.
    # This means the QR's bottom edge is (QR_CODE_MARGIN_FACTOR * margin_rl) from the PDF bottom,
    # and its top edge aligns with the PDF top if no y_offset.
    qr_y_base_rl = label_height_rl - qr_size_rl 

    # Text layout (original logic)
    # Text starts to the right of where the QR code (if at x=0) would end.
    text_x_start_base_rl = qr_size_rl 
    # Text baseline for the first line, near the top of the label.
    text_y_start_base_rl = label_height_rl - margin_rl - (scaled_text_additional_top_offset_mm * mm)

    # Apply offsets to base positions
    layout_params = {
        "page_width": actual_pdf_page_width_rl,
        "page_height": actual_pdf_page_height_rl,
        "qr_x": qr_x_base_rl + eff_x_offset_rl,
        "qr_y": qr_y_base_rl + eff_y_offset_rl, # Base Y was already calculated from top
        "qr_size": qr_size_rl,
        "text_x_start": text_x_start_base_rl + eff_x_offset_rl,
        "text_y_start": text_y_start_base_rl + eff_y_offset_rl, # Base Y was already calculated from top
        "font_size": scaled_text_font_size_pt,
        "line_height": scaled_text_line_height_mm * mm,
        "margin_for_text_wrap": margin_rl # Used for text wrapping width calculation
    }
    return layout_params

def _draw_qr_code_on_canvas(c, qr_image_path, x, y, size):
    """Draws the QR code onto the canvas."""
    if os.path.exists(qr_image_path):
        try:
            c.drawImage(ImageReader(qr_image_path), x, y, width=size, height=size, preserveAspectRatio=True)
        except Exception as e:
            print(f"Warning: Could not draw QR image from {qr_image_path}. Error: {e}")
    else:
        print(f"Warning: QR image not found at {qr_image_path}")

def _draw_asset_details_on_canvas(c, asset_details, custom_field_display_name, custom_field_actual_value, layout_params):
    """Prepares and draws the asset details text onto the canvas."""
    
    # --- Prepare Text Data ---
    asset_name = asset_details.get('name', 'N/A')
    asset_tag = asset_details.get('asset_tag', 'N/A')
    serial = asset_details.get('serial', 'N/A')
    model_info = asset_details.get('model', {})
    model_name = model_info.get('name', 'N/A')
    
    display_custom_value = custom_field_actual_value if custom_field_actual_value is not None else "N/A"

    details_to_print = [
        (f"Name: {asset_name}", asset_name != 'N/A'),
        (f"Tag: {asset_tag}", asset_tag != 'N/A'),
        (f"Serial: {serial}", serial != 'N/A'),
        (f"Model: {model_name}", model_name != 'N/A'),
        (f"{custom_field_display_name}: {display_custom_value}", display_custom_value != 'N/A')
    ]

    # --- Draw Text Data ---
    text_object = c.beginText()
    text_object.setFont(TEXT_FONT_FAMILY, layout_params["font_size"])
    text_object.setTextOrigin(layout_params["text_x_start"], layout_params["text_y_start"])
    text_object.setLeading(layout_params["line_height"])

    # Max width available for text (from text_x_start to right edge of PDF page minus a margin)
    max_text_width = layout_params["page_width"] - layout_params["text_x_start"] - layout_params["margin_for_text_wrap"]

    for text_line, should_print in details_to_print:
        if should_print:
            # Basic word wrapping (original logic)
            if c.stringWidth(text_line, TEXT_FONT_FAMILY, layout_params["font_size"]) > max_text_width:
                parts = text_line.split(":", 1)
                if len(parts) == 2:
                    prefix, value = parts
                    if value.strip() and value.strip() != 'N/A': # Ensure value is meaningful
                        text_object.textLine(f"{prefix}:")
                        text_object.textLine(f"  {value.strip()}")
                    # else, if value is not meaningful, maybe skip or print prefix only?
                    # For now, if value is not meaningful after split, it won't print the line.
                else: # No colon, print as is if it fits (though unlikely if it's too long)
                    text_object.textLine(text_line) 
            else:
                parts = text_line.split(":", 1)
                # Ensure that even if it fits, we don't print lines like "Field: N/A" or "Field: "
                if len(parts) == 2:
                    prefix, value = parts
                    if value.strip() and value.strip() != 'N/A':
                        text_object.textLine(text_line)
                else: # Should not happen with current details_to_print structure
                    text_object.textLine(text_line)

    c.drawText(text_object)

def create_label_pdf(asset_details, qr_image_path, output_pdf_path, custom_field_display_name, custom_field_actual_value, scale_factor, x_offset_mm, y_offset_mm):
    """
    Creates a PDF label with a QR code and asset information, using settings from config.py.

    Args:
        asset_details (dict): The full asset data from Snipe-IT.
        qr_image_path (str): Path to the generated QR code image.
        output_pdf_path (str): Path where the PDF label will be saved.
        custom_field_display_name (str): The display name of the target custom field (e.g., "Klasse").
        custom_field_actual_value (str): The value of the target custom field for this asset.
        scale_factor (float): Factor by which to scale the label dimensions and internal layout constants.
        x_offset_mm (float): The selected X offset in mm for the chosen size. This is used directly.
        y_offset_mm (float): The selected Y offset in mm for the chosen size. This is used directly.
    """
    # Read label dimensions from config
    label_width_cm = getattr(config, 'LABEL_WIDTH_CM', 7.62) # Default if not in config
    label_height_cm = getattr(config, 'LABEL_HEIGHT_CM', 5.08) # Default if not in config
    
    # Apply scale_factor to base label dimensions
    scaled_label_width_cm = label_width_cm * scale_factor
    scaled_label_height_cm = label_height_cm * scale_factor

    # Calculate all layout parameters
    # Pass the scaled dimensions, the UNMODIFIED selected offsets, and the scale_factor
    layout = _calculate_layout_parameters(
        scaled_label_width_cm, 
        scaled_label_height_cm, 
        x_offset_mm,  # Use the direct, selected offset from arguments
        y_offset_mm,  # Use the direct, selected offset from arguments
        scale_factor
    )
    
    # Create canvas
    c = canvas.Canvas(output_pdf_path, pagesize=(layout["page_width"], layout["page_height"]))

    # Draw QR Code
    _draw_qr_code_on_canvas(c, qr_image_path, layout["qr_x"], layout["qr_y"], layout["qr_size"])

    # Draw Asset Details Text
    _draw_asset_details_on_canvas(c, asset_details, custom_field_display_name, custom_field_actual_value, layout)
    
    c.save()
    
    if hasattr(config, 'VERBOSE_OUTPUT') and config.VERBOSE_OUTPUT:
        print(f"PDF label generated: {output_pdf_path}")
