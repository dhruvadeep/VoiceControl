import whisper
from torch import cuda
from API_calls import *

DEVICE = "cuda" if cuda.is_available() else "cpu"
try:
    MODEL = whisper.load_model("medium.en", DEVICE)
except:
    MODEL = whisper.load_audio("medium.en", "cpu")
COMMANDS = [
    (["search for", "search", "bing"], open_browser_and_search),
    (["open browser"], open_browser),
    (["open camera"], open_camera),
    (["take screenshot", "take a screenshot"], screenshot),
    (["show ram info", "get ram info", "show ram usage", "get ram usage"], get_ram),
    (["show disk info", "get disk info", "show disk usage", "get disk usage"], get_disk),
    (["show cpu usage", "get cpu usage"], get_cpu_usage),
    (["show cpu info", "get cpu info"], get_cpu_info),
    (["show system info", "get system info", "show hardware info", "get hardware info"], get_all)
]

def commands(transcription: str):
    command_executed = False
    try:
        for cmds, fn in COMMANDS:
            for cmd in cmds:
                if cmd in transcription:
                    if cmd == "search for":
                        query = " ".join(transcription.split("search for")[1:])
                        if query != "":
                            fn(query)
                            command_executed = True
                        break
                    elif cmd == "search":
                        query = " ".join(transcription.split("search")[1:])
                        if query != "":
                            fn(query)
                            command_executed = True
                        break
                    elif cmd == "bing":
                        query = " ".join(transcription.split("bing")[1:])
                        if query != "":
                            fn(query)
                            command_executed = True
                        break
                    else:
                        fn()
                        command_executed = True
                        break
            if command_executed:
                break
    except:
        print("some unexpected error occured")
        speak("some unexpected error occured")
    if not command_executed:
        speak("no command executed")

def transcribe(recording):
    print("shape of the recording", recording.shape)
    result = MODEL.transcribe(
        recording,
        temperature=0,
        condition_on_previous_text=False,
        word_timestamps=True,
        # hallucination_silence_threshold=0.7,
        # no_speech_threshold=0.8
    )
    print("text:", result["text"])
    transcription = result["text"].lower()
    commands(transcription)