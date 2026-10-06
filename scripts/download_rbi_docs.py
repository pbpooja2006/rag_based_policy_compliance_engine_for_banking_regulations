from __future__ import annotations

import hashlib
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import fitz
import requests


USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36"
BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = BASE_DIR / "data" / "raw"
MANIFEST_PATH = RAW_DIR / "sources_manifest.json"


SOURCES = [
    {
        "title": "Master Direction - Know Your Customer (KYC) Direction, 2016",
        "source_url": "https://rbidocs.rbi.org.in/rdocs/notification/PDFs/MD18KYCF6E92C82E1E1419D87323E3869BC9F13.PDF",
        "referer": "https://www.rbi.org.in/Scripts/BS_ViewMasDirections.aspx?id=11566",
        "category": "KYC & Customer Due Diligence",
    },
    {
        "title": "Guidelines on Digital Lending",
        "source_url": "https://rbidocs.rbi.org.in/rdocs/notification/PDFs/GUIDELINESDIGITALLENDINGD5C35A71D8124A0E92AEB940A7D25BB3.PDF",
        "referer": "https://www.rbi.org.in/Scripts/NotificationUser.aspx?Id=12382&Mode=0",
        "category": "Digital Lending & FinTech",
    },
    {
        "title": "Annex-II - Illustrative Format of Key Fact Statement",
        "source_url": "https://rbidocs.rbi.org.in/rdocs/content/pdfs/DigitalLending02092022_A2.pdf",
        "referer": "https://www.rbi.org.in/Scripts/NotificationUser.aspx?Id=12382&Mode=0",
        "category": "Digital Lending & FinTech",
    },
    {
        "title": "Customer Protection – Limiting Liability of Customers in Unauthorised Electronic Banking Transactions",
        "source_url": "https://rbidocs.rbi.org.in/rdocs/notification/PDFs/NOTI15D620D2C4D2CA4A33AABC928CA6204B19.PDF",
        "referer": "https://www.rbi.org.in/Scripts/NotificationUser.aspx?Id=11040&Mode=0",
        "category": "Customer Protection & Grievance",
    },
    {
        "title": "Reserve Bank of India (All India Financial Institutions – Fraud Risk Management) Directions, 2026",
        "source_url": "https://rbidocs.rbi.org.in/rdocs/notification/PDFs/457MDAC203EBBDF604A81958E02BB2C4BB1B1.PDF",
        "referer": "https://www.rbi.org.in/scripts/NotificationUser.aspx?Mode=0&Id=13596",
        "category": "Fraud Risk Management",
    },
    {
        "title": "Reserve Bank of India (Commercial Banks - Responsible Business Conduct) Fourth Amendment Directions, 2026",
        "source_url": "https://rbidocs.rbi.org.in/rdocs/notification/PDFs/NT2231ED57C3AA5F1493BA85E48591D755A18.PDF",
        "referer": "https://www.rbi.org.in/scripts/NotificationUser.aspx?Mode=0&Id=13665",
        "category": "Customer Protection & Grievance",
    },
]


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_manifest() -> list[dict]:
    if not MANIFEST_PATH.exists():
        return []
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def save_manifest(items: list[dict]) -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(json.dumps(items, indent=2, ensure_ascii=False), encoding="utf-8")


def robots_allowed(url: str, user_agent: str) -> bool:
    parsed = urlparse(url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    parser = RobotFileParser()
    try:
        parser.set_url(robots_url)
        parser.read()
        return parser.can_fetch(user_agent, url)
    except Exception:
        return True


def extract_dates(text: str) -> tuple[str | None, str | None]:
    pub_match = re.search(
        r"(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s+\d{4}",
        text,
        flags=re.IGNORECASE,
    )
    eff_match = re.search(r"with effect from\s+([A-Za-z]+\s+\d{1,2},\s+\d{4})", text, flags=re.IGNORECASE)
    return (pub_match.group(0) if pub_match else None, eff_match.group(1) if eff_match else None)


def download_pdf(session: requests.Session, source: dict) -> tuple[Path | None, dict | None]:
    url = source["source_url"]
    filename = Path(urlparse(url).path).name or f"{re.sub(r'[^a-z0-9]+', '-', source['title'].lower())}.pdf"
    target = RAW_DIR / filename
    if target.exists():
        target.unlink()

    if not robots_allowed(url, USER_AGENT):
        print(f"robots.txt disallows download: {url}")
        return None, None

    time.sleep(2)
    referer = source.get("referer", url)
    try:
        session.get(referer, headers={"User-Agent": USER_AGENT, "Accept": "text/html,*/*"}, timeout=45)
    except Exception:
        pass
    response = session.get(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Referer": referer,
            "Accept": "application/pdf,*/*",
            "Accept-Language": "en-US,en;q=0.9",
            "Connection": "keep-alive",
        },
        timeout=45,
        stream=True,
    )
    response.raise_for_status()
    content_type = response.headers.get("content-type", "")
    body = response.content
    if "pdf" not in content_type.lower() and not body.startswith(b"%PDF"):
        print(f"Skipped non-PDF response for {url}: {content_type}")
        return None, None

    target.write_bytes(body)
    try:
        doc = fitz.open(target)
    except Exception as exc:
        target.unlink(missing_ok=True)
        print(f"Invalid PDF for {url}: {exc}")
        return None, None

    try:
        page_text = "\n".join(doc[i].get_text("text") for i in range(min(3, doc.page_count)))
        if not page_text.strip():
            print(f"No extractable text in {url}")
            target.unlink(missing_ok=True)
            return None, None
        sha256 = sha256_bytes(body)
        publication_date, effective_date = extract_dates(page_text)
        return target, {
            "title": source["title"],
            "source_url": url,
            "filename": target.name,
            "download_date": datetime.now(timezone.utc).isoformat(),
            "sha256": sha256,
            "publication_date": publication_date,
            "effective_date": effective_date,
            "category": source.get("category"),
        }
    finally:
        doc.close()


def main() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    manifest = load_manifest()
    known_hashes = {item.get("sha256") for item in manifest if item.get("sha256")}
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    for source in SOURCES:
        try:
            path, entry = download_pdf(session, source)
            if not entry:
                continue
            if entry["sha256"] in known_hashes:
                print(f"Duplicate skipped: {source['title']}")
                if path:
                    path.unlink(missing_ok=True)
                continue
            known_hashes.add(entry["sha256"])
            manifest = [item for item in manifest if item.get("sha256") != entry["sha256"]]
            manifest.append(entry)
            print(f"Downloaded: {source['title']} -> {path.name if path else 'n/a'}")
        except Exception as exc:
            print(f"Failed: {source['title']} -> {exc}")

    save_manifest(manifest)
    print(f"Manifest written to {MANIFEST_PATH}")


if __name__ == "__main__":
    main()
