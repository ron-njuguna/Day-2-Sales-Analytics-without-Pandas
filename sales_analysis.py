import csv
import re
from pathlib import Path

DATA_PATH = Path("data") / "electronics_sales.csv"
REPORT_PATH = Path("output") / "sales_report.txt"
THRESHOLD = 50_000

NUMBER_WORDS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
}

def read_sales(path: Path = DATA_PATH) -> list[dict[str, str]]:
    
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        columns = reader.fieldnames
    print(f"Read {len(rows)} rows")
    print(f"Columns: {', '.join(columns)}")
    return rows


def parse_number(value: str) -> float | None:
    
    if value is None:
        return None
    text = value.strip().lower()
    if text == "":
        return None
    if text in NUMBER_WORDS:
        return float(NUMBER_WORDS[text])
    text = re.sub(r"^(kes|ksh|ksh\.|kshs)\s*", "", text)   
    text = re.sub(r"\s*(kes|ksh|kshs)$", "", text)          
    text = text.replace(",", "").strip()
    if not re.fullmatch(r"\d+(\.\d+)?", text):
        return None
    number = float(text)
    return number if number > 0 else None


def convert_rows(rows: list[dict[str, str]]) -> tuple[list[dict], list[dict]]:
    
    clean, skipped = [], []
    for row in rows:
        quantity = parse_number(row["quantity"])
        price = parse_number(row["unit_price_kes"])

        reason = None
        if quantity is None:
            reason = f"unusable quantity ({row['quantity']!r})"
        elif quantity != int(quantity):
            reason = f"non-whole quantity ({row['quantity']!r})"
        elif price is None:
            reason = f"unusable unit price ({row['unit_price_kes']!r})"

        if reason:
            skipped.append({"sale_id": row["sale_id"], "reason": reason})
            continue

        new_row = dict(row)
        new_row["quantity"] = int(quantity)
        new_row["unit_price_kes"] = price
        new_row["revenue"] = quantity * price
        clean.append(new_row)
    return clean, skipped


def total_revenue(rows: list[dict]) -> float:
    total = 0.0
    for row in rows:
        total += row["revenue"]
    return total


def revenue_by(rows: list[dict], field: str) -> dict[str, float]:
    
    totals = {}
    for row in rows:
        key = row[field]
        if key in totals:
            totals[key] += row["revenue"]
        else:
            totals[key] = row["revenue"]
    return totals


def top_n(totals: dict[str, float], n: int = 3) -> list[tuple[str, float]]:
    
    ranked = sorted(totals.items(), key=lambda item: (-item[1], item[0]))
    return ranked[:n]


def high_value(rows: list[dict], threshold: float) -> list[dict]:
  
    return [row for row in rows if row["revenue"] >= threshold]


def mean(values: list[float]) -> float:
    if not values:
        raise ValueError
    total = 0.0
    for v in values:
        total += v
    return total / len(values)


def median(values: list[float]) -> float:
    if not values:
        raise ValueError
    ordered = sorted(values)
    n = len(ordered)
    mid = n // 2
    if n % 2 == 1:
        return ordered[mid]
    return (ordered[mid - 1] + ordered[mid]) / 2


def minimum_maximum(values: list[float]) -> tuple[float, float]:
    if not values:
        raise ValueError
    low = high = values[0]
    for v in values[1:]:
        if v < low:
            low = v
        if v > high:
            high = v
    return low, high

def verify_with_pandas(path: Path, my_results: dict) -> list[str]:
    
    import pandas as pd

    df = pd.read_csv(path, dtype=str, keep_default_na=False)

    def clean(series, words=False):
        s = series.str.strip().str.lower()
        if words:
            
            s = s.replace({w: str(n) for w, n in NUMBER_WORDS.items()})
        s = (s.str.replace(r"^(kes|ksh|ksh\.|kshs)\s*", "", regex=True)
              .str.replace(r"\s*(kes|ksh|kshs)$", "", regex=True)
              .str.replace(",", "", regex=False))
        s = pd.to_numeric(s, errors="coerce")
        return s.where(s > 0)

    df["qty"] = clean(df["quantity"], words=True)
    df["price"] = clean(df["unit_price_kes"])
    df = df.dropna(subset=["qty", "price"])
    df = df[df["qty"] == df["qty"].round()]
    df["revenue"] = df["qty"] * df["price"]

    def same(a, b):
        return abs(a - b) < 0.005

    lines = []

    p_total = float(df["revenue"].sum())
    lines.append("Total revenue      : " + (
        "MATCH" if same(p_total, my_results["total"])
        else f"MISMATCH (pure={my_results['total']:,.2f}, pandas={p_total:,.2f})"))

    p_prod = df.groupby("product")["revenue"].sum()
    ok = (set(p_prod.index) == set(my_results["by_product"])
          and all(same(p_prod[k], v) for k, v in my_results["by_product"].items()))
    lines.append("Revenue by product : " + (
        "MATCH" if ok else f"MISMATCH (pure={my_results['by_product']}, pandas={p_prod.to_dict()})"))

    p_top = sorted(p_prod.items(), key=lambda kv: (-kv[1], kv[0]))[:3]
    ok = ([k for k, _ in p_top] == [k for k, _ in my_results["top3"]]
          and all(same(a[1], b[1]) for a, b in zip(p_top, my_results["top3"])))
    lines.append("Top 3              : " + (
        "MATCH" if ok else f"MISMATCH (pure={my_results['top3']}, pandas={p_top})"))

    p_mean, p_median = float(df["revenue"].mean()), float(df["revenue"].median())
    ok = same(p_mean, my_results["mean"]) and same(p_median, my_results["median"])
    lines.append("Mean / median      : " + (
        "MATCH" if ok else
        f"MISMATCH (pure={my_results['mean']:,.2f}/{my_results['median']:,.2f}, "
        f"pandas={p_mean:,.2f}/{p_median:,.2f})"))
    return lines


