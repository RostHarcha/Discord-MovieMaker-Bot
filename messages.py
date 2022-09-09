import database

#order_created = lambda game: database.Messages.get_text('order_created').format(game=game)

chat_oppened = lambda nickname: database.Messages.get_text('chat_oppened').format(nickname=nickname)

new_name = lambda what: f'Введите новое название для {what}:'

name_for_new = lambda what: f'Введите название для создания {what}:'

new_name_for_category = lambda category: f'Введите новое название для категории {category}:'

#order_sent = lambda game: database.Messages.get_text('order_sent').format(game=game)

new_order = lambda order_id, category, subcategory: f'[Заказ №{order_id}] Заявка на {category} > {subcategory}'

back = lambda: database.Messages.get_text('back')

choose_game = lambda: database.Messages.get_text('choose_game')

def choose_moviemaker(game_id: int):
    message = database.Games.get_message(game_id)
    if message is None:
        return database.Messages.get_text('choose_moviemaker')
    return message

other = lambda: database.Messages.get_text('other')

enter_game = lambda: database.Messages.get_text('enter_game')

create_order = lambda: database.Messages.get_text('create_order')

to_create_order = lambda: database.Messages.get_text('to_create_order')

payment = lambda: database.Messages.get_text('payment')

participants = lambda: database.Messages.get_text('participants')

admin = lambda: database.Messages.get_text('admin')

moviemaker = lambda: database.Messages.get_text('moviemaker')

games = lambda: database.Messages.get_text('games')

admin_panel = lambda: database.Messages.get_text('admin_panel')

rename = lambda: database.Messages.get_text('rename')

delete = lambda: database.Messages.get_text('delete')

add = lambda: database.Messages.get_text('add')

name_for_game = lambda: database.Messages.get_text('name_for_game')

name_for_category = lambda: 'Введите название для категории:'

categories = lambda: 'Категории'

edit_message = lambda: 'Изменить текст'

texts = lambda: database.Messages.get_text('texts')

new_message_text = lambda: 'Введите новый текст:'

choose_category = lambda: 'Выберите категорию:'

enter_ohter = lambda category: f'Уточните, что бы вы хотели заказать?' # ({category})'

order_created = lambda subcategory: f'Создан заказ на {subcategory}'

order_sent = lambda category, subcategory: f'Заявка на {category} > {subcategory} отправлена. Ожидайте, мы рассмотрим заявку, через некоторое время в этом диалоге с вами свяжется исполнитель заказа.'

subcategories = lambda: 'Подкатегории'

cancel_order = lambda: 'Отменить заказ'