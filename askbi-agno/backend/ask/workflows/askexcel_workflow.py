from __future__ import annotations

import contextlib
import io
import json
import os
import traceback
from pathlib import Path
from typing import Any, Callable

import pandas as pd
from openai import OpenAI

from core import _load_config
from core.global_knowledge import get_global_knowledge

SECTION_RESULT = "## 1. 问题结果"
SECTION_EVIDENCE = "## 2. 回答依据"
SECTION_CHART = "## 3. 数据图表"
SECTION_ANALYSIS = "## 4. 分析解读"
DISPLAY_ANALYSIS_SECTION = "## 3. 分析解读"

try:
    import matplotlib.pyplot as plt
except Exception:
    plt = None


class AskExcelWorkflow:
    def __init__(self, max_rounds: int = 6) -> None:
        self.max_rounds = max_rounds
        conf = _load_config()
        self.client = OpenAI(api_key=conf["api_key"], base_url=conf["base_url"], timeout=90.0)
        self.model = conf["model"]

    def _emit(self, progress_callback: Callable[[str, dict[str, Any]], None] | None, event: str, payload: dict[str, Any]) -> None:
        if progress_callback is not None:
            progress_callback(event, payload)

    def _emit_stage(self, chatid: str, stage: str, status: str, message: str = "", detail: str = "") -> None:
        """发送结构化阶段事件（供 SSE 流消费）。"""
        from backend.ask.services.progress_service import progress_service
        progress_service.append_event(chatid, "stage", {
            "stage": stage,
            "status": status,
            "message": message,
            "detail": detail[:500] if detail else "",
        })

    def _build_system_prompt(self, agent_name: str, skill_ids: list[int] | None = None) -> str:
        """从 AgentManager 加载 agent 指令并注入技能。"""
        try:
            from backend.ask.agents_config.agent_manager import agent_manager
            config = agent_manager.get_agent_config(agent_name, skill_ids=skill_ids)
            instructions = config.get("instructions", "")
            skill_prompt = config.get("skill_prompt", "")
            if skill_prompt:
                return f"{instructions}\n{skill_prompt}"
            return instructions
        except Exception:
            return ""

    def _log(self, progress_callback: Callable[[str, dict[str, Any]], None] | None, text: str) -> None:
        if progress_callback is not None:
            progress_callback("log", {"text": text})
        print(f"[PROGRESS] {text}")

    def _preview(self, text: str, limit: int = 1200) -> str:
        text = text or ""
        return text if len(text) <= limit else text[:limit] + "\n...(已截断)"

    def _collect_metadata(self, excel_paths: list[str], sample_rows: int = 3) -> list[dict[str, Any]]:
        metadata: list[dict[str, Any]] = []
        allowed_suffixes = {".xlsx", ".xls", ".csv", ".json"}
        for file_path in excel_paths:
            path = Path(file_path)
            if not path.exists():
                metadata.append({"file_path": str(path), "exists": False, "error": "file not found"})
                continue
            if path.name.startswith("~$") or path.suffix.lower() not in allowed_suffixes:
                continue
            if path.suffix.lower() == ".csv":
                df = pd.read_csv(path)
                sample_df = df.head(sample_rows)
                metadata.append(
                    {
                        "file_path": str(path),
                        "file_name": path.name,
                        "exists": True,
                        "sheets": [
                            {
                                "sheet_name": "Sheet1",
                                "columns": [str(col) for col in df.columns.tolist()],
                                "sample_rows": sample_df.where(pd.notna(sample_df), None).to_dict(orient="records"),
                                "row_count": int(len(df)),
                            }
                        ],
                    }
                )
                continue
            if path.suffix.lower() == ".json":
                df = pd.read_json(path)
                sample_df = df.head(sample_rows)
                metadata.append(
                    {
                        "file_path": str(path),
                        "file_name": path.name,
                        "exists": True,
                        "sheets": [
                            {
                                "sheet_name": "Sheet1",
                                "columns": [str(col) for col in df.columns.tolist()],
                                "sample_rows": sample_df.where(pd.notna(sample_df), None).to_dict(orient="records"),
                                "row_count": int(len(df)),
                            }
                        ],
                    }
                )
                continue
            workbook = pd.ExcelFile(path)
            sheets: list[dict[str, Any]] = []
            for sheet_name in workbook.sheet_names:
                df = pd.read_excel(path, sheet_name=sheet_name)
                sample_df = df.head(sample_rows)
                sheets.append(
                    {
                        "sheet_name": sheet_name,
                        "columns": [str(col) for col in df.columns.tolist()],
                        "sample_rows": sample_df.where(pd.notna(sample_df), None).to_dict(orient="records"),
                        "row_count": int(len(df)),
                    }
                )
            metadata.append({"file_path": str(path), "file_name": path.name, "exists": True, "sheets": sheets})
        return metadata

    def _llm(self, system: str, user: str) -> str:
        result = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            temperature=0.1,
            max_tokens=4000,
            extra_body={"enable_thinking": False},
        )
        return (result.choices[0].message.content or "").strip()

    def _clean_code(self, code: str) -> str:
        text = code.strip()
        if "```python" in text:
            text = text.split("```python", 1)[1].split("```", 1)[0]
        elif "```" in text:
            text = text.split("```", 1)[1].split("```", 1)[0]
        return text.strip()

    def _make_json_safe(self, value: Any) -> Any:
        if value is None or isinstance(value, (str, int, bool)):
            return value
        if isinstance(value, float):
            if value != value:
                return None
            if value == float("inf"):
                return "Infinity"
            if value == float("-inf"):
                return "-Infinity"
            return value
        if isinstance(value, dict):
            return {str(k): self._make_json_safe(v) for k, v in value.items()}
        if isinstance(value, (list, tuple, set)):
            return [self._make_json_safe(v) for v in value]
        if isinstance(value, pd.DataFrame):
            return self._make_json_safe(value.where(pd.notna(value), None).to_dict(orient="records"))
        if isinstance(value, pd.Series):
            return self._make_json_safe(value.where(pd.notna(value), None).tolist())
        if hasattr(value, "item"):
            try:
                return self._make_json_safe(value.item())
            except Exception:
                pass
        if hasattr(value, "isoformat"):
            try:
                return value.isoformat()
            except Exception:
                pass
        return str(value)

    def _sanitize_report(self, report: str) -> str:
        lines = report.splitlines()
        cleaned: list[str] = []
        skipping_json = False
        brace_depth = 0

        for line in lines:
            stripped = line.strip()
            lower = stripped.lower()

            if stripped.startswith("```"):
                continue
            if any(keyword in stripped for keyword in ["图表展示", "vega-lite", "$schema", "mark", "encoding"]):
                continue
            if not skipping_json and stripped.startswith("{"):
                skipping_json = True
                brace_depth = stripped.count("{") - stripped.count("}")
                continue
            if skipping_json:
                brace_depth += stripped.count("{") - stripped.count("}")
                if brace_depth <= 0:
                    skipping_json = False
                continue
            if lower.startswith("![") and "](" in stripped:
                continue
            cleaned.append(line)

        return "\n".join(cleaned).strip()

    def _normalize_report(self, report: str, chart: dict[str, Any] | None, enable_analysis: bool) -> str:
        text = self._sanitize_report(report or "")
        if not text:
            text = "未能生成有效回答。"

        def has_section(title: str) -> bool:
            return title in text

        has_chart = bool(chart and chart.get("chart_needed", True) and (chart.get("$schema") or chart.get("mark")))
        analysis_prompt_text = "请结合业务背景，从结果波动原因、结构特征变化、后续趋势判断三个方面展开解读，并说明需要继续关注的指标或风险点。"

        text = text.replace(SECTION_CHART, "")
        text = text.replace(SECTION_ANALYSIS, DISPLAY_ANALYSIS_SECTION)
        text = text.replace("\n\n已生成图表，请结合下方图表查看。", "")
        text = text.replace("\n已生成图表，请结合下方图表查看。", "")
        text = text.replace("\n\n> 已生成数据图表，请查看下方图表区域。", "")
        text = text.replace("\n> 已生成数据图表，请查看下方图表区域。", "")

        if not has_section(SECTION_RESULT):
            parts = [p.strip() for p in text.split("\n\n") if p.strip()]
            result_part = parts[0] if parts else text.strip()
            evidence_part = "\n\n".join(parts[1:]).strip() if len(parts) > 1 else "暂无可补充的详细数据。"
            normalized = [SECTION_RESULT, result_part, "", SECTION_EVIDENCE, evidence_part]
            if enable_analysis:
                normalized.extend(["", DISPLAY_ANALYSIS_SECTION, analysis_prompt_text])
            text = "\n".join(normalized).strip()
        elif not enable_analysis and DISPLAY_ANALYSIS_SECTION in text:
            text = text.split(DISPLAY_ANALYSIS_SECTION)[0].rstrip()
        elif enable_analysis and DISPLAY_ANALYSIS_SECTION not in text:
            text = f"{text}\n\n{DISPLAY_ANALYSIS_SECTION}\n{analysis_prompt_text}"

        if has_chart:
            text = f"{text}\n\n> 已生成数据图表，请查看下方图表区域。"
        return text

    def _build_analysis_prompt(self, question: str, report: str, result_payload: Any) -> str:
        return f"""用户问题：{question}

当前已生成内容：
{report}

真实结果数据：
{json.dumps(result_payload, ensure_ascii=False, indent=2)}

请只输出“{DISPLAY_ANALYSIS_SECTION}”这一节的正文内容，不要重复前两节内容。
要求：
1. 至少 3 段或 3 个自然段，不要只写一句话。
2. 必须分别覆盖：结果波动原因、结构特征变化、后续趋势判断。
3. 每一段都要结合当前结果里的具体数据变化，不要空泛表述。
4. 最后补一句需要继续关注的指标或风险点。
5. 不要输出代码块、JSON、图表配置。"""

    def _expand_analysis_section(self, question: str, report: str, result_payload: Any) -> str:
        if DISPLAY_ANALYSIS_SECTION not in report:
            return report
        before, after = report.split(DISPLAY_ANALYSIS_SECTION, 1)
        analysis_body = after.strip()
        if len(analysis_body) > 80 and "请结合业务背景" not in analysis_body:
            return report
        analysis_prompt = self._build_analysis_prompt(question, report, result_payload)
        analysis_text = self._llm("你是业务分析专家。只输出分析解读正文。", analysis_prompt)
        analysis_text = self._sanitize_report(analysis_text)
        if not analysis_text:
            return report
        return f"{before.rstrip()}\n\n{DISPLAY_ANALYSIS_SECTION}\n{analysis_text.strip()}"

    def _build_report_prompt(self, question: str, metadata_text: str, result_payload: Any, enable_analysis: bool) -> str:
        analysis_rule = f"4. 输出“{SECTION_ANALYSIS}”，从业务视角做解读，可适度融合建议。" if enable_analysis else f"4. 不要输出“{SECTION_ANALYSIS}”。"
        return (
            f"用户问题：{question}\n\n"
            f"文件元数据摘要：\n{metadata_text}\n\n"
            f"真实执行结果：\n{json.dumps(result_payload, ensure_ascii=False, indent=2)}\n\n"
            "请输出中文分析回答正文。\n"
            "要求：\n"
            f"1. 第一部分固定为“{SECTION_RESULT}”，必须直接回答用户问题。\n"
            f"2. 第二部分固定为“{SECTION_EVIDENCE}”，必须给出支撑结论的详细数据、明细或 Markdown 表格。\n"
            f"3. 如果用户开启分析解读，则第三部分固定为“{SECTION_ANALYSIS}”，至少写 3 句，分别覆盖波动原因、结构变化、趋势判断，可适度融合建议。\n"
            "4. 不要在正文中输出“## 3. 数据图表”标题，图表会在正文下方独立展示；如已生成图表，只需用一句自然语言提示用户查看下方图表区域。\n"
            f"{analysis_rule}\n"
            "5. 不要输出任何 JSON、代码块、Vega-Lite 配置、图片路径或 Markdown 图片语法。"
        )

    def _build_chart_prompt(self, question: str, result_payload: Any, report: str) -> str:
        from prompt import build_chart_prompt
        data = result_payload if isinstance(result_payload, list) else [result_payload]
        prompt = build_chart_prompt(data)
        prompt += f"\n\n用户问题：{question}\n分析报告摘要：{report[:500]}"
        prompt += "\n若用户明确要求图表形式，优先满足该形式。"
        return prompt

    def _extract_thoughts(self, execution: dict[str, Any] | None) -> list[str]:
        thoughts: list[str] = []
        if execution and execution.get("stdout"):
            thoughts.append("已完成代码执行并获取结果。")
        if execution and execution.get("success"):
            thoughts.append("已基于真实执行结果生成回答与图表。")
        return thoughts

    def _block_unsafe_code(self, cleaned_code: str) -> None:
        blocked_patterns = [
            "savefig(",
            "plt.savefig(",
            ".to_file(",
            ".write_image(",
            "open(",
            "write_bytes(",
            "write_text(",
            "Image.save(",
            "cv2.imwrite(",
            "fig.write_image(",
        ]
        lower_code = cleaned_code.lower()
        for pattern in blocked_patterns:
            if pattern.lower() in lower_code:
                raise RuntimeError("禁止在分析代码中生成或保存图片/文件，请只输出数据结果；图表由后置 Vega-Lite 配置阶段处理。")

    def _execute_code(self, code: str, excel_paths: list[str], metadata: list[dict[str, Any]]) -> dict[str, Any]:
        exec_globals = {
            "__builtins__": __builtins__,
            "pd": pd,
            "json": json,
            "os": os,
            "FILE_LIST": excel_paths,
            "FILE_METADATA": metadata,
            "RESULT": None,
        }
        if plt is not None:
            exec_globals["plt"] = plt
        stdout = io.StringIO()
        cleaned_code = self._clean_code(code)
        try:
            self._block_unsafe_code(cleaned_code)
            with contextlib.redirect_stdout(stdout):
                exec(cleaned_code, exec_globals, exec_globals)
            return {
                "success": True,
                "code": cleaned_code,
                "stdout": stdout.getvalue(),
                "result": self._make_json_safe(exec_globals.get("RESULT")),
                "error": None,
            }
        except Exception:
            return {
                "success": False,
                "code": cleaned_code,
                "stdout": stdout.getvalue(),
                "result": self._make_json_safe(exec_globals.get("RESULT")),
                "error": traceback.format_exc(),
            }

    def _build_code_prompt(
        self,
        question: str,
        metadata_text: str,
        global_knowledge: str = "",
        previous_error: str | None = None,
        previous_code: str | None = None,
    ) -> str:
        prompt = (
            f"用户问题：{question}\n\n"
            + (f"[KNOWLEDGE]:\n{global_knowledge}\n\n" if global_knowledge else "")
            + f"文件元数据：\n{metadata_text}\n\n"
            + "请只输出一段 Python 代码，使用 pandas 读取 FILE_LIST 中的文件分析数据，最终把答案赋值给 RESULT，并 print(RESULT)。\n"
            + "要求：\n"
            + "1. 只能使用 FILE_LIST / FILE_METADATA 里的文件，不要编造路径。\n"
            + "2. 必须基于真实列名写代码，不要随意重命名后再假设列顺序。\n"
            + "3. 如果需要取最大值/最小值对应的行，先算 Series，再用 idxmax()/idxmin() 取索引，不能把数值序列直接传给 .loc。\n"
            + "4. 可以生成用于图表渲染的数据结构，但禁止保存图片、禁止写文件、禁止返回本地图片路径。\n"
            + "5. 图表由后置 Vega-Lite 配置阶段处理，分析代码只负责结果数据。\n"
            + "6. 严格遵守 [KNOWLEDGE] 中与业务口径、字段含义、筛选规则、统计规则相关的约束。\n"
            + "7. 不要输出 markdown，不要解释。"
        )
        if previous_error:
            prompt += f"\n\n上轮代码执行失败，错误信息：\n{previous_error}\n请修复代码后重新输出完整 Python 代码。"
        if previous_code:
            prompt += f"\n\n上轮失败代码：\n```python\n{previous_code}\n```"
        return prompt

    def run(self, payload: dict[str, Any]) -> dict[str, Any]:
        progress_callback = payload.get("progress_callback") if callable(payload.get("progress_callback")) else None
        question = str(payload["question"]).strip()
        excel_paths = [str(Path(p)) for p in payload.get("excel_paths", [])]
        enable_analysis = bool(payload.get("enable_analysis"))
        chatid = payload.get("chatid", "")
        active_skill_ids = payload.get("skill_ids")  # 用户选择的技能 ID 列表

        print("=" * 60)
        print(f"[EXCEL WORKFLOW] 开始处理问题: {question}")
        print(f"[EXCEL MODEL] {self.model}")
        print(f"[EXCEL PATHS]\n{json.dumps(excel_paths, ensure_ascii=False)}")
        print("=" * 60)

        # 加载技能注入 prompt
        code_system_prompt = self._build_system_prompt("askexcel_code_agent", skill_ids=active_skill_ids) or "你是 Excel 问数场景下的 Python 数据分析专家。只输出 Python 代码，不要 markdown，不要解释。"
        report_system_prompt = self._build_system_prompt("askexcel_report_agent", skill_ids=active_skill_ids) or "你是数据分析报告专家。直接回答问题，只输出纯报告正文。"
        from prompt import VEGALITE_SYSTEM_PROMPT, validate_vegalite_json
        chart_system_prompt = self._build_system_prompt("askexcel_chart_agent", skill_ids=active_skill_ids) or VEGALITE_SYSTEM_PROMPT

        self._emit_stage(chatid, "understanding", "running", "正在加载数据文件…")
        self._log(progress_callback, "正在加载数据文件...")
        self._emit(progress_callback, "started", {"question": question, "excel_paths": excel_paths})
        metadata = self._collect_metadata(excel_paths)
        self._emit_stage(chatid, "understanding", "done", "数据文件加载完成")
        self._emit(progress_callback, "metadata_loaded", {"files": [{"file_name": item.get("file_name"), "sheet_count": len(item.get("sheets", []))} for item in metadata]})

        if not excel_paths:
            return {"status": "failed", "error": "excel_paths 不能为空", "trace": {"metadata": metadata}}
        if any(not item.get("exists", False) for item in metadata):
            return {"status": "failed", "error": "存在无效 Excel 路径", "metadata": metadata, "trace": {"metadata": metadata}}

        metadata_text = json.dumps(metadata, ensure_ascii=False, indent=2)
        datasource_name = str(payload.get("datasource_name") or "").strip() or None
        global_knowledge = get_global_knowledge(datasource_name)

        execution: dict[str, Any] | None = None
        previous_error: str | None = None
        previous_code: str | None = None

        for round_num in range(1, self.max_rounds + 1):
            self._emit_stage(chatid, "code_generation", "running", f"第{round_num}轮代码生成中…")
            code_prompt = self._build_code_prompt(question, metadata_text, global_knowledge, previous_error, previous_code)
            self._emit(progress_callback, "code_started", {"input": self._preview(code_prompt), "round": round_num})
            code = self._llm(code_system_prompt, code_prompt)
            cleaned_code = self._clean_code(code)
            self._emit_stage(chatid, "code_generation", "done", f"第{round_num}轮代码生成完成", cleaned_code)
            self._emit_stage(chatid, "code_execution", "running", f"第{round_num}轮代码执行中…", cleaned_code)
            execution = self._execute_code(code, excel_paths, metadata)
            self._emit(progress_callback, "code_round", {"round": round_num, "input": self._preview(code_prompt), "output": self._preview(code), "execution": execution, "validation": {"passed": execution.get("success"), "issue": execution.get("error")}})
            if execution.get("success"):
                self._emit_stage(
                    chatid,
                    "code_execution",
                    "done",
                    "代码执行成功",
                    json.dumps({"stdout": execution.get("stdout"), "result": execution.get("result")}, ensure_ascii=False, indent=2, default=str),
                )
                break
            previous_error = execution.get("error") or "代码执行失败"
            previous_code = cleaned_code

        if not execution or not execution.get("success"):
            self._emit_stage(chatid, "code_execution", "error", "代码执行失败")
            return {"status": "failed", "error": previous_error or "代码执行失败", "trace": {"metadata": metadata, "execution": execution, "last_code": previous_code}}

        result_payload = execution.get("result")
        self._emit_stage(chatid, "report_generation", "running", "正在生成分析报告…")
        report_prompt = self._build_report_prompt(question, metadata_text, result_payload, enable_analysis)
        report = self._llm(report_system_prompt, report_prompt)
        report = self._sanitize_report(report)
        self._emit_stage(chatid, "report_generation", "done", "报告生成完成")
        if enable_analysis:
            report = self._expand_analysis_section(question, report, result_payload)

        self._emit_stage(chatid, "chart_generation", "running", "正在生成图表…")
        chart_prompt = self._build_chart_prompt(question, result_payload, report)
        chart_raw = self._llm(chart_system_prompt, chart_prompt)
        chart = validate_vegalite_json(chart_raw)
        if chart.get("chart_needed") is False:
            self._emit_stage(chatid, "chart_generation", "done", "不需要生成图表")
        else:
            self._emit_stage(chatid, "chart_generation", "done", "图表生成完成")

        report = self._normalize_report(report, chart if isinstance(chart, dict) else None, enable_analysis)
        thoughts = self._extract_thoughts(execution)
        self._emit(progress_callback, "report_completed", {"output": self._preview(report)})
        self._emit(progress_callback, "chart_completed", {"output": self._preview(chart_raw)})
        self._emit(progress_callback, "completed", {"status": "success"})
        return {
            "status": "success",
            "report": report,
            "summary": report,
            "code": execution.get("code", ""),
            "result": result_payload,
            "chart": chart,
            "thoughts": thoughts,
            "trace": {"metadata": metadata, "execution": execution, "report": report, "chart": chart},
        }


askexcel_workflow_impl = AskExcelWorkflow()