def money(x: float) -> str:
    return f"{x:,.2f}"


def build_report(raw, clean, skipped, my_results) -> str:
    out = []
    skipped_text = ", ".join(f"{s['sale_id']}: {s['reason']}" for s in skipped)
    out.append("=== Sales report: September 2026 ===")
    out.append(f"Rows read          : {len(raw)}")
    out.append(f"Rows used          : {len(clean)}")
    out.append(f"Rows skipped       : {len(skipped)}   ({skipped_text})")
    out.append("")
    out.append(f"Total revenue (KES): {money(my_results['total'])}")
    out.append("")

    by_product = my_results["by_product"]
    out.append("Revenue by product (KES)")
    for product, amount in sorted(by_product.items(), key=lambda kv: (-kv[1], kv[0])):
        out.append(f"  {product:<26}{money(amount):>14}")
    out.append("")

    out.append("Revenue by store (KES)")
    for store, amount in sorted(my_results["by_store"].items(), key=lambda kv: (-kv[1], kv[0])):
        out.append(f"  {store:<26}{money(amount):>14}")
    out.append("")
    out.append("Revenue by payment method (KES)")
    for method, amount in sorted(my_results["by_payment"].items(), key=lambda kv: (-kv[1], kv[0])):
        out.append(f"  {method:<26}{money(amount):>14}")
    out.append("")

    out.append("Top 3 products")
    for i, (product, amount) in enumerate(my_results["top3"], start=1):
        out.append(f"  {i}. {product} - KES {money(amount)}")
    out.append("")

    hv = my_results["high_value"]
    out.append(f"High-value transactions (>= KES {THRESHOLD:,}): {len(hv)}")
    for r in hv:
        out.append(f"  {r['sale_id']}  {r['sale_date']}  {r['store']}  {r['product']}  KES {money(r['revenue'])}")
    out.append("  Per store: " + ", ".join(f"{s}: {n}" for s, n in my_results["hv_by_store"].items()))
    out.append("")

    out.append("Transaction revenue statistics")
    out.append(f"  mean   : {money(my_results['mean'])}")
    out.append(f"  median : {money(my_results['median'])}")
    out.append(f"  min    : {money(my_results['min'])}")
    out.append(f"  max    : {money(my_results['max'])}")
    out.append("")
    out.append("=== pandas verification ===")
    out.extend(my_results["verification"])
    return "\n".join(out) + "\n"


def main() -> None:
    raw = read_sales(DATA_PATH)
    clean, skipped = convert_rows(raw)

    revenues = [r["revenue"] for r in clean]
    by_product = revenue_by(clean, "product")
    hv = high_value(clean, THRESHOLD)
    low, high = minimum_maximum(revenues)

    my_results = {
        "total": total_revenue(clean),
        "by_product": by_product,
        "by_store": revenue_by(clean, "store"),
        "by_payment": revenue_by(clean, "payment_method"),
        "top3": top_n(by_product, 3),
        "high_value": hv,
        "hv_by_store": {store: len([r for r in hv if r["store"] == store])
                        for store in sorted({r["store"] for r in clean})},
        "mean": mean(revenues),
        "median": median(revenues),
        "min": low,
        "max": high,
    }

    try:
        my_results["verification"] = verify_with_pandas(DATA_PATH, my_results)
    except ImportError:
        my_results["verification"] = ["pandas not installed - verification skipped"]

    report = build_report(raw, clean, skipped, my_results)
    print(report)
    REPORT_PATH.parent.mkdir(exist_ok=True)
    REPORT_PATH.write_text(report, encoding="utf-8")
    print(f"Saved to {REPORT_PATH}")


if __name__ == "__main__":
    main()
