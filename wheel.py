import math
import random
import sys
from time import sleep, time as now

from graphics import Point, Polygon, Circle, Entry, GraphicsError
from game_tools import (GameFileError, Button, new_window, clear, label, box, fit_text,
                        font_size, money, wait_for_button, read_spreadsheet)


# A "wheel of fortune" style word puzzle game for 1 to 4 players (or teams).
#
# Puzzles come from wheel_puzzles.csv (open it in Excel or Google Sheets).
# Columns: Category, Puzzle
# To use a different file:  python wheel.py my_puzzles.csv
#
# How to play: see README.md

PUZZLE_FILE = "wheel_puzzles.csv"

ROUNDS = 3                  # how many puzzles in one game
SHUFFLE_PUZZLES = True      # False plays the puzzles in spreadsheet order
VOWEL_COST = 250
MINIMUM_ROUND_WIN = 1000    # solving a puzzle always pays at least this much
MAX_PLAYERS = 4
SPIN_SECONDS = 3.2          # how long the wheel spins

BANKRUPT = "BANKRUPT"
LOSE_A_TURN = "LOSE A TURN"
WEDGES = [2500, 300, 900, 500, BANKRUPT, 600, 700, 550, 800, LOSE_A_TURN, 650, 500,
          900, BANKRUPT, 600, 700, 300, 800, 550, 650, 500, 900, 600, 700]
WEDGE_COLORS = ["red", "dark orange", "gold", "forest green", "deep sky blue", "medium purple", "hot pink"]

VOWELS = "AEIOU"
ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
BOARD_COLUMNS = 14
BOARD_ROWS = 4

WHEEL_X, WHEEL_Y, WHEEL_RADIUS = 290, 735, 225


# --------------------------------------------------------------------------
# Puzzles
# --------------------------------------------------------------------------

def puzzle_rows(puzzle):  # Split a puzzle into the lines shown on the board
    rows, line = [], ""
    for word in puzzle.split():
        if line and len(line) + 1 + len(word) > BOARD_COLUMNS:
            rows.append(line)
            line = word
        else:
            line = (line + " " + word).strip()
    if line:
        rows.append(line)
    return rows


def load_puzzles(path=None):
    path = path or PUZZLE_FILE
    puzzles = []
    for line_number, row in read_spreadsheet(path, ["category", "puzzle"]):
        puzzle = " ".join(row["puzzle"].upper().split())
        if not puzzle:
            continue
        if not any(ch in ALPHABET for ch in puzzle):
            raise GameFileError(f"Row {line_number} of {path}: the puzzle has no letters in it.")
        longest = max(puzzle.split(), key=len)
        if len(longest) > BOARD_COLUMNS:
            raise GameFileError(
                f"Row {line_number} of {path}: the word '{longest}' is too long. "
                f"Words can be up to {BOARD_COLUMNS} letters."
            )
        if len(puzzle_rows(puzzle)) > BOARD_ROWS:
            raise GameFileError(
                f"Row {line_number} of {path}: '{puzzle}' is too long to fit on the board "
                f"({BOARD_ROWS} lines of {BOARD_COLUMNS} letters)."
            )
        puzzles.append({"category": row["category"] or "Puzzle", "puzzle": puzzle})
    if not puzzles:
        raise GameFileError(f"{path} does not contain any puzzles.")
    return puzzles


# --------------------------------------------------------------------------
# Drawing
# --------------------------------------------------------------------------

def wheel_point(angle, radius):  # angle in degrees, 0 = straight up, going clockwise
    radians = math.radians(angle)
    return Point(WHEEL_X + radius * math.sin(radians), WHEEL_Y - radius * math.cos(radians))


