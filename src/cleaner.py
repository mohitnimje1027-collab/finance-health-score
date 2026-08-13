import re
import pandas as pd

def parse_transaction_narration(description):
    """
    Tries multiple known Indian bank narration formats and extracts:
    - payee/merchant name fragment (if identifiable)
    - transaction_type tag (UPI, NEFT, RTGS, IMPS, POS, ATM, CHEQUE, OTHER)
    Returns (payee_name_or_None, transaction_type)
    """
    text = str(description).upper().strip()

    # UPI: UPI/DR|CR/refno/PAYEE/BANK/handle...
    match = re.search(r'UPI/(?:DR|CR)/\d+/([A-Za-z0-9 .]+?)/', text)
    if match:
        return match.group(1).strip(), 'UPI'

    # NEFT: NEFT-refno-PAYEE or NEFT/refno/PAYEE
    match = re.search(r'NEFT[\-/]\w+[\-/]([A-Za-z0-9 .]+)', text)
    if match:
        return match.group(1).strip(), 'NEFT'

    # RTGS: similar to NEFT
    match = re.search(r'RTGS[\-/]\w+[\-/]([A-Za-z0-9 .]+)', text)
    if match:
        return match.group(1).strip(), 'RTGS'

    # IMPS: IMPS/refno/PAYEE or IMPS-refno-PAYEE
    match = re.search(r'IMPS[\-/]\w+[\-/]([A-Za-z0-9 .]+)', text)
    if match:
        return match.group(1).strip(), 'IMPS'

    # POS / Card swipe: POS <merchant name> or POS/merchant
    match = re.search(r'POS[\s/]+([A-Za-z0-9 .]+)', text)
    if match:
        return match.group(1).strip(), 'POS'

    # ATM withdrawal: no merchant, it's cash
    if re.search(r'\bATM\b|\bCASH WDL\b|\bCSH WDL\b', text):
        return None, 'ATM'

    # Cheque: no merchant identifiable directly
    if re.search(r'\bCHQ\b|\bCHEQUE\b', text):
        return None, 'CHEQUE'

    # Nothing matched
    return None, 'OTHER'

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
    payee, txn_type = parse_transaction_narration(description)

    # Cash and cheque transactions have no merchant — handle explicitly, don't guess
    if txn_type == 'ATM':
        return 'ATM Withdrawal'
    if txn_type == 'CHEQUE':
        return 'Cheque Transaction'

    text = payee if payee else str(description).upper()

    income_keywords = ['SALARY', 'INTEREST CREDIT', 'REFUND', 'CASHBACK', 'DIVIDEND']
    for kw in income_keywords:
        if kw in text:
            return kw.title()

    text = re.sub(r'^(UPI|NEFT|IMPS|POS|ECS|ACH|RTGS)[\s\-/]*', '', text)
    text = re.split(r'[\*/@]', text)[0]
    text = re.sub(r'\d{4,}', '', text)

    noise_words = ['SUBSCRIPTION', 'ONLINE', 'PAY', 'PAYMENT', 'ORDER', 'BANGALORE',
                   'MUMBAI', 'DELHI', 'PUNE', 'HYDERABAD', 'CORP', 'LTD', 'PVT', 'TFR', 'DEP', 'WDL']
    for word in noise_words:
        text = text.replace(word, '')

    text = re.sub(r'[^A-Z\s]', ' ', text)
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

def handle_edge_cases(df):
    """
    Cleans up remaining real-world messiness:
    - Blank/NaN descriptions -> labeled as 'Unknown'
    - Zero-amount transactions -> removed (not real spend/income)
    """
    df['description'] = df['description'].replace('', pd.NA)
    df['description'] = df['description'].fillna('Unknown Transaction')

    before = len(df)
    df = df[df['amount'] != 0].reset_index(drop=True)
    removed = before - len(df)
    if removed:
        print(f"Removed {removed} zero-amount transaction(s).")

    return df