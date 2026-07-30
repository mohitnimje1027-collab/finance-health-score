import pandas as pd
from pathlib import Path
import re

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
    """
    Reads a transaction file (CSV or Excel) and returns a pandas DataFrame.
    Raises a clear error if the file type isn't supported.
    """
    if str(filepath).endswith('.csv'):
        df = pd.read_csv(filepath)
    elif str(filepath).endswith(('.xlsx', '.xls')):
        df = pd.read_excel(filepath)
    else:
        raise ValueError("Unsupported file type. Please upload a CSV or Excel file.")
    
    print(f"Loaded {len(df)} rows and {len(df.columns)} columns.")
    print("Columns found:", list(df.columns))
    return df


if __name__ == "__main__":
    project_root = Path(__file__).resolve().parent.parent
    sample_path = project_root / "data" / "sample_transactions.csv"
    
    df = load_transaction_file(sample_path)
    roles = detect_column_roles(df)
    print("Detected roles:", roles)
    
    clean_df = standardize_transactions(df, roles)
    print(clean_df)