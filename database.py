from sqlite3 import connect, PARSE_DECLTYPES, PARSE_COLNAMES
from typing import Iterable, List
import models
from datetime import datetime

con = connect('database.db', detect_types=PARSE_DECLTYPES | PARSE_COLNAMES)
cur = con.cursor()

class Table:
    def __init__(self, table: str, model = None) -> None:
        self.table = table
        self.model = model

    def from_iterable(self, args: Iterable):
        if args == [None]:
            return None
        return self.model(*args)

    async def add(self, parameters: str, _values: str, values: Iterable, exc: str = None):
        try:
            con.execute(f"""
                INSERT INTO {self.table} {parameters}
                VALUES {_values}
            """, values)
            con.commit()
        except Exception as e:
            print(parameters, e)

    def get(self, select: str, condition: str, values: Iterable):
        cur.execute(f"""
            SELECT {select}
            FROM {self.table}
            WHERE {condition}
        """, values)
        answer = cur.fetchone()
        return [None] if answer is None else answer

    def get_no_condition(self, select: str):
        cur.execute(f"""
            SELECT {select}
            FROM {self.table}
        """)
        answer = cur.fetchone()
        return [None] if answer is None else answer

    def get_all(self, select: str, condition: str, values: Iterable):
        cur.execute(f"""
            SELECT {select}
            FROM {self.table}
            WHERE {condition}
        """, values)
        return cur.fetchall()

    def get_all_no_condition(self, select: str):
        cur.execute(f"""
            SELECT {select}
            FROM {self.table}
        """)
        return cur.fetchall()

    async def update(self, set: str, condition: str, values: Iterable, exc: str = None):
        try:
            cur.execute(f"""
                UPDATE {self.table}
                SET {set}
                WHERE {condition}
            """, values)
            con.commit()
        except Exception as e:
            print(f'{set=}, {condition=}, {values=}, {e=}')

    async def delete(self, condition: str, values: Iterable, exc: str = None):
        try:
            cur.execute(f"DELETE FROM {self.table} WHERE {condition}", values)
            con.commit()
        except Exception as e:
            print(condition, e)


class Orders:
    table = Table('orders', models.Orders)

    @classmethod
    def get_game_id_by_customer_channel_id(cls, customer_channel_id: int) -> int:
        return cls.table.get('game_id', 'customer_channel_id = ?', [customer_channel_id])[0]

    @classmethod
    async def add(cls, customer_channel_id: int, order_id: int):
        await cls.table.add('(id, customer_channel_id, moviemaker_channel_id, created)', 
                            '(?, ?, ?, ?)',
                            (order_id, customer_channel_id, None, datetime.now().isoformat()))

    @classmethod
    async def update_moviemaker_channel_id(cls, customer_channel_id: int, moviemaker_channel_id: int):
        await cls.table.update('moviemaker_channel_id = ?', 'customer_channel_id = ?', 
                                (moviemaker_channel_id, customer_channel_id))

    @classmethod
    async def update_moviemaker_channel_id_by_id(cls, id: int, moviemaker_channel_id: int):
        await cls.table.update('moviemaker_channel_id = ?', 'id = ?', 
                                (moviemaker_channel_id, id))

    @classmethod
    async def update_subcategory_id(cls, customer_channel_id: int, subcategory_id: int):
        await cls.table.update('subcategory_id = ?', 'customer_channel_id = ?', (subcategory_id, customer_channel_id))

    @classmethod
    def get_by_channel_id(cls, channel_id: int) -> models.Orders:
        order = cls.table.get('*', 'moviemaker_channel_id = ? OR customer_channel_id = ?', (channel_id, channel_id))
        return cls.table.from_iterable(order)


class Config:
    table = Table('config', models.Config)

    @classmethod
    def get(cls) -> models.Config:
        config = cls.table.get_no_condition('*')
        return cls.table.from_iterable(config)

    @classmethod
    async def iter_last_order_id(cls) -> int:
        last_order_id = cls.table.get_no_condition('last_order_id')[0]
        await cls.table.update('last_order_id = ?', '0 = 0', [last_order_id + 1])
        return last_order_id + 1


