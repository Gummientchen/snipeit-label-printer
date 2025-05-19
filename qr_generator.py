# qr_generator.py
import qrcode

def generate_qr_code_image(data, filename):
    """Generates a QR code and saves it as an image file."""
    img = qrcode.make(data)
    img.save(filename)
    return filename