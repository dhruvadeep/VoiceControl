"""Audio transcription and command extraction service using FastAPI and PyYAML."""

from io import BytesIO
from typing import Annotated

import numpy as np
import uvicorn
import whisper
import yaml
import httpx
import toml
from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import validate_call
from pydub.audio_segment import AudioSegment

from models import CommandListResponse, CommandResponse, FinalResponse

APP = FastAPI()
APP.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change to specific domains in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class CannotLoadModelError(Exception):
    """CannotLoadModelError occurs when you are facing issues while loading a model."""

def logger_info(message:str):
    "Log message in a server."
    url = toml.load("log_config.toml")["url"]+"/log"
    httpx.request(method="POST", url=url, json={"message":message})


DEVICE = "cpu"

try:
    MODEL = whisper.load_model("base.en", device=DEVICE)
except CannotLoadModelError:
    # Fall back in case there's a problem loading the model
    # (This except block is a bit unusual. Possibly you meant another fallback.)
    MODEL = whisper.load_audio("base.en", DEVICE)

# ------------------------------------------------
# Load commands from `commands.yaml`
# ------------------------------------------------
COMMANDS_YAML_PATH = "commands.yaml"

try:
    with open(COMMANDS_YAML_PATH, encoding="utf-8") as file:
        YAML_COMMANDS = yaml.safe_load(file)
except FileNotFoundError:
    logger_info(f"Could not find {COMMANDS_YAML_PATH} file.")
    YAML_COMMANDS = []

# Flatten the YAML command structure into a list of (List[str], str) tuples.
# Example: [ (["open browser", "start browser"], "open_browser"), ... ]
COMMAND_LIST: list[tuple[list[str], str]] = []

for category_dict in YAML_COMMANDS:
    for _, command_dict in category_dict.items():
        for cmd, queries in command_dict.items():
            COMMAND_LIST.append((queries, cmd))


@validate_call
def commands(transcription: str) -> CommandListResponse:
    """Take a transcription string as input and match it against known commands
    loaded from the YAML file.

    Returns:
        CommandListResponse: A response object containing matched commands.

    """
    transcription_lower = transcription.lower()

    # Break down user instructions on "and", ".", "," so we can match each part.
    user_instructions = []
    for splitter_part in transcription_lower.split("and"):
        for period_part in splitter_part.split("."):
            for comma_part in period_part.split(","):
                user_instructions.append(comma_part.strip())

    responses = []
    for user_instruction in user_instructions:
        for queries, command_key in COMMAND_LIST:
            for query in queries:
                query_lower = query.lower()
                if query_lower in user_instruction:
                    # Attempt to find any additional text after the query
                    try:
                        additional_information = user_instruction.split(query_lower)[1].strip()
                    except IndexError:
                        additional_information = ""
                    logger_info("Command recorded: "+ command_key)
                    response = CommandResponse(command=command_key, additional=additional_information)
                    responses.append(response)
                    break

    logger_info("Sending commands")
    return CommandListResponse(commands=responses)


@APP.post("/transcribe", response_model=FinalResponse)
async def transcribe(recording: Annotated[UploadFile, File(...)]) -> FinalResponse:
    """Handle audio transcription requests.

    Args:
        recording (UploadFile): The audio file upload.

    Returns:
        FinalResponse: An object containing transcription text and matched commands.

    """
    logger_info("Transcribe request received.")

    # Read the uploaded audio content
    audio = await recording.read()
    audio_buffer = BytesIO(audio)

    # Convert the audio to single-channel, 16kHz
    audio_segment = AudioSegment.from_file(audio_buffer).set_frame_rate(16000).set_channels(1).set_sample_width(2)

    # Convert samples to float32 in range [-1,1]
    samples = np.array(audio_segment.get_array_of_samples(), dtype=np.float32) / 32768

    # Perform transcription
    result = MODEL.transcribe(
        samples,
        temperature=0,
        condition_on_previous_text=False,
        word_timestamps=True,
    )
    transcription = result["text"]
    logger_info("Raw transcription: " + transcription)

    # Generate commands from transcription
    response = commands(transcription)

    # Return the final response containing transcription and commands
    logger_info("Sending final response.")
    return FinalResponse(response=response, message=transcription)


if __name__ == "__main__":
    uvicorn.run("__main__:APP", host="0.0.0.0", port=8005, reload=True)
