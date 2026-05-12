#!/usr/bin/env python3
"""
玄机阁 Dashboard Web服务器 v2

提供看板的Web界面和REST API。

新增端点：
  GET  /api/tasks          → 从Kanban SQLite读取任务
  GET  /api/stats          → 系统统计
  GET  /api/health         → 健康状态 + 运行时间
  GET  /api/hermes/status  → Hermes Agent状态
  GET  /api/cron/jobs      → Cron任务列表
  GET  /api/agents         → Agent注册表
  POST /api/tasks          → 创建新任务（触发玄机阁步骤链）
  POST /api/cmd            → 发送命令到Hermes Agent（飞书/Feishu）
  POST /api/cron/pause     → 暂停cron任务
  POST /api/cron/resume    → 恢复cron任务

启动:
  python3 dashboard/server.py [--host 127.0.0.1] [--port 7892]
"""
import json
import pathlib
import sys
import os
import datetime
import http.server
import socketserver
import urllib.parse
import sqlite3
import subprocess
import signal

_BASE = pathlib.Path(os.environ.get('HERMESTRIX_HOME',
           pathlib.Path(__file__).resolve().parent.parent))
DATA_DIR = _BASE / 'data'
DATA_DIR.mkdir(parents=True, exist_ok=True)
TASKS_FILE = DATA_DIR / 'tasks.json'
REGISTRY_FILE = _BASE / 'agents' / 'registry.json'
EVOLUTION_FILE = DATA_DIR / 'evolution_log.json'
KANBAN_DB = pathlib.Path(os.environ.get('KANBAN_DB',
    str(pathlib.Path.home() / '.hermes' / 'kanban.db')))

STATIC_DIR = pathlib.Path(__file__).parent / 'static'
STATIC_DIR.mkdir(exist_ok=True)

PORT = 7892
HOST = '0.0.0.0'

_START_TIME = datetime.datetime.now()


def _sqlite_tasks(limit=200):
    """从Kanban SQLite读取任务（所有workspace_kind=scratch的任务）"""
    if not KANBAN_DB.exists():
        return []
    try:
        conn = sqlite3.connect(str(KANBAN_DB))
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM tasks ORDER BY created_at DESC LIMIT ?",
            (limit,)
        ).fetchall()
        conn.close()
        tasks = []
        for r in rows:
            task = dict(r)
            if task.get('body'):
                try:
                    task['body_parsed'] = json.loads(task['body'])
                except Exception:
                    task['body_parsed'] = {}
            # Map status → state for frontend compatibility
            task['state'] = task.get('status', 'todo')
            tasks.append(task)
        return tasks
    except Exception as e:
        print(f"[WARN] SQLite read failed: {e}")
        return []


