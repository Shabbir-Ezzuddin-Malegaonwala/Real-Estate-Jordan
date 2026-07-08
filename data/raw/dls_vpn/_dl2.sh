#!/usr/bin/env bash
BASE="https://www.dls.gov.jo"
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
: > _dl.log
declare -a NAMES URLS
NAMES=(
 "monthly_trading_2026-06_June_AR.pdf"
 "annual_report_2023_AR.pdf"
 "annual_report_2018_EN.pdf"
 "annual_report_2017_EN.pdf"
 "annual_report_2016_EN.pdf"
 "annual_report_2015_EN.pdf"
 "annual_report_2014_EN.pdf"
 "annual_report_2013_EN.pdf"
 "annual_report_2012_EN.pdf"
)
URLS=(
 "$BASE/ebv4.0/root_storage/ar/eb_list_page/%D8%AD%D8%B1%D9%83%D8%A9_%D8%AA%D8%AF%D8%A7%D9%88%D9%84%D8%A7%D8%AA_%D8%B3%D9%88%D9%82_%D8%A7%D9%84%D8%B9%D9%82%D8%A7%D8%B1_%D9%84%D8%B4%D9%87%D8%B1_%D8%AD%D8%B2%D9%8A%D8%B1%D8%A7%D9%86_%D9%85%D9%86_%D8%B9%D8%A7%D9%85_2026.pdf"
 "$BASE/EBV4.0/Root_Storage/AR/EB_HomePage/annualreport2023.pdf"
 "$BASE/ebv4.0/root_storage/en/eb_list_page/annual_report_2018.pdf"
 "$BASE/ebv4.0/root_storage/en/eb_list_page/annual_report_2017.pdf"
 "$BASE/ebv4.0/root_storage/en/eb_list_page/annual_report_2016.pdf"
 "$BASE/ebv4.0/root_storage/en/eb_list_page/annual_report_2015.pdf"
 "$BASE/ebv4.0/root_storage/en/eb_list_page/annual_report_2014.pdf"
 "$BASE/ebv4.0/root_storage/en/eb_list_page/annual_report_2013.pdf"
 "$BASE/ebv4.0/root_storage/en/eb_list_page/annual_report_2012.pdf"
)
for i in "${!NAMES[@]}"; do
  f="${NAMES[$i]}"; u="${URLS[$i]}"
  for attempt in $(seq 1 25); do
    before=$(stat -c%s "$f" 2>/dev/null || echo 0)
    curl -sS -A "$UA" --connect-timeout 30 --max-time 300 \
         --speed-limit 300 --speed-time 30 -C - -o "$f" "$u" 2>>_dl.log
    rc=$?
    after=$(stat -c%s "$f" 2>/dev/null || echo 0)
    if [ "$rc" -eq 0 ]; then echo "OK  $f  $after bytes (attempt $attempt)" >> _dl.log; break; fi
    if [ "$after" -le "$before" ] && [ "$attempt" -ge 8 ]; then echo "STALL $f  stuck at $after bytes" >> _dl.log; break; fi
    sleep 2
  done
done
echo "ALLDONE" >> _dl.log
