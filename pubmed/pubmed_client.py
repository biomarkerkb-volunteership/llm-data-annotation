import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import json
from pathlib import Path


EFETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
PMC_ID_URL = "https://www.ncbi.nlm.nih.gov/pmc/utils/idconv/v1.0/"

CACHE_DIR = Path(__file__).parent / "cache"
CACHE_DIR.mkdir(exist_ok=True)

def parse_pubmed_id(evidence_source):
    """Extract PMID from a BiomarkerKB evidence_source."""

    if not evidence_source:
        return None

    evidence_source = str(evidence_source).strip()

    if not evidence_source.lower().startswith("pubmed:"):
        return None

    pmid = evidence_source.split(":", 1)[1].strip()

    if not pmid.isdigit():
        return None

    return pmid

def get_pmc_id(pmid):
    """Return the PMC ID for a PMID if an open-access PMC version exists."""

    params = {
        "ids": str(pmid),
        "format": "json",
    }

    url = PMC_ID_URL + "?" + urllib.parse.urlencode(params)

    with urllib.request.urlopen(url, timeout=30) as response:
        import json
        data = json.loads(response.read().decode("utf-8"))

    records = data.get("records", [])

    if not records:
        return None

    return records[0].get("pmcid")



def fetch_pmc_full_text(pmcid):
    """Fetch full text from PubMed Central."""

    params = {
        "db": "pmc",
        "id": pmcid,
        "retmode": "xml",
    }

    url = EFETCH_URL + "?" + urllib.parse.urlencode(params)

    with urllib.request.urlopen(url, timeout=30) as response:
        xml_data = response.read()

    root = ET.fromstring(xml_data)

    body = root.find(".//body")

    if body is None:
        return None

    paragraphs = []

    for paragraph in body.findall(".//p"):
        text = "".join(paragraph.itertext()).strip()

        if text:
            paragraphs.append(text)

    return "\n\n".join(paragraphs)

def fetch_pubmed_record(pmid):
    """Fetch the title and abstract for one PubMed ID."""

    params = {
        "db": "pubmed",
        "id": str(pmid),
        "retmode": "xml",
    }

    url = EFETCH_URL + "?" + urllib.parse.urlencode(params)

    with urllib.request.urlopen(url, timeout=30) as response:
        xml_data = response.read()

    root = ET.fromstring(xml_data)

    article = root.find(".//PubmedArticle")

    if article is None:
        raise ValueError(f"No PubMed article found for PMID {pmid}")

    # Get title
    title_element = article.find(".//ArticleTitle")
    title = "".join(title_element.itertext()).strip() if title_element is not None else ""

    # Get abstract
    abstract_parts = []

    for abstract_element in article.findall(".//Abstract/AbstractText"):
        text = "".join(abstract_element.itertext()).strip()

        if text:
            abstract_parts.append(text)

    abstract = "\n".join(abstract_parts)

    return {
        "pmid": str(pmid),
        "title": title,
        "abstract": abstract,
    }

def load_from_cache(pmid):
    """Load a previously retrieved paper from disk."""

    cache_file = CACHE_DIR / f"{pmid}.json"

    if not cache_file.exists():
        return None

    with open(cache_file, "r", encoding="utf-8") as f:
        return json.load(f)


def save_to_cache(paper):
    """Save a retrieved paper to disk."""

    cache_file = CACHE_DIR / f"{paper['pmid']}.json"

    with open(cache_file, "w", encoding="utf-8") as f:
        json.dump(paper, f, indent=2, ensure_ascii=False)

    return cache_file

if __name__ == "__main__":
    evidence_source = "PubMed:34816550"

    pmid = parse_pubmed_id(evidence_source)

    print("Evidence source:", evidence_source)
    print("Extracted PMID:", pmid)

    if pmid:
        paper = load_from_cache(pmid)

        if paper:
            print("\nLoaded from cache.")
        else:
            print("\nNot cached. Retrieving from NCBI...")

            record = fetch_pubmed_record(pmid)
            pmcid = get_pmc_id(pmid)

            full_text = None

            if pmcid:
                full_text = fetch_pmc_full_text(pmcid)

            paper = {
                "pmid": pmid,
                "pmcid": pmcid,
                "title": record["title"],
                "abstract": record["abstract"],
                "full_text": full_text,
            }

            cache_file = save_to_cache(paper)
            print("Saved to:", cache_file)

        print("\nTITLE:")
        print(paper["title"])

        print("\nPMC ID:", paper["pmcid"])

        if paper["full_text"]:
            print("Full text characters:", len(paper["full_text"]))
        else:
            print("Full text: Not available")