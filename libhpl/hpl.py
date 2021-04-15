import io
import os
import contextlib

from PIL import Image, ImageDraw

RAW_RGBA_SIZE = 4  # FIXME
RAW_RGB_SIZE = 3
RAW_A_SIZE = 1

HPL_MAX_COLORS = 256
PALETTE_SQUARE_SIZE = 16

HPAL_HEADER = (b"HPAL%\x01\x00\x00 \x04\x00\x00\x00\x01\x00\x00\x00\x00"
               b"\x00\x00\x00\x00\x00\x00\x01\x00\x00\x10\x00\x00\x00\x00")


@contextlib.contextmanager
def output_palette(hpl_output):
    """
    Helper context manager that either wraps `open()` or simply yields an `io.BytesIO`.
    Also provides basic type validation.
    """
    if isinstance(hpl_output, str):
        with open(hpl_output, "wb") as hpl_fp:
            yield hpl_fp

    elif isinstance(hpl_output, io.BytesIO):
        yield hpl_output

    else:
        raise TypeError(f"Unsupported output palette type {hpl_output}!")


def _parse_color_data(color_data):
    """
    Parse the color data present in our HPL palette.
    Separate the RGB and Alpha channels as we cannot create a palette image with an alpha channel
    in the palette data. The transparency information needs to be included in a tRNS header.
    """
    num_colors = len(color_data) // (RAW_RGB_SIZE + RAW_A_SIZE)
    if num_colors > HPL_MAX_COLORS:
        raise ValueError(f"Palette has {num_colors} colors but HPL palettes support up to {HPL_MAX_COLORS}!")

    rgba = bytearray()

    # We flip the palette data for compatibility with PNG palette images.
    # Note that HPL palette files store there color data in the format BGRA.
    # This is important and we need to remember this in `_load_hpl`.
    remaining_argb = color_data[::-1]

    while remaining_argb:
        a = remaining_argb[:RAW_A_SIZE]
        remaining_argb = remaining_argb[RAW_A_SIZE:]

        rgb = remaining_argb[:RAW_RGB_SIZE]
        remaining_argb = remaining_argb[RAW_RGB_SIZE:]

        rgba += rgb + a

    return rgba


def _load_hpl(hpl_input):
    """
    Helper function to read HPL files and create raw palette data.
    """
    if isinstance(hpl_input, str) and os.path.exists(hpl_input):
        with open(hpl_input, "rb") as hpl_fp:
            hpl_contents = hpl_fp.read()

    elif isinstance(hpl_input, str) and not os.path.exists(hpl_input):
        raise ValueError(f"Palette {hpl_input} does not exist!")

    elif isinstance(hpl_input, io.BytesIO):
        hpl_contents = hpl_input.read()

    else:
        raise TypeError(f"Unsupported palette type {hpl_input}!")

    if not hpl_contents.startswith(HPAL_HEADER):
        raise ValueError("Not a valid HPL file!")

    remaining = hpl_contents[len(HPAL_HEADER):]
    rgba = _parse_color_data(remaining)

    return rgba


def _save_hpl(rgba, hpl_output):
    """
    Create a valid HPL file from raw RGB and Alpha channel data.
    """
    num_colors = len(rgba) // (RAW_RGB_SIZE + RAW_A_SIZE)
    if num_colors > HPL_MAX_COLORS:
        raise ValueError(f"Palette has {num_colors} colors but HPL palettes support up to {HPL_MAX_COLORS}!")

    if not isinstance(hpl_output, (str, io.BytesIO)):
        raise TypeError(f"Unsupported output type {hpl_output}!")

    with output_palette(hpl_output) as hpl_fp:
        hpl_fp.write(HPAL_HEADER)

        # Iterate our palette data in reverse.
        # We have previously flipped the palette data from an HPL file we read or
        # we read the data from a PNG palette image.
        remaining_abgr = rgba[::-1]

        # Note that we convert ABGR to BGRA before writing it to our output.
        while remaining_abgr:
            a = remaining_abgr[:RAW_A_SIZE]
            remaining_abgr = remaining_abgr[RAW_A_SIZE:]

            bgr = remaining_abgr[:RAW_RGB_SIZE]
            remaining_abgr = remaining_abgr[RAW_RGB_SIZE:]

            bgra = bgr + a
            hpl_fp.write(bgra)


