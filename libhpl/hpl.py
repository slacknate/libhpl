import io
import os

from PIL import Image, ImageDraw

RAW_A_SIZE = 1
RAW_RGB_SIZE = 3
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
        # Get color information from the palette.
        rgb = image_fp.getdata().getpalette()
        # Get transparency information from the tRNS header.
        alpha = image_fp.info["transparency"]

    if len(rgb) != len(alpha) * 3:
        raise ValueError("Mismatch between RGB and transparency data!")

    with open(out, "wb") as hpl_fp:
        hpl_fp.write(HPAL_HEADER)

        # Iterate our palette data in reverse.
        remaining_palette = rgb[::-1]
        remaining_alpha = alpha[::-1]

        while remaining_palette:
            color = remaining_palette[:RAW_RGB_SIZE]
            alpha = remaining_alpha[:RAW_A_SIZE]

            remaining_palette = remaining_palette[RAW_RGB_SIZE:]
            remaining_alpha = remaining_alpha[RAW_A_SIZE:]

            hpl_fp.write(color + alpha)


def _parse_color_data(color_data):
    """
    Parse the color data present in our HPL palette.
    Separate the RGB and Alpha channels as we cannot create a palette image with an alpha channel
    in the palette data. The transparency information needs to be included in a tRNS header.
    """
    palette_data = bytearray()
    alpha_data = bytearray()
    remaining = color_data

    while remaining:
        rgb = remaining[:RAW_RGB_SIZE]
        remaining = remaining[RAW_RGB_SIZE:]

        alpha = remaining[:RAW_A_SIZE]
        remaining = remaining[RAW_A_SIZE:]

        palette_data += rgb
        alpha_data += alpha

    if len(palette_data) != len(alpha_data) * 3:
        raise ValueError("Mismatch between RGB and transparency data!")

    return palette_data[::-1], alpha_data[::-1]


def _read_hpl(palette):
    """
    Helper function to read HPL files and create raw palette data.
    """
    if isinstance(palette, str) and os.path.exists(palette):
        with open(palette, "rb") as hpl_fp:
            hpl_contents = hpl_fp.read()

    elif isinstance(palette, str) and not os.path.exists(palette):
        raise ValueError(f"Palette {palette} does not exist!")

    elif isinstance(palette, io.BytesIO):
        hpl_contents = palette.read()

    else:
        raise TypeError(f"Unsupported palette type {palette}!")

    if not hpl_contents.startswith(HPAL_HEADER):
        raise ValueError("Not a valid HPL file!")

    remaining = hpl_contents[len(HPAL_HEADER):]
    palette_data, alpha_data = _parse_color_data(remaining)

    return palette_data, alpha_data


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

    palette, alpha = _read_hpl(palette)

    with Image.new("P", image_size) as image_fp:
        # Copy the image data from the source PNG.
        image_fp.im = raw_img
        # Set the palette from the provided HPL file.
        image_fp.putpalette(palette)

        # Reload the image so all the Pillow internals are up to date.
        image_fp.load()

        # Setting the transparency kwarg to our alpha raw data creates a tRNS header.
        # The kwarg expects an instance of `bytes()`.
        image_fp.save(out, format="PNG", transparency=bytes(alpha))


def convert_from_hpl(hpl_palette, color_size, out=None):
    """
    Create a PNG from an HPL palette file.
    The image created is a visual representation of the contents of the palette.
    """
    img_side_len = color_size * PALETTE_SQUARE_SIZE

    if out is None:
        if not isinstance(hpl_palette, str):
            raise ValueError("Must provide an output path or fp when not supplying palette via file path!")

        out = hpl_palette.replace(".hpl", ".png")

    palette, alpha = _read_hpl(hpl_palette)

    # We create a "P" image as that is a palette image. This will create a PNG
    # with a palette, meaning we can pass this image to `convert_to_hpl` and it will work.
    with Image.new("P", (img_side_len, img_side_len)) as image_fp:
        image_fp.putpalette(palette)
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

        # Setting the transparency kwarg to our alpha raw data creates a tRNS header.
        # The kwarg expects an instance of `bytes()`.
        image_fp.save(out, format="PNG", transparency=bytes(alpha))


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
    byte_offset = color_offset * RAW_RGB_SIZE

    with Image.open(image, formats=("PNG",)) as image_fp:
        image_fp.load()

        palette = image_fp.getdata().getpalette()
        
        color_data = palette[byte_offset:byte_offset+RAW_RGB_SIZE]
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
    byte_offset = color_offset * RAW_RGB_SIZE

    with Image.open(image, formats=("PNG",)) as image_fp:
        image_fp.load()

        # Get color data from the palette.
        palette = image_fp.getdata().getpalette()
        # Get transparency information from the tRNS header.
        alpha = image_fp.info["transparency"]

        before = palette[:byte_offset]
        after = palette[byte_offset+RAW_RGB_SIZE:]
        new_palette = before + bytes(color_tuple) + after

        # If our image has been provided via BytesIO we need to seek to the beginning before writing
        # out the new PNG data or we will most definitely corrupt the PNG integrity.
        if isinstance(image, io.BytesIO):
            image.seek(0)

        image_fp.putpalette(new_palette)
        # Setting the transparency kwarg to our alpha raw data creates a tRNS header.
        # We do this to ensure the transparency is preserved, although it is likely not necessary
        # as we already have a tRNS header present from the source image.
        image_fp.save(image, format="PNG", transparency=alpha)
