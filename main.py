import os
os.chdir(os.path.dirname(__file__))
from gateio_new_coins_announcements_bot.main import main

if __name__ == "__main__":
    # TODO: refactor this main call
    main()
