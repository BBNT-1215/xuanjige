#!/usr/bin/env python3
"""
Hermestrix 主CLI

Usage:
  xuanjige <command> [options]

Commands:
  skill       Skill库管理（list/search/create/inspect）
  role        Role库管理（list/search/inspect）
  evolution   进化状态（status/pending/confirm/rollback）
  task        任务管理（create/list/state/flow）
  health      健康检查（check/monitor）
  workflow    玄机阁工作流引擎（start/submit/process/watch）
  jiyan       机研常驻进程（start/stop/status/once）
"""

import argparse
import os
import sys
import pathlib
import json
import datetime

# HERMESTRIX_HOME setup
HERMESTRIX_HOME = pathlib.Path(os.environ.get("HERMESTRIX_HOME",
    pathlib.Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(HERMESTRIX_HOME))

from engine import (
    MemoryManager, EvolutionEngine, HealthMonitor,
    SkillStats, RoleStats, TaskRecord
)

# ============================================================
# 通用格式
# ============================================================

def ts():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def cprint(msg, color="", bold=False):
    # 简单彩色输出
    colors = {
        "red": "\033[91m", "green": "\033[92m", "yellow": "\033[93m",
        "blue": "\033[94m", "magenta": "\033[95m", "cyan": "\033[96m",
        "reset": "\033[0m"
    }
    bold_seq = "\033[1m" if bold else ""
    reset = colors.get("reset", "\033[0m")
    c = colors.get(color, "")
    print(f"{bold_seq}{c}{msg}{reset}")

def header(text):
    cprint(f"\n{'='*50}", "cyan", bold=True)
    cprint(f" {text}", "cyan", bold=True)
    cprint(f"{'='*50}\n", "cyan")

def indent(text, n=2):
    print(" " * n + text)


# ============================================================
# skill 命令
# ============================================================

def cmd_skill(args):
    """Skill库管理"""
    from engine import MemoryManager
    mm = MemoryManager()

    if args.list:
        header("Skill库")
        all_skills = mm.get_all_skill_effectiveness()
        if not all_skills:
            cprint("  Skill库为空（尚未有任何Skill使用记录）", "yellow")
            return

        cprint(f"  共 {len(all_skills)} 个Skill\n", "green")
        # 从 registry 读取元数据
        registry_path = HERMESTRIX_HOME / "skills" / "registry.json"
        registry = json.loads(registry_path.read_text()) if registry_path.exists() else {}
        registry_map = {s["id"]: s for s in registry.get("skills", [])}

        print(f"  {'Skill ID':<28} {'Effectiveness':>14} {'Confidence':>12} {'Domain':>15}")
        print(f"  {'-'*28} {'-'*14} {'-'*12} {'-'*15}")
        for skill_id, score in sorted(all_skills.items(), key=lambda x: -x[1]):
            meta = registry_map.get(skill_id, {})
            eff = f"{score:.3f}"
            conf = meta.get("confidence", "—")
            domain = meta.get("domain", "—")
            bar = "█" * int(score * 10) + "░" * (10 - int(score * 10))
            cprint(f"  {skill_id:<28} {eff} {bar} {conf:>4} {domain:>15}", "green" if score > 0.7 else "yellow")

    elif args.inspect:
        from engine import MemoryManager
        mm = MemoryManager()
        stats = mm.get_skill_stats(args.inspect)
        sd = stats.stats
        header(f"Skill: {args.inspect}")
        print(f"  Effectiveness:  {stats.effectiveness_score:.3f}")
        print(f"  Confidence:    {stats.confidence}")
        print(f"  Total uses:   {sd.get('total_uses', 0)}")
        print(f"  Avg quality:  {sd.get('avg_quality', 0.0):.3f}")
        print(f"  Success rate: {sd.get('avg_quality', 0.0):.3f} ({sd.get('success_count', 0)}/{sd.get('total_uses', 0)})")
        print(f"  Last used:    {sd.get('last_used', '—')}")
        print(f"  Updated:     {stats.updated_at}")
        v = stats.verification
        print(f"  Verification: {v.get('status', 'none')}")
        if v.get("observations_avg"):
            print(f"    Obs avg:     {v['observations_avg']:.3f}")
        if v.get("verification_confirmed_at"):
            print(f"    Confirmed at: {v['verification_confirmed_at']}")

    elif args.search:
        from engine import MemoryManager
        mm = MemoryManager()
        all_skills = mm.get_all_skill_effectiveness()
        query = args.search.lower()
        results = [(sid, score) for sid, score in all_skills.items() if query in sid.lower()]
        if not results:
            cprint(f"  未找到包含 '{args.search}' 的Skill", "yellow")
            return
        cprint(f"  找到 {len(results)} 个结果：\n", "green")
        for skill_id, score in sorted(results, key=lambda x: -x[1]):
            print(f"  {skill_id:<28} {score:.3f}")

    else:
        cprint("  使用 hermestrix skill --help 查看用法", "yellow")


# ============================================================
# role 命令
# ============================================================

def cmd_role(args):
    """Role库管理"""
    from engine import MemoryManager
    mm = MemoryManager()

    if args.list:
        header("Role库")
        registry_path = HERMESTRIX_HOME / "agents" / "registry.json"
        registry = json.loads(registry_path.read_text()) if registry_path.exists() else {}
        roles = registry.get("roles", [])
        cprint(f"  共 {len(roles)} 个Role\n", "green")

        print(f"  {'Role ID':<20} {'Name':<16} {'Tasks':>8} {'Avg Quality':>12} {'Tier':>10}")
        print(f"  {'-'*20} {'-'*16} {'-'*8} {'-'*12} {'-'*10}")

        for role in sorted(roles, key=lambda r: r.get("id", "")):
            role_id = role.get("id", "—")
            name = role.get("name", role.get("id", "—"))[:14]
            rstats = mm.get_role_stats(role_id)
            stats_data = rstats.stats
            tier = role.get("tier", "—")
            avg_q = stats_data.get("avg_quality", 0.0)
            tasks = stats_data.get("tasks_completed", 0)
            bar = "█" * int(avg_q * 10) + "░" * (10 - int(avg_q * 10))
            cprint(f"  {role_id:<20} {name:<16} {tasks:>8} {avg_q:.3f} {bar} {tier:>4}", "green" if avg_q > 0.7 else "yellow")

    elif args.inspect:
        header(f"Role: {args.inspect}")
        rstats = mm.get_role_stats(args.inspect)
        sd = rstats.stats
        print(f"  Tasks completed:  {sd.get('tasks_completed', 0)}")
        print(f"  Avg quality:     {sd.get('avg_quality', 0.0):.3f}")
        print(f"  Avg duration:    {sd.get('avg_duration_minutes', 0)} min")
        print(f"  Last active:     {sd.get('last_active', '—')}")
        collaborations = rstats.collaborations
        print(f"  Collaborators:    {', '.join(collaborations.keys()) if collaborations else '—'}")

        # 读取 SOUL
        role_dir = HERMESTRIX_HOME / "agents" / args.inspect
        soul_path = role_dir / "SOUL.md"
        if soul_path.exists():
            content = soul_path.read_text(encoding="utf-8")
            lines = content.split("\n")[:15]
            cprint("\n  SOUL.md 预览：", "cyan")
            for line in lines:
                print(f"    {line}")

    elif args.search:
        registry_path = HERMESTRIX_HOME / "agents" / "registry.json"
        registry = json.loads(registry_path.read_text()) if registry_path.exists() else {}
        roles = registry.get("roles", [])
        query = args.search.lower()
        results = [r for r in roles if query in r.get("id", "").lower() or query in r.get("name", "").lower()]
        if not results:
            cprint(f"  未找到包含 '{args.search}' 的Role", "yellow")
            return
        cprint(f"  找到 {len(results)} 个结果：\n", "green")
        for r in results:
            print(f"  {r.get('id'):<20} {r.get('name', ''):<16} tier={r.get('tier', '—')}")

    else:
        cprint("  使用 hermestrix role --help 查看用法", "yellow")


# ============================================================
# evolution 命令
# ============================================================

def cmd_evolution(args):
    """进化状态"""
    ee = EvolutionEngine()
    mm = ee.memory

    if args.status:
        header("进化引擎状态")
        print(f"  待验证: {ee.verifier.get_pending_count()} 个Skill")
        pending = ee.verifier.get_pending_list()
        if pending:
            cprint("\n  Pending验证：", "yellow")
            for p in pending:
                print(f"    {p['skill_id']}: new={p['new_score']:.3f}, obs={p['observations']}/{p['required']}")
        else:
            cprint("  无待验证项", "green")

        # L2 Skill 统计摘要
        all_skills = mm.get_all_skill_effectiveness()
        if all_skills:
            scores = list(all_skills.values())
            avg = sum(scores) / len(scores)
            high = sum(1 for s in scores if s > 0.75)
            cprint(f"\n  Skill统计: {len(scores)}个, 均值={avg:.3f}, 高效(>0.75)={high}个", "green")

        # L2 Role 统计摘要
        registry_path = HERMESTRIX_HOME / "agents" / "registry.json"
        registry = json.loads(registry_path.read_text()) if registry_path.exists() else {}
        roles = registry.get("roles", [])
        total_tasks = sum(mm.get_role_stats(r["id"]).stats.get("tasks_completed", 0) for r in roles)
        cprint(f"  Role统计: {len(roles)}个, 总任务={total_tasks}", "green")

    elif args.confirm:
        # 手动确认pending的验证
        pending = ee.verifier.pending
        if args.confirm not in pending:
            cprint(f"  Skill '{args.confirm}' 不在pending列表中", "red")
            return
        cprint(f"  手动确认 {args.confirm} 的进化验证（通常由系统自动处理）", "yellow")
        cprint(f"  pending验证需等待观察窗口自动触发，不支持手动提前确认", "yellow")

    elif args.rollback:
        pending = ee.verifier.pending
        if args.rollback not in pending:
            cprint(f"  Skill '{args.rollback}' 不在pending列表中", "red")
            return
        p = pending[args.rollback]
        old_score = p["old_score"]
        ee.verifier.pending.pop(args.rollback, None)
        stats = mm.get_skill_stats(args.rollback)
        stats.effectiveness_score = old_score
        stats.verification["status"] = "manual_rollback"
        mm.save_skill_stats(stats)
        cprint(f"  已回滚 {args.rollback} 到 {old_score}", "green")

    else:
        cprint("  使用 hermestrix evolution --help 查看用法", "yellow")


# ============================================================
# workflow 命令（玄机阁工作流引擎）
# ============================================================

def cmd_workflow(args):
    """玄机阁工作流引擎控制"""
    from workflow.engine import get_engine
    engine = get_engine()

    if args.start:
        header("玄机阁 · 引擎启动")
        engine.start()
        status = engine.status()
        cprint(f"  引擎状态: {'运行中' if status['running'] else '已停止'}", "green")
        cprint(f"  Agent数量: {len(status['agents'])}", "cyan")
        cprint(f"  任务统计: {json.dumps(status['stats']['by_state'], ensure_ascii=False)}", "cyan")
        cprint(f"\n  用 xuanjige workflow submit <任务标题> 提交新任务", "yellow")

    elif args.stop:
        header("玄机阁 · 引擎停止")
        engine.stop()
        cprint("  引擎已停止", "yellow")

    elif args.status:
        header("玄机阁 · 引擎状态")
        st = engine.status()
        cprint(f"  引擎: {'🟢 运行中' if st['running'] else '🔴 已停止'}", "green" if st['running'] else "red")
        cprint(f"  Agent数量: {len(st['agents'])}", "cyan")
        cprint(f"\n  任务统计:", "cyan")
        for state, cnt in st['stats']['by_state'].items():
            cprint(f"    {state}: {cnt}", "yellow")
        cprint(f"\n  最近日志:", "cyan")
        for entry in engine.get_log()[-5:]:
            cprint(f"    [{entry['time'][11:19]}] {entry['msg']}", "")

    elif args.submit:
        header("玄机阁 · 提交任务")
        task = engine.submit(title=args.submit,
                            description=args.desc or "",
                            skills=args.skills.split(',') if args.skills else None,
                            tags=args.tags.split(',') if args.tags else None,
                            priority=int(args.priority or 0))
        cprint(f"  ✅ 任务已提交", "green")
        cprint(f"  ID:     {task['id']}", "cyan")
        cprint(f"  标题:   {task['title']}", "yellow")
        cprint(f"  状态:   {task['state']}", "")
        cprint(f"\n  用 xuanjige workflow process {task['id']} 执行工作流", "yellow")

    elif args.process:
        header("玄机阁 · 执行工作流")
        result = engine.process_task(args.process)
        if result.get("ok"):
            cprint(f"  ✅ 流程执行成功", "green")
            cprint(f"  当前步骤: {result.get('step', 'unknown')}", "cyan")
            if result.get("next"):
                cprint(f"  下一步: {result.get('next')}", "yellow")
        else:
            cprint(f"  ❌ 执行失败: {result.get('error')}", "red")

    elif args.watch:
        header("玄机阁 · 监控模式 (Ctrl+C 退出)")
        engine.start()
        try:
            while True:
                st = engine.status()
                stats = st['stats']['by_state']
                ts_str = datetime.datetime.now().strftime("%H:%M:%S")
                pending = stats.get('待分拣', 0)
                running = stats.get('执行中', 0)
                done = stats.get('已完成', 0)
                cprint(f"[{ts_str}] 待分拣={pending} 执行中={running} 已完成={done}", "cyan")
                import time; time.sleep(3)
        except KeyboardInterrupt:
            cprint("\n  监控退出", "yellow")

    elif args.log:
        header("玄机阁 · 执行日志")
        for entry in engine.get_log()[-20:]:
            cprint(f"  [{entry['time'][11:19]}] {entry['msg']}", "")

    else:
        cprint("  使用 xuanjige workflow --help 查看用法", "yellow")
        cprint("\n  子命令:", "cyan")
        cprint("    --start              启动工作流引擎", "")
        cprint("    --stop               停止工作流引擎", "")
        cprint("    --status             查看引擎状态", "")
        cprint("    --submit <标题>      提交新任务", "")
        cprint("    --process <ID>       执行单任务完整流程", "")
        cprint("    --watch              实时监控模式", "")
        cprint("    --log                查看执行日志", "")


# ============================================================
# task 命令（封装 kanban）
# ============================================================

def cmd_task(args):
    """任务管理（封装 kanban）"""
    import subprocess

    cmd = ["python3", str(HERMESTRIX_HOME / "scripts" / "kanban.py")]
    if args.create:
        cmd += ["create", args.create]
    elif args.list:
        cmd += ["list"]
    elif args.state:
        # task --state TASK_ID 缺少NEW_STATE参数，提示用户
        cprint("  --state 需要两个参数: TASK_ID NEW_STATE", "yellow")
        cprint("  用法: hermestrix task --state <TASK_ID> <NEW_STATE>", "yellow")
        return
    elif args.flow:
        # task --flow TASK_ID 缺少FROM_D TO_D参数，提示用户
        cprint("  --flow 需要三个参数: TASK_ID FROM_D TO_D", "yellow")
        cprint("  用法: hermestrix task --flow <TASK_ID> <FROM_DEPT> <TO_DEPT>", "yellow")
        return
    elif args.show:
        cmd += ["get", args.show]
    else:
        cprint("  使用 hermestrix task --help 查看用法", "yellow")
        return

    result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(HERMESTRIX_HOME))
    print(result.stdout)
    if result.stderr:
        cprint(result.stderr, "red")


