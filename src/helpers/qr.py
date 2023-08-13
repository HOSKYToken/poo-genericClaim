import qrcode
from PIL import Image


def generate_qr_image(data, version=1, correction=qrcode.constants.ERROR_CORRECT_H, box_size=10, border_size=4):
    qr = qrcode.QRCode(
        version=version,
        error_correction=correction,
        box_size=box_size,
        border=border_size
    )

    qr.add_data(data)

    return qr.make_image(fill='black', back_color='white')


def is_valid_qr_png(qr_path):
    try:
        img = Image.open(qr_path)
        img.verify()  # verify that it is, in fact, an image
        return True
    except (IOError, SyntaxError):
        return False
