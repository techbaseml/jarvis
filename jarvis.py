import os
import re
import json
import time
import shutil
import socket
import platform
import subprocess
import webbrowser
import datetime
import threading

import requests
import psutil
import speech_recognition as sr
import sounddevice as sd


# =========================================================
# JARVIS CONFIGURATION
# =========================================================

API_KEY = os.getenv("OPENROUTER_API_KEY")
API_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "openrouter/free"

ASSISTANT_NAME = "JARVIS"
CREATOR_NAME = "Sanjay"

# Voice settings
VOICE_LANGUAGE = "en-US"
VOICE_RATE = 180

# Microphone settings
MIC_SAMPLE_RATE = 16000
MIC_CHANNELS = 1


# =========================================================
# STARTUP CHECK
# =========================================================

if not API_KEY:
    print("JARVIS: OPENROUTER_API_KEY is not set.")
    print()
    print("Make sure your Windows User environment variable exists.")
    input("Press Enter to exit...")
    raise SystemExit


# =========================================================
# TEXT TO SPEECH
# Windows built-in SAPI - no extra package required
# =========================================================

def speak(text):
    """
    Make JARVIS speak using Windows Speech API.
    """

    if not text:
        return

    # Clean markdown for speech
    speech_text = text.replace("*", "")
    speech_text = speech_text.replace("#", "")
    speech_text = speech_text.replace("`", "")

    # Limit extremely long speech
    if len(speech_text) > 1200:
        speech_text = speech_text[:1200] + "."

    powershell_script = r'''
Add-Type -AssemblyName System.Speech
$speak = New-Object System.Speech.Synthesis.SpeechSynthesizer
$speak.Rate = 0
$speak.Volume = 100
$text = [Console]::In.ReadToEnd()
$speak.Speak($text)
'''

    try:
        subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                powershell_script
            ],
            input=speech_text,
            text=True,
            capture_output=True,
            encoding="utf-8",
            errors="replace"
        )
    except Exception as e:
        print(f"JARVIS voice error: {e}")


# =========================================================
# MICROPHONE / VOICE INPUT
# =========================================================

recognizer = sr.Recognizer()


def listen_once():
    """
    Record from microphone using sounddevice,
    then send the audio to SpeechRecognition.
    """

    print()
    print("🎤 Listening... Speak now.")

    try:
        audio_data = sd.rec(
            int(MIC_SAMPLE_RATE * 6),
            samplerate=MIC_SAMPLE_RATE,
            channels=MIC_CHANNELS,
            dtype="int16"
        )

        sd.wait()

        # Convert NumPy audio into SpeechRecognition AudioData
        raw_audio = audio_data.tobytes()

        audio = sr.AudioData(
            raw_audio,
            MIC_SAMPLE_RATE,
            2
        )

        print("🔎 Recognizing...")

        text = recognizer.recognize_google(
            audio,
            language=VOICE_LANGUAGE
        )

        return text.strip()

    except sr.UnknownValueError:
        print("JARVIS: I couldn't understand that.")
        return ""

    except sr.RequestError as e:
        print(f"JARVIS: Speech recognition service error: {e}")
        return ""

    except Exception as e:
        print(f"JARVIS: Microphone error: {e}")
        return ""


# =========================================================
# PERMISSION SYSTEM
# =========================================================

def ask_permission(action):
    print()
    answer = input(
        f"JARVIS: I need your permission to {action}. "
        "Allow? (yes/no): "
    ).strip().lower()

    return answer in ("yes", "y")


# =========================================================
# APPLICATIONS
# =========================================================

APPLICATIONS = {
    "notepad": "notepad.exe",
    "calculator": "calc.exe",
    "calc": "calc.exe",
    "paint": "mspaint.exe",
}


def open_application(app_name):

    app_name = app_name.lower().strip()

    if app_name not in APPLICATIONS:
        print(f"JARVIS: I don't know how to open {app_name}.")
        return

    if not ask_permission(f"open {app_name}"):
        print("JARVIS: Permission denied.")
        return

    try:
        subprocess.Popen(APPLICATIONS[app_name])

        print(f"JARVIS: Opening {app_name}.")
        speak(f"Opening {app_name}.")

    except Exception as e:
        print(f"JARVIS: Failed to open {app_name}: {e}")


# =========================================================
# WEBSITES
# =========================================================

