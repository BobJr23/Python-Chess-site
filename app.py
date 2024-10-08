from flask import (
    Flask,
    render_template,
    request,
    redirect,
)
import uuid
import chess
import json
import chess.svg
import time

from markupsafe import Markup

app = Flask(__name__)
app.config["DEBUG"] = True


def get_games():
    with open("games.json", "r") as f:
        return json.load(f)


def get_board_from_code(game_code):
    games = get_games()
    game = games["games"][game_code]
    board = chess.Board(fen=game["fen"])
    return board


def get_active_players():
    games = get_games()
    active_players = set()
    for game in games["games"].values():
        if game["status"] == "playing":
            if game["player1_id"]:
                active_players.add(game["player1_id"])
            if game["player2_id"]:
                active_players.add(game["player2_id"])
    return len(active_players)


def verify_player(game_code, username):
    games = get_games()
    game = games["games"][game_code]
    if username == game["player1_id"]:

        return "white"

    if username == game["player2_id"]:
        return "black"

    return None


@app.route("/")
def hello_world():
    users = get_games()
    try:
        username = users["usernames"][request.cookies.get("username")]
    except KeyError:
        username = None

    return render_template("home.html", username=username, active=get_active_players())


@app.route("/signup", methods=["POST"])
def login():
    username = request.form.get("username")
    users = get_games()
    if username in users["usernames"].values():
        return redirect("/")
    else:
        user_code = str(uuid.uuid4())
        users["usernames"][user_code] = username
        with open("games.json", "w") as f:
            json.dump(users, f)
        resp = redirect("/")
        resp.set_cookie("username", user_code)
        return resp


@app.route("/logout", methods=["POST", "GET"])
def logout():
    resp = redirect("/")
    resp.set_cookie("username", "", expires=0)
    return resp


@app.route("/new_game", methods=["POST"])
def new_game():
    game_type = request.form.get("game_type")
    code = str(uuid.uuid4())
    username = request.cookies.get("username")
    if username is None:
        return "You need to be logged in to create a game", 401
    games = get_games()
    games["games"][code] = {
        "status": "waiting",
        "player1_id": username,
        "player1_name": games["usernames"][username],
        "player2_id": None,
        "player2_name": None,
        "game_url": request.url_root + "game/" + code,
        "game_type": game_type,
        "id": code,
        "player_turn": "white",
        "fen": chess.Board().fen(),
        "messages": [
            {
                "player": "System",
                "message": "Waiting for player... Invite your friend with the code:\n"
                + code
                + "\nor share this link:\n"
                + request.url_root
                + "game/"
                + code
                + "/join",
            }
        ],
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
        game_share_code=request.url_root + "game/" + code + "/join",
    )


@app.route("/game/<game_code>/message", methods=["POST"])
def send_message(game_code):
    message = request.form.get("message")
    games = get_games()
    games["games"][game_code]["messages"].append(
        {
            "player": get_games()["usernames"][request.cookies.get("username")],
            "message": message,
            "timestamp": time.time(),
        }
    )
    with open("games.json", "w") as f:
        json.dump(games, f)
    return games["games"][game_code]["messages"]


@app.route("/game/<game_code>/get_messages", methods=["GET"])
def get_messages(game_code):
    games = get_games()
    return games["games"][game_code]["messages"]


@app.route("/game/<game_code>/click", methods=["POST"])
def click(game_code):
    form = request.form
    square = form.get("square")
    selected = form.get("selected")
    if not square:
        return {"board": "Invalid", "status": 400}

    board = get_board_from_code(game_code)
    legal_moves = [move for move in board.legal_moves if move.uci().startswith(square)]
    selected_legal = [
        move for move in board.legal_moves if move.uci().startswith(selected)
    ]
    color = verify_player(game_code, request.cookies.get("username"))
    # means player moved while highlighted
    if (
        selected
        and selected + square in [move.uci() for move in selected_legal]
        and verify_player(game_code, request.cookies.get("username"))
        == ("white" if board.turn else "black")
    ):
        print("move is valid")
        board.push_san(selected + square)
        games = get_games()
        game = games["games"][game_code]
        game["fen"] = board.fen()
        game["player_turn"] = "black" if game["player_turn"] == "white" else "white"

        with open("games.json", "w") as f:
            json.dump(games, f)
        return {
            "board": Markup(
                chess.svg.board(
                    board,
                    size=800,
                    orientation=(color == "white"),
                )
            ),
            "status": 200,
        }

    highlighted_squares = [chess.SQUARE_NAMES[move.to_square] for move in legal_moves]
    fill_colors = {
        chess.SQUARE_NAMES.index(sq): "#cc0000cc" for sq in highlighted_squares
    }
    board_svg = Markup(
        chess.svg.board(
            board,
            size=800,
            fill=fill_colors,
            orientation=(color == "white"),
        )
    )

    return {"board": board_svg, "status": 200}


@app.route("/join")
@app.route("/game/<game_code>/join", methods=["GET"])
def join_game(game_code=None):
    games = get_games()
    if not game_code:
        game_code = request.form.get("game_code")
    if game_code not in games["games"].keys():
        return "Game not found", 404
    if games["games"][game_code]["player2_id"]:
        return "Game is full", 400
    if games["games"][game_code]["player2_id"] == request.cookies.get("username"):
        return redirect("/game/" + game_code)

    try:
        player2_name = games["usernames"][request.cookies.get("username")]
    except KeyError:
        return "You need to be logged in to join a game", 401
    if player2_name == games["games"][game_code]["player1_name"]:
        return render_template(
            "game.html",
            game_code=game_code,
            error="You can't play against yourself",
            board_svg=Markup(
                chess.svg.board(board=get_board_from_code(game_code), size=800)
            ),
            color="white",
        )

    games["games"][game_code]["player2_id"] = request.cookies.get("username")
    games["games"][game_code]["player2_name"] = player2_name
    games["games"][game_code]["status"] = "playing"
    games["games"][game_code]["messages"].append(
        {"player": "System", "message": "Game started!"}
    )
    with open("games.json", "w") as f:
        json.dump(games, f)

    return redirect("/game/" + game_code)
    # redirect seems to be better than returning the template cuz of url issues when reloading
    # return render_template(
    #     "game.html",
    #     game_code=game_code,
    #     board_svg=Markup(
    #         chess.svg.board(board=get_board_from_code(game_code), size=800)
    #     ),
    # )


@app.route("/game/<game_code>", methods=["GET"])
def get_board(game_code):
    games = get_games()
    if game_code not in games["games"]:
        return "Game not found", 404
    game = games["games"][game_code]
    color = verify_player(game_code, request.cookies.get("username"))
    board_svg = chess.svg.board(
        board=get_board_from_code(game_code), size=800, orientation=(color == "white")
    )
    return render_template(
        "game.html",
        board_svg=Markup(board_svg),
        game_code=game_code,
        color=color,
    )


@app.route("/find-open", methods=["GET"])
def find_open():
    games = get_games()
    open_games = [
        game for game in games["games"].values() if game["status"] == "waiting"
    ]
    return render_template("open_games.html", open_games=open_games)


if __name__ == "__main__":
    app.run(debug=True)
