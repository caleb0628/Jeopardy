import random
import sys

from graphics import GraphicsError
from game_tools import (GameFileError, Button, new_window, clear, label, box, fit_text,
                        money, wait_for_button, read_spreadsheet)


# A "smarter than a 5th grader" style quiz for one contestant at a time.
#
# Questions come from fifth_grader_questions.csv (open it in Excel or Google Sheets).
# Columns: Grade, Subject, Question, Answer
#   Grade is 1, 2, 3, 4 or 5. Use "Bonus" for million dollar questions.
# Each game picks two questions from every grade plus one bonus question at random.
# To use a different file:  python fifth_grader.py my_questions.csv
#
# How to play: see README.md

QUESTION_FILE = "fifth_grader_questions.csv"

# Prize for each correct answer, in order. The last question is worth MILLION.
LADDER = [1000, 2000, 5000, 10000, 25000, 50000, 100000, 175000, 300000, 500000]
MILLION = 1000000
SAFE_AMOUNT = 25000  # once you reach this, a wrong answer drops you back to it

GRADE_NAMES = {1: "1st Grade", 2: "2nd Grade", 3: "3rd Grade", 4: "4th Grade", 5: "5th Grade"}
BONUS_WORDS = {"bonus", "final", "million", "milliondollar", "b"}
QUESTION_SIZES = [(30, 52, 6), (26, 62, 8), (22, 74, 10), (18, 90, 13)]


# --------------------------------------------------------------------------
# Questions
# --------------------------------------------------------------------------

def load_questions(path=None):  # Read the spreadsheet into {grade: [questions]} plus bonus questions
    path = path or QUESTION_FILE
    grades = {grade: [] for grade in GRADE_NAMES}
    bonus = []

    for line_number, row in read_spreadsheet(path, ["grade", "subject", "question", "answer"]):
        if not row["question"] or not row["answer"]:
            continue  # a row that has not been filled in yet
        question = {"subject": row["subject"] or "General Knowledge",
                    "question": row["question"], "answer": row["answer"]}

        grade_text = "".join(ch for ch in row["grade"].lower() if ch.isalnum())
        if grade_text in BONUS_WORDS:
            question["grade"] = "bonus"
            bonus.append(question)
            continue

        digits = "".join(ch for ch in grade_text if ch.isdigit())
        if digits not in ("1", "2", "3", "4", "5"):
            raise GameFileError(
                f"Row {line_number} of {path}: the Grade column says '{row['grade']}'. "
                "Use 1, 2, 3, 4, 5 or Bonus."
            )
        question["grade"] = int(digits)
        grades[int(digits)].append(question)

    for grade, questions in grades.items():
        if len(questions) < 2:
            raise GameFileError(
                f"{path} needs at least 2 questions for grade {grade} (it has {len(questions)})."
            )
    if not bonus:
        raise GameFileError(f"{path} needs at least 1 question with Bonus in the Grade column.")
    return grades, bonus


def pick_game(grades, bonus, used):  # Choose 10 questions (2 per grade) and a bonus, avoiding repeats
    def choose(pool, count):
        fresh = [question for question in pool if id(question) not in used]
        if len(fresh) < count:  # everything has been asked - start reusing questions
            for question in pool:
                used.discard(id(question))
            fresh = pool
        picked = random.sample(fresh, count)
        used.update(id(question) for question in picked)
        return picked

    board = []
    for grade in sorted(grades):
        board += choose(grades[grade], 2)
    return board, choose(bonus, 1)[0]


# --------------------------------------------------------------------------
# Screens
# --------------------------------------------------------------------------

def draw_ladder(win, correct_count):  # Prize ladder down the left side
    amounts = LADDER + [MILLION]
    for index, amount in enumerate(amounts):
        y2 = 930 - index * 74
        if index < correct_count:
            fill, color = "forest green", "white"   # already won
        elif index == correct_count:
            fill, color = "gold", "black"           # playing for this now
        else:
            fill, color = "blue", "white"
        box(win, 30, y2 - 68, 330, y2, fill, width=2)
        text = money(amount) + ("  (safe)" if amount == SAFE_AMOUNT else "")
        label(win, 180, y2 - 34, text, 22, color)


def draw_cheats(win, cheats, x1, y1, width, height, step_x, step_y, clickable):  # Peek / Copy / Save
    buttons = {}
    for index, name in enumerate(["PEEK", "COPY", "SAVE"]):
        left, top = x1 + index * step_x, y1 + index * step_y
        available = cheats[name]
        button = Button(win, left, top, left + width, top + height,
                        name if available else name + "\n(used)", fill="dark orange", size=20, value=name)
        button.set_enabled(available)
        if name not in clickable:
            button.enabled = False  # shown, but cannot be clicked on this screen
        buttons[name] = button
    return buttons


