"""Shared helpers for fifth_grader.py and wheel.py.

Everything is drawn on a 1602x1002 grid (the same as the Jeopardy board) and the
window shrinks to fit smaller screens.
"""

import csv
import os
import textwrap

import graphics
from graphics import GraphWin, Point, Rectangle, Text, GraphicsError
from time import sleep

BOARD_WIDTH = 1602
BOARD_HEIGHT = 1002

SCALE = None  # worked out the first time a window is opened


class GameFileError(Exception):
    """Raised with a plain-English message when a spreadsheet has a problem."""


# --------------------------------------------------------------------------
# Windows and text
# --------------------------------------------------------------------------

def screen_scale():  # How much to shrink the window so it fits on this screen
    root = graphics._root
    usable_width = root.winfo_screenwidth() - 20
    usable_height = root.winfo_screenheight() - 90  # room for the title bar and taskbar
    return min(1.0, usable_width / BOARD_WIDTH, usable_height / BOARD_HEIGHT)


def new_window(title, background="light blue"):
    global SCALE
    if SCALE is None:
        SCALE = screen_scale()
    win = GraphWin(title, int(BOARD_WIDTH * SCALE), int(BOARD_HEIGHT * SCALE))
    win.setCoords(0, BOARD_HEIGHT, BOARD_WIDTH, 0)
    win.setBackground(background)
    return win


def font_size(size):  # Shrink text along with the window (graphics.py allows sizes 5 to 36)
    return max(5, min(36, int(round(size * (SCALE or 1.0)))))


def fit_text(text, choices):  # Wrap long text, using a smaller size if it needs too many lines
    # choices is a list of (font size, characters per line, most lines allowed)
    for size, width, max_lines in choices:
        lines = []
        for part in str(text).split("\n"):
            lines += textwrap.wrap(part, width) or [""]
        if len(lines) <= max_lines:
            break
    return "\n".join(lines), size


def label(win, x, y, text, size=24, color="black", style="bold"):  # Draw text and return it
    item = Text(Point(x, y), text)
    item.setStyle(style)
    item.setSize(font_size(size))
    item.setFill(color)
    item.draw(win)
    return item


def box(win, x1, y1, x2, y2, fill, outline="black", width=1):  # Draw a rectangle and return it
    item = Rectangle(Point(x1, y1), Point(x2, y2))
    item.setFill(fill)
    item.setOutline(outline)
    item.setWidth(width)
    item.draw(win)
    return item


def clear(win):  # Remove everything that has been drawn in a window
    for item in win.items[:]:
        item.undraw()


def money(amount):  # 25000 -> "$25,000"
    return f"-${abs(amount):,}" if amount < 0 else f"${amount:,}"


# --------------------------------------------------------------------------
# Buttons and clicks
# --------------------------------------------------------------------------

class Button:
    """A clickable rectangle with text on it."""

    def __init__(self, win, x1, y1, x2, y2, text, fill="blue", text_color="white", size=22, value=None):
        self.x1, self.y1, self.x2, self.y2 = x1, y1, x2, y2
        self.fill = fill
        self.text_color = text_color
        self.value = text if value is None else value
        self.enabled = True
        self.rect = box(win, x1, y1, x2, y2, fill, width=2)
        self.text = label(win, (x1 + x2) / 2, (y1 + y2) / 2, text, size, text_color)

    def contains(self, point):
        return self.x1 < point.getX() < self.x2 and self.y1 < point.getY() < self.y2

    def set_enabled(self, enabled, off_fill="gray70", off_text="gray45"):
        self.enabled = enabled
        self.rect.setFill(self.fill if enabled else off_fill)
        self.text.setFill(self.text_color if enabled else off_text)

    def set_text(self, text):
        self.text.setText(text)

    def undraw(self):
        self.rect.undraw()
        self.text.undraw()


def wait_for_click(win):  # Pause until the window is clicked and return where
    while True:
        click = win.checkMouse()
        if click:
            return click
        sleep(0.02)


def wait_for_button(win, buttons, keys=None):
    """Wait until one of the enabled buttons is clicked and return it.

    keys is an optional {keyboard key: button} dictionary so a key press works too.
    """
    win.checkKey()  # forget keys pressed earlier
    while True:
        click = win.checkMouse()
        if click:
            for button in buttons:
                if button.enabled and button.contains(click):
                    return button
        if keys:
            key = win.checkKey().lower()
            if key in keys and keys[key].enabled:
                return keys[key]
        sleep(0.02)


# --------------------------------------------------------------------------
# Spreadsheets
# --------------------------------------------------------------------------

def read_spreadsheet(path, required):
    """Read a CSV saved from Excel or Google Sheets.

    Returns a list of (row number, {column name: text}) with column names in lower case
    without spaces, for example "Question Image" -> "questionimage".
    """
    if not os.path.isfile(path):
        raise GameFileError(f"Could not find {path}. It should be in the same folder as the game.")

    # Excel on Windows saves either "CSV UTF-8" or plain "CSV" (Windows-1252).
    with open(path, "rb") as file:
        raw = file.read()
    for encoding in ("utf-8-sig", "cp1252"):
        try:
            text = raw.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    else:
        text = raw.decode("utf-8", errors="replace")

    first_line = text.split("\n", 1)[0]
    delimiter = max([",", ";", "\t"], key=first_line.count)  # some Excel setups use ; or tabs
    rows = list(csv.reader(text.splitlines(), delimiter=delimiter))
    if not rows:
        raise GameFileError(f"{path} is empty.")

    header = ["".join(ch for ch in cell.lower() if ch.isalnum()) for cell in rows[0]]
    for name in required:
        if name not in header:
            raise GameFileError(
                f"{path} needs a column called '{name.title()}' in the first row. "
                f"The first row should have: {', '.join(word.title() for word in required)}"
            )

    result = []
    for line_number, row in enumerate(rows[1:], start=2):
        if not any(cell.strip() for cell in row):
            continue  # blank spreadsheet row
        values = {name: (row[index].strip() if index < len(row) else "") for index, name in enumerate(header)}
        result.append((line_number, values))
    return result
