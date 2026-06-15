"""智能体配置管理器：CRUD + 配置合并 + 内置种子 + 自定义智能体文件生成。"""
from __future__ import annotations

import json
import logging
import os
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from utils.db_utils import db_utils

logger = logging.getLogger(__name__)

# 6 个内置 Agent 的默认 instructions（从现有 agents/*.py 提取）
BUILTIN_AGENTS = [
    {
        "name": "normal_chat_agent",
        "display_name": "普通对话助手",
        "description": "默认普通对话智能体",
        "base_instructions": (
            "你是 AskBI 的默认对话助手。\n\n"
            "当用户尚未选择数据源或团队时，你负责进行正常中文对话。\n"
            "1. 可以回答通用问题、解释系统能力、协助用户明确分析意图。\n"
            "2. 不要伪造数据库结果、SQL 执行结果或 Excel 分析结论。\n"
            "3. 如果用户的问题明显需要数据查询，但当前没有选定数据源，可以直接提醒用户先选择数据源。\n"
            "4. 输出自然、简洁、直接。"
        ),
    },
    {
        "name": "bi_sql_agent",
        "display_name": "BI SQL 专家",
        "description": "PostgreSQL BI 问数 SQL 生成智能体",
        "base_instructions": (
            "你是 PostgreSQL BI 问数 SQL 专家。\n\n"
            "你会收到：\n"
            "1. 用户问题\n"
            "2. 数据源名称\n"
            "3. schema 元数据（表、列、注释、样例）\n"
            "4. 可能的修正反馈\n\n"
            "你的任务：只输出一条 PostgreSQL SELECT SQL。\n\n"
            "硬性要求：\n"
            "1. 只输出 SQL，不要 markdown，不要解释。\n"
            "2. 只能生成 SELECT / WITH ... SELECT 查询。\n"
            "3. 不允许 INSERT / UPDATE / DELETE / ALTER / DROP / CREATE。\n"
            "4. 必须优先使用提出的真实表名和列名。\n"
            "5. 如果需要统计'多少/数量/几条'，优先用 count(*)。\n"
            "6. 如果需要分组、TopN、占比，直接输出可执行 SQL。\n"
            "7. 如果列名大小写敏感，请使用双引号。\n"
            "8. 不要编造不存在的 schema、表、列。"
        ),
    },
    {
        "name": "bi_report_agent",
        "display_name": "BI 报告专家",
        "description": "BI 问数报告生成智能体",
        "base_instructions": (
            "你是 BI 数据分析报告专家。\n\n"
            "你会收到：\n"
            "1. 用户问题\n"
            "2. 真实 SQL\n"
            "3. 真实执行结果\n\n"
            "请输出中文报告：\n"
            "1. 先直接回答问题。\n"
            "2. 只基于真实结果，不要编造数据。\n"
            "3. 如果结果是列表，先总结，再提炼重点。\n"
            "4. 不要输出 SQL、代码、日志。\n"
            "5. 输出只需要报告正文。"
        ),
    },
    {
        "name": "bi_chart_agent",
        "display_name": "BI 图表专家",
        "description": "BI 问数图表生成智能体",
        "base_instructions": (
            "你是 BI 图表配置专家，擅长生成 Vega-Lite v5 规范 JSON。\n\n"
            "你会收到：\n"
            "1. 用户问题\n"
            "2. 真实执行结果\n"
            "3. 分析报告\n\n"
            "请输出符合 Vega-Lite v5 规范的 JSON。\n"
            "1. 只输出 JSON，必须包含 \"$schema\": \"https://vega.github.io/schema/vega-lite/v5.json\"。\n"
            "2. 如果不适合画图，输出 {\"chart_needed\": false}。\n"
            "3. 不要编造字段。\n"
            "4. 使用 data.values 内联数据，mark 中设置 \"background\": \"transparent\"。"
        ),
    },
    {
        "name": "askexcel_code_agent",
        "display_name": "Excel 代码专家",
        "description": "Excel 分析代码生成智能体",
        "base_instructions": (
            "你是 Excel 问数场景下的 Python 数据分析专家，擅长使用 pandas 对 Excel 数据做筛选、聚合、统计与解释。\n\n"
            "你会收到：\n"
            "1. 用户问题\n"
            "2. 文件元数据（文件路径、sheet 名称、列名、示例数据）\n"
            "3. 若上一轮代码执行失败，会收到错误信息\n\n"
            "你的唯一任务是生成一段可执行 Python 代码。\n\n"
            "硬性要求：\n"
            "1. 只输出 Python 代码本身，不要加 markdown 代码块，不要解释。\n"
            "2. 执行环境已预置：pd、json、os、FILE_LIST、FILE_METADATA、RESULT。\n"
            "3. 必须优先参考 FILE_METADATA 里的真实列名。\n"
            "4. 必须把最终结果赋值给 RESULT，并在最后 print(RESULT)。"
        ),
    },
    {
        "name": "askexcel_report_agent",
        "display_name": "Excel 报告专家",
        "description": "Excel 分析报告生成智能体",
        "base_instructions": (
            "你是数据分析报告专家。\n\n"
            "你会收到：\n"
            "1. 用户问题\n"
            "2. 真实执行结果\n"
            "3. 文件元数据摘要\n\n"
            "请输出中文分析报告，要求：\n"
            "1. 直接回答问题。\n"
            "2. 结论必须基于真实结果，不要编造数据。\n"
            "3. 结构清晰，适合直接展示给业务用户。\n"
            "4. 不要输出代码、SQL、图表配置、执行日志。\n"
            "5. 输出只需要报告正文。"
        ),
    },
    {
        "name": "askexcel_chart_agent",
        "display_name": "Excel 图表专家",
        "description": "Excel 分析图表生成智能体",
        "base_instructions": (
            "你是图表配置生成专家，擅长生成 Vega-Lite v5 规范 JSON。\n\n"
            "你会收到：\n"
            "1. 用户问题\n"
            "2. 真实执行结果\n"
            "3. 分析报告\n\n"
            "请根据数据特征生成符合 Vega-Lite v5 规范的 JSON。\n\n"
            "硬性要求：\n"
            "1. 只输出 JSON 对象，不要加 markdown 代码块，不要解释。\n"
            "2. 必须是合法 JSON，必须包含 \"$schema\": \"https://vega.github.io/schema/vega-lite/v5.json\"。\n"
            "3. 优先输出柱状图(bar)、折线图(line)、饼图(arc)三类之一。\n"
            "4. 使用 data.values 内联数据，mark 中设置 \"background\": \"transparent\"。\n"
            "5. 如果结果不适合做图，输出：{\"chart_needed\": false}\n"
            "6. 不要编造不存在的数据字段。"
        ),
    },
]