WEBSITES = {
    "youtube": ("https://www.youtube.com", "YouTube"),
    "google": ("https://www.google.com", "Google"),
    "github": ("https://github.com", "GitHub"),
}


def open_website(site_name):

    site_name = site_name.lower().strip()

    if site_name not in WEBSITES:
        print(f"JARVIS: I don't know that website.")
        return

    url, display_name = WEBSITES[site_name]

    if not ask_permission(f"open {display_name}"):
        print("JARVIS: Permission denied.")
        return

    try:
        webbrowser.open(url)

        print(f"JARVIS: Opening {display_name}.")
        speak(f"Opening {display_name}.")

    except Exception as e:
        print(f"JARVIS: Failed to open website: {e}")


# =========================================================
# CLEAN USER COMMAND
# =========================================================

def clean_command(command):

    command = command.lower().strip()

    prefixes = [
        "jarvis",
        "please",
        "can you",
        "could you",
        "would you",
        "will you",
        "hey jarvis",
    ]

    for prefix in prefixes:
        command = command.replace(prefix, "")

    return command.strip()


# =========================================================
# FIND APPLICATION
# =========================================================

def find_application(command):

    command = clean_command(command)

    patterns = [
        r"open\s+(notepad|calculator|calc|paint)",
        r"launch\s+(notepad|calculator|calc|paint)",
        r"start\s+(notepad|calculator|calc|paint)",
        r"run\s+(notepad|calculator|calc|paint)",
        r"go\s+to\s+(notepad|calculator|calc|paint)",
    ]

    for pattern in patterns:

        match = re.search(pattern, command)

        if match:
            return match.group(1)

    return None


# =========================================================
# FIND WEBSITE
# =========================================================

def find_website(command):

    command = clean_command(command)

    patterns = [
        r"open\s+(youtube|google|github)",
        r"launch\s+(youtube|google|github)",
        r"start\s+(youtube|google|github)",
        r"visit\s+(youtube|google|github)",
        r"go\s+to\s+(youtube|google|github)",
    ]

    for pattern in patterns:

        match = re.search(pattern, command)

        if match:
            return match.group(1)

    return None


# =========================================================
# REAL SYSTEM INFORMATION
# =========================================================

def get_battery():

    try:

        battery = psutil.sensors_battery()

        if battery is None:
            return "No battery was detected on this computer."

        percent = battery.percent

        if battery.power_plugged:
            status = "plugged in and charging"
        else:
            status = "running on battery"

        return f"Battery level is {percent:.0f} percent and the computer is {status}."

    except Exception as e:

        return f"I couldn't read the battery information: {e}"


def get_ram():

    try:

        memory = psutil.virtual_memory()

        total_gb = memory.total / (1024 ** 3)
        used_gb = memory.used / (1024 ** 3)
        available_gb = memory.available / (1024 ** 3)

        return (
            f"RAM usage is {memory.percent:.0f} percent. "
            f"{used_gb:.1f} GB used out of {total_gb:.1f} GB, "
            f"with {available_gb:.1f} GB available."
        )

    except Exception as e:

        return f"I couldn't read RAM information: {e}"


def get_cpu():

    try:

        cpu_name = platform.processor()

        if not cpu_name:
            cpu_name = "Unknown CPU"

        physical = psutil.cpu_count(logical=False)
        logical = psutil.cpu_count(logical=True)
        usage = psutil.cpu_percent(interval=1)

        return (
            f"CPU: {cpu_name}. "
            f"Current CPU usage is {usage:.0f} percent. "
            f"{physical or 'unknown'} physical cores and "
            f"{logical or 'unknown'} logical processors."
        )

    except Exception as e:

        return f"I couldn't read CPU information: {e}"


def get_storage():

    try:

        total, used, free = shutil.disk_usage("C:\\")

        total_gb = total / (1024 ** 3)
        used_gb = used / (1024 ** 3)
        free_gb = free / (1024 ** 3)

        return (
            f"C drive storage: {free_gb:.1f} GB free, "
            f"{used_gb:.1f} GB used, "
            f"{total_gb:.1f} GB total."
        )

    except Exception as e:

        return f"I couldn't read storage information: {e}"


def get_windows():

    try:

        version = platform.win32_ver()[1]

        if not version:
            version = platform.version()

        release = platform.win32_ver()[0]

        return f"Windows {release}, version {version}."

    except Exception as e:

        return f"I couldn't read the Windows version: {e}"


