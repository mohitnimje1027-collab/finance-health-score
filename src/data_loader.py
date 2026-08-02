from cleaner import clean_transactions
import pandas as pd
from pathlib import Path
import re
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
        debit = pd.to_numeric(df[roles['debit']], errors='coerce').fillna(0)
        credit = pd.to_numeric(df[roles['credit']], errors='coerce').fillna(0)
        clean['amount'] = credit - debit
    else:
        clean['amount'] = pd.to_numeric(df[roles['amount']], errors='coerce')

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


def standardize_transactions(df, roles):
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
    return clean

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

if __name__ == "__main__":
    project_root = Path(__file__).resolve().parent.parent

    print("--- Testing CSV ---")
    csv_path = project_root / "data" / "sample_transactions.csv"
    df_csv = load_transaction_file(csv_path)
    roles_csv = detect_column_roles(df_csv)
    print("Detected roles:", roles_csv)
    clean_df = standardize_transactions(df_csv, roles_csv)
    clean_df = clean_transactions(clean_df)
    print(clean_df)