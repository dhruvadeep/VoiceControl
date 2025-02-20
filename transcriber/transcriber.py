from io import BytesIO

import numpy as np
import uvicorn
import whisper
from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import validate_call
from pydub.audio_segment import AudioSegment

APP = FastAPI()
APP.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change to specific domains in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DEVICE = "cpu"
try:
    MODEL = whisper.load_model("base.en", DEVICE)
except Exception:
    MODEL = whisper.load_audio("base.en")

# incomplete: need to add more commands
COMMANDS = [
    (["search for", "search", "bing"], "search"),
    (["open browser", "open page", "open new page"], "open_new_window   "),
    (["close browser", "shutdown browser"], "close_browser"),
    (["close current window", "close window"], "close_current_window"),
    (["open camera", "open the camera"], "capture"),
    (["take screenshot", "take a screenshot"], "screenshot"),
    (
        [
            "show ram info",
            "get ram info",
            "show ram usage",
            "get ram usage",
            "ram",
            "take ram",
        ],
        "ram",
    ),
    (
        ["show disk info", "get disk info", "show disk usage", "get disk usage"],
        "get_disk",
    ),
    (["show cpu usage", "get cpu usage"], "get_cpu_usage"),
    (["show cpu info", "get cpu info"], "get_cpu_info"),
    (
        [
            "show system info",
            "get system info",
            "show hardware info",
            "get hardware info",
        ],
        "get_all",
    ),
    (["show life", "show life help"], "get_all"),
]


@validate_call
def commands(transcription: str) -> dict:
    transcription = transcription.lower()
    user_instructions = []
    for i in transcription.split("and"):
        for j in i.split("."):
            for k in j.split(","):
                user_instructions.append(k)
    responses = []
    for user_instruction in user_instructions:
        for queries, command in COMMANDS:
            for query in queries:
                if query in user_instruction:
                    additional_information = user_instruction.split(query)[1]
                    response = {
                        "command": command,
                        "additional": additional_information,
                    }
                    responses.append(response)
                    break
    return {"response": responses}


@APP.post("/transcribe")
async def transcribe(recording: UploadFile = File(...)):
    audio = await recording.read()
    audio_buffer = BytesIO(audio)
    audio_segment = AudioSegment.from_file(audio_buffer).set_frame_rate(16000).set_channels(1).set_sample_width(2)
    samples = np.array(audio_segment.get_array_of_samples(), dtype=np.float32) / 32768
    result = MODEL.transcribe(
        samples,
        temperature=0,
        condition_on_previous_text=False,
        word_timestamps=True,
        # hallucination_silence_threshold=0.7,
        # no_speech_threshold=0.8
    )
    transcription = result["text"].lower()
    response = commands(transcription)
    return {"response": response, "message": transcription}


if __name__ == "__main__":
    uvicorn.run("__main__:APP", host="0.0.0.0", port=8005, reload=True)
