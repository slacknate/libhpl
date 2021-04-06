import io
import os

from PIL import Image, ImageDraw

HPL_COLOR_SIZE = 3
HPL_MAX_COLORS = 256
PALETTE_SQUARE_SIZE = 16

HPAL_HEADER = (b"HPAL%\x01\x00\x00 \x04\x00\x00\x00\x01\x00\x00\x00\x00"
               b"\x00\x00\x00\x00\x00\x00\x01\x00\x00\x10\x00\x00\x00\x00")


def convert_to_hpl(image, out=None):
    """
    Convert a PNG image to an HPL palette file.

    Note that PNG images are not required to have a palette and
    PIL will complain about images that do not contain one (i.e. raise an exception).

    Original script by resnovae, slight tweak by Labryz.
    Cleaned up some by slacknate.
    """
    if out is None:
        if not isinstance(image, str):
            raise ValueError("Must provide an output path or fp when not supplying image via file path!")

        out = image.replace(".png", ".hpl")

    with Image.open(image) as image_fp:
        palette = image_fp.getdata().getpalette()

    with open(out, "wb") as hpl_fp:
        hpl_fp.write(HPAL_HEADER)

        # Iterate our palette data in reverse.
        remaining = palette[::-1]
        while remaining:
            # We grab 3 byte chunks as each of these is an RGB tuple.
            chunk = remaining[0:HPL_COLOR_SIZE]
            remaining = remaining[HPL_COLOR_SIZE:]

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
        chunk = remaining[0:HPL_COLOR_SIZE]
        remaining = remaining[HPL_COLOR_SIZE + 1:]

        yield chunk


def _read_hpl(palette):
    """
    Helper function to read HPL files and create a bytestring raw palette.
    """
    if isinstance(palette, str) and os.path.exists(palette):
        with open(palette, "rb") as hpl_fp:
            data = hpl_fp.read()

    elif isinstance(palette, io.BytesIO):
        data = palette.read()

    else:
        raise TypeError(f"Unsupported palette type {palette}!")

    _, color_data = data.split(HPAL_HEADER)
    return b"".join(_remove_0xff(color_data))[::-1]


def replace_palette(image, palette):
    """
    Do in-place palette swap of an existing image.
    """
    with Image.open(image, formats=("PNG",)) as image_fp:
        image_size = image_fp.size
        raw_img = image_fp.getdata()

    # If our image is provided via path then it is also our output path.
    if isinstance(image, str) and os.path.exists(image):
        out = image

    # If our image has been provided via BytesIO we need to seek to the beginning before writing
    # out the new PNG data or we will most definitely corrupt the PNG integrity.
    elif isinstance(image, io.BytesIO):
        image.seek(0)
        out = image

    else:
        raise TypeError(f"Unsupported image type {image}!")

    palette = _read_hpl(palette)

    with Image.new("P", image_size) as image_fp:
        image_fp.im = raw_img
        image_fp.putpalette(palette)
        image_fp.load()
        image_fp.save(out, format="PNG")


def convert_from_hpl(palette, color_size, out=None):
    """
    Create a PNG from an HPL palette file.
    The image created is a visual representation of the contents of the palette.
    """
    img_side_len = color_size * PALETTE_SQUARE_SIZE

    if out is None:
        if not isinstance(palette, str):
            raise ValueError("Must provide an output path or fp when not supplying palette via file path!")

        out = palette.replace(".hpl", ".png")

    palette_data = _read_hpl(palette)

    # We create a "P" image as that is a palette image. This will create a PNG
    # with a palette, meaning we can pass this image to `convert_to_hpl` and it will work.
    with Image.new("P", (img_side_len, img_side_len)) as image_fp:
        image_fp.putpalette(palette_data)
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

        image_fp.save(out, format="PNG")


def get_palette_index(image, pixel):
    """
    Get the palette index for the given pixel. The pixel is provided as an (x, y) tuple.
    The `getpixel` method returns an integer value that is a color offset (i.e. a value from 0-255)
    and we convert this value to an (x, y) tuple that maps into a 16 x 16 square of colors.
    """
    with Image.open(image, formats=("PNG",)) as image_fp:
        image_fp.load()
        color_offset = image_fp.getpixel(pixel)
        palette_x = color_offset % PALETTE_SQUARE_SIZE
        palette_y = int((color_offset - palette_x) / PALETTE_SQUARE_SIZE)
        return palette_x, palette_y


def get_index_color(image, palette_index):
    """
    Return the RGB tuple of the color at the palette index `palette_index`.
    The index is the (x, y) coordinate of a 16 x 16 square of colors.
    These colors are actually linear in memory/on disk so we have to convert
    the index to a color offset and then to a byte offset.
    """
    x, y = palette_index
    color_offset = y * PALETTE_SQUARE_SIZE + x
    byte_offset = color_offset * HPL_COLOR_SIZE

    with Image.open(image, formats=("PNG",)) as image_fp:
        image_fp.load()
        palette = image_fp.getdata().getpalette()
        
        color_data = palette[byte_offset:byte_offset+HPL_COLOR_SIZE]
        return tuple(color_data)


def set_index_color(image, palette_index, color_tuple):
    """
    Set the color for the given PNG palette image for the given palette index.
    The index is the (x, y) coordinate of a 16 x 16 square of colors.
    These colors are actually linear in memory/on disk so we have to convert
    the index to a color offset and then to a byte offset.
    """
    x, y = palette_index
    color_offset = y * PALETTE_SQUARE_SIZE + x
    byte_offset = color_offset * HPL_COLOR_SIZE

    with Image.open(image, formats=("PNG",)) as image_fp:
        image_fp.load()
        palette = image_fp.getdata().getpalette()

        before = palette[:byte_offset]
        after = palette[byte_offset+HPL_COLOR_SIZE:]
        new_palette = before + bytes(color_tuple) + after

        # If our image has been provided via BytesIO we need to seek to the beginning before writing
        # out the new PNG data or we will most definitely corrupt the PNG integrity.
        if isinstance(image, io.BytesIO):
            image.seek(0)

        image_fp.putpalette(new_palette)
        image_fp.save(image, format="PNG")
