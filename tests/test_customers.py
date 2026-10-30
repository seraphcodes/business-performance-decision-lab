"""Tests for the customer views (cohort retention, RFM, concentration).

Everything is worked out by hand from one tiny sheet (one line per invoice,
price 1.0, so quantity = value). Customers:

  A 1001  2010-01-10 £10, 2010-02-15 £20, 2010-04-05 £30, 2010-05-02 £5   (4 orders, £65)
  B 1002  2010-01-20 £40                                                   (1 order,  £40)
  C 1003  2010-02-03 £5,  2010-03-09 £15                                   (2 orders, £20)
  D 1004  2010-03-12 £100, 2010-04-20 £50                                  (2 orders, £150)
  E 1005  2010-05-08 £25                                                   (1 order,  £25)
  guest   2010-03-01 £7 (no customer ID)

The data ends on 8 May, so May 2010 is a PARTIAL month. Gross = 307, of which 300 has a customer.
Snapshot day = 2010-05-09.
"""
import pytest

from src import metrics
from src.build_db import build_from_sheets
import pandas as pd
from tests.helpers import raw_row

quiet = lambda *_: None  # noqa: E731

ORDERS = [  # (invoice, customer, date, value)
    ("100001", 1001, "2010-01-10", 10), ("100002", 1001, "2010-02-15", 20),
    ("100003", 1001, "2010-04-05", 30), ("100004", 1001, "2010-05-02", 5),
    ("100005", 1002, "2010-01-20", 40),
    ("100006", 1003, "2010-02-03", 5), ("100007", 1003, "2010-03-09", 15),
    ("100008", 1004, "2010-03-12", 100), ("100009", 1004, "2010-04-20", 50),
    ("100010", 1005, "2010-05-08", 25),
    ("100011", None, "2010-03-01", 7),
]


@pytest.fixture
def db(tmp_path):
    rows = [raw_row(inv, "85123A", "WHITE HEART", value, f"{day} 10:00", 1.0,
                    float(cust) if cust else float("nan"))
            for inv, cust, day, value in ORDERS]
    path = tmp_path / "customers.db"
    build_from_sheets({"S": pd.DataFrame(rows)}, path, baseline=None, log=quiet)
    return path


def test_customer_values(db):
    table = metrics.read_view("SELECT * FROM v_customer_value ORDER BY customer_id", db).set_index("customer_id")
    assert table["orders"].to_dict() == {1001: 4, 1002: 1, 1003: 2, 1004: 2, 1005: 1}
    assert table["gross_value"].round(2).to_dict() == {1001: 65, 1002: 40, 1003: 20, 1004: 150, 1005: 25}
    assert table.loc[1001, "first_month"] == "2010-01"
    assert table.loc[1001, "last_day"] == "2010-05-02"


def test_known_customers_plus_guests_equal_all_gross_sales(db):
    known = metrics.read_view("SELECT SUM(gross_value) AS v FROM v_customer_value", db)["v"][0]
    guest = metrics.read_view("SELECT SUM(gross_without_customer) AS v FROM v_customer_coverage", db)["v"][0]
    assert (round(known, 2), round(guest, 2)) == (300.00, 7.00)


def test_cohort_retention_by_hand(db):
    table = metrics.cohort_retention(db)
    got = {(r.cohort_month, r.months_since): (r.active_customers, r.cohort_customers, r.retention_pct)
           for r in table.itertuples()}
    assert got == {
        ("2010-01", 0): (2, 2, 100.0), ("2010-01", 1): (1, 2, 50.0), ("2010-01", 3): (1, 2, 50.0),
        ("2010-02", 0): (1, 1, 100.0), ("2010-02", 1): (1, 1, 100.0),
        ("2010-03", 0): (1, 1, 100.0), ("2010-03", 1): (1, 1, 100.0),
    }


def test_partial_month_is_not_a_cohort_and_not_activity(db):
    table = metrics.cohort_retention(db)
    assert "2010-05" not in set(table["cohort_month"]) | set(table["activity_month"])


def test_first_month_of_the_data_is_flagged_as_left_censored(db):
    table = metrics.cohort_retention(db)
    flagged = set(table.loc[table["is_left_censored"] == 1, "cohort_month"])
    assert flagged == {"2010-01"}


def test_rfm_scores_and_segments_by_hand(db):
    rfm = metrics.customer_rfm(db).set_index("customer_id")
    assert rfm["recency_days"].to_dict() == {1001: 7, 1002: 109, 1003: 61, 1004: 19, 1005: 1}
    assert rfm["r_score"].to_dict() == {1001: 4, 1002: 1, 1003: 2, 1004: 3, 1005: 5}
    assert rfm["f_score"].to_dict() == {1001: 5, 1002: 2, 1003: 4, 1004: 4, 1005: 2}
    assert rfm["m_score"].to_dict() == {1001: 4, 1002: 3, 1003: 1, 1004: 5, 1005: 2}
    assert rfm["segment"].to_dict() == {1001: "Champions", 1002: "Inactive", 1003: "At risk",
                                        1004: "Loyal", 1005: "Recent"}


