#!/usr/bin/env python3

import socket
import ssl
import time
import json
import yaml
import inspect
import sys
import os
import importlib.util
from src.channel_manager import ChannelManager
from src.logger import Logger
from src.plugin_base import PluginBase
from src.sasl import handle_sasl, handle_authenticate, handle_903

class Bot:
    def __init__(self, config_file):
        self.config = self.load_config(config_file)
        self.channel_manager = ChannelManager()
        self.logger = Logger('logs/elitebot.log')
        self.connected = False
        self.ircsock = None
        self.running = True
        self.plugins = []
        self.load_plugins()
        self.config = self.load_config(config_file)
        self.validate_config(self.config)

    def validate_config(self, config):
        required_fields = [
            ["Connection", "Port"],
            ["Connection", "Hostname"],
            ["Connection", "Nick"],
            ["Connection", "Ident"],
            ["Connection", "Name"],
            ["SASL", "UseSASL"]
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
        plugin_folder = "./plugins"
        for filename in os.listdir(plugin_folder):
            if filename.endswith('.py'):
                filepath = os.path.join(plugin_folder, filename)
                spec = importlib.util.spec_from_file_location("module.name", filepath)
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
        return bytes.decode('utf-8', 'ignore')  # Ignore errors and return as much as possible

    def ircsend(self, msg):
        try:
            if msg != '':
                self.logger.info(f'Sending command: {msg}')
                self.ircsock.send(bytes(f'{msg}\r\n','UTF-8'))
        except Exception as e:
            self.logger.error(f'Error sending IRC message: {e}')
            raise

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

    def connect(self):
        try:
            self.ircsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

            if str(self.config["Connection"].get("Port"))[:1] == '+':
                context = ssl.create_default_context()
                self.ircsock = context.wrap_socket(self.ircsock, server_hostname=self.config["Connection"].get("Hostname"))
                port = int(self.config['Connection'].get('Port')[1:])
            else:
                port = int(self.config['Connection'].get('Port'))

            if 'BindHost' in self.config:
                self.ircsock.bind((self.config['Connection'].get('BindHost'), 0))

            self.ircsock.connect_ex((self.config['Connection'].get('Hostname'), port))
            self.ircsend(f'NICK {self.config["Connection"].get("Nick")}')
            self.ircsend(f'USER {self.config["Connection"].get("Ident")} * * :{self.config["Connection"].get("Name")}')
            if self.config["SASL"].get("UseSASL"):
                self.ircsend('CAP REQ :sasl')
        except Exception as e:
            self.logger.error(f"Error establishing connection: {e}")
            self.connected = False
            return

    def start(self):
        while True:
            if not self.connected:
                try:
                    self.connect()
                    self.connected = True
                except Exception as e:
                    self.logger.error(f'Connection error: {e}')
                    time.sleep(60)
                    continue

            try:
                recvText = self.ircsock.recv(2048)
                if not recvText:
                    self.connected = False
                    continue

                ircmsg = self.decode(recvText)
                source, command, args = self.parse_message(ircmsg)
                self.logger.debug(f'Received: source: {source} | command: {command} | args: {args}')

                # Handle PING requests immediately
                if command == 'PING':
                    nospoof = args[0][1:] if args[0].startswith(':') else args[0]
                    self.ircsend(f'PONG :{nospoof}')
                    continue

                # Process other messages
                if command == 'PRIVMSG':
                    channel, message = args[0], args[1]
                    source_nick = source.split('!')[0]
                    if message.startswith('&'):
                        cmd, *cmd_args = message[1:].split()
                        self.handle_command(source_nick, channel, cmd, cmd_args)
                    for plugin in self.plugins:
                        plugin.handle_message(source_nick, channel, message)

                elif command == 'CAP' and args[1] == 'ACK' and 'sasl' in args[2]:
                    handle_sasl(self.config, self.ircsend)

                elif command == 'AUTHENTICATE':
                    handle_authenticate(args, self.config, self.ircsend)

                elif command == '903':
                    handle_903(self.ircsend)

                if command == 'PRIVMSG' and args[1].startswith('\x01VERSION\x01'):
                    source_nick = source.split('!')[0]
                    self.ircsend(f'NOTICE {source_nick} :\x01VERSION EliteBot 0.1\x01')

                if command == '001':
                    for channel in self.channel_manager.get_channels():
                        self.ircsend(f'JOIN {channel}')

                if command == 'INVITE':
                    channel = args[1]
                    self.ircsend(f'JOIN {channel}')
                    self.channel_manager.save_channel(channel)

                if command == 'VERSION':
                    self.ircsend('NOTICE', f'{source_nick} :I am a bot version 1.0.0')

            except Exception as e:
                self.logger.error(f'General error: {e}')
                self.connected = False

if __name__ == '__main__':
    try:
        bot = Bot(sys.argv[1])
        bot.start()
    except KeyboardInterrupt:
        print('\nEliteBot has been stopped.')
    except Exception as e:
        print(f'An unexpected error occurred: {e}')
