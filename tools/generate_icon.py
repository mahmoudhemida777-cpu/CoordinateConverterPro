from pathlib import Path
from PIL import Image, ImageDraw

OUT = Path("resources/icon.ico")
OUT.parent.mkdir(parents=True, exist_ok=True)

sizes = [16, 24, 32, 48, 64, 128, 256]
images = []
for size in sizes:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    m = max(1, int(size * 0.08))
    d.rounded_rectangle((m, m, size - m - 1, size - m - 1), radius=max(2, int(size * 0.14)), fill="#1F3864")
    cx = cy = size / 2
    r = size * 0.30
    w = max(1, int(size * 0.025))
    d.ellipse((cx-r, cy-r, cx+r, cy+r), outline="#C9A227", width=w)
    d.line((cx-r*0.82, cy, cx+r*0.82, cy), fill="#FFFFFF", width=max(1, int(size*0.018)))
    d.line((cx, cy-r*0.82, cx, cy+r*0.82), fill="#FFFFFF", width=max(1, int(size*0.018)))
    diamond = [(cx, cy-r*0.72), (cx+r*0.22, cy), (cx, cy+r*0.72), (cx-r*0.22, cy)]
    d.polygon(diamond, fill="#C9A227")
    images.append(img)

images[-1].save(OUT, format="ICO", sizes=[(s, s) for s in sizes])
print(f"Generated {OUT}")
