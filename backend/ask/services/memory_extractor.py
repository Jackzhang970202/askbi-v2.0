from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Dict, List, Tuple
import logging

logger = logging.getLogger("askbi.memory_extractor")

USER_PROFILE_HINTS = (
    ("preference", ["以后", "今后", "默认", "尽量", "习惯", "偏好", "请用", "统一用"]),
    ("constraint", ["一律", "必须", "只能", "不要", "禁止", "口径", "按.*口径"]),
    ("background", ["我是", "我们是", "我负责", "我们负责", "我的工作", "我们部门"]),
    ("goal", ["长期", "持续", "一直", "后续都", "主要关注"]),
)

from typing import Any, Dict, List




from openai import OpenAI

from core import _load_config


USER_KINDS = {"preference", "background", "constraint", "goal"}
SESSION_KINDS = {"goal", "subject", "decision", "state"}


class MemoryExtractor:
    def __init__(self) -> None:
        conf = _load_config()
        self.client = OpenAI(api_key=conf.get("api_key", ""), base_url=conf.get("base_url", ""), timeout=60.0)
        self.model = conf.get("model", "")

    def build_dedupe_key(self, candidate: Dict[str, Any]) -> str:
        text = f"{candidate.get('scope')}|{candidate.get('memory_kind')}|{candidate.get('summary')}|{candidate.get('profile_text')}"
        return hashlib.sha256(text.encode("utf-8")).hexdigest()[:24]

    def extract_after_turn(self, payload: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
        question = str(payload.get("question") or "").strip()
        if self._should_force_user_profile(question):
            logger.info("memory extractor 命中用户画像规则: %s", question[:120])
            return self._normalize(self._heuristic_extract(payload, include_user=True))
        prompt = self._build_prompt(payload)
        try:
            result = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "你是记忆抽取器。只输出 JSON，不要 markdown。"},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.1,
                max_tokens=1200,
                extra_body={"enable_thinking": False},
            )
            text = (result.choices[0].message.content or "").strip()
            logger.info("memory extractor llm 输出: %s", text[:300])
            data = self._parse_json(text)
        except Exception as exc:
            logger.warning("memory extractor llm 失败，回退 heuristic: %s", exc)
            data = self._heuristic_extract(payload, include_user=False)
        return self._normalize(data)

    def _build_prompt(self, payload: Dict[str, Any]) -> str:
        return f"""请从本轮对话中抽取有价值记忆。

输出 JSON 格式：
{{
  "user_memories": [{{"memory_kind":"preference|background|constraint|goal", "summary":"...", "profile_text":"...", "profile_json":{{}} }}],
  "session_memories": [{{"memory_kind":"goal|subject|decision|state", "summary":"...", "profile_text":"...", "profile_json":{{}} }}]
}}

规则：
1. 用户画像只保存跨会话长期有用的信息。
2. 会话记忆只保存当前会话内目标、主题、决策、状态。
3. 不要保存临时寒暄、无业务价值内容。
4. 不确定时少写，允许返回空数组。

本轮数据：
{json.dumps(payload, ensure_ascii=False, indent=2, default=str)[:6000]}
"""

    def _parse_json(self, text: str) -> Dict[str, Any]:
        clean = text.strip()
        if "```json" in clean:
            clean = clean.split("```json", 1)[1].split("```", 1)[0]
        elif "```" in clean:
            clean = clean.split("```", 1)[1].split("```", 1)[0]
        return json.loads(clean)

    def _should_force_user_profile(self, question: str) -> bool:
        for _, hints in USER_PROFILE_HINTS:
            for hint in hints:
                if hint.startswith("按.*"):
                    if re.search(hint, question):
                        return True
                elif hint in question:
                    return True
        return False

    def _infer_user_profile(self, question: str) -> List[Dict[str, Any]]:
        items: List[Dict[str, Any]] = []
        for kind, hints in USER_PROFILE_HINTS:
            for hint in hints:
                matched = re.search(hint, question) if hint.startswith("按.*") else (hint in question)
                if matched:
                    items.append({
                        "memory_kind": kind,
                        "summary": question[:80],
                        "profile_text": question[:200],
                        "profile_json": {"question": question, "source": "heuristic"},
                    })
                    return items
        return items

    def _heuristic_extract(self, payload: Dict[str, Any], include_user: bool = False) -> Dict[str, Any]:
        question = str(payload.get("question") or "").strip()
        context = payload.get("context") or {}
        user_memories = self._infer_user_profile(question) if include_user and question else []
        session_memories: List[Dict[str, Any]] = []
        if question:
            session_memories.append({
                "memory_kind": "goal",
                "summary": question[:80],
                "profile_text": f"用户当前会话目标：{question[:200]}",
                "profile_json": {"question": question},
            })
        if context and any(context.get(key) for key in ["datasource_name", "ref_name", "ref_id"]):
            session_memories.append({
                "memory_kind": "state",
                "summary": "当前会话上下文",
                "profile_text": f"当前会话上下文：{json.dumps(context, ensure_ascii=False, default=str)}",
                "profile_json": context,
            })
        return {"user_memories": user_memories, "session_memories": session_memories}

    def _normalize(self, data: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
        user_items = []
        for item in data.get("user_memories") or []:
            kind = item.get("memory_kind")
            text = str(item.get("profile_text") or "").strip()
            if kind in USER_KINDS and text:
                item["scope"] = "user"
                item["dedupe_key"] = item.get("dedupe_key") or self.build_dedupe_key(item)
                user_items.append(item)
        session_items = []
        for item in data.get("session_memories") or []:
            kind = item.get("memory_kind")
            text = str(item.get("profile_text") or "").strip()
            if kind in SESSION_KINDS and text:
                item["scope"] = "session"
                item["dedupe_key"] = item.get("dedupe_key") or self.build_dedupe_key(item)
                session_items.append(item)
        return {"user_memories": user_items, "session_memories": session_items}


memory_extractor = MemoryExtractor()
