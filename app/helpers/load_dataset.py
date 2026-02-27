import re
from datasets import load_dataset
import json

dataset = load_dataset(
    "wikimedia/wikipedia",
    "20231101.en",
    split="train",
    streaming=True
)

count = 0
target_size = 1000

# Stronger biography regex patterns
born_pattern = re.compile(r"\(born\s+[^)]+\)")
definition_pattern = re.compile(r"\bis (an?|the)\b")

# Optional: exclude obvious non-humans
non_human_keywords = [
    "film", "album", "song", "company",
    "band", "city", "village", "river",
    "mountain", "organization", "school"
]

with open("people_sample.jsonl", "w", encoding="utf-8") as f:
    for article in dataset:

        text = article.get("text", "")
        title = article.get("title", "")
        url = article.get("url", "")

        if not text or len(text) < 200:
            continue

        # Extract first sentence more safely
        sentences = re.split(r'(?<=[.!?])\s+', text)
        first_sentence = sentences[0] if sentences else ""

        # Apply biography filters
        if born_pattern.search(first_sentence) and \
           definition_pattern.search(first_sentence):

            # Exclude obvious non-human pages
            if any(word in first_sentence.lower() for word in non_human_keywords):
                continue

            json.dump({
                "id": article.get("id"),
                "title": title,
                "url": url,
                "text": text
            }, f, ensure_ascii=False)

            f.write("\n")

            count += 1

            if count >= target_size:
                break

print("Saved:", count)