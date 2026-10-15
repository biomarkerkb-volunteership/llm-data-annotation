import pandas as pd


# Path to the BiomarkerKB dataset
DATA_FILE = "biomarkers_top_50.tsv"


def load_records(file_path):
    """
    Load BiomarkerKB records from a TSV file.
    """
    df = pd.read_csv(file_path, sep="\t")
    return df


def get_record(df, biomarker_id):
    """
    Find and return one BiomarkerKB record
    using its biomarker_id.
    """
    record = df[df["biomarker_id"] == biomarker_id]

    if record.empty:
        print(f"Record {biomarker_id} not found.")
        return None

    return record.iloc[0]


if __name__ == "__main__":

    # Step 1: Load all BiomarkerKB records
    records = load_records(DATA_FILE)

    print("BiomarkerKB records loaded successfully.")
    print("Number of records:", len(records))
    print("Number of columns:", len(records.columns))

    # Step 2: Retrieve one specific record
    # This is our Serum Ferritin / COVID-19 case
    record = get_record(records, "AN6284-1")

    # Step 3: Display the record
    if record is not None:
        print("\nSelected record:")
        print(record)