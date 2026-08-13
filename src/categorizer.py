import joblib
import pandas as pd
from pathlib import Path
from merchant_dictionary import match_known_merchant

_model = None

def load_model():
    global _model
    if _model is None:
        project_root = Path(__file__).resolve().parent.parent
        model_path = project_root / "src" / "categorizer_model.joblib"
        _model = joblib.load(model_path)
    return _model




from cleaner import parse_transaction_narration

def predict_category(merchant_name, confidence_threshold=0.25, original_description=None):
    dict_category, dict_score = match_known_merchant(merchant_name)
    if dict_category is not None:
        return dict_category, round(dict_score / 100, 2)

    # If this looks like a person-to-person UPI transfer with no merchant match, tag it honestly
    if original_description:
        payee, txn_type = parse_transaction_narration(original_description)
        if txn_type == 'UPI' and payee and len(payee.split()) <= 3:
            return "Personal Transfer", 0.7

    model = load_model()
    probs = model.predict_proba([merchant_name])[0]
    best_idx = probs.argmax()
    category = model.classes_[best_idx]
    confidence = probs[best_idx]

    if confidence < confidence_threshold:
        return "Uncategorized", confidence
    return category, confidence


def categorize_transactions(df):
    categories = []
    confidences = []

    for _, row in df.iterrows():
        category, confidence = predict_category(row['merchant'], original_description=row['description'])

        if category == "Personal Transfer":
            category = classify_personal_transfer(row['merchant'], row['amount'], df)
            confidence = 0.7

        categories.append(category)
        confidences.append(confidence)

    df['category'] = categories
    df['category_confidence'] = confidences
    return df

def classify_personal_transfer(merchant_name, amount, all_transactions_df):
    """
    Refines generic personal transfers using direction and recurrence
    instead of a single catch-all label.
    """
    occurrences = all_transactions_df[all_transactions_df['merchant'] == merchant_name]

    if len(occurrences) >= 3:
        return "Recurring Transfer"

    if amount > 0:
        return "Personal Transfer (Received)"
    else:
        return "Personal Transfer (Sent)"