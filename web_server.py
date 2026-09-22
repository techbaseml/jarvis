import os
import re
import time
import uuid
import platform
import subprocess
import webbrowser
from datetime import datetime

import requests
import psutil
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS


# ============================================================
# JARVIS v15
# ============================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WEB_DIR = os.path.join(BASE_DIR, "web")

API_KEY = os.getenv("OPENROUTER_API_KEY")
API_URL = "https://openrouter.ai/api/v1/chat/completions"

MODEL = "openrouter/free"

HOST = "127.0.0.1"
PORT = 5000

ASSISTANT_NAME = "JARVIS"
CREATOR_NAME = "Sanjay"

PERMISSION_TIMEOUT = 60
MAX_HISTORY = 20


# ============================================================
# FLASK
# ============================================================

app = Flask(
    __name__,
    static_folder=WEB_DIR,
    static_url_path=""
)

CORS(app)


# ============================================================
# MEMORY
# ============================================================

pending_permissions = {}
sessions = {}


# ============================================================
# HELPERS
# ============================================================

def clean(text):
    return re.sub(
        r"\s+",
        " ",
        str(text).strip().lower()
    )


def current_time():
    return datetime.now().strftime("%I:%M %p")


def current_date():
    return datetime.now().strftime("%A, %d %B %Y")


def create_permission(action):

    request_id = str(uuid.uuid4())

    pending_permissions[request_id] = {
        "action": action,
        "created": time.time()
    }

    return request_id


def clean_permissions():

    now = time.time()

    expired = []

    for request_id, item in pending_permissions.items():

        if now - item["created"] > PERMISSION_TIMEOUT:
            expired.append(request_id)

    for request_id in expired:
        pending_permissions.pop(
            request_id,
            None
        )


# ============================================================
# SYSTEM INFORMATION
# ============================================================

def get_system_info():

    memory = psutil.virtual_memory()

    drive = os.environ.get(
        "SystemDrive",
        "C:"
    ) + "\\"

    disk = psutil.disk_usage(drive)

    battery = psutil.sensors_battery()

    battery_info = None

    if battery:

        battery_info = {
            "percent": round(
                battery.percent
            ),
            "plugged": battery.power_plugged
        }

    return {

        "cpu_percent":
            psutil.cpu_percent(
                interval=0.15
            ),

        "ram_percent":
            memory.percent,

        "ram_used_gb":
            round(
                memory.used / (1024 ** 3),
                2
            ),

        "ram_total_gb":
            round(
                memory.total / (1024 ** 3),
                2
            ),

        "storage_percent":
            disk.percent,

        "storage_used_gb":
            round(
                disk.used / (1024 ** 3),
                2
            ),

        "storage_total_gb":
            round(
                disk.total / (1024 ** 3),
                2
            ),

        "battery":
            battery_info,

        "windows":
            platform.platform(),

        "computer":
            platform.node(),

        "processor":
            platform.processor()
    }


# ============================================================
# LOCAL COMMANDS
# ============================================================