def board_screen(win, state):  # Pick a subject (or drop out). Returns a question index or "dropout".
    clear(win)
    correct_count = state["correct"]
    label(win, 801, 45, f"Winnings: {money(state['winnings'])}        Next question: "
                        f"{money(LADDER[correct_count])}", 26)
    draw_ladder(win, correct_count)

    cards = []
    for index, question in enumerate(state["board"]):
        column, row = index % 2, index // 2
        x1, y1 = 370 + column * 440, 110 + row * 164
        text, size = fit_text(f"{GRADE_NAMES[question['grade']]}\n{question['subject']}",
                              [(24, 24, 3), (20, 30, 4), (16, 38, 5)])
        card = Button(win, x1, y1, x1 + 420, y1 + 150, text, fill="blue", size=size, value=index)
        if index in state["asked"]:
            card.set_enabled(False)
        cards.append(card)

    label(win, 1420, 110, "CHEATS", 22)
    draw_cheats(win, state["cheats"], 1280, 140, 280, 90, 0, 106, clickable=[])
    dropout = Button(win, 1280, 780, 1560, 930, f"DROP OUT\nkeep {money(state['winnings'])}",
                     fill="firebrick", size=22, value="dropout")
    dropout.set_enabled(state["winnings"] > 0)
    label(win, 801, 965, "Contestant: pick a subject", 20, style="italic")

    return wait_for_button(win, cards + [dropout]).value


def question_screen(win, state, question, value, final=False):
    """Show one question. Returns "correct", "wrong" or "dropout"."""
    clear(win)
    grade = "MILLION DOLLAR QUESTION" if final else GRADE_NAMES[question["grade"]]
    label(win, 801, 60, f"{grade}  -  {question['subject']}", 30)
    label(win, 801, 120, f"For {money(value)}", 26, "dark green")

    text, size = fit_text(question["question"], QUESTION_SIZES)
    label(win, 801, 360, text, size)
    note = label(win, 801, 640, "", 22, "dark orange", "bold italic")

    # Before the answer: cheats, show answer, drop out (none of these on the million dollar question)
    cheats = {}
    dropout = None
    if not final:
        cheats = draw_cheats(win, state["cheats"], 60, 800, 200, 120, 220, 0, clickable=["PEEK", "COPY"])
        dropout = Button(win, 1242, 800, 1542, 920, f"DROP OUT\nkeep {money(state['winnings'])}",
                         fill="firebrick", size=20, value="dropout")
        dropout.set_enabled(state["winnings"] > 0)
    show = Button(win, 760, 800, 1200, 920, "SHOW ANSWER", fill="blue", size=26, value="show")

    while True:
        choices = [show] + ([dropout] if dropout else []) + [cheats[name] for name in ("PEEK", "COPY") if name in cheats]
        picked = wait_for_button(win, choices, keys={"space": show}).value
        if picked == "show":
            break
        if picked == "dropout":
            return "dropout"
        state["cheats"][picked] = False
        cheats[picked].set_text(picked + "\n(used)")
        cheats[picked].set_enabled(False)
        if picked == "PEEK":
            note.setText("PEEK: look at your classmate's answer. Use it or give your own.")
        else:
            note.setText("COPY: your classmate's answer is now your answer.")

    # After the answer: the host says whether it was right
    for button in [show] + ([dropout] if dropout else []) + list(cheats.values()):
        button.undraw()
    note.setText("")
    answer_text, answer_size = fit_text(question["answer"], QUESTION_SIZES)
    label(win, 801, 560, "Answer:", 22, "gray25", "italic")
    label(win, 801, 640, answer_text, answer_size, "dark green")

    correct = Button(win, 300, 800, 700, 920, "CORRECT", fill="forest green", size=28, value="correct")
    wrong = Button(win, 902, 800, 1302, 920, "WRONG", fill="firebrick", size=28, value="wrong")
    buttons = [correct, wrong]
    if not final and state["cheats"]["SAVE"]:
        label(win, 801, 745, "If the contestant is wrong but the classmate is right, press SAVED.", 18, style="italic")
        correct.undraw()
        wrong.undraw()
        correct = Button(win, 100, 800, 500, 920, "CORRECT", fill="forest green", size=28, value="correct")
        saved = Button(win, 601, 800, 1001, 920, "SAVED", fill="dark orange", size=28, value="saved")
        wrong = Button(win, 1102, 800, 1502, 920, "WRONG", fill="firebrick", size=28, value="wrong")
        buttons = [correct, saved, wrong]

    picked = wait_for_button(win, buttons).value
    if picked == "saved":
        state["cheats"]["SAVE"] = False
        return "correct"
    return picked


