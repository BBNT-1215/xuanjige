#!/usr/bin/env python3
"""
Hermestrix 看板任务更新工具

用法:
  python3 scripts/kanban.py create "<title>" --org <org> --official <official>
  python3 scripts/kanban.py state <id> <state> "<说明>"
  python3 scripts/kanban.py flow <id> "<from>" "<to>" "<remark>"
  python3 scripts/kanban.py done <id> "<output>" "<summary>"
  python3 scripts/kanban.py progress <id> "<当前在做什么>" "<计划1✅|计划2🔄|计划3>"
  python3 scripts/kanban.py todo <id> <todo_id> "<title>" <status> --detail "<产出详情>"
  python3 scripts/kanban.py list [--state <state>] [--org <org>]
  python3 scripts/kanban.py get <id>
"""
import datetime
import json
import pathlib
import sys
import logging
import os
import re

# ── 路径解析 ──────────────────────────────────────────────
_BASE = pathlib.Path(os.environ.get('HERMESTRIX_HOME',
           pathlib.Path(__file__).resolve().parent.parent))
DATA_DIR = _BASE / 'data'
DATA_DIR.mkdir(parents=True, exist_ok=True)
TASKS_FILE = DATA_DIR / 'tasks.json'
AUDIT_FILE = DATA_DIR / 'audit_log.json'
TASKS_FILE.parent.mkdir(parents=True, exist_ok=True)

log = logging.getLogger('hermestrix.kanban')
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(name)s] %(message)s',
    datefmt='%H:%M:%S'
)

# ── 原子读写 ──────────────────────────────────────────────
def _read_json(path):
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except (json.JSONDecodeError, OSError):
        return None

def _atomic_write(path, data):
    """先写.tmp，再rename，原子保证"""
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    os.replace(tmp, path)

def atomic_json_read(path, default=None):
    data = _read_json(path)
    return data if data is not None else default

def atomic_json_update(path, modifier, default=None):
    for attempt in range(3):
        try:
            data = atomic_json_read(path, default)
            data = modifier(data)
            _atomic_write(path, data)
            return
        except (json.JSONDecodeError, OSError) as e:
            if attempt == 2:
                raise
            import time; time.sleep(0.1 * (attempt + 1))

# ── 时间 ──────────────────────────────────────────────────
def now_iso():
    return datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%S')

# ── 状态映射 ──────────────────────────────────────────────
STATE_ORG_MAP = {
    'Taizi': '太子', 'Zhongshu': '中书省', 'Menxia': '门下省',
    'Assigned': '尚书省', 'Next': '尚书省',
    'Doing': '执行中', 'Review': '尚书省', 'Done': '完成', 'Blocked': '阻塞',
    'PendingConfirm': '尚书省', 'Pending': '中书省',
}

_ORG_TO_STATE_AGENT = {
    '太子': 'chengzhi', '中书省': 'jiheng', '门下省': 'shenyi',
    '尚书省': 'jiheng', '户部': 'shusuan', '礼部': 'libu',
    '兵部': 'bingrong', '刑部': 'xingce', '工部': 'jizao', '吏部': 'jiyan',
    '早朝官': 'zaohuang', '钦天监': 'qitian',
}

_AGENT_LABELS = {
    'main': '太子', 'chengzhi': '太子',
    'jiheng': '中书省', 'shenyi': '门下省', 'jiheng': '尚书省',
    'libu': '礼部', 'shusuan': '户部', 'bingrong': '兵部', 'xingce': '刑部',
    'jizao': '工部', 'jiyan': '吏部', 'zaohuang': '早朝官',
    'qitian': '钦天监',
}

