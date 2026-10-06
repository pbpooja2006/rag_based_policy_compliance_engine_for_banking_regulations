import re
import requests

headers = {
    "User-Agent": "AdaptiveRAG-ComplianceBot/1.0 (academic-research; banking-compliance-project)"
}

# Search RBI notifications page for recent fraud and ombudsman circulars
# Search using NotificationUser.aspx with keywords
keywords = ["Fraud Risk Management", "Integrated Ombudsman", "Grievance Redressal Mechanism"]

for kw in keywords:
    print(f"\nSearching RBI for keyword: {kw}")
    search_url = f"https://www.rbi.org.in/Scripts/NotificationUser.aspx"
    try:
        r = requests.get(search_url, headers=headers, timeout=15)
        # Look for links with the keyword or PDF links
        matches = re.findall(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?' + kw + r'.*?)</a>', r.text, re.IGNORECASE)
        print(f"Found {len(matches)} direct matches on first page")
        for href, text in matches[:5]:
            print(f"Text: {text.strip()} -> Href: {href}")
    except Exception as e:
        print(f"Error: {e}")