def get_computer_name():

    try:

        name = socket.gethostname()

        return f"The computer name is {name}."

    except Exception as e:

        return f"I couldn't read the computer name: {e}"


def get_system_summary():

    try:

        battery = psutil.sensors_battery()

        if battery:
            battery_text = f"{battery.percent:.0f}%"
        else:
            battery_text = "No battery detected"

        memory = psutil.virtual_memory()

        total, used, free = shutil.disk_usage("C:\\")

        cpu = platform.processor() or "Unknown CPU"

        computer = socket.gethostname()

        windows = platform.win32_ver()[0] or "Windows"

        return (
            f"Computer: {computer}\n"
            f"Windows: {windows}\n"
            f"CPU: {cpu}\n"
            f"RAM: {memory.percent:.0f}% used "
            f"({memory.total / (1024 ** 3):.1f} GB total)\n"
            f"Storage: {free / (1024 ** 3):.1f} GB free "
            f"of {total / (1024 ** 3):.1f} GB\n"
            f"Battery: {battery_text}"
        )

    except Exception as e:

        return f"Unable to read system information: {e}"


# =========================================================
# TIME / DATE
# =========================================================

def get_time():

    now = datetime.datetime.now()

    return now.strftime("%I:%M %p")


def get_date():

    now = datetime.datetime.now()

    return now.strftime("%A, %B %d, %Y")


# =========================================================
# LOCAL COMMAND HANDLER
# =========================================================

def handle_local_command(command):

    original = command
    command = clean_command(command)

    # -----------------------------------------------------
    # EXIT
    # -----------------------------------------------------

    if command in (
        "exit",
        "quit",
        "close",
        "goodbye",
        "shutdown jarvis",
        "stop",
    ):

        print("JARVIS: Goodbye.")
        speak("Goodbye.")

        return "EXIT"


    # -----------------------------------------------------
    # IDENTITY
    # -----------------------------------------------------

    if (
        "who are you" in command
        or "what are you" in command
        or command == "your name"
    ):

        response = (
            "I am JARVIS, your personal AI assistant. "
            "I can interact with your computer when you give permission."
        )

        print(f"JARVIS: {response}")
        speak(response)

        return True


    # -----------------------------------------------------
    # CREATOR
    # -----------------------------------------------------

    if (
        "who created you" in command
        or "who made you" in command
        or "who built you" in command
        or "your creator" in command
    ):

        response = f"I was created and developed by {CREATOR_NAME}."

        print(f"JARVIS: {response}")
        speak(response)

        return True


    # -----------------------------------------------------
    # STATUS
    # -----------------------------------------------------

    if command in (
        "status",
        "system status",
        "computer status",
        "pc status",
        "system information",
        "computer information",
        "pc information",
        "show system information",
    ):

        response = get_system_summary()

        print("JARVIS:")
        print(response)

        speak(
            "Here is your current computer status. "
            + response.replace("\n", ". ")
        )

        return True


    # -----------------------------------------------------
    # BATTERY
    # -----------------------------------------------------

    if (
        "battery" in command
        or "battery level" in command
        or "battery percentage" in command
    ):

        response = get_battery()

        print(f"JARVIS: {response}")
        speak(response)

        return True


    # -----------------------------------------------------
    # RAM
    # -----------------------------------------------------

    if (
        "ram" in command
        or "memory usage" in command
        or "memory used" in command
        or "how much memory" in command
    ):

        response = get_ram()

        print(f"JARVIS: {response}")
        speak(response)

        return True


    # -----------------------------------------------------
    # CPU
    # -----------------------------------------------------

    if (
        "cpu" in command
        or "processor" in command
        or "processor information" in command
        or "cpu information" in command
    ):

        response = get_cpu()

        print(f"JARVIS: {response}")
        speak(response)

        return True


    # -----------------------------------------------------
    # STORAGE
    # -----------------------------------------------------

    if (
        "storage" in command
        or "disk space" in command
        or "free space" in command
        or "hard drive" in command
        or "ssd space" in command
    ):

        response = get_storage()

        print(f"JARVIS: {response}")
        speak(response)

        return True


    # -----------------------------------------------------
    # WINDOWS
    # -----------------------------------------------------

    if (
        "windows version" in command
        or "which windows" in command
        or "what windows" in command
    ):

        response = get_windows()

        print(f"JARVIS: {response}")
        speak(response)

        return True


    # -----------------------------------------------------
    # COMPUTER NAME
    # -----------------------------------------------------

    if (
        "computer name" in command
        or "pc name" in command
        or "device name" in command
    ):

        response = get_computer_name()

        print(f"JARVIS: {response}")
        speak(response)

        return True


    # -----------------------------------------------------
    # TIME
    # -----------------------------------------------------

    if (
        command == "time"
        or "what time is it" in command
        or "current time" in command
    ):

        current_time = get_time()

        response = f"The current time is {current_time}."

        print(f"JARVIS: {response}")
        speak(response)

        return True


    # -----------------------------------------------------
    # DATE
    # -----------------------------------------------------

    if (
        command == "date"
        or "what is today's date" in command
        or "what is the date" in command
        or "today's date" in command
    ):

        current_date = get_date()

        response = f"Today is {current_date}."

        print(f"JARVIS: {response}")
        speak(response)

        return True


    # -----------------------------------------------------
    # APPLICATIONS
    # -----------------------------------------------------

    application = find_application(original)

    if application:

        open_application(application)

        return True


    # -----------------------------------------------------
    # WEBSITES
    # -----------------------------------------------------

    website = find_website(original)

    if website:

        open_website(website)

        return True


    return False


