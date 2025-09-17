from werkzeug.security import check_password_hash

# Your scrypt hash
hash = "scrypt:32768:8:1$F8M0tNI4ZHwDczrG$6a56f5ed17bf6b4ee7f8d788eb12df50f88665066d5d8d6277326fbfb41453ade2b1ff25ffa75bade0de17d68120199281eb05d7802044fa1b261c5da1c20807"

# All password guesses that start with "barath"
prefix = "Barath"
suffixes = [
    # "", "1", "123", "1234", "12345", "@2023", "@2024", "2025", "!", "01", "barath",
    # "123!", "!123", "@",
    "15092005","321","860868"
]

# Try each password
for suffix in suffixes:
    guess = prefix + suffix
    if check_password_hash(hash, guess):
        print(f"[+] Password found: {guess}")
        break
else:
    print("[-] Password not found in guess list.")
