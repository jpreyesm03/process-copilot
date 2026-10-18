"""Stream-parse BPI 2019 XES -> stats JSON + events CSV.gz (stdlib only).
usage: python3 -I parse_xes.py <xes> <out_csv_gz> <out_stats_json>
"""

import csv
import gzip
import json
import sys
import time
import xml.etree.ElementTree as ET
from collections import Counter

xes, out_csv, out_stats = sys.argv[1:4]
TRACE_COLS = [
    "concept:name",
    "Purchasing Document",
    "Item",
    "Item Type",
    "Item Category",
    "GR-Based Inv. Verif.",
    "Goods Receipt",
    "Source",
    "Purch. Doc. Category name",
    "Company",
    "Spend classification text",
    "Spend area text",
    "Sub spend area text",
    "Vendor",
    "Name",
    "Document Type",
]
EVENT_COLS = [
    "concept:name",
    "time:timestamp",
    "org:resource",
    "User",
    "Cumulative net worth (EUR)",
    "eventID ",
]
OUT_HEADER = ["case_id", "activity", "timestamp", "resource", "user", "cum_net_worth_eur", "event_id"] + [
    "case_" + c.replace(":", "_").replace(" ", "_").replace(".", "").replace("-", "_").lower()
    for c in TRACE_COLS[1:]
]


def local(tag):
    return tag.rsplit("}", 1)[-1]


t0 = time.time()
trace_keys, event_keys = Counter(), Counter()
acts = Counter()
cats = Counter()
n_traces = n_events = 0
tmin = tmax = None
example = None
ev_per_trace = []
fo = gzip.open(out_csv, "wt", newline="", compresslevel=5)
w = csv.writer(fo)
w.writerow(OUT_HEADER)

depth_trace = False
cur_trace = {}
cur_events = []
for evt, el in ET.iterparse(xes, events=("start", "end")):
    tag = local(el.tag)
    if evt == "start":
        if tag == "trace":
            depth_trace = True
            cur_trace = {}
            cur_events = []
        continue
    if tag == "event":
        e = {}
        for ch in el:
            k = ch.get("key")
            if k is not None:
                e[k] = ch.get("value")
                event_keys[k] += 1
        cur_events.append(e)
        el.clear()
    elif tag == "trace":
        for ch in el:
            if local(ch.tag) != "event" and ch.get("key") is not None:
                cur_trace[ch.get("key")] = ch.get("value")
                trace_keys[ch.get("key")] += 1
        n_traces += 1
        ev_per_trace.append(len(cur_events))
        cats[cur_trace.get("Item Category")] += 1
        cid = cur_trace.get("concept:name")
        tvals = [cur_trace.get(c) for c in TRACE_COLS[1:]]
        for e in cur_events:
            n_events += 1
            a = e.get("concept:name")
            acts[a] += 1
            ts = e.get("time:timestamp")
            if ts:
                if tmin is None or ts < tmin:
                    tmin = ts
                if tmax is None or ts > tmax:
                    tmax = ts
            w.writerow(
                [
                    cid,
                    a,
                    ts,
                    e.get("org:resource"),
                    e.get("User"),
                    e.get("Cumulative net worth (EUR)"),
                    e.get("eventID ") or e.get("eventID"),
                ]
                + tvals
            )
        if example is None and 5 <= len(cur_events) <= 12:
            example = {"trace": cur_trace, "events": cur_events}
        el.clear()
        depth_trace = False
fo.close()
ev_per_trace.sort()
stats = {
    "seconds": round(time.time() - t0, 1),
    "n_traces": n_traces,
    "n_events": n_events,
    "n_activities": len(acts),
    "ts_min_lexical": tmin,
    "ts_max_lexical": tmax,
    "events_per_trace_median": ev_per_trace[len(ev_per_trace) // 2] if ev_per_trace else None,
    "events_per_trace_max": ev_per_trace[-1] if ev_per_trace else None,
    "trace_attr_keys": dict(trace_keys),
    "event_attr_keys": dict(event_keys),
    "item_category_counts": dict(cats),
    "activities": acts.most_common(),
    "example": example,
}
json.dump(stats, open(out_stats, "w"), indent=1, default=str)
print("done", stats["seconds"], n_traces, n_events)
