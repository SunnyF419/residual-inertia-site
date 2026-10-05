"""Generate crisp favicon assets from the existing, unmodified brand symbol.

Pillow is only needed when regenerating assets; the site publishes these files
directly without introducing a rendering dependency into its build.
"""
from copy import deepcopy
from pathlib import Path
import re
import xml.etree.ElementTree as ET

from PIL import Image, ImageChops, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / 'assets/brand'
INK = '#0A2122'
PAPER = '#F2F2EB'
NS = '{http://www.w3.org/2000/svg}'
ICO_SIZES = (16, 32, 48, 64, 128, 256)


def symbol_transform(size):
    # Fit the visible mark, rather than the original logo's padded canvas.
    scale = size * 0.78 / 175
    return scale, size / 2 - 91.5 * scale, size / 2 - 68 * scale


def cubic_polygon(path):
    """Sample the source symbol's M/L/C/Z paths without changing their geometry."""
    tokens = re.findall(r'[MLCZ]|-?\d+(?:\.\d+)?', path)
    points = []
    position = 0
    while position < len(tokens):
        command = tokens[position]
        position += 1
        if command in ('M', 'L'):
            current = tuple(map(float, tokens[position:position + 2]))
            position += 2
            points.append(current)
        elif command == 'C':
            values = list(map(float, tokens[position:position + 6]))
            position += 6
            control1, control2, end = values[:2], values[2:4], values[4:]
            for step in range(1, 129):
                t = step / 128
                points.append(tuple((1-t)**3 * current[i] + 3*(1-t)**2*t * control1[i]
                                    + 3*(1-t)*t*t * control2[i] + t**3 * end[i] for i in (0, 1)))
            current = end
        elif command != 'Z':
            raise ValueError(f'Unsupported brand path command: {command}')
    return points


def source_symbol():
    return ET.parse(OUT_DIR / 'RI-symbol-reverse.svg').getroot().find(NS + 'g')


def draw_symbol(size):
    """Render the exact source bars, clearance curve, and swoosh at high resolution."""
    group = source_symbol()
    scale, offset_x, offset_y = symbol_transform(size)

    def point(x, y):
        return offset_x + x * scale, offset_y + y * scale

    background = Image.new('RGBA', (size, size))
    ImageDraw.Draw(background).rounded_rectangle((0, 0, size-1, size-1), radius=size * 96 / 512, fill=INK)
    bars = Image.new('L', (size, size))
    draw = ImageDraw.Draw(bars)
    for bar in group.findall('.//' + NS + 'rect'):
        x, y, width, height = (float(bar.get(key)) for key in ('x', 'y', 'width', 'height'))
        draw.rectangle((*point(x, y), *point(x+width, y+height)), fill=255)
    clip = group.find('.//' + NS + 'clipPath/' + NS + 'path').get('d')
    clearance = clip[clip.rindex('M'):]
    draw.polygon([point(x, y) for x, y in cubic_polygon(clearance)], fill=0)
    swoosh = group.find(NS + 'path').get('d')
    draw.polygon([point(x, y) for x, y in cubic_polygon(swoosh)], fill=255)
    background.paste(PAPER, (0, 0, size, size), ImageChops.multiply(bars, background.getchannel('A')))
    return background


def write_svg():
    ET.register_namespace('', 'http://www.w3.org/2000/svg')
    root = ET.Element(NS + 'svg', {'viewBox': '0 0 512 512'})
    ET.SubElement(root, NS + 'rect', {'width': '512', 'height': '512', 'rx': '96', 'fill': INK})
    group = deepcopy(source_symbol())
    scale, x, y = symbol_transform(512)
    group.set('transform', f'translate({x:.6f} {y:.6f}) scale({scale:.6f})')
    root.append(group)
    (OUT_DIR / 'favicon.svg').write_text(ET.tostring(root, encoding='unicode') + '\n', encoding='utf-8')


def main():
    # Supersample curves and diagonal edges before producing each final size.
    master = draw_symbol(2048)
    for size, name in [(16, 'favicon-16x16.png'), (32, 'favicon-32x32.png'),
                       (48, 'favicon-48x48.png'), (180, 'apple-touch-icon.png'),
                       (192, 'android-chrome-192x192.png'), (512, 'android-chrome-512x512.png')]:
        master.resize((size, size), Image.Resampling.LANCZOS).save(OUT_DIR / name, 'PNG')
    # Saving from a 16px frame silently discarded larger ICO sizes in the old generator.
    master.resize((256, 256), Image.Resampling.LANCZOS).save(
        OUT_DIR / 'favicon.ico', format='ICO', sizes=[(size, size) for size in ICO_SIZES])
    write_svg()
    print('Generated matching SVG, six PNG sizes, and multi-resolution ICO:', ICO_SIZES)


if __name__ == '__main__':
    main()
