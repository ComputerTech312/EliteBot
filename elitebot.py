#!/usr/bin/env python3

import asyncio
import os
import sys

from src.bot import Bot


def main():
    os.makedirs('data', exist_ok=True)

    if len(sys.argv) < 2:
        print('Usage: python elitebot.py <config_file>')
        sys.exit(1)

    config_file = sys.argv[1]
    try:
        bot = Bot(config_file)
    except FileNotFoundError as e:
        print(f'Config file not found: {e}')
        sys.exit(1)
    except Exception as e:
        print(f'Error loading bot: {e}')
        sys.exit(1)

    try:
        print('EliteBot started successfully!')
        asyncio.run(bot.start())
    except KeyboardInterrupt:
        print('\nShutting down EliteBot...')
        # Create a new event loop for shutdown if needed
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        loop.run_until_complete(bot.shutdown())
        print('EliteBot has been stopped.')
    except Exception as e:
        print(f'Error starting EliteBot: {e}')
        sys.exit(1)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('\nEliteBot has been stopped.')
    except Exception as e:
        print(f'An unexpected error occurred: {e}')
        sys.exit(1)
