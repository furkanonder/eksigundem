import argparse

from eksi.eksi import Eksi


def main():
    parser = argparse.ArgumentParser(
        description="Komut satırında Ekşi Sözlük!"
    )
    parser.add_argument("-v", "--versiyon", action="version", version="0.3.0")
    parser.add_argument(
        "-b",
        "--baslik",
        type=int,
        choices=range(1, 51),
        help="Gösterilecek başlık sayısı",
    )
    args = parser.parse_args()
    eksi = Eksi()
    eksi.main(args.baslik)


if __name__ == "__main__":
    main()
