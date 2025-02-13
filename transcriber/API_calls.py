import requests
from pydantic import validate_call


"""
command is the defined command in the COMMAND list.

user_instruction is the instruction passed by the user.

suppose user instruction is 'search for elden ring' and command is 'search for'
then split while sending requests, send only 'elden ring' part
"""


@validate_call
def search(command:str, user_instruction:str):
    pass

@validate_call
def open_browser(command:str, user_instruction:str):
    pass

@validate_call
def close_browser(command:str, user_instruction:str):
    pass

@validate_call
def close_current_window(command:str, user_instruction:str):
    pass

@validate_call
def open_camera(command:str, user_instruction:str):
    pass

@validate_call
def screenshot(command:str, user_instruction:str):
    pass

@validate_call
def get_ram(command:str, user_instruction:str):
    pass

@validate_call
def get_disk(command:str, user_instruction:str):
    pass

@validate_call
def get_cpu_usage(command:str, user_instruction:str):
    pass

@validate_call
def get_cpu_info(command:str, user_instruction:str):
    pass

@validate_call
def get_all(command:str, user_instruction:str):
    pass