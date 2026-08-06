from categorizer import predict_category

test_merchants = [
    "Chaayos",          # unseen — Food, similar pattern to Chai Point
    "Purplle",          # unseen — Shopping, similar pattern to Nykaa/Myntra
    "Ubereats",         # unseen — Food, contains "Uber" pattern (tricky — could confuse with Travel)
    "Ekart Logistics",  # unseen — ambiguous, real-world messy case
    "Random Merchant X" # nonsense — should stay Uncategorized
]

for merchant in test_merchants:
    category, confidence = predict_category(merchant)
    print(f"{merchant:20s} -> {category:15s} (confidence: {confidence:.2f})")