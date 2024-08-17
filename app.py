# app.py
from flask import Flask, render_template, request, make_response, render_template_string
import uuid
import chess
import json
import chess.svg
import time

from markupsafe import Markup

app = Flask(__name__)
app.config["DEBUG"] = True


@app.route("/")
def hello_world():

    username = request.cookies.get("username")
    print(username)
    return render_template("home.html", username=username)


# Todo: save uuid to cookie and check if user is logged in via games.json instead - cuz it's safer
@app.route("/signup", methods=["POST"])
def login():
    username = request.form.get("username")
    with open("games.json", "r") as f:
        users = json.load(f)
    if username in users["usernames"]:
        return "User already exists"
    else:
        users["usernames"].append(username)
        with open("games.json", "w") as f:
            json.dump(users, f)
        resp = make_response("Sign up successful")
        resp.set_cookie("username", username)
        return resp


@app.route("/logout", methods=["POST", "GET"])
def logout():
    resp = make_response("You logged out")
    resp.set_cookie("username", "", expires=0)
    return resp


@app.route("/new_game", methods=["POST"])
def new_game():
    game_type = request.form.get("game_type")
    code = str(uuid.uuid4())

    with open("games.json", "r") as f:
        games = json.load(f)
    games["games"][code] = {
        "status": "waiting",
        "player1": request.cookies.get("username"),
        "game_type": game_type,
        "id": code,
        "player_turn": "white",
        "fen": chess.Board().fen(),
        "messages": [],
    }
    if game_type == "public":
        pass
    elif game_type == "private":
        pass

    with open("games.json", "w") as f:
        json.dump(games, f)
    return render_template(
        "new_game.html",
        game_code=code,
        game_share_code=request.url_root + "game/" + code,
    )


@app.route("/game/<game_code>/message", methods=["POST"])
def send_message(game_code):
    message = request.form.get("message")
    with open("games.json", "r") as f:
        games = json.load(f)
    games["games"][game_code]["messages"].append(
        {
            "player": request.cookies.get("username"),
            "message": message,
            "timestamp": time.time(),
        }
    )
    with open("games.json", "w") as f:
        json.dump(games, f)
    return games["games"][game_code]["messages"]


@app.route("/game/<game_code>/join", methods=["POST"])
def join_game(game_code):
    with open("games.json", "r") as f:
        games = json.load(f)
    if game_code not in games["games"]:
        return "Game not found", 404
    if games["games"][game_code]["player2"]:
        return "Game is full", 400

    games["games"][game_code]["player2"] = request.cookies.get("username")
    with open("games.json", "w") as f:
        json.dump(games, f)
    return "You joined the game"


@app.route("/game/<game_code>", methods=["GET"])
def get_board(game_code):
    with open("games.json", "r") as f:
        games = json.load(f)
    if game_code not in games["games"]:
        return "Game not found", 404
    game = games["games"][game_code]
    board = chess.Board(fen=game["fen"])
    board_svg = chess.svg.board(board=board, size=800)
    return render_template(
        "game.html", board_svg=Markup(board_svg), game_code=game_code
    )


if __name__ == "__main__":
    app.run(debug=True)
