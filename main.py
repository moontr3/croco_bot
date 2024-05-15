import time
from config import *
import api
from log import *
import utils

from typing import *
import discord
from discord.ext import commands

from dotenv import load_dotenv
import os
from typing import *


# loading token
load_dotenv()
TOKEN = os.getenv('BOT_TOKEN')

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(
    command_prefix=PREFIX,
    help_command=None,
    intents=intents
)
mg = api.Manager(DATA_FILE, USERS_FILE)


# events

@bot.event
async def on_ready():
    log('Ready!', level=SUCCESS)

@bot.event
async def on_connect():
    log('Connected')

@bot.event
async def on_disconnect():
    log('Disconnected', level=WARNING)

@bot.event
async def on_resumed():
    log('Resumed', level=SUCCESS)


# callback

async def edit_finish_msg(message:discord.Message, r:api.Reaction):
    # creating new view
    view = discord.ui.View()

    btn = discord.ui.Button(
        style=discord.ButtonStyle.blurple,
        label='Хочу быть ведущим!',
        emoji='✋'
    )
    btn.callback = new_game

    like_btn = discord.ui.Button(
        style=discord.ButtonStyle.green,
        label=f'{len(r.likes)}', emoji='👍'
    )
    like_btn.callback = like_callback

    dislike_btn = discord.ui.Button(
        style=discord.ButtonStyle.red,
        label=f'{len(r.dislikes)}', emoji='👎'
    )
    dislike_btn.callback = dislike_callback

    view.add_item(btn)
    view.add_item(like_btn)
    view.add_item(dislike_btn)

    # editing embed
    embed = message.embeds[0]
    embed.clear_fields()

    if r.likes != []:
        embed.add_field(
            name=f'👍 {len(r.likes)}',
            value='\n'.join([f":white_small_square: <@{i}>" for i in r.likes]),
            inline=True
        )

    if r.dislikes != []:
        embed.add_field(
            name=f'👎 {len(r.dislikes)}',
            value='\n'.join([f":white_small_square: <@{i}>" for i in r.dislikes]),
            inline=True
        )

    await message.edit(embed=embed, view=view)


# on_message event

@bot.event
async def on_message(message:discord.Message):
    # no not bots that's not, no.
    if message.author.bot:
        return
    
    await bot.process_commands(message)

    # checking for ongoing game
    game = mg.get_game(message.channel.id)
    if game == None or message.author.id == game.starter_id:
        return
    
    # checking if guess is correct
    if game.word.lower() == message.content.lower().strip().replace('ё','е'):
        game, guesser_events, explainer_events = mg.word_guessed(
            message.channel.id,
            message.guild.id,
            message.author.id
        )
        # creating view
        view = discord.ui.View()

        btn = discord.ui.Button(
            style=discord.ButtonStyle.blurple,
            label='Хочу быть ведущим!',
            emoji='✋'
        )
        btn.callback = new_game

        like_btn = discord.ui.Button(
            style=discord.ButtonStyle.green,
            label='0', emoji='👍'
        )
        like_btn.callback = like_callback

        dislike_btn = discord.ui.Button(
            style=discord.ButtonStyle.red,
            label='0', emoji='👎'
        )
        dislike_btn.callback = dislike_callback

        view.add_item(btn)
        view.add_item(like_btn)
        view.add_item(dislike_btn)

        # creating embed
        footer = f'+{len(game.word)} XP для {message.author.name} и {game.starter_name}'
        if game.moonrocks > 0:
            footer += f'\n{game.starter_name} получил 💎{game.moonrocks}!'

        if guesser_events:
            footer += '\n'+utils.events_to_text(message.author.name, guesser_events)
        
        if explainer_events:
            footer += '\n'+utils.events_to_text(game.starter_name, explainer_events)

        embed = discord.Embed(
            description=f'✅ <@{message.author.id}> отгадал(а) слово **{game.word}**!',
            color=discord.Color.green()
        )
        embed.set_footer(text=footer)
        msg = await message.reply(embed=embed, view=view)

        # adding reference
        mg.add_reactions(msg.id, game.starter_id)



# reload data command

