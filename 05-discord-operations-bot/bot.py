import logging
from dotenv import load_dotenv
from operations.config import Config
from operations.discord_app import OperationsClient


def main():
    load_dotenv()
    logging.basicConfig(level=logging.INFO)
    config = Config.from_env()
    OperationsClient(config).run(config.token, log_handler=None)


if __name__ == '__main__':
    main()
