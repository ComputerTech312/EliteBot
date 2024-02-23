from sqlalchemy import create_engine, Table, MetaData, inspect, update, select, insert, delete
from sqlalchemy_utils import database_exists, create_database


# TODO: Load ConnectionString from config
class Database:
    def __init__(self, table: Table, meta: MetaData):
        self.engine = create_engine(r'sqlite:///.\data\database.db')
        self.table = table
        self.meta = meta

        if not database_exists(self.engine.url):
            create_database(self.engine.url)

    def create_table(self, table_name):
        if not inspect(self.engine).has_table(table_name):
            self.meta.create_all(self.engine)

    def set_user(self, user: str, values: dict):
        with self.engine.connect() as conn:
            stmt = select(self.table).where(self.table.c.name == user)
            cnt = len(conn.execute(stmt).fetchall())

            if cnt == 1:
                conn.execute((
                    update(self.table).
                    values(values)
                ))
                conn.commit()

    def get_user(self, user: str, index: int):
        with self.engine.connect() as conn:
            stmt = select(self.table).where(self.table.c.name == user)
            cnt = len(conn.execute(stmt).fetchall())

            if cnt == 1:
                return conn.execute(select(self.table).where(self.table.c.name == user)).fetchone()[index]
            else:
                return -1

    def _load_channels(self):
        with self.engine.connect() as conn:
            return conn.execute(select(self.table)).fetchall()

    def _save_channel(self, channel: str):
        with self.engine.connect() as conn:
            stmt = select(self.table).where(self.table.c.channel == channel)
            cnt = len(conn.execute(stmt).fetchall())

            if cnt == 0:
                conn.execute((
                    insert(self.table).
                    values({'channel': channel})
                ))
                conn.commit()

    def _remove_channel(self, channel: str):
        with self.engine.connect() as conn:
            stmt = select(self.table).where(self.table.c.channel == channel)
            cnt = len(conn.execute(stmt).fetchall())

            if cnt == 1:
                conn.execute((
                    delete(self.table).
                    where(self.table.c.channel == channel)
                ))
                conn.commit()
