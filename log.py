import logging
from termcolor import colored

logging.basicConfig(format="[%(asctime)s]%(message)s", level=logging.INFO)
Loger = logging.getLogger("")


def info(data, status=False):
    Loger.info(f"{colored(data, 'blue')}")


def success(data, status=False):
    Loger.info(f"{colored(data, 'green')}")


def warning(data, status=False):
    Loger.warning(f"{colored(data, 'yellow')}")


def error(data, status=False):
    Loger.error(f"{colored(data, 'red')}")
