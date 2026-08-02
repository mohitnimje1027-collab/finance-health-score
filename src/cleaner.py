import re
import pandas as pd

def remove_duplicate_transactions(df):
    """
    Removes exact duplicate transactions (same date, description, amount).
    Real bank exports sometimes double-list a transaction, especially
    around statement page breaks.
    """
    before = len(df)
    df = df.drop_duplicates(subset=['date', 'description', 'amount']).reset_index(drop=True)
    after = len(df)
    if before != after:
        print(f"Removed {before - after} duplicate transaction(s).")
    return df


def normalize_merchant_name(description):
    text = str(description).upper()
    
    # Income-type entries aren't merchants — label them directly
    income_keywords = ['SALARY', 'INTEREST CREDIT', 'REFUND', 'CASHBACK', 'DIVIDEND']
    for kw in income_keywords:
        if kw in text:
            return kw.title()

    # Remove common prefixes banks add (UPI, NEFT, IMPS, POS, etc.)
    text = re.sub(r'^(UPI|NEFT|IMPS|POS|ECS|ACH)[\s\-/]*', '', text)

    # Remove anything after a *, /, or @ (transaction IDs, UPI handles, locations)
    text = re.split(r'[\*/@]', text)[0]

    # Remove trailing/embedded long digit sequences (reference numbers)
    text = re.sub(r'\d{4,}', '', text)

    # Remove common noise words
    noise_words = ['SUBSCRIPTION', 'ONLINE', 'PAY', 'PAYMENT', 'ORDER', 'BANGALORE',
                   'MUMBAI', 'DELHI', 'PUNE', 'HYDERABAD', 'CORP', 'LTD', 'PVT']
    for word in noise_words:
        text = text.replace(word, '')

    # Strip anything that isn't a letter or space (leftover symbols/punctuation)
    text = re.sub(r'[^A-Z\s]', ' ', text)

    # Collapse extra spaces and trim
    text = re.sub(r'\s+', ' ', text).strip()

    return text.title() if text else "Unknown"

def clean_transactions(df):
    """
    Full cleaning pipeline: removes duplicates, adds a normalized
    'merchant' column derived from the raw description.
    """
    df = remove_duplicate_transactions(df)
    df['merchant'] = df['description'].apply(normalize_merchant_name)
    return df