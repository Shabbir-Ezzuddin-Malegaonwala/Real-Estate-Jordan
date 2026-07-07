// Display-layer formatting only. The API/engine stores canonical values;
// the client decorates (per project convention: conversions live in the UI).

export function jd(n: number): string {
  return new Intl.NumberFormat("en-JO", { maximumFractionDigits: 0 }).format(n);
}

export function jdPerM2(n: number): string {
  return `${jd(n)} JD/m²`;
}

export function money(n: number): string {
  return `${jd(n)} JD`;
}

export function pct(dec: number, digits = 1): string {
  const sign = dec > 0 ? "+" : dec < 0 ? "−" : "±";
  return `${sign}${Math.abs(dec * 100).toFixed(digits)}%`;
}

export function shortDate(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" });
}

export function titleCase(s: string): string {
  return s.charAt(0).toUpperCase() + s.slice(1);
}