# ============================================================
# health 命令
# ============================================================

def cmd_health(args):
    """健康检查"""
    hm = HealthMonitor()

    if args.check:
        report = hm.check_all()
        header("系统健康检查")
        overall_color = "green" if report.overall == "ok" else "red"
        cprint(f"  Overall: {report.overall}", overall_color, bold=True)

        if report.alerts:
            cprint(f"\n  告警 ({len(report.alerts)}项)：", "red")
            for alert in report.alerts:
                level_color = "red" if alert["level"] == "critical" else "yellow"
                cprint(f"    [{alert['level']}] {alert['message']}", level_color)

        if hasattr(report, "metrics") and report.metrics:
            cprint(f"\n  指标详情：", "cyan")
            for m in report.metrics:
                status = m.get("status", "—")
                bar = "█" * int(float(m.get("value", 0)) * 10) if m.get("value") is not None else "?"
                cprint(f"    {m.get('name',''):<35} {m.get('value','?'):>8} [{status}]")

        # 详细报告
        if hasattr(report, "details"):
            for k, v in report.details.items():
                print(f"  {k}: {v}")

    elif args.monitor:
        cprint(f"  实时监控模式 (Ctrl+C 退出)", "cyan")
        try:
            while True:
                report = hm.check_all()
                ts_str = datetime.datetime.now().strftime("%H:%M:%S")
                color = "green" if report.overall == "ok" else "red"
                alerts = len(report.alerts) if hasattr(report, "alerts") else 0
                cprint(f"[{ts_str}] overall={report.overall}, alerts={alerts}", color)
                if hasattr(args, 'verbose') and args.verbose and hasattr(report, "metrics"):
                    for m in report.metrics:
                        cprint(f"    {m.get('name','')}={m.get('value','?')}", "cyan")
                import time; time.sleep(args.monitor)
        except KeyboardInterrupt:
            cprint("\n  监控退出", "yellow")

    else:
        cprint("  使用 hermestrix health --help 查看用法", "yellow")


