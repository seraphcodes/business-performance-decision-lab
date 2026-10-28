// Usage: node tests/js_scenario_check.js <cases.json>  -> prints JSON results for each case.
const fs = require("fs");
const path = require("path");
const S = require(path.join(__dirname, "..", "web", "js", "scenario.js"));
const cases = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
const out = cases.map((c) => {
  const r = S.scenario(c.base, c.price, c.volume, c.cost);
  return { net: r.net, cost: r.cost, profit: r.profit, profit_change: r.profit_change,
           breakeven: S.breakevenVolumePct(c.price, c.cost) };
});
const monthly = cases[0].monthly;
const b = S.baseline(monthly, 2);
process.stdout.write(JSON.stringify({ out, baseline: b }));
