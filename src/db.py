from sqlalchemy import create_engine, Table, MetaData, inspect, update, select
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

    def set(self, user: str, values: dict):
        with self.engine.connect() as conn:
            stmt = select(self.table).where(self.table.c.name == user)
            cnt = len(conn.execute(stmt).fetchall())

            if cnt == 1:
                conn.execute((
                    update(self.table).
                    values(values)
                ))
                conn.commit()

    def get(self, user: str, index: int):
        with self.engine.connect() as conn:
            stmt = select(self.table).where(self.table.c.name == user)
            cnt = len(conn.execute(stmt).fetchall())

            if cnt == 1:
                return conn.execute(select(self.table).where(self.table.c.name == user)).fetchone()[index]
            else:
                return -1
