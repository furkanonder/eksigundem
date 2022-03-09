from colorama import Fore
from typing import Any

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


def cprint(color:str, *args:Any, **kwargs:Any)->None:
    kwargs["sep"] = ""
    print(colors[color], *args, Fore.RESET, **kwargs)
