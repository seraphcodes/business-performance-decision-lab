/* What-if arithmetic: a line-for-line port of src/scenario.py (see its docstring).
   Accounting, not forecasting: price, volume and cost share are user inputs. */
(function (root) {
  "use strict";

  function baseline(monthly, months) {
    months = months || 12;
    var full = monthly.filter(function (m) { return !m.is_partial_month; })
      .sort(function (a, b) { return a.year_month < b.year_month ? -1 : 1; })
      .slice(-months);
    if (!full.length) throw new Error("No full months available for a baseline.");
    var gross = 0, cancelled = 0;
    full.forEach(function (m) { gross += m.gross_product_sales; cancelled += m.cancellation_value; });
    return {
      gross: gross, cancellations: cancelled, net: gross + cancelled,
      cancellation_rate: gross ? -cancelled / gross : 0,
      first_month: full[0].year_month, last_month: full[full.length - 1].year_month,
      months: full.length
    };
  }

  function scenario(base, pricePct, volumePct, costSharePct) {
    var price = pricePct / 100, volume = volumePct / 100, cost = costSharePct / 100;
    var gross = base.gross * (1 + price) * (1 + volume);
    var net = gross * (1 - base.cancellation_rate);
    var costTotal = cost * base.net * (1 + volume);
    var profit = net - costTotal;
    var baseProfit = base.net * (1 - cost);
    return {
      gross: gross, net: net, cost: costTotal, profit: profit,
      net_change: net - base.net, profit_change: profit - baseProfit, base_profit: baseProfit
    };
  }

  function breakevenVolumePct(pricePct, costSharePct) {
    var price = pricePct / 100, cost = costSharePct / 100;
    var oldMargin = 1 - cost, newMargin = (1 + price) - cost;
    if (newMargin <= 0) return null;
    return (oldMargin / newMargin - 1) * 100;
  }

  function sensitivity(base, prices, volumes, costSharePct) {
    return prices.map(function (p) {
      return volumes.map(function (v) { return scenario(base, p, v, costSharePct).profit_change; });
    });
  }

  var api = { baseline: baseline, scenario: scenario, breakevenVolumePct: breakevenVolumePct, sensitivity: sensitivity };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.Scenario = api;
})(typeof window !== "undefined" ? window : this);
