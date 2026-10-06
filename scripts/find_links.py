import re
import requests

headers = {
    "User-Agent": "AdaptiveRAG-ComplianceBot/1.0 (academic-research; banking-compliance-project)"
}

urls = [
    "https://www.rbi.org.in/Scripts/BS_ViewMasDirections.aspx?id=11566",
    "https://www.rbi.org.in/Scripts/NotificationUser.aspx?Id=12382&Mode=0",
    "https://www.rbi.org.in/Scripts/NotificationUser.aspx?Id=11040&Mode=0",
]

for url in urls:
    print(f"\n--- Checking {url} ---")
    try:
        r = requests.get(url, headers=headers, timeout=15)
        matches = re.findall(r'href=["\']([^"\']+\.pdf)["\']', r.text, re.IGNORECASE)
        for m in set(matches):
            if "pdf" in m.lower():
                full_url = m if m.startswith("http") else f"https://www.rbi.org.in/{m.lstrip('/')}"
                print("PDF:", full_url)
    except Exception as e:
        print(f"Error checking {url}: {e}")