# ============================================================
# libu 命令
# ============================================================

def cmd_jiyan(args):
    """机研常驻进程"""
    from engine.jiyan_agent import JiyanAgent
    import subprocess, signal

    DATA_DIR = HERMESTRIX_HOME / "data"
    PID_FILE = DATA_DIR / "jiyan_agent.pid"

    if args.start:
        # 检查是否已运行
        if PID_FILE.exists():
            pid = int(PID_FILE.read_text().strip())
            try:
                os.kill(pid, 0)
                cprint(f"  机研进程已在运行 (PID={pid})，无需重复启动", "yellow")
                return
            except OSError:
                cprint(f"  PID文件过期，清理中...", "yellow")
                PID_FILE.unlink()

        cprint("  启动机研常驻进程...", "green")
        proc = subprocess.Popen(
            ["python3", str(HERMESTRIX_HOME / "engine" / "jiyan_agent.py")],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            cwd=str(HERMESTRIX_HOME)
        )
        cprint(f"  已启动 (PID={proc.pid})，输出：", "green")
        cprint(f"  (查看日志: tail -f {HERMESTRIX_HOME}/data/events.json)", "cyan")

    elif args.stop:
        if not PID_FILE.exists():
            cprint("  机研进程未运行（无PID文件）", "yellow")
            return
        pid = int(PID_FILE.read_text().strip())
        try:
            os.kill(pid, signal.SIGTERM)
            cprint(f"  已发送SIGTERM (PID={pid})", "green")
            PID_FILE.unlink()
        except OSError as e:
            cprint(f"  停止失败: {e}", "red")

    elif args.status:
        if not PID_FILE.exists():
            cprint("  机研进程: 未运行", "red")
            return
        pid = int(PID_FILE.read_text().strip())
        try:
            os.kill(pid, 0)
            cprint(f"  机研进程: 运行中 (PID={pid})", "green")
        except OSError:
            cprint(f"  机研进程: PID文件存在但进程已死", "red")
            PID_FILE.unlink()

    elif args.once:
        agent = LibuAgent(verbose=args.verbose)
        agent.run(once=True)

    else:
        cprint("  使用 hermestrix jiyan --help 查看用法", "yellow")