# ── 状态机（与edict兼容）─────────────────────────────────
_VALID_TRANSITIONS = {
    'Pending':        {'Taizi', 'Cancelled'},
    'Taizi':          {'Zhongshu', 'Cancelled'},
    'Zhongshu':       {'Menxia', 'Cancelled', 'Blocked'},
    'Menxia':         {'Assigned', 'Zhongshu', 'Cancelled'},
    'Assigned':       {'Doing', 'Next', 'Blocked', 'Cancelled'},
    'Next':           {'Doing', 'Blocked', 'Cancelled'},
    'Doing':          {'Review', 'Done', 'Blocked', 'Cancelled'},
    'Review':         {'Done', 'Menxia', 'Doing', 'Cancelled', 'PendingConfirm'},
    'PendingConfirm': {'Done', 'Review', 'Cancelled'},
    'Blocked':        {'Taizi', 'Zhongshu', 'Menxia', 'Assigned', 'Next', 'Doing', 'Review', 'Cancelled'},
    'Done':           set(),
    'Cancelled':      set(),
}

# ── 审计日志 ──────────────────────────────────────────────
MAX_AUDIT_LOG = 5000

def _append_audit(task_id, agent, action, old_val=None, new_val=None, reason=""):
    entry = {
        "ts": now_iso(),
        "task": task_id or "",
        "agent": agent or "",
        "action": action,
        "from": old_val,
        "to": new_val,
        "reason": reason,
    }
    def modifier(logs):
        if logs is None: logs = []
        logs.append(entry)
        if len(logs) > MAX_AUDIT_LOG:
            logs = logs[-MAX_AUDIT_LOG:]
        return logs
    atomic_json_update(AUDIT_FILE, modifier, [])

# ── 从环境/路径推断Agent ─────────────────────────────────
def _infer_agent_id():
    for k in ('HERMESTRIX_AGENT_ID', 'AGENT_ID', 'OPENCLAW_AGENT_ID'):
        v = (os.environ.get(k) or '').strip()
        if v: return v
    cwd = str(pathlib.Path.cwd())
    m = re.search(r'workspace-([a-zA-Z0-9_-]+)', cwd)
    if m: return m.group(1)
    fpath = str(pathlib.Path(__file__).resolve())
    m2 = re.search(r'workspace-([a-zA-Z0-9_-]+)', fpath)
    if m2: return m2.group(1)
    return ''

# ── 文本清洗 ─────────────────────────────────────────────
_JUNK_TITLES = {
    '?', '？', '好', '好的', '是', '否', '不', '不是', '对',
    '了解', '收到', '嗯', '哦', '知道了', '开启了么', '可以',
    '不行', '行', 'ok', 'yes', 'no', '你去开启', '测试', '试试', '看看',
}

def _sanitize(raw, max_len=80):
    if not raw: return ''
    t = raw.strip()
    t = re.split(r'\n*Conversation\b', t, maxsplit=1)[0].strip()
    t = re.split(r'\n*```', t, maxsplit=1)[0].strip()
    t = re.sub(r'[/\\.~][A-Za-z0-9_\-./]+(?:\.(?:py|js|ts|json|md|sh|yaml|yml|txt|csv|html|css|log))?', '', t)
    t = re.sub(r'https?://\S+', '', t)
    t = re.sub(r'^(传旨|下旨)([（(][^)）]*[)）])?[：:\uff1a]\s*', '', t)
    t = re.sub(r'(message_id|session_id|chat_id|open_id|user_id|tenant_key)\s*[:=]\s*\S+', '', t)
    t = re.sub(r'\s+', ' ', t).strip()
    if len(t) > max_len:
        t = t[:max_len] + '…'
    return t

def _is_valid_title(title):
    t = (title or '').strip()
    if len(t) < 6:
        return False, f'标题过短（{len(t)}<6字），疑似非旨意'
    if t.lower() in _JUNK_TITLES:
        return False, f'标题 "{t}" 不是有效旨意'
    if re.fullmatch(r'[\s?？!！.。,，…·\-—~]+', t):
        return False, '标题只有标点符号'
    if re.match(r'^[/\\~.]', t) or re.search(r'/[a-zA-Z0-9_-]+/[a-zA-Z0-9_-]+', t):
        return False, '标题看起来像文件路径，请用中文概括'
    if re.fullmatch(r'[\s\W]*', t):
        return False, '标题清洗后为空'
    return True, ''

def _find_task(tasks, task_id):
    return next((t for t in tasks if t.get('id') == task_id), None)

# ── 命令实现 ─────────────────────────────────────────────