class Screen:
    """Everything drawn for one round, and the pieces that change while playing."""

    def __init__(self, win, puzzle, players, round_number, total_rounds):
        self.win = win
        self.puzzle = puzzle
        self.players = players
        clear(win)

        self.tiles = {}        # "A" -> the text items for every A on the board
        self.letter_keys = {}  # "A" -> Button
        self.player_items = []
        self.pointer = None
        self.wedge_shapes = []
        self.lit_wedge = None
        self.angle = 0.0       # where the pointer is right now

        self.draw_puzzle_board()
        label(win, 801, 398, f"{puzzle['category']}   (round {round_number} of {total_rounds})", 24, "navy")
        self.message = label(win, 801, 452, "", 22, "black")
        self.draw_wheel()
        self.draw_letter_keys()

        self.spin = Button(win, 585, 745, 775, 840, "SPIN", fill="forest green", size=24, value="spin")
        self.vowel = Button(win, 790, 745, 980, 840, f"BUY A VOWEL\n{money(VOWEL_COST)}", fill="medium purple", size=17, value="vowel")
        self.solve = Button(win, 995, 745, 1185, 840, "SOLVE", fill="blue", size=24, value="solve")
        self.correct = Button(win, 585, 860, 880, 955, "CORRECT", fill="forest green", size=24, value="correct")
        self.wrong = Button(win, 890, 860, 1185, 955, "WRONG", fill="firebrick", size=24, value="wrong")
        self.correct.set_enabled(False)
        self.wrong.set_enabled(False)

    # ----- puzzle board -----

    def draw_puzzle_board(self):
        tile_width, tile_height = 78, 82
        left = (1602 - BOARD_COLUMNS * tile_width) / 2
        top = 30
        box(self.win, left - 12, top - 12, left + BOARD_COLUMNS * tile_width + 12,
            top + BOARD_ROWS * tile_height + 12, "navy")

        rows = puzzle_rows(self.puzzle["puzzle"])
        first_row = (BOARD_ROWS - len(rows)) // 2
        letters = {}
        for row_index, text in enumerate(rows):
            first_column = (BOARD_COLUMNS - len(text)) // 2
            for offset, ch in enumerate(text):
                if ch != " ":
                    letters[(first_row + row_index, first_column + offset)] = ch

        for row in range(BOARD_ROWS):
            for column in range(BOARD_COLUMNS):
                x1, y1 = left + column * tile_width, top + row * tile_height
                ch = letters.get((row, column))
                box(self.win, x1 + 2, y1 + 2, x1 + tile_width - 2, y1 + tile_height - 2,
                    "white" if ch else "sea green")
                if ch:
                    shown = "" if ch in ALPHABET else ch  # punctuation shows from the start
                    item = label(self.win, x1 + tile_width / 2, y1 + tile_height / 2, shown, 34)
                    self.tiles.setdefault(ch, []).append(item)

    def reveal(self, letter):  # Turn over every copy of a letter
        for item in self.tiles.get(letter, []):
            item.setText(letter)

    def reveal_all(self):
        for letter in self.tiles:
            self.reveal(letter)

    # ----- wheel -----

    def draw_wheel(self):
        size = 360 / len(WEDGES)
        Circle(Point(WHEEL_X, WHEEL_Y), WHEEL_RADIUS + 8).draw(self.win).setFill("gray20")
        for index, wedge in enumerate(WEDGES):
            start = index * size
            points = [Point(WHEEL_X, WHEEL_Y)] + [wheel_point(start + step * size / 3, WHEEL_RADIUS) for step in range(4)]
            shape = Polygon(points)
            if wedge == BANKRUPT:
                fill, text_color, text = "black", "white", BANKRUPT
            elif wedge == LOSE_A_TURN:
                fill, text_color, text = "white", "black", LOSE_A_TURN
            else:
                fill, text_color, text = WEDGE_COLORS[index % len(WEDGE_COLORS)], "black", money(wedge)
            shape.setFill(fill)
            shape.draw(self.win)
            self.wedge_shapes.append(shape)

            middle = start + size / 2
            spot = wheel_point(middle, WHEEL_RADIUS * 0.63)
            item = label(self.win, spot.getX(), spot.getY(), text, 12 if len(text) < 7 else 10, text_color)
            # Turn the text so it runs along the wedge (needs Tk 8.6, which comes with Python)
            turn = (90 - middle) % 360
            if 90 < turn < 270:
                turn = (turn + 180) % 360
            try:
                self.win.itemconfig(item.id, angle=turn)
            except Exception:
                pass
        Circle(Point(WHEEL_X, WHEEL_Y), 34).draw(self.win).setFill("gray20")
        self.draw_pointer()

    def draw_pointer(self):  # A marker that travels around the outside of the wheel
        if self.pointer is not None:
            self.pointer.undraw()
        self.pointer = Polygon(wheel_point(self.angle, WHEEL_RADIUS - 14),
                               wheel_point(self.angle - 5, WHEEL_RADIUS + 34),
                               wheel_point(self.angle + 5, WHEEL_RADIUS + 34))
        self.pointer.setFill("white")
        self.pointer.setOutline("black")
        self.pointer.setWidth(2)
        self.pointer.draw(self.win)

    def spin_wheel(self):  # Animate the pointer and return the wedge it stops on
        if self.lit_wedge is not None:
            self.lit_wedge.setWidth(1)
            self.lit_wedge.setOutline("black")

        size = 360 / len(WEDGES)
        target = random.randrange(len(WEDGES))
        stop_at = target * size + random.uniform(2, size - 2)
        start = self.angle % 360
        travel = (stop_at - start) % 360 + 360 * random.randint(2, 3)

        duration = SPIN_SECONDS
        began = now()
        while True:
            progress = min(1.0, (now() - began) / duration)
            self.angle = start + travel * (1 - (1 - progress) ** 3)  # fast at first, then slowing
            self.draw_pointer()
            if progress >= 1.0:
                break
            sleep(0.015)

        self.lit_wedge = self.wedge_shapes[target]
        self.lit_wedge.setOutline("white")
        self.lit_wedge.setWidth(4)
        self.draw_pointer()  # keep the pointer on top of the highlight
        return WEDGES[target]

    # ----- letters -----

    def draw_letter_keys(self):
        for index, letter in enumerate(ALPHABET):
            row, column = divmod(index, 9)
            x1, y1 = 585 + column * 67 + (33 if row == 2 else 0), 505 + row * 76
            fill = "light pink" if letter in VOWELS else "white"
            self.letter_keys[letter] = Button(self.win, x1, y1, x1 + 62, y1 + 70, letter,
                                              fill=fill, text_color="black", size=24, value=letter)

    def set_letters(self, used, clickable):  # Gray out used letters; only "clickable" ones can be picked
        for letter, key in self.letter_keys.items():
            key.set_enabled(letter not in used, off_fill="gray55", off_text="gray40")
            key.enabled = letter in clickable

    # ----- players -----

    def draw_players(self, current, round_money):
        for item in self.player_items:
            item.undraw()
        self.player_items = []
        label_item = label(self.win, 1400, 505, "This round          Total", 15, "gray25", "italic")
        self.player_items.append(label_item)
        for index, player in enumerate(self.players):
            y1 = 525 + index * 108
            fill = "gold" if index == current else "white"
            self.player_items.append(box(self.win, 1225, y1, 1580, y1 + 98, fill, width=3 if index == current else 1))
            name, size = fit_text(player["name"], [(24, 20, 1), (18, 28, 1), (14, 36, 1)])
            self.player_items.append(label(self.win, 1402, y1 + 28, name, size))
            self.player_items.append(label(self.win, 1315, y1 + 70, money(round_money[index]), 22, "dark green"))
            self.player_items.append(label(self.win, 1495, y1 + 70, money(player["total"]), 22, "navy"))

    def say(self, text):
        wrapped, size = fit_text(text, [(22, 80, 1), (18, 100, 1), (15, 120, 2)])
        self.message.setText(wrapped)
        self.message.setSize(font_size(size))


