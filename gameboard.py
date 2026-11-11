import json
import sys
import textwrap
import threading
import urllib.request
from random import sample

import graphics
from graphics import *
from time import sleep, time as now  # after graphics, which has its own "time"
from question_loader import load_questions, QuestionFileError


# Questions come from questions.csv (a spreadsheet) or the older questions.json.
# To use a different file:  python gameboard.py my_questions.csv
#
# Images are optional and must be png files inside the "images" folder.
# The board is drawn on a 1602x1002 grid and shrinks to fit smaller screens.

BOARD_WIDTH = 1602
BOARD_HEIGHT = 1002
QUESTION_SECONDS = 10          # countdown shown on each question
DAILY_DOUBLES = {1: 1, 2: 2}   # how many daily doubles in round 1 and round 2

# If the buzzer website (main.py) is running on this computer, the board tells it
# which question is open so the host's phone shows the right dollar amount.
BUZZER_URL = "http://127.0.0.1:5000/board"

SCALE = 1.0  # set in gameboard_main() once the screen size is known


def screen_scale():  # Work out how much to shrink the board so it fits on this screen
    root = graphics._root
    usable_width = root.winfo_screenwidth() - 20
    usable_height = root.winfo_screenheight() - 90  # leave room for the title bar and taskbar
    return min(1.0, usable_width / BOARD_WIDTH, usable_height / BOARD_HEIGHT)


def new_window(title):  # Create a window that uses the 1602x1002 grid no matter its real size
    win = GraphWin(title, int(BOARD_WIDTH * SCALE), int(BOARD_HEIGHT * SCALE))
    win.setCoords(0, BOARD_HEIGHT, BOARD_WIDTH, 0)
    win.setBackground("light blue")
    return win


def font_size(size):  # Shrink text along with the window (graphics.py allows sizes 5 to 36)
    return max(5, min(36, int(round(size * SCALE))))


def fit_text(text, choices):  # Wrap long text, using a smaller size if it needs too many lines
    # choices is a list of (font size, characters per line, most lines allowed)
    for size, width, max_lines in choices:
        lines = []
        for part in str(text).split("\n"):
            lines += textwrap.wrap(part, width) or [""]
        if len(lines) <= max_lines:
            break
    return "\n".join(lines), size


TITLE_SIZES = [(26, 13, 3), (22, 15, 4), (18, 19, 5), (14, 24, 7)]
QUESTION_SIZES = [(28, 58, 9), (24, 68, 11), (20, 82, 13), (16, 100, 18)]


def notify_buzzer(event, **details):  # Tell the buzzer website what the board is doing
    def send():
        try:
            body = json.dumps(dict(details, event=event)).encode("utf-8")
            request = urllib.request.Request(
                BUZZER_URL, data=body, headers={"Content-Type": "application/json"})
            urllib.request.urlopen(request, timeout=1).close()
        except Exception:
            pass  # the buzzer website is not running - the board works fine without it

    threading.Thread(target=send, daemon=True).start()


def wait_for_click(win):  # Pause until the window is clicked
    while True:
        if win.checkMouse():
            return
        sleep(0.02)


def gameWindow(categories, round_number):  # Create a game window with categories and questions
    win = new_window("Jasonpardy" if round_number == 1 else "Jasonpardy - Double Jeopardy")

    boxes = []  # List to store question card objects (Rectangles), None where there is no question
    labels = []  # List to store labels on question card text objects

    # Create category title cards
    for i in range(6):
        titlecard = Rectangle(Point((int(i))*267, 0), Point((int(i)+1)*267, 167))
        titlecard.setFill("Blue")
        titlecard.draw(win)
        if i < len(categories):
            title_text, title_size = fit_text(categories[i]["title"], TITLE_SIZES)
            title_label = Text(Point((int(i)+0.5)*267, (0.5)*167), title_text)
            title_label.setStyle("bold")
            title_label.setSize(font_size(title_size))
            title_label.setFill("white")
            title_label.draw(win)

        # Create question card objects for each question in the category
        for j in range(5):
            clue = categories[i]["clues"][j] if i < len(categories) else None
            if clue is None:  # no question written for this spot - leave it empty
                boxes.append(None)
                labels.append(None)
                continue

            quesiton_card = Rectangle(Point((int(i))*267, (int(j)+1)*167), Point((int(i)+1)*267, (int(j)+2)*167))
            quesiton_card.setFill("Blue")
            quesiton_card.draw(win)
            quesiton__label = Text(Point((int(i)+0.5)*267, (int(j)+1.5)*167), f"${clue['value']}")
            quesiton__label.setStyle("bold")
            quesiton__label.setSize(font_size(28))
            quesiton__label.setFill("#FFFF00")
            quesiton__label.draw(win)

            boxes.append(quesiton_card)
            labels.append(quesiton__label)

    # Add dividers between questions and between categories
    for j in range(5):
        divider = Rectangle(Point(0, (int(j)+1)*167 - 3), Point(1602, (int(j)+1)*167 + 3))
        divider.setFill("Black")
        divider.draw(win)
    for i in range(6):
        divider = Rectangle(Point((int(i) + 1)*267 - 3, 0), Point((int(i) + 1)*267 + 3, 1002))
        divider.setFill("Black")
        divider.draw(win)

    return win, boxes, labels


def clicked(click, rect):  # Check if a point (click) is within a given rectangle
    if not click or rect is None:
        return False
    mx, my = click.getX(), click.getY()
    x1, y1 = rect.getP1().getX(), rect.getP1().getY()
    x2, y2 = rect.getP2().getX(), rect.getP2().getY()

    return (x1 < mx < x2) and (y1 < my < y2)