def million_offer_screen(win, state, bonus):  # See the subject, then decide to play or walk away
    clear(win)
    label(win, 801, 150, "THE MILLION DOLLAR QUESTION", 36)
    label(win, 801, 300, f"The subject is:  {bonus['subject']}", 32, "dark green")
    label(win, 801, 470,
          f"You have {money(state['winnings'])}.\n\n"
          f"Answer correctly and win {money(MILLION)}.\n"
          f"Answer wrong and you drop to {money(SAFE_AMOUNT)}.\n\n"
          "No cheats, and no dropping out once you see the question.", 24)
    play = Button(win, 250, 750, 700, 900, "PLAY FOR\n" + money(MILLION), fill="forest green", size=28, value="play")
    walk = Button(win, 902, 750, 1352, 900, f"WALK AWAY\nwith {money(state['winnings'])}",
                  fill="firebrick", size=28, value="walk")
    return wait_for_button(win, [play, walk]).value


def end_screen(win, winnings, outcome):  # Final result. Returns True to play another game.
    clear(win)
    if outcome == "million":
        headline, color = "YOU ARE SMARTER THAN A 5TH GRADER!", "dark green"
    elif outcome == "dropout":
        headline, color = "You dropped out. Say it with us:\n\"I am not smarter than a 5th grader.\"", "black"
    else:
        headline, color = "Wrong answer!\n\"I am not smarter than a 5th grader.\"", "firebrick"
    label(win, 801, 300, headline, 34, color)
    label(win, 801, 520, f"You leave with {money(winnings)}", 36, "dark green")
    again = Button(win, 300, 750, 700, 900, "NEXT\nCONTESTANT", fill="blue", size=26, value=True)
    close = Button(win, 902, 750, 1302, 900, "QUIT", fill="gray30", size=26, value=False)
    return wait_for_button(win, [again, close]).value


def start_screen(win):
    clear(win)
    label(win, 801, 280, "ARE YOU SMARTER THAN", 36)
    label(win, 801, 360, "A 5TH GRADER?", 36)
    label(win, 801, 560,
          "10 questions from 1st to 5th grade, then one for a million.\n"
          "Pick a classmate to write down their answer to every question.", 24)
    start = Button(win, 551, 740, 1051, 890, "START", fill="forest green", size=34, value="start")
    wait_for_button(win, [start], keys={"space": start, "return": start})


# --------------------------------------------------------------------------
# One full game
# --------------------------------------------------------------------------

def play_game(win, board, bonus):  # Returns (winnings, outcome)
    state = {
        "board": board,
        "asked": set(),
        "correct": 0,       # how many questions answered correctly so far
        "winnings": 0,
        "cheats": {"PEEK": True, "COPY": True, "SAVE": True},
    }

    while state["correct"] < len(LADDER):
        choice = board_screen(win, state)
        if choice == "dropout":
            return state["winnings"], "dropout"

        state["asked"].add(choice)
        result = question_screen(win, state, board[choice], LADDER[state["correct"]])
        if result == "dropout":
            return state["winnings"], "dropout"
        if result == "wrong":
            return (SAFE_AMOUNT if state["winnings"] >= SAFE_AMOUNT else 0), "wrong"

        state["winnings"] = LADDER[state["correct"]]
        state["correct"] += 1

    # All ten correct - offer the million dollar question
    if million_offer_screen(win, state, bonus) == "walk":
        return state["winnings"], "dropout"
    if question_screen(win, state, bonus, MILLION, final=True) == "correct":
        return MILLION, "million"
    return SAFE_AMOUNT, "wrong"


def fifth_grader_main(question_file=None):
    grades, bonus = load_questions(question_file)
    used = set()  # questions already asked today, so the next contestant gets new ones
    win = new_window("Smarter Than a 5th Grader?")
    try:
        while True:
            start_screen(win)
            board, bonus_question = pick_game(grades, bonus, used)
            winnings, outcome = play_game(win, board, bonus_question)
            if not end_screen(win, winnings, outcome):
                break
        win.close()
    except GraphicsError:
        pass  # the window was closed with the X button


if __name__ == "__main__":
    try:
        fifth_grader_main(sys.argv[1] if len(sys.argv) > 1 else None)
    except GameFileError as problem:
        print()
        print("There is a problem with the question file:")
        print("  ", problem)
        print()
        input("Press Enter to close.")
