import discord
from discord.ext import commands
from discord.ext import tasks
from typing import List

import models
import database
import messages

from datetime import datetime

#import vk.dav

config = database.Config.get()

#######
# BOT #
#######

bot = commands.Bot(command_prefix='!', intents=discord.Intents.all())

async def log(order_id, author, msg):
    with open(f'logs/{order_id}.txt', 'a') as file:
        file.write(f'{author}: {msg}\n')

def bot_log(msg):
    with open('log.txt', 'a') as file:
        datetime_ = str(datetime.now())
        file.write(f'[{datetime_}]\t{msg}\n')

@tasks.loop(minutes=30)
async def checkInactiveOrders():
    for id, customer_channel_id in database.Orders.get_all_inactive():
        await database.Orders.delete(id)
        try:
            channel = await bot.fetch_channel(customer_channel_id)
            await channel.delete()
        except Exception as e:
            bot_log(e)

@bot.event
async def on_ready():
    bot_log('Bot connected successfully!')
    channel = await bot.fetch_channel(991404882307317860)
    await channel.purge()
    await channel.send(messages.to_create_order(), view=CreateOrder(timeout=None))
    checkInactiveOrders.start()



#######################
# CHOOSING MOVIEMAKER #
#######################

class MoviemakerButton(discord.ui.Button):
    def __init__(self, moviemaker: models.Moviemakers, subcategory: models.Subcategories):
        self.moviemaker = moviemaker
        self.subcategory = subcategory
        super().__init__(label=moviemaker.nickname, style=discord.ButtonStyle.green)

    async def callback(self, interaction: discord.Interaction):
        guild = discord.utils.get(bot.guilds, id=config.moviemakers_guild_id)
        moviemaker = await bot.fetch_user(self.moviemaker.user_id)
        overwrites = {
           guild.default_role: discord.PermissionOverwrite(view_channel=False),
           moviemaker: discord.PermissionOverwrite(view_channel=True)
        }
        channel = await guild.create_text_channel(  name=interaction.channel.name,
                                                    overwrites=overwrites)
        await database.Orders.update_moviemaker_channel_id(interaction.channel.id, channel.id)
        await channel.send(messages.order_created(self.subcategory.name))

        await interaction.message.delete()
        await interaction.channel.send(content=messages.chat_oppened(self.moviemaker.nickname))


class BackButton(discord.ui.Button):
    def __init__(self, content: str, view_: discord.ui.View):
        super().__init__(label=messages.back(), style=discord.ButtonStyle.red)
        self.view_ = view_
        self.content = content

    async def callback(self, interaction: discord.Interaction):
        await interaction.message.delete()
        await interaction.channel.send(self.content, view=self.view_)


class ChooseMoviemaker(discord.ui.View):
    def __init__(self, moviemakers: List[models.Moviemakers], subcategory: models.Subcategories, order_id: int):
        super().__init__(timeout=None)
        for moviemaker in moviemakers:
            self.add_item(MoviemakerButton(moviemaker, subcategory))
        category = database.Categories.get(subcategory.category_id)
        self.add_item(BackButton(category.message, ChooseSubcategory(category, order_id)))



########################
# CHOOSING SUBCATEGORY #
########################

class OtherSubcategoryButton(discord.ui.Button):
    def __init__(self, order_id: int, category: models.Categories):
        self.order_id = order_id
        self.category = category
        super().__init__(label=messages.other(), style=discord.ButtonStyle.grey)

    async def callback(self, interaction: discord.Interaction):
        try:
            await interaction.message.delete()
            await database.Users.update_context(interaction.user.id, f'{models.CTX_OTHER_SUBCATEGORY};{self.category.name}')
            await interaction.channel.send(content=messages.enter_ohter(self.category.name))
        except Exception as e:
            bot_log(e)
    