def _index_to_offset(index):
    """
    Convert the given palette index into a byte offset we can
    use to index into the RGBA array that describes our palette data.
    """
    if not isinstance(index, (int, tuple)):
        raise TypeError(f"Unsupported palette index type {index}!")

    # If we have a tuple we need to calculate the color offset as if
    # we are given the (x, y) coordinates of a 16x16 2D array.
    if isinstance(index, tuple):
        x, y = index
        color_offset = y * PALETTE_SQUARE_SIZE + x

    # Otherwise we were given the index directly as an integer.
    else:
        color_offset = index

    return color_offset * RAW_RGBA_SIZE


class HPLPalette:
    """
    A raw palette class that directly manipulates RGBA data from HPL palettes..
    """
    def __init__(self):
        self.rgba = bytearray()

    def load_hpl(self, hpl_input):
        """
        Read an HPL file and store the palette.
        """
        self.rgba = _load_hpl(hpl_input)

    def save_hpl(self, hpl_output):
        """
        Write out an HPL palette file based on our raw palette.
        """
        if not self.rgba:
            raise ValueError("No palette has been loaded!")

        _save_hpl(self.rgba, hpl_output)

    def _get_index_color(self, index):
        """
        Helper method for a common implementation between
        both `get_index_color` and `get_index_color_range`.
        """
        rgba_offset = _index_to_offset(index)
        return self.rgba[rgba_offset:rgba_offset+RAW_RGBA_SIZE]

    def get_index_color(self, index):
        """
        Get the color in the palette at the given index.
        """
        if not self.rgba:
            raise ValueError("No palette has been loaded!")

        return self._get_index_color(index)

    def get_index_color_range(self, *indices):
        """
        Get the colors in the palette at the given indices.
        """
        if not self.rgba:
            raise ValueError("No palette has been loaded!")

        color_range = []

        for index in indices:
            rgba = self._get_index_color(index)
            color_range.append(rgba)

        return color_range

    def _set_index_color(self, index, rgba):
        """
        Helper method for a common implementation between
        both `set_index_color` and `set_index_color_range`.
        """
        color_size = len(rgba)
        if color_size != RAW_RGBA_SIZE:
            raise ValueError("Colors must be provided as RGBA!")

        if not isinstance(rgba, (bytes, bytearray, tuple)):
            raise TypeError(f"Invalid color type {rgba!r}")

        if isinstance(rgba, tuple):
            rgba = bytes(rgba)

        rgba_offset = _index_to_offset(index)
        self.rgba[rgba_offset:rgba_offset+RAW_RGBA_SIZE] = rgba

    def set_index_color(self, index, rgba):
        """
        Set the color in the palette at the given index.
        """
        if not self.rgba:
            raise ValueError("No palette has been loaded!")

        self._set_index_color(index, rgba)

    def set_index_color_range(self, *index_colors):
        """
        Set the colors in the palette at the corresponding indices.
        """
        if not self.rgba:
            raise ValueError("No palette has been loaded!")

        for index, rgba in index_colors:
            self._set_index_color(index, rgba)


def _load_png(png_input):
    """
    Read a PNG image and return the image size, image data, and RGBA palette data.
    """
    rgba = bytearray()

    with Image.open(png_input) as image_fp:
        # Get image size.
        size = image_fp.size
        # Get image data.
        image = image_fp.getdata()
        # Get color information from the palette.
        rgb = image_fp.getdata().getpalette()
        # Get transparency information from the tRNS header.
        alpha = image_fp.info["transparency"]

    if len(rgb) != len(alpha) * RAW_RGB_SIZE:
        raise ValueError("Mismatch between RGB and transparency data!")

    remaining_rgb = rgb
    remaining_alpha = alpha

    while remaining_rgb:
        rgba += remaining_rgb[:RAW_RGB_SIZE]
        remaining_rgb = remaining_rgb[RAW_RGB_SIZE:]

        rgba += remaining_alpha[:RAW_A_SIZE]
        remaining_alpha = remaining_alpha[RAW_A_SIZE:]

    return size, image, rgba


