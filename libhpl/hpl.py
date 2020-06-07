import os
import struct

from PIL import Image, ImageDraw

COLOR_SIZE = 20
SQUARE_SIZE = 16
IMG_SIDE_LEN = COLOR_SIZE * SQUARE_SIZE

HPAL_HDR = (b"HPAL%\x01\x00\x00 \x04\x00\x00\x00\x01\x00\x00\x00\x00"
            b"\x00\x00\x00\x00\x00\x00\x01\x00\x00\x10\x00\x00\x00\x00")


def convert_to_hpal(f):
    """
    Original script by resnovae, slight tweak by Labryz.
    """
    with Image.open(f) as i:
        p = i.getdata().getpalette()

    out = os.path.splitext(f)[0]+".hpl"
    with open(out, "wb") as f:
        f.write(HPAL_HDR)
        a = 0
        for c in [p[i:i+1] for i in range(0, len(p), 1)][::-1]:
            f.write(c)
            a += 1
            if a == 3:
                f.write(b"\xff")
                a = 0


def _blap(color_data):
    a = 0
    for c in color_data:
        if a == 3:
            a = 0
            continue

        yield c
        a += 1


def convert_from_hpal(f):
    with open(f, "rb") as i:
        data = i.read()
        _, color_data = data.split(HPAL_HDR)

    palette = b"".join(list(_blap(color_data)))

    a = 0
    curr = []
    color_list = []
    for c in palette:
        if a == 3:
            a = 0
            color_list.append(tuple(curr[::-1]))
            curr = []
            continue

        curr.append(struct.unpack("B", c)[0])
        a += 1

    num_colors = len(color_list)
    color_list = ([(0, 0, 0)] * (256 - num_colors)) + color_list

    out = os.path.splitext(f)[0]+".png"
    with Image.new("P", (IMG_SIDE_LEN, IMG_SIDE_LEN)) as i:
        i.putpalette(palette[::-1])
        d = ImageDraw.Draw(i)

        x = 0
        y = 0
        curr = 0
        for _ in color_list:
            i.palette.colors[(x, y)] = curr
            dim = [((x * COLOR_SIZE), (y * COLOR_SIZE)), ((x * COLOR_SIZE) + COLOR_SIZE, (y * COLOR_SIZE) + COLOR_SIZE)]
            d.rectangle(dim, fill=(x, y))
            x += 1
            if x == SQUARE_SIZE:
                x = 0
                y += 1
            curr += 1

        i.save(out)
