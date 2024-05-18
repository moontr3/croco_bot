import os
import random
import time
from typing import *
import json
from log import *
from config import *


# user

class User:
    def __init__(self, id:str, data:dict):
        '''
        Represents a user in the bot.
        '''
        self.id: int = int(id)
        self.data: dict = data

        self.started_playing: int = data.get('started_playing',time.time())

        self.xp: int = data.get('xp', 0)
        self.xp_guessed: int = data.get('xp_guessed', 0)
        self.xp_explained: int = data.get('xp_explained', 0)
        self.moonrocks: int = data.get('moonrocks',0)

        self.words_guessed: int = data.get('words_guessed',0)
        self.words_explained: int = data.get('words_explained',0)
        self.words_chosen: int = data.get('words_chosen',0)

        self.likes: int = data.get('likes', 0)
        self.dislikes: int = data.get('dislikes', 0)


    def to_dict(self) -> dict:
        return {
            "xp": self.xp,
            "xp_guessed": self.xp_guessed,
            "xp_explained": self.xp_explained,
            "moonrocks": self.moonrocks,
            "words_guessed": self.words_guessed,
            "words_explained": self.words_explained,
            "words_chosen": self.words_chosen,
            "started_playing": self.started_playing,
            "likes": self.likes,
            "dislikes": self.dislikes,
        }


# language

class Language:
    def __init__(self, key:str, data:dict):
        '''
        Represents a language in the game.
        '''
        self.key: str = key
        self.data: dict = data

        self.name: str = data['name']
        self.file: str = LANG_FOLDER+data['file']
        self.emoji: str = data['emoji']

        self.reload_file()

    
    def reload_file(self):
        '''
        Reloads language file.
        '''
        log(f'Loading language {self.key}...', 'api',)

        with open(self.file, encoding='utf-8') as f:
            self.raw: str = f.read()
        
        # getting word list
        log(f'[{self.key}] Parsing words...', 'api',)

        self.words: Set[str] = self.raw.split('\n')
        self.words = {i.lower().replace('ё','е') for i in self.words if i != ''}
        self.word_amount: int = len(self.words)

        # filtered list only with words without symbols
        log(f'[{self.key}] Filtering words...', 'api',)

        self.filtered_words: Set[str] = {
            i for i in self.words if i.isalpha()
        }
        self.filtered_word_amount: int = len(self.filtered_words)

        log(f'Language {self.key} loaded', 'api', level=SUCCESS,)


# guild

class Guild:
    def __init__(
        self, id:str, data:dict,
        default_language:str
    ):
        '''
        Represents a Discord guild.
        '''
        self.id: int = int(id)
        self.data: dict = data

        self.total_words_guessed: int = data.get('total_words_guessed',0)
        self.leaderboard: Dict[int, int] = {
            int(key): value for key, value in data.get('leaderboard',{}).items()
        }

        self.language: str = data.get('language',default_language)
        self.filter: bool = data.get('filter',FILTER_SYMBOLS_BY_DEFAULT)


    def word_guessed(self, id:int):
        '''
        Adds one game as the passed ID to the leaderboard
        and one to the games counter.
        '''
        self.total_words_guessed += 1

        # adding to leaderboard
        if id not in self.leaderboard:
            self.leaderboard[id] = 0
        self.leaderboard[id] += 1


    def get_leaderboard(self, amount:int) -> Dict[int, int]:
        '''
        Returns a sorted leaderboard with the specified amount
        of entries.
        '''
        # sorting the leaderboard by value
        _leaderboard = dict(sorted(
            self.leaderboard.items(),
            key=lambda x: x[1],
            reverse=True
        ))

        # getting the first couple of values
        _leaderboard = dict(list(_leaderboard.items())[:amount])

        return _leaderboard


    def to_dict(self) -> dict:
        return {
            "total_words_guessed": self.total_words_guessed,
            "leaderboard": self.leaderboard,
            "filter": self.filter,
            "language": self.language
        }


# game

class Game:
    def __init__(
        self, channel_id:int,
        message_id:int, starter_id:int,
        word:str, starter_name:str
    ):
        self.channel_id: int = channel_id
        self.message_id: int = message_id
        self.starter_id: int = starter_id
        self.starter_name: str = starter_name
        self.word: str = word
        self.moonrocks: int = max(0,int(len(word)/5)-1)
        self.until: float = time.time()+GAME_LENGTH


    def change_word(self, new_word:str):
        self.word: str = new_word
        self.moonrocks: int = max(0,int(len(new_word)/5)-1)


# restriction

class Restriction:
    def __init__(
        self, channel_id:int, guesser_id:int, until:float
    ):
        self.channel_id: int = channel_id
        self.guesser_id: int = guesser_id
        self.until: float = until


# reaction

class Reaction:
    def __init__(self, message_id:int, explainer_id:int):
        self.message_id: int = message_id
        self.explainer_id: int = explainer_id

        self.likes: List[int] = []
        self.dislikes: List[int] = []

    
    def get_user(self, id:int) -> int:
        '''
        Returns 0 if did not react, 1 if liked, 2 if disliked
        '''
        if id in self.likes:
            return 1
        elif id in self.dislikes:
            return 2
        
        return 0


