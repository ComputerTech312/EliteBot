#!/usr/bin/env python3

from src.db import Database
from sqlalchemy import Table, Column, Integer, String, Boolean, MetaData

meta = MetaData()
channel_table = Table(
    'Channels',
    meta,
    Column('id', Integer, primary_key=True, autoincrement=True),
    Column('channel', String, unique=True, nullable=False),
    Column('autojoin', Boolean, default=True),
)
db = Database(channel_table, meta)


class ChannelManager:
    def __init__(self):
        db.create_table(channel_table.name)

        self.channels = db._load_channels()

    def save_channel(self, channel):
        db._save_channel(channel)

    def remove_channel(self, channel):
        db._remove_channel(channel)

    def get_channels(self):
        return self.channels
