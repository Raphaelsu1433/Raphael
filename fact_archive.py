import json
import os

FILE_NAME = "facts.json"


def load_facts():
    """Load facts from a local JSON file."""
    if not os.path.exists(FILE_NAME):
        return []

    try:
        with open(FILE_NAME, "r", encoding="utf-8") as file:
            return json.load(file)
    except (json.JSONDecodeError, FileNotFoundError):
        return []


def save_facts(facts):
    """Save facts to a local JSON file."""
    with open(FILE_NAME, "w", encoding="utf-8") as file:
        json.dump(facts, file, ensure_ascii=False, indent=4)


def fact_exists(facts, new_fact_text):
    """Check whether a fact already exists in the archive."""
    normalized_new_fact = new_fact_text.strip().lower()

    for fact in facts:
        existing_text = fact.get("text", "").strip().lower()
        if existing_text == normalized_new_fact:
            return True

    return False


def add_fact(new_fact_text, source="unknown"):
    """Add a new fact only if it is not already stored."""
    facts = load_facts()

    if fact_exists(facts, new_fact_text):
        print("This fact already exists in the archive.")
        return False

    new_fact = {
        "id": len(facts) + 1,
        "text": new_fact_text,
        "source": source
    }

    facts.append(new_fact)
    save_facts(facts)
    print("New fact added successfully.")
    return True


# Example usage
if __name__ == "__main__":
    sample_fact = "Bananas are berries, but strawberries are not."
    add_fact(sample_fact, source="manual")

    all_facts = load_facts()
    print("\nStored facts:")
    for fact in all_facts:
        print(fact)