# ============================================================
# 主入口
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        prog="hermestrix",
        description="Hermestrix - 自我进化的AI Agent协作操作系统"
    )
    sub = parser.add_subparsers(dest="command", metavar="<command>")

    # skill
    p_skill = sub.add_parser("skill", help="Skill库管理")
    g = p_skill.add_mutually_exclusive_group()
    g.add_argument("--list", "-l", action="store_true", help="列出所有Skill")
    g.add_argument("--inspect", "-i", metavar="SKILL_ID", help="查看Skill详情")
    g.add_argument("--search", "-s", metavar="KEYWORD", help="搜索Skill")

    # role
    p_role = sub.add_parser("role", help="Role库管理")
    g = p_role.add_mutually_exclusive_group()
    g.add_argument("--list", "-l", action="store_true", help="列出所有Role")
    g.add_argument("--inspect", "-i", metavar="ROLE_ID", help="查看Role详情")
    g.add_argument("--search", "-s", metavar="KEYWORD", help="搜索Role")

    # evolution
    p_ev = sub.add_parser("evolution", help="进化状态")
    g = p_ev.add_mutually_exclusive_group()
    g.add_argument("--status", "-s", action="store_true", help="查看进化状态")
    g.add_argument("--confirm", metavar="SKILL_ID", help="手动确认进化（不推荐）")
    g.add_argument("--rollback", metavar="SKILL_ID", help="手动回滚进化")

    # task
    p_task = sub.add_parser("task", help="任务管理")
    g = p_task.add_mutually_exclusive_group()
    g.add_argument("--create", "-c", metavar="TITLE", help="创建任务")
    g.add_argument("--list", "-l", action="store_true", help="列出任务")
    g.add_argument("--state", metavar="TASK_ID", help="查看任务状态")
    g.add_argument("--flow", metavar="TASK_ID", help="流转任务到下一部门")
    g.add_argument("--show", metavar="TASK_ID", help="查看任务详情")

    # health
    p_h = sub.add_parser("health", help="健康检查")
    g = p_h.add_mutually_exclusive_group()
    g.add_argument("--check", action="store_true", help="执行健康检查")
    g.add_argument("--monitor", "-m", nargs="?", const="5", type=int, metavar="SECS", help="实时监控")

    # workflow
    p_wf = sub.add_parser("workflow", help="玄机阁工作流引擎")
    g = p_wf.add_mutually_exclusive_group()
    g.add_argument("--start", action="store_true", help="启动工作流引擎")
    g.add_argument("--stop", action="store_true", help="停止工作流引擎")
    g.add_argument("--status", action="store_true", help="查看引擎状态")
    g.add_argument("--submit", "-s", metavar="TITLE", help="提交新任务")
    g.add_argument("--process", "-p", metavar="TASK_ID", help="执行单任务完整流程")
    g.add_argument("--watch", "-w", action="store_true", help="实时监控模式")
    g.add_argument("--log", action="store_true", help="查看执行日志")
    p_wf.add_argument("--desc", help="任务描述")
    p_wf.add_argument("--skills", help="所需Skill(逗号分隔)")
    p_wf.add_argument("--tags", help="标签(逗号分隔)")
    p_wf.add_argument("--priority", help="优先级(数字)")

    # libu
    p_l = sub.add_parser("jiyan", help="机研常驻进程")
    g = p_l.add_mutually_exclusive_group()
    g.add_argument("--start", action="store_true", help="启动机研进程")
    g.add_argument("--stop", action="store_true", help="停止机研进程")
    g.add_argument("--status", action="store_true", help="查看运行状态")
    g.add_argument("--once", action="store_true", help="运行一次后退出")
    p_l.add_argument("-v", "--verbose", action="store_true", help="详细输出")

    args = parser.parse_args()

    if args.command is None:
        print(__doc__)
        cprint("\n命令列表：", "cyan", bold=True)
        print("  xuanjige skill     --list            # 列出所有Skill")
        print("  xuanjige role     --list            # 列出所有Role")
        print("  xuanjige evolution --status          # 进化引擎状态")
        print("  xuanjige task     --list             # 任务列表")
        print("  xuanjige health   --check            # 健康检查")
        print("  xuanjige workflow --start            # 启动工作流引擎")
        print("  xuanjige jiyan     --status           # 机研进程状态")
        return

    # 分发
    dispatch = {
        "skill": cmd_skill,
        "role": cmd_role,
        "evolution": cmd_evolution,
        "task": cmd_task,
        "health": cmd_health,
        "workflow": cmd_workflow,
        "jiyan": cmd_jiyan,
    }

    try:
        dispatch[args.command](args)
    except Exception as e:
        cprint(f"\n  错误: {e}", "red")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
