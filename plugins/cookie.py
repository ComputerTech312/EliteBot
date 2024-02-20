import random
import time
from datetime import datetime

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
            if len(parts) == 1:
                self.insert_user(source_nick)

                cookies = c_db.get(source_nick, 2)
                rnd = random.randint(1, 10)
                last = datetime.strptime(c_db.get(source_nick, 3), '%Y/%m/%d %H:%M:%S')
                current = datetime.strptime(datetime.now().strftime('%Y/%m/%d %H:%M:%S'), '%Y/%m/%d %H:%M:%S')
                diff = round((current - last).total_seconds() / 60.0)

                if diff >= 30:
                    c1 = 'no cookies' if rnd == 0 \
                        else f'{rnd} cookie' if rnd == 1 \
                        else f'{rnd} cookies'
                    c2 = 'no cookies' if (cookies + rnd) == 0 \
                        else f'{(cookies + rnd)} cookie' if (cookies + rnd) == 1 \
                        else f'{(cookies + rnd)} cookies'

                    self.bot.ircsend(f'PRIVMSG {channel} :\x01ACTION gives {c1} to {source_nick}.\x01')
                    self.bot.ircsend(f'PRIVMSG {channel} :You now have a total of {c2}.')

                    c_db.set(source_nick, {
                        'cookies': (cookies + rnd),
                        'last': current.strftime('%Y/%m/%d %H:%M:%S')
                    })
                else:
                    rem = self.remaining_time(last.strftime('%Y/%m/%d %H:%M:%S'), 30 * 60000)
                    self.bot.ircsend(f'PRIVMSG {channel} :Remaining time: {rem}')
            elif len(parts) == 2:
                cookies = c_db.get(parts[1], 2)

                if cookies == -1:
                    self.bot.ircsend(f'PRIVMSG {channel} :I\'ve looked everywhere for {parts[1]}, but I couldn\'t '
                                     f'find them.')
                else:
                    c = 'no cookies' if cookies == 0 \
                        else f'{cookies} cookie' if cookies == 1 \
                        else f'{cookies} cookies'
                    self.bot.ircsend(f'PRIVMSG {channel} :{parts[1]} currently has {c}.')

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

    def remaining_time(self, date: str, timeout: int):
        diff = (int(time.mktime(
            datetime.strptime(datetime.now().strftime('%Y/%m/%d %H:%M:%S'), '%Y/%m/%d %H:%M:%S').timetuple()) * 1000) -
                int(time.mktime(datetime.strptime(date, '%Y/%m/%d %H:%M:%S').timetuple()) * 1000))
        h = int((timeout - diff) / (60 * 60 * 1000) % 24)
        m = int((timeout - diff) / (60 * 1000) % 60)
        s = int((timeout - diff) / 1000 % 60)
        hms = ''

        if h == 0 and m == 0 and s == 0:
            return 0

        if h != 0:
            hms += f'{h}h '
        if m != 0:
            hms += f'{m}m '
        if s != 0:
            hms += f'{s}s '

        return f'{hms[:-1]}.'