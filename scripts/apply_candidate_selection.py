"""Apply the 2026-10-14 batch decision: promote >=64 scored jobs to ready, reject off-target ones.

Rationale
---------
The user asked for ~100 candidates and approved widening the pool from the default
threshold (71) down to 64, excluding postings whose direction does not match their
C++ / backend / embedded / server target.

Two deliberate carve-outs that the raw keyword rules would have wrongly dropped:
  * 安凯微电子 "2027届校招岗-嵌入式软件/测试" — a mixed campus posting that includes 嵌入式软件
  * 万宝盛华 "软件开发/测试工程师" — 软件开发 leads, 测试 is one of several tracks

Both stay in the pool. Run with --dry-run to preview without touching the DB.
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from bosshunter.config import load_config  # noqa: E402
from bosshunter.db import get_db, update_jobs_manual_status  # noqa: E402

MIN_SCORE = 64

# (company fragment, title fragment) — matched with LIKE, unique within the pool
REJECT = [
    ("六联智能", "商务/销售"),
    ("迅雷网络", "客户端开发-iOS"),
    ("要务科技", "全栈工程师"),
    ("上海从鲸信息技术", "ios开发工程师"),
    ("凡岛", "AI技术经理"),
    ("上海从鲸信息技术", "java后端工程师"),
    ("树根互联", "AI全栈"),
    ("深蓝互动", "Java开发工程师"),
    ("杉岩数据", "python/golang"),
    ("阿里巴巴集团", "2025届"),
    ("上海万宝盛华信息科技", "测试"),
    ("广东火丁科技", "mes高级"),
    ("辛孚科技", "python后端"),
]


def resolve_reject_ids(conn: sqlite3.Connection) -> tuple[list[str], list[str]]:
    ids: list[str] = []
    missing: list[str] = []
    for company, title in REJECT:
        row = conn.execute(
            """SELECT id FROM jobs
               WHERE deleted_at IS NULL
                 AND status IN ('ready', 'filtered')
                 AND score >= ?
                 AND company LIKE ?
                 AND title LIKE ?""",
            (MIN_SCORE, f"%{company}%", f"%{title}%"),
        ).fetchone()
        if row is None:
            missing.append(f"{company} / {title}")
        else:
            ids.append(str(row["id"]))
    return ids, missing


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    config = load_config("config.yaml")
    db_path = Path(config.get("db_path") or "data/bosshunter.db")
    conn = get_db(db_path)
    try:
        reject_ids, missing = resolve_reject_ids(conn)
        if missing:
            print("[!] 以下剔除目标未命中，请人工确认：")
            for item in missing:
                print("   ", item)

        promote = [
            str(row["id"])
            for row in conn.execute(
                """SELECT id FROM jobs
                   WHERE deleted_at IS NULL AND status = 'filtered' AND score >= ?
                   ORDER BY score DESC""",
                (MIN_SCORE,),
            ).fetchall()
            if str(row["id"]) not in set(reject_ids)
        ]

        current_ready = conn.execute(
            "SELECT COUNT(*) FROM jobs WHERE status = 'ready' AND deleted_at IS NULL"
        ).fetchone()[0]
        demoted = len(
            [
                i
                for i in reject_ids
                if conn.execute(
                    "SELECT status FROM jobs WHERE id = ?", (i,)
                ).fetchone()[0]
                == "ready"
            ]
        )

        print(f"剔除（→ rejected）: {len(reject_ids)}（其中 {demoted} 个原为 ready）")
        print(f"提升（filtered → ready）: {len(promote)}")
        print(f"预期最终 ready: {current_ready - demoted + len(promote)}")

        if args.dry_run:
            print("\n[dry-run] 未修改数据库。")
            return 0

        if reject_ids:
            result = update_jobs_manual_status(conn, reject_ids, "rejected")
            print(f"已剔除: {result['affected_count']} 个")
        if promote:
            result = update_jobs_manual_status(conn, promote, "ready")
            print(f"已提升: {result['affected_count']} 个")

        final_ready = conn.execute(
            "SELECT COUNT(*) FROM jobs WHERE status = 'ready' AND deleted_at IS NULL"
        ).fetchone()[0]
        print(f"\n最终 ready 数量: {final_ready}")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