class Games:
    table = Table('games', models.Games)
    
    @classmethod
    async def add(cls, name: str) -> models.Games:
        await cls.table.add('(name)', '(?)', [name])
        id =  cls.get_id(name)
        return models.Games(id, name, None)

    @classmethod
    def get_games(cls) -> List[str]:
        games = [i[0] for i in cls.table.get_all_no_condition('name')]
        return games

    @classmethod
    def get(cls, id: int) -> models.Games:
        game = cls.table.get('*', 'id = ?', [id])
        return cls.table.from_iterable(game)

    @classmethod
    def get_all(cls) -> List[models.Games]:
        games = cls.table.get_all_no_condition('*')
        return [cls.table.from_iterable(game) for game in games]

    @classmethod
    def get_id(cls, name: str) -> int:
        return cls.table.get('id', 'name = ?', [name])[0]

    @classmethod
    def get_name(cls, id: int) -> str:
        return cls.table.get('name', 'id = ?', [id])[0]

    @classmethod
    def get_game_by_channel_id(cls, customer_channel_id: int) -> str:
        game_id = Orders.get_game_id_by_customer_channel_id(customer_channel_id)
        return cls.table.get('name', 'id = ?', [game_id])[0]

    @classmethod
    async def delete(cls, game_id):
        await cls.table.delete('id = ?', [game_id])

    @classmethod
    async def update_name(cls, game_id: int, new_name: str):
        await cls.table.update('name = ?', 'id = ?', (new_name, game_id))

    @classmethod
    async def update_message(cls, game_id: int, new_message: str):
        await cls.table.update('message = ?', 'id = ?', (new_message, game_id))

    @classmethod
    def get_message(cls, game_id: int) -> str:
        return cls.table.get('message', 'id = ?', [game_id])[0]


class Categories:
    table = Table('categories', models.Categories)

    @classmethod
    def get_all(cls) -> List[models.Categories]:
        categories = cls.table.get_all_no_condition('*')
        return [cls.table.from_iterable(category) for category in categories]

    @classmethod
    async def delete(cls, category_id):
        await cls.table.delete('id = ?', [category_id])
    
    @classmethod
    async def update_name(cls, category_id: int, new_name: str):
        await cls.table.update('name = ?', 'id = ?', (new_name, category_id))

    @classmethod
    def get_categories(cls) -> List[str]:
        categories = [i[0] for i in cls.table.get_all_no_condition('name')]
        return categories

    @classmethod
    def get(cls, id: int) -> models.Categories:
        category = cls.table.get('*', 'id = ?', [id])
        return cls.table.from_iterable(category)

    @classmethod
    async def update_message(cls, category_id: int, new_message: str):
        await cls.table.update('message = ?', 'id = ?', (new_message, category_id))

    @classmethod
    def get_id(cls, name: str) -> int:
        return cls.table.get('id', 'name = ?', [name])[0]

    @classmethod
    async def add(cls, name: str) -> models.Categories:
        await cls.table.add('(name)', '(?)', [name])
        id = cls.get_id(name)
        return models.Categories(id, name, None)

    @classmethod
    def get_name(cls, id: int) -> str:
        return cls.table.get('name', 'id = ?', [id])[0]

