#!/usr/bin/env python3

import json
import os
from os import path


class ChannelManager:
    def __init__(self):
        self.channels = self._load_channels()

    def _load_channels(self):
        os.makedirs("data", exist_ok=True)
        if not path.exists('data/channels.json'):
            with open('data/channels.json', 'w') as f:
                json.dump([], f)
            return []
        try:
            with open('data/channels.json', 'r') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON: {e}")
            return []
        except Exception as e:
            print(f"Error loading channels: {e}")
            return []

    def save_channel(self, channel):
        channel = channel.lstrip(':')
        if channel not in self.channels:
            self.channels.append(channel)
            self._write_channels()

    def remove_channel(self, channel):
        channel = channel.lstrip(':')
        if channel in self.channels:
            self.channels.remove(channel)
            self._write_channels()

    def _write_channels(self):
        os.makedirs("data", exist_ok=True)
        try:
            with open('data/channels.json', 'w') as f:
                json.dump(self.channels, f)
        except Exception as e:
            print(f"Error saving channels: {e}")

    def get_channels(self):
        return self.channels
