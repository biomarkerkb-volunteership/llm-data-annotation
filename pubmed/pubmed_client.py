import json
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path


# ---------------------------------------------------------------------
# NCBI URLs and settings
# ---------------------------------------------------------------------

EFETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
PMC_ID_URL = "https://www.ncbi.nlm.nih.gov/pmc/utils/idconv/v1.0/"

# Stay below the NCBI request limit when not using an API key
REQUEST_DELAY = 0.4

# Local cache folder
CACHE_DIR = Path(__file__).parent / "cache"
CACHE_DIR.mkdir(exist_ok=True)


# ---------------------------------------------------------------------
# Rate limiting
# ---------------------------------------------------------------------

def rate_limit():
    """Pause between NCBI requests."""
    time.sleep(REQUEST_DELAY)


# ---------------------------------------------------------------------
# Parse BiomarkerKB evidence_source
# ---------------------------------------------------------------------

def parse_pubmed_id(evidence_source):
    """
    Extract a PMID from a BiomarkerKB evidence_source.

    Returns:
        (pmid, error_reason)
    """

    if evidence_source is None or not str(evidence_source).strip():
        return None, "missing_citation"

    evidence_source = str(evidence_source).strip()

    if not evidence_source.lower().startswith("pubmed:"):
        return None, "not_pubmed"

    pmid = evidence_source.split(":", 1)[1].strip()

    if not pmid:
        return None, "missing_pmid"

    if not pmid.isdigit():
        return None, "malformed_pmid"

    return pmid, None


# ---------------------------------------------------------------------
# PubMed → PMC ID
# ---------------------------------------------------------------------

def get_pmc_id(pmid):
    """Return the PMC ID for a PMID if a PMC version exists."""

    params = {
        "ids": str(pmid),
        "format": "json",
    }

    url = PMC_ID_URL + "?" + urllib.parse.urlencode(params)

    rate_limit()

    with urllib.request.urlopen(url, timeout=30) as response:
        data = json.loads(response.read().decode("utf-8"))

    records = data.get("records", [])

    if not records:
        return None

    return records[0].get("pmcid")


# ---------------------------------------------------------------------
# Fetch PMC full text
# ---------------------------------------------------------------------

def fetch_pmc_full_text(pmcid):
    """Fetch full text from PubMed Central."""

    params = {
        "db": "pmc",
        "id": pmcid,
        "retmode": "xml",
    }

    url = EFETCH_URL + "?" + urllib.parse.urlencode(params)

    rate_limit()

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


# ---------------------------------------------------------------------
# Fetch PubMed title + abstract
# ---------------------------------------------------------------------

def fetch_pubmed_record(pmid):
    """Fetch the title and abstract for one PubMed ID."""

    params = {
        "db": "pubmed",
        "id": str(pmid),
        "retmode": "xml",
    }

    url = EFETCH_URL + "?" + urllib.parse.urlencode(params)

    rate_limit()

    with urllib.request.urlopen(url, timeout=30) as response:
        xml_data = response.read()

    root = ET.fromstring(xml_data)

    article = root.find(".//PubmedArticle")

    if article is None:
        raise ValueError(f"No PubMed article found for PMID {pmid}")

    # Get title
    title_element = article.find(".//ArticleTitle")

    title = (
        "".join(title_element.itertext()).strip()
        if title_element is not None
        else ""
    )

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


# ---------------------------------------------------------------------
# Cache functions
# ---------------------------------------------------------------------

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
        json.dump(
            paper,
            f,
            indent=2,
            ensure_ascii=False
        )

    return cache_file


# ---------------------------------------------------------------------
# Main reusable retrieval function
# ---------------------------------------------------------------------

def retrieve_paper(evidence_source):
    """
    Retrieve and cache a paper from a BiomarkerKB evidence_source.

    Returns either:
        resolved paper information
    or:
        unresolved status with a reason
    """

    pmid, error = parse_pubmed_id(evidence_source)

    # Citation itself is invalid
    if error:
        return {
            "status": "unresolved",
            "reason": error,
            "evidence_source": evidence_source,
        }

    # Check cache first
    cached = load_from_cache(pmid)

    if cached:
        cached["status"] = "resolved"
        cached["source"] = "cache"
        return cached

    # Otherwise retrieve from NCBI
    try:
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

        save_to_cache(paper)

        paper["status"] = "resolved"
        paper["source"] = "ncbi"

        return paper

    except Exception as e:
        return {
            "status": "unresolved",
            "reason": f"retrieval_error: {e}",
            "evidence_source": evidence_source,
            "pmid": pmid,
        }


# ---------------------------------------------------------------------
# Single-paper test
# ---------------------------------------------------------------------

if __name__ == "__main__":

    evidence_source = "PubMed:32425269"

    result = retrieve_paper(evidence_source)

    print("Evidence source:", evidence_source)
    print("Status:", result["status"])

    if result["status"] == "resolved":

        print("PMID:", result["pmid"])
        print("Source:", result["source"])
        print("Title:", result["title"])
        print("PMC ID:", result["pmcid"])

        if result["full_text"]:
            print(
                "Full text characters:",
                len(result["full_text"])
            )
        else:
            print("Full text: Not available")

    else:
        print("Reason:", result["reason"])