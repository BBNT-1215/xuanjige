"""
Hermestrix Engine - Decay Service

记忆衰减管理，防止记忆无限膨胀
"""

import sys
from pathlib import Path
from typing import Optional, List
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).parent.parent))

from engine.memory_manager import MemoryManager, DECAY_HALF_LIFE_DAYS, COLD_STORAGE_THRESHOLD_DAYS

# ============================================================
# DecayService
# ============================================================

class DecayService:
    """
    记忆衰减服务

    职责：
    1. 计算并更新L1记录的衰减权重
    2. 将长期未访问的记忆移到cold storage
    3. 垃圾回收（清理无价值记忆）
    """

    def __init__(self, memory: Optional[MemoryManager] = None):
        self.memory = memory or MemoryManager()

    def apply_decay_to_all(self) -> int:
        """
        对所有L1记录应用衰减权重

        Returns:
            更新的记录数量
        """
        index = self.memory._load_memory_index()
        updated = 0

        for task_id in index.get("tasks", {}).keys():
            if index["tasks"][task_id].get("in_cold_storage"):
                continue

            record = self.memory.get_task_record(task_id)
            if not record:
                continue

            new_weight = self.memory.calculate_decay_weight(
                datetime.fromisoformat(record.completed_at or record.created_at)
            )

            if abs(new_weight - record.decay_weight) > 0.001:
                record.decay_weight = new_weight

                # 保存
                from engine.memory_manager import RAW_DIR
                path = RAW_DIR / f"{task_id}.json"
                import json
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(record.to_dict(), f, ensure_ascii=False, indent=2)
                updated += 1

        return updated

    def archive_cold_memories(self) -> int:
        """
        将超过阈值的记忆移到cold storage

        Returns:
            归档的记忆数量
        """
        threshold_days = COLD_STORAGE_THRESHOLD_DAYS
        index = self.memory._load_memory_index()
        archived = 0

        for task_id, info in list(index["tasks"].items()):
            if info.get("in_cold_storage"):
                continue

            record = self.memory.get_task_record(task_id)
            if not record:
                continue

            days_since = (datetime.now(timezone.utc) - datetime.fromisoformat(
                record.completed_at or record.created_at
            )).days

            if days_since >= threshold_days:
                from engine.memory_manager import RAW_DIR, COLD_DIR
                import json

                raw_path = RAW_DIR / f"{task_id}.json"
                cold_path = COLD_DIR / f"{task_id}.json"

                if raw_path.exists():
                    with open(raw_path, encoding="utf-8") as f:
                        data = json.load(f)

                    data["decay"]["in_cold_storage"] = True
                    data["decay"]["archived_at"] = datetime.now(timezone.utc).isoformat()

                    with open(cold_path, "w", encoding="utf-8") as f:
                        json.dump(data, f, ensure_ascii=False, indent=2)

                    raw_path.unlink()

                    info["in_cold_storage"] = True
                    archived += 1

        # 更新索引
        import json
        index_path = self.memory.home / "three_libs" / "memory" / "index.json"
        with open(index_path, "w", encoding="utf-8") as f:
            json.dump(index, f, ensure_ascii=False, indent=2)

        return archived

    def garbage_collect(self) -> dict:
        """
        垃圾回收：清理低价值记忆

        清理条件（同时满足）：
        1. 在cold storage中
        2. 衰减权重极低（< 0.1）
        3. 超过冷存储时间（> 365天）

        Returns:
            清理统计
        """
        from engine.memory_manager import COLD_DIR
        import json

        removed = 0
        reviewed = 0

        for cold_file in COLD_DIR.glob("*.json"):
            reviewed += 1
            try:
                with open(cold_file, encoding="utf-8") as f:
                    data = json.load(f)

                decay = data.get("decay", {})
                archived_at = decay.get("archived_at", "")

                if not archived_at:
                    continue

                days_since_archive = (datetime.now(timezone.utc) - datetime.fromisoformat(archived_at)).days

                # 清理条件：归档超过365天 且 衰减权重 < 0.1
                if days_since_archive > 365 and decay.get("decay_weight", 1.0) < 0.1:
                    cold_file.unlink()
                    removed += 1

                    # 从索引中移除
                    task_id = cold_file.stem
                    index = self.memory._load_memory_index()
                    if task_id in index["tasks"]:
                        del index["tasks"][task_id]

                    index_path = self.memory.home / "three_libs" / "memory" / "index.json"
                    with open(index_path, "w", encoding="utf-8") as f:
                        json.dump(index, f, ensure_ascii=False, indent=2)

            except Exception:
                continue

        return {"reviewed": reviewed, "removed": removed}

    def get_decay_stats(self) -> dict:
        """
        获取衰减统计
        """
        index = self.memory._load_memory_index()
        tasks = index.get("tasks", {})

        total = len(tasks)
        in_cold = sum(1 for t in tasks.values() if t.get("in_cold_storage"))
        active = total - in_cold

        # 计算衰减分布
        high_weight = 0
        medium_weight = 0
        low_weight = 0

        for task_id in tasks:
            if tasks[task_id].get("in_cold_storage"):
                continue
            record = self.memory.get_task_record(task_id)
            if record:
                w = record.decay_weight
                if w >= 0.8:
                    high_weight += 1
                elif w >= 0.4:
                    medium_weight += 1
                else:
                    low_weight += 1

        return {
            "total_records": total,
            "active_records": active,
            "cold_storage_records": in_cold,
            "decay_distribution": {
                "high_weight": high_weight,
                "medium_weight": medium_weight,
                "low_weight": low_weight
            }
        }
