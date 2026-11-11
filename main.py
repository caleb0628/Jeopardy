from flask import Flask, render_template, request, session, redirect, url_for, jsonify
from flask_socketio import join_room, emit, SocketIO
import random
import secrets
import socket
from string import ascii_uppercase

PORT = 5000
MAX_NAME_LENGTH = 20

# Create the Flask application instance
app = Flask(__name__)
# Set the secret key for session management (a new random key every time the server starts)
app.config["SECRET_KEY"] = secrets.token_hex(16)
# Initialize SocketIO with the Flask app
socketio = SocketIO(app, async_mode="threading")

# Dictionary to store room information
rooms = {}


# Function to generate a unique room code
def generate_unique_code(length):
    while True:
        code = ""
        for _ in range(length):
            code += random.choice(ascii_uppercase)

        if code not in rooms:
            break

    return code


# Create an empty room
def new_room():
    return {
        "players": {},      # name -> {"score": 0, "connections": 0}
        "buzzes": [],       # names in the order they buzzed
        "locked_out": [],   # names that already answered this question wrong
        "open": True,       # are the buzzers accepting buzzes right now?
        "amount": 200,      # dollars added or taken away when the host taps right/wrong
        "clue": None,       # what the board says is on screen (if gameboard.py is running)
    }


# Find this computer's address on the wifi so players know where to go
def lan_address():
    probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        probe.connect(("8.8.8.8", 80))  # no data is sent, this only looks up the address
        return probe.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        probe.close()


# Everything the phones need to draw their screens
def room_state(room):
    info = rooms[room]
    players = [
        {"name": name, "score": player["score"], "connected": player["connections"] > 0}
        for name, player in info["players"].items()
    ]
    players.sort(key=lambda player: (-player["score"], player["name"].lower()))
    return {
        "players": players,
        "buzzes": info["buzzes"],
        "lockedOut": info["locked_out"],
        "open": info["open"],
        "amount": info["amount"],
        "clue": info["clue"],
    }


# Send the latest state to everyone in the room
def broadcast(room):
    socketio.emit("state", room_state(room), to=room)


# Turn whatever the host typed into a whole dollar amount
def to_amount(value, default=0):
    try:
        return max(0, min(1000000, int(float(value))))
    except (TypeError, ValueError):
        return default


# Route for the home page
@app.route("/", methods=["POST", "GET"])
def home():
    # Clear the session data
    session.clear()
    if request.method == "POST":
        # Get form data
        name = (request.form.get("name") or "").strip()[:MAX_NAME_LENGTH]
        code = (request.form.get("code") or "").strip().upper()
        join = request.form.get("join", False)
        create = request.form.get("create", False)

        if create != False:
            # Generate a unique room code and create the room
            room = generate_unique_code(4)
            rooms[room] = new_room()
            session["room"] = room
            session["name"] = "Host"
            session["host"] = True
            return redirect(url_for("host"))

        # Validation for joining a room
        if not name:
            return render_template("home.html", error="Please enter a name.", code=code, name=name)

        if not code:
            return render_template("home.html", error="Please enter a room code.", code=code, name=name)

        if code not in rooms:
            return render_template("home.html", error="Room does not exist.", code=code, name=name)

        if name.lower() == "host":
            return render_template("home.html", error="Please pick a different name.", code=code, name=name)

        # Names are matched without caring about capital letters
        players = rooms[code]["players"]
        existing = next((player for player in players if player.lower() == name.lower()), None)
        if existing is not None and players[existing]["connections"] > 0:
            return render_template("home.html", error="That name is already taken.", code=code, name=name)
        if existing is not None:
            name = existing  # coming back after closing the page - keep the old score
        else:
            players[name] = {"score": 0, "connections": 0}

        # Store room and name in session
        session["room"] = code
        session["name"] = name
        return redirect(url_for("room"))

    return render_template("home.html")


# Route for the host page
@app.route("/host")
def host():
    room = session.get("room")
    if room is None or not session.get("host") or room not in rooms:
        return redirect(url_for("home"))

    return render_template("host.html", code=room, join_address=f"{lan_address()}:{PORT}")


# Route for the room page
@app.route("/room")
def room():
    room = session.get("room")
    name = session.get("name")
    if room is None or name is None or room not in rooms or name not in rooms[room]["players"]:
        return redirect(url_for("home"))

    return render_template("room.html", code=room, name=name)


