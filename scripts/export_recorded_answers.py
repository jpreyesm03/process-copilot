"""Export passing answers from an eval run as the app's recorded examples (shown when the live model is unavailable).

Usage: python scripts/export_recorded_answers.py evals/runs/2026-10-18_1859_v3_tlv2_haiku
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "app" / "recorded_answers.json"
SAMPLES = ["desc_01", "time_02", "cyc_01", "vend_02", "case_01", "case_04", "amb_01", "unans_01", "adv_burger"]


def main(run_dir: Path) -> None:
    rows = [json.loads(line) for line in (run_dir / "answers.jsonl").read_text().splitlines()]
    judgments = json.loads((run_dir / "judgments.json").read_text())
    model = json.loads((run_dir / "meta.json").read_text())["model"]
    recorded = []
    for qid in SAMPLES:
        for r in rows:
            key = f"{r['id']}#{r['repeat']}"
            judged_ok = judgments.get(key, {}).get("pass", True)
            if r["id"] == qid and r["auto"]["ok"] and judged_ok and not r.get("flagged"):
                recorded.append({
                    "question": r["question"], "answer": r["answer"],
                    "steps": [{"tool": s["tool"], "args": s["args"]} for s in r["steps"]],
                    "model": model, "run": run_dir.name, "latency_ms": r["latency_ms"],
                })
                break
    OUT.write_text(json.dumps(recorded, indent=1, ensure_ascii=False))
    print(f"wrote {len(recorded)} of {len(SAMPLES)} answers to {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main(Path(sys.argv[1]))
