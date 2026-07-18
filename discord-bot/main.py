"""Railway entry point — delegates to bot.main().

Railway uses this file (python main.py) while the Replit workflow
continues to run bot.py directly.  Both point to the same logic.
"""
from bot import main

if __name__ == "__main__":
    main()