# manager

class Manager:
    def __init__(
        self,
        data_file_path:str,
        users_file_path:str
    ):
        '''
        Manages all games, users, languages and more.
        '''
        self.data_file: str = data_file_path
        self.users_file: str = users_file_path

        self.games: Dict[int, Game] = {}
        self.restrictions: Dict[int, Restriction] = {}

        self.reactions: Dict[int, Reaction] = {}

        self.load_data()
        self.load_users()


    def new_db(self):
        '''
        Completely overwrites the current user data
        and creates a new database from scratch.
        '''
        self.users: Dict[int, User] = {}
        self.guilds: Dict[int, Guild] = {}

        self.commit()
        log('Created new database', 'api', level=SUCCESS)


    def clone_db(self):
        '''
        Copies the database into a backup file.
        '''
        with open(self.users_file, encoding='utf8') as f:
            data = f.read()

        with open(f'{self.users_file}.bak', 'w', encoding='utf8') as f:
            f.write(data)

        log(f'Cloned database into {self.users_file}.bak', 'api', level=SUCCESS)


    def load_data(self):
        '''
        Reloads data.json file.
        '''
        log('Loading data...', 'api')

        with open(self.data_file, encoding='utf-8') as f:
            data: dict = json.load(f)

        # loading languages
        log('Parsing languages...', 'api')
        self.default_language: str = data['default_language']
        self.languages: Dict[str, Language] = {}

        for key, lang in data['languages'].items():
            self.languages[key] = Language(key, lang)

        log('Data loaded', 'api', level=SUCCESS)


    def load_users(self):
        '''
        Reloads user.json file.
        '''
        log('Loading database...', 'api')

        # checking if file exists
        if not os.path.exists(self.users_file):
            self.new_db()
            return
        
        # trying to open the file
        try:
            with open(self.users_file, encoding='utf-8') as f:
                raw: dict = json.load(f)

        # creating the database if failed
        except Exception as e:
            log(f'Failed opening the database: {e}', 'api', level=ERROR)
            self.clone_db()
            self.new_db()
            return
        
        # parsing users
        log('Parsing users...', 'api')
        self.users = {int(id): User(id, data) for id, data in raw['users'].items()}
        
        # parsing guilds
        log('Parsing guilds...', 'api')
        self.guilds = {int(id): Guild(
            id, data, self.default_language
        ) for id, data in raw['guilds'].items()}

        log('Database loaded', 'api', level=SUCCESS)


    def commit(self):
        '''
        Dumps user data into a file.
        '''
        data = {
            "users": {
                i: self.users[i].to_dict() for i in self.users
            },
            "guilds": {
                i: self.guilds[i].to_dict() for i in self.guilds
            }
        }

        with open(self.users_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)


    def check_user(self, id:int) -> List[dict]:
        '''
        Checks if user is in database. If not, creates one.
        '''
        if id not in self.users:
            log(f'Created a new user {id}', 'api')
            self.users[id] = User(id, {})
            self.commit()

        # just in case
        events: List[dict] = []

        return events


    def check_guild(self, id:int):
        '''
        Checks if guild is in database. If not, creates one.
        '''
        if id in self.guilds:
            return
        
        log(f'Created a new guild {id}', 'api')
        self.guilds[id] = Guild(id, {}, self.default_language)
        self.commit()


    def get_word(self, guild_id:int) -> str:
        '''
        Returns a random word from guild's set list.
        '''
        # getting guild settings
        self.check_guild(guild_id)
        guild = self.guilds[guild_id]
        language: Language = self.languages[guild.language]
        
        # choosing word
        word_list: Set[str] = language.filtered_words\
            if guild.filter else language.words
        word: str = random.choice(list(word_list))

        return word


    def add_xp(self, id:int, amount:int) -> User:
        '''
        Adds XP to the specified user. Returns the user.
        '''
        self.check_user(id)
        self.users[id].xp += amount
        self.commit()

        log(f'Added {amount} XP to {id}', 'api')
        return self.users[id]
    

    def transfer_moonrocks(
        self, from_id:int, to_id:int, amount:str
    ) -> "int":
        '''
        Transfers moonrocks from one user to another.

        Returns 1 if `amount` is not a number,
        2 if `to_id` is not a registered user,
        3 if not enough to transfer,
        0 if transfer successful.
        '''
        # checking users
        self.check_user(from_id)

        if to_id not in self.users:
            return 2, None

        # getting amount
        if amount.lower() in ['all','все','всё']:
            amount = int(self.users[from_id].moonrocks)

            if amount <= 0:
                return 3, None

        else:
            try:
                amount = int(amount)
                assert amount > 0
            except:
                return 1, None
            
        # checking balance
        if self.users[from_id].moonrocks < amount:
            return 3, None
        
        # transferring
        self.users[from_id].moonrocks -= amount
        self.users[to_id].moonrocks += amount
        self.commit()

        log(f'Transferred {amount} moonrocks from {from_id} to {to_id}', 'api')
        return 0, amount
    

    def like(self, game_id:int, user_id:int) -> "int | None":
        '''
        Returns None if no game found.

        0 if liked successfully.
        1 if already liked.
        2 if already disliked.
        3 if liking himself.
        '''
        self.check_user(user_id)

        if game_id not in self.reactions:
            return None
        
        r = self.reactions[game_id]

        # checking if liked own explanation
        if r.explainer_id == user_id:
            return 3

        state = r.get_user(user_id)

        # liking
        if state == 0:
            r.likes.append(user_id)
            self.users[r.explainer_id].likes += 1
            self.commit()
            # adding xp to author
            log(f'{user_id} liked {game_id}, +1 XP to {r.explainer_id}', 'api')
            self.add_xp(r.explainer_id, 1)

        return state 
    

    def dislike(self, game_id:int, user_id:int) -> "int | None":
        '''
        Returns None if no game found.

        0 if disliked successfully.
        1 if already liked.
        2 if already disliked.
        3 if disliking himself.
        '''
        self.check_user(user_id)

        if game_id not in self.reactions:
            return None
        
        r = self.reactions[game_id]

        # checking if liked own explanation
        if r.explainer_id == user_id:
            return 3
        
        state = r.get_user(user_id)

        # disliking
        if state == 0:
            r.dislikes.append(user_id)
            self.users[r.explainer_id].dislikes += 1
            self.commit()
            log(f'{user_id} disliked {game_id}', 'api')

        return state 


    def get_restriction(
        self, channel_id:int
    ) -> "Restriction | None":
        '''
        Returns the channel restriction.

        If there is none, returns None.
        
        If the restriction expired, removes the channel restriction.
        '''
        if channel_id not in self.restrictions:
            return None
        
        if self.restrictions[channel_id].until <= time.time():
            # removing expired restriction
            self.restrictions.pop(channel_id)
            return None
        
        return self.restrictions[channel_id]
    

    def get_game(self, channel_id:int) -> "Game | None":
        '''
        Returns the game if it exists in the current channel.
        Otherwise returns None.
        '''
        if channel_id not in self.games:
            return None
        
        if self.games[channel_id].until <= time.time():
            # removing expired game
            self.games.pop(channel_id)
            return None
        
        return self.games[channel_id]
    

    def new_game(
        self,
        guild_id:int,
        channel_id:int,
        message_id:int,
        starter_id:int,
        starter_name:str
    ) -> Tuple[str, List[dict]]:
        '''
        Starts a new game. Returns the word and the list of events.
        '''
        # adding stat
        events = self.check_user(starter_id)
        self.users[starter_id].words_chosen += 1

        # creating game
        word: str = self.get_word(guild_id)

        self.games[channel_id] = Game(
            channel_id, message_id, starter_id, word, starter_name
        )

        log(f'{starter_id} started new game in {channel_id} with word {word}', 'api')
        self.commit()
        return word, events
    

    def stop_game(
        self, channel_id:int
    ):
        '''
        Stops the ongoing game.
        '''
        if channel_id in self.games:
            log(f'Game in {channel_id} stopped', 'api')
            self.games.pop(channel_id)


    def new_word(
        self, user_id:int, channel_id:int, guild_id:int
    ) -> "str | None":
        '''
        Changes the word in a game. Returns the new word.
        Returns None if there's no game in the channel.
        '''
        # checking for a game
        if channel_id not in self.games:
            return
        
        # adding stat
        events = self.check_user(user_id)
        self.users[user_id].words_chosen += 1
        
        # changing word
        word: str = self.get_word(guild_id)
        self.games[channel_id].change_word(word)

        self.commit()
        return word, events
    

    def add_reactions(
        self, message_id:int,
        explainer_id:int
    ):
        '''
        Adds a reaction manager.
        '''
        self.reactions[message_id] = Reaction(
            message_id, explainer_id
        )
    

    def word_guessed(
        self, channel_id:int,  
        guild_id:int,
        guesser_id:int
    ):
        '''
        Writes to the stat counters and adds XP based on word length.
        Returns the game.
        '''
        game: Game = self.games[channel_id]
        explainer_id: int = game.starter_id

        guesser_events: List[dict] = []
        explainer_events: List[dict] = []

        guesser_events.extend(self.check_user(guesser_id))
        explainer_events.extend(self.check_user(explainer_id))
        self.check_guild(guild_id)

        # finish game
        self.games.pop(channel_id)
        self.restrictions[channel_id] = Restriction(
            channel_id, guesser_id, time.time()+RESTRICTION_TIME
        )

        # add moonrocks
        self.users[explainer_id].moonrocks += game.moonrocks

        # add stat
        self.users[guesser_id].xp += len(game.word)
        self.users[guesser_id].xp_guessed += len(game.word)
        self.users[guesser_id].words_guessed += 1

        self.users[explainer_id].xp += len(game.word)
        self.users[explainer_id].xp_explained += len(game.word)
        self.users[explainer_id].words_explained += 1

        self.guilds[guild_id].word_guessed(guesser_id)
        guesser_events.extend(self.check_user(guesser_id))

        self.commit()
        log(f'{guesser_id} guessed the word {game.word} and got {len(game.word)} XP', 'api')
        return game, guesser_events, explainer_events
