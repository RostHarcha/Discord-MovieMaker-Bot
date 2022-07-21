from dataclasses import dataclass

@dataclass
class Config:
    bot_token: str
    bot_name: str
    bot_command_prefix: str
    customers_guild_id: int
    moviemakers_guild_id: int
    last_order_id: int
    other_subcategories_channel_id: int
    create_order_channel_id: int
    channel_name_prefix: str = 'заказ-'

@dataclass
class Games:
    id: int
    name: str 
    message: str

@dataclass
class SubcategoriesMoviemakers:
    subcategory_id: int
    user_id: int

@dataclass
class Moviemakers:
    user_id: int
    nickname: str

@dataclass
class Orders:
    id: int
    customer_channel_id: int
    moviemaker_channel_id: int
    created: str
    subcategory_id: int

@dataclass
class Users:
    id: int
    context: str
    moviemaker: bool
    admin: bool

@dataclass
class Messages:
    key: str
    text: str
    description: str

@dataclass
class Categories:
    id: int
    name: str 
    message: str

@dataclass
class Subcategories:
    id: int
    category_id: int
    name: str 
    message: str

CTX_DEFAULT = '0'
CTX_EDIT_MESSAGE = 'edit_message'

CTX_NEW_CATEGORY = 'new_category'
CTX_RENAME_CATEGORY = 'rename_category'
CTX_EDIT_CATEGORY_MESSAGE = 'edit_category_message'

CTX_OTHER_SUBCATEGORY = 'other_subcategory'

CTX_NEW_SUBCATEGORY = 'new_subcategory'
CTX_RENAME_SUBCATEGORY = 'rename_subcategory'
CTX_EDIT_SUBCATEGORY_MESSAGE = 'edit_subcategory_message'