def local_command(text):

    command = clean(text)

    # --------------------------------------------------------
    # IDENTITY
    # --------------------------------------------------------

    if command in {
        "who are you",
        "what are you",
        "who is jarvis",
        "what is jarvis"
    }:

        return {
            "type": "answer",
            "message":
                "I'm JARVIS, your local AI assistant. "
                "I can chat with you, provide live computer "
                "information, and perform approved actions."
        }


    # --------------------------------------------------------
    # CREATOR
    # --------------------------------------------------------

    if command in {
        "who created you",
        "who made you",
        "who built you"
    }:

        return {
            "type": "answer",
            "message":
                f"I was created and configured by "
                f"{CREATOR_NAME}."
        }


    # --------------------------------------------------------
    # TIME
    # --------------------------------------------------------

    if command in {
        "time",
        "what time is it",
        "current time",
        "what is the time"
    }:

        return {
            "type": "answer",
            "message":
                f"The current local time is "
                f"{current_time()}."
        }


    # --------------------------------------------------------
    # DATE
    # --------------------------------------------------------

    if command in {
        "date",
        "today",
        "what date is it",
        "what is today's date"
    }:

        return {
            "type": "answer",
            "message":
                f"Today is {current_date()}."
        }


    info = get_system_info()


    # --------------------------------------------------------
    # CPU
    # --------------------------------------------------------

    if (
        "cpu" in command
        or "processor usage" in command
    ):

        return {
            "type": "answer",
            "message":
                f"Current CPU usage is "
                f"{info['cpu_percent']}%."
        }


    # --------------------------------------------------------
    # RAM
    # --------------------------------------------------------

    if (
        "ram" in command
        or "memory usage" in command
    ):

        return {
            "type": "answer",
            "message":
                f"RAM usage is "
                f"{info['ram_percent']}%. "
                f"{info['ram_used_gb']} GB of "
                f"{info['ram_total_gb']} GB is currently used."
        }


    # --------------------------------------------------------
    # STORAGE
    # --------------------------------------------------------

    if (
        "storage" in command
        or "disk usage" in command
        or "disk space" in command
    ):

        return {
            "type": "answer",
            "message":
                f"Storage is "
                f"{info['storage_percent']}% used. "
                f"{info['storage_used_gb']} GB of "
                f"{info['storage_total_gb']} GB is currently used."
        }


    # --------------------------------------------------------
    # BATTERY
    # --------------------------------------------------------

    if "battery" in command:

        battery = info["battery"]

        if not battery:

            return {
                "type": "answer",
                "message":
                    "Battery information is unavailable."
            }

        state = (
            "charging"
            if battery["plugged"]
            else "not charging"
        )

        return {
            "type": "answer",
            "message":
                f"Battery is at "
                f"{battery['percent']}% and is "
                f"{state}."
        }


    # --------------------------------------------------------
    # WINDOWS
    # --------------------------------------------------------

    if (
        command == "windows"
        or "windows version" in command
    ):

        return {
            "type": "answer",
            "message":
                f"You are running "
                f"{info['windows']}."
        }


    # --------------------------------------------------------
    # COMPUTER NAME
    # --------------------------------------------------------

    if (
        command == "computer"
        or "computer name" in command
        or "pc name" in command
    ):

        return {
            "type": "answer",
            "message":
                f"Your computer name is "
                f"{info['computer']}."
        }


    # --------------------------------------------------------
    # STATUS
    # --------------------------------------------------------

    if command in {
        "status",
        "system status",
        "jarvis status"
    }:

        battery = info["battery"]

        battery_text = (
            f"{battery['percent']}%"
            if battery
            else "Unavailable"
        )

        return {
            "type": "answer",
            "message":
                "JARVIS system status:\n\n"
                f"CPU: {info['cpu_percent']}%\n"
                f"RAM: {info['ram_percent']}%\n"
                f"Storage: {info['storage_percent']}%\n"
                f"Battery: {battery_text}\n"
                f"Computer: {info['computer']}"
        }


    return None


# ============================================================
# APP / WEBSITE ACTIONS
# ============================================================

def known_action(text):

    command = clean(text)

    apps = {
        "notepad": ["notepad.exe"],
        "calculator": ["calc.exe"],
        "paint": ["mspaint.exe"]
    }

    websites = {

        "youtube":
            "https://www.youtube.com",

        "google":
            "https://www.google.com",

        "github":
            "https://github.com"
    }


    # --------------------------------------------------------
    # APPS
    # --------------------------------------------------------

    for name, executable in apps.items():

        patterns = [
            f"open {name}",
            f"launch {name}",
            f"start {name}",
            f"run {name}",
            f"can you open {name}",
            f"please open {name}"
        ]

        if command in patterns:

            request_id = create_permission({
                "type": "app",
                "name": name,
                "command": executable
            })

            return {
                "type": "permission",
                "request_id": request_id,
                "action":
                    f"Open {name.title()}",
                "message":
                    f"JARVIS wants permission "
                    f"to open {name.title()}."
            }


    # --------------------------------------------------------
    # WEBSITES
    # --------------------------------------------------------

    for name, url in websites.items():

        patterns = [
            f"open {name}",
            f"launch {name}",
            f"start {name}",
            f"go to {name}",
            f"open {name}.com",
            f"can you open {name}",
            f"please open {name}"
        ]

        if command in patterns:

            request_id = create_permission({
                "type": "website",
                "name": name,
                "url": url
            })

            return {
                "type": "permission",
                "request_id": request_id,
                "action":
                    f"Open {name.title()}",
                "message":
                    f"JARVIS wants permission "
                    f"to open {name.title()}."
            }


    return None


# ============================================================
# OPENROUTER
# ============================================================

def ask_ai(text, session_id):

    if not API_KEY:

        return {
            "type": "error",
            "message":
                "OPENROUTER_API_KEY is missing."
        }


    system_prompt = """
You are JARVIS, a personal AI assistant created by Sanjay.

You are running through a local Windows web application.

Be helpful, natural and concise.

You can answer questions, explain things, help with coding,
technology, projects and everyday tasks.

IMPORTANT:
Do not claim that you performed an action on the computer
unless the local JARVIS backend actually performed it.

Do not invent system information.

If the user asks about the current computer status,
the local JARVIS system commands provide that information.

You are JARVIS v15.
Attachments and image uploads are NOT supported in this version.
"""


    history = sessions.get(
        session_id,
        []
    )


    messages = [
        {
            "role": "system",
            "content": system_prompt
        }
    ]


    messages.extend(
        history[-MAX_HISTORY:]
    )


    messages.append({
        "role": "user",
        "content": text
    })


    headers = {

        "Authorization":
            f"Bearer {API_KEY}",

        "Content-Type":
            "application/json",

        "HTTP-Referer":
            "http://127.0.0.1:5000",

        "X-Title":
            "JARVIS v15"
    }


    payload = {

        "model":
            MODEL,

        "messages":
            messages,

        "temperature":
            0.7
    }


    try:

        response = requests.post(
            API_URL,
            headers=headers,
            json=payload,
            timeout=90
        )


        if not response.ok:

            try:
                error = response.json()

            except Exception:
                error = response.text

            return {
                "type": "error",
                "message":
                    f"OpenRouter error:\n{error}"
            }


        data = response.json()

        choices = data.get(
            "choices",
            []
        )


        if not choices:

            return {
                "type": "error",
                "message":
                    "JARVIS received no response."
            }


        answer = (
            choices[0]
            .get("message", {})
            .get("content", "")
        )


        if isinstance(answer, list):

            answer = "\n".join(
                part.get(
                    "text",
                    ""
                )
                for part in answer
                if isinstance(
                    part,
                    dict
                )
            )


        if not answer:

            answer = "I didn't receive a response."


        history.append({
            "role": "user",
            "content": text
        })

        history.append({
            "role": "assistant",
            "content": answer
        })


        sessions[session_id] = (
            history[-MAX_HISTORY:]
        )


        return {
            "type": "answer",
            "message": answer
        }


    except requests.exceptions.Timeout:

        return {
            "type": "error",
            "message":
                "The AI request timed out."
        }


    except requests.exceptions.RequestException as exc:

        return {
            "type": "error",
            "message":
                f"Network error:\n{exc}"
        }


    except Exception as exc:

        return {
            "type": "error",
            "message":
                f"JARVIS error:\n{exc}"
        }


# ============================================================
# PERMISSIONS
# ============================================================

def execute_permission(
    request_id,
    allow
):

    clean_permissions()

    item = pending_permissions.pop(
        request_id,
        None
    )


    if not item:

        return {
            "type": "error",
            "message":
                "This permission request has expired."
        }


    if not allow:

        return {
            "type": "answer",
            "message":
                "Permission denied. No action was performed."
        }


    action = item["action"]


    # --------------------------------------------------------
    # APP
    # --------------------------------------------------------

    if action["type"] == "app":

        try:

            subprocess.Popen(
                action["command"],
                shell=False
            )

            return {
                "type": "answer",
                "message":
                    f"Permission granted. "
                    f"{action['name'].title()} "
                    f"is opening."
            }

        except Exception as exc:

            return {
                "type": "error",
                "message":
                    f"Could not open "
                    f"{action['name'].title()}:\n{exc}"
            }


    # --------------------------------------------------------
    # WEBSITE
    # --------------------------------------------------------

    if action["type"] == "website":

        try:

            webbrowser.open(
                action["url"],
                new=2
            )

            return {
                "type": "answer",
                "message":
                    f"Permission granted. "
                    f"{action['name'].title()} "
                    f"is opening."
            }

        except Exception as exc:

            return {
                "type": "error",
                "message":
                    f"Could not open "
                    f"{action['name'].title()}:\n{exc}"
            }


    return {
        "type": "error",
        "message":
            "Unknown permission action."
    }


# ============================================================
# ROUTES
# ============================================================

@app.route("/")
def home():

    return send_from_directory(
        WEB_DIR,
        "index.html"
    )


@app.route("/api/health")
def health():

    return jsonify({
        "ok": True,
        "jarvis": "JARVIS v15",
        "ai_configured":
            bool(API_KEY),
        "model":
            MODEL,
        "attachments":
            False
    })


@app.route("/api/system")
def system():

    return jsonify(
        get_system_info()
    )


@app.route(
    "/api/command",
    methods=["POST"]
)
def command():

    try:

        data = request.get_json(
            silent=True
        ) or {}

        text = str(
            data.get(
                "command",
                ""
            )
        ).strip()

        session_id = str(
            data.get(
                "session_id",
                "default"
            )
        )


        if not text:

            return jsonify({
                "type": "error",
                "message":
                    "Please enter a command."
            })


        # LOCAL COMMAND

        result = local_command(
            text
        )

        if result:

            return jsonify(result)


        # APP / WEBSITE

        result = known_action(
            text
        )

        if result:

            return jsonify(result)


        # AI

        return jsonify(
            ask_ai(
                text,
                session_id
            )
        )


    except Exception as exc:

        return jsonify({
            "type": "error",
            "message":
                f"Server error: {exc}"
        }), 500


@app.route(
    "/api/permission",
    methods=["POST"]
)
def permission():

    try:

        data = request.get_json(
            silent=True
        ) or {}

        request_id = data.get(
            "request_id"
        )

        allow = bool(
            data.get(
                "allow",
                False
            )
        )


        if not request_id:

            return jsonify({
                "type": "error",
                "message":
                    "Missing permission ID."
            }), 400


        return jsonify(
            execute_permission(
                request_id,
                allow
            )
        )


    except Exception as exc:

        return jsonify({
            "type": "error",
            "message":
                f"Permission error: {exc}"
        }), 500


# ============================================================
# START
# ============================================================

if __name__ == "__main__":

    print()
    print("=" * 55)
    print(" JARVIS v15")
    print("=" * 55)
    print()
    print(
        "API KEY:",
        "READY" if API_KEY else "MISSING"
    )
    print(
        "MODEL:",
        MODEL
    )
    print(
        "ATTACHMENTS: DISABLED"
    )
    print()
    print(
        "http://127.0.0.1:5000"
    )
    print()
    print("=" * 55)

    try:

        webbrowser.open(
            f"http://{HOST}:{PORT}"
        )

    except Exception:
        pass


    app.run(
        host=HOST,
        port=PORT,
        debug=False,
        threaded=True
    )
