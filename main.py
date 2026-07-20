"""Railway entry point — delegates to discord-bot/bot.py main() function.

This is the startup script that Railway uses when deploying style-bot.
It imports and runs the Discord bot's main function, which keeps the bot
running continuously and listening for Discord events.
"""

import sys
import os

# Add discord-bot directory to Python path so we can import its modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "discord-bot"))

from bot import main

if __name__ == "__main__":
    main()

