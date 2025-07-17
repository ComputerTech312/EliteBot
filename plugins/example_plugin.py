#!/usr/bin/env python3

import sys
import os

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from src.plugin_base import PluginBase


class ExamplePlugin(PluginBase):
    """
    Example plugin demonstrating basic functionality
    """
    
    def __init__(self, bot_instance):
        super().__init__(bot_instance)
        self.name = "Example Plugin"
        self.version = "1.0.0"
        self.description = "An example plugin showing basic functionality"
        
    async def handle_message(self, source_nick, channel, message):
        """
        Handle incoming messages
        """
        # React to messages containing "hello"
        if "hello" in message.lower():
            await self.bot.privmsg(channel, f"Hello {source_nick}! 👋")
    
    async def handle_command(self, source_nick, channel, cmd, cmd_args):
        """
        Handle bot commands
        """
        if cmd.lower() == 'example':
            await self.bot.privmsg(channel, f"{source_nick}: This is an example command!")
            return True
        elif cmd.lower() == 'echo' and cmd_args:
            message = ' '.join(cmd_args)
            await self.bot.privmsg(channel, f"{source_nick}: {message}")
            return True
        
        return False
    
    def on_connect(self):
        """
        Called when the bot connects
        """
        self.bot.logger.info(f"{self.name} loaded successfully")
    
    def on_disconnect(self):
        """
        Called when the bot disconnects
        """
        self.bot.logger.info(f"{self.name} unloaded")