# --------------------------------------------------------------------------
# Screens before and after the rounds
# --------------------------------------------------------------------------

def setup_screen(win):  # Type in the player names. Returns a list of names.
    clear(win)
    label(win, 801, 150, "WHEEL OF FORTUNE", 36)
    label(win, 801, 250, "Type the player or team names (leave a box empty if you have fewer players)", 22)
    entries = []
    for index in reversed(range(MAX_PLAYERS)):  # drawn last to first so the cursor starts in box 1
        label(win, 560, 360 + index * 90, f"Player {index + 1}", 24)
        entry = Entry(Point(880, 360 + index * 90), 22)
        entry.setSize(font_size(22))
        entry.setFill("white")
        entry.setText(f"Player {index + 1}" if index < 2 else "")
        entry.draw(win)
        entries.insert(0, entry)
    start = Button(win, 551, 760, 1051, 900, "START", fill="forest green", size=34, value="start")
    wait_for_button(win, [start])

    names = [entry.getText().strip()[:24] for entry in entries]
    names = [name for name in names if name]
    return names or ["Player 1"]


def final_screen(win, players):  # Show the final scores. Returns True to play again.
    clear(win)
    ranked = sorted(players, key=lambda player: -player["total"])
    best = ranked[0]["total"]
    winners = [player["name"] for player in ranked if player["total"] == best]
    headline = f"{winners[0]} WINS!" if len(winners) == 1 else "IT'S A TIE!"
    label(win, 801, 150, headline, 36, "dark green")
    for index, player in enumerate(ranked):
        label(win, 801, 300 + index * 90, f"{player['name']}:  {money(player['total'])}", 32)
    again = Button(win, 300, 760, 700, 900, "PLAY AGAIN", fill="blue", size=28, value=True)
    close = Button(win, 902, 760, 1302, 900, "QUIT", fill="gray30", size=28, value=False)
    return wait_for_button(win, [again, close]).value


