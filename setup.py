from setuptools import setup, find_packages


setup(

    name="libhpl",
    version="0.0.1",
    url="https://github.com/slacknate/libhpl",
    description="A library for manipulating HPL color palettes via PNG.",
    packages=find_packages(include=["libhpl", "libhpl.*"]),
    install_requires=["Pillow==9.0.0"]
)
