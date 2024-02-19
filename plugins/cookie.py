from sqlalchemy import Table, Column, Integer, String, MetaData, insert, select

from src.channel_manager import ChannelManager
from src.db import Database
from src.plugin_base import PluginBase

meta = MetaData()
cookie_table = Table(
    'Cookie',
    meta,
    Column('id', Integer, primary_key=True, autoincrement=True),
    Column('name', String, unique=True, nullable=False),
    Column('cookies', Integer, default=0),
    Column('last', String, default='1999/01/01 00:00:00'),
)
c_db = Database(cookie_table, meta)


class Plugin(PluginBase):
    def handle_message(self, source_nick, channel, message):
        parts = message.split()
        c_db.create_table('Cookie')
        self.channel_manager = ChannelManager()

        if parts[0].lower() == '!cookie':
            if len(parts) == 1:  # !cookie
                self.insert_user(source_nick)
                self.bot.ircsend(f'PRIVMSG {channel} :Nooooo~~')

                c_db.set(source_nick, {'cookies': 1, 'last': '1999/01/01 00:00:01'})
            elif len(parts) == 2:  # !cookie USER
                cookies = c_db.get(parts[1], 2)

                if cookies == -1:
                    self.bot.ircsend(f'PRIVMSG {channel} :I\'ve looked everywhere for {parts[1]}, but I couldn\'t '
                                     f'find them.')
                else:
                    c = 'cookie'
                    if cookies == 0:
                        c = 'no cookies.'
                    elif cookies == 1:
                        c = f'{cookies} cookie.'
                    else:
                        c = f'{cookies} cookies.'

                    self.bot.ircsend(f'PRIVMSG {channel} :{parts[1]} currently has {c}')

    def insert_user(self, user: str):
        with c_db.engine.connect() as conn:
            stmt = select(cookie_table).where(cookie_table.c.name == user)
            cnt = len(conn.execute(stmt).fetchall())

            if cnt == 0:
                conn.execute((
                    insert(cookie_table).
                    values({'name': user})
                ))
                conn.commit()