def cmd_create(task_id, title, state, org, official, remark=None):
    title = _sanitize(title, 80)
    valid, reason = _is_valid_title(title)
    if not valid:
        print(f'[看板] 拒绝创建：{reason}', flush=True)
        return

    actual_org = STATE_ORG_MAP.get(state, org)
    clean_remark = _sanitize(remark, 120) if remark else f'已下旨，等待{actual_org}接旨'

    def modifier(tasks):
        if tasks is None: tasks = []
        existing = _find_task(tasks, task_id)
        if existing and existing.get('state') in ('Done', 'Cancelled'):
            print(f'[看板] 任务 {task_id} 已完结，不可覆盖', flush=True)
            return tasks
        tasks = [t for t in tasks if t.get('id') != task_id]
        tasks.insert(0, {
            "id": task_id,
            "title": title,
            "official": official,
            "org": actual_org,
            "state": state,
            "now": clean_remark[:60] if remark else f'已下旨，等待{actual_org}接旨',
            "eta": "-",
            "block": "无",
            "output": "",
            "flow_log": [{"at": now_iso(), "from": "用户", "to": actual_org, "remark": clean_remark}],
            "progress_log": [],
            "todos": [],
            "updatedAt": now_iso()
        })
        return tasks

    atomic_json_update(TASKS_FILE, modifier, [])
    log.info(f'✅ 创建 {task_id} | {title[:30]} | state={state}')
    _append_audit(task_id, _infer_agent_id(), 'create', None, state, title)


def cmd_state(task_id, new_state, now_text=None):
    rejected = [False]

    def modifier(tasks):
        if tasks is None: tasks = []
        t = _find_task(tasks, task_id)
        if not t:
            print(f'[看板] 任务 {task_id} 不存在', flush=True)
            return tasks
        old_state = t['state']
        allowed = _VALID_TRANSITIONS.get(old_state)
        if allowed is not None and new_state not in allowed:
            print(f'[看板] ❌ 非法状态转换 {task_id}: {old_state} → {new_state}（允许: {allowed}）', flush=True)
            rejected[0] = True
            return tasks
        t['state'] = new_state
        if new_state in STATE_ORG_MAP:
            t['org'] = STATE_ORG_MAP[new_state]
        if now_text:
            t['now'] = now_text
        t['updatedAt'] = now_iso()
        return tasks

    atomic_json_update(TASKS_FILE, modifier, [])
    if not rejected[0]:
        log.info(f'✅ {task_id} 状态更新: → {new_state}')
        _append_audit(task_id, _infer_agent_id(), 'state', None, new_state, now_text or '')


def cmd_flow(task_id, from_dept, to_dept, remark):
    clean_remark = _sanitize(remark, 120)
    agent_id = _infer_agent_id()
    agent_label = _AGENT_LABELS.get(agent_id, agent_id)

    def modifier(tasks):
        if tasks is None: tasks = []
        t = _find_task(tasks, task_id)
        if not t:
            print(f'[看板] 任务 {task_id} 不存在', flush=True)
            return tasks
        # 流转时同步更新状态：尚书省 → Review，其他部门 → Doing
        dept_lower = to_dept.lower()
        if dept_lower == '尚书省':
            new_state = 'Review'
        elif dept_lower in ('中书省', '门下省', '太子'):
            new_state = dept_lower  # 这些部门对应自己的state名
        else:
            new_state = 'Doing'
        t.setdefault('flow_log', []).append({
            "at": now_iso(),
            "from": from_dept,
            "to": to_dept,
            "remark": clean_remark,
            "agent": agent_id,
            "agentLabel": agent_label,
            "state_change": new_state,
        })
        t['state'] = new_state
        t['org'] = to_dept
        t['updatedAt'] = now_iso()
        return tasks

    atomic_json_update(TASKS_FILE, modifier, [])
    log.info(f'✅ {task_id} 流转: {from_dept} → {to_dept}')
    _append_audit(task_id, agent_id, 'flow', from_dept, to_dept, clean_remark)