class Subcategories:
    table = Table('subcategories', models.Subcategories)

    @classmethod
    def get_all_by_category_id(cls, category_id: int) -> List[models.Subcategories]:
        subcategories = cls.table.get_all('*', 'category_id = ?', [category_id])
        return [cls.table.from_iterable(subcategory) for subcategory in subcategories]

    @classmethod
    def get_name(cls, id: int) -> str:
        return cls.table.get('name', 'id = ?', [id])[0]

    @classmethod
    async def delete(cls, subcategory_id):
        await cls.table.delete('id = ?', [subcategory_id])

    @classmethod
    def get_id(cls, name: str) -> int:
        return cls.table.get('id', 'name = ?', [name])[0]

    @classmethod
    async def add(cls, category_id: int, name: str) -> models.Subcategories:
        await cls.table.add('(category_id, name)', '(?, ?)', (category_id, name))
        id = cls.get_id(name)
        return models.Subcategories(id, category_id, name, None)

    @classmethod
    async def update_message(cls, subcategory_id: int, new_message: str):
        await cls.table.update('message = ?', 'id = ?', (new_message, subcategory_id))

    @classmethod
    def get(cls, id: int) -> models.Subcategories:
        subcategory = cls.table.get('*', 'id = ?', [id])
        return cls.table.from_iterable(subcategory)
    
    @classmethod
    async def update_name(cls, subcategory_id: int, new_name: str):
        await cls.table.update('name = ?', 'id = ?', (new_name, subcategory_id))

    @classmethod
    def get_all(cls) -> List[models.Subcategories]:
        subcategories = cls.table.get_all_no_condition('*')
        return [cls.table.from_iterable(subcategory) for subcategory in subcategories]


class Users:
    table = Table('users', models.Users)

    @classmethod
    async def add(cls, id: int) -> models.Users:
        await cls.table.add('(id, context, moviemaker, admin)', 
                            '(?, ?, ?, ?)', (id, '0', False, False))
        return models.Users(id, '0', False, False)

    @classmethod
    def get(cls, id: int) -> models.Users:
        user = cls.table.get('*', 'id = ?', [id])
        return cls.table.from_iterable(user)

    @classmethod
    def get_context(cls, id: int) -> str:
        return cls.table.get('context', 'id = ?', [id])[0]

    @classmethod
    async def update_context(cls, id: int, new_context: str):
        await cls.table.update('context = ?', 'id = ?', (new_context, id))

    @classmethod
    def is_admin(cls, id: int) -> bool:
        return cls.table.get('admin', 'id = ?', [id])[0] == True

    @classmethod
    async def update_admin(cls, id: int, admin: bool):
        await cls.table.update('admin = ?', 'id = ?', (admin, id))

    @classmethod
    async def update_moviemaker(cls, id: int, moviemaker: bool):
        await cls.table.update('moviemaker = ?', 'id = ?', (moviemaker, id))

    @classmethod
    def get_all(cls) -> List[models.Users]:
        users = cls.table.get_all_no_condition('*')
        return [cls.table.from_iterable(user) for user in users]

    @classmethod
    def get_moviemakers_ids(cls) -> List[int]:
        ids = cls.table.get_all('id', 'moviemaker = ?', [True])
        return [i[0] for i in ids]


class SubcategoriesMoviemakers:
    table = Table('subcategories_moviemakers', models.SubcategoriesMoviemakers)

    @classmethod
    def get_subcategory_ids(cls, user_id: int) -> List[str]:
        subcategory_ids = cls.table.get_all('subcategory_id', 'user_id = ?', [user_id])
        return [id[0] for id in subcategory_ids]

    @classmethod
    async def delete(cls, subcategory_id: int, user_id: int):
        await cls.table.delete('subcategory_id = ? AND user_id = ?', (subcategory_id, user_id))

    @classmethod
    async def add(cls, subcategory_id: int, user_id: int):
        await cls.table.add('(subcategory_id, user_id)', '(?, ?)', (subcategory_id, user_id))

    @classmethod
    def exists(cls, user_id: int, subcategory_id: int) -> bool:
        exists = cls.table.get('*', 'user_id = ? AND subcategory_id = ?', (user_id, subcategory_id))[0]
        return False if exists is None else True


class Messages:
    table = Table('messages', models.Messages)

    @classmethod
    def get_text(cls, key: str) -> str:
        return cls.table.get('text', 'key = ?', [key])[0]

    @classmethod
    def get(cls, key: str) -> models.Messages:
        message = cls.table.get('*', 'key = ?', [key])
        return cls.table.from_iterable(message)

    @classmethod
    def get_all(cls) -> List[models.Messages]:
        messages = cls.table.get_all_no_condition('*')
        return [cls.table.from_iterable(msg) for msg in messages]

    @classmethod
    async def update(cls, key: str, new_text: str):
        await cls.table.update('text = ?', 'key = ?', (new_text, key))