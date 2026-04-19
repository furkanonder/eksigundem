import argparse
import sys

from eksi import __version__
from eksi.client import EksiError
from eksi.color import RED, set_color
from eksi.eksi import Eksi


def _positive_int(value: str) -> int:
    n = int(value)
    if n < 1:
        raise argparse.ArgumentTypeError("Lütfen pozitif bir tamsayı girin.")
    return n


def main() -> None:
    parser = argparse.ArgumentParser(description="Komut satırında Ekşi Sözlük!")
    parser.add_argument("-v", "--versiyon", action="version", version=__version__)
    parser.add_argument(
        "-b",
        "--baslik_sayisi",
        type=_positive_int,
        default=10,
        help="Gösterilecek başlık sayısı (varsayılan: 10)",
    )

    try:
        args = parser.parse_args()
        eksi = Eksi(topic_count=args.baslik_sayisi)
        eksi.main()
    except EksiError as e:
        print(set_color(RED, f"Hata: {e}"))
        sys.exit(1)
    except (KeyboardInterrupt, EOFError):
        sys.exit(0)
    except Exception as e:  # noqa: BLE001
        print(set_color(RED, f"Beklenmeyen hata: {e}"))
        sys.exit(1)


if __name__ == "__main__":
    main()