def cmd_done(task_id, output_path='', summary=''):
    rejected = [False]

    def modifier(tasks):
        if tasks is None: tasks = []
        t = _find_task(tasks, task_id)
        if not t:
            print(f'[看板] 任务 {task_id} 不存在', flush=True)
            return tasks
        old_state = t.get('state')
        if old_state not in ('Doing', 'Next', 'Review'):
            rejected[0] = True
            print(f'[看板] {task_id} done被拒绝：当前状态 {old_state} 不允许完成', flush=True)
            return tasks
        from_org = t.get('org', '执行部门')
        t['state'] = 'Done'
        t['org'] = '完成'
        t['output'] = output_path
        t['now'] = summary or '执行已完成'
        t.setdefault('flow_log', []).append({
            "at": now_iso(), "from": from_org, "to": "完成",
            "remark": f"✅ 完成：{summary or '已完成'}"
        })
        t['updatedAt'] = now_iso()
        return tasks

    atomic_json_update(TASKS_FILE, modifier, [])
    if not rejected[0]:
        log.info(f'✅ {task_id} 已完成')
        _append_audit(task_id, _infer_agent_id(), 'done', None, 'Done', summary or '')


def cmd_progress(task_id, current, plan):
    """进展上报，不改变状态"""
    def modifier(tasks):
        if tasks is None: tasks = []
        t = _find_task(tasks, task_id)
        if not t:
            return tasks
        t.setdefault('progress_log', []).append({
            "at": now_iso(),
            "current": _sanitize(current, 120),
            "plan": _sanitize(plan, 200),
            "agent": _infer_agent_id(),
        })
        # 保留最新100条
        if len(t['progress_log']) > 100:
            t['progress_log'] = t['progress_log'][-100:]
        t['now'] = _sanitize(current, 60)
        t['updatedAt'] = now_iso()
        return tasks

    atomic_json_update(TASKS_FILE, modifier, [])


def cmd_todo(task_id, todo_id, title, status, detail=None):
    """添加/更新子任务"""
    def modifier(tasks):
        if tasks is None: tasks = []
        t = _find_task(tasks, task_id)
        if not t:
            return tasks
        todos = t.setdefault('todos', [])
        # 找已有的或创建新的
        existing = next((td for td in todos if str(td.get('id')) == str(todo_id)), None)
        entry = {
            "id": int(todo_id),
            "title": _sanitize(title, 80),
            "status": status,
            "detail": _sanitize(detail, 300) if detail else '',
            "updatedAt": now_iso()
        }
        if existing:
            existing.update(entry)
        else:
            todos.append(entry)
        t['updatedAt'] = now_iso()
        return tasks

    atomic_json_update(TASKS_FILE, modifier, [])


def cmd_list(state_filter=None, org_filter=None):
    """列出任务"""
    tasks = atomic_json_read(TASKS_FILE, [])
    if state_filter:
        tasks = [t for t in tasks if t.get('state') == state_filter]
    if org_filter:
        tasks = [t for t in tasks if org_filter in t.get('org', '')]

    print(f'\n📋 任务列表（共 {len(tasks)} 项）\n')
    print(f'{"ID":<20} {"状态":<12} {"部门":<8} {"标题":<40} {"更新"}')
    print('-' * 100)
    for t in tasks:
        ts = t.get('updatedAt', '')[:10]
        title = t.get('title', '')[:38]
        print(f'{t.get("id",""):<20} {t.get("state",""):<12} {t.get("org",""):<8} {title:<40} {ts}')
    print()


def cmd_get(task_id):
    """查看任务详情"""
    tasks = atomic_json_read(TASKS_FILE, [])
    t = _find_task(tasks, task_id)
    if not t:
        print(f'[看板] 任务 {task_id} 不存在')
        return
    print(f'\n📋 任务详情: {task_id}')
    print(f'标题: {t.get("title")}')
    print(f'状态: {t.get("state")} | 部门: {t.get("org")}')
    print(f'当前动态: {t.get("now")}')
    print(f'更新: {t.get("updatedAt")}')
    if t.get('flow_log'):
        print(f'\n流转记录:')
        for fl in t.get('flow_log', []):
            print(f'  [{fl.get("at","")[:19]}] {fl.get("from")} → {fl.get("to")}: {fl.get("remark")}')
    if t.get('progress_log'):
        print(f'\n最近进展:')
        for pl in t.get('progress_log', [])[-5:]:
            print(f'  [{pl.get("at","")[:19]}] {pl.get("current")}')
            if pl.get('plan'):
                print(f'    计划: {pl.get("plan")}')
    if t.get('todos'):
        print(f'\n子任务:')
        for td in t.get('todos', []):
            print(f'  [{td.get("id")}] {td.get("status"):<12} {td.get("title")}')
    print()