def test_customers_with_equal_values_get_equal_scores(tmp_path):
    rows = [raw_row(f"20000{i}", "85123A", "WHITE HEART", 10, "2010-03-05 10:00", 1.0, float(1000 + i))
            for i in range(4)]
    path = tmp_path / "ties.db"
    build_from_sheets({"S": pd.DataFrame(rows)}, path, baseline=None, log=quiet)
    rfm = metrics.customer_rfm(path)
    assert rfm["r_score"].nunique() == rfm["f_score"].nunique() == rfm["m_score"].nunique() == 1


def test_segment_summary_adds_up(db):
    seg = metrics.rfm_segments(db).set_index("segment")
    assert seg["customers"].sum() == 5
    assert seg["gross_value"].sum() == pytest.approx(300.0)
    assert seg["gross_value_pct"].sum() == pytest.approx(100.0)
    assert seg.loc["Champions", "gross_value"] == pytest.approx(65.0)


def test_concentration_by_hand(db):
    # values largest first: 150, 65, 40, 25, 20 (total 300)
    table = metrics.customer_concentration(db, shares=(0.2, 0.4, 1.0)).set_index("top_pct")
    assert table.loc[20.0, "customers"] == 1
    assert table.loc[20.0, "share_of_known_pct"] == pytest.approx(50.0)
    assert table.loc[40.0, "share_of_known_pct"] == pytest.approx(100 * 215 / 300)
    assert table.loc[100.0, "share_of_known_pct"] == pytest.approx(100.0)


def test_a_build_with_no_known_customers_still_works(tmp_path):
    rows = [raw_row("300001", "85123A", "WHITE HEART", 5, "2010-03-05 10:00", 1.0, float("nan"))]
    path = tmp_path / "none.db"
    build_from_sheets({"S": pd.DataFrame(rows)}, path, baseline=None, log=quiet)
    assert metrics.cohort_retention(path).empty
    assert metrics.customer_rfm(path).empty
    assert metrics.rfm_segments(path).empty
    assert metrics.customer_concentration(path)["share_of_known_pct"].eq(0).all()


@pytest.mark.parametrize("seed", [1, 2, 3])
def test_customer_views_match_an_independent_pandas_calculation(seed, tmp_path):
    import random
    rng = random.Random(seed)
    rows = []
    for number in range(400):
        month, day = rng.randint(1, 8), rng.randint(1, 27)
        if month == 8:
            day = min(day, 12)  # data ends mid-August -> August is partial
        customer = rng.choice([None] + [float(1000 + i) for i in range(40)])
        rows.append(raw_row(str(400000 + number), "85123A", "WHITE HEART", rng.randint(1, 30),
                            f"2010-{month:02d}-{day:02d} 10:00", rng.choice([1.0, 2.5, 4.0]),
                            customer if customer is not None else float("nan")))
    path = tmp_path / "rand.db"
    df, _ = build_from_sheets({"S": pd.DataFrame(rows)}, path, baseline=None, log=quiet)

    sales = df[(df["RowClass"] == "normal_sale") & df["CustomerID"].notna()]
    inv = sales.groupby("InvoiceNo").agg(customer=("CustomerID", "first"), day=("InvoiceDay", "first"),
                                         month=("YearMonth", "first"), value=("LineValue", "sum"))
    last_day = df["InvoiceDay"].max()
    partial = set(df.loc[df["IsPartialMonth"], "YearMonth"])

    # concentration
    per_customer = inv.groupby("customer")["value"].sum().sort_values(ascending=False)
    got = metrics.customer_concentration(path, shares=(0.1, 0.25, 0.5)).set_index("top_pct")
    for share in (0.1, 0.25, 0.5):
        k = -(-round(share * len(per_customer), 9) // 1)
        assert got.loc[100 * share, "share_of_known_pct"] == pytest.approx(
            100 * per_customer.head(int(k)).sum() / per_customer.sum(), abs=1e-6)

    # cohorts (full months only)
    first = inv.groupby("customer")["month"].min()
    active = inv[~inv["month"].isin(partial)].groupby(["customer", "month"]).size().reset_index()
    active["cohort"] = active["customer"].map(first)
    active = active[~active["cohort"].isin(partial)]
    expected = active.groupby(["cohort", "month"]).size()
    table = metrics.cohort_retention(path)
    assert len(table) == len(expected)
    for row in table.itertuples():
        assert row.active_customers == expected[(row.cohort_month, row.activity_month)]

    # RFM scores: ties share a score, 5 = best
    rfm = metrics.customer_rfm(path).set_index("customer_id")
    snapshot = pd.Timestamp(last_day) + pd.Timedelta(days=1)
    recency = (snapshot - pd.to_datetime(inv.groupby("customer")["day"].max())).dt.days
    frequency = inv.groupby("customer").size()
    monetary = inv.groupby("customer")["value"].sum()

    def score(series, best_is_high):
        share = series.rank(method="max", pct=True) if best_is_high else (-series).rank(method="max", pct=True)
        return (1 + ((share * 5 - 1e-9).astype(int)))
    for name, series, high in (("r_score", recency, False), ("f_score", frequency, True),
                               ("m_score", monetary, True)):
        want = score(series, high)
        for customer_id, value in want.items():
            assert rfm.loc[int(customer_id), name] == value
