from pathlib import Path

from setuptools import setup

CURRENT_DIR = Path(__file__).parent


def get_long_description():
    readme_md = CURRENT_DIR / "README.md"
    with open(readme_md, encoding="utf8") as ld_file:
        return ld_file.read()


setup(
    name="eksi",
    version="0.3.0",
    description="Komut satırında Ekşisözlük!",
    keywords=["ekşisözlük", "ekşi", "eksi", "sözlük"],
    long_description=get_long_description(),
    long_description_content_type="text/markdown",
    author="Furkan Onder",
    author_email="furkanonder@protonmail.com",
    url="https://github.com/furkanonder/eksigundem/",
    license="MIT",
    python_requires=">=3.7",
    packages=["eksi"],
    install_requires=[
        "beautifulsoup4==4.9.3",
    ],
    extras_require={},
    zip_safe=False,
    include_package_data=False,
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Topic :: Utilities",
        "Environment :: Console",
        "Operating System :: OS Independent",
    ],
    entry_points={
        "console_scripts": [
            "eksi = eksi.__main__:main",
        ]
    },
)
