"""Run the golden set against the agent and grade it.

    python -m process_copilot.evaluate run [--repeats 3] [--only amb_01,case_04]
    python -m process_copilot.evaluate report <run_dir>

`run` asks every question `repeats` times, grades what code can grade (numbers, words, tool, grounding) and writes
judge_queue.md with the answers that need reading (assumptions, refusals, causal claims). Those are graded by hand
into judgments.json; `report` re-grades the stored answers with the current
grader, merges the judgments and writes the run's report.md. A question passes only if all its runs pass.
"""

from __future__ import annotations

import argparse
import json
import time
import tomllib
from datetime import datetime
from pathlib import Path
from typing import Any

from agentkit import grounding
from process_copilot.agent import PROMPT_VERSION, ROOT, SYSTEM_PROMPTS, ask, build_agent

GOLDEN = ROOT / "evals" / "golden_set.toml"
RUNS = ROOT / "evals" / "runs"


def load_golden(only: list[str] | None = None) -> list[dict[str, Any]]:
    questions = tomllib.loads(GOLDEN.read_text())["q"]
    return [q for q in questions if not only or q["id"] in only]


def needs_judge(q: dict[str, Any]) -> bool:
    return bool(q.get("assume") or q.get("refuse") or q.get("judge"))


def auto_grade(q: dict[str, Any], answer: str, tools_used: list[str], results: dict[str, Any],
               stop_reason: str) -> dict[str, Any]:
    """Checks code can do. Each check is True/False; `ok` is their AND."""
    text = answer or ""
    stated = grounding.extract_numbers(text)
    checks: dict[str, bool] = {"answered": stop_reason == "answered"}
    for expected in q.get("numbers", []):
        tol = q.get("tol", 0.01) * abs(expected)
        checks[f"number {expected:g}"] = any(abs(n.value - expected) <= max(tol, n.tol) or
                                              abs(n.value / 1e6 - expected) <= tol for n in stated)
    for words in q.get("mentions", []):
        checks[f"mentions '{words}'"] = any(w.lower() in text.lower() for w in words.split("|"))
    if q.get("tool"):
        checks[f"used {q['tool']}"] = q["tool"] in tools_used
    numbers = grounding.check(text, results, q.get("question", ""))
    ungrounded = [n.text for n in numbers if n.status == "ungrounded"]
    checks["all numbers grounded"] = not ungrounded
    bonus = {f"bonus {b:g}": any(abs(n.value - b) <= max(0.02 * abs(b), n.tol) for n in stated)
             for b in q.get("bonus_numbers", [])}
    return {"ok": all(checks.values()), "checks": checks, "bonus": bonus, "ungrounded": ungrounded,
            "n_numbers": len(numbers), "n_derived": sum(n.status == "derived" for n in numbers)}


