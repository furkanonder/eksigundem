from colorama import Fore

colors = dict(
    red=Fore.RED,
    green=Fore.GREEN,
    yellow=Fore.YELLOW,
    blue=Fore.BLUE,
    magenta=Fore.MAGENTA,
    cyan=Fore.CYAN,
    white=Fore.WHITE,
    reset=Fore.RESET,
)


def cprint(color, *args, **kwargs):
    kwargs["sep"] = ""
    print(colors[color], *args, Fore.RESET, **kwargs)
