"""What-if arithmetic for the simulator page. Pure functions, no I/O, no prediction.

Everything here is *accounting*, not forecasting:
  * the baseline comes from the data (last 12 full months);
  * price change, volume change and the cost share are INPUTS chosen by the user;
  * the data has no product costs, so profit exists only through the cost-share
    assumption. Revenue effects are grounded in the data, profit effects are not.
  * nothing here says how volume would react to a price change (no elasticity).

Model (all relative to the baseline period):
  gross_new   = gross * (1 + price) * (1 + volume)
  net_new     = gross_new * (1 - cancellation_rate)      (rate held at its baseline value)
  cost_new    = cost_share * net_base * (1 + volume)     (unit cost unchanged, units follow volume)
  profit_new  = net_new - cost_new
"""
import pandas as pd


def baseline(monthly, months=12):
    """Totals over the last `months` full months of the monthly table."""
    full = monthly[monthly["is_partial_month"] == 0].sort_values("year_month").tail(months)
    if full.empty:
        raise ValueError("No full months available for a baseline.")
    gross = float(full["gross_product_sales"].sum())
    cancelled = float(full["cancellation_value"].sum())
    return {
        "gross": gross,
        "cancellations": cancelled,
        "net": gross + cancelled,
        "cancellation_rate": (-cancelled / gross) if gross else 0.0,
        "first_month": full["year_month"].iloc[0],
        "last_month": full["year_month"].iloc[-1],
        "months": int(len(full)),
    }


def scenario(base, price_pct, volume_pct, cost_share_pct):
    """Revenue, cost and profit for one scenario. Percent arguments are in percent (10 = +10%)."""
    price, volume, cost_share = price_pct / 100, volume_pct / 100, cost_share_pct / 100
    gross = base["gross"] * (1 + price) * (1 + volume)
    net = gross * (1 - base["cancellation_rate"])
    cost = cost_share * base["net"] * (1 + volume)
    profit = net - cost
    base_profit = base["net"] * (1 - cost_share)
    return {
        "gross": gross, "net": net, "cost": cost, "profit": profit,
        "net_change": net - base["net"],
        "profit_change": profit - base_profit,
        "base_profit": base_profit,
    }


def breakeven_volume_pct(price_pct, cost_share_pct):
    """Volume change (in percent) that leaves profit unchanged after a price change.

    None if the new unit margin is zero or negative (no volume increase can compensate).
    """
    price, cost_share = price_pct / 100, cost_share_pct / 100
    old_margin = 1 - cost_share
    new_margin = (1 + price) - cost_share
    if new_margin <= 0:
        return None
    return (old_margin / new_margin - 1) * 100


def sensitivity(base, price_values, volume_values, cost_share_pct):
    """Profit change (GBP) for every price x volume pair, as a DataFrame (rows = price)."""
    grid = [[scenario(base, p, v, cost_share_pct)["profit_change"] for v in volume_values]
            for p in price_values]
    return pd.DataFrame(grid, index=list(price_values), columns=list(volume_values))
