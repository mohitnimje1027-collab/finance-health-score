import pandas as pd
from pathlib import Path
from rapidfuzz import process, fuzz

_dictionary = None

def load_dictionary():
    global _dictionary
    if _dictionary is None:
        project_root = Path(__file__).resolve().parent.parent
        dict_path = project_root / "data" / "merchant_dictionary.csv"
        df = pd.read_csv(dict_path)
        _dictionary = dict(zip(df['merchant'], df['category']))
    return _dictionary


def match_known_merchant(merchant_name, score_threshold=85):
    """
    Tries to match merchant_name against the curated dictionary using fuzzy matching.
    Returns (category, score) if a confident match is found, else (None, 0).
    score_threshold=85 means "must be at least 85% similar" (out of 100) to count as a match.
    """
    dictionary = load_dictionary()
    known_names = list(dictionary.keys())

    result = process.extractOne(merchant_name, known_names, scorer=fuzz.WRatio)
    if result is None:
        return None, 0

    best_match, score, _ = result
    if score >= score_threshold:
        return dictionary[best_match], score
    return None, score