@bot.command()
async def reload(ctx:commands.Context):
    if ctx.author.id not in config.ADMINS:
        return
    
    log(f'{ctx.author.id} ran {PREFIX}reload')

    embed = discord.Embed(
        description='📂 Загружаем...',
        color=discord.Color.yellow()
    )
    message = await ctx.reply(embed=embed)

    mg.load_data()
    mg.load_users()
    log(f'Reloaded!', level=SUCCESS)

    embed = discord.Embed(
        description=f'✅ Успешно!',
        color=discord.Color.green()
    )
    await message.edit(embed=embed)



# sync tree command

@bot.command()
async def sync(ctx:commands.Context):
    if ctx.author.id not in config.ADMINS:
        return
    
    log(f'{ctx.author.id} ran {PREFIX}sync')

    embed = discord.Embed(
        description='🌳 Синхронизация...',
        color=discord.Color.yellow()
    )
    message = await ctx.reply(embed=embed)

    log(f'Syncing tree...')
    commands: list = await bot.tree.sync()
    log(f'Tree synced with {len(commands)} commands!', level=SUCCESS)

    embed = discord.Embed(
        description=f'✅ Успешна синхронизация {len(commands)} команд!',
        color=discord.Color.green()
    )
    await message.edit(embed=embed)



# like callback

async def like_callback(inter: discord.Interaction):
    # liking
    state = mg.like(inter.message.id, inter.user.id)

    # game not found
    if state == None:
        return
    
    r = mg.reactions[inter.message.id]

    # error message
    if state != 0:
        text = [
            f'Вы уже лайкнули объяснение <@{r.explainer_id}>!',
            f'Вы уже дизлайкнули объяснение <@{r.explainer_id}>!',
            'Вы не можете лайкнуть свое же объяснение!',
        ][state-1]
        embed = discord.Embed(
            description=f'🚫 {text}',
            color=discord.Color.red()
        )
        await inter.response.send_message(embed=embed, ephemeral=True)
        return
    
    # sending the word
    embed = discord.Embed(
        description=f'👍 Вам **понравилось** объяснение <@{r.explainer_id}>!',
        color=discord.Color.green()
    )
    await inter.response.send_message(embed=embed, ephemeral=True)

    # editing original message
    await edit_finish_msg(inter.message, r)



# dislike callback

async def dislike_callback(inter: discord.Interaction):
    # disliking
    state = mg.dislike(inter.message.id, inter.user.id)

    # game not found
    if state == None:
        return
    
    r = mg.reactions[inter.message.id]
    
    # error message
    if state != 0:
        text = [
            f'Вы уже лайкнули объяснение <@{r.explainer_id}>!',
            f'Вы уже дизлайкнули объяснение <@{r.explainer_id}>!',
            'Вы не можете дизлайкнуть свое же объяснение!',
        ][state-1]
        embed = discord.Embed(
            description=f'🚫 {text}',
            color=discord.Color.red()
        )
        await inter.response.send_message(embed=embed, ephemeral=True)
        return
    
    # sending the word
    embed = discord.Embed(
        description=f'👎 Вам **не понравилось** объяснение <@{r.explainer_id}>',
        color=discord.Color.green()
    )
    await inter.response.send_message(embed=embed, ephemeral=True)

    # editing original message
    await edit_finish_msg(inter.message, r)



# view word callback

async def view_word(inter: discord.Interaction):
    # checking for ongoing game
    game = mg.get_game(inter.channel_id)
    if game == None:
        embed = discord.Embed(
            description=f'🚫 В этом канале сейчас никто не играет!',
            color=discord.Color.red()
        )
        await inter.response.send_message(embed=embed, ephemeral=True)
        return
    
    # checking if some sneaky ass pressed the button
    if game.starter_id != inter.user.id:
        embed = discord.Embed(
            description=f'🚫 Не для тебя моя кнопочка росла',
            color=discord.Color.red()
        )
        await inter.response.send_message(embed=embed, ephemeral=True)
        return
    
    # sending the word
    embed = discord.Embed(
        description=f'📜 Ваше слово - **{game.word}**',
        color=discord.Color.green()
    )
    await inter.response.send_message(embed=embed, ephemeral=True)



