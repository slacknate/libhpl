import os
import unittest
import contextlib

from libhpl.hpl import HPLPalette, PNGPalette, PNGPaletteImage

TEST_DIRECTORY = os.path.abspath(os.path.dirname(__file__))


@contextlib.contextmanager
def test_file(file_name):
    file_path = os.path.join(TEST_DIRECTORY, file_name)

    try:
        yield file_path

    finally:
        os.remove(file_path)


def read_file(file_name):
    with open(file_name, "rb") as ref_fp:
        return ref_fp.read()


REF_PAL_HPL = os.path.join(TEST_DIRECTORY, "ref_pal.hpl")
REF_PAL_HPL_DATA = read_file(REF_PAL_HPL)

REF_PAL_PNG = os.path.join(TEST_DIRECTORY, "ref_pal.png")
REF_PAL_PNG_DATA = read_file(REF_PAL_PNG)

SRC_IMG = os.path.join(TEST_DIRECTORY, "src_img.png")
SRC_IMG_DATA = read_file(SRC_IMG)

REF_IMG = os.path.join(TEST_DIRECTORY, "ref_img.png")
REF_IMG_DATA = read_file(REF_IMG)


class HPLPaletteTests(unittest.TestCase):
    def setUp(self):
        self.palette = HPLPalette()

    def test_hpl_from_hpl(self):
        with test_file("hpl_from_hpl.hpl") as hpl_from_hpl:
            self.palette.load_hpl(REF_PAL_HPL)
            self.palette.save_hpl(hpl_from_hpl)
            hpl_from_hpl_data = read_file(hpl_from_hpl)
            self.assertEqual(hpl_from_hpl_data, REF_PAL_HPL_DATA)

    def test_get_index_color(self):
        self.palette.load_hpl(REF_PAL_HPL)
        palette_index = self.palette.get_index_color((15, 15))
        self.assertEqual(palette_index, b"\x00\xFF\x00\xFF")


class PNGPaletteTests(HPLPaletteTests):
    def setUp(self):
        self.palette = PNGPalette(20)

    def test_png_from_hpl(self):
        with test_file("png_from_hpl.png") as png_from_hpl:
            self.palette.load_hpl(REF_PAL_HPL)
            self.palette.save_png(png_from_hpl)
            png_from_hpl_data = read_file(png_from_hpl)
            self.assertEqual(png_from_hpl_data, REF_PAL_PNG_DATA)

    def test_hpl_from_png(self):
        with test_file("hpl_from_png.hpl") as hpl_from_png:
            self.palette.load_png(REF_PAL_PNG)
            self.palette.save_hpl(hpl_from_png)
            hpl_from_png_data = read_file(hpl_from_png)
            self.assertEqual(hpl_from_png_data, REF_PAL_HPL_DATA)

    def test_png_from_png(self):
        with test_file("png_from_png.png") as png_from_png:
            self.palette.load_png(REF_PAL_PNG)
            self.palette.save_png(png_from_png)
            png_from_png_data = read_file(png_from_png)
            self.assertEqual(png_from_png_data, REF_PAL_PNG_DATA)


class PNGPaletteImageTests(HPLPaletteTests):
    def setUp(self):
        self.palette = PNGPaletteImage()

    def test_palette_change(self):
        with test_file("img_from_src.png") as img_from_src:
            self.palette.load_png(SRC_IMG)
            self.palette.load_hpl(REF_PAL_HPL)
            self.palette.save_png(img_from_src)
            img_from_src_data = read_file(img_from_src)
            self.assertEqual(img_from_src_data, REF_IMG_DATA)

    def test_get_palette_index(self):
        self.palette.load_png(SRC_IMG)
        palette_index = self.palette.get_palette_index((0, 0))
        self.assertEqual(palette_index, (15, 15))