class SubcategoryButton(discord.ui.Button):
    def __init__(self, subcategory: models.Subcategories, order_id: int):
        self.subcategory = subcategory
        self.order_id = order_id
        super().__init__(style=discord.ButtonStyle.green, label=subcategory.name)

    async def callback(self, interaction: discord.Interaction):
        await database.Orders.update_subcategory_id(interaction.channel.id, self.subcategory.id)

        moviemakers = []
        for id in database.Users.get_moviemakers_ids():
            if database.SubcategoriesMoviemakers.exists(id, self.subcategory.id):
                try:
                    user = await bot.fetch_user(id)
                    moviemakers.append(models.Moviemakers(id, user.name))
                except:
                    pass

        await interaction.message.delete()
        await interaction.channel.send(content=self.subcategory.message, view=ChooseMoviemaker(moviemakers, self.subcategory, self.order_id))


class ChooseSubcategory(discord.ui.View):
    def __init__(self, category: models.Categories, order_id: int):
        super().__init__(timeout=None)
        for subcategory in database.Subcategories.get_all_by_category_id(category.id):
            self.add_item(SubcategoryButton(subcategory, order_id))
        self.add_item(OtherSubcategoryButton(order_id, category))
        self.add_item(BackButton(messages.categories(), ChooseCategory(order_id)))



#####################
# CHOOSING CATEGORY #
#####################

class CategoryButton(discord.ui.Button):
    def __init__(self, category: models.Categories, order_id: int):
        self.category = category
        self.order_id = order_id
        super().__init__(style=discord.ButtonStyle.green, label=category.name)

    async def callback(self, interaction: discord.Interaction):
        await interaction.message.delete()
        await interaction.channel.send(self.category.message, view=ChooseSubcategory(self.category, self.order_id))

class ChooseCategory(discord.ui.View):
    def __init__(self, order_id: int):
        self.order_id = order_id
        super().__init__(timeout=None)
        for category in database.Categories.get_all():
            self.add_item(CategoryButton(category, order_id))

    @discord.ui.button(label=messages.cancel_order(), style=discord.ButtonStyle.red)
    async def cancel_order(self, callback: discord.interactions.Interaction, button: discord.ui.Button):
        await callback.channel.delete()
        await database.Users.update_context(callback.user.id, '0')



##################
# CREATING ORDER #
##################

class CreateOrder(discord.ui.View):
    @discord.ui.button(label=messages.create_order(), style=discord.ButtonStyle.green, emoji='🤝')
    async def create_order(self, callback: discord.interactions.Interaction, button: discord.ui.Button):
        # Get user from database
        user = database.Users.get(callback.user.id)
        if user is None:
            user = await database.Users.add(callback.user.id)
            
        guild = discord.utils.get(bot.guilds, id=config.customers_guild_id)
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            callback.user: discord.PermissionOverwrite(view_channel=True)
        }
        order_id = await database.Config.iter_last_order_id()
        channel = await guild.create_text_channel(  name=f'{config.channel_name_prefix}-{order_id}',
                                                    overwrites=overwrites)
        await database.Orders.add(channel.id, order_id)
        await channel.send(messages.choose_category(), view=ChooseCategory(order_id))
        await callback.message.delete()
        await callback.channel.send(messages.to_create_order(), view=CreateOrder(timeout=None))



################
# TEST COMMAND #
################

@bot.command('test')
async def test(ctx: commands.Context):
    bot_log('test')



###################
# PAYMENT COMMAND #
###################

@bot.command('payment')
async def payment(ctx: commands.Context):
    try:
        if ctx.guild.id != config.moviemakers_guild_id:
            return

        order = database.Orders.get_by_channel_id(ctx.channel.id)
        if order is None:
            return

        channel_id = order.customer_channel_id
        message = messages.payment()
        await bot.get_channel(channel_id).send(message)
        await log(order.id, ctx.author, f'!ОТПРАВЛЕНЫ РЕКВИЗИТЫ: {message}')
    except:
        return


class BackButton(discord.ui.Button):
    def __init__(self, content: str, view_: discord.ui.View):
        super().__init__(label=messages.back(), style=discord.ButtonStyle.red)
        self.view_ = view_
        self.content = content

    async def callback(self, interaction: discord.Interaction):
        await interaction.message.delete()
        await interaction.channel.send(self.content, view=self.view_)



####################
# ADMIN DECORATORS #
####################

