from cleaner import clean_transactions
import pandas as pd
from pathlib import Path
import re
from cleaner import clean_transactions, handle_edge_cases
from categorizer import categorize_transactions
from feature_engineering import compute_monthly_summary, compute_category_breakdown


REQUIRED_ROLES_OPTION_A = ['date', 'description', 'amount']
REQUIRED_ROLES_OPTION_B = ['date', 'description', 'debit', 'credit']

def check_detection_confidence(roles):
    """
    Checks if detected roles are enough to standardize the data.
    Returns (is_confident: bool, missing: list of roles still needed)
    """
    has_option_a = all(r in roles for r in REQUIRED_ROLES_OPTION_A)
    has_option_b = all(r in roles for r in REQUIRED_ROLES_OPTION_B)

    if has_option_a or has_option_b:
        return True, []
    
    missing = [r for r in ['date', 'description'] if r not in roles]
    if 'amount' not in roles and not ('debit' in roles and 'credit' in roles):
        missing.append('amount (or debit/credit)')
    
    return False, missing

def clean_amount_column(series):
    """Strips currency symbols, commas, and spaces before numeric conversion."""
    return (
        series.astype(str)
        .str.replace('₹', '', regex=False)
        .str.replace(',', '', regex=False)
        .str.replace(' ', '', regex=False)
        .replace('', pd.NA)
    )


def standardize_transactions(df, roles, manual_overrides=None):
    """
    Same as before, but now accepts manual_overrides — a dict like
    {'date': 'Some Column Name', 'amount': 'Another Column'}
    to patch in columns the auto-detector missed.
    """
    if manual_overrides:
        roles = {**roles, **manual_overrides}

    is_confident, missing = check_detection_confidence(roles)
    if not is_confident:
        raise ValueError(
            f"Could not confidently detect columns for: {missing}. "
            f"Please provide manual_overrides, e.g. manual_overrides={{'date': 'YourColumnName'}}"
        )

    clean = pd.DataFrame()
    clean['date'] = pd.to_datetime(df[roles['date']], dayfirst=True, errors='coerce')
    clean['description'] = df[roles['description']].astype(str).str.strip()

    if 'debit' in roles and 'credit' in roles:
        debit = pd.to_numeric(clean_amount_column(df[roles['debit']]), errors='coerce').fillna(0)
        credit = pd.to_numeric(clean_amount_column(df[roles['credit']]), errors='coerce').fillna(0)
        clean['amount'] = credit - debit
    else:
        clean['amount'] = pd.to_numeric(clean_amount_column(df[roles['amount']]), errors='coerce')

    clean = clean.dropna(subset=['date', 'amount']).reset_index(drop=True)
    return clean

def detect_column_roles(df):
    """
    Guesses which column is date, description, debit, credit, or a single amount column.
    Returns a dict like {'date': 'Txn Date', 'description': 'Narration', ...}
    """
    roles = {}
    
    date_keywords = ['date', 'txn date', 'value date', 'transaction date']
    desc_keywords = ['narration', 'description', 'particulars', 'details', 'remarks']
    debit_keywords = ['debit', 'withdrawal', 'withdrawl', 'dr']
    credit_keywords = ['credit', 'deposit', 'cr']
    amount_keywords = ['amount', 'amt', 'value']

    for col in df.columns:
        col_lower = col.strip().lower()

        if roles.get('date') is None and any(k in col_lower for k in date_keywords):
            roles['date'] = col
        elif roles.get('description') is None and any(k in col_lower for k in desc_keywords):
            roles['description'] = col
        elif any(k in col_lower for k in debit_keywords):
            roles['debit'] = col
        elif any(k in col_lower for k in credit_keywords):
            roles['credit'] = col
        elif roles.get('amount') is None and any(k in col_lower for k in amount_keywords):
            roles['amount'] = col

    return roles