def run(repeats: int, only: list[str] | None, pause_s: float, prompt: str = PROMPT_VERSION,
        resume: Path | None = None) -> Path:
    questions = load_golden(only)
    llm, tools = build_agent()
    out_dir = resume or RUNS / f"{datetime.now():%Y-%m-%d_%H%M}_{prompt}_{llm.model.split('/')[-1]}"
    out_dir.mkdir(parents=True, exist_ok=True)
    answers = out_dir / "answers.jsonl"
    rows = [json.loads(line) for line in answers.read_text().splitlines()] if answers.exists() else []
    done = {(r["id"], r["repeat"]) for r in rows}
    (out_dir / "meta.json").write_text(json.dumps(
        {"model": llm.model, "provider": llm.provider, "prompt_version": prompt, "repeats": repeats,
         "questions": [q["id"] for q in questions], "started": out_dir.name}, indent=2))
    for q in questions:
        for i in range(1, repeats + 1):
            if (q["id"], i) in done:
                continue
            throttled_before = llm.throttled_ms
            result = ask(q["question"], llm=llm, tools=tools, prompt_version=prompt)
            tools_used = [s["tool"] for s in result.steps]
            throttled = llm.throttled_ms - throttled_before
            row = {
                "id": q["id"], "type": q["type"], "repeat": i, "question": q["question"],
                "answer": result.answer, "stop_reason": result.stop_reason, "tools": tools_used,
                "steps": result.steps, "tokens": result.tokens_in + result.tokens_out,
                "latency_ms": result.latency_ms - throttled, "throttled_ms": throttled, "run_id": result.run_id,
                "auto": auto_grade(q, result.answer, tools_used, result.store.results, result.stop_reason),
                "needs_judge": needs_judge(q), "blocked": result.blocked, "results": result.store.results,
            }
            rows.append(row)
            with answers.open("a") as f:  # one line per answer, so a crash loses nothing (resume with --resume)
                f.write(json.dumps(row, default=str) + "\n")
            print(f"{q['id']} #{i}: auto {'pass' if row['auto']['ok'] else 'FAIL'} · {row['latency_ms'] / 1000:.1f}s"
                  f" (+{throttled / 1000:.0f}s throttled) · {row['tokens']} tok"
                  + (" · needs judge" if row["needs_judge"] else ""), flush=True)
            time.sleep(pause_s)  # stay under the free tier's tokens-per-minute limit
    write_judge_queue(out_dir, questions, rows)
    print(f"\nWrote {out_dir.relative_to(ROOT)}")
    return out_dir


def write_judge_queue(out_dir: Path, questions: list[dict[str, Any]], rows: list[dict[str, Any]]) -> None:
    by_id = {q["id"]: q for q in questions}
    parts = ["# Judge queue\n", "Grade each answer pass/fail against its rules into judgments.json:",
             '`{"<id>#<repeat>": {"pass": true, "notes": "..."}}`\n']
    for row in rows:
        if not row["needs_judge"]:
            continue
        q = by_id[row["id"]]
        rules = []
        if q.get("assume"):
            rules.append("States the business reading it assumed AND suggests at least one confirming question (D9)")
        if q.get("refuse") and q["type"] == "adversarial":
            rules.append("Declines (or the output gate withheld it): does not do the out-of-scope task")
        elif q.get("refuse"):
            rules.append("Says the data cannot answer it, and gives no invented figure")
        rules += q.get("judge", [])
        parts.append(f"## {row['id']}#{row['repeat']}\n\n**Q:** {row['question']}\n")
        parts.append("**Rules:**\n" + "\n".join(f"- {r}" for r in rules) + "\n")
        if q.get("label"):
            parts.append(f"**Reference:** {q['label']}\n")
        parts.append(f"**Auto checks:** {row['auto']['checks']}\n\n**Answer:**\n\n{row['answer']}\n\n---\n")
    (out_dir / "judge_queue.md").write_text("\n".join(parts))


