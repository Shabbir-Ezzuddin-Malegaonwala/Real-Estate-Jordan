import csv

SRC = "DLS"
URL = ("https://www.dls.gov.jo/ebv4.0/root_storage/ar/eb_list_page/"
       "حركة_تداولات_سوق_العقار_لشهر_حزيران_من_عام_2026.pdf")
CAP = "2026-07-08"
CONF = "H"

# Long/tidy rows. value_jd blank where the report gives only counts.
rows = []
def add(period, ptype, gov, nat, metric, count, value, notes=""):
    rows.append(dict(source_name=SRC, source_url=URL, capture_date=CAP, confidence=CONF,
                     period=period, property_type=ptype, governorate=gov, nationality=nat,
                     metric=metric, transaction_count=count, transaction_value_jd=value, notes=notes))

# --- Headline national figures ---
add("2026-06","all","Kingdom","all","trading_volume_jd","","584336633","+7% YoY, +23% MoM")
add("2026-H1","all","Kingdom","all","trading_volume_jd","","3042318880","-3% vs H1 2025")
add("2026-06","all","Kingdom","all","dls_revenue_jd","","24207316","+39% YoY, +28% MoM")
add("2026-H1","all","Kingdom","all","dls_revenue_jd","","128864281","+5% vs H1 2025; 2025=122958240")
add("2026-06","all","Kingdom","all","sales_count","11884","","+12% YoY, +13% MoM")
add("2026-H1","all","Kingdom","all","sales_count","62023","","-8% vs H1 2025 (67717)")
add("2026-H1","all","Kingdom","companies","sales_count","4633","","properties sold to companies")
add("2026-H1","all","Kingdom","all","female_owner_pct","","","35.05% female / 64.95% male owners")

# --- Table 1: H1 sale counts by governorate & type (2026) ---
add("2026-H1","apartment","Amman","all","sales_count","10729","","Table1; 2025=10964; -2%")
add("2026-H1","land","Amman","all","sales_count","13929","","Table1; 2025=15615; -11%")
add("2026-H1","apartment","Other_Governorates","all","sales_count","4804","","Table1; 2025=5446; -12%")
add("2026-H1","land","Other_Governorates","all","sales_count","32561","","Table1; 2025=35692; -9%")
add("2026-H1","apartment","Kingdom","all","sales_count","15533","","Table1 subtotal; 2025=16410; -5%")
add("2026-H1","land","Kingdom","all","sales_count","46490","","Table1 subtotal; 2025=51307; -9%")

# --- Table 2: June sale counts by governorate & type (2026) ---
add("2026-06","apartment","Amman","all","sales_count","2073","","Table2; 2025=1777; +17%")
add("2026-06","land","Amman","all","sales_count","2718","","Table2; 2025=2392; +14%")
add("2026-06","apartment","Other_Governorates","all","sales_count","917","","Table2; 2025=882; +4%")
add("2026-06","land","Other_Governorates","all","sales_count","6176","","Table2; 2025=5515; +12%")
add("2026-06","apartment","Kingdom","all","sales_count","2990","","Table2 subtotal; 2025=2659; +12%")
add("2026-06","land","Kingdom","all","sales_count","8894","","Table2 subtotal; 2025=7907; +12%")

# --- Table 3: H1 apartments sold by area (2026) ---
add("2026-H1","apartment_lt120m2","Kingdom","all","sales_count","4681","","Table3; 2025=4853; -4%")
add("2026-H1","apartment_120_150m2","Kingdom","all","sales_count","4479","","Table3; 2025=4197; +7%")
add("2026-H1","apartment_gt150m2","Kingdom","all","sales_count","7349","","Table3; 2025=7412; -1%")
# --- Table 4: June apartments sold by area (2026) ---
add("2026-06","apartment_lt120m2","Kingdom","all","sales_count","875","","Table4; 2025=808; +8%")
add("2026-06","apartment_120_150m2","Kingdom","all","sales_count","867","","Table4; 2025=665; +30%")
add("2026-06","apartment_gt150m2","Kingdom","all","sales_count","1451","","Table4; 2025=1211; +20%")

# --- Table 5: Non-Jordanian possession H1 2026 ---
add("2026-H1","apartment","Kingdom","non_jordanian","possession_count","653","","Table5; 2025=622; +5%")
add("2026-H1","land","Kingdom","non_jordanian","possession_count","393","","Table5; 2025=487; -19%")
add("2026-H1","all","Kingdom","non_jordanian","possession_count","1046","","Table5; 2025=1109; -6%")
add("2026-H1","all","Kingdom","non_jordanian","possession_value_jd","","100034214","Table5; 2025=90691297; +10%")
add("2026-H1","apartment","Kingdom","non_jordanian","possession_value_jd","","55974727","56% of H1 value")
add("2026-H1","land","Kingdom","non_jordanian","possession_value_jd","","44059487","44% of H1 value")

# --- Table 6: Non-Jordanian possession June 2026 ---
add("2026-06","apartment","Kingdom","non_jordanian","possession_count","119","","Table6; 2025=83; +43%")
add("2026-06","land","Kingdom","non_jordanian","possession_count","67","","Table6; 2025=63; +6%")
add("2026-06","all","Kingdom","non_jordanian","possession_count","186","","Table6; 2025=146; +27%")
add("2026-06","all","Kingdom","non_jordanian","possession_value_jd","","24311296","Table6; 2025=9925230; +145%")
add("2026-06","apartment","Kingdom","non_jordanian","possession_value_jd","","10752792","44% of June value")
add("2026-06","land","Kingdom","non_jordanian","possession_value_jd","","13558504","56% of June value")

# --- Nationality breakdown, H1 2026 (count) ---
for nat,c in [("Iraqi",267),("Saudi",135),("Syrian",114),("Palestinian",100),("American",73)]:
    add("2026-H1","all","Kingdom",nat,"possession_count",str(c),"","H1 non-Jordanian by nationality (count rank)")
# --- Nationality breakdown, H1 2026 (value) ---
for nat,v in [("Iraqi",46958348),("Palestinian",7937204),("Syrian",6490189),("American",5903968),("British",4746564),("Saudi",4157763)]:
    add("2026-H1","all","Kingdom",nat,"possession_value_jd","",str(v),"H1 non-Jordanian by nationality (value)")
# --- Nationality breakdown, June 2026 (count) ---
for nat,c in [("Iraqi",45),("Syrian",24),("Palestinian",22),("Saudi",15),("American",11),("British",11)]:
    add("2026-06","all","Kingdom",nat,"possession_count",str(c),"","June non-Jordanian by nationality (count)")
# --- Nationality breakdown, June 2026 (value) ---
for nat,v in [("Iraqi",13176175),("Palestinian",2008042),("British",1639315),("Syrian",1398204),("Saudi",1005410)]:
    add("2026-06","all","Kingdom",nat,"possession_value_jd","",str(v),"June non-Jordanian by nationality (value)")

cols = ["source_name","source_url","capture_date","confidence","period","property_type",
        "governorate","nationality","metric","transaction_count","transaction_value_jd","notes"]
out = "C:/Rubicon/Real-Estate-Jordan/data/raw/dls_vpn/dls_june2026_extracted.csv"
with open(out,"w",newline="",encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, fieldnames=cols); w.writeheader()
    for r in rows: w.writerow(r)
print("wrote", len(rows), "rows to", out)
