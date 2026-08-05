from categorizer import predict_category

test_merchants = [
    "Kfc",              # never seen — should still lean Food via pattern
    "Nykaa",            # never seen — Shopping-ish name pattern
    "Airtel Dth",       # variant of Airtel — should catch Bills
    "Big Basket",       # variant of Bigbasket — should catch Groceries
    "Random Merchant X" # totally nonsense — should be low confidence
]

for merchant in test_merchants:
    category, confidence = predict_category(merchant)
    print(f"{merchant:20s} -> {category:15s} (confidence: {confidence:.2f})")