#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
推荐问题生成器 - 用于 Excel 数据分析
基于大模型生成推荐问题（直接调用 API，不依赖 autogen）
"""

import json
import logging
from pathlib import Path
from typing import List, Dict, Any

from openai import OpenAI

logger = logging.getLogger(__name__)


def _fallback_questions(columns: List[str]) -> List[str]:
    if not columns:
        return [
            '这张表有多少行数据？',
            '各字段分别是什么？',
            '这张表的关键信息有哪些？',
            '可以先做一个数据概览吗？'
        ]
    first = columns[0]
    second = columns[1] if len(columns) > 1 else columns[0]
    return [
        f'按{first}做个统计汇总',
        f'看看{second}的分布情况',
        f'{first}和{second}有什么关系',
        f'这张表有哪些异常数据'
    ]


def _find_project_root() -> Path:
    here = Path(__file__).resolve()
    for p in [here.parent, *here.parent.parents]:
        if (p / "config.json").exists():
            return p
    cwd = Path.cwd().resolve()
    for p in [cwd, *cwd.parents]:
        if (p / "config.json").exists():
            return p
    return here.parent.parent


def _load_llm_config() -> Dict[str, str]:
    config_path = _find_project_root() / "config.json"
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found at: {config_path}")
    with open(config_path, "r", encoding="utf-8") as f:
        conf = json.load(f)
    return {
        "model": conf["model"],
        "api_key": conf["api_key"],
        "base_url": conf["base_url"],
    }


class SuggestionGenerator:
    def __init__(self, model_client=None):
        config = _load_llm_config()
        self._model_config = config["model"]
        self._api_config = config["api_key"]
        self._base_url = config["base_url"]
        logger.info(f"SuggestionGenerator 初始化: model={self._model_config}, base_url={self._base_url}")

    async def _call_llm(self, prompt: str) -> Dict[str, Any]:
        try:
            client = OpenAI(api_key=self._api_config, base_url=self._base_url, timeout=90.0)
            result = client.chat.completions.create(
                model=self._model_config,
                messages=[
                    {
                        "role": "system",
                        "content": "你是一个专业的数据分析助手，擅长根据 Excel 表格结构生成有价值的推荐问题。请始终返回有效的 JSON 格式。",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.7,
                max_tokens=500,
                extra_body={"enable_thinking": False},
                stream=False,
            )
            content = result.choices[0].message.content
            if "```json" in content:
                content = content.split("```json", 1)[1].split("```", 1)[0].strip()
            elif "```" in content:
                content = content.split("```", 1)[1].split("```", 1)[0].strip()
            return json.loads(content)
        except Exception as e:
            logger.error(f"LLM 调用失败: {e}", exc_info=True)
            raise

    async def generate_for_excel(self, file_name: str, sheet_name: str, columns: List[str], sample_data: List[List] = None, qa_history: List[Dict[str, str]] = None) -> List[str]:
        if len(columns) <= 10:
            col_info = ", ".join(columns)
        else:
            col_info = ", ".join(columns[:10]) + f" ... (共{len(columns)}列)"

        sample_info = ""
        if sample_data:
            sample_info = f"\n样本数据（前2行）:\n{json.dumps(sample_data[:2], ensure_ascii=False, indent=2)}"

        history_info = ""
        if qa_history and len(qa_history) > 0:
            recent_history = qa_history[-2:] if len(qa_history) > 2 else qa_history
            history_info = "\n\n最近的问答历史（用于生成后续问题）:\n"
            for i, qa in enumerate(recent_history, 1):
                history_info += f"\n第{i}轮:\n"
                history_info += f"  问题: {qa.get('question', '')}\n"
                history_info += f"  回答: {qa.get('answer', '')[:100]}...\n"

        if qa_history and len(qa_history) > 0:
            prompt = f"""用户正在分析 Excel 文件「{file_name}」的工作表「{sheet_name}」。

工作表包含以下列:
{col_info}{sample_info}{history_info}

基于以上信息，请生成 4 个用户接下来可能想问的后续问题，要求：
1. 问题要自然、口语化，符合中文表达习惯
2. 问题应该基于之前的问答历史，探索数据的更深层或相关方面
3. 每个问题控制在 20 字以内
4. 问题要具体，使用实际的列名
5. 4个问题之间要有差异性，不要重复

返回 JSON 格式，严格按照以下格式输出：
{{"questions": ["问题1", "问题2", "问题3", "问题4"]}}

注意：只返回 JSON，不要有其他说明文字。"""
        else:
            prompt = f"""用户正在分析 Excel 文件「{file_name}」的工作表「{sheet_name}」。

工作表包含以下列:
{col_info}{sample_info}

请生成 4 个用户最可能想问的数据分析问题，要求：
1. 问题要自然、口语化，符合中文表达习惯
2. 覆盖不同分析维度：数据概览、统计分析、对比分析、趋势分析
3. 每个问题控制在 20 字以内
4. 问题要具体，使用实际的列名
5. 4个问题之间要有差异性，不要重复

返回 JSON 格式，严格按照以下格式输出：
{{"questions": ["问题1", "问题2", "问题3", "问题4"]}}

注意：只返回 JSON，不要有其他说明文字。"""

        response = await self._call_llm(prompt)
        questions = response.get("questions", [])
        if len(questions) < 4:
            raise ValueError(f"LLM 返回的问题数量不足: {len(questions)}")
        return questions[:4]
