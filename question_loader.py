"""Loads Jeopardy questions for gameboard.py.

Two file types are supported:

1. A spreadsheet saved as CSV (the easy way) - see questions.csv.
   Columns: Round, Category, Value, Question, Answer, Question Image, Answer Image
     Round    -> 1, 2 (Double Jeopardy) or Final
     Value    -> dollar amount (200, 400 ...). Leave blank to fill in automatically.
     Images   -> optional file name of a png inside the "images" folder.

2. The original questions.json layout, so old question sets keep working.

Either way the game gets back the same structure:

    {
        "rounds": [
            {"multiplier": 1, "categories": [{"title": str, "clues": [clue or None] * 5}, ...]},
            {"multiplier": 2, "categories": [...]},
        ],
        "final": {"category": str, "clue": clue} or None,
    }

    clue = {"question": str, "answer": str, "value": int,
            "q_image": path or None, "a_image": path or None}
"""

import csv
import json
import os

CATEGORIES_PER_ROUND = 6
CLUES_PER_CATEGORY = 5
IMAGE_FOLDER = "images"

# Files looked for (in this order) when no file name is given.
DEFAULT_FILES = ["questions.csv", "questions.json", "temp_questions.json"]

FINAL_NAMES = {"final", "f", "fj", "final jeopardy", "finaljeopardy"}
ROUND_NAMES = {
    "1": 1, "one": 1, "single": 1, "jeopardy": 1, "round 1": 1,
    "2": 2, "two": 2, "double": 2, "double jeopardy": 2, "round 2": 2,
}


class QuestionFileError(Exception):
    """Raised with a plain-English message when the question file has a problem."""


def find_question_file(folder="."):
    for name in DEFAULT_FILES:
        path = os.path.join(folder, name)
        if os.path.isfile(path):
            return path
    raise QuestionFileError(
        "No question file found. Put a questions.csv (or questions.json) "
        "in the same folder as gameboard.py."
    )


def load_questions(path=None):
    """Load a question file. Picks the file type from its extension."""
    if path is None:
        path = find_question_file()
    if not os.path.isfile(path):
        raise QuestionFileError(f"Could not find the question file: {path}")

    folder = os.path.dirname(os.path.abspath(path))
    if path.lower().endswith(".json"):
        game = _load_json(path, folder)
    else:
        game = _load_csv(path, folder)

    if not game["rounds"] and game["final"] is None:
        raise QuestionFileError(f"{path} does not contain any questions.")
    return game


# --------------------------------------------------------------------------
# Spreadsheet (CSV) files
# --------------------------------------------------------------------------

