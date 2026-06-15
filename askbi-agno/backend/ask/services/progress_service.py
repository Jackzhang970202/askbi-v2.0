from __future__ import annotations

import asyncio
import threading
import time
from typing import Any, Dict, List, Optional


class ProgressService:
    """进度服务：同时支持轮询（list cache）和 SSE 实时推送（asyncio.Queue）。"""

    def __init__(self) -> None:
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._queues: Dict[str, asyncio.Queue] = {}
        self._loops: Dict[str, asyncio.AbstractEventLoop] = {}
        self._lock = threading.Lock()

    # ---------- 初始化 / 清理 ----------

    def init(self, chatid: str) -> None:
        self._cache[chatid] = {"items": [], "done": False, "updated_at": time.time()}

    def register_queue(self, chatid: str, queue: asyncio.Queue, loop: asyncio.AbstractEventLoop) -> None:
        with self._lock:
            self._queues[chatid] = queue
            self._loops[chatid] = loop
            cached_items = list(self._cache.get(chatid, {}).get("items", []))
            is_done = bool(self._cache.get(chatid, {}).get("done", False))
        for item in cached_items:
            loop.call_soon_threadsafe(queue.put_nowait, {"type": "stage", "data": item} if isinstance(item, dict) else {"type": "text", "data": item})
        if is_done:
            loop.call_soon_threadsafe(queue.put_nowait, {"type": "done", "data": {}})

    def unregister_queue(self, chatid: str) -> None:
        with self._lock:
            self._queues.pop(chatid, None)
            self._loops.pop(chatid, None)

    # ---------- 写入（从 worker 线程调用）----------

    def _push_event(self, chatid: str, event: Dict[str, Any]) -> None:
        with self._lock:
            queue = self._queues.get(chatid)
            loop = self._loops.get(chatid)
        if queue and loop and loop.is_running():
            # 使用 run_coroutine_threadsafe 确保事件在正确的事件循环中入队
            try:
                asyncio.run_coroutine_threadsafe(queue.put(event), loop)
            except RuntimeError:
                # 事件循环已关闭，回退到 call_soon_threadsafe
                loop.call_soon_threadsafe(queue.put_nowait, event)
        elif queue:
            # 没有 loop 引用（降级模式），直接入队
            try:
                queue.put_nowait(event)
            except Exception:
                pass

    def append_text(self, chatid: str, text: str) -> None:
        if chatid not in self._cache:
            self.init(chatid)
        self._cache[chatid]["items"].append(text)
        self._cache[chatid]["updated_at"] = time.time()
        self._push_event(chatid, {"type": "text", "data": text})

    def append_event(self, chatid: str, event: str, payload: dict[str, Any]) -> None:
        if chatid not in self._cache:
            self.init(chatid)
        item = {
            "time": time.strftime("%Y-%m-%d %H:%M:%S"),
            "event": event,
            "message": payload,
        }
        self._cache[chatid]["items"].append(item)
        self._cache[chatid]["updated_at"] = time.time()
        self._push_event(chatid, {"type": "stage", "data": item})

    def done(self, chatid: str) -> None:
        if chatid in self._cache:
            self._cache[chatid]["done"] = True
        self._push_event(chatid, {"type": "done", "data": {}})

    # ---------- 读取（轮询兼容）----------

    def get_bi(self, chatid: str, offset: int = 0) -> Dict[str, Any]:
        if chatid not in self._cache:
            return {"items": [], "done": False, "next_offset": 0}
        all_items = self._cache[chatid].get("items", [])
        return {"items": all_items[offset:], "done": self._cache[chatid].get("done", False), "next_offset": len(all_items)}

    def get_excel(self, chatid: str) -> List[Dict[str, Any]]:
        items = self._cache.get(chatid, {}).get("items", [])
        return items if isinstance(items, list) else []

    def clear(self, chatid: str) -> None:
        self._cache.pop(chatid, None)
        self.unregister_queue(chatid)


progress_service = ProgressService()
