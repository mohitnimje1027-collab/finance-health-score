import pandas as pd
from pathlib import Path
import msoffcrypto
import io

filepath = Path.home() / "Downloads" / "AccountStatement_11082026_154907.xlsx"
password = input("Enter the file's password: ")

with open(filepath, 'rb') as f:
    office_file = msoffcrypto.OfficeFile(f)
    office_file.load_key(password=password)
    decrypted = io.BytesIO()
    office_file.decrypt(decrypted)
    decrypted.seek(0)
    df_raw = pd.read_excel(decrypted, header=None)

pd.set_option('display.max_columns', None)
pd.set_option('display.width', 200)
print(df_raw.head(20))