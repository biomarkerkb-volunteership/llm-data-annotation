from pathlib import Path


VOCAB_DIR = Path("controlled_vocab")


def load_vocabulary(file_path):
    """
    Load a controlled vocabulary text file.

    Each non-empty line becomes one allowed term.
    """
    with open(file_path, "r", encoding="utf-8") as file:
        terms = {
            line.strip()
            for line in file
            if line.strip()
        }

    return terms


if __name__ == "__main__":

    # Load the three BiomarkerKB controlled vocabularies
    entity_types = load_vocabulary(
        VOCAB_DIR / "entity_type.txt"
    )

    change_types = load_vocabulary(
        VOCAB_DIR / "change_type.txt"
    )

    aspect_types = load_vocabulary(
        VOCAB_DIR / "aspect_type.txt"
    )

    print("Controlled vocabularies loaded successfully.")

    print("\nEntity types:")
    print(entity_types)

    print("\nChange types:")
    print(change_types)

    print("\nAspect types:")
    print(aspect_types)