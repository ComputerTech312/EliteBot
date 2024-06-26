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
        for filename in os.listdir(plugin_folder):
            if filename.endswith('.py'):
                filepath = os.path.join(plugin_folder, filename)
                spec = importlib.util.spec_from_file_location('module.name', filepath)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                for name, obj in inspect.getmembers(module):
                    if inspect.isclass(obj) and issubclass(obj, PluginBase) and obj is not PluginBase:
                        plugin_instance = obj(self)
                        self.plugins.append(plugin_instance)

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
        while True:
            await asyncio.sleep(60)
            await self.ircsend(f'PING :{self.config["Connection"].get("Hostname")}')
            
    async def start(self):
        ping_task = None
        while True:
            if not self.connected:
                try:
                    await self.connect()
                    self.connected = True
                    # Start the ping task after the bot has connected
                    if ping_task is None or ping_task.done():
                        ping_task = asyncio.create_task(self.send_ping())
                except Exception as e:
                    self.logger.error(f'Connection error: {e}')
                    await asyncio.sleep(60)
                    continue

            try:
                recvText = await self.reader.read(2048)
                if not recvText:
                    self.connected = False
                    continue

                ircmsg = self.decode(recvText)

                if '\r\n' in ircmsg:
                    messages = ircmsg.split('\r\n')
                elif '\n' in ircmsg:
                    messages = ircmsg.split('\n')
                else:
                    messages = [ircmsg]  # If no newline characters, treat the whole message as a single message

                for message in messages:
                    if message:  # Check if message is not empty
                        source, command, args = self.parse_message(message)
                        self.logger.debug(f'Received: source: {source} | command: {command} | args: {args}')

                match command:
                    case 'CAP':
                        if args[1] == 'ACK' and 'sasl' in args[2]:
                            await handle_sasl(self.config, self.ircsend)
                    case 'PING':
                        nospoof = args[0][1:] if args[0].startswith(':') else args[0]
                        await self.ircsend(f'PONG :{nospoof}')
                        continue
                    case 'PRIVMSG':
                        channel, message = args[0], args[1]
                        source_nick = source.split('!')[0]

                        if message.startswith('&'):
                            cmd, *cmd_args = message[1:].split()
                            self.handle_command(source_nick, channel, cmd, cmd_args)

                        if args[1].startswith('\x01VERSION\x01'):
                            source_nick = source.split('!')[0]
                            await self.ircsend(f'NOTICE {source_nick} :\x01VERSION EliteBot 0.1\x01')

                        for plugin in self.plugins:
                            await plugin.handle_message(source_nick, channel, message)
                    case 'AUTHENTICATE':
                        await handle_authenticate(args, self.config, self.ircsend)
                    case 'INVITE':
                        channel = args[1]
                        await self.ircsend(f'JOIN {channel}')
                        self.channel_manager.save_channel(channel)
                    case 'VERSION':
                        await self.ircsend(f'NOTICE {source_nick} :I am a bot version 1.0.0')
                    case '001':
                        for channel in self.channel_manager.get_channels():
                            await self.ircsend(f'JOIN {channel[1]}')
                    case '903':
                        await handle_903(self.ircsend)
                    case _:
                        continue
            except Exception as e:
                self.logger.error(f'General error: {e}')
                self.connected = False


if __name__ == '__main__':
    try:
        bot = Bot(sys.argv[1])
        asyncio.run(bot.start())
    except KeyboardInterrupt:
        print('\nEliteBot has been stopped.')
    except Exception as e:
        print(f'An unexpected error occurred: {e}')
