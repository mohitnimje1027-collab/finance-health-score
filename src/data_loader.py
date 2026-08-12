from cleaner import clean_transactions
import pandas as pd
from pathlib import Path
import re
from cleaner import clean_transactions, handle_edge_cases
from categorizer import categorize_transactions
from feature_engineering import compute_monthly_summary, compute_category_breakdown
from feature_engineering import prepare_forecast_data
from forecaster import forecast_savings, assess_overspending_risk
import io
import msoffcrypto

class PDFPasswordRequired(Exception):
    """Raised when a PDF needs a password to open, or the given password was wrong."""
    pass


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

def load_excel_statement(filepath, password=None):
    try:
        with open(filepath, 'rb') as f:
            office_file = msoffcrypto.OfficeFile(f)
            if office_file.is_encrypted():
                if password is None:
                    raise PDFPasswordRequired("This Excel file is password protected. Please provide the password.")
                decrypted = io.BytesIO()
                try:
                    office_file.load_key(password=password)
                    office_file.decrypt(decrypted)
                except Exception:
                    raise PDFPasswordRequired("Incorrect password for this Excel file.")
                decrypted.seek(0)
                df_raw = pd.read_excel(decrypted, header=None)
            else:
                f.seek(0)
                df_raw = pd.read_excel(f, header=None)
    except PDFPasswordRequired:
        raise
    except Exception:
        tables = pd.read_html(filepath)
        if not tables:
            raise ValueError("Could not read this file as Excel or as an HTML table.")
        return tables[0]

    header_row = find_header_row(df_raw)
    if header_row is None:
        # No detectable header block — assume it's already clean, row 0 is the header
        df_raw.columns = df_raw.iloc[0]
        return df_raw[1:].reset_index(drop=True)

    df_raw.columns = df_raw.iloc[header_row]
    df_clean = df_raw[header_row + 1:].reset_index(drop=True)
    return df_clean

def load_transaction_file(filepath, password=None):
    filepath = str(filepath)
    if filepath.endswith('.csv'):
        df = pd.read_csv(filepath)
    elif filepath.endswith(('.xlsx', '.xls')):
        df = load_excel_statement(filepath, password=password)
    elif filepath.endswith('.pdf'):
        df = load_pdf_statement(filepath, password=password)
    else:
        raise ValueError("Unsupported file type. Please upload a CSV, Excel, or PDF file.")

    print(f"Loaded {len(df)} rows and {len(df.columns)} columns.")
    print("Columns found:", list(df.columns))
    return df

import pdfplumber

def load_pdf_statement(filepath, password=None):
    """
    Extracts the transaction table from a PDF bank statement.
    Supports password-protected PDFs — pass password=None first;
    if the PDF is locked, this raises PDFPasswordRequired so the
    caller (the app) can prompt the user and retry.
    """
    all_rows = []
    headers = None

    try:
        with pdfplumber.open(filepath, password=password) as pdf:
            for page in pdf.pages:
                table = page.extract_table()
                if table:
                    if headers is None:
                        headers = table[0]
                        all_rows.extend(table[1:])
                    else:
                        all_rows.extend(table)
    except Exception as e:
        err_text = str(e).lower()
        if "password" in err_text or "encrypt" in err_text or "decrypt" in err_text:
            if password is None:
                raise PDFPasswordRequired("This PDF is password protected. Please provide the password.")
            else:
                raise PDFPasswordRequired("Incorrect password for this PDF.")
        raise

    if headers is None:
        raise ValueError("No table found in PDF. This statement format may not be supported yet.")

    df = pd.DataFrame(all_rows, columns=headers)
    print(f"Extracted {len(df)} rows from PDF.")
    print("Columns found:", list(df.columns))
    return df

def process_statement(filepath, manual_overrides=None, password=None):
    df = load_transaction_file(filepath, password=password)
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

def find_header_row(df_raw, keyword_sets=None):
    """
    Scans a raw (headerless) dataframe to find which row contains the
    real column headers, by looking for known keywords like 'Date',
    'Debit', 'Credit', 'Narration', 'Details', etc.
    Returns the row index, or None if not found.
    """
    if keyword_sets is None:
        keyword_sets = ['date', 'debit', 'credit', 'narration', 'description',
                         'particulars', 'details', 'withdrawal', 'deposit', 'balance']

    for idx, row in df_raw.iterrows():
        row_text = ' '.join(str(cell).lower() for cell in row if pd.notna(cell))
        matches = sum(1 for kw in keyword_sets if kw in row_text)
        if matches >= 3:  # require at least 3 keyword matches to be confident it's a real header row
            return idx
    return None

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

    print("\nSavings Forecast (next 6 months):")
    X, y = prepare_forecast_data(monthly_summary)
    forecast = forecast_savings(X, y)
    print(forecast)

    print("\nRisk Assessment:")
    print(assess_overspending_risk(monthly_summary, forecast))