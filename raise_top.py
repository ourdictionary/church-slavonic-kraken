#!/usr/bin/env python3
"""Поднимает верх строк в разметке kraken, чтобы ударения, придыхания и титла не срезались.
Разметка `kraken -x -i page.png lines.xml segment -bl` часто проводит верх строки по верху букв, и надстрочных знаков модель не видит.
Скрипт поднимает верх каждой строки до 3/4 межстрочия над её базовой линией (межстрочие — медиана по странице), низ не меняет.
kraken ищет картинку страницы относительно файла разметки, поэтому при записи в другую папку путь к картинке пересчитывается.
Запуск: python3 raise_top.py lines.xml lines_top.xml
Папка целиком: python3 raise_top.py xml_dir xml_top_dir
Свой подъём в пикселях: python3 raise_top.py -u 52 lines.xml lines_top.xml

Raises the top of every line polygon in a kraken PAGE XML segmentation to 3/4 of the line spacing above the baseline
(median spacing on the page), so that accents, breathings and titlos stay inside the line. The bottom is not changed.
When the output goes to another folder, a relative image path is rewritten, since kraken looks for the image next to the XML.
"""
import os
import statistics
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

RATIO = 0.74   # Минея 1893 г.: межстрочие 70 px, надстрочные знаки — до 51 px над базовой линией
FALLBACK = 52  # подъём в пикселях, если на странице меньше трёх пар строк


def pts(s):
    return [tuple(map(float, p.split(","))) for p in s.split()]


def spacing(lines, q):
    """Медиана расстояния от базовой линии строки до ближайшей строки над ней, если по горизонтали они перекрываются."""
    spans = []
    for line in lines:
        bl = pts(line.find(q("Baseline")).get("points"))
        xs = [p[0] for p in bl]
        spans.append((min(xs), max(xs), statistics.mean(p[1] for p in bl)))
    gaps = []
    for x0, x1, y in spans:
        above = [y - y2 for a0, a1, y2 in spans if y2 < y - 5 and min(x1, a1) - max(x0, a0) > 0.3 * (x1 - x0)]
        if above:
            gaps.append(min(above))
    return statistics.median(gaps) if len(gaps) >= 3 else None


def raise_line(line, up, q):
    bl = sorted(pts(line.find(q("Baseline")).get("points")))

    def base(x):
        if x <= bl[0][0]:
            return bl[0][1]
        for (x0, y0), (x1, y1) in zip(bl, bl[1:]):
            if x <= x1:
                return y0 + (y1 - y0) * (x - x0) / max(x1 - x0, 1e-9)
        return bl[-1][1]

    coords = line.find(q("Coords"))
    out, n = [], 0
    for x, y in pts(coords.get("points")):
        if base(x) - up < y < base(x):
            y, n = max(0, base(x) - up), n + 1
        out.append(f"{int(round(x))},{int(round(y))}")
    coords.set("points", " ".join(out))
    return n


def fix(data, up=None, src_dir=".", dst_dir="."):
    root = ET.fromstring(data)
    ns = root.tag[1:].split("}")[0]
    ET.register_namespace("", ns)
    q = lambda tag: f"{{{ns}}}{tag}"
    lines = [l for l in root.iter(q("TextLine")) if l.find(q("Baseline")) is not None and l.find(q("Coords")) is not None]
    if up is None:
        gap = spacing(lines, q)
        up = round(RATIO * gap) if gap else FALLBACK
    n = sum(raise_line(line, up, q) for line in lines)
    src, dst = os.path.abspath(src_dir), os.path.abspath(dst_dir)
    for page in root.iter(q("Page")):
        img = page.get("imageFilename")
        if img and src != dst and not os.path.isabs(img) and "://" not in img:
            page.set("imageFilename", os.path.relpath(os.path.join(src, img), dst))
    return ET.tostring(root, encoding="UTF-8", xml_declaration=True), up, n


def main(args):
    up = None
    if len(args) == 4 and args[0] == "-u":
        up, args = int(args[1]), args[2:]
    if len(args) != 2:
        sys.exit(__doc__)
    src, dst = Path(args[0]), Path(args[1])
    if src.is_dir():
        dst.mkdir(parents=True, exist_ok=True)
        pairs = [(f, dst / f.name) for f in sorted(src.glob("*.xml"))]
    else:
        pairs = [(src, dst)]
    for a, b in pairs:
        data, up_px, n = fix(a.read_bytes(), up, a.parent, b.parent)
        b.write_bytes(data)
        print(f"{a.name}: line tops raised to {up_px} px above the baseline ({n} points) -> {b}")


if __name__ == "__main__":
    main(sys.argv[1:])
