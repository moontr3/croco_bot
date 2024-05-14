from typing import *

PREFIX: str = 'c!'

ADMINS: List[int] = [698457845301248010] # list of bot admins
                                         # change these to yours

LANG_FOLDER: str = 'lang/'
LOG_FILE: str = 'log.txt'
DATA_FILE: str = 'data.json'
USERS_FILE: str = 'users.json'

FILTER_SYMBOLS_BY_DEFAULT: bool = False
RESTRICTION_TIME: int = 10 # time in seconds between guessing the word
                           # and any user being able to start the game
GAME_LENGTH: int = 60*5 # time given in seconds to explain the word
                        # before the game stops
