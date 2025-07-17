# EliteBot Plugins

This directory contains plugins for EliteBot. Plugins extend the bot's functionality by handling messages and commands.

## Plugin Structure

All plugins must inherit from `PluginBase` and implement the following methods:

### Required Methods

- `__init__(self, bot_instance)`: Initialize the plugin
- `handle_message(self, source_nick, channel, message)`: Process incoming messages
- `handle_command(self, source_nick, channel, cmd, cmd_args)`: Process bot commands (return True if handled)

### Optional Methods

- `on_connect(self)`: Called when bot connects to IRC
- `on_disconnect(self)`: Called when bot disconnects from IRC

## Example Plugin

See `example_plugin.py` for a basic plugin implementation.

## Creating a Plugin

1. Create a new `.py` file in this directory
2. Import `PluginBase` from `src.plugin_base`
3. Create a class that inherits from `PluginBase`
4. Implement the required methods
5. Restart the bot to load your plugin

## Available Bot Methods

Your plugin can access the bot instance through `self.bot`:

- `await self.bot.privmsg(target, message)`: Send a message
- `await self.bot.notice(target, message)`: Send a notice
- `await self.bot.action(target, message)`: Send an action (/me)
- `await self.bot.ircsend(raw_command)`: Send raw IRC command
- `self.bot.logger`: Access the logging system
- `self.bot.config`: Access bot configuration
- `self.bot.channel_manager`: Access channel management

## Plugin Loading

Plugins are automatically loaded when the bot starts. If a plugin fails to load, the error will be logged and the bot will continue without that plugin.
