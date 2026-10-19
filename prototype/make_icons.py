"""Build simple open-book app icons using geometric shapes, no external assets."""
from pathlib import Path
from PIL import Image, ImageDraw


def main():
    for size in (192, 512):
        image = Image.new('RGB', (size, size), '#263d59')
        draw = ImageDraw.Draw(image)
        # Open book inside the maskable-icon safe zone.
        draw.polygon([(round(x*size),round(y*size)) for x,y in
                      ((.22,.30),(.46,.34),(.46,.73),(.22,.69))],fill='#ffffff')
        draw.polygon([(round(x*size),round(y*size)) for x,y in
                      ((.54,.34),(.78,.30),(.78,.69),(.54,.73))],fill='#dce5ef')
        image.save(Path(__file__).parent / 'static' / f'icon-{size}.png')


if __name__ == '__main__':
    main()
