# Game Night: Jeopardy, 5th Grader and Wheel

Three game-show style games for a party or classroom. Each one runs on a laptop (plug it into a TV), and the questions and puzzles live in spreadsheets you can edit in Excel or Google Sheets.

| Game | Start it with | Questions file |
|------|---------------|----------------|
| Jeopardy | `Start Board.bat` (and `Start Buzzer.bat` for phone buzzers) | `questions.csv` |
| Smarter Than a 5th Grader | `Start 5th Grader.bat` | `fifth_grader_questions.csv` |
| Wheel | `Start Wheel.bat` | `wheel_puzzles.csv` |

## One-time setup

1. Install Python from https://www.python.org/downloads/ (on Windows, tick **Add python.exe to PATH** in the installer).
2. Double-click **`Install (run once).bat`**. On Mac or Linux run `pip install -r requirements.txt` instead. (Only the Jeopardy phone buzzer needs this step.)

When you save a questions file from Excel, keep the file type as **CSV**.

---

## Jeopardy

Two parts that work on their own or together:

- **The board** (`gameboard.py`) - the big game board, with two rounds, Daily Doubles and Final Jeopardy.
- **The buzzer** (`main.py`) - a small website so players can buzz in on their phones. The host sees who buzzed first and keeps score with one tap.

### Writing your own questions

Open **`questions.csv`**. Each row is one question:

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

`questions_blank_template.csv` is an empty copy to start from. To check a file for mistakes, run `python question_loader.py questions.csv`.

Older `questions.json` files still work. The board uses `questions.csv` if it exists, otherwise `questions.json`. To play a different file: `python gameboard.py my_questions.csv`.

### Playing

**The board:** double-click **`Start Board.bat`** (or run `python gameboard.py`). Click a dollar amount to show the question, click again for the answer, and click once more to go back to the board.

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

---

## Smarter Than a 5th Grader

One contestant at a time answers 10 questions, two from each grade 1 to 5, climbing a prize ladder from $1,000 to $500,000. Then comes one bonus question for $1,000,000.

Double-click **`Start 5th Grader.bat`** (or run `python fifth_grader.py`).

### How to play

1. Pick a **host** to run the laptop and a **classmate**: another person who secretly writes down their own answer to every question.
2. The contestant picks a subject. The host reads the question.
3. The contestant answers out loud, then the host presses **SHOW ANSWER** and then **CORRECT** or **WRONG**.
4. A wrong answer ends the game. The contestant leaves with $0, or with $25,000 if they had already reached it.
5. **DROP OUT** lets the contestant leave with what they have won, even after seeing a question.

**Cheats** (each can be used once, and not on the million dollar question):

- **PEEK** - look at the classmate's answer, then use it or give your own.
- **COPY** - the classmate's answer becomes your answer, without seeing it first.
- **SAVE** - used automatically: if the contestant is wrong but the classmate is right, the host presses **SAVED** and the game goes on.

After the game, **NEXT CONTESTANT** starts a new game with questions that have not been asked yet.

### Writing your own questions

Open **`fifth_grader_questions.csv`**:

| Grade | Subject | Question | Answer |
|-------|---------|----------|--------|
| 1 | Animal Science | What do caterpillars turn into? | Butterflies (or moths) |
| 5 | U.S. Government | How many justices sit on the U.S. Supreme Court? | 9 |
| Bonus | World Geography | Which continent has no countries? | Antarctica |

- **Grade** is `1` to `5`, or `Bonus` for million dollar questions.
- You need at least 2 questions per grade and 1 bonus question. Add more and each game picks a random set.

---

## Wheel

A word puzzle game for 1 to 4 players or teams. Players spin for a dollar amount, call consonants, buy vowels and try to solve the puzzle.

Double-click **`Start Wheel.bat`** (or run `python wheel.py`).

### How to play

1. Type the player names and press **START**. A game is 3 puzzles.
2. On your turn, choose one:
   - **SPIN** - then pick a consonant (click it or type it). You win the amount for every copy of that letter in the puzzle and go again. If the letter is not there, your turn ends.
   - **BUY A VOWEL** - costs $250 of this round's money.
   - **SOLVE** - say the answer out loud. The host presses **CORRECT** or **WRONG**.
3. **BANKRUPT** wipes out your money for this round. **LOSE A TURN** passes play to the next player.
4. Whoever solves the puzzle banks their money for the round (at least $1,000). Everyone else's round money is lost.
5. Most money after the last puzzle wins.

The space bar also spins the wheel.

### Writing your own puzzles

Open **`wheel_puzzles.csv`**:

| Category | Puzzle |
|----------|--------|
| Phrase | BETTER LATE THAN NEVER |
| Place | GRAND CANYON |

- A puzzle fits 4 lines of 14 letters, and no single word can be longer than 14 letters. The game tells you which row is too long.
- Each game picks puzzles at random and does not repeat one until all have been played.
- The number of rounds, the vowel price and the wheel's wedges are settings at the top of `wheel.py`.

---

## Files

| File | What it is |
|------|------------|
| `gameboard.py` | The Jeopardy board |
| `question_loader.py` | Reads `questions.csv` / `questions.json` |
| `main.py`, `templates/`, `static/` | The Jeopardy buzzer and scoreboard website |
| `fifth_grader.py` | The 5th Grader game |
| `wheel.py` | The Wheel game |
| `game_tools.py` | Shared pieces used by `fifth_grader.py` and `wheel.py` |
| `graphics.py` | John Zelle's graphics library, used to draw all three games |
