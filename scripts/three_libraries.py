#!/usr/bin/env python3
"""
Hermestrix 三库管理系统
记忆库 / 技能库 / 知识库

用法:
  python3 scripts/three_libraries.py archive-memory [任务ID] --type [类型] --result [好/坏] --detail "[描述]"
  python3 scripts/three_libraries.py archive-skill [任务ID] --method "[方法名]" --effect "[效果]"
  python3 scripts/three_libraries.py archive-knowledge [任务ID] --domain "[领域]" --content "[知识]"
  python3 scripts/three_libraries.py search-memory --type [类型] --limit 5
  python3 scripts/three_libraries.py search-skill --domain [领域] --limit 5
  python3 scripts/three_libraries.py search-knowledge --query "[查询]"
  python3 scripts/three_libraries.py list
"""
import datetime
import json
import pathlib
import sys
import os

_BASE = pathlib.Path(os.environ.get('HERMESTRIX_HOME',
           pathlib.Path(__file__).resolve().parent.parent))
DATA_DIR = _BASE / 'three_libs'
DATA_DIR.mkdir(parents=True, exist_ok=True)

MEMORY_DIR = DATA_DIR / 'memory'
SKILLS_DIR = DATA_DIR / 'skills'
KNOWLEDGE_DIR = DATA_DIR / 'knowledge'

for d in [MEMORY_DIR, SKILLS_DIR, KNOWLEDGE_DIR]:
    d.mkdir(parents=True, exist_ok=True)

def now_iso():
    return datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%S')

def _atomic_write(path, data):
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    os.replace(tmp, path)

def _read_json(path):
    if not path.exists(): return None
    try: return json.loads(path.read_text(encoding='utf-8'))
    except: return None

def _atomic_json_update(path, modifier, default=None):
    for attempt in range(3):
        try:
            data = _read_json(path) or default
            data = modifier(data)
            _atomic_write(path, data)
            return
        except Exception:
            if attempt == 2: raise
            import time; time.sleep(0.1 * (attempt + 1))

# ── 记忆库 ──────────────────────────────────────────────
MEMORY_INDEX = DATA_DIR / 'memory_index.json'

def archive_memory(task_id, mem_type, result, detail):
    """归档执行记忆"""
    entry = {
        "id": f"mem_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}",
        "task_id": task_id,
        "type": mem_type,  # 调研/创作/技术
        "result": result,  # 好/坏
        "detail": detail,
        "createdAt": now_iso()
    }
    # 按类型分目录存储
    type_dir = MEMORY_DIR / mem_type
    type_dir.mkdir(exist_ok=True)
    fpath = type_dir / f"{entry['id']}.json"
    _atomic_write(fpath, entry)
    # 更新索引
    def modifier(idx):
        if idx is None: idx = {"entries": [], "by_type": {}}
        idx["entries"].insert(0, {"id": entry["id"], "type": mem_type, "result": result, "task_id": task_id, "createdAt": entry["createdAt"]})
        idx["by_type"].setdefault(mem_type, []).insert(0, entry["id"])
        return idx
    _atomic_json_update(MEMORY_INDEX, modifier, {"entries": [], "by_type": {}})
    print(f"[三库] 记忆归档完成: {entry['id']} ({mem_type}/{result})")

def search_memory(mem_type=None, limit=5):
    """检索记忆"""
    idx = _read_json(MEMORY_INDEX) or {"entries": [], "by_type": {}}
    if mem_type:
        ids = idx.get("by_type", {}).get(mem_type, [])[:limit]
    else:
        ids = [e["id"] for e in idx.get("entries", [])[:limit]]
    results = []
    for eid in ids:
        for f in MEMORY_DIR.rglob(f"{eid}.json"):
            results.append(_read_json(f))
    return results

# ── 技能库 ──────────────────────────────────────────────
SKILLS_INDEX = DATA_DIR / 'skills_index.json'

def archive_skill(task_id, method, effect):
    """归档技能"""
    entry = {
        "id": f"skill_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}",
        "task_id": task_id,
        "method": method,
        "effect": effect,
        "createdAt": now_iso()
    }
    fpath = SKILLS_DIR / f"{entry['id']}.json"
    _atomic_write(fpath, entry)
    def modifier(idx):
        if idx is None: idx = {"entries": [], "by_method": {}}
        idx["entries"].insert(0, {"id": entry["id"], "method": method, "task_id": task_id, "createdAt": entry["createdAt"]})
        idx["by_method"].setdefault(method, []).insert(0, entry["id"])
        return idx
    _atomic_json_update(SKILLS_INDEX, modifier, {"entries": [], "by_method": {}})
    print(f"[三库] 技能归档完成: {entry['id']} ({method})")

def search_skill(domain=None, limit=5):
    """检索技能"""
    idx = _read_json(SKILLS_INDEX) or {"entries": [], "by_method": {}}
    if domain:
        ids = idx.get("by_method", {}).get(domain, [])[:limit]
    else:
        ids = [e["id"] for e in idx.get("entries", [])[:limit]]
    results = []
    for eid in ids:
        for f in SKILLS_DIR.rglob(f"{eid}.json"):
            results.append(_read_json(f))
    return results