# skip word callback

async def skip_word(inter: discord.Interaction):
    # checking for ongoing game
    game = mg.get_game(inter.channel_id)
    if game == None:
        embed = discord.Embed(
            description=f'🚫 В этом канале сейчас никто не играет!',
            color=discord.Color.red()
        )
        await inter.response.send_message(embed=embed, ephemeral=True)
        return
    
    # checking if some sneaky ass pressed the button
    if game.starter_id != inter.user.id:
        embed = discord.Embed(
            description=f'🚫 Не для тебя моя кнопочка росла',
            color=discord.Color.red()
        )
        await inter.response.send_message(embed=embed, ephemeral=True)
        return
    
    # changing word
    word, events = mg.new_word(inter.user.id, inter.channel_id, inter.guild_id)
    log(f'{inter.user.id} changed word to {word}')
    
    # creating view
    view = discord.ui.View()

    skip_btn = discord.ui.Button(
        style=discord.ButtonStyle.gray,
        label='Новое слово',
        emoji='⏩'
    )
    skip_btn.callback = skip_word
    view.add_item(skip_btn)

    # sending the new word
    embed = discord.Embed(
        description=f'📜 Новое слово - **{word}**',
        color=discord.Color.green()
    )
    if events != []:
        embed.set_footer(text=utils.events_to_text(inter.user.name, events))
    
    await inter.response.send_message(embed=embed, view=view, ephemeral=True)



# end turn word callback

async def end_turn(inter: discord.Interaction):
    # checking for ongoing game
    game = mg.get_game(inter.channel_id)
    if game == None:
        embed = discord.Embed(
            description=f'🚫 В этом канале сейчас никто не играет!',
            color=discord.Color.red()
        )
        await inter.response.send_message(embed=embed, ephemeral=True)
        return
    
    # checking if some sneaky ass pressed the button
    if game.starter_id != inter.user.id:
        embed = discord.Embed(
            description=f'🚫 Не для тебя моя кнопочка росла',
            color=discord.Color.red()
        )
        await inter.response.send_message(embed=embed, ephemeral=True)
        return
    
    # ending game
    mg.games.pop(game.channel_id)
    log(f'{inter.user.id} removed game in {game.channel_id}')
    
    # creating view
    view = discord.ui.View()

    new_game_btn = discord.ui.Button(
        style=discord.ButtonStyle.blurple,
        label='Играть ещё',
        emoji='🎮'
    )
    new_game_btn.callback = new_game
    view.add_item(new_game_btn)

    # sending the message
    embed = discord.Embed(
        description=f'🤚 <@{game.starter_id}> пропустил свой ход!',
        color=discord.Color.green()
    )
    
    await inter.response.send_message(embed=embed, view=view)




# new game callback

async def new_game(inter: discord.Interaction):
    # checking for restrictions
    restr = mg.get_restriction(inter.channel_id)
    if restr != None and restr.guesser_id != inter.user.id:
        embed = discord.Embed(
            description=f'🚫 Игра разблокируется для всех <t:{int(restr.until)}:R>',
            color=discord.Color.red()
        )
        await inter.response.send_message(embed=embed, ephemeral=True)
        return

    # checking for ongoing game
    game = mg.get_game(inter.channel_id)
    if game != None:
        embed = discord.Embed(
            description=f'🚫 Этот раунд закончится <t:{int(game.until)}:R>,'\
                f' а пока объясняет слово <@{game.starter_id}>.',
            color=discord.Color.red()
        )
        await inter.response.send_message(embed=embed, ephemeral=True)
        return

    # creating game
    word, events = mg.new_game(
        inter.guild_id, inter.channel_id,
        inter.message.id, inter.user.id, inter.user.name
    )

    # responding
    embed = discord.Embed(
        description=f'📜 Ваше слово - **{word}**',
        color=discord.Color.green()
    )
    await inter.response.send_message(embed=embed, ephemeral=True)

    # creating view
    view = discord.ui.View()

    view_btn = discord.ui.Button(
        style=discord.ButtonStyle.blurple,
        label='Посмотреть слово',
        emoji='📜'
    )
    view_btn.callback = view_word
    view.add_item(view_btn)

    skip_btn = discord.ui.Button(
        style=discord.ButtonStyle.gray,
        label='Новое слово',
        emoji='⏩'
    )
    skip_btn.callback = skip_word
    view.add_item(skip_btn)

    turn_btn = discord.ui.Button(
        style=discord.ButtonStyle.red,
        label='Пропустить ход',
        emoji='❌'
    )
    turn_btn.callback = end_turn
    view.add_item(turn_btn)

    # creating embed
    embed = discord.Embed(
        description=f'💭 <@{inter.user.id}> загадывает слово!',
        color=discord.Color.green()
    )
    if events != []:
        embed.set_footer(text=utils.events_to_text(inter.user.name, events))

    await inter.channel.send(embed=embed, view=view)



