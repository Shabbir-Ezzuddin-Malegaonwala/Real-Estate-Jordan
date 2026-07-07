"""Fetch CBJ Real Estate Price Index page and discover downloadable files.
Task A of official-data workstream. Saves originals to data/raw/cbj/.
"""
import os
import re
import sys
import requests

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,ar;q=0.8",
}
RAW = r"C:\Rubicon\Real-Estate-Jordan\data\raw\cbj"

PAGES = [
    "https://www.cbj.gov.jo/En/List/Jordan_Real_Estate_Price_Index",
    "https://www.cbj.gov.jo/Ar/List/الرقم_القياسي_لأسعار_العقارات",
]


def fetch(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=40, verify=True)
        return r
    except Exception as e:
        print(f"ERROR fetching {url}: {e}")
        return None


def main():
    os.makedirs(RAW, exist_ok=True)
    for url in PAGES:
        print(f"\n=== GET {url}")
        r = fetch(url)
        if r is None:
            continue
        print(f"HTTP {r.status_code} len={len(r.content)} ctype={r.headers.get('content-type')}")
        if r.status_code != 200:
            continue
        html = r.text
        # find hrefs to files
        links = re.findall(r'href="([^"]+)"', html, flags=re.IGNORECASE)
        interesting = [l for l in links if re.search(r'\.(xlsx?|pdf|csv)(\?|$)', l, re.I)
                       or 'download' in l.lower() or 'file' in l.lower() or 'attach' in l.lower()]
        print(f"total links={len(links)} interesting={len(interesting)}")
        for l in sorted(set(interesting)):
            print("  ", l)
        # save the html for inspection
        fn = os.path.join(RAW, "page_" + re.sub(r'\W+', '_', url)[-40:] + ".html")
        with open(fn, "w", encoding="utf-8") as f:
            f.write(html)
        print("saved", fn)


if __name__ == "__main__":
    main()
