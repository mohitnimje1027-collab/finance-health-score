import joblib
import pandas as pd
from pathlib import Path

_model = None

def load_model():
    global _model
    if _model is None:
        project_root = Path(__file__).resolve().parent.parent
        model_path = project_root / "src" / "categorizer_model.joblib"
        _model = joblib.load(model_path)
    return _model


def predict_category(merchant_name, confidence_threshold=0.35):
    """
    Predicts a category for a given merchant name.
    Returns (category, confidence). If confidence is below threshold,
    category is returned as 'Uncategorized' so it can be flagged for manual review.
    """
    model = load_model()
    probs = model.predict_proba([merchant_name])[0]
    best_idx = probs.argmax()
    category = model.classes_[best_idx]
    confidence = probs[best_idx]

    if confidence < confidence_threshold:
        return "Uncategorized", confidence
    return category, confidence


def categorize_transactions(df):
    """
    Applies predict_category to every row in a transactions dataframe
    (expects a 'merchant' column). Adds 'category' and 'category_confidence' columns.
    """
    results = df['merchant'].apply(lambda m: predict_category(m))
    df['category'] = results.apply(lambda x: x[0])
    df['category_confidence'] = results.apply(lambda x: round(x[1], 2))
    return df