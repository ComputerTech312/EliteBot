import os
from datetime import datetime

import colorama


class Logger:
    def __init__(self, log_file: str, datefmt: str = '%m/%d/%Y %I:%M:%S %p'):
        colorama.init()
        self.log_file = log_file
        self.datefmt = datefmt

        os.makedirs(os.path.dirname(log_file), exist_ok=True)

    def log(self, level, message):
        asctime = datetime.now().strftime(self.datefmt)

        match level:
            case 'debug':
                print(f'\033[92m[{asctime}] - {message}\033[39m')
            case 'info':
                print(f'\033[96m[{asctime}] - {message}\033[39m')
            case 'warn' | 'warning':
                print(f'\033[93m[{asctime}] - {message}\033[39m')
            case 'error':
                print(f'\033[91m[{asctime}] - {message}\033[39m')
            case _:
                pass  # just ignore it.

    def debug(self, message):
        self.log('debug', message)

    def info(self, message):
        self.log('info', message)

    def warning(self, message):
        self.log('warning', message)

    def error(self, message):
        self.log('error', message)
