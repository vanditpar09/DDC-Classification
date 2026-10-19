"""Create synthetic typography fixtures, never presented as real book scans."""
from pathlib import Path
import json
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = Path(__file__).resolve().parent
FONT_CANDIDATES = ["/System/Library/Fonts/Supplemental/Arial.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]


def font(size):
    for path in FONT_CANDIDATES:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default(size=size)


def create():
    out = HERE / "samples"
    out.mkdir(exist_ok=True)
    cover = Image.new("RGB", (1100, 1400), "#f7f3e9")
    draw = ImageDraw.Draw(cover)
    draw.text((140, 310), "Connections", fill="#163d32", font=font(105))
    # Geometric artwork carries no classification clues or fabricated metadata.
    draw.rectangle((150, 600, 950, 1000), outline="#82a58b", width=3)
    draw.line((150, 600, 950, 1000), fill="#b1c1ab", width=3)
    draw.line((950, 600, 150, 1000), fill="#b1c1ab", width=3)
    cover.save(out / "ambiguous_cover.png")
    back = Image.new("RGB", (1100, 1400), "#fffdf7")
    draw = ImageDraw.Draw(back)
    lines = ["A practical introduction to computer science.", "Learn Python programming, data structures,", "and algorithms. Build software applications", "and understand how computers solve problems.", "Includes exercises on functions and databases."]
    for i, text in enumerate(lines):
        draw.text((85, 250 + i * 72), text, fill="#193328", font=font(37))
    back.save(out / "informative_back.png")
    blur = back.filter(ImageFilter.GaussianBlur(9))
    blur.save(out / "blurred_page.png")
    small = Image.new("RGB", (900, 600), "white")
    ImageDraw.Draw(small).text((50, 220), "Python programming and computer algorithms", fill="black", font=font(15))
    small.save(out / "small_text.png")
    Image.new("RGB", (800, 1000), "white").save(out / "blank.png")
    samples = [
        dict(name="Ambiguous cover", file="ambiguous_cover.png", kind="cover", language="eng", expected="request_page"),
        dict(name="Descriptive back cover", file="informative_back.png", kind="back_cover", language="eng", expected="request_page"),
        dict(name="Blurred page", file="blurred_page.png", kind="cover", language="eng", expected="recapture_region"),
        dict(name="Small print", file="small_text.png", kind="cover", language="eng", expected="reprocess_region"),
    ]
    (out / "manifest.json").write_text(json.dumps(samples, indent=2) + "\n")
    print(out)


if __name__ == "__main__":
    create()
