# qr_generator.py
import qrcode
import os

def generate_qr_code_image(data, filename):
    """
    Generates a QR code and saves it as an image file.

    Args:
        data (str): The string or URL to encode in the QR code.
        filename (str): The path to save the generated image.

    Returns:
        str: The path to the saved QR code image.

    Raises:
        ValueError: If data is empty.
        IOError: If writing to the file fails.
    """
    if not data or not str(data).strip():
        raise ValueError("QR code data cannot be empty.")

    # Ensure output directory exists
    dir_name = os.path.dirname(filename)
    if dir_name and not os.path.exists(dir_name):
        try:
            os.makedirs(dir_name, exist_ok=True)
        except Exception as e:
            raise IOError(f"Could not create directory for QR code image: {dir_name}. Error: {e}")

    try:
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=1,
        )
        qr.add_data(data)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")
        img.save(filename)
        return filename
    except Exception as e:
        raise IOError(f"Failed to generate or write QR code image to '{filename}'. Detail: {e}")