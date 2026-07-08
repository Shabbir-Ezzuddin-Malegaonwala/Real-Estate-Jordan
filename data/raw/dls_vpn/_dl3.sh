#!/usr/bin/env bash
BASE="https://www.dls.gov.jo"
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
echo "=== _dl3 start $(date) ===" >> _dl.log
declare -a NAMES URLS
NAMES=(
 "monthly_trading_2026-05_May_AR.pdf"
 "monthly_trading_2026-04_April_AR.pdf"
 "monthly_trading_2026-01_January_AR.pdf"
 "monthly_trading_2025-12_December_AR.pdf"
 "monthly_trading_2025-11_November_AR.pdf"
 "mortgage_by_governorate_2025_AR.pdf"
 "mortgage_by_governorate_2024_AR.pdf"
 "property_owners_by_gov_gender_2025_AR.pdf"
 "property_owners_by_gov_gender_2024_AR.pdf"
 "annual_report_2013_EN.pdf"
 "annual_report_2014_EN.pdf"
 "annual_report_2015_EN.pdf"
 "annual_report_2016_EN.pdf"
 "annual_report_2017_EN.pdf"
)
URLS=(
 "$BASE/ebv4.0/root_storage/ar/eb_list_page/nashra-aqaria5-2026-0.pdf"
 "$BASE/ebv4.0/root_storage/ar/eb_list_page/nashra-aqaria4-2026.pdf"
 "$BASE/ebv4.0/root_storage/ar/eb_list_page/real_estate_1_2026.pdf"
 "$BASE/ebv4.0/root_storage/ar/eb_list_page/nashra_aqaria11_12_2025.pdf"
 "$BASE/ebv4.0/root_storage/ar/eb_list_page/nashra-aqaria11-2025.pdf"
 "$BASE/ebv4.0/root_storage/ar/eb_list_page/%D8%B9%D8%AF%D8%AF_%D9%85%D8%B9%D8%A7%D9%85%D9%84%D8%A7%D8%AA_%D8%A7%D9%84%D8%B1%D9%87%D9%86_%D8%A7%D9%84%D8%AA%D8%A3%D9%85%D9%8A%D9%86%D9%8A_%D8%AD%D8%B3%D8%A8_%D8%A7%D9%84%D9%85%D8%AD%D8%A7%D9%81%D8%B8%D8%A9_%D9%88%D8%A7%D9%84%D9%85%D8%AF%D9%8A%D8%B1%D9%8A%D8%A9_%D9%84%D8%B9%D8%A7%D9%85_2025-0.pdf"
 "$BASE/ebv4.0/root_storage/ar/eb_list_page/%D8%B9%D8%AF%D8%AF_%D9%85%D8%B9%D8%A7%D9%85%D9%84%D8%A7%D8%AA_%D8%A7%D9%84%D8%B1%D9%87%D9%86_%D8%A7%D9%84%D8%AA%D8%A3%D9%85%D9%8A%D9%86%D9%8A_%D8%AD%D8%B3%D8%A8_%D8%A7%D9%84%D9%85%D8%AD%D8%A7%D9%81%D8%B8%D8%A9_%D9%88%D8%A7%D9%84%D9%85%D8%AF%D9%8A%D8%B1%D9%8A%D8%A9_%D9%84%D8%B9%D8%A7%D9%85_2024-0.pdf"
 "$BASE/ebv4.0/root_storage/ar/eb_list_page/%D8%A3%D8%B9%D8%AF%D8%A7%D8%AF_%D9%85%D8%A7%D9%84%D9%83%D9%8A_%D8%A7%D9%84%D8%B9%D9%82%D8%A7%D8%B1%D8%A7%D8%AA_%D9%81%D9%8A_%D8%A7%D9%84%D9%85%D9%85%D9%84%D9%83%D8%A9_%D9%85%D8%B5%D9%86%D9%81%D9%8A%D9%86_%D8%AD%D8%B3%D8%A8_%D8%A7%D9%84%D9%85%D8%AD%D8%A7%D9%81%D8%B8%D8%A9_%D9%88%D8%A7%D9%84%D9%85%D8%AF%D9%8A%D8%B1%D9%8A%D8%A9_%D9%88%D8%A7%D9%84%D8%AC%D9%86%D8%B3_%D8%AD%D8%AA%D9%89_%D9%86%D9%87%D8%A7%D9%8A%D8%A9_%D8%B9%D8%A7%D9%85_2025-0.pdf"
 "$BASE/ebv4.0/root_storage/ar/eb_list_page/%D8%A3%D8%B9%D8%AF%D8%A7%D8%AF_%D9%85%D8%A7%D9%84%D9%83%D9%8A_%D8%A7%D9%84%D8%B9%D9%82%D8%A7%D8%B1%D8%A7%D8%AA_%D9%81%D9%8A_%D8%A7%D9%84%D9%85%D9%85%D9%84%D9%83%D8%A9_%D9%85%D8%B5%D9%86%D9%81%D9%8A%D9%86_%D8%AD%D8%B3%D8%A8_%D8%A7%D9%84%D9%85%D8%AD%D8%A7%D9%81%D8%B8%D8%A9_%D9%88%D8%A7%D9%84%D9%85%D8%AF%D9%8A%D8%B1%D9%8A%D8%A9_%D9%88%D8%A7%D9%84%D8%AC%D9%86%D8%B3_%D8%AD%D8%AA%D9%89_%D9%86%D9%87%D8%A7%D9%8A%D8%A9_%D8%B9%D8%A7%D9%85_2024-0.pdf"
 "$BASE/ebv4.0/root_storage/en/eb_list_page/annual_report_2013.pdf"
 "$BASE/ebv4.0/root_storage/en/eb_list_page/annual_report_2014.pdf"
 "$BASE/ebv4.0/root_storage/en/eb_list_page/annual_report_2015.pdf"
 "$BASE/ebv4.0/root_storage/en/eb_list_page/annual_report_2016.pdf"
 "$BASE/ebv4.0/root_storage/en/eb_list_page/annual_report_2017.pdf"
)
for i in "${!NAMES[@]}"; do
  f="${NAMES[$i]}"; u="${URLS[$i]}"
  for attempt in $(seq 1 30); do
    before=$(stat -c%s "$f" 2>/dev/null || echo 0)
    curl -sS -A "$UA" --connect-timeout 30 --max-time 300 --speed-limit 250 --speed-time 30 -C - -o "$f" "$u" 2>>_dl.log
    rc=$?
    after=$(stat -c%s "$f" 2>/dev/null || echo 0)
    if [ "$rc" -eq 0 ]; then echo "OK  $f  $after bytes (attempt $attempt)" >> _dl.log; break; fi
    if [ "$after" -le "$before" ] && [ "$attempt" -ge 10 ]; then echo "STALL $f  stuck at $after bytes" >> _dl.log; break; fi
    sleep 2
  done
done
echo "ALLDONE3 $(date)" >> _dl.log