'''def standardize_transactions(df, roles):
    """
    Converts the raw dataframe into a clean standard format:
    columns = ['date', 'description', 'amount']
    amount is signed: positive = money in, negative = money out
    """
    clean = pd.DataFrame()
    
    clean['date'] = pd.to_datetime(df[roles['date']], dayfirst=True, errors='coerce')
    clean['description'] = df[roles['description']].astype(str).str.strip()

    if 'debit' in roles and 'credit' in roles:
        debit = pd.to_numeric(df[roles['debit']], errors='coerce').fillna(0)
        credit = pd.to_numeric(df[roles['credit']], errors='coerce').fillna(0)
        clean['amount'] = credit - debit
    elif 'amount' in roles:
        clean['amount'] = pd.to_numeric(df[roles['amount']], errors='coerce')
    else:
        raise ValueError("Could not detect amount columns. Manual column mapping needed.")

    clean = clean.dropna(subset=['date', 'amount']).reset_index(drop=True)
    return clean'''

def load_transaction_file(filepath):
    filepath = str(filepath)
    if filepath.endswith('.csv'):
        df = pd.read_csv(filepath)
    elif filepath.endswith(('.xlsx', '.xls')):
        df = pd.read_excel(filepath)
    elif filepath.endswith('.pdf'):
        df = load_pdf_statement(filepath)
    else:
        raise ValueError("Unsupported file type. Please upload a CSV, Excel, or PDF file.")
    
    print(f"Loaded {len(df)} rows and {len(df.columns)} columns.")
    print("Columns found:", list(df.columns))
    return df

import pdfplumber

def load_pdf_statement(filepath):
    """
    Extracts the transaction table from a PDF bank statement.
    Returns a pandas DataFrame with the raw extracted columns.
    """
    all_rows = []
    headers = None

    with pdfplumber.open(filepath) as pdf:
        for page in pdf.pages:
            table = page.extract_table()
            if table:
                if headers is None:
                    headers = table[0]
                    all_rows.extend(table[1:])
                else:
                    all_rows.extend(table)

    if headers is None:
        raise ValueError("No table found in PDF. This statement format may not be supported yet.")

    df = pd.DataFrame(all_rows, columns=headers)
    print(f"Extracted {len(df)} rows from PDF.")
    print("Columns found:", list(df.columns))
    return df

def process_statement(filepath, manual_overrides=None):
    df = load_transaction_file(filepath)
    roles = detect_column_roles(df)

    is_confident, missing = check_detection_confidence({**roles, **(manual_overrides or {})})
    if not is_confident:
        raise ValueError(f"Low confidence in detected columns. Missing: {missing}")

    df = standardize_transactions(df, roles, manual_overrides)
    df = clean_transactions(df)
    df = handle_edge_cases(df)
    df = categorize_transactions(df)

    needs_review = df[df['category'] == 'Uncategorized']
    if len(needs_review) > 0:
        print(f"\n{len(needs_review)} transaction(s) need manual review.")

    print(f"Pipeline complete: {len(df)} clean, categorized transactions ready.")
    return df, needs_review

if __name__ == "__main__":
    from feature_engineering import (
        compute_monthly_summary,
        compute_category_breakdown,
        compute_behavioral_features,
        detect_anomalies
    )
    from health_score import compute_health_score

    project_root = Path(__file__).resolve().parent.parent
    csv_path = project_root / "data" / "sample_transactions.csv"

    final_df, review_df = process_statement(csv_path)
    print(final_df)
    if len(review_df) > 0:
        print("\nNeeds manual review:")
        print(review_df[['date', 'description', 'merchant']])

    print("\nMonthly summary:")
    monthly_summary = compute_monthly_summary(final_df)
    print(monthly_summary)

    print("\nCategory breakdown:")
    print(compute_category_breakdown(final_df))

    print("\nBehavioral features:")
    behavioral = compute_behavioral_features(final_df)
    print(behavioral)

    print("\nAnomalies detected:")
    print(detect_anomalies(final_df))

    print("\nHealth Score:")
    score = compute_health_score(monthly_summary, behavioral)
    print(score)