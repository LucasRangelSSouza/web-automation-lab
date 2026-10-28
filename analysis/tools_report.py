"""Per-tool report for the sandbox suite: attempts and outcomes, failure classes, footprint of the last successful run, metrics each test printed."""
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from common import BLUE, GREEN, GREY, ORANGE, RED, read, save_fig, save_table, update_summary
from config import TOOL_IDS

att = read("sandbox_attempts.csv")
att = att[att.tool_id.isin(TOOL_IDS)].copy()
att["ok"] = att.status == "ok"
HARNESS = {"python command missing in the sandbox", "pip blocked by the system Python"}
att["harness_failure"] = att.failure_class.isin(HARNESS)
order = list(TOOL_IDS)

per = att.groupby("tool_id").agg(name=("tool_name", "first"), tier=("tier", "first"), attempts=("ok", "size"), successes=("ok", "sum"), harness_failures=("harness_failure", "sum"), other_failures=("ok", lambda s: int((~s).sum()))).reindex(order)
per["other_failures"] = per.other_failures - per.harness_failures
last = att[att.ok].sort_values("t_utc").groupby("tool_id").tail(1).set_index("tool_id")
per = per.join(last[["wall_s", "peak_rss_mb", "disk_mb"]])
save_table(per.round(1), "tools_outcome_and_footprint")

fails = att[~att.ok].groupby(["tool_id", "failure_class"]).size().unstack(fill_value=0).reindex(order).fillna(0).astype(int)
save_table(fails, "failure_classes_by_tool")

m = read("sandbox_metrics.csv")
m = m[m.id.isin(TOOL_IDS)].copy()
m["value_num"] = pd.to_numeric(m.value, errors="coerce")
save_table(m[["tool", "id", "metric", "value", "wall_s", "peak_rss_mb"]], "metrics_printed_by_the_tests", index=False)

fig, axes = plt.subplots(1, 2, figsize=(12, 4))
y = np.arange(len(per))
axes[0].barh(y, per.successes, color=GREEN, label="succeeded")
axes[0].barh(y, per.harness_failures, left=per.successes, color=ORANGE, label="failed: my harness (no python / pip blocked)")
axes[0].barh(y, per.other_failures, left=per.successes + per.harness_failures, color=RED, label="failed: other")
axes[0].set_yticks(y)
axes[0].set_yticklabels(per.name, fontsize=8)
axes[0].invert_yaxis()
axes[0].set_xlabel("Attempts")
axes[0].legend(frameon=False, fontsize=7)
f = per.dropna(subset=["peak_rss_mb"])
axes[1].scatter(f.disk_mb.clip(lower=1), f.peak_rss_mb.clip(lower=1), s=np.clip(f.wall_s, 5, 400), color=BLUE, alpha=0.6)
for n, r in f.iterrows():
    axes[1].annotate(r["name"], (max(r.disk_mb, 1), max(r.peak_rss_mb, 1)), xytext=(5, 4), textcoords="offset points", fontsize=7)
axes[1].set_xscale("log")
axes[1].set_yscale("log")
axes[1].set_xlabel("Disk used (MB)")
axes[1].set_ylabel("Peak memory (MB)")
axes[1].set_title("Footprint of the last successful run (size ~ wall time)", fontsize=9)
save_fig(fig, "tools_outcome_and_footprint.png")

summary = {"tools": len(order), "tools_with_success": int((per.successes > 0).sum()), "attempts": len(att), "attempts_ok": int(att.ok.sum()),
           "harness_failures": int(att.harness_failure.sum()), "other_failures": int((~att.ok & ~att.harness_failure).sum())}
for r in m.itertuples():
    if pd.notna(r.value_num):
        summary[f"m_{r.id}_{r.metric}"] = float(r.value_num)
for tid, r in per.iterrows():
    summary[f"wall_{tid}"] = None if pd.isna(r.wall_s) else float(r.wall_s)
    summary[f"rss_{tid}"] = None if pd.isna(r.peak_rss_mb) else float(r.peak_rss_mb)
    summary[f"disk_{tid}"] = None if pd.isna(r.disk_mb) else float(r.disk_mb)
update_summary(summary)
print(per.round(1))