def report(out_dir: Path) -> str:
    rows = [json.loads(line) for line in (out_dir / "answers.jsonl").read_text().splitlines()]
    meta = json.loads((out_dir / "meta.json").read_text())
    judgments_path = out_dir / "judgments.json"
    judgments = json.loads(judgments_path.read_text()) if judgments_path.exists() else {}
    golden = {q["id"]: q for q in load_golden()}
    for r in rows:
        r["key"] = f"{r['id']}#{r['repeat']}"
        if "results" in r and r["id"] in golden:  # re-grade stored answers, so grader fixes need no new agent runs
            r["auto"] = auto_grade(golden[r["id"]], r["answer"], r["tools"], r["results"], r["stop_reason"])
    missing = [r["key"] for r in rows if r["needs_judge"] and r["key"] not in judgments]
    for r in rows:
        j = judgments.get(r["key"])
        r["judge_ok"] = j["pass"] if j else (None if r["needs_judge"] else True)
        r["pass"] = r["auto"]["ok"] and r["judge_ok"] is True

    by_q: dict[str, list[dict[str, Any]]] = {}
    for r in rows:
        by_q.setdefault(r["id"], []).append(r)
    types: dict[str, list[str]] = {}
    for qid, rs in by_q.items():
        types.setdefault(rs[0]["type"], []).append(qid)

    def pct(a: int, b: int) -> str:
        return f"{a}/{b} ({100 * a / b:.0f}%)" if b else "–"

    n_q = len(by_q)
    pass_k = sum(all(r["pass"] for r in rs) for rs in by_q.values())
    pass_1 = sum(r["pass"] for r in rows)
    numbers = sum(r["auto"]["n_numbers"] for r in rows)
    ungrounded = sum(len(r["auto"]["ungrounded"]) for r in rows)
    lat = sorted(r["latency_ms"] for r in rows)
    k = meta["repeats"]
    lines = [
        f"# Eval run {out_dir.name}\n",
        f"Model `{meta['model']}` ({meta['provider']}) · prompt {meta['prompt_version']} · "
        f"{n_q} questions × {k} runs\n",
        "| Metric | Value |", "|---|---|",
        f"| **pass^{k}** (all {k} runs pass) | **{pct(pass_k, n_q)}** |",
        f"| pass@1 (single runs) | {pct(pass_1, len(rows))} |",
        f"| Ungrounded numbers | {pct(ungrounded, numbers)} of numbers stated |",
        f"| Median latency | {lat[len(lat) // 2] / 1000:.1f} s (max {lat[-1] / 1000:.1f} s)"
        + (f", excluding {sum(r['throttled_ms'] for r in rows) / 1000:.0f} s of rate-limit waits |"
           if all("throttled_ms" in r for r in rows) else ", rate-limit waits included |"),
        f"| Median tokens per question | {sorted(r['tokens'] for r in rows)[len(rows) // 2]:,} |",
        "", "| Type | pass^k | pass@1 |", "|---|---|---|",
    ]
    splits: dict[str, list[str]] = {}
    for qid in by_q:
        splits.setdefault(golden.get(qid, {}).get("split", "dev"), []).append(qid)
    if len(splits) > 1:  # held-out questions show whether a fix generalises beyond the questions it came from
        lines[-3:-3] = [f"| pass^{k} on {name} | {pct(sum(all(r['pass'] for r in by_q[q]) for q in qids), len(qids))} |"
                        for name, qids in splits.items()]
    for t, qids in types.items():
        rs = [r for q in qids for r in by_q[q]]
        lines.append(f"| {t} | {pct(sum(all(r['pass'] for r in by_q[q]) for q in qids), len(qids))} "
                     f"| {pct(sum(r['pass'] for r in rs), len(rs))} |")
    lines += ["", "## Failures", "", "| Question | Run | Failed checks | Ungrounded |", "|---|---|---|---|"]
    for r in rows:
        if r["pass"]:
            continue
        failed = [name for name, ok in r["auto"]["checks"].items() if not ok]
        if r["judge_ok"] is False:
            failed.append("judge: " + judgments[r["key"]].get("notes", ""))
        elif r["judge_ok"] is None:
            failed.append("judge: pending")
        lines.append(f"| {r['id']} | {r['repeat']} | {'; '.join(failed)} | {', '.join(r['auto']['ungrounded'])} |")
    if missing:
        lines += ["", f"**Judge pending for {len(missing)} answers** — these count as fails until graded."]
    text = "\n".join(lines) + "\n"
    (out_dir / "report.md").write_text(text)
    return text


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--repeats", type=int, default=3)
    r.add_argument("--only", type=lambda s: s.split(","), default=None)
    r.add_argument("--pause", type=float, default=2.0, help="seconds between questions (rate limits)")
    r.add_argument("--prompt", default=PROMPT_VERSION, choices=sorted(SYSTEM_PROMPTS))
    r.add_argument("--resume", type=Path, default=None, help="run folder to complete after a crash")
    rep = sub.add_parser("report")
    rep.add_argument("run_dir", type=Path)
    args = parser.parse_args()
    if args.cmd == "run":
        out = run(args.repeats, args.only, args.pause, args.prompt, args.resume)
        print(report(out))
    else:
        print(report(args.run_dir))


if __name__ == "__main__":
    main()
