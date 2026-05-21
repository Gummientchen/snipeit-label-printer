# label_generator.py
import os
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm, cm
from reportlab.lib.utils import ImageReader

# --- Default Layout Constants ---
# These constants define the base layout. Offsets will be applied to these.
BASE_MARGIN_MM = 3
QR_CODE_MARGIN_FACTOR = 3  # Determines QR code size relative to label height and margins
TEXT_FONT_FAMILY = "Helvetica"
TEXT_FONT_SIZE_PT = 9
TEXT_LINE_HEIGHT_MM = 4
TEXT_ADDITIONAL_TOP_OFFSET_MM = 2  # Additional offset for the first line of text from the top margin

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

    # PDF page dimensions (width adjusted by positive X offset)
    actual_pdf_page_width_rl = base_label_width_rl + max(0, eff_x_offset_rl)
    actual_pdf_page_height_rl = label_height_rl  # Height is not auto-adjusted by offset

    # QR Code layout
    # QR size is calculated to fit within label height, considering margin_rl space.
    qr_size_rl = label_height_rl - (QR_CODE_MARGIN_FACTOR * margin_rl)

    qr_x_base_rl = 0
    qr_y_base_rl = label_height_rl - qr_size_rl

    # Text layout
    text_x_start_base_rl = qr_size_rl
    text_y_start_base_rl = label_height_rl - margin_rl - (scaled_text_additional_top_offset_mm * mm)

    # Apply offsets to base positions
    layout_params = {
        "page_width": actual_pdf_page_width_rl,
        "page_height": actual_pdf_page_height_rl,
        "qr_x": qr_x_base_rl + eff_x_offset_rl,
        "qr_y": qr_y_base_rl + eff_y_offset_rl,
        "qr_size": qr_size_rl,
        "text_x_start": text_x_start_base_rl + eff_x_offset_rl,
        "text_y_start": text_y_start_base_rl + eff_y_offset_rl,
        "font_size": scaled_text_font_size_pt,
        "line_height": scaled_text_line_height_mm * mm,
        "margin_for_text_wrap": margin_rl
    }
    return layout_params

def _draw_qr_code_on_canvas(c, qr_image_path, x, y, size):
    """Draws the QR code onto the canvas."""
    if not qr_image_path:
        raise ValueError("No QR image path provided.")
    if not os.path.exists(qr_image_path):
        raise FileNotFoundError(f"QR image not found at '{qr_image_path}'")

    try:
        c.drawImage(ImageReader(qr_image_path), x, y, width=size, height=size, preserveAspectRatio=True)
    except Exception as e:
        raise RuntimeError(f"Could not draw QR image onto canvas. Detail: {e}")

def _draw_asset_details_on_canvas(c, asset_details, custom_field_display_name, custom_field_actual_value, layout_params):
    """Prepares and draws the asset details text onto the canvas."""
    if not asset_details:
        raise ValueError("No asset details data provided to draw.")

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

    try:
        # --- Draw Text Data ---
        text_object = c.beginText()
        text_object.setFont(TEXT_FONT_FAMILY, layout_params["font_size"])
        text_object.setTextOrigin(layout_params["text_x_start"], layout_params["text_y_start"])
        text_object.setLeading(layout_params["line_height"])

        # Max width available for text
        max_text_width = layout_params["page_width"] - layout_params["text_x_start"] - layout_params["margin_for_text_wrap"]

        for text_line, should_print in details_to_print:
            if should_print:
                # Basic word wrapping
                if c.stringWidth(text_line, TEXT_FONT_FAMILY, layout_params["font_size"]) > max_text_width:
                    parts = text_line.split(":", 1)
                    if len(parts) == 2:
                        prefix, value = parts
                        if value.strip() and value.strip() != 'N/A':
                            text_object.textLine(f"{prefix}:")
                            text_object.textLine(f"  {value.strip()}")
                    else:
                        text_object.textLine(text_line)
                else:
                    parts = text_line.split(":", 1)
                    if len(parts) == 2:
                        prefix, value = parts
                        if value.strip() and value.strip() != 'N/A':
                            text_object.textLine(text_line)
                    else:
                        text_object.textLine(text_line)

        c.drawText(text_object)
    except Exception as e:
        raise RuntimeError(f"Error rendering asset details text on PDF. Detail: {e}")

def create_label_pdf(asset_details, qr_image_path, output_pdf_path, custom_field_display_name, custom_field_actual_value, scale_factor, x_offset_mm, y_offset_mm, label_width_cm=7.0, label_height_cm=3.2, verbose_output=False):
    """
    Creates a PDF label with a QR code and asset information.

    Args:
        asset_details (dict): The full asset data from Snipe-IT.
        qr_image_path (str): Path to the generated QR code image.
        output_pdf_path (str): Path where the PDF label will be saved.
        custom_field_display_name (str): The display name of the target custom field (e.g., "Klasse").
        custom_field_actual_value (str): The value of the target custom field for this asset.
        scale_factor (float): Factor by which to scale the label dimensions.
        x_offset_mm (float): The selected X offset in mm.
        y_offset_mm (float): The selected Y offset in mm.
        label_width_cm (float): Width of the label in cm (default: 7.0).
        label_height_cm (float): Height of the label in cm (default: 3.2).
        verbose_output (bool): Set to True for verbose output (default: False).

    Raises:
        Exception: If any part of the PDF creation process fails.
    """
    if not output_pdf_path:
        raise ValueError("Output PDF path is required.")

    # Apply scale_factor to label dimensions
    scaled_label_width_cm = label_width_cm * scale_factor
    scaled_label_height_cm = label_height_cm * scale_factor

    # Calculate layout parameters
    layout = _calculate_layout_parameters(
        scaled_label_width_cm,
        scaled_label_height_cm,
        x_offset_mm,
        y_offset_mm,
        scale_factor
    )

    try:
        # Create canvas
        c = canvas.Canvas(output_pdf_path, pagesize=(layout["page_width"], layout["page_height"]))

        # Draw QR Code
        _draw_qr_code_on_canvas(c, qr_image_path, layout["qr_x"], layout["qr_y"], layout["qr_size"])

        # Draw Asset Details Text
        _draw_asset_details_on_canvas(c, asset_details, custom_field_display_name, custom_field_actual_value, layout)

        c.save()

        if verbose_output:
            print(f"PDF label generated: {output_pdf_path}")

    except Exception as e:
        # Clean up partial file if exists
        if os.path.exists(output_pdf_path):
            try:
                os.remove(output_pdf_path)
            except OSError:
                pass
        raise RuntimeError(f"Failed to generate PDF label at '{output_pdf_path}'. Detail: {e}")
