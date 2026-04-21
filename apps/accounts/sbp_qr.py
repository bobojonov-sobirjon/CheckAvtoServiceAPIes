"""PNG QR (base64) for SBP / NSPK payment URL."""
from __future__ import annotations

import base64
import io

import qrcode


def pay_url_to_qr_png_base64(pay_url: str, *, box_size: int = 8) -> str:
    qr = qrcode.QRCode(version=None, box_size=box_size, border=2)
    qr.add_data(pay_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color='black', back_color='white')
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    return base64.b64encode(buf.getvalue()).decode('ascii')
