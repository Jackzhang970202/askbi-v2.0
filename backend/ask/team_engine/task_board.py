"""任务看板: Tasks 模式的任务管理（创建、状态追踪、依赖关系）。"""
from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional


class TaskBoard:
    """管理任务列表，支持依赖关系和状态追踪。"""

    def __init__(self):
        self._tasks: Dict[str, Dict[str, Any]] = {}

    def add(self, task_data: Dict[str, Any]) -> str:
        """添加新任务，返回任务 ID。"""
        task_id = str(uuid.uuid4())[:8]
        self._tasks[task_id] = {
            "id": task_id,
            "title": task_data.get("title", ""),
            "description": task_data.get("description", ""),
            "assignee": task_data.get("assignee", ""),
            "depends_on": task_data.get("depends_on", []),
            "status": "pending",
            "result": None,
            "error": None,
        }
        return task_id

    def update_status(self, task_id: str, status: str) -> None:
        if task_id in self._tasks:
            self._tasks[task_id]["status"] = status

    def complete(self, task_id: str, result: str) -> None:
        if task_id in self._tasks:
            self._tasks[task_id]["status"] = "completed"
            self._tasks[task_id]["result"] = result

    def fail(self, task_id: str, error: str) -> None:
        if task_id in self._tasks:
            self._tasks[task_id]["status"] = "failed"
            self._tasks[task_id]["error"] = error
            # 级联失败: 依赖此任务的也标记为 blocked
            for tid, task in self._tasks.items():
                if task_id in task.get("depends_on", []) and task["status"] == "pending":
                    task["status"] = "blocked"
                    task["error"] = f"依赖任务 {task_id} 失败"

    def get_executable(self) -> List[Dict[str, Any]]:
        """获取可执行的任务（pending 且依赖全部完成）。"""
        result = []
        for task in self._tasks.values():
            if task["status"] != "pending":
                continue
            deps = task.get("depends_on", [])
            all_deps_done = all(
                self._tasks.get(dep_id, {}).get("status") == "completed"
                for dep_id in deps
            )
            if all_deps_done:
                result.append(task)
        return result

    def has_pending(self) -> bool:
        """是否还有可执行的 pending 任务。"""
        return any(
            t["status"] == "pending"
            for t in self._tasks.values()
        )

    def get_all_results(self) -> Dict[str, Dict[str, Any]]:
        """获取所有任务结果。"""
        return {
            tid: {
                "title": t["title"],
                "result": t.get("result", ""),
                "status": t["status"],
            }
            for tid, t in self._tasks.items()
        }

    def to_dict(self) -> Dict[str, Dict[str, Any]]:
        return dict(self._tasks)
