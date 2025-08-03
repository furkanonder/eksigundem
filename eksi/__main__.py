import argparse
import sys

from eksi import __version__
from eksi.color import RED, YELLOW, set_color
from eksi.eksi import Eksi, EksiError


def main() -> None:
    parser = argparse.ArgumentParser(description="Komut satırında Ekşi Sözlük!")
    parser.add_argument("-v", "--versiyon", action="version", version=__version__)
    parser.add_argument(
        "-b",
        "--baslik_sayisi",
        type=int,
        default=50,
        choices=range(1, 51),
        help="Gösterilecek başlık sayısı",
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
        print(set_color(YELLOW, "Bu bir hata ise, lütfen GitHub'da issue açın."))
        sys.exit(1)


if __name__ == "__main__":
    main()