# change word command

@bot.hybrid_command(
    name='change-word', description='Пропускает ваш ход.',
    aliases=['changeword','change_word','change','cw']
)
async def changeword(ctx:commands.Context):
    log(f'{ctx.author.id} ran {PREFIX}change-word')

    # checking for ongoing game
    game = mg.get_game(ctx.channel.id)
    if game == None:
        embed = discord.Embed(
            description=f'🚫 В этом канале сейчас никто не играет!',
            color=discord.Color.red()
        )
        await ctx.reply(embed=embed)
        return
    
    # checking if some sneaky ass pressed the button
    if game.starter_id != ctx.author.id:
        embed = discord.Embed(
            description=f'🚫 Не для тебя моя команда росла',
            color=discord.Color.red()
        )
        await ctx.reply(embed=embed)
        return
    
    # changing word
    word, events = mg.new_word(ctx.author.id, ctx.channel.id, ctx.guild.id)
    log(f'{ctx.author.id} changed word to {word}')
    
    # creating view
    view = discord.ui.View()

    view_btn = discord.ui.Button(
        style=discord.ButtonStyle.blurple,
        label='Посмотреть слово',
        emoji='📜'
    )
    view_btn.callback = view_word
    view.add_item(view_btn)

    skip_btn = discord.ui.Button(
        style=discord.ButtonStyle.gray,
        label='Новое слово',
        emoji='⏩'
    )
    skip_btn.callback = skip_word
    view.add_item(skip_btn)

    # sending the new word
    embed = discord.Embed(
        description=f'📜 Нажми на кнопку, чтобы посмотреть новое слово',
        color=discord.Color.green()
    )
    if events != []:
        embed.set_footer(text=utils.events_to_text(ctx.author.name, events))
    await ctx.reply(embed=embed, view=view)



# skip turn command

@bot.hybrid_command(
    name='skip', description='Пропускает ваш ход.',
    aliases=['stop']
)
async def skip(ctx:commands.Context):
    log(f'{ctx.author.id} ran {PREFIX}skip')

    # checking for ongoing game
    game = mg.get_game(ctx.channel.id)
    if game == None:
        embed = discord.Embed(
            description=f'🚫 В этом канале сейчас никто не играет!',
            color=discord.Color.red()
        )
        await ctx.reply(embed=embed)
        return
    
    # checking if some sneaky ass pressed the button
    if game.starter_id != ctx.author.id:
        embed = discord.Embed(
            description=f'🚫 Не для тебя моя команда росла',
            color=discord.Color.red()
        )
        await ctx.reply(embed=embed)
        return
    
    # ending game
    mg.games.pop(game.channel_id)
    log(f'{ctx.author.id} removed game in {game.channel_id}')
    
    # creating view
    view = discord.ui.View()

    new_game_btn = discord.ui.Button(
        style=discord.ButtonStyle.blurple,
        label='Играть ещё',
        emoji='🎮'
    )
    new_game_btn.callback = new_game
    view.add_item(new_game_btn)

    # sending the message
    embed = discord.Embed(
        description=f'🤚 <@{game.starter_id}> пропустил свой ход!',
        color=discord.Color.green()
    )
    await ctx.reply(embed=embed, view=view)



# play command