# --------------------------------------------------------------------------
# One round
# --------------------------------------------------------------------------

def play_round(win, puzzle, players, first_player, round_number, total_rounds):
    screen = Screen(win, puzzle, players, round_number, total_rounds)
    answer_letters = set(ch for ch in puzzle["puzzle"] if ch in ALPHABET)
    used = set()                              # letters that have been called
    round_money = [0] * len(players)
    current = first_player

    def name():
        return players[current]["name"]

    def pick_letter(choices):  # Wait for one of these letters to be clicked or typed
        screen.set_letters(used, choices)
        for button in (screen.spin, screen.vowel, screen.solve):
            button.set_enabled(False)
        keys = {letter.lower(): screen.letter_keys[letter] for letter in choices}
        letter = wait_for_button(win, [screen.letter_keys[letter] for letter in choices], keys).value
        used.add(letter)
        return letter

    def call_letter(letter):  # Reveal the letter and return how many there are
        count = puzzle["puzzle"].count(letter)
        if count:
            screen.reveal(letter)
        return count

    def next_player():
        return (current + 1) % len(players)

    note = ""  # what just happened, shown in front of the next instruction
    while True:
        # The round is over as soon as every letter is showing
        if answer_letters <= used:
            break

        consonants_left = [letter for letter in ALPHABET if letter not in VOWELS and letter not in used]
        vowels_left = [letter for letter in VOWELS if letter not in used]
        hidden_consonants = any(letter in answer_letters for letter in consonants_left)
        hidden_vowels = any(letter in answer_letters for letter in vowels_left)

        screen.draw_players(current, round_money)
        screen.set_letters(used, [])
        screen.spin.set_enabled(hidden_consonants)
        screen.vowel.set_enabled(hidden_vowels and round_money[current] >= VOWEL_COST)
        screen.solve.set_enabled(True)
        screen.correct.set_enabled(False)
        screen.wrong.set_enabled(False)

        hint = "spin, buy a vowel or solve"
        if not hidden_consonants:
            hint = "only vowels are left - buy a vowel or solve"
        screen.say(f"{note}{name()}: {hint}")
        note = ""

        action = wait_for_button(win, [screen.spin, screen.vowel, screen.solve], keys={"space": screen.spin}).value

        if action == "spin":
            for button in (screen.spin, screen.vowel, screen.solve):
                button.set_enabled(False)
            screen.say(f"{name()} spins...")
            wedge = screen.spin_wheel()
            if wedge == BANKRUPT:
                round_money[current] = 0
                note = f"BANKRUPT! {name()} loses this round's money.  "
                current = next_player()
            elif wedge == LOSE_A_TURN:
                note = f"{name()} loses a turn.  "
                current = next_player()
            else:
                screen.say(f"{name()} spun {money(wedge)} - pick a consonant")
                letter = pick_letter(consonants_left)
                count = call_letter(letter)
                if count:
                    round_money[current] += wedge * count
                    note = f"{count} {letter}{'s' if count > 1 else ''} for {money(wedge * count)}!  "
                else:
                    note = f"No {letter}.  "
                    current = next_player()

        elif action == "vowel":
            round_money[current] -= VOWEL_COST
            screen.draw_players(current, round_money)
            screen.say(f"{name()} bought a vowel - pick one")
            letter = pick_letter(vowels_left)
            count = call_letter(letter)
            if count:
                note = f"{count} {letter}{'s' if count > 1 else ''}.  "
            else:
                note = f"No {letter}.  "
                current = next_player()

        else:  # solve
            for button in (screen.spin, screen.vowel, screen.solve):
                button.set_enabled(False)
            screen.correct.set_enabled(True)
            screen.wrong.set_enabled(True)
            screen.say(f"{name()} is solving - say the answer out loud. Host: is it right?")
            if wait_for_button(win, [screen.correct, screen.wrong]).value == "correct":
                break
            note = "Not the answer.  "
            current = next_player()

    # Somebody solved it: only the winner keeps this round's money
    screen.reveal_all()
    prize = max(round_money[current], MINIMUM_ROUND_WIN)
    players[current]["total"] += prize
    round_money = [prize if index == current else 0 for index in range(len(players))]
    screen.draw_players(current, round_money)
    screen.set_letters(used, [])
    for button in (screen.spin, screen.vowel, screen.solve, screen.correct, screen.wrong):
        button.undraw()
    screen.say(f"{name()} solves the puzzle and banks {money(prize)}!")
    last = round_number == total_rounds
    proceed = Button(win, 700, 760, 1070, 900, "FINAL SCORES" if last else "NEXT ROUND",
                     fill="forest green", size=26, value="next")
    wait_for_button(win, [proceed], keys={"space": proceed, "return": proceed})


# --------------------------------------------------------------------------
# The whole game
# --------------------------------------------------------------------------

def wheel_main(puzzle_file=None):
    puzzles = load_puzzles(puzzle_file)
    win = new_window("Wheel", background="light sky blue")
    unused = []  # puzzles not played yet today
    try:
        while True:
            players = [{"name": player_name, "total": 0} for player_name in setup_screen(win)]
            total_rounds = min(ROUNDS, len(puzzles))
            for round_number in range(1, total_rounds + 1):
                if not unused:
                    unused = puzzles[:]
                    if SHUFFLE_PUZZLES:
                        random.shuffle(unused)
                puzzle = unused.pop(0)
                first_player = (round_number - 1) % len(players)
                play_round(win, puzzle, players, first_player, round_number, total_rounds)
            if not final_screen(win, players):
                break
        win.close()
    except GraphicsError:
        pass  # the window was closed with the X button


if __name__ == "__main__":
    try:
        wheel_main(sys.argv[1] if len(sys.argv) > 1 else None)
    except GameFileError as problem:
        print()
        print("There is a problem with the puzzle file:")
        print("  ", problem)
        print()
        input("Press Enter to close.")