def _get_default_model_config() -> Dict[str, Any]:
    """从 config.json 读取默认模型配置。"""
    try:
        import json as _json
        from pathlib import Path
        cfg_path = Path(__file__).resolve().parents[3] / "config.json"
        if cfg_path.exists():
            with open(cfg_path, "r", encoding="utf-8") as f:
                cfg = _json.load(f)
            return {
                "model": cfg.get("model", ""),
                "temperature": cfg.get("temperature", 0.1),
                "api_key": cfg.get("api_key", ""),
                "base_url": cfg.get("base_url", ""),
            }
        return {"model": "", "temperature": 0.1, "api_key": "", "base_url": ""}
    except Exception:
        return {"model": "", "temperature": 0.1, "api_key": "", "base_url": ""}


class AgentManager:
    """智能体 CRUD 与配置合并。"""

    def __init__(self):
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._cache_ts: float = 0
        self._cache_ttl = 60

    def _invalidate_cache(self):
        self._cache.clear()
        self._cache_ts = 0

    def list_agents(self) -> List[Dict[str, Any]]:
        return db_utils.list_agents()

    def get_agent(self, agent_id: int) -> Optional[Dict[str, Any]]:
        return db_utils.get_agent(agent_id)

    def get_agent_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """优先从缓存获取，过期则查 DB。"""
        if name in self._cache and time.time() - self._cache_ts <= self._cache_ttl:
            return self._cache[name]
        agent = db_utils.get_agent_by_name(name)
        if agent:
            self._cache[name] = agent
            self._cache_ts = time.time()
        return agent

    def create_agent(self, data: Dict[str, Any], user_id: Optional[int] = None) -> Dict[str, Any]:
        if db_utils.get_agent_by_name(data["name"]):
            return {"success": False, "error": f"智能体名称 '{data['name']}' 已存在"}
        agent_id = db_utils.create_agent(data, user_id)
        if agent_id is None:
            return {"success": False, "error": "创建失败"}
        self._invalidate_cache()
        return {"success": True, "agent": {"id": agent_id, "name": data["name"]}}

    def update_agent(self, agent_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
        agent = db_utils.get_agent(agent_id)
        if not agent:
            return {"success": False, "error": "智能体不存在"}
        # name 字段不可修改
        data.pop("name", None)
        ok = db_utils.update_agent(agent_id, data)
        if ok:
            self._invalidate_cache()
        return {"success": ok, "error": None if ok else "更新失败"}

    def delete_agent(self, agent_id: int) -> Dict[str, Any]:
        agent = db_utils.get_agent(agent_id)
        if not agent:
            return {"success": False, "error": "智能体不存在"}
        if agent.get("is_builtin"):
            return {"success": False, "error": "内置智能体不可删除"}
        ok = db_utils.delete_agent(agent_id)
        if ok:
            self._invalidate_cache()
        return {"success": ok, "error": None if ok else "删除失败"}

    def bind_skills(self, agent_id: int, skill_ids: List[int]) -> Dict[str, Any]:
        agent = db_utils.get_agent(agent_id)
        if not agent:
            return {"success": False, "error": "智能体不存在"}
        # 过滤无效的 skill_id
        valid_ids = []
        for sid in skill_ids:
            if db_utils.get_skill(sid):
                valid_ids.append(sid)
        ok = db_utils.update_agent(agent_id, {"bound_skills": valid_ids})
        if ok:
            self._invalidate_cache()
        return {"success": ok, "bound_skills": valid_ids}

    def get_merged_model_config(self, agent: Dict[str, Any]) -> Dict[str, Any]:
        """合并 agent 自定义配置与全局默认值（字段级覆盖）。"""
        defaults = _get_default_model_config()
        custom = agent.get("model_config") or {}
        merged = {}
        for key in ("model", "temperature", "api_key", "base_url"):
            val = custom.get(key)
            merged[key] = val if val not in (None, "", 0) else defaults.get(key, "")
        return merged

    def get_agent_config(self, agent_name: str, skill_ids: Optional[List[int]] = None) -> Dict[str, Any]:
        """获取 agent 的完整运行时配置（合并后），供工作流使用。
        
        skill_ids: 用户指定的技能 ID 列表，为 None 时使用所有激活技能。
        """
        agent = self.get_agent_by_name(agent_name)
        if not agent:
            # DB 中无记录，回退到内置默认
            for builtin in BUILTIN_AGENTS:
                if builtin["name"] == agent_name:
                    return {
                        "name": agent_name,
                        "instructions": builtin["base_instructions"],
                        "model_config": _get_default_model_config(),
                        "skill_prompt": "",
                    }
            return {"name": agent_name, "instructions": "", "model_config": _get_default_model_config(), "skill_prompt": ""}

        # 从 DB 加载
        instructions = agent.get("base_instructions", "")
        model_config = self.get_merged_model_config(agent)

        # 注入技能
        from backend.ask.skills.skill_registry import skill_registry
        skill_prompt = skill_registry.get_active_skill_instructions(agent_name, datasource_name=None, skill_ids=skill_ids)

        return {
            "name": agent_name,
            "instructions": instructions,
            "model_config": model_config,
            "skill_prompt": skill_prompt,
        }

    def seed_builtin_agents(self):
        """幂等写入 6 个内置智能体。"""
        for a in BUILTIN_AGENTS:
            if db_utils.get_agent_by_name(a["name"]):
                continue
            db_utils.create_agent(
                {**a, "is_builtin": True, "is_active": True},
                user_id=None,
            )
            logger.info("已创建内置智能体: %s", a["name"])

    def create_custom_agent(self, data: Dict[str, Any], user_id: Optional[int] = None) -> Dict[str, Any]:
        """创建自定义智能体: DB 记录 + 自动生成 .py 文件。"""
        if db_utils.get_agent_by_name(data["name"]):
            return {"success": False, "error": f"智能体名称 '{data['name']}' 已存在"}

        if not re.match(r'^[a-zA-Z][a-zA-Z0-9_]*$', data["name"]):
            return {"success": False, "error": "智能体名称只能包含字母、数字和下划线，且必须以字母开头"}

        agents_custom_dir = Path(__file__).resolve().parent.parent / "agents_custom"
        agents_custom_dir.mkdir(parents=True, exist_ok=True)
        file_name = f"{data['name']}.py"
        file_path = str(agents_custom_dir / file_name)

        if os.path.exists(file_path):
            return {"success": False, "error": f"文件已存在: {file_name}"}

        try:
            self._generate_agent_py_file(file_path, data["base_instructions"])
        except Exception as e:
            return {"success": False, "error": f"生成 .py 文件失败: {e}"}

        db_data = {
            "name": data["name"],
            "display_name": data["display_name"],
            "description": data.get("description", ""),
            "base_instructions": data["base_instructions"],
            "is_builtin": False,
            "is_active": True,
            "agent_type": data.get("agent_type", "specialist"),
            "file_path": file_path,
            "role_description": data.get("role_description", ""),
            "capabilities": data.get("capabilities", []),
        }
        agent_id = db_utils.create_agent(db_data, user_id)
        if agent_id is None:
            try:
                os.remove(file_path)
            except OSError:
                pass
            return {"success": False, "error": "DB 创建失败"}

        self._invalidate_cache()
        return {"success": True, "agent": {"id": agent_id, "name": data["name"], "file_path": file_path}}

    def update_custom_agent(self, agent_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
        """更新自定义智能体: 同步更新 .py 文件。"""
        agent = db_utils.get_agent(agent_id)
        if not agent:
            return {"success": False, "error": "智能体不存在"}
        if agent.get("is_builtin"):
            return {"success": False, "error": "内置智能体不可通过此方法修改"}

        if "base_instructions" in data and agent.get("file_path"):
            try:
                self._generate_agent_py_file(agent["file_path"], data["base_instructions"])
            except Exception as e:
                return {"success": False, "error": f"更新 .py 文件失败: {e}"}

        data.pop("name", None)
        ok = db_utils.update_agent(agent_id, data)
        if ok:
            self._invalidate_cache()
        return {"success": ok, "error": None if ok else "更新失败"}

    def delete_custom_agent(self, agent_id: int) -> Dict[str, Any]:
        """删除自定义智能体: 删除 .py 文件 + DB 记录。"""
        agent = db_utils.get_agent(agent_id)
        if not agent:
            return {"success": False, "error": "智能体不存在"}
        if agent.get("is_builtin"):
            return {"success": False, "error": "内置智能体不可删除"}

        file_path = agent.get("file_path")
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except OSError:
                pass

        ok = db_utils.delete_agent(agent_id)
        if ok:
            self._invalidate_cache()
        return {"success": ok, "error": None if ok else "删除失败"}

    @staticmethod
    def _generate_agent_py_file(file_path: str, instructions: str) -> None:
        """生成自定义智能体的 .py 文件。"""
        safe_instructions = instructions.replace('"""', '\\"""')
        content = f'''# 自动生成 - 通过管理页面修改，请勿手动编辑
from openai import OpenAI
from core import _load_config

INSTRUCTIONS = """
{safe_instructions}
"""


def run(user_input: str, context: dict = None) -> str:
    """执行智能体任务。"""
    conf = _load_config()
    client = OpenAI(api_key=conf["api_key"], base_url=conf["base_url"], timeout=90.0)
    model = conf["model"]

    system_prompt = INSTRUCTIONS
    if context and context.get("skill_prompt"):
        system_prompt = f"{{system_prompt}}\\n{{context['skill_prompt']}}"

    messages = [{{"role": "system", "content": system_prompt}}]
    if context and context.get("history"):
        messages.extend(context["history"])
    messages.append({{"role": "user", "content": user_input}})

    result = client.chat.completions.create(
        model=model, messages=messages, temperature=0.1,
        extra_body={{"enable_thinking": False}},
    )
    return (result.choices[0].message.content or "").strip()
'''
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)


agent_manager = AgentManager()
