import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent))

from cleaner import normalize_merchant_name, parse_transaction_narration

test_narrations = [
    "WDL TFR   UPI/DR/220113430287/MEESHO T/YESB/MEESHOONLI/UPI",
    "DEP TFR   UPI/CR/133831126691/ATHARVAH/CNRB/9",
    "WDL TFR   UPI/DR/172316906372/Bhumika /ICIC/8",
    "ATM WDL  SBI ATM INDORE",
    "NEFT-N123456789-JOHN DOE",
]

for n in test_narrations:
    payee, txn_type = parse_transaction_narration(n)
    merchant = normalize_merchant_name(n)
    print(f"{n[:40]:40s} -> type: {txn_type:8s} payee: {str(payee):15s} merchant: {merchant}")

from merchant_dictionary import match_known_merchant

test_merchants = ["Meesho T", "Atharvah", "Bhumika"]
for m in test_merchants:
    category, score = match_known_merchant(m)
    print(f"{m:15s} -> {category} (score: {score})")