# ── 知识库 ──────────────────────────────────────────────
KNOWLEDGE_INDEX = DATA_DIR / 'knowledge_index.json'

def archive_knowledge(task_id, domain, content):
    """归档知识"""
    entry = {
        "id": f"know_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}",
        "task_id": task_id,
        "domain": domain,
        "content": content,
        "createdAt": now_iso(),
        "updatedAt": now_iso()
    }
    domain_dir = KNOWLEDGE_DIR / domain
    domain_dir.mkdir(exist_ok=True)
    fpath = domain_dir / f"{entry['id']}.json"
    _atomic_write(fpath, entry)
    def modifier(idx):
        if idx is None: idx = {"entries": [], "by_domain": {}}
        idx["entries"].insert(0, {"id": entry["id"], "domain": domain, "task_id": task_id, "createdAt": entry["createdAt"]})
        idx["by_domain"].setdefault(domain, []).insert(0, entry["id"])
        return idx
    _atomic_json_update(KNOWLEDGE_INDEX, modifier, {"entries": [], "by_domain": {}})
    print(f"[三库] 知识归档完成: {entry['id']} ({domain})")

def search_knowledge(query=None, domain=None, limit=5):
    """检索知识"""
    idx = _read_json(KNOWLEDGE_INDEX) or {"entries": [], "by_domain": {}}
    if domain:
        ids = idx.get("by_domain", {}).get(domain, [])[:limit]
    else:
        ids = [e["id"] for e in idx.get("entries", [])[:limit]]
    results = []
    for eid in ids:
        for f in KNOWLEDGE_DIR.rglob(f"{eid}.json"):
            data = _read_json(f)
            if query is None or query.lower() in data.get("content", "").lower():
                results.append(data)
    return results[:limit]

def cmd_list():
    mem_idx = _read_json(MEMORY_INDEX) or {}
    skill_idx = _read_json(SKILLS_INDEX) or {}
    know_idx = _read_json(KNOWLEDGE_INDEX) or {}
    print("\n📚 Hermestrix 三库概览")
    print(f"记忆库: {len(mem_idx.get('entries', []))} 条")
    for k, v in mem_idx.get('by_type', {}).items():
        print(f"  - {k}: {len(v)} 条")
    print(f"技能库: {len(skill_idx.get('entries', []))} 条")
    for k, v in skill_idx.get('by_method', {}).items():
        print(f"  - {k}: {len(v)} 条")
    print(f"知识库: {len(know_idx.get('entries', []))} 条")
    for k, v in know_idx.get('by_domain', {}).items():
        print(f"  - {k}: {len(v)} 条")
    print()

# ── CLI ──────────────────────────────────────────────
def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == 'archive-memory':
        task_id = sys.argv[2] if len(sys.argv) > 2 else ''
        kwargs = dict(a.split('=', 1) for a in sys.argv[3:] if '=' in a)
        archive_memory(task_id, kwargs.get('--type','技术'), kwargs.get('--result','好'), kwargs.get('--detail',''))

    elif cmd == 'archive-skill':
        task_id = sys.argv[2] if len(sys.argv) > 2 else ''
        kwargs = dict(a.split('=', 1) for a in sys.argv[3:] if '=' in a)
        archive_skill(task_id, kwargs.get('--method',''), kwargs.get('--effect',''))

    elif cmd == 'archive-knowledge':
        task_id = sys.argv[2] if len(sys.argv) > 2 else ''
        kwargs = dict(a.split('=', 1) for a in sys.argv[3:] if '=' in a)
        archive_knowledge(task_id, kwargs.get('--domain',''), kwargs.get('--content',''))

    elif cmd == 'search-memory':
        kwargs = dict(a.split('=', 1) for a in sys.argv[2:] if '=' in a)
        results = search_memory(kwargs.get('--type'), int(kwargs.get('--limit', 5)))
        for r in results:
            print(f"[{r.get('type')}/{r.get('result')}] {r.get('detail','')[:100]}")

    elif cmd == 'search-skill':
        kwargs = dict(a.split('=', 1) for a in sys.argv[2:] if '=' in a)
        results = search_skill(kwargs.get('--domain'), int(kwargs.get('--limit', 5)))
        for r in results:
            print(f"[{r.get('method')}] {r.get('effect','')[:100]}")

    elif cmd == 'search-knowledge':
        kwargs = dict(a.split('=', 1) for a in sys.argv[2:] if '=' in a)
        results = search_knowledge(kwargs.get('--query'), kwargs.get('--domain'), int(kwargs.get('--limit', 5)))
        for r in results:
            print(f"[{r.get('domain')}] {r.get('content','')[:100]}")

    elif cmd == 'list':
        cmd_list()

    else:
        print(f"未知命令: {cmd}")
        print(__doc__)

if __name__ == '__main__':
    main()