def _task_body(task_id, board='hermestrix'):
    """读取单个任务body"""
    if not KANBAN_DB.exists():
        return {}
    try:
        conn = sqlite3.connect(str(KANBAN_DB))
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT body FROM tasks WHERE id=? AND board=?",
            (str(task_id), board)
        ).fetchone()
        conn.close()
        if row and row['body']:
            return json.loads(row['body'])
    except Exception:
        pass
    return {}


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(pathlib.Path(__file__).parent), **kwargs)

    # ── GET handlers ────────────────────────────────────────────

    def do_GET(self):
        if self.path == '/api/tasks':
            self.send_json(self._get_tasks())
        elif self.path == '/api/registry':
            self.send_json(self._get_registry())
        elif self.path == '/api/stats':
            self.send_json(self._get_stats())
        elif self.path == '/api/health':
            self.send_json(self._get_health())
        elif self.path == '/api/hermes/status':
            self.send_json(self._get_hermes_status())
        elif self.path == '/api/cron/jobs':
            self.send_json(self._get_cron_jobs())
        elif self.path == '/api/agents':
            self.send_json(self._get_agents())
        elif self.path.startswith('/pixel'):
            self.path = '/pixel/index.html'
            super().do_GET()
        elif self.path == '/' or self.path == '/index.html':
            self.path = '/index.html'
            super().do_GET()
        else:
            super().do_GET()

    # ── POST handlers ────────────────────────────────────────────

    def do_POST(self):
        if self.path == '/api/tasks':
            self._handle_create_task()
        elif self.path == '/api/cmd':
            self._handle_send_cmd()
        elif self.path == '/api/cron/pause':
            self._handle_cron_pause()
        elif self.path == '/api/cron/resume':
            self._handle_cron_resume()
        elif self.path == '/api/tasks/flow':
            self._handle_flow_task()
        else:
            self.send_error(404)

    # ── Task CRUD ────────────────────────────────────────────────

    def _get_tasks(self):
        limit = int(self._query_param('limit') or 200)
        tasks = _sqlite_tasks(limit=limit)
        return tasks

    def _handle_create_task(self):
        """POST /api/tasks — 创建新任务，触发步骤链"""
        try:
            length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(length).decode('utf-8') if length else '{}'
            data = json.loads(body) if body.strip() else {}
        except Exception as e:
            self.send_json({'ok': False, 'error': f'Invalid JSON: {e}'})
            return

        title = data.get('title') or data.get('task_title') or '新任务'
        description = data.get('description') or data.get('desc') or ''
        priority = data.get('priority', 'normal')

        # 使用真实的玄机阁步骤链创建任务
        sys.path.insert(0, str(_BASE))
        sys.path.insert(0, str(_BASE / 'hermes-agent'))
        try:
            from hermes_cli.kanban_db import connect
            from workflow.kanban_step_chain import create_root_task, build_step_chain
        except ImportError as e:
            self.send_json({'ok': False, 'error': f'Import error: {e}'})
            return

        try:
            # 1. 创建根任务
            root_id = create_root_task(
                title=title,
                description=description,
                routing={},
            )
            # 2. 构建6步子任务链
            step_ids = build_step_chain(
                task_id=root_id,
                title=title,
                routing={},
            )
        except Exception as e:
            self.send_json({'ok': False, 'error': f'Step chain error: {e}'})
            return

        self.send_json({
            'ok': True,
            'task_id': root_id,
            'title': title,
            'message': f'任务已创建: {title}（{len(step_ids)}个步骤）',
            'step_ids': step_ids,
        })

    def _handle_flow_task(self):
        """POST /api/tasks/flow — 将任务流转到下一状态"""
        try:
            length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(length).decode('utf-8') if length else '{}'
            data = json.loads(body) if body.strip() else {}
        except Exception as e:
            self.send_json({'ok': False, 'error': f'Invalid JSON: {e}'})
            return

        task_id = data.get('task_id')
        action = data.get('action')  # 'next' | 'cancel' | 'retry'

        if not task_id:
            self.send_json({'ok': False, 'error': 'task_id required'})
            return

        # Update task status in DB (real schema: status, no board)
        if KANBAN_DB.exists():
            try:
                conn = sqlite3.connect(str(KANBAN_DB))
                import time
                now_ts = int(time.time())
                if action == 'cancel':
                    conn.execute(
                        "UPDATE tasks SET status=? WHERE id=?",
                        ('archived', str(task_id))
                    )
                elif action == 'retry':
                    conn.execute(
                        "UPDATE tasks SET status=? WHERE id=?",
                        ('ready', str(task_id))
                    )
                elif action == 'done':
                    conn.execute(
                        "UPDATE tasks SET status=?, completed_at=? WHERE id=?",
                        ('done', now_ts, str(task_id))
                    )
                conn.commit()
                conn.close()
                self.send_json({'ok': True, 'message': f'任务 {task_id} 已{action}'})
                return
            except Exception as e:
                self.send_json({'ok': False, 'error': str(e)})
                return

        self.send_json({'ok': False, 'error': 'Kanban DB not found'})

    # ── Hermes Command ────────────────────────────────────────────

    def _handle_send_cmd(self):
        """POST /api/cmd — 发送命令到Hermes（通过飞书bot或直接CLI）"""
        try:
            length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(length).decode('utf-8') if length else '{}'
            data = json.loads(body) if body.strip() else {}
        except Exception as e:
            self.send_json({'ok': False, 'error': f'Invalid JSON: {e}'})
            return

        cmd = data.get('cmd') or data.get('message') or data.get('prompt', '')
        channel = data.get('channel', 'local')  # 'feishu' | 'local'

        if not cmd.strip():
            self.send_json({'ok': False, 'error': 'Empty command'})
            return

        result = {'ok': False, 'output': ''}

        if channel == 'feishu':
            # 通过飞书CLI发送消息
            result = self._send_feishu(cmd)
        else:
            # 直接执行命令
            result = self._exec_local_cmd(cmd)

        self.send_json(result)

    def _send_feishu(self, message: str) -> dict:
        """通过飞书发送消息"""
        try:
            # 使用lark-cli发送消息到指定chat
            lark_cmd = ['python3', '-m', 'hermes_cli', 'send', '--msg', message]
            proc = subprocess.run(
                lark_cmd,
                capture_output=True,
                text=True,
                timeout=15,
                cwd=str(_BASE),
            )
            return {
                'ok': proc.returncode == 0,
                'output': proc.stdout[:500] if proc.stdout else proc.stderr[:500],
            }
        except Exception as e:
            return {'ok': False, 'output': str(e)}

    def _exec_local_cmd(self, cmd: str) -> dict:
        """执行本地命令"""
        try:
            # 使用hermes_cli执行
            proc = subprocess.run(
                ['python3', '-m', 'hermes_cli'] + cmd.split(),
                capture_output=True,
                text=True,
                timeout=30,
                cwd=str(_BASE),
                env={**os.environ, 'HERMESTRIX_HOME': str(_BASE)},
            )
            return {
                'ok': proc.returncode == 0,
                'output': proc.stdout[:1000] if proc.stdout else proc.stderr[:1000],
                'exit_code': proc.returncode,
            }
        except Exception as e:
            return {'ok': False, 'output': str(e)}

    # ── Cron Jobs ────────────────────────────────────────────────

    def _get_cron_jobs(self) -> dict:
        """获取cron任务列表"""
        try:
            from hermes_tools import cronjob  # type: ignore
            jobs = cronjob.list()
            job_list = []
            for j in (jobs or []):
                job_list.append({
                    'id': j.get('id', ''),
                    'name': j.get('name', ''),
                    'schedule': j.get('schedule', ''),
                    'enabled': j.get('enabled', True),
                    'last_run': j.get('last_run'),
                    'next_run': j.get('next_run'),
                })
            return {'ok': True, 'jobs': job_list}
        except Exception as e:
            # Fallback: read from cron job file
            cron_file = DATA_DIR / 'cron_jobs.json'
            if cron_file.exists():
                try:
                    return {'ok': True, 'jobs': json.loads(cron_file.read_text())}
                except Exception:
                    pass
            return {'ok': True, 'jobs': [], 'error': str(e)}

    def _handle_cron_pause(self):
        """暂停cron任务"""
        try:
            length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(length).decode('utf-8') if length else '{}'
            data = json.loads(body) if body.strip() else {}
        except Exception:
            data = {}
        job_id = data.get('job_id')
        if job_id:
            try:
                from hermes_tools import cronjob  # type: ignore
                cronjob.pause(job_id)
                self.send_json({'ok': True, 'message': f'Job {job_id} paused'})
            except Exception:
                self.send_json({'ok': True, 'message': 'Cron pause not available (using file-based)'})
        else:
            self.send_json({'ok': False, 'error': 'job_id required'})

    def _handle_cron_resume(self):
        """恢复cron任务"""
        try:
            length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(length).decode('utf-8') if length else '{}'
            data = json.loads(body) if body.strip() else {}
        except Exception:
            data = {}
        job_id = data.get('job_id')
        if job_id:
            try:
                from hermes_tools import cronjob  # type: ignore
                cronjob.resume(job_id)
                self.send_json({'ok': True, 'message': f'Job {job_id} resumed'})
            except Exception:
                self.send_json({'ok': True, 'message': 'Cron resume not available'})
        else:
            self.send_json({'ok': False, 'error': 'job_id required'})

    # ── Data Providers ────────────────────────────────────────────

    def _get_registry(self) -> dict:
        if not REGISTRY_FILE.exists():
            return {"roles": []}
        try:
            return json.loads(REGISTRY_FILE.read_text(encoding='utf-8'))
        except Exception:
            return {"roles": []}

    def _get_stats(self) -> dict:
        tasks = _sqlite_tasks(limit=500)
        states = {}
        for t in tasks:
            s = t.get('status', 'unknown')
            states[s] = states.get(s, 0) + 1

        return {
            'total': len(tasks),
            'by_status': states,
            'updated_at': datetime.datetime.now().isoformat(),
        }

    def _get_health(self) -> dict:
        uptime = (datetime.datetime.now() - _START_TIME).total_seconds()
        return {
            'status': 'ok',
            'uptime_seconds': int(uptime),
            'uptime_human': self._fmt_uptime(uptime),
            'timestamp': datetime.datetime.now().isoformat(),
            'kanban_db': str(KANBAN_DB),
            'db_exists': KANBAN_DB.exists(),
        }

    def _get_hermes_status(self) -> dict:
        """获取Hermes Agent运行状态"""
        # Check if hermes-agent is running
        try:
            proc = subprocess.run(
                ['pgrep', '-f', 'hermes-agent'],
                capture_output=True,
                text=True,
            )
            hermes_running = proc.returncode == 0
            pids = proc.stdout.strip().split('\n') if proc.stdout.strip() else []
        except Exception:
            hermes_running = False
            pids = []

        # Check watchdog process
        try:
            proc2 = subprocess.run(
                ['pgrep', '-f', 'watchdog'],
                capture_output=True,
                text=True,
            )
            watchdog_running = proc2.returncode == 0
        except Exception:
            watchdog_running = False

        # Check dashboard server
        try:
            proc3 = subprocess.run(
                ['pgrep', '-f', 'dashboard.server'],
                capture_output=True,
                text=True,
            )
            dashboard_pid = proc3.stdout.strip().split('\n')[0] if proc3.stdout.strip() else None
        except Exception:
            dashboard_pid = None

        return {
            'hermes_running': hermes_running,
            'hermes_pids': [p for p in pids if p],
            'watchdog_running': watchdog_running,
            'dashboard_pid': dashboard_pid,
            'dashboard_port': PORT,
        }

    def _get_agents(self) -> dict:
        """获取Agent详细信息"""
        agents = []
        agents_dir = _BASE / 'agents'
        if agents_dir.exists():
            for d in agents_dir.iterdir():
                if not d.is_dir() or d.name.startswith('.'):
                    continue
                meta_file = d / 'METADATA.yaml'
                soul_file = d / 'SOUL.md'
                meta = {}
                if meta_file.exists():
                    try:
                        import yaml
                        meta = yaml.safe_load(meta_file.read_text()) or {}
                    except Exception:
                        pass
                agents.append({
                    'id': d.name,
                    'name': meta.get('name', d.name),
                    'role': meta.get('role_name', ''),
                    'dept': meta.get('department', ''),
                    'description': meta.get('description', ''),
                    'has_soul': soul_file.exists(),
                })
        return {'ok': True, 'agents': agents}

    # ── Utilities ────────────────────────────────────────────────

    def _query_param(self, key: str) -> str | None:
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)
        vals = params.get(key, [])
        return vals[0] if vals else None

    def _trigger_watchdog(self, task_id: str):
        """通知watchdog处理新任务"""
        try:
            # 写入trigger文件
            trigger_file = DATA_DIR / 'watchdog_trigger.json'
            triggers = []
            if trigger_file.exists():
                try:
                    triggers = json.loads(trigger_file.read_text())
                except Exception:
                    pass
            triggers.append({
                'action': 'process_task',
                'task_id': task_id,
                'timestamp': datetime.datetime.now().isoformat(),
            })
            trigger_file.write_text(json.dumps(triggers[-10:], ensure_ascii=False))
        except Exception as e:
            print(f"[WARN] Trigger failed: {e}")

    @staticmethod
    def _fmt_uptime(seconds: float) -> str:
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        return f"{h}h {m}m {s}s"

    def send_json(self, data: dict, status=200):
        response = json.dumps(data, ensure_ascii=False, indent=2)
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.send_header('Content-Length', len(response.encode('utf-8')))
        self.end_headers()
        self.wfile.write(response.encode('utf-8'))

    def log_message(self, format, *args):
        pass  # 静默日志


def main():
    global PORT, HOST
    for i, a in enumerate(sys.argv):
        if a == '--port' and i+1 < len(sys.argv):
            PORT = int(sys.argv[i+1])
        if a == '--host' and i+1 < len(sys.argv):
            HOST = sys.argv[i+1]

    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer((HOST, PORT), Handler) as httpd:
        print(f"\n\n⚔️ 玄机阁 Dashboard v2")
        print(f"   http://{HOST}:{PORT}")
        print(f"   看板: http://{HOST}:{PORT}/index.html")
        print(f"   API:  http://{HOST}:{PORT}/api/tasks")
        print(f"\n   按 Ctrl+C 停止\n")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n已停止")

if __name__ == '__main__':
    main()
