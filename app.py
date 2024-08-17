# app.py
from flask import Flask, render_template, request
import uuid
import chess
import json
import chess.svg

app = Flask(__name__)


@app.route("/")
def hello_world():
    return render_template("home.html")


@app.route("/new_game", methods=["POST"])
def new_game():
    game_type = request.form.get("game_type")
    # Logic to create a new game based on the game_type
    if game_type == "public":
        # Create a public game
        pass
    elif game_type == "private":
        # Create a private game
        pass
    code = str(uuid.uuid4())

    return "New game created: " + game_type + ". The game code is: " + code


@app.route("/game/<game_code>/message", methods=["POST"])
def send_message(game_code):
    message = request.form.get("message")
    return "Message sent: " + message


@app.route("/game/<game_code>", methods=["GET"])
def get_board(game_code):
    with open("games.json", "r") as f:
        games = json.load(f)
    if game_code not in games:
        return "Game not found", 404
    game = games[game_code]
    board = chess.Board(fen=game["fen"])
    board_svg = chess.svg.board(board=board)
    return render_template("game.html", board_svg=board_svg, game_code=game_code)


if __name__ == "__main__":
    app.run(debug=True)