def _read_text(path):
    # Excel on Windows saves either "CSV UTF-8" or plain "CSV" (Windows-1252).
    with open(path, "rb") as file:
        raw = file.read()
    for encoding in ("utf-8-sig", "cp1252"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def _header_key(text):
    return "".join(ch for ch in text.lower() if ch.isalnum())


def _load_csv(path, folder):
    text = _read_text(path)
    first_line = text.split("\n", 1)[0]
    # Some versions of Excel use ; or tabs instead of commas.
    delimiter = max([",", ";", "\t"], key=first_line.count)
    rows = list(csv.reader(text.splitlines(), delimiter=delimiter))
    if not rows:
        raise QuestionFileError(f"{path} is empty.")

    header = [_header_key(cell) for cell in rows[0]]
    wanted = {
        "round": ["round"],
        "category": ["category"],
        "value": ["value", "points", "amount"],
        "question": ["question", "clue"],
        "answer": ["answer"],
        "q_image": ["questionimage", "qimage"],
        "a_image": ["answerimage", "aimage"],
    }
    columns = {}
    for field, names in wanted.items():
        for name in names:
            if name in header:
                columns[field] = header.index(name)
                break
    for required in ("category", "question", "answer"):
        if required not in columns:
            raise QuestionFileError(
                f"{path} needs a column called '{required.title()}' in the first row. "
                "The first row should be: Round, Category, Value, Question, Answer, "
                "Question Image, Answer Image"
            )

    def cell(row, field):
        index = columns.get(field)
        if index is None or index >= len(row):
            return ""
        return row[index].strip()

    # round number -> {category title -> list of clues}, keeping spreadsheet order
    rounds = {}
    final = None

    for line_number, row in enumerate(rows[1:], start=2):
        if not any(part.strip() for part in row):
            continue  # blank spreadsheet row

        category = cell(row, "category")
        question = cell(row, "question")
        answer = cell(row, "answer")
        q_image = _image_path(cell(row, "q_image"), folder)
        a_image = _image_path(cell(row, "a_image"), folder)
        round_text = cell(row, "round").lower() or "1"

        if round_text in FINAL_NAMES:
            if question or answer or q_image or a_image:
                final = {
                    "category": category or "Final Jeopardy",
                    "clue": {"question": question, "answer": answer, "value": 0,
                             "q_image": q_image, "a_image": a_image},
                }
            continue

        if round_text not in ROUND_NAMES:
            raise QuestionFileError(
                f"Row {line_number}: the Round column says '{cell(row, 'round')}'. "
                "Use 1, 2 or Final."
            )
        round_number = ROUND_NAMES[round_text]

        if not category:
            raise QuestionFileError(f"Row {line_number}: the Category column is empty.")

        value = _parse_value(cell(row, "value"), line_number)
        clue = None
        if question or answer or q_image or a_image:
            clue = {"question": question, "answer": answer, "value": value,
                    "q_image": q_image, "a_image": a_image}

        categories = rounds.setdefault(round_number, {})
        categories.setdefault(category, []).append((value, line_number, clue))

    game = {"rounds": [], "final": final}
    for round_number in sorted(rounds):
        categories = rounds[round_number]
        if len(categories) > CATEGORIES_PER_ROUND:
            raise QuestionFileError(
                f"Round {round_number} has {len(categories)} categories "
                f"({', '.join(categories)}). The board fits {CATEGORIES_PER_ROUND}. "
                "Check for a category name that is spelled two different ways."
            )
        built = []
        for title, entries in categories.items():
            if len(entries) > CLUES_PER_CATEGORY:
                raise QuestionFileError(
                    f"Round {round_number}, category '{title}' has {len(entries)} rows. "
                    f"Each category fits {CLUES_PER_CATEGORY} questions."
                )
            # Rows with a Value are sorted cheapest first; rows without keep their order.
            if all(value is not None for value, _, _ in entries):
                entries = sorted(entries, key=lambda entry: entry[0])
            clues = []
            for position, (value, _, clue) in enumerate(entries):
                if clue is not None and clue["value"] is None:
                    clue["value"] = (position + 1) * 200 * round_number
                clues.append(clue)
            clues += [None] * (CLUES_PER_CATEGORY - len(clues))
            built.append({"title": title, "clues": clues})
        game["rounds"].append({"multiplier": round_number, "categories": built})
    return game


def _parse_value(text, line_number):
    text = text.replace("$", "").replace(",", "").strip()
    if not text:
        return None
    try:
        return int(float(text))
    except ValueError:
        raise QuestionFileError(
            f"Row {line_number}: the Value column says '{text}'. Use a number like 200."
        ) from None


def _image_path(name, folder):
    if not name:
        return None
    return os.path.join(folder, IMAGE_FOLDER, name)


# --------------------------------------------------------------------------
# Original questions.json files
# --------------------------------------------------------------------------

def _load_json(path, folder):
    try:
        with open(path, "r", encoding="utf-8") as file:
            data = json.load(file)
    except json.JSONDecodeError as error:
        raise QuestionFileError(
            f"{path} has a typo on line {error.lineno} (usually a missing comma, "
            "quote or bracket). Tip: questions.csv is much easier to edit."
        ) from None

    titles = list(data.keys())
    final = None
    if titles and len(titles) > CATEGORIES_PER_ROUND or (titles and "final" in titles[-1].lower()):
        final_title = titles.pop()
        final_clue = _json_clue(data[final_title], folder, "FJ", 0)
        if final_clue is not None:
            final = {"category": final_title, "clue": final_clue}

    categories = []
    for column, title in enumerate(titles[:CATEGORIES_PER_ROUND]):
        clues = []
        for row, entry in enumerate(data[title][:CLUES_PER_CATEGORY]):
            # Old image naming: images/11Q.png = category 1, question 1, Question side
            clues.append(_json_clue(entry, folder, f"{column + 1}{row + 1}", (row + 1) * 200))
        clues += [None] * (CLUES_PER_CATEGORY - len(clues))
        categories.append({"title": title, "clues": clues})

    rounds = [{"multiplier": 1, "categories": categories}] if categories else []
    return {"rounds": rounds, "final": final}


def _json_clue(entry, folder, image_prefix, value):
    (q_has_image, question), (a_has_image, answer) = entry
    q_image = os.path.join(folder, IMAGE_FOLDER, image_prefix + "Q.png") if q_has_image else None
    a_image = os.path.join(folder, IMAGE_FOLDER, image_prefix + "A.png") if a_has_image else None
    if not (question or answer or q_image or a_image):
        return None
    return {"question": question, "answer": answer, "value": value,
            "q_image": q_image, "a_image": a_image}


if __name__ == "__main__":
    # Run "python question_loader.py" to check a question file for mistakes.
    import sys

    try:
        loaded = load_questions(sys.argv[1] if len(sys.argv) > 1 else None)
    except QuestionFileError as problem:
        print("PROBLEM:", problem)
        sys.exit(1)
    for game_round in loaded["rounds"]:
        print(f"Round {game_round['multiplier']}:")
        for category in game_round["categories"]:
            filled = sum(clue is not None for clue in category["clues"])
            print(f"   {category['title']!r}: {filled} of {CLUES_PER_CATEGORY} questions filled in")
    print("Final Jeopardy:", "yes" if loaded["final"] else "none")
    print("Question file looks good.")
