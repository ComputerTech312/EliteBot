#!/usr/bin/env python3

import asyncio
import importlib.util
import inspect
import json
import os
import ssl
import sys

import yaml

from src.channel_manager import ChannelManager
from src.logger import Logger
from src.plugin_base import PluginBase
from src.sasl import handle_sasl, handle_authenticate, handle_903


class Bot:
    def __init__(self, config_file):
        self.config = self.load_config(config_file)
        self.validate_config(self.config)
        self.connection_string = self.config['Database'].get('ConnectionString')
        self.channel_manager = ChannelManager()
        self.logger = Logger('logs/elitebot.log')
        self.connected = False
        self.reader = None
        self.writer = None
        self.running = True
        self.plugins = []
        self.load_plugins()

    def validate_config(self, config):
        required_fields = [
            ['Connection', 'Port'],
            ['Connection', 'Hostname'],
            ['Connection', 'Nick'],
            ['Connection', 'Ident'],
            ['Connection', 'Name'],
            ['Database', 'ConnectionString']
        ]

        for field in required_fields:
            if not self.get_nested_config_value(config, field):
                raise ValueError(f'Missing required config field: {" -> ".join(field)}')

    def get_nested_config_value(self, config, keys):
        value = config
        for key in keys:
            value = value.get(key)
            if value is None:
                return None
        return value

    def load_plugins(self):
        self.plugins = []
        plugin_folder = './plugins'
        
        if not os.path.exists(plugin_folder):
            self.logger.warning(f"Plugin folder '{plugin_folder}' does not exist")
            return
        
        # Add plugin folder to Python path
        sys.path.insert(0, plugin_folder)
        
        try:
            for filename in os.listdir(plugin_folder):
                if filename.endswith('.py') and not filename.startswith('__'):
                    module_name = filename[:-3]  # Remove .py extension
                    try:
                        filepath = os.path.join(plugin_folder, filename)
                        spec = importlib.util.spec_from_file_location(module_name, filepath)
                        module = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(module)
                        
                        # Look for classes that inherit from PluginBase
                        for name, obj in inspect.getmembers(module):
                            if (inspect.isclass(obj) and 
                                issubclass(obj, PluginBase) and 
                                obj is not PluginBase):
                                try:
                                    plugin_instance = obj(self)
                                    self.plugins.append(plugin_instance)
                                    self.logger.info(f"Loaded plugin: {name}")
                                    
                                    # Call on_connect if method exists
                                    if hasattr(plugin_instance, 'on_connect'):
                                        plugin_instance.on_connect()
                                except Exception as e:
                                    self.logger.error(f"Error initializing plugin {name}: {e}")
                    except Exception as e:
                        self.logger.error(f"Error loading plugin {filename}: {e}")
        except Exception as e:
            self.logger.error(f"Error loading plugins: {e}")
        
        self.logger.info(f"Loaded {len(self.plugins)} plugins")

    def load_config(self, config_file):
        _, ext = os.path.splitext(config_file)
        try:
            with open(config_file, 'r') as file:
                if ext == '.json':
                    config = json.load(file)
                elif ext == '.yaml' or ext == '.yml':
                    config = yaml.safe_load(file)
                else:
                    raise ValueError(f'Unsupported file extension: {ext}')
        except FileNotFoundError as e:
            self.logger.error(f'Error loading config file: {e}')
            raise
        except (json.JSONDecodeError, yaml.YAMLError) as e:
            self.logger.error(f'Error parsing config file: {e}')
            raise
        return config

    def decode(self, bytes):
        for encoding in ['utf-8', 'latin1', 'iso-8859-1', 'cp1252']:
            try:
                return bytes.decode(encoding)
            except UnicodeDecodeError:
                continue
        self.logger.error('Could not decode byte string with any known encoding')
        return bytes.decode('utf-8', 'ignore')

    async def ircsend(self, msg):
        try:
            if msg != '':
                self.logger.info(f'Sending command: {msg}')
                self.writer.write(bytes(f'{msg}\r\n', 'UTF-8'))
                await self.writer.drain()
        except Exception as e:
            self.logger.error(f'Error sending IRC message: {e}')
            raise

    async def privmsg(self, target, msg):
        await self.ircsend(f'PRIVMSG {target} :{msg}')

    async def action(self, target, msg):
        await self.ircsend(f'PRIVMSG {target} :\x01ACTION {msg}\x01')

    async def notice(self, target, msg):
        await self.ircsend(f'NOTICE {target} :{msg}')

    async def handle_command(self, source_nick, channel, cmd, cmd_args):
        """
        Handle bot commands starting with &
        
        :param source_nick: Nick of the user who sent the command
        :param channel: Channel where the command was sent
        :param cmd: The command name
        :param cmd_args: List of command arguments
        """
        try:
            # Built-in commands
            if cmd.lower() == 'help':
                await self.privmsg(channel, f'{source_nick}: Available commands: help, version, ping, join, part')
            elif cmd.lower() == 'version':
                await self.privmsg(channel, f'{source_nick}: EliteBot v{self.config.get("VERSION", "1.0.0")}')
            elif cmd.lower() == 'ping':
                await self.privmsg(channel, f'{source_nick}: Pong!')
            elif cmd.lower() == 'join' and cmd_args:
                target_channel = cmd_args[0]
                if target_channel.startswith('#'):
                    await self.ircsend(f'JOIN {target_channel}')
                    self.channel_manager.save_channel(target_channel)
                    await self.privmsg(channel, f'{source_nick}: Joined {target_channel}')
                else:
                    await self.privmsg(channel, f'{source_nick}: Invalid channel name')
            elif cmd.lower() == 'part':
                if cmd_args:
                    target_channel = cmd_args[0]
                else:
                    target_channel = channel
                
                if target_channel.startswith('#'):
                    await self.ircsend(f'PART {target_channel}')
                    self.channel_manager.remove_channel(target_channel)
                    if target_channel != channel:
                        await self.privmsg(channel, f'{source_nick}: Left {target_channel}')
                else:
                    await self.privmsg(channel, f'{source_nick}: Invalid channel name')
            else:
                # Check if any plugin handles this command
                command_handled = False
                for plugin in self.plugins:
                    if hasattr(plugin, 'handle_command'):
                        result = await plugin.handle_command(source_nick, channel, cmd, cmd_args)
                        if result:
                            command_handled = True
                            break
                
                if not command_handled:
                    await self.privmsg(channel, f'{source_nick}: Unknown command: {cmd}')
        
        except Exception as e:
            self.logger.error(f'Error handling command "{cmd}": {e}')
            await self.privmsg(channel, f'{source_nick}: Error processing command')

    def parse_message(self, message):
        parts = message.split()
        if not parts:
            return None, None, []
        source = parts[0][1:] if parts[0].startswith(':') else None
        command = parts[1] if source else parts[0]
        args_start = 2 if source else 1
        args = []
        trailing_arg_start = None
        for i, part in enumerate(parts[args_start:], args_start):
            if part.startswith(':'):
                trailing_arg_start = i
                break
            else:
                args.append(part)
        if trailing_arg_start is not None:
            args.append(' '.join(parts[trailing_arg_start:])[1:])
        return source, command, args

    async def connect(self):
        try:
            ssl_context = None
            if str(self.config['Connection'].get('Port'))[:1] == '+':
                ssl_context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)  # Corrected here

            self.reader, self.writer = await asyncio.open_connection(
                self.config['Connection'].get('Hostname'),
                int(self.config['Connection'].get('Port')[1:]) if ssl_context else int(
                    self.config['Connection'].get('Port')),
                ssl=ssl_context
            )

            if self.config['SASL'].get('UseSASL'):
                await self.ircsend('CAP LS 302')
            await self.ircsend(f'NICK {self.config["Connection"].get("Nick")}')
            await self.ircsend(f'USER {self.config["Connection"].get("Ident")} * * :'
                               f'{self.config["Connection"].get("Name")}')
            if self.config['SASL'].get('UseSASL'):
                await self.ircsend('CAP REQ :sasl')
        except Exception as e:
            self.logger.error(f'Error establishing connection: {e}')
            self.connected = False
            return

    async def send_ping(self):
        while self.connected and self.running:
            await asyncio.sleep(60)
            if self.connected:
                try:
                    await self.ircsend(f'PING :{self.config["Connection"].get("Hostname")}')
                except Exception as e:
                    self.logger.error(f'Error sending ping: {e}')
                    self.connected = False
                    break

    async def shutdown(self):
        """
        Gracefully shutdown the bot
        """
        self.logger.info("Shutting down bot...")
        self.running = False
        
        # Call plugin disconnect handlers
        for plugin in self.plugins:
            try:
                if hasattr(plugin, 'on_disconnect'):
                    plugin.on_disconnect()
            except Exception as e:
                self.logger.error(f'Error in plugin {plugin.__class__.__name__} disconnect: {e}')
        
        # Send QUIT message if connected
        if self.connected and self.writer:
            try:
                await self.ircsend('QUIT :EliteBot shutting down')
                await asyncio.sleep(1)  # Give time for message to send
            except Exception as e:
                self.logger.error(f'Error sending QUIT message: {e}')
        
        # Close connection
        if self.writer:
            try:
                self.writer.close()
                await self.writer.wait_closed()
            except Exception as e:
                self.logger.error(f'Error closing connection: {e}')
        
        self.logger.info("Bot shutdown complete")
            
    async def start(self):
        ping_task = None
        reconnect_delay = 30  # Start with 30 second delay
        max_reconnect_delay = 300  # Maximum 5 minute delay
        
        while self.running:
            if not self.connected:
                try:
                    self.logger.info("Attempting to connect to IRC server...")
                    await self.connect()
                    self.connected = True
                    reconnect_delay = 30  # Reset delay on successful connection
                    self.logger.info("Successfully connected to IRC server")
                    
                    # Start the ping task after the bot has connected
                    if ping_task is None or ping_task.done():
                        ping_task = asyncio.create_task(self.send_ping())
                        
                except Exception as e:
                    self.logger.error(f'Connection error: {e}')
                    self.connected = False
                    self.logger.info(f'Retrying connection in {reconnect_delay} seconds...')
                    await asyncio.sleep(reconnect_delay)
                    # Exponential backoff with maximum delay
                    reconnect_delay = min(reconnect_delay * 2, max_reconnect_delay)
                    continue

            try:
                # Set a timeout for reading to avoid hanging indefinitely
                recvText = await asyncio.wait_for(self.reader.read(2048), timeout=300)
                
                if not recvText:
                    self.logger.warning("Received empty data, connection may be closed")
                    self.connected = False
                    continue

                ircmsg = self.decode(recvText)
                self.logger.debug(f'Raw IRC message: {ircmsg.strip()}')

                # Handle multiple messages in one packet
                if '\r\n' in ircmsg:
                    messages = ircmsg.split('\r\n')
                elif '\n' in ircmsg:
                    messages = ircmsg.split('\n')
                else:
                    messages = [ircmsg]

                for message in messages:
                    if message.strip():  # Only process non-empty messages
                        try:
                            await self.process_message(message.strip())
                        except Exception as e:
                            self.logger.error(f'Error processing message "{message}": {e}')
                            # Continue processing other messages
                            continue
                            
            except asyncio.TimeoutError:
                self.logger.warning("Read timeout, connection may be stale")
                self.connected = False
                continue
            except ConnectionResetError:
                self.logger.warning("Connection reset by peer")
                self.connected = False
                continue
            except Exception as e:
                self.logger.error(f'General error in main loop: {e}')
                self.connected = False
                await asyncio.sleep(5)  # Brief pause before retry
                continue

    async def process_message(self, message):
        """
        Process a single IRC message with proper error handling
        """
        try:
            source, command, args = self.parse_message(message)
            self.logger.debug(f'Parsed: source={source} | command={command} | args={args}')

            if not command:
                return

            match command:
                case 'CAP':
                    if len(args) >= 3 and args[1] == 'ACK' and 'sasl' in args[2]:
                        await handle_sasl(self.config, self.ircsend)
                        
                case 'PING':
                    nospoof = args[0][1:] if args[0].startswith(':') else args[0]
                    await self.ircsend(f'PONG :{nospoof}')
                    
                case 'PRIVMSG':
                    if len(args) >= 2:
                        channel, message_text = args[0], args[1]
                        source_nick = source.split('!')[0] if source else 'unknown'

                        # Handle commands
                        if message_text.startswith('&'):
                            cmd, *cmd_args = message_text[1:].split()
                            await self.handle_command(source_nick, channel, cmd, cmd_args)

                        # Handle CTCP VERSION
                        if message_text.startswith('\x01VERSION\x01'):
                            await self.ircsend(f'NOTICE {source_nick} :\x01VERSION EliteBot {self.config.get("VERSION", "1.0.0")}\x01')

                        # Pass message to plugins
                        for plugin in self.plugins:
                            try:
                                await plugin.handle_message(source_nick, channel, message_text)
                            except Exception as e:
                                self.logger.error(f'Error in plugin {plugin.__class__.__name__}: {e}')
                                
                case 'AUTHENTICATE':
                    await handle_authenticate(args, self.config, self.ircsend)
                    
                case 'INVITE':
                    if len(args) >= 2:
                        channel = args[1]
                        await self.ircsend(f'JOIN {channel}')
                        self.channel_manager.save_channel(channel)
                        self.logger.info(f'Auto-joined channel {channel} after invite')
                        
                case 'VERSION':
                    source_nick = source.split('!')[0] if source else 'unknown'
                    await self.ircsend(f'NOTICE {source_nick} :EliteBot v{self.config.get("VERSION", "1.0.0")}')
                    
                case '001':  # RPL_WELCOME - successful connection
                    self.logger.info('Successfully registered with IRC server')
                    # Auto-join channels
                    for channel in self.channel_manager.get_channels():
                        try:
                            await self.ircsend(f'JOIN {channel[1]}')
                            self.logger.info(f'Auto-joined channel: {channel[1]}')
                        except Exception as e:
                            self.logger.error(f'Error joining channel {channel[1]}: {e}')
                            
                case '903':  # RPL_SASLSUCCESS
                    await handle_903(self.ircsend)
                    
                case '904' | '905' | '906' | '907':  # SASL failure codes
                    self.logger.error(f'SASL authentication failed: {command}')
                    await self.ircsend('CAP END')  # Continue without SASL
                    
                case 'ERROR':
                    error_msg = args[0] if args else 'Unknown error'
                    self.logger.error(f'Server error: {error_msg}')
                    self.connected = False
                    
                case _:
                    # Log unknown commands for debugging
                    self.logger.debug(f'Unhandled command: {command} with args: {args}')
                    
        except Exception as e:
            self.logger.error(f'Error processing IRC message: {e}')
            raise


if __name__ == '__main__':
    try:
        bot = Bot(sys.argv[1])
        asyncio.run(bot.start())
    except KeyboardInterrupt:
        print('\nEliteBot has been stopped.')
    except Exception as e:
        print(f'An unexpected error occurred: {e}')