@bot.hybrid_command(
    name='start', description='Начинает игру в чате.',
    aliases=['play','begin']
)
async def start(ctx:commands.Context):
    log(f'{ctx.author.id} ran {PREFIX}start')

    # checking for restrictions
    restr = mg.get_restriction(ctx.channel.id)
    if restr != None and restr.guesser_id != ctx.author.id:
        embed = discord.Embed(
            description=f'🚫 Игра разблокируется для всех <t:{int(restr.until)}:R>',
            color=discord.Color.red()
        )
        await ctx.reply(embed=embed)
        return

    # checking for ongoing game
    game = mg.get_game(ctx.channel.id)
    if game != None:
        embed = discord.Embed(
            description=f'🚫 Этот раунд закончится <t:{int(game.until)}:R>,'\
                f' а пока объясняет слово <@{game.starter_id}>.',
            color=discord.Color.red()
        )
        await ctx.reply(embed=embed)
        return
    
    # creating game
    word, events = mg.new_game(
        ctx.guild.id, ctx.channel.id,
        ctx.message.id, ctx.author.id, ctx.author.name
    )

    # creating view
    view = discord.ui.View()

    view_btn = discord.ui.Button(
        style=discord.ButtonStyle.blurple,
        label='Посмотреть слово',
        emoji='📜'
    )
    view_btn.callback = view_word
    view.add_item(view_btn)

    skip_btn = discord.ui.Button(
        style=discord.ButtonStyle.gray,
        label='Новое слово',
        emoji='⏩'
    )
    skip_btn.callback = skip_word
    view.add_item(skip_btn)

    turn_btn = discord.ui.Button(
        style=discord.ButtonStyle.red,
        label='Пропустить ход',
        emoji='❌'
    )
    turn_btn.callback = end_turn
    view.add_item(turn_btn)

    # creating embed
    embed = discord.Embed(
        description=f'💭 <@{ctx.author.id}> загадывает слово!',
        color=discord.Color.green()
    )
    if events != []:
        embed.set_footer(text=utils.events_to_text(ctx.author.name, events))

    await ctx.reply(embed=embed, view=view)



# profile command

@bot.hybrid_command(
    name='profile',
    description='Показывает ваш профиль или профиль другого игрока.',
    aliases=['acc','bal','balance','stat','stats','account']
)
@discord.app_commands.describe(user='Пользователь')
async def profile(ctx:commands.Context, user:discord.User=None):
    log(f'{ctx.author.id} ran {PREFIX}profile')

    if user == None:
        user = ctx.author

    # checking if the user's a bot
    if user.bot:
        embed = discord.Embed(
            description=f'🚫 Боты не умеют играть в Крокодила!',
            color=discord.Color.red()
        )
        await ctx.reply(embed=embed)
        return

    # checking if the profile exists
    if user.id not in mg.users:
        text = f'<@{user.id}> еще не играл(а)'\
            if ctx.author.id != user.id else 'Вы еще не играли'
        embed = discord.Embed(
            description=f'🚫 {text} в Крокодила!',
            color=discord.Color.red()
        )
        await ctx.reply(embed=embed)
        return
    
    bot_user = mg.users[user.id]

    # creating embed
    embed = discord.Embed(
        description=f'Профиль <@{user.id}>',
        color=discord.Color.green()
    )
    embed.add_field(
        name=f'💎 **{bot_user.moonrocks}** лунных камней',
        value=''
    )
    xp_left = bot_user.xp-bot_user.xp_explained-bot_user.xp_guessed
    embed.add_field(
        name=f'✨ Всего опыта: **{bot_user.xp} XP**',
        value=f':white_small_square: Получено отгадыванием: **{bot_user.xp_guessed} XP**\n'\
            f':white_small_square: Получено загадыванием: **{bot_user.xp_explained} XP**\n'+\
            (f':white_small_square: Остальное: **{xp_left} XP**\n' if xp_left != 0 else ''),
        inline=False  
    )
    embed.add_field(
        name=f'📜 Статистика слов',
        value=f':white_small_square: Отгадано: **{bot_user.words_guessed}**\n'\
            f':white_small_square: Загадано: **{bot_user.words_explained}**\n'\
            f':white_small_square: Пропущено/выбрано: **{bot_user.words_chosen}**',
        inline=False
    )
    embed.add_field(
        name=f'📊 Рейтинг',
        value=f':white_small_square: Лайков: **{bot_user.likes}**\n'\
            f':white_small_square: Дизлайков: **{bot_user.dislikes}**',
        inline=False
    )
    embed.add_field(
        name=f'⌚ Начал(а) играть',
        value=f':white_small_square: <t:{int(bot_user.started_playing)}> (<t:{int(bot_user.started_playing)}:R>)'
    )

    await ctx.reply(embed=embed)