def _save_png(rgba, png_output, image_size, draw_image):
    """
    Helper to create a PNG palette image with PIL and write out the contents.
    We accept a callback to draw image data so the two PNG-bases classes can
    provide different images.
    """
    if not callable(draw_image):
        raise TypeError("Draw image callback must be a callable object!")

    rgb = b""
    alpha = b""

    remaining_rgba = rgba

    while remaining_rgba:
        rgb += remaining_rgba[:RAW_RGB_SIZE]
        remaining_rgba = remaining_rgba[RAW_RGB_SIZE:]

        alpha += remaining_rgba[:RAW_A_SIZE]
        remaining_rgba = remaining_rgba[RAW_A_SIZE:]

    with Image.new("P", image_size) as image_fp:
        # Draw image information into our PIL Image.
        draw_image(image_fp)
        # Set the palette. This will come from an HPL file or another PNG palette image.
        # We intentionally set the palette after drawing the image in case the draw image callback
        # manages to overwrite any palette data.
        image_fp.putpalette(rgb)
        # Setting the transparency kwarg to our alpha raw data creates a tRNS header.
        # To be compatible with HPL files, a PNG palette image must use a tRNS header to describe transparency.
        # The kwarg expects an instance of `bytes()`.
        image_fp.save(png_output, format="PNG", transparency=alpha)


class PNGPalette(HPLPalette):
    """
    PNG palette class used to visualize HPL palettes with PNG images.
    """
    def __init__(self, pixel_size):
        super(PNGPalette, self).__init__()
        self.pixel_size = pixel_size

    def load_png(self, png_input):
        """
        Read a PNG image but only retain the palette data.
        We will be writing out a specific image when we invoke `save_png`.
        """
        _, __, self.rgba = _load_png(png_input)

    def save_png(self, png_output):
        """
        Write out the HPL palette visualization to the provided destination.
        """
        if not self.rgba:
            raise ValueError("No palette has been loaded!")

        length = self.pixel_size * PALETTE_SQUARE_SIZE
        _save_png(self.rgba, png_output, (length, length), self._draw_image)

    def _draw_image(self, image_fp):
        """
        Create the visualization of our HPL palette.
        We draw a 16x16 square of "pixels" representing each color in the palette.
        The size of each "pixel" is defined by `self.pixel_size`.
        """
        d = ImageDraw.Draw(image_fp)

        # The index of each "pixel" we draw in the image.
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

            x_offset = x * self.pixel_size
            y_offset = y * self.pixel_size

            # Draw a square that is a single color from the palette.
            dim = [(x_offset, y_offset), (x_offset + self.pixel_size, y_offset + self.pixel_size)]
            d.rectangle(dim, fill=(x, y))

            # Move to the next column in the row. Once we reach the end of the row we head back to column 0.
            x += 1
            x %= PALETTE_SQUARE_SIZE
            # Once we have filled a row of 16 we move to the next row.
            if x == 0:
                y += 1


class PNGPaletteImage(HPLPalette):
    """
    A PNG palette image class used for manipulating image data.
    """
    def __init__(self):
        super(PNGPaletteImage, self).__init__()
        self.image_size = (0, 0)
        self.image_data = b""

    def load_png(self, png_input):
        """
        Read a PNG and retain the image data.
        Optionally we can later modify the palette before writing out a copy.
        """
        self.image_size, self.image_data, _ = _load_png(png_input)

    def save_png(self, png_output):
        """
        Write out a copy of the source image.
        The palette may or may not have since been modified.
        """
        if not self.rgba:
            raise ValueError("No palette has been loaded!")

        _save_png(self.rgba, png_output, self.image_size, self._draw_image)

    def _draw_image(self, image_fp):
        """
        Copy the source image data to the new image we are writing out.
        """
        image_fp.im = self.image_data
        image_fp.load()

    def _get_palette_index(self, x, y):
        """
        Helper method for a common implementation between
        both `get_palette_index` and `get_palette_index_range`.
        """
        width, _ = self.image_size
        pixel_offset = y * width + x

        # Our image data is a bytearray of length (width * height) where each byte is a palette index (integer 0-255).
        palette_index_int = self.image_data[pixel_offset]

        palette_x = palette_index_int % PALETTE_SQUARE_SIZE
        palette_y = int((palette_index_int - palette_x) / PALETTE_SQUARE_SIZE)

        return palette_x, palette_y

    def get_palette_index(self, pixel):
        """
        Get the palette index for the given pixel. The pixel is provided as an (x, y) tuple.
        """
        if not self.image_data:
            raise ValueError("No image has been loaded!")

        return self._get_palette_index(*pixel)

    def get_palette_index_range(self, *pixels):
        """
        The palette indices of the given pixels. Each pixel is an (x, y) tuple.
        """
        palette_index_list = []

        for pixel in pixels:
            palette_index = self._get_palette_index(*pixel)
            palette_index_list.append(palette_index)

        return palette_index_list
