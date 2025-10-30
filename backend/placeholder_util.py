
from PIL import Image, ImageDraw, ImageFont
from typing import Optional

def make_placeholder_png(path: str, width: int, height: int, message: str) -> None:
    """Create a simple placeholder PNG with an error message."""
    img = Image.new("RGB", (width, height), (0, 0, 0))
    draw = ImageDraw.Draw(img)
    # Try a default font
    try:
        font = ImageFont.load_default()
    except Exception:
        font = None
    msg = (message or "Error").strip().replace("\n", " ")
    if len(msg) > 80:
        msg = msg[:77] + "..."
    wrapped = "\n".join(_wrap_text(draw, msg, width - 80, font))
    # center text
    text_w, text_h = draw.multiline_textbbox((0, 0), wrapped, font=font)[2:]
    x = (width - text_w) // 2
    y = (height - text_h) // 2
    draw.multiline_text((x, y), wrapped, fill=(255, 255, 255), font=font, align="center")
    img.save(path, format="PNG")

def _wrap_text(draw: ImageDraw.ImageDraw, text: str, max_width: int, font: Optional[ImageFont.ImageFont]):
    words = text.split()
    lines = []
    cur = ""
    for w in words:
        trial = (cur + " " + w).strip()
        if draw.textlength(trial, font=font) <= max_width:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines
