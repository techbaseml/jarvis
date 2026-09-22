import os
import uuid
import datetime
import requests

from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
MODEL = "openrouter/free"

sessions = {}
permissions = {}


# ---------------------------------------------------------
# HELPERS
# ---------------------------------------------------------

def get_session(session_id):
    if session_id not in sessions:
        sessions[session_id] = []

    return sessions[session_id]


def ask_ai(session_id, user_message):

    if not OPENROUTER_API_KEY:
        return "OpenRouter API key is not configured on the Vercel server."

    history = get_session(session_id)

    system_message = {
        "role": "system",
        "content": """
You are JARVIS, a helpful personal AI assistant.

Be concise, natural and useful.

You are running as JARVIS v15 on a Vercel backend.

Important:
- You cannot directly control the user's Windows computer.
- You cannot open Windows applications from Vercel.
- You cannot read the user's PC CPU, RAM, battery or storage.
- Never claim that you performed a computer action if you did not.
- If the user asks for an unavailable local computer action, explain that this cloud version cannot access their PC.
"""
    }

    messages = [system_message]

    messages.extend(history[-20:])

    messages.append({
        "role": "user",
        "content": user_message
    })

    try:

        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://vercel.app",
                "X-Title": "JARVIS v15"
            },
            json={
                "model": MODEL,
                "messages": messages
            },
            timeout=60
        )

        response.raise_for_status()

        data = response.json()

        answer = (
            data.get("choices", [{}])[0]
            .get("message", {})
            .get("content")
        )

        if not answer:
            return "I received an empty response from the AI service."

        history.append({
            "role": "user",
            "content": user_message
        })

        history.append({
            "role": "assistant",
            "content": answer
        })

        sessions[session_id] = history[-20:]

        return answer

    except requests.exceptions.Timeout:
        return "The AI service took too long to respond."

    except requests.exceptions.RequestException as e:
        return "I couldn't connect to the AI service."


# ---------------------------------------------------------
# HEALTH
# ---------------------------------------------------------

@app.route("/api/health", methods=["GET"])
def health():

    return jsonify({
        "status": "online",
        "jarvis": "v15",
        "backend": "Vercel",
        "model": MODEL
    })


# ---------------------------------------------------------
# SYSTEM
# ---------------------------------------------------------

@app.route("/api/system", methods=["GET"])
def system():

    # Cloud server information only.
    # This is NOT the user's Windows PC.

    return jsonify({
        "cpu": 0,
        "ram_percent": 0,
        "cloud": True,
        "message": "Local Windows system information is unavailable in cloud mode."
    })


# ---------------------------------------------------------
# COMMAND
# ---------------------------------------------------------

@app.route("/api/command", methods=["POST"])
def command():

    data = request.get_json(silent=True) or {}

    message = str(
        data.get("message", "")
    ).strip()

    session_id = str(
        data.get("session_id", "default")
    )

    if not message:

        return jsonify({
            "error": "Message is empty."
        }), 400

    lower = message.lower()

    # -----------------------------------------------------
    # LOCAL INFORMATION
    # -----------------------------------------------------

    now = datetime.datetime.now()

    if lower in [
        "who are you",
        "what are you",
        "who is jarvis"
    ]:

        return jsonify({
            "response":
                "I am JARVIS v15, your personal AI assistant."
        })

    if "what time" in lower or lower == "time":

        return jsonify({
            "response":
                "The current server time is "
                + now.strftime("%I:%M %p")
                + "."
        })

    if "what date" in lower or lower == "date":

        return jsonify({
            "response":
                "Today's date is "
                + now.strftime("%d %B %Y")
                + "."
        })

    # -----------------------------------------------------
    # WINDOWS ACTIONS
    # -----------------------------------------------------

    windows_actions = [
        "open notepad",
        "launch notepad",
        "open calculator",
        "launch calculator",
        "open paint",
        "launch paint",
        "open youtube",
        "launch youtube",
        "open google",
        "launch google",
        "open github",
        "launch github"
    ]

    if any(action in lower for action in windows_actions):

        return jsonify({
            "response":
                "This JARVIS cloud version runs on Vercel, so it cannot access or control your Windows PC. "
                "Windows app launching requires the local JARVIS backend."
        })

    # -----------------------------------------------------
    # AI
    # -----------------------------------------------------

    answer = ask_ai(
        session_id,
        message
    )

    return jsonify({
        "response": answer
    })


# ---------------------------------------------------------
# PERMISSION
# ---------------------------------------------------------

@app.route("/api/permission", methods=["POST"])
def permission():

    data = request.get_json(silent=True) or {}

    allowed = bool(
        data.get("allowed", False)
    )

    permission_id = data.get(
        "permission_id"
    )

    if allowed:

        return jsonify({
            "success": True,
            "message":
                "Permission received. However, this cloud version cannot control your Windows PC."
        })

    return jsonify({
        "success": True,
        "message": "Permission denied."
    })


# ---------------------------------------------------------
# VERCEL ENTRY
# ---------------------------------------------------------

@app.route("/", methods=["GET"])
def home():

    return jsonify({
        "name": "JARVIS",
        "version": "15",
        "status": "online"
    })


if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=False
    )
