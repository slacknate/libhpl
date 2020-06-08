import os
import argparse

from .hpl import convert_to_hpl, convert_from_hpl

DEF_COLOR_SQUARE_SIZE = 20


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

    args, _ = parser.parse_known_args()

    if getattr(args, "image", None) is not None:
        convert_to_hpal(args.image)

    elif getattr(args, "palette", None) is not None:
        convert_from_hpal(args.palette, args.size)


if __name__ == "__main__":
    main()
