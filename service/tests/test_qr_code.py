import sys
from pathlib import Path

SERVICE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERVICE_ROOT))

from app.qr_code import qr_svg_data


def test_qr_svg_is_rendered_without_text_token() -> None:
    value = "2@test-token,part-two,part-three,part-four"
    rendered = qr_svg_data(value)
    assert rendered is not None
    assert rendered.lstrip().startswith("<svg")
    assert "svg:rect" in rendered
    assert value not in rendered


def test_qr_svg_empty_value_returns_none() -> None:
    assert qr_svg_data(None) is None
    assert qr_svg_data("  ") is None
