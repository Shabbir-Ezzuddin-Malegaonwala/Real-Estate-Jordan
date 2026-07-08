import csv

CAP = "2026-07-08"
CONF = "H"
SRC = "DLS"
BASE = "https://www.dls.gov.jo/ebv4.0/root_storage/ar/eb_list_page/"

URLS = {
 "2025-11": BASE + "nashra-aqaria11-2025.pdf",
 "2025-12": BASE + "nashra_aqaria11_12_2025.pdf",
 "2026-01": BASE + "real_estate_1_2026.pdf",
 "2026-04": BASE + "nashra-aqaria4-2026.pdf",
 "2026-05": BASE + "nashra-aqaria5-2026-0.pdf",
 "2026-06": BASE + "%D8%AD%D8%B1%D9%83%D8%A9_%D8%AA%D8%AF%D8%A7%D9%88%D9%84%D8%A7%D8%AA_%D8%B3%D9%88%D9%82_%D8%A7%D9%84%D8%B9%D9%82%D8%A7%D8%B1_%D9%84%D8%B4%D9%87%D8%B1_%D8%AD%D8%B2%D9%8A%D8%B1%D8%A7%D9%86_%D9%85%D9%86_%D8%B9%D8%A7%D9%85_2026.pdf",
}

# Per month: volume, revenue, total sales count, gov-type counts, non-Jordanian.
# gov-type: (amman_apt, amman_land, other_apt, other_land)
# nonj: (count_total, value_total, count_apt, count_land, value_apt, value_land)
M = {
 "2025-11": dict(volume=636161090, revenue=22504779, sales=12444,
    gov=(1978,3084,1041,6341), nonj=(240,24060085,152,88,13270788,10789297)),
 "2025-12": dict(volume=724702526, revenue=27926940, sales=13752,
    gov=(2073,3647,1104,6928), nonj=(201,15449729,128,73,10051315,5398414)),
 "2026-01": dict(volume=513414037, revenue=25928026, sales=9562,
    gov=(1658,2075,735,5094), nonj=(173,10033331,105,68,8063546,1969785)),
 "2026-04": dict(volume=573018685, revenue=22419593, sales=11727,
    gov=(1944,2566,919,6298), nonj=(166,15637228,99,67,8544983,7092245)),
 "2026-05": dict(volume=474268087, revenue=18896506, sales=10513,
    gov=(1812,2307,823,5571), nonj=(174,19652185,115,59,10604371,9047814)),
 "2026-06": dict(volume=584336633, revenue=24207316, sales=11884,
    gov=(2073,2718,917,6176), nonj=(186,24311296,119,67,10752792,13558504)),
}

# Nationality (non-Jordanian) — only months fully read from tables
NAT = {
 "2026-06": {"count":[("Iraqi",45),("Syrian",24),("Palestinian",22),("Saudi",15),("American",11),("British",11)],
             "value":[("Iraqi",13176175),("Palestinian",2008042),("British",1639315),("Syrian",1398204),("Saudi",1005410)]},
 "2026-05": {"count":[("Iraqi",49),("Syrian",24),("American",15),("Palestinian",14),("Saudi",13),("Egyptian",13)],
             "value":[("Iraqi",9817680),("Palestinian",1886754),("Yemeni",1463192),("Syrian",1249778),("American",1001236)]},
}

rows = []
def add(period, ptype, gov, nat, metric, count, value, url, notes=""):
    rows.append(dict(source_name=SRC, source_url=url, capture_date=CAP, confidence=CONF,
        period=period, property_type=ptype, governorate=gov, nationality=nat, metric=metric,
        transaction_count=(count if count is not None else ""),
        transaction_value_jd=(value if value is not None else ""), notes=notes))

