from typing import *


def events_to_text(username:str, events:List[dict]) -> str:
    '''
    Converts a list of events into text to display in the embed.
    '''
    # converting events to text
    text_events: List[str] = []
    
    for i in events:
        pass

    # composing message
    text = f'{username} {", ".join(text_events)}!'
    return text