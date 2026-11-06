# -*- coding: utf-8 -*-
"""Recalculate the reviewed contribution ledger without network access.

python3 contributions/recalculate.py --check
python3 contributions/recalculate.py --write

Ratings are manual, evidence-backed judgments. This script validates and adds
them; it does not infer value from comment length, counts or code size.
"""

import argparse
import hashlib
import itertools
import json
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path


HERE = Path(__file__).resolve().parent


def instant(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def rank_and_share(scores):
    """Competition ranks; largest remainder allocates exactly 1000 tenths."""
    scores = {name: score for name, score in scores.items() if score > 0}
    total = sum(scores.values())
    if not total:
        return []
    order = sorted(scores, key=lambda name: (-scores[name], name.casefold()))
    units = {name: scores[name] * 1000 // total for name in order}
    remainder_order = sorted(
        order, key=lambda name: (-(scores[name] * 1000 % total), name.casefold())
    )
    for name in remainder_order[:1000 - sum(units.values())]:
        units[name] += 1
    rows = []
    for name in order:
        rows.append({
            "person": name,
            "rank": 1 + sum(score > scores[name] for score in scores.values()),
            "points": scores[name],
            "share_tenths": units[name],
        })
    assert sum(row["share_tenths"] for row in rows) == 1000
    return rows


def aggregate(items, weights):
    scores = defaultdict(int)
    dimensions = defaultdict(lambda: [0, 0, 0, 0])
    counts = defaultdict(int)
    for item in items:
        if item.get("status") == "pending_allocation":
            continue
        name = item["person"]
        counts[name] += 1
        scores[name] += sum(a * b for a, b in zip(item["dimensions"], weights))
        for i, value in enumerate(item["dimensions"]):
            dimensions[name][i] += value
    rows = rank_and_share(scores)
    for row in rows:
        name = row["person"]
        row["dimensions"] = dimensions[name]
        row["weighted_dimensions"] = [a * b for a, b in zip(dimensions[name], weights)]
        row["case_count"] = counts[name]
        row["mean_points"] = round(row["points"] / counts[name], 2)
    return rows


def sensitivity(items, weights):
    """16 corner scenarios of independently varying each weight by +/-20%."""
    ranks = defaultdict(list)
    scenarios = []
    for factors in itertools.product((4, 6), repeat=4):
        # Weights are multiplied by five so all calculations stay integral.
        varied = [a * b for a, b in zip(weights, factors)]
        rows = aggregate(items, varied)
        scenarios.append({"weight_factors_fifths": list(factors),
                          "order": [row["person"] for row in rows]})
        for row in rows:
            ranks[row["person"]].append(row["rank"])
    return {"scenarios": scenarios, "rank_ranges": {
        name: [min(values), max(values)] for name, values in ranks.items()
    }}


def validate(data):
    end = instant(data["snapshot"])
    ids = set()
    claimed_ranges = defaultdict(list)
    source_groups = defaultdict(list)
    assert data["project_weights"] == [2, 3, 2, 1]
    assert data["maintenance_weights"] == [2, 2, 1, 1]
    for kind, bounds, weights in (
        ("project", [5, 5, 5, 3], data["project_weights"]),
        ("maintenance", [4, 4, 3, 2], data["maintenance_weights"]),
    ):
        for item in data[kind]:
            assert item["id"] not in ids, item["id"]
            ids.add(item["id"])
            assert item["person"] != "powerycy" and "[bot]" not in item["person"]
            assert len(item["dimensions"]) == 4
            assert all(isinstance(v, int) and 0 <= v <= bound
                       for v, bound in zip(item["dimensions"], bounds)), item["id"]
            assert item["points"] == sum(a * b for a, b in zip(item["dimensions"], weights)), item["id"]
            assert item["reason"] and item["title"]
            if kind == "project":
                assert len(set(item["source_prs"])) == len(item["source_prs"])
                assert sum(a["points"] for a in item["adoptions"]) == item["points"]
                for adoption in item["adoptions"]:
                    assert 0 <= adoption["points"] <= item["points"]
                    assert instant(adoption["adopted_at"]) <= end
                    meta = data["adoption_metadata"][str(adoption["pr"])]
                    assert meta["merged_at"], item["id"]
                assert (item["points"] == 0) == (item["status"] == "pending_allocation")
            else:
                name = item["person"]
                start = instant(data["maintenance_coverage"][name]["start"] + "T00:00:00+08:00")
                assert item["points"] > 0 and item["evidence"], item["id"]
                for number in item["source_prs"]:
                    assert number not in data["known_own_or_coimplemented"][name], item["id"]
                    assert data["pr_metadata"][str(number)]["author"].casefold() != name.casefold(), item["id"]
                for ev in item["evidence"]:
                    assert ev["author"].casefold() == name.casefold(), (item["id"], ev["id"])
                    assert start <= instant(ev["created_at"]) <= end, (item["id"], ev["id"])
                    assert ev["url"].startswith(data["repository"] + "/")
                    assert ev["text"].strip()
                # Full records remain available for coverage; only these exact
                # source ranges support scoring. Changing a title or row ID
                # cannot make the same person's source passage reusable.
                evidence = {ev["url"]: ev for ev in item["evidence"]}
                assert item["scoring_evidence"], item["id"]
                for claim in item["scoring_evidence"]:
                    assert claim["url"] in evidence, item["id"]
                    lo, hi = claim["start"], claim["end"]
                    body = evidence[claim["url"]]["text"]
                    assert isinstance(lo, int) and isinstance(hi, int)
                    assert 0 <= lo < hi <= len(body), item["id"]
                    assert claim["excerpt"] == body[lo:hi], item["id"]
                    key = (name.casefold(), claim["url"])
                    for other_lo, other_hi, other_id in claimed_ranges[key]:
                        assert hi <= other_lo or lo >= other_hi, (item["id"], other_id, "overlapping evidence")
                    claimed_ranges[key].append((lo, hi, item["id"]))
                group = (name, tuple(sorted(item["source_prs"])), tuple(sorted(item["source_issues"])))
                source_groups[group].append(item["id"])
    for group in source_groups.values():
        if len(group) > 1:
            assert all(data["split_maintenance_scopes"].get(key) for key in group), group
    # Independent goals may share a review, but cannot repeat the same rationale.
    for kind in ("project", "maintenance"):
        keys = [(r["person"], r["title"]) for r in data[kind]]
        assert len(keys) == len(set(keys)), kind
    for name, stats in data["maintenance_coverage"].items():
        items = [r for r in data["maintenance"] if r["person"] == name]
        prs = {n for r in items for n in r["source_prs"]}
        issues = {n for r in items for n in r["source_issues"]}
        evidence = {ev["url"]: ev for r in items for ev in r["evidence"]}
        local = timezone(timedelta(hours=8))
        days = {instant(ev["created_at"]).astimezone(local).date().isoformat()
                for ev in evidence.values()}
        assert stats["case_count"] == len(items)
        assert stats["pr_count"] == len(prs)
        assert stats["issue_count"] == len(issues)
        assert stats["active_days"] == len(days)
        assert stats["active_dates"] == sorted(days)
        assert stats["issue_reply_records"] == sum(ev["kind"] == "issues" for ev in evidence.values())
        assert stats["review_records"] == sum(bool(ev["review_state"]) and ev["kind"] == "pull" for ev in evidence.values())
        assert stats["pr_count"] == stats["merged_prs"] + stats["open_prs"] + stats["closed_unmerged_prs"]
    return len(ids)


def calculate(data):
    validate(data)
    project = aggregate(data["project"], data["project_weights"])
    maintenance = aggregate(data["maintenance"], data["maintenance_weights"])
    recent_scores = defaultdict(int)
    recent_counts = defaultdict(int)
    start, end = instant(data["recent_start"]), instant(data["snapshot"])
    for item in data["project"]:
        points = sum(a["points"] for a in item["adoptions"]
                     if start <= instant(a["adopted_at"]) <= end)
        if points:
            recent_scores[item["person"]] += points
            recent_counts[item["person"]] += 1
    recent = rank_and_share(recent_scores)
    for row in recent:
        row["case_count"] = recent_counts[row["person"]]
    for row in maintenance:
        row["coverage"] = data["maintenance_coverage"][row["person"]]
    return {
        "snapshot": data["snapshot"], "main_sha": data["main_sha"],
        "project": project, "project_recent": recent, "maintenance": maintenance,
        "project_total": sum(r["points"] for r in project),
        "project_recent_total": sum(r["points"] for r in recent),
        "maintenance_total": sum(r["points"] for r in maintenance),
        "project_pending": [r for r in data["project"] if r["status"] == "pending_allocation"],
        "sensitivity": {"project": sensitivity(data["project"], data["project_weights"]),
                        "maintenance": sensitivity(data["maintenance"], data["maintenance_weights"])},
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ledger", type=Path, default=HERE / "2026-10-31.json")
    parser.add_argument("--check", action="store_true", help="also check the saved calculation matches")
    parser.add_argument("--write", action="store_true", help="save the recalculated result")
    args = parser.parse_args()
    raw = args.ledger.read_bytes()
    result = calculate(json.loads(raw))
    result["ledger_sha256"] = hashlib.sha256(raw).hexdigest()
    target = args.ledger.with_name(args.ledger.stem + "-results.json")
    if args.write:
        target.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.check:
        assert json.loads(target.read_text(encoding="utf-8")) == result, "Saved results are stale"
    for board in ("maintenance", "project", "project_recent"):
        print(board, "total", sum(r["points"] for r in result[board]), "people", len(result[board]))
        for row in result[board][:10]:
            print(row["rank"], row["person"], row["points"],
                  str(row["share_tenths"] / 10) + "%", row["case_count"])
    print("Ledger validation passed")


if __name__ == "__main__":
    main()