# gameboard.py calls this (from the same computer only) when a question opens or closes
@app.route("/board", methods=["POST"])
def board():
    if request.remote_addr not in ("127.0.0.1", "::1"):
        return jsonify(ok=False), 403

    data = request.get_json(silent=True) or {}
    for room, info in rooms.items():
        if data.get("event") == "open":
            special = bool(data.get("daily_double") or data.get("final"))
            info["clue"] = {
                "category": str(data.get("category", ""))[:80],
                "value": to_amount(data.get("value")),
                "dailyDouble": bool(data.get("daily_double")),
                "final": bool(data.get("final")),
            }
            info["buzzes"] = []
            info["locked_out"] = []
            info["open"] = not special  # nobody buzzes on a Daily Double or Final Jeopardy
            if not special:
                info["amount"] = info["clue"]["value"]
        elif data.get("event") == "close":
            info["clue"] = None
            info["buzzes"] = []
            info["locked_out"] = []
            info["open"] = False
        broadcast(room)
    return jsonify(ok=True)


# Event handler for new connections
@socketio.on("connect")
def connect(auth=None):
    room = session.get("room")
    name = session.get("name")
    if not room or not name or room not in rooms:
        return False

    join_room(room)
    if not session.get("host"):
        player = rooms[room]["players"].get(name)
        if player is None:
            return False
        player["connections"] += 1
        print(f"{name} joined room {room}")
    broadcast(room)


# Event handler for disconnections
@socketio.on("disconnect")
def disconnect(reason=None):
    room = session.get("room")
    name = session.get("name")
    if room not in rooms:
        return

    # Rooms and scores are kept so a phone that locks or refreshes can come right back
    player = rooms[room]["players"].get(name)
    if player is not None and not session.get("host"):
        player["connections"] = max(0, player["connections"] - 1)
        print(f"{name} has left the room {room}")
    broadcast(room)


# A player pressed the buzzer
@socketio.on("buzz")
def buzz():
    room = session.get("room")
    name = session.get("name")
    if room not in rooms or session.get("host"):
        return

    info = rooms[room]
    if name not in info["players"] or not info["open"]:
        return
    if name in info["buzzes"] or name in info["locked_out"]:
        return

    info["buzzes"].append(name)
    print(f"{name} buzzed in ({len(info['buzzes'])})")
    broadcast(room)


# Everything below is for the host only
def host_room():
    room = session.get("room")
    if room in rooms and session.get("host"):
        return room
    return None


# The host tapped Correct or Wrong for a player
@socketio.on("judge")
def judge(data):
    room = host_room()
    if room is None or not isinstance(data, dict):
        return

    info = rooms[room]
    name = data.get("name")
    if name not in info["players"]:
        return

    amount = to_amount(data.get("amount"), info["amount"])
    if data.get("correct"):
        info["players"][name]["score"] += amount
        if name in info["buzzes"]:  # the question is over - lock the buzzers
            info["buzzes"] = []
            info["locked_out"] = []
            info["open"] = False
    else:
        info["players"][name]["score"] -= amount
        if name in info["buzzes"]:  # the next person in line gets a turn
            info["buzzes"].remove(name)
            info["locked_out"].append(name)
    broadcast(room)


# The host cleared the buzzers for a new question
@socketio.on("reset")
def reset():
    room = host_room()
    if room is None:
        return

    rooms[room]["buzzes"] = []
    rooms[room]["locked_out"] = []
    rooms[room]["open"] = True
    broadcast(room)


# The host changed the dollar amount
@socketio.on("set_amount")
def set_amount(data):
    room = host_room()
    if room is None or not isinstance(data, dict):
        return

    rooms[room]["amount"] = to_amount(data.get("amount"), rooms[room]["amount"])
    broadcast(room)


# The host typed in a score by hand
@socketio.on("set_score")
def set_score(data):
    room = host_room()
    if room is None or not isinstance(data, dict):
        return

    player = rooms[room]["players"].get(data.get("name"))
    if player is None:
        return
    try:
        player["score"] = max(-1000000, min(1000000, int(float(data.get("score")))))
    except (TypeError, ValueError):
        return
    broadcast(room)


# The host removed a player (for example a name typed wrong)
@socketio.on("remove_player")
def remove_player(data):
    room = host_room()
    if room is None or not isinstance(data, dict):
        return

    info = rooms[room]
    name = data.get("name")
    if name in info["players"]:
        del info["players"][name]
        info["buzzes"] = [buzzer for buzzer in info["buzzes"] if buzzer != name]
        info["locked_out"] = [buzzer for buzzer in info["locked_out"] if buzzer != name]
        socketio.emit("removed", {"name": name}, to=room)
        broadcast(room)


# Run the application
if __name__ == "__main__":
    print()
    print("Jeopardy buzzer is running.")
    print(f"  Host (this computer):   http://localhost:{PORT}")
    print(f"  Players (same wifi):    http://{lan_address()}:{PORT}")
    print("Leave this window open during the game. Close it to stop the buzzer.")
    print()
    socketio.run(app, host="0.0.0.0", port=PORT, allow_unsafe_werkzeug=True)