# =========================================================
# OPENROUTER AI
# =========================================================

conversation = [
    {
        "role": "system",
        "content": (
            "You are JARVIS, a personal AI assistant created and "
            "developed by Sanjay. "
            "Be helpful, concise, accurate and natural. "
            "You are running on a Windows computer. "
            "Do not claim to have performed computer actions unless "
            "the local JARVIS program actually performed them. "
            "Do not invent hardware information. "
            "If the user asks for live computer information, "
            "the local system functions should provide it."
        )
    }
]


def ask_ai(command):

    conversation.append(
        {
            "role": "user",
            "content": command
        }
    )

    payload = {
        "model": MODEL,
        "messages": conversation,
        "temperature": 0.7
    }

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost",
        "X-Title": "JARVIS Personal AI Assistant"
    }

    try:

        response = requests.post(
            API_URL,
            headers=headers,
            json=payload,
            timeout=60
        )

        if response.status_code != 200:

            print(
                f"JARVIS: OpenRouter error "
                f"{response.status_code}"
            )

            try:
                error_data = response.json()
                print(json.dumps(error_data, indent=2))
            except Exception:
                print(response.text)

            return


        data = response.json()

        answer = data["choices"][0]["message"]["content"]

        conversation.append(
            {
                "role": "assistant",
                "content": answer
            }
        )

        print()
        print(f"JARVIS: {answer}")
        print()

        speak(answer)

    except requests.exceptions.Timeout:

        print("JARVIS: The AI request timed out.")

    except requests.exceptions.ConnectionError:

        print("JARVIS: I couldn't connect to OpenRouter.")

    except Exception as e:

        print(f"JARVIS: AI error: {e}")


# =========================================================
# INPUT MODE
# =========================================================

def get_user_input():

    print()
    print("Choose input:")
    print("  [T] Type")
    print("  [V] Voice")
    print()

    choice = input("Input mode: ").strip().lower()

    if choice in ("v", "voice"):

        return listen_once()

    return input("You: ").strip()


# =========================================================
# MAIN
# =========================================================

def main():

    print("=" * 55)
    print("                 JARVIS")
    print("=" * 55)
    print("Personal AI Assistant")
    print()
    print("Voice input: V")
    print("Text input : T")
    print("Exit       : exit")
    print("=" * 55)

    startup_message = (
        "JARVIS is ready. "
        "Voice input and computer information systems are online."
    )

    print()
    print(startup_message)

    speak("JARVIS is ready.")

    while True:

        try:

            command = get_user_input()

            if not command:
                continue

            print()
            print(f"You: {command}")

            result = handle_local_command(command)

            if result == "EXIT":
                break

            if result is True:
                continue

            # Unknown command -> AI
            ask_ai(command)

        except KeyboardInterrupt:

            print()
            print("JARVIS: Goodbye.")
            speak("Goodbye.")
            break

        except Exception as e:

            print(f"JARVIS: Unexpected error: {e}")


# =========================================================
# RUN
# =========================================================

if __name__ == "__main__":
    main()