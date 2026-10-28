<!-- ## Day 2 – Tech Hub Kenya September Sales Analytics -->
<!-- ## Approach -->

- **Tasks 1–7 use only the Python standard library** (`csv`, `re`, `pathlib`), so the script runs on the
  reporting server with no packages installed.
- `read_sales` loads raw rows with `csv.DictReader`; `convert_rows` cleans them; every later
  function works on the cleaned rows (each gets a `revenue = quantity × unit price` field).
- `revenue_by` uses a plain `dict` (no `defaultdict`/`Counter`); `top_n` uses `sorted()` with a key;
  `high_value` is a list comprehension; the per-store count is a dict comprehension.
- `mean`, `median`, `minimum_maximum` are hand-written, with no `statistics` module and no
  `min()`/`max()` inside `minimum_maximum`. Each raises `ValueError` on an empty list.
- **Task 8:** `verify_with_pandas` re-reads the CSV with pandas, re-applies the same cleaning rules
  and compares total, per-product revenue, top 3 and mean/median. pandas is imported only inside that
  function, so if it is missing the script still produces the full report and says verification was skipped.

<!-- ## How to run -->

```bash
cd day2-sales-analytics
pip install -r requirements.txt  
python sales_analysis.py          
```

<!-- ## Cleaning rules (and why) -->

 38,999 (S-3017)  price repaired is 38999  A thousands separator; same price as every other Hisense TV row (38,999). 
 KES 18999 (S-3029)  price repaired is 18999  Currency label only; matches the other Samsung Galaxy A15 rows. 
 two (S-3006)  quantity repaired is 2  Unambiguous spelled-out number. Only `one` `ten` are accepted. 
 N/A (S-3030)  price skipped  No price recorded. Filling it from other HP laptop rows would be inventing data. 
 empty (S-3035)  quantity Skipped  Quantity unknown; assuming 1 could badly under- or over-state a KES 13,499 phone sale. 
 empty (S-3039)  price  Skipped  Price unknown (same reasoning as `N/A`). 

General rules in parse_number: strip whitespace, strip a `KES`/`Ksh` tag, remove commas, accept spelled-out
small numbers for quantity; anything that is not a plain positive number afterwards returns `None`.
Zero and negative values are rejected, and a fractional quantity is rejected (items are sold whole).
Skipped rows are listed with their reason in the report.

**Result:** 50 rows read, 47 used, 3 skipped (S-3030, S-3035, S-3039).

<!-- ## Tie-breaking -->

top_n sorts with the key (revenue, product_name): highest revenue first, and if two products have exactly
equal revenue, alphabetical order decides. This makes the ranking deterministic. (No ties occur in this data.)

<!-- ## Assumptions -->

Revenue = quantity × unit price; no discounts, tax or returns appear in the data.
The threshold is at or above KES 50,000 (`>=`), as in the starter docstring.
Skipped rows are excluded from every figure, so reported revenue is a **lower bound**: the three skipped
sales could add roughly KES 13k–65k each depending on what was actually sold.
Product, store and payment names are consistent in this file, so no name normalisation was needed.
<!-- 
## Files -->

```
day2-sales-analytics/
├── sales_analysis.py
├── data/electronics_sales.csv
├── output/sales_report.txt
├── requirements.txt
└── README.md
```