def cmd_morning_brief():
    """早朝播报"""
    tasks = atomic_json_read(TASKS_FILE, [])
    today = datetime.date.today().isoformat()

    pending = [t for t in tasks if t.get('state') not in ('Done', 'Cancelled')]
    done_today = [t for t in tasks if t.get('state') == 'Done'
                  and t.get('updatedAt', '').startswith(today)]

    print(f'\n🌅 Hermestrix 早朝播报 - {today}')
    print(f'\n📊 昨日完成: {len(done_today)} 项任务')
    for t in done_today[:5]:
        print(f'  ✅ {t.get("title", "")[:50]}')
    print(f'\n🔄 进行中: {len(pending)} 项任务')
    active = [t for t in pending if t.get('state') in ('Doing', 'Assigned', 'Menxia', 'Zhongshu')]
    for t in active[:5]:
        print(f'  🔄 [{t.get("state")}] {t.get("title", "")[:50]}')
    print()


# ── CLI 入口 ──────────────────────────────────────────────
def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == 'create':
        title = sys.argv[2] if len(sys.argv) > 2 else ''
        task_id = f'JJ-{datetime.date.today().strftime("%Y%m%d")}-{len(atomic_json_read(TASKS_FILE, []))+1:03d}'
        org = 'Zhongshu'
        official = '太子'
        # 简单解析
        args = sys.argv[3:]
        for i, a in enumerate(args):
            if a == '--org' and i+1 < len(args):
                org = args[i+1]
            if a == '--official' and i+1 < len(args):
                official = args[i+1]
        cmd_create(task_id, title, org, org, official)
        print(f'任务ID: {task_id}')

    elif cmd == 'state':
        task_id, new_state = sys.argv[2], sys.argv[3]
        now_text = sys.argv[4] if len(sys.argv) > 4 else None
        cmd_state(task_id, new_state, now_text)

    elif cmd == 'flow':
        task_id, from_d, to_d = sys.argv[2], sys.argv[3], sys.argv[4]
        remark = sys.argv[5] if len(sys.argv) > 5 else ''
        cmd_flow(task_id, from_d, to_d, remark)

    elif cmd == 'done':
        task_id = sys.argv[2]
        output = sys.argv[3] if len(sys.argv) > 3 else ''
        summary = sys.argv[4] if len(sys.argv) > 4 else ''
        cmd_done(task_id, output, summary)

    elif cmd == 'progress':
        task_id = sys.argv[2]
        current = sys.argv[3] if len(sys.argv) > 3 else ''
        plan = sys.argv[4] if len(sys.argv) > 4 else ''
        cmd_progress(task_id, current, plan)

    elif cmd == 'todo':
        task_id = sys.argv[2]
        todo_id = sys.argv[3]
        title = sys.argv[4] if len(sys.argv) > 4 else ''
        status = sys.argv[5] if len(sys.argv) > 5 else 'open'
        detail = None
        for i, a in enumerate(sys.argv):
            if a == '--detail' and i+1 < len(sys.argv):
                detail = sys.argv[i+1]
        cmd_todo(task_id, todo_id, title, status, detail)

    elif cmd == 'list':
        state_f, org_f = None, None
        args = sys.argv[2:]
        for i, a in enumerate(args):
            if a == '--state' and i+1 < len(args):
                state_f = args[i+1]
            if a == '--org' and i+1 < len(args):
                org_f = args[i+1]
        cmd_list(state_f, org_f)

    elif cmd == 'get':
        cmd_get(sys.argv[2])

    elif cmd == 'morning-brief':
        cmd_morning_brief()

    else:
        print(f'未知命令: {cmd}')
        print(__doc__)
        sys.exit(1)

if __name__ == '__main__':
    main()
