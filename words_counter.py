# words_counter.py

file_path = "/Users/ngcaditya/PycharmProjects/Prismatic-Engine/text.txt"

with open(file_path, "r", encoding="utf-8") as f:
    text = f.read().strip()

words = text.split()
word_count = len(words)

print(f"Number of words: {word_count}")
