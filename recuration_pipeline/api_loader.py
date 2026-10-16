import requests


BASE_URL = "https://api.biomarkerkb.org"


def load_record_from_api(biomarker_id):
    """
    Load one BiomarkerKB record from the API
    using its biomarker ID.
    """

    url = f"{BASE_URL}/biomarker/detail/{biomarker_id}"

    try:
        response = requests.get(url, timeout=30)

        response.raise_for_status()

        return response.json()

    except requests.exceptions.RequestException as error:
        print("API request failed:")
        print(error)
        return None

    except ValueError:
        print("API returned an invalid JSON response.")
        return None



if __name__ == "__main__":

    # One of our known records
    biomarker_id = "AN6284-1"

    print("====================================")
    print("BIOMARKERKB API LOADER")
    print("====================================")

    print("\nRequesting:", biomarker_id)

    record = load_record_from_api(biomarker_id)

    if record is not None:

        print("\nRecord retrieved successfully.")

        print("\nAPI response:")
        print(record)

    else:

        print("\nRecord could not be retrieved.")