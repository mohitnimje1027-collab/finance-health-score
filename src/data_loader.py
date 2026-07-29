import pandas as pd
from pathlib import Path

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
    # Build a path relative to this script's location, not the current working directory
    project_root = Path(__file__).resolve().parent.parent
    sample_path = project_root / "data" / "sample_transactions.csv"
    
    df = load_transaction_file(sample_path)
    print(df.head())