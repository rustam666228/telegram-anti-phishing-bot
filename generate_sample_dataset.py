import csv
import os

file_path = "phishing_dataset.csv"

# Примеры ссылок и метки
data = [
    # Фишинговые
    ["http://paypal-login-confirm.com", "phishing"],
    ["http://secure-login-appleid.com", "phishing"],
    ["http://verify-banking-login.com", "phishing"],
    ["http://update.webmail-auth-check.com", "phishing"],
    ["http://amazon-account-recovery.xyz", "phishing"],
    # Безопасные
    ["https://www.google.com", "safe"],
    ["https://github.com", "safe"],
    ["https://www.kaspi.kz", "safe"],
    ["https://mail.ru", "safe"],
    ["https://www.python.org", "safe"],
]

# Запись в CSV
if not os.path.exists(file_path):
    with open(file_path, "w", newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["url", "label"])
        for row in data:
            writer.writerow(row)

    print(f"✅ Dataset created: {file_path}")
else:
    print("⚠️ Dataset already exists. Delete it manually to recreate.")
