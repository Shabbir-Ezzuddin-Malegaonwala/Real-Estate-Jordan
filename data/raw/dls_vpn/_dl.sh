#!/usr/bin/env bash
BASE="https://www.dls.gov.jo"
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
dl() {
  curl -sSL --retry 5 --retry-all-errors --retry-delay 3 -C - --max-time 1200 \
       --connect-timeout 40 -A "$UA" -o "$2" "$1" \
    && echo "OK  $2  $(stat -c%s "$2" 2>/dev/null) bytes" >> _dl.log \
    || echo "FAIL $2  $1" >> _dl.log
}
: > _dl.log
dl "$BASE/ebv4.0/root_storage/ar/eb_list_page/%D8%AD%D8%B1%D9%83%D8%A9_%D8%AA%D8%AF%D8%A7%D9%88%D9%84%D8%A7%D8%AA_%D8%B3%D9%88%D9%82_%D8%A7%D9%84%D8%B9%D9%82%D8%A7%D8%B1_%D9%84%D8%B4%D9%87%D8%B1_%D8%AD%D8%B2%D9%8A%D8%B1%D8%A7%D9%86_%D9%85%D9%86_%D8%B9%D8%A7%D9%85_2026.pdf" "monthly_trading_2026-06_June_AR.pdf"
dl "$BASE/EBV4.0/Root_Storage/AR/EB_HomePage/annualreport2023.pdf" "annual_report_2023_AR.pdf"
for y in 2012 2013 2014 2015 2016 2017 2018; do
  dl "$BASE/ebv4.0/root_storage/en/eb_list_page/annual_report_${y}.pdf" "annual_report_${y}_EN.pdf"
done
echo "ALLDONE" >> _dl.log
