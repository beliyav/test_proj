import os
import os.path

import asyncio

from server.app import Application
from server.utils import load_conf


def main():
    config_path = os.path.join(os.getcwd(), 'config.yml')
    config = load_conf(config_path)
    app = Application(config)

    app.run()


if __name__ == "__main__":
    main()