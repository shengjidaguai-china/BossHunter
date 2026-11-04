"""Send every ready job: fixed greeting first, then the greeting plus resume images.

Why this exists: ``bosshunter greet`` only looks at ``approved`` jobs, while jobs
that cleared scoring sit in ``ready`` -- so the stock command silently generates
nothing for them. This script passes the ids explicitly.

It deliberately does not score anything. Run it inside the configured send
window (09:00-19:00); ``force`` is used only so a 5% "random day off" roll cannot
silently skip the whole batch the user asked to be sent.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC = REPO_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from rich.console import Console  # noqa: E402

console = Console()


def main() -> int:
    from bosshunter.ai import greeter
    from bosshunter.browser import configure, find_boss_tab
    from bosshunter.db import get_db
    from bosshunter.executor.sender import send_greetings

    from bosshunter.config import load_config

    config = load_config(REPO_ROOT / "config.yaml")

    # --- Preflight: fail loudly rather than half-sending -----------------
    error = greeter.greeting_config_error(config)
    if error:
        console.print(f"[red]招呼语配置有问题，已停止：{error}[/red]")
        return 2
    if config["profile"].get("ai_greeting_enabled"):
        console.print(
            "[yellow]注意：AI 招呼语当前是开启状态，将消耗 AI 额度。"
            "如需固定文案请把 profile.ai_greeting_enabled 设为 false。[/yellow]"
        )

    configure(config)
    if not find_boss_tab():
        console.print(
            "[red]未找到 BOSS 直聘 标签页。[/red]\n"
            "请先启动带调试端口的 Chrome 并登录 BOSS 直聘，保持窗口开启，然后重跑。"
        )
        return 3

    images = config["profile"].get("resume_images") or []
    sending_images = bool(config["profile"].get("send_resume_images")) and bool(images)
    console.print("[bold]准备发送 ready 状态的岗位[/bold]")
    console.print(f"  简历图片: {'将随招呼语发送 ' + str(len(images)) + ' 张' if sending_images else '不发送'}")

    # --- Pick targets: ready jobs that still need a greeting -------------
    db = get_db(REPO_ROOT / "data" / "bosshunter.db")
    rows = db.execute(
        "SELECT id FROM jobs WHERE status = 'ready' AND deleted_at IS NULL"
        " AND (greeting IS NULL OR TRIM(greeting) = '')"
    ).fetchall()
    needing_greeting = [str(row["id"]) for row in rows]

    if needing_greeting:
        console.print(f"  先为 {len(needing_greeting)} 个岗位写入固定招呼语…")
        generated = greeter.generate_greetings(config, needing_greeting)
        console.print(f"  ✓ 招呼语已生成 {generated} 条")

    sendable = db.execute(
        "SELECT COUNT(*) AS n FROM jobs WHERE status IN ('ready', 'approved')"
        " AND deleted_at IS NULL AND greeting IS NOT NULL AND TRIM(greeting) != ''"
    ).fetchone()["n"]
    db.close()

    if not sendable:
        console.print("[yellow]没有可发送的岗位（需要 status=ready 且已有招呼语）。[/yellow]")
        return 0

    console.print(f"  待发送岗位: {sendable} 个")

    # Send the cities the user actually wants first: within a run the ordering is
    # "priority cities by score", then everything else by score. This keeps a
    # partially-completed batch from burning the quota on the long tail.
    priority = [str(c).strip() for c in (config["profile"].get("priority_cities") or []) if str(c).strip()]
    if priority:
        config["_send_city_priority"] = priority
        console.print(f"  优先城市: {'、'.join(priority)}")

    console.print("[bold]开始发送…[/bold]")
    sent = send_greetings(config, force=True)
    console.print(f"[green]✓ 发送完成: {sent} 条[/green]")

    db = get_db(REPO_ROOT / "data" / "bosshunter.db")
    row = db.execute(
        "SELECT (SELECT COUNT(*) FROM jobs WHERE status = 'sent') AS sent,"
        " (SELECT COUNT(*) FROM jobs WHERE status = 'error') AS failed,"
        " (SELECT COUNT(*) FROM jobs WHERE status = 'ready') AS still_ready"
    ).fetchone()
    db.close()
    console.print(
        f"  结果: 已发送 {row['sent']} ｜ 失败 {row['failed']} ｜ 仍未发送 {row['still_ready']}"
    )

    # A non-zero exit when nothing went out keeps scheduled runs honest.
    return 0 if sent > 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
