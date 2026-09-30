"""Generate favicon PNG and ICO files from the brand symbol using PIL."""
from PIL import Image, ImageDraw
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / 'assets/brand'

INK = '#0A2122'
PAPER = '#F2F2EB'


def draw_symbol(size: int):
    """Draw the brand symbol on a square canvas of the given size."""
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Background with rounded corners
    radius = int(size * 0.18)
    draw.rounded_rectangle([0, 0, size, size], radius=radius, fill=INK)

    # Symbol coordinate system: original symbol is 184x132, centered in canvas
    scale = size * 0.55 / 184
    offset_x = (size - 184 * scale) / 2
    offset_y = (size - 132 * scale) / 2

    def sx(x):
        return offset_x + x * scale

    def sy(y):
        return offset_y + y * scale

    # Three bars
    bar_w = 23 * scale
    draw.rectangle([sx(40), sy(49), sx(40 + 23), sy(49 + 64)], fill=PAPER)
    draw.rectangle([sx(72), sy(31), sx(72 + 23), sy(31 + 82)], fill=PAPER)
    draw.rectangle([sx(104), sy(13), sx(104 + 23), sy(13 + 100)], fill=PAPER)

    # Curve (same path as brand symbol)
    # M 8 116 C 59 101 122 70 174 18 C 132 79 67 121 8 116 Z
    points = []
    for t in range(101):
        t /= 100.0
        x = (1 - t) ** 2 * 8 + 2 * (1 - t) * t * 59 + t ** 2 * 122
        y = (1 - t) ** 2 * 116 + 2 * (1 - t) * t * 101 + t ** 2 * 70
        points.append((sx(x), sy(y)))
    for t in range(101):
        t /= 100.0
        x = (1 - t) ** 2 * 122 + 2 * (1 - t) * t * 174 + t ** 2 * 67
        y = (1 - t) ** 2 * 70 + 2 * (1 - t) * t * 18 + t ** 2 * 121
        points.append((sx(x), sy(y)))
    for t in range(101):
        t /= 100.0
        x = (1 - t) ** 2 * 67 + 2 * (1 - t) * t * 8 + t ** 2 * 8
        y = (1 - t) ** 2 * 121 + 2 * (1 - t) * t * 116 + t ** 2 * 116
        points.append((sx(x), sy(y)))

    draw.polygon(points, fill=PAPER)

    return img


def main():
    # Generate master 512px image
    master = draw_symbol(512)

    # PNG fallbacks
    outputs = [
        (16, OUT_DIR / 'favicon-16x16.png'),
        (32, OUT_DIR / 'favicon-32x32.png'),
        (180, OUT_DIR / 'apple-touch-icon.png'),
        (192, OUT_DIR / 'android-chrome-192x192.png'),
        (512, OUT_DIR / 'android-chrome-512x512.png'),
    ]
    for size, path in outputs:
        master.resize((size, size), Image.LANCZOS).save(path, 'PNG')

    # Multi-resolution ICO
    frames = [master.resize((s, s), Image.LANCZOS).convert('RGBA') for s in (16, 32, 48)]
    frames[0].save(OUT_DIR / 'favicon.ico', format='ICO', sizes=[(f.width, f.height) for f in frames])

    generated = sorted(p.name for p in OUT_DIR.iterdir()
                       if 'favicon' in p.name.lower()
                       or 'android-chrome' in p.name.lower()
                       or 'apple-touch' in p.name.lower())
    print('Generated:', generated)


if __name__ == '__main__':
    main()
