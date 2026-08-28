from __future__ import annotations

import qrcode
from qrcode.image.svg import SvgImage


def qr_svg_data(value: object) -> str | None:
    """Return a self-contained SVG for a provider QR value.

    The provider value is used only in memory to render the QR. Callers should
    not log, persist, or include the textual value in a response intended for
    browser display.
    """
    if value is None:
        return None
    raw = str(value).strip()
    if not raw:
        return None
    if raw.startswith("data:image/"):
        return raw
    image = qrcode.make(raw, image_factory=SvgImage)
    rendered = image.to_string(encoding="unicode")
    return rendered if rendered.lstrip().startswith("<svg") else None
