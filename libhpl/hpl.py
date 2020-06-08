from PIL import Image, ImageDraw

HPL_CHUNK_SIZE = 3
HPL_MAX_COLORS = 256
PALETTE_SQUARE_SIZE = 16

HPAL_HEADER = (b"HPAL%\x01\x00\x00 \x04\x00\x00\x00\x01\x00\x00\x00\x00"
               b"\x00\x00\x00\x00\x00\x00\x01\x00\x00\x10\x00\x00\x00\x00")


def convert_to_hpl(image_path):
    """
    Convert a PNG image to an HPL palette file.

    Note that PNG images are not required to have a palette and
    PIL will complain about images that do not contain one (i.e. raise an exception).

    Original script by resnovae, slight tweak by Labryz.
    Cleaned up some by slacknate.
    """
    out = image_path.replace(".png", ".hpl")

    with Image.open(image_path) as image_fp:
        palette = image_fp.getdata().getpalette()

    with open(out, "wb") as hpl_fp:
        hpl_fp.write(HPAL_HEADER)

        # Iterate our palette data in reverse.
        remaining = palette[::-1]
        while remaining:
            # We grab 3 byte chunks as each of these is an RGB tuple.
            chunk = remaining[0:HPL_CHUNK_SIZE]
            remaining = remaining[HPL_CHUNK_SIZE:]

            # When we write a chunk we append 0xFF. This seems to be some kind of marker.
            # It could also be other information we do not need? Perhaps an alpha channel?
            hpl_fp.write(chunk + b"\xFF")


def _remove_0xff(color_data):
    """
    Remove every fourth byte of the color data we read
    from the palette file. Looking at `convert_to_hpl` we can
    see that 0xFF is inserted after every third byte of our palette data.
    """
    remaining = color_data
    while remaining:
        chunk = remaining[0:HPL_CHUNK_SIZE]
        remaining = remaining[HPL_CHUNK_SIZE + 1:]

        yield chunk


def convert_from_hpl(palette_path, color_size):
    img_side_len = color_size * PALETTE_SQUARE_SIZE

    with open(palette_path, "rb") as hpl_fp:
        data = hpl_fp.read()
        _, color_data = data.split(HPAL_HEADER)

    # Create our raw palette data.
    palette = b"".join(_remove_0xff(color_data))

    out = palette_path.replace(".hpl", ".png")

    # We create a "P" image as that is a palette image. This will create a PNG
    # with a palette, meaning we can pass this image to `convert_to_hpl` and it will work.
    with Image.new("P", (img_side_len, img_side_len)) as image_fp:
        image_fp.putpalette(palette[::-1])
        d = ImageDraw.Draw(image_fp)

        # Our palette will have 256 colors max. We draw this in image form as a 16x16 square of "pixels".
        # The pixel size is determined by `color_size`.
        x = 0
        y = 0

        # Iterate over all 256 colors of the palette.
        for palette_index in range(HPL_MAX_COLORS):
            # Honestly? This might be jank. But `image_fp.putpalette` creates a raw mode palette.
            # When we go to draw the rectangle in a few lines, calling out a fill looks into this colors
            # dict that is set on the palette and it ignores the raw data we have set in it, and actually
            # will overwrite that data for some reason.
            # PIL wants the index of this dict to be a tuple so we just make it our XY index of this color square.
            # The value is our palette index and NOT THE ACTUAL RGB VALUE, as the RGB value will be grabbed
            # from the palette (I believe it's a mapping sort of deal).
            image_fp.palette.colors[(x, y)] = palette_index

            # Draw a square that is a single color from the palette.
            dim = [((x * color_size), (y * color_size)), ((x * color_size) + color_size, (y * color_size) + color_size)]
            d.rectangle(dim, fill=(x, y))

            # Move to the next column in the row. Once we reach the end of the row we head back to column 0.
            x += 1
            x %= PALETTE_SQUARE_SIZE
            # Once we have filled a row of 16 we move to the next row.
            if x == 0:
                y += 1

        image_fp.save(out)
