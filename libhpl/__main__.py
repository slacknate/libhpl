import os
import argparse

from .hpl import PNGPalette, PNGPaletteImage

DEF_COLOR_SQUARE_SIZE = 20


def convert_to_hpl(image_path):
    palette = PNGPalette(0)
    palette.load_png(image_path)
    palette.save_hpl(image_path.replace(".png", ".hpl"))


def convert_from_hpl(hpl_path, size):
    palette = PNGPalette(size)
    palette.load_hpl(hpl_path)
    palette.save_png(hpl_path.replace(".hpl", ".png"))


def replace_palette(image_path, hpl_path):
    palette = PNGPaletteImage()
    palette.load_hpl(hpl_path)
    palette.load_png(image_path)
    palette.save_png(image_path)


def abs_path(value):
    value = os.path.abspath(value)

    if not os.path.exists(value):
        raise argparse.ArgumentError("Invalid file path! Does not exist!")

    return value


def main():
    parser = argparse.ArgumentParser("hpl")
    subparsers = parser.add_subparsers(title="commands")

    frompng = subparsers.add_parser("frompng")
    frompng.add_argument(dest="image", type=abs_path, help="Image input path.")

    topng = subparsers.add_parser("topng")
    topng.add_argument(dest="palette", type=abs_path, help="Palette input path.")
    topng.add_argument("--size", "-s", dest="size", type=int,
                       default=DEF_COLOR_SQUARE_SIZE, help="Size of color blocks in pixels.")

    newpal = subparsers.add_parser("newpal")
    newpal.add_argument(dest="image", type=abs_path, help="Image input path.")
    newpal.add_argument(dest="palette", type=abs_path, help="Palette input path.")

    args, _ = parser.parse_known_args()

    image = getattr(args, "image", None)
    palette = getattr(args, "palette", None)

    if image is not None and palette is None:
        convert_to_hpl(args.image)

    elif image is None and palette is not None:
        convert_from_hpl(args.palette, args.size)

    elif image is not None and palette is not None:
        replace_palette(image, palette)


if __name__ == "__main__":
    main()