for period, d in M.items():
    u = URLS[period]
    aa, al, oa, ol = d["gov"]
    ta, tl = aa+oa, al+ol
    # headline
    add(period,"all","Kingdom","all","trading_volume_jd",None,d["volume"],u,"registered transactions, all property types")
    add(period,"all","Kingdom","all","dls_revenue_jd",None,d["revenue"],u,"")
    add(period,"all","Kingdom","all","sales_count",d["sales"],None,u,"total registered sale transactions")
    add(period,"all","Kingdom","all","avg_deal_size_jd",None,round(d["volume"]/d["sales"]),u,"volume/count; blended land+apartment")
    # governorate x type counts
    add(period,"apartment","Amman","all","sales_count",aa,None,u,"Table 2")
    add(period,"land","Amman","all","sales_count",al,None,u,"Table 2")
    add(period,"apartment","Other_Governorates","all","sales_count",oa,None,u,"Table 2")
    add(period,"land","Other_Governorates","all","sales_count",ol,None,u,"Table 2")
    add(period,"apartment","Kingdom","all","sales_count",ta,None,u,"subtotal")
    add(period,"land","Kingdom","all","sales_count",tl,None,u,"subtotal")
    # non-Jordanian
    nc,nv,nca,ncl,nva,nvl = d["nonj"]
    add(period,"all","Kingdom","non_jordanian","possession_count",nc,None,u,"Table 6")
    add(period,"all","Kingdom","non_jordanian","possession_value_jd",None,nv,u,"Table 6")
    add(period,"apartment","Kingdom","non_jordanian","possession_count",nca,None,u,"")
    add(period,"land","Kingdom","non_jordanian","possession_count",ncl,None,u,"")
    add(period,"apartment","Kingdom","non_jordanian","possession_value_jd",None,nva,u,"")
    add(period,"land","Kingdom","non_jordanian","possession_value_jd",None,nvl,u,"")
    add(period,"apartment","Kingdom","non_jordanian","avg_deal_size_jd",None,round(nva/nca),u,"non-Jordanian apt avg")
    add(period,"land","Kingdom","non_jordanian","avg_deal_size_jd",None,round(nvl/ncl),u,"non-Jordanian land avg")
    # nationality
    if period in NAT:
        for nat,c in NAT[period]["count"]:
            add(period,"all","Kingdom",nat,"possession_count",c,None,u,"non-Jordanian by nationality")
        for nat,v in NAT[period]["value"]:
            add(period,"all","Kingdom",nat,"possession_value_jd",None,v,u,"non-Jordanian by nationality")

# Cumulative anchors
add("2025-FY","all","Kingdom","all","trading_volume_jd",None,7179606527,URLS["2025-12"],"full-year 2025, +7% vs 2024")
add("2025-FY","all","Kingdom","all","dls_revenue_jd",None,274973376,URLS["2025-12"],"full-year 2025")
add("2026-H1","all","Kingdom","all","trading_volume_jd",None,3042318880,URLS["2026-06"],"Jan-Jun 2026, -3% vs H1 2025")
add("2026-H1","all","Kingdom","all","dls_revenue_jd",None,128864281,URLS["2026-06"],"Jan-Jun 2026")
add("2026-H1","all","Kingdom","all","sales_count",62023,None,URLS["2026-06"],"Jan-Jun 2026, -8% YoY")
add("2026-H1","all","Kingdom","non_jordanian","possession_count",1046,None,URLS["2026-06"],"Jan-Jun 2026")
add("2026-H1","all","Kingdom","non_jordanian","possession_value_jd",None,100034214,URLS["2026-06"],"Jan-Jun 2026")

cols = ["source_name","source_url","capture_date","confidence","period","property_type",
        "governorate","nationality","metric","transaction_count","transaction_value_jd","notes"]
out = "C:/Rubicon/Real-Estate-Jordan/data/raw/dls_vpn/dls_monthly_transactions.csv"
with open(out,"w",newline="",encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, fieldnames=cols); w.writeheader()
    for r in rows: w.writerow(r)
print("wrote", len(rows), "rows ->", out)
# print the national series for the report
print("\nMONTH  VOLUME_JD  SALES  AVG_DEAL  NONJ_CNT  NONJ_VAL")
for p,d in M.items():
    print(f"{p}  {d['volume']:>13,}  {d['sales']:>6,}  {round(d['volume']/d['sales']):>7,}  {d['nonj'][0]:>5}  {d['nonj'][1]:>12,}")
