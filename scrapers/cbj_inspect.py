"""Dump CBJ real_estate.xls fully to a UTF-8 text file for structure analysis."""
import xlrd

wb = xlrd.open_workbook(r"C:\Rubicon\Real-Estate-Jordan\data\raw\cbj\real_estate_en.xls")
out = []
out.append("SHEETS: " + " | ".join(wb.sheet_names()))
for sn in wb.sheet_names():
    sh = wb.sheet_by_name(sn)
    out.append(f"\n===== SHEET '{sn}': {sh.nrows} rows x {sh.ncols} cols =====")
    for r in range(min(sh.nrows, 120)):
        cells = []
        for c in range(sh.ncols):
            v = sh.cell_value(r, c)
            if isinstance(v, float) and v == int(v):
                v = int(v)
            cells.append(str(v))
        line = " | ".join(cells).rstrip(" |")
        if line.strip():
            out.append(f"[{r}] {line}")

with open(r"C:\Rubicon\Real-Estate-Jordan\data\raw\cbj\_dump.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(out))
print("wrote dump, sheets:", len(wb.sheet_names()))
