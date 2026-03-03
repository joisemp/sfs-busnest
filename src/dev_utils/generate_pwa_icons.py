"""
Generate PWA PNG icons from logo-icon.svg using cairosvg + Pillow.
Produces icon-192.png and icon-512.png in src/static/images/.
Run inside Docker: docker exec sfs-busnest-container python dev_utils/generate_pwa_icons.py
"""
import io
import sys
from pathlib import Path

try:
    import cairosvg
except ImportError:
    print("cairosvg not installed. Run: pip install cairosvg")
    sys.exit(1)

try:
    from PIL import Image
except ImportError:
    print("Pillow not installed. Run: pip install pillow")
    sys.exit(1)

BASE_DIR = Path(__file__).resolve().parent.parent
SVG_PATH = BASE_DIR / "static" / "images" / "logo-icon.svg"
OUTPUT_DIR = BASE_DIR / "static" / "images"

SIZES = [192, 512]


def generate_icon(size: int):
    padding = int(size * 0.12)  # 12% padding on each side
    icon_size = size - padding * 2
    corner_radius = int(size * 0.22)  # rounded corners ~22% of size

    # Rasterise SVG at the padded inner size
    png_bytes = cairosvg.svg2png(
        url=str(SVG_PATH),
        output_width=icon_size,
        output_height=icon_size,
    )
    icon = Image.open(io.BytesIO(png_bytes)).convert("RGBA")
    icon = icon.resize((icon_size, icon_size), Image.LANCZOS)

    # White background at full size
    background = Image.new("RGBA", (size, size), (255, 255, 255, 255))

    # Rounded corner mask for the background
    mask = Image.new("L", (size, size), 0)
    from PIL import ImageDraw
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle([(0, 0), (size - 1, size - 1)], radius=corner_radius, fill=255)

    # Apply rounded mask to background
    rounded_bg = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    rounded_bg.paste(background, mask=mask)

    # Paste icon centered onto rounded background
    rounded_bg.paste(icon, (padding, padding), mask=icon.split()[3])

    out_path = OUTPUT_DIR / f"icon-{size}.png"
    rounded_bg.save(out_path, "PNG")
    print(f"Generated {size}x{size}: {out_path}")


if __name__ == "__main__":
    if not SVG_PATH.exists():
        print(f"SVG not found: {SVG_PATH}")
        sys.exit(1)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for sz in SIZES:
        generate_icon(sz)
    print("Done.")
