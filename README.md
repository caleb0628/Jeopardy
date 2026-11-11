# Jeopardy

A Jeopardy game for a party or classroom. It has two parts that work on their own or together:

- **The board** (`gameboard.py`) - the big game board for a TV or projector, with two rounds, Daily Doubles and Final Jeopardy.
- **The buzzer** (`main.py`) - a small website so players can buzz in on their phones. The host sees who buzzed first and keeps score with one tap.

## One-time setup

1. Install Python from https://www.python.org/downloads/ (on Windows, tick **Add python.exe to PATH** in the installer).
2. Double-click **`Install (run once).bat`**. On Mac or Linux run `pip install -r requirements.txt` instead.

## Writing your own questions

Open **`questions.csv`** in Excel or Google Sheets. Each row is one question:

| Round | Category | Value | Question | Answer | Question Image | Answer Image |
|-------|----------|-------|----------|--------|----------------|--------------|
| 1 | Science | 200 | This planet is known as the Red Planet | Mars | | |
| 2 | Space | 1600 | The galaxy that contains our solar system | The Milky Way | | |
| Final | World Landmarks | | Begun more than 2,000 years ago... | The Great Wall of China | | |

- **Round** is `1`, `2` (Double Jeopardy) or `Final`. Leave out round 2 or Final if you do not want them.
- Each round fits **6 categories** with **5 questions** each. Spell a category the same way on all of its rows.
- **Value** is the dollar amount on the board. Leave it blank and it fills in by itself.
- A row with no question is simply left empty on the board.
- **Images** are optional: put a png in a folder called `images` next to the game and type its file name (for example `eiffel.png`) in the image column.
- When you save from Excel, keep the file type as **CSV**.

`questions_blank_template.csv` is an empty copy to start from. To check a file for mistakes, run `python question_loader.py questions.csv`.

Older `questions.json` files still work. The board uses `questions.csv` if it exists, otherwise `questions.json`. To play a different file: `python gameboard.py my_questions.csv`.

## Playing

**The board:** double-click **`Start Board.bat`** (or run `python gameboard.py`). Click a dollar amount to show the question, click again for the answer, and click once more to go back to the board. The board shrinks to fit smaller screens.

**The buzzer:** double-click **`Start Buzzer.bat`** (or run `python main.py`) and leave that window open. It prints two addresses:

- The host opens `http://localhost:5000` on the computer (or the player address on a phone) and presses **Create a Room (Host)**.
- Players on the same wifi open the player address shown in the window, type a name and the room code, and press **Join a Room**.

If players cannot connect, Windows Firewall is usually blocking it: allow Python on private networks when Windows asks.

**Host screen:**

- **Buzzed in** lists players in the order they buzzed, with the first one highlighted.
- **Correct** adds the amount to that player's score and locks the buzzers. **Wrong** subtracts it and moves to the next player in line.
- **Reset buzzers** clears the list and lets everyone buzz again.
- When the board and buzzer run on the same computer, the amount is set automatically each time a question is opened, and the buzzers reset by themselves.
- For **Daily Doubles** and **Final Jeopardy**, type the wager in the amount box and use the **+** or **-** next to that player's score. Tap a score to type in a correction.

## Files

| File | What it is |
|------|------------|
| `gameboard.py` | The game board |
| `question_loader.py` | Reads `questions.csv` / `questions.json` |
| `questions.csv` | The questions (a sample game is included) |
| `main.py` | The buzzer and scoreboard website |
| `templates/`, `static/` | The buzzer web pages |
| `graphics.py` | John Zelle's graphics library, used to draw the board |