# leaderboard command

@bot.hybrid_command(
    name='leaders',
    description='Показывает таблицу лидеров этого сервера.',
    aliases=['leaderboard','lb']
)
@discord.app_commands.describe(places='Кол-во мест (10 по умолчанию)')
async def leaders(ctx:commands.Context, places:int=10):
    log(f'{ctx.author.id} ran {PREFIX}leaders')

    # haven't played yet
    if ctx.guild.id not in mg.guilds\
        or len(mg.guilds[ctx.guild.id].leaderboard) == 0:
            embed = discord.Embed(
                description=f'🚫 Тут пока не играли в Крокодила!',
                color=discord.Color.red()
            )
            await ctx.reply(embed=embed)
            return
    
    # checking amount
    if places < 1 or places > 20:
        embed = discord.Embed(
            description=f'🚫 Можно запросить от 1 до 20 мест!',
            color=discord.Color.red()
        )
        await ctx.reply(embed=embed)
        return
    
    # getting leaders
    guild = mg.guilds[ctx.guild.id]
    leaders = guild.get_leaderboard(places)
    leader_text = ''

    place = 0
    old_amount = 0

    for id, amount in leaders.items():
        if old_amount != amount:
            place += 1
            old_amount = amount

        text = ['`🥇`','`🥈`','`🥉`']\
            [place-1] if place <= 3 else f'`#{place}`'
        leader_text += f'{text} <@{id}>  -  **`{amount}`**\n'

    embed = discord.Embed(color=discord.Color.green())
    embed.add_field(
        name=f'Таблица лидеров {ctx.guild.name} по угадываниям',
        value=leader_text
    )
    embed.set_footer(
        text=f'Всего людей: {len(guild.leaderboard)}\n'\
            f'Всего угадываний: {guild.total_words_guessed}')
    await ctx.reply(embed=embed)



# transfer command

@bot.hybrid_command(
    name='pay',
    description='Переводит лунные камни на счёт другого игрока.',
    aliases=['transfer']
)
@discord.app_commands.describe(user='Пользователь', amount='Количество')
async def pay(ctx:commands.Context, user:discord.User, amount:str):
    log(f'{ctx.author.id} ran {PREFIX}pay')

    # checking if the user's a bot
    if user.bot:
        embed = discord.Embed(
            description=f'🚫 Боты не умеют играть в Крокодила!',
            color=discord.Color.red()
        )
        await ctx.reply(embed=embed)
        return

    # checking if the user's himself
    if user.id == ctx.author.id:
        embed = discord.Embed(
            description=f'🚫 А ты чего ожидал?',
            color=discord.Color.red()
        )
        await ctx.reply(embed=embed)
        return
    
    # transferring
    state, amount = mg.transfer_moonrocks(ctx.author.id, user.id, amount)

    # error messages
    if state != 0:
        text = [
            'Количество должно быть целым числом больше нуля!',
            'Пользователь еще не играл в Крокодила!',
            'У вас недостаточно лунных камней для перевода!\n\n'\
                f'Ваш баланс: **{mg.users[ctx.author.id].moonrocks}💎**'
        ][state-1]

        embed = discord.Embed(
            description=f'🚫 {text}',
            color=discord.Color.red()
        )
        await ctx.reply(embed=embed)
        return
    
    # success message
    embed = discord.Embed(
        description=f'✅ Вы успешно перевели **{amount}** лунных'\
            f' камней пользователю <@{user.id}>!',
        color=discord.Color.green()
    )

    await ctx.reply(embed=embed)



# running bot

bot.run(TOKEN)