def admin_button(func):
    async def decorator(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not database.Users.is_admin(interaction.user.id):
            return
        await func(self, interaction, button)
    return decorator

def admin_callback(func):
    async def decorator(self, interaction: discord.Interaction):
        if not database.Users.is_admin(interaction.user.id):
            return
        await func(self, interaction)
    return decorator



##############################
# ADMIN SUBCATEGORY SETTINGS #
##############################

class AdminSubcategorySettings(discord.ui.View):
    def __init__(self, subcategory: models.Subcategories):
        self.subcategory = subcategory
        super().__init__(timeout=None)
    
    @discord.ui.button(label=messages.back(), style=discord.ButtonStyle.grey)
    @admin_button
    async def back(self, interaction: discord.interactions.Interaction, button: discord.ui.Button):
        await interaction.message.delete()
        category = database.Categories.get(self.subcategory.category_id)
        await interaction.channel.send(messages.subcategories(), view=AdminSubcategories(category))

    @discord.ui.button(label=messages.delete(), style=discord.ButtonStyle.red)
    @admin_button
    async def delete(self, interaction: discord.interactions.Interaction, button: discord.ui.Button):
        await database.Subcategories.delete(self.subcategory.id)
        await interaction.message.delete()  
        category = database.Categories.get(self.subcategory.category_id)
        await interaction.channel.send(messages.categories(), view=AdminSubcategories(category))

    @discord.ui.button(label=messages.rename(), style=discord.ButtonStyle.blurple)
    @admin_button
    async def rename(self, interaction: discord.interactions.Interaction, button: discord.ui.Button):
        await database.Users.update_context(interaction.user.id, f'{models.CTX_RENAME_SUBCATEGORY};{str(self.subcategory.id)}')
        await interaction.message.delete()
        category = database.Categories.get(self.subcategory.category_id)
        await interaction.channel.send(messages.new_name(f'подкатегории {self.subcategory.name} в категории {category.name}'))

    @discord.ui.button(label=messages.edit_message(), style=discord.ButtonStyle.blurple)
    @admin_button
    async def edit_message(self, interaction: discord.interactions.Interaction, button: discord.ui.Button):
        await database.Users.update_context(interaction.user.id, f'{models.CTX_EDIT_SUBCATEGORY_MESSAGE};{str(self.subcategory.id)}')
        await interaction.message.delete()
        await interaction.channel.send(messages.new_message_text())



#######################
# ADMIN SUBCATEGORIES #
#######################

class AdminSubcategoryButton(discord.ui.Button):
    def __init__(self, subcategory: models.Subcategories):
        self.subcategory = subcategory
        super().__init__(label=subcategory.name, style=discord.ButtonStyle.blurple)

    @admin_callback
    async def callback(self, interaction: discord.Interaction):
        content = f'**{self.subcategory.name}**\n\n{self.subcategory.message}'
        await interaction.message.delete()
        await interaction.channel.send(content, view=AdminSubcategorySettings(self.subcategory))

class AdminSubcategories(discord.ui.View):
    def __init__(self, category: models.Categories):
        self.category = category
        super().__init__(timeout=None)
        self.add_item(BackButton(messages.categories(), AdminCategories()))
        for subcategory in database.Subcategories.get_all_by_category_id(category.id):
            self.add_item(AdminSubcategoryButton(subcategory))

    @discord.ui.button(label=messages.add(), style=discord.ButtonStyle.green)
    @admin_button
    async def add(self, interaction: discord.interactions.Interaction, button: discord.ui.Button):
        await database.Users.update_context(interaction.user.id, f'{models.CTX_NEW_SUBCATEGORY};{self.category.id}')
        await interaction.message.delete()
        await interaction.channel.send(messages.name_for_new(f'подкатегории в категории {self.category.name}'))




###########################
# ADMIN CATEGORY SETTINGS #
###########################

class AdminCategorySettings(discord.ui.View):
    def __init__(self, category: models.Categories):
        self.category = category
        super().__init__(timeout=None)
    
    @discord.ui.button(label=messages.back(), style=discord.ButtonStyle.grey)
    @admin_button
    async def back(self, interaction: discord.interactions.Interaction, button: discord.ui.Button):
        await interaction.message.delete()
        await interaction.channel.send(messages.categories(), view=AdminCategories())

    @discord.ui.button(label=messages.delete(), style=discord.ButtonStyle.red)
    @admin_button
    async def delete(self, interaction: discord.interactions.Interaction, button: discord.ui.Button):
        await database.Categories.delete(self.category.id)
        await interaction.message.delete()
        await interaction.channel.send(messages.categories(), view=AdminCategories())

    @discord.ui.button(label=messages.rename(), style=discord.ButtonStyle.blurple)
    @admin_button
    async def rename(self, interaction: discord.interactions.Interaction, button: discord.ui.Button):
        await database.Users.update_context(interaction.user.id, f'{models.CTX_RENAME_CATEGORY};{str(self.category.id)}')
        await interaction.message.delete()
        await interaction.channel.send(messages.new_name(f'категории {self.category.name}'))

    @discord.ui.button(label=messages.edit_message(), style=discord.ButtonStyle.blurple)
    @admin_button
    async def edit_message(self, interaction: discord.interactions.Interaction, button: discord.ui.Button):
        await database.Users.update_context(interaction.user.id, f'{models.CTX_EDIT_CATEGORY_MESSAGE};{str(self.category.id)}')
        await interaction.message.delete()
        await interaction.channel.send(messages.new_message_text())

    @discord.ui.button(label=messages.subcategories(), style=discord.ButtonStyle.blurple)
    @admin_button
    async def subcategories(self, interaction: discord.interactions.Interaction, button: discord.ui.Button):
        await interaction.message.delete()
        await interaction.channel.send(f'**{self.category.name}**', view=AdminSubcategories(self.category))
        


####################
# ADMIN CATEGORIES #
####################

class AdminCategoryButton(discord.ui.Button):
    def __init__(self, category: models.Categories):
        self.category = category
        super().__init__(label=category.name, style=discord.ButtonStyle.blurple)

    @admin_callback
    async def callback(self, interaction: discord.Interaction):
        content = f'**{self.category.name}**\n\n{self.category.message}'
        await interaction.message.delete()
        await interaction.channel.send(content, view=AdminCategorySettings(self.category))


class AdminCategories(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(BackButton(messages.admin_panel(), AdminPanel()))
        for category in database.Categories.get_all():
            self.add_item(AdminCategoryButton(category))

    @discord.ui.button(label=messages.add(), style=discord.ButtonStyle.green)
    @admin_button
    async def add(self, interaction: discord.interactions.Interaction, button: discord.ui.Button):
        await database.Users.update_context(interaction.user.id, models.CTX_NEW_CATEGORY)
        await interaction.message.delete()
        await interaction.channel.send(messages.name_for_new('категории'))



#################
# ADMIN MEMBERS #
#################

class AdminAdminButton(discord.ui.Button):
    def __init__(self, user: models.Users):
        self.user = user
        emoji = '✅' if user.admin else None
        super().__init__(style=discord.ButtonStyle.blurple, label=messages.admin(), emoji=emoji)

    @admin_callback
    async def callback(self, interaction: discord.Interaction):
        self.user.admin = not self.user.admin
        await database.Users.update_admin(self.user.id, self.user.admin)
        members = await get_moviemakers_members()
        await interaction.message.delete()
        await interaction.channel.send(messages.participants(), view=AdminMembers(members, self.user))


class AdminMoviemakerButton(discord.ui.Button):
    def __init__(self, user: models.Users):
        self.user = user
        emoji = '✅' if user.moviemaker else None
        super().__init__(style=discord.ButtonStyle.blurple, label=messages.moviemaker(), emoji=emoji)

    @admin_callback
    async def callback(self, interaction: discord.Interaction):
        self.user.moviemaker = not self.user.moviemaker
        await database.Users.update_moviemaker(self.user.id, self.user.moviemaker)
        members = await get_moviemakers_members()
        await interaction.message.delete()
        await interaction.channel.send(messages.participants(), view=AdminMembers(members, self.user))


class AdminCategoriesButton(discord.ui.Button):
    def __init__(self, user: models.Users, user_name: str):
        self.user = user
        self.user_name = user_name
        super().__init__(style=discord.ButtonStyle.blurple, label=messages.categories())

    @admin_callback
    async def callback(self, interaction: discord.Interaction):
        await interaction.message.delete()
        content = f'**{self.user_name}**\nКатегории:'
        await interaction.channel.send(content, view=AdminUserCategories(self.user, self.user_name))


class AdminMembersSelect(discord.ui.Select):
    def __init__(self, members: List[discord.Member], user: models.Users = None):
        if user is None:
            options = [discord.SelectOption(label=member.name, value=f'{member.id};{member.name}') for member in members]
        else:
            options = [discord.SelectOption(label=member.name, value=f'{member.id};{member.name}', default=user.id==member.id) for member in members]
        super().__init__(options=options)

    @admin_callback
    async def callback(self, interaction: discord.Interaction):
        user_id, user_name = interaction.data['values'][0].split(';')
        user = database.Users.get(int(user_id))
        members = await get_moviemakers_members()
        await interaction.message.delete()
        await interaction.channel.send(messages.participants(), view=AdminMembers(members, user, user_name))


class AdminMembers(discord.ui.View):
    def __init__(self, members: List[discord.Member], user: models.Users = None, user_name: str = None):
        super().__init__(timeout=None)
        for m in range(0, len(members), 25):
            self.add_item(AdminMembersSelect(members[m:m+25], user))
        if user is not None:
            self.add_item(AdminAdminButton(user))
            self.add_item(AdminMoviemakerButton(user))
            self.add_item(AdminCategoriesButton(user, user_name))
        self.add_item(BackButton(messages.admin_panel(), AdminPanel()))



############################
# ADMIN USER SUBCATEGORIES #
############################

class AdminUserSubcategoryButton(discord.ui.Button):
    def __init__(self, subcategory: models.Subcategories, user_id: int, allowed: bool, user_name: str):
        self.subcategory = subcategory
        self.user_id = user_id
        self.allowed = allowed
        self.user_name = user_name
        emoji = '✅' if allowed else None
        super().__init__(style=discord.ButtonStyle.blurple, label=subcategory.name, emoji=emoji)

    @admin_callback
    async def callback(self, interaction: discord.Interaction):
        if self.allowed:
            await database.SubcategoriesMoviemakers.delete(self.subcategory.id, self.user_id)
        else:
            await database.SubcategoriesMoviemakers.add(self.subcategory.id, self.user_id)
        await interaction.message.delete()
        await interaction.channel.send(self.user_name, view=AdminUserSubcategories(self.user_id, self.user_name, self.subcategory.category_id))

class AdminUserSubcategoriesButton(discord.ui.Button):
    def __init__(self, user: models.Users, user_name: str):
        self.user = user
        self.user_name = user_name
        super().__init__(style=discord.ButtonStyle.blurple, label=messages.subcategories())

    @admin_callback
    async def callback(self, interaction: discord.Interaction):
        await interaction.message.delete()
        await interaction.channel.send(self.user_name, view=AdminUserSubcategories(self.user.id, self.user_name))


class AdminUserSubcategories(discord.ui.View):
    def __init__(self, user_id: int, user_name: str, category_id: int):
        self.user_id = user_id
        self.user_name = user_name
        super().__init__(timeout=None)
        allowed_ids = database.SubcategoriesMoviemakers.get_subcategory_ids(user_id)
        subcategories = database.Subcategories.get_all_by_category_id(category_id)
        for subcategory in subcategories:
            self.add_item(AdminUserSubcategoryButton(subcategory, user_id, subcategory.id in allowed_ids, user_name))

    @discord.ui.button(label=messages.back(), style=discord.ButtonStyle.red)
    @admin_button
    async def back_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        user = database.Users.get(self.user_id)
        await interaction.message.delete()
        await interaction.channel.send(messages.categories(), view=AdminUserCategories(user, self.user_name))



#########################
# ADMIN USER CATEGORIES #
#########################

class AdminUserCategoryButton(discord.ui.Button):
    def __init__(self, category: models.Categories, user_id: models.Users, user_name: str):
        self.category = category
        self.user_id = user_id
        self.user_name = user_name
        super().__init__(label=category.name, style=discord.ButtonStyle.blurple)

    @admin_callback
    async def callback(self, interaction: discord.Interaction):
        await interaction.message.delete()
        await interaction.channel.send(self.category.name, view=AdminUserSubcategories(self.user_id, self.user_name, self.category.id))

class AdminUserCategories(discord.ui.View):
    def __init__(self, user: models.Users, user_name: str):
        self.user = user
        self.user_name = user_name
        super().__init__(timeout=None)
        for category in database.Categories.get_all():
            self.add_item(AdminUserCategoryButton(category, user.id, user_name))

    @discord.ui.button(label=messages.back(), style=discord.ButtonStyle.red)
    @admin_button
    async def back_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        members = await get_moviemakers_members()
        user = database.Users.get(self.user.id)
        await interaction.message.delete()
        await interaction.channel.send(messages.participants(), view=AdminMembers(members, user, self.user_name))



######################
# ADMIN UPDATE TEXTS #
######################

class AdminUpdateMessage(discord.ui.View):
    def __init__(self, message: models.Messages):
        self.message = message
        super().__init__(timeout=None)
        self.add_item(BackButton(messages.texts(), AdminMessages()))

    @discord.ui.button(label=messages.edit_message(), style=discord.ButtonStyle.green)
    @admin_button
    async def edit_message(self, interaction: discord.interactions.Interaction, button: discord.ui.Button):
        await database.Users.update_context(interaction.user.id, f'{models.CTX_EDIT_MESSAGE};{self.message.key}')
        await interaction.message.delete()
        await interaction.channel.send(messages.new_message_text())


class AdminMessagesSelect(discord.ui.Select):
    def __init__(self, messages: List[models.Messages]):
        options = [discord.SelectOption(label=msg.description, value=f'{msg.key}') for msg in messages]
        super().__init__(options=options)

    @admin_callback
    async def callback(self, interaction: discord.Interaction):
        key = interaction.data['values'][0]
        message = database.Messages.get(key)
        content = f'**{message.description}**\n\n{message.text}'
        await interaction.message.delete()
        await interaction.channel.send(content, view=AdminUpdateMessage(message))


class AdminMessages(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        msg_list = database.Messages.get_all()
        self.add_item(AdminMessagesSelect(msg_list))
        self.add_item(BackButton(messages.admin_panel(), AdminPanel()))



################
# ADMIN PANNEL #
################

async def get_moviemakers_members() -> List[discord.Member]:
    guild = await bot.fetch_guild(config.moviemakers_guild_id)
    members = []
    async for member in guild.fetch_members():
        if not member.bot:
            members += [member]
            if database.Users.get(member.id) is None:
                await database.Users.add(member.id) 
    return members


class AdminPanel(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label=messages.participants(), style=discord.ButtonStyle.blurple)
    @admin_button
    async def members(self, interaction: discord.interactions.Interaction, button: discord.ui.Button):
        members = await get_moviemakers_members()
        await interaction.message.delete()
        await interaction.channel.send(messages.participants(), view=AdminMembers(members))

    @discord.ui.button(label=messages.categories(), style=discord.ButtonStyle.blurple)
    @admin_button
    async def categories(self, interaction: discord.interactions.Interaction, button: discord.ui.Button):
        await interaction.message.delete()
        await interaction.channel.send(messages.categories(), view=AdminCategories())

    @discord.ui.button(label=messages.texts(), style=discord.ButtonStyle.blurple)
    @admin_button
    async def texts(self, interaction: discord.interactions.Interaction, button: discord.ui.Button):
        await interaction.message.delete()
        await interaction.channel.send(messages.texts(), view=AdminMessages())
        

@bot.command('admin')
async def admin(ctx: commands.Context):
    if not database.Users.is_admin(ctx.message.author.id):
        return
    
    await ctx.send(messages.admin_panel(), view=AdminPanel())



##############
# ON MESSAGE #
##############

@bot.event
async def on_message(message: discord.Message):
    try:
        # Ignore own messages
        if message.author == bot.user:
            return

        # Get user from database
        user = database.Users.get(message.author.id)
        if user is None:
            user = await database.Users.add(message.author.id)

        # Process commands
        if message.content.startswith(config.bot_command_prefix):
            return await bot.process_commands(message)

        context = database.Users.get_context(message.author.id).split(';')
        match context[0]:
            case models.CTX_NEW_CATEGORY:
                await database.Users.update_context(message.author.id, models.CTX_DEFAULT)
                category = await database.Categories.add(message.content)
                await message.channel.send(message.content, view=AdminCategorySettings(category))
                return
            case models.CTX_RENAME_CATEGORY:
                category_id = context[1]
                await database.Categories.update_name(category_id, message.content)
                await database.Users.update_context(message.author.id, models.CTX_DEFAULT)
                category = database.Categories.get(category_id)
                await message.channel.send(category.name, view=AdminCategorySettings(category))
                return
            case models.CTX_EDIT_CATEGORY_MESSAGE:
                category_id = context[1]
                await database.Categories.update_message(category_id, message.content)
                await database.Users.update_context(message.author.id, models.CTX_DEFAULT)
                category = database.Categories.get(category_id)
                content = f'**{category.name}**\n\n{category.message}'
                await message.channel.send(content, view=AdminCategorySettings(category))
                return
            case models.CTX_NEW_SUBCATEGORY:
                await database.Users.update_context(message.author.id, models.CTX_DEFAULT)
                category_id = context[1]
                subcategory = await database.Subcategories.add(category_id, message.content)
                await message.channel.send(message.content, view=AdminSubcategorySettings(subcategory))
                return
            case models.CTX_RENAME_SUBCATEGORY:
                subcategory_id = context[1]
                await database.Subcategories.update_name(subcategory_id, message.content)
                await database.Users.update_context(message.author.id, models.CTX_DEFAULT)
                subcategory = database.Subcategories.get(subcategory_id)
                await message.channel.send(subcategory.name, view=AdminSubcategorySettings(subcategory))
                return
            case models.CTX_EDIT_SUBCATEGORY_MESSAGE:
                subcategory_id = context[1]
                await database.Subcategories.update_message(subcategory_id, message.content)
                await database.Users.update_context(message.author.id, models.CTX_DEFAULT)
                subcategory = database.Subcategories.get(subcategory_id)
                content = f'**{subcategory.name}**\n\n{subcategory.message}'
                await message.channel.send(content, view=AdminSubcategorySettings(subcategory))
                return
            case models.CTX_OTHER_SUBCATEGORY:
                order = database.Orders.get_by_channel_id(message.channel.id)
                await database.Users.update_context(message.author.id, models.CTX_DEFAULT)
                category_name = context[1]
                await message.channel.send(content=messages.order_sent(category_name, message.content))
                channel = await bot.fetch_channel(config.other_subcategories_channel_id)
                await channel.send(messages.new_order(order.id, category_name, message.content))

                guild = discord.utils.get(bot.guilds, id=config.moviemakers_guild_id)
                overwrites = {
                    guild.default_role: discord.PermissionOverwrite(view_channel=False)
                }
                channel = await guild.create_text_channel(  name=f'{config.channel_name_prefix}-{order.id}',
                                                            overwrites=overwrites)
                await database.Orders.update_moviemaker_channel_id_by_id(order.id, channel.id)
                return
            case models.CTX_EDIT_MESSAGE:
                key = context[1]
                await database.Messages.update(key, message.content)
                await database.Users.update_context(message.author.id, models.CTX_DEFAULT)
                msg = database.Messages.get(key)
                content = f'**{msg.description}**\n\n{msg.text}'
                await message.channel.send(content, view=AdminUpdateMessage(msg))
                return
            case '0':
                # Get order id
                try:
                    order = database.Orders.get_by_channel_id(message.channel.id)
                    if order is None: return
                except:
                    return

                # Re-send message
                if message.channel.guild.id == config.customers_guild_id:
                    channel_id = order.moviemaker_channel_id
                elif message.channel.guild.id == config.moviemakers_guild_id:
                    channel_id = order.customer_channel_id
                else: 
                    return
                await bot.get_channel(channel_id).send(message.content)
                await log(order.id, message.author, message.content)
            case _:
                bot_log(f'Unexpected context: {context=}')
    except Exception as e:
        bot_log(e)

bot.run(config.bot_token)