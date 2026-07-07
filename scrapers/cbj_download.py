"""Download CBJ Real Estate Price Index Excel + probe statistical DB.
Saves originals to data/raw/cbj/.
"""
import os
import requests

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.9,ar;q=0.8",
    "Referer": "https://www.cbj.gov.jo/En/List/Jordan_Real_Estate_Price_Index",
}
RAW = r"C:\Rubicon\Real-Estate-Jordan\data\raw\cbj"

FILES = [
    ("https://www.cbj.gov.jo/ebv4.0/root_storage/en/eb_list_page/real_estate.xls", "real_estate_en.xls"),
    ("https://www.cbj.gov.jo/ebv4.0/root_storage/ar/eb_list_page/real_estate.xls", "real_estate_ar.xls"),
]


def dl(url, name):
    try:
        r = requests.get(url, headers=HEADERS, timeout=60, verify=True)
        print(f"{url} -> HTTP {r.status_code} len={len(r.content)} ctype={r.headers.get('content-type')}")
        if r.status_code == 200 and len(r.content) > 200:
            path = os.path.join(RAW, name)
            with open(path, "wb") as f:
                f.write(r.content)
            print("  saved", path)
            return path
    except Exception as e:
        print(f"  ERROR {url}: {e}")
    return None


def main():
    os.makedirs(RAW, exist_ok=True)
    for url, name in FILES:
        dl(url, name)


if __name__ == "__main__":
    main()
