"""Export the verified metric views to a small file for the static web frontend.

    python -m src.export_web

Reads data/processed/retail.db (read-only), re-checks that the views still add up to
the reconciliation bridge, and writes web/data/metrics.js (plus metrics.json).
The frontend is plain HTML/CSS/JS: it only displays this file, so the numbers on
the web pages are the numbers the build already reconciled.

Aggregates only (no transaction rows), so the output is small and safe to publish.
"""
import argparse
import json
import sys
from pathlib import Path

import pandas as pd

from src import metrics
from src.config import DATABASE, PROJECT_ROOT
from src.reconcile import ReconciliationError

WEB_DATA = PROJECT_ROOT / "web" / "data"
TOLERANCE = 0.005
DOCS = {"cleaning_rules": "cleaning_rules.md", "metrics": "metrics.md"}


def _records(frame):
    """DataFrame -> list of plain dicts (NaN becomes null, numpy types become Python)."""
    return json.loads(frame.to_json(orient="records"))


def _bridge_value(bridge, label_part):
    rows = bridge[bridge["label"].str.contains(label_part, regex=False)]
    if len(rows) != 1:
        raise ReconciliationError(f"Bridge row not found exactly once: {label_part!r}")
    return float(rows["value"].iloc[0])


def verify(monthly, countries, products_all, bridge):
    """The exported tables must tie to the reconciliation bridge (unrounded values)."""
    gross = _bridge_value(bridge, "Gross product sales")
    cancel = _bridge_value(bridge, "Cancellation value")
    net = _bridge_value(bridge, "Net product revenue")
    checks = [
        ("monthly gross", monthly["gross_product_sales"].sum(), gross),
        ("monthly cancellations", monthly["cancellation_value"].sum(), cancel),
        ("monthly net", monthly["net_product_revenue"].sum(), net),
        ("countries net", countries["net_product_revenue"].sum(), net),
        ("products net", products_all["net_sales"].sum(), net),
    ]
    problems = [f"{name}: {got:,.2f} vs bridge {want:,.2f}" for name, got, want in checks
                if abs(got - want) > TOLERANCE]
    if problems:
        raise ReconciliationError("Export refused, views no longer tie to the bridge: " + "; ".join(problems))
    return [{"name": name, "passed": True, "detail": f"{got:,.2f}"} for name, got, _ in checks]


def build_payload(database=DATABASE, top_n=20, docs_dir=None):
    docs_dir = Path(docs_dir) if docs_dir else PROJECT_ROOT / "docs"
    monthly = metrics.monthly_revenue(database, include_partial=True)
    countries = metrics.country_revenue(database)
    products_all = metrics.read_view("SELECT * FROM v_top_products ORDER BY sales_rank, stock_code", database)
    bridge = metrics.read_view("SELECT step, label, rows, value FROM reconciliation", database)
    checks = verify(monthly, countries, products_all, bridge)

    kpis = metrics.headline_kpis(database)
    info = metrics.read_view("SELECT key, value FROM build_metadata", database).set_index("key")["value"]
    docs = {}
    for key, name in DOCS.items():
        path = docs_dir / name
        docs[key] = path.read_text(encoding="utf-8") if path.is_file() else ""

    def money(frame):
        out = frame.copy()
        for column in out.columns:
            if pd.api.types.is_float_dtype(out[column]):
                out[column] = out[column].round(4 if "pct" in column else 2)
        return out

    return {
        "meta": {
            "dataset": "Online Retail II, UCI Machine Learning Repository (Chen, 2012), CC BY 4.0",
            "doi": "https://doi.org/10.24432/C5CG6D",
            "currency": "GBP",
            "built_at": info.get("built_at", ""),
            "source_file": info.get("source_file", ""),
            "source_sha256": info.get("source_sha256", ""),
            "reconciliation_checks_passed": info.get("reconciliation_checks_passed", ""),
            "export_checks": checks,
        },
        "kpis": {key: round(float(value), 4) for key, value in kpis.items()},
        "monthly": _records(money(monthly)),
        "services": _records(money(metrics.monthly_service_lines(database))),
        "products": _records(money(products_all.head(top_n))),
        "countries": _records(money(countries)),
        "coverage": _records(money(metrics.customer_coverage(database))),
        "bridge": _records(money(bridge)),
        "docs": docs,
    }


def write(payload, out_dir=WEB_DATA):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, ensure_ascii=False, indent=1)
    (out_dir / "metrics.json").write_text(text, encoding="utf-8")
    # A .js file (not fetch) so the site also works when index.html is opened from disk.
    (out_dir / "metrics.js").write_text("window.METRICS = " + text + ";\n", encoding="utf-8")
    return out_dir / "metrics.js"


def main(argv=None):
    parser = argparse.ArgumentParser(description="Export metrics for the static web frontend.")
    parser.add_argument("--database", default=str(DATABASE))
    parser.add_argument("--out", default=str(WEB_DATA))
    args = parser.parse_args(argv)
    try:
        payload = build_payload(args.database)
        path = write(payload, args.out)
    except (ReconciliationError, FileNotFoundError) as error:
        sys.exit(f"\nEXPORT STOPPED: {error}")
    print(f"Wrote {path} ({path.stat().st_size / 1024:.0f} KB). "
          f"Months: {len(payload['monthly'])}, products: {len(payload['products'])}, "
          f"countries: {len(payload['countries'])}.")


if __name__ == "__main__":
    main()
