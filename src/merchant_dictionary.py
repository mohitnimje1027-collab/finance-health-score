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


def match_known_merchant(merchant_name, score_threshold=80):
    dictionary = load_dictionary()
    known_names = list(dictionary.keys())

    result = process.extractOne(merchant_name, known_names, scorer=fuzz.partial_ratio)
    if result is None:
        return None, 0

    best_match, score, _ = result
    if score >= score_threshold:
        return dictionary[best_match], score
    return None, score