def splash(win, text):  # Show a big message in the middle of a window until it is clicked
    label = Text(Point(801, 501), text)
    label.setStyle("bold")
    label.setSize(font_size(36))
    label.setFill("black")
    label.draw(win)
    wait_for_click(win)
    label.undraw()


def show_image(win, image_path, text_label):  # Draw an image and slide the text underneath it
    if not image_path:
        return None, 0
    try:
        image = Image(Point(801, 420), image_path)
        image.draw(win)
    except Exception:
        print(f"Could not open the image {image_path} - showing the text without it.")
        return None, 0
    imgHeight = image.getHeight() / SCALE
    dy = (((1002 - (420 + imgHeight/2)) / 2) + 420 + imgHeight/2) - 501
    text_label.move(0, dy)
    return image, dy


def question(clue, title, daydub=False, fj=False):  # Display question/answer window
    win2 = new_window("Jeopardy")
    try:
        # Display the title of the category with point value
        heading = " ".join(str(title).split())
        if not fj:
            heading = heading + "\n$" + str(clue["value"])
        title_label = Text(Point(801, 90), heading)
        title_label.setStyle("bold italic")
        title_label.setSize(font_size(28))
        title_label.setFill("black")
        title_label.draw(win2)

        if daydub:  # Check if chosen question is the daily double
            notify_buzzer("open", category=heading.split("\n")[0], value=clue["value"], daily_double=True)
            splash(win2, "! ! ! DAILY ! ! !\n! ! ! DOUBLE ! ! !")
        elif fj:  # Give everyone time to write down a wager before the question shows
            notify_buzzer("open", category=heading, value=0, final=True)
            splash(win2, "FINAL JEOPARDY\n\nWrite down your wagers")
        else:
            notify_buzzer("open", category=heading.split("\n")[0], value=clue["value"])

        # Display the question text and image if provided
        question_text, question_size = fit_text(clue["question"], QUESTION_SIZES)
        question_label = Text(Point(801, 501), question_text)
        question_label.setStyle("bold")
        question_label.setSize(font_size(question_size))
        question_label.setFill("black")
        question_label.draw(win2)

        image, dy = show_image(win2, clue["q_image"], question_label)

        # Display question countdown (Final Jeopardy has no countdown)
        count_label = Text(Point(1200, 90), str(QUESTION_SECONDS))
        count_label.setStyle("bold italic")
        count_label.setSize(font_size(36))
        count_label.setFill("red")
        if not fj:
            count_label.draw(win2)

        # Wait for a click in the window, ticking the countdown once a second
        started = now()
        while not win2.checkMouse():
            remaining = max(0, QUESTION_SECONDS - int(now() - started))
            if not fj and count_label.getText() != str(remaining):
                count_label.setText(str(remaining))
            sleep(0.02)

        # Remove countdown
        count_label.undraw()

        # Delete image and return question label to center of window
        if image is not None:
            image.undraw()
            question_label.move(0, -1 * dy)

        # Display the answer text
        answer_text, answer_size = fit_text(clue["answer"], QUESTION_SIZES)
        question_label.setText(answer_text)
        question_label.setSize(font_size(answer_size))

        image, dy = show_image(win2, clue["a_image"], question_label)

        # Wait for a click in the window
        wait_for_click(win2)
    except GraphicsError:
        pass  # the question window was closed with the X button - go back to the board
    finally:
        notify_buzzer("close")
        # Close the window after the user clicks
        win2.close()


def play_round(game_round):  # Show one board and play it until every question is answered
    categories = game_round["categories"]
    round_number = game_round["multiplier"]

    win, boxes, labels = gameWindow(categories, round_number)
    if round_number > 1:
        banner = Rectangle(Point(301, 351), Point(1301, 651))
        banner.setFill("light blue")
        banner.draw(win)
        splash(win, "DOUBLE JEOPARDY!\n\nClick to start")
        banner.undraw()

    # Only spots that actually have a question can be picked or be a daily double
    available = [j for j in range(30) if boxes[j] is not None]
    questions_answered = set()
    daily_double_count = min(DAILY_DOUBLES.get(round_number, 1), len(available))
    daily_doubles = set(sample(available, daily_double_count))

    # Loop until every question in the round is answered
    while len(questions_answered) < len(available):
        click = win.checkMouse()
        if not click:
            sleep(0.02)
            continue

        for j in available:  # Check all question object boxes if they have been clicked on
            if j not in questions_answered and clicked(click, boxes[j]):
                boxes[j].undraw()
                labels[j].undraw()

                daydub = (j in daily_doubles)  # Boolean if daily double
                category = categories[int(j/5)]

                question(category["clues"][j % 5], title=category["title"], daydub=daydub)  # Open question window

                questions_answered.add(j)  # Add question index to answered list
                win.checkMouse()  # forget any clicks made on the board while the question was open

    win.close()  # Close round window


def gameboard_main(question_file=None):  # Read questions from a spreadsheet (csv) or JSON file
    global SCALE
    game = load_questions(question_file)
    SCALE = screen_scale()

    try:
        for game_round in game["rounds"]:
            play_round(game_round)

        # Display the final question
        if game["final"] is not None:
            question(game["final"]["clue"], title=game["final"]["category"], fj=True)
    except GraphicsError:
        pass  # the board was closed with the X button


if __name__ == "__main__":
    try:
        gameboard_main(sys.argv[1] if len(sys.argv) > 1 else None)
    except QuestionFileError as problem:
        print()
        print("There is a problem with the question file:")
        print("  ", problem)
        print()
        input("Press Enter to close.")
