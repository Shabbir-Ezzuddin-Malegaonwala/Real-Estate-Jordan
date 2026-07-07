"""Discovery probe for DLS, DoS, and CBJ statistical DB. Logs HTTP codes + file links.
Does not extract — just maps what is reachable and downloadable.
"""
import re
import requests

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,ar;q=0.8",
}

TARGETS = {
    "CBJ_statdb": "http://statisticaldb.cbj.gov.jo/index?lang=en",
    "DLS_home_en": "https://www.dls.gov.jo/Default/En",
    "DLS_indicators_ar": "https://www.dls.gov.jo/AR/List/%D9%85%D8%A4%D8%B4%D8%B1%D8%A7%D8%AA",
    "DLS_annual_en": "https://www.dls.gov.jo/EN/List/Annual_Reports",
    "DoS_permits": "https://dosweb.dos.gov.jo/industry/building-licenses/",
    "JDP": "http://jdp.dos.gov.jo",
}


def probe(name, url):
    print(f"\n===== {name}: {url}")
    try:
        r = requests.get(url, headers=HEADERS, timeout=35, verify=False)
    except Exception as e:
        print(f"  ERROR: {type(e).__name__}: {e}")
        return
    print(f"  HTTP {r.status_code} len={len(r.content)} ctype={r.headers.get('content-type')} final={r.url}")
    if r.status_code != 200 or "html" not in (r.headers.get("content-type") or ""):
        return
    html = r.text
    links = re.findall(r'href="([^"]+)"', html, flags=re.I)
    files = sorted(set(l for l in links if re.search(r'\.(xlsx?|pdf|csv|zip)(\?|$)', l, re.I)
                       or re.search(r'(download|getfile|attach|storage|upload)', l, re.I)))
    print(f"  links={len(links)} file-like={len(files)}")
    for l in files[:40]:
        print("    ", l)


if __name__ == "__main__":
    requests.packages.urllib3.disable_warnings()
    for n, u in TARGETS.items():
        probe(n, u)
