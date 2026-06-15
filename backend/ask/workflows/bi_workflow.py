from __future__ import annotations

import json
import re
import textwrap
from typing import Any, Callable, Dict, List, Optional


SECTION_RESULT = "## 1. 问题结果"
SECTION_EVIDENCE = "## 2. 回答依据"
SECTION_CHART = "## 3. 数据图表"
SECTION_ANALYSIS = "## 4. 分析解读"
DISPLAY_ANALYSIS_SECTION = "## 3. 分析解读"

from openai import OpenAI

from core import _load_config
from core.schema_loader import load_schema_from_refer
from utils.datasource_sql_executor import run_sql


def _unescape_python_string(s: str) -> str:
    """还原 Python 字符串中的转义字符（\" → "，\\' → '，\\\\ → \\）"""
    s = s.replace('\\"', '"')
    s = s.replace("\\'", "'")
    s = s.replace("\\\\", "\\")
    s = s.replace("\\n", "\n")
    s = s.replace("\\t", "\t")
    return s


class BiWorkflow:
    def __init__(self) -> None:
        conf = _load_config()
        self.client = OpenAI(api_key=conf["api_key"], base_url=conf["base_url"], timeout=90.0)
        self.model = conf["model"]
        self.max_rounds = 8  # 最大重试次数

    def _emit(self, progress_callback: Callable[[str], None] | None, text: str) -> None:
        """发送进度事件（同时调用 progress_callback 和发送 stage 事件）。"""
        if progress_callback:
            progress_callback(text)
        print(f"[PROGRESS] {text}")

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

    def _llm(self, system: str, user: str, messages: list[dict] | None = None) -> str:
        msg_list = [{"role": "system", "content": system}]
        if messages:
            msg_list.extend(messages)
        msg_list.append({"role": "user", "content": user})
        result = self.client.chat.completions.create(
            model=self.model,
            messages=msg_list,
            temperature=0.1,
            max_tokens=4000,
            extra_body={"enable_thinking": False},
        )
        response_text = (result.choices[0].message.content or "").strip()
        print(f"[LLM RESPONSE] 长度: {len(response_text)} 字符")
        return response_text

    def _extract_python_code(self, text: str) -> str:
        """从 LLM 回复中提取代码块"""
        if "```python" in text:
            return text.split("```python", 1)[1].split("```", 1)[0].strip()
        if "```sql" in text:
            return text.split("```sql", 1)[1].split("```", 1)[0].strip()
        if "```" in text:
            return text.split("```", 1)[1].split("```", 1)[0].strip()
        return text.strip()

    def _extract_sql_from_python(self, code: str) -> list[str]:
        """从 Python 代码中提取 SQL 语句"""
        if not code:
            return []

        sql_statements = []

        # 1. 首先尝试匹配 run_sql(...) 模式（支持单/双/三引号）
        run_sql_pattern = r'run_sql\s*\(\s*(["\']{1,3})(.*?)\1\s*\)'
        for match in re.finditer(run_sql_pattern, code, re.DOTALL | re.IGNORECASE):
            sql = match.group(2).strip()
            if sql:
                sql_statements.append(sql)

        if sql_statements:
            return sql_statements

        # 2. 尝试匹配 execute_sql(...) 模式
        exec_sql_pattern = r'execute_sql\s*\(\s*(["\']{1,3})(.*?)\1\s*\)'
        for match in re.finditer(exec_sql_pattern, code, re.DOTALL | re.IGNORECASE):
            sql = match.group(2).strip()
            if sql:
                sql_statements.append(sql)

        if sql_statements:
            return sql_statements

        # 3. 尝试匹配 sql = "..." 或 query = "..." 模式
        var_pattern = r'(?:sql|query)\s*=\s*(["\']{1,3})(.*?)\1'
        var_match = re.search(var_pattern, code, re.DOTALL | re.IGNORECASE)
        if var_match:
            sql = var_match.group(2).strip()
            if sql:
                return [sql]

        # 4. 回退：如果代码本身就是纯 SQL
        if code.strip().upper().startswith("SELECT") or code.strip().upper().startswith("WITH"):
            return [code.strip()]

        return []

    def _safe_sql(self, sql: str) -> str:
        text = sql.strip().strip("`")
        lower = text.lower()
        if not (lower.startswith("select") or lower.startswith("with")):
            raise ValueError("只允许执行 SELECT 查询")
        for token in [" insert ", " update ", " delete ", " alter ", " drop ", " create ", " truncate "]:
            if token in f" {lower} ":
                raise ValueError("检测到非查询 SQL")
        return text

    def _clean_report(self, report: str) -> str:
        """清理报告中可能残留的图表相关段落和数据库表名"""
        # 清理数据库表名（schema.table_name 或 schema.table_name 格式）
        report = re.sub(r'\b[a-z_]+\.[a-z_]+\b', '数据表', report, flags=re.IGNORECASE)
        # 清理独立的 schema 名称引用
        report = re.sub(r'\bjiceng\b', '数据源', report, flags=re.IGNORECASE)

        lines = report.split("\n")
        filtered_lines = []
        skip_block = False  # 是否在跳过代码块
        skip_section = False  # 是否在跳过图表相关章节

        for line in lines:
            # 跳过代码块
            if line.strip().startswith("```"):
                skip_block = not skip_block
                continue
            if skip_block:
                continue

            # 跳过图表相关章节标题和 mermaid/graph 代码
            stripped = line.strip().lower()
            if any(keyword in stripped for keyword in [
                "可视化", "图表展示", "饼图", "柱状图", "折线图",
                "graph lr", "graph tb", "pie title", "xychart",
                "plantuml", "mermaid", "文本化柱状图"
            ]):
                skip_section = True
                continue

            # 遇到下一个非图表标题时恢复
            if skip_section and stripped and not stripped.startswith("██") and not stripped.startswith("---"):
                if stripped[0].isdigit() and "图表" not in stripped and "可视化" not in stripped:
                    skip_section = False
                elif stripped and not stripped.startswith("-") and not stripped.startswith("*") and len(stripped) < 50:
                    # 可能是新章节标题
                    skip_section = False

            if skip_section:
                continue

            # 跳过 ASCII 图表行
            if "██" in line:
                continue

            filtered_lines.append(line)

        return "\n".join(filtered_lines).strip()

    def _schema_context(self, datasource_name: str | None) -> tuple[str, dict[str, Any]]:
        schema_data = load_schema_from_refer("refer", datasource_name)
        tables = schema_data.get("tables", {}) if isinstance(schema_data, dict) else {}
        parts: list[str] = []
        for table_name, table_info in tables.items():
            parts.append(f"TABLE: {table_name}")
            comment = table_info.get("comment")
            if comment:
                parts.append(f"COMMENT: {comment}")
            columns = table_info.get("columns", [])
            column_names = [col.get("name", "") for col in columns if isinstance(col, dict)]
            parts.append(f"COLUMNS: {', '.join(column_names)}")
            sample_data = table_info.get("sample_data") or []
            if sample_data:
                parts.append(f"SAMPLE: {json.dumps(sample_data[:1], ensure_ascii=False)}")
            parts.append("")
        return "\n".join(parts), schema_data

    def _build_sql_prompt(self, question: str, datasource_name: str, schema_context: str, error_feedback: str | None = None) -> str:
        prompt = f"""用户问题：{question}

数据源：{datasource_name}

元数据：
{schema_context}

请生成 Python 代码来查询数据库并返回结果。
要求：
1. 必须使用 `run_sql("SELECT ...")` 格式执行查询
2. 打印结果：`print("RESULT:", run_sql("SELECT ..."))`
3. 只生成 SELECT 查询，禁止 INSERT/UPDATE/DELETE
4. PostgreSQL 列名大小写敏感，混合大小写列名必须用双引号
5. 不要使用 DISTINCT、LIMIT、聚合函数（SUM/AVG/COUNT/GROUP BY），返回所有原始记录
"""
        if error_feedback:
            prompt += f"\n\n上次执行失败，错误信息：\n{error_feedback}\n请修复 SQL 后重试。"
        return prompt

    def _build_validator_prompt(self, question: str, sql: str, result: Any, error: str | None = None) -> str:
        if error:
            return f"""用户问题：{question}
生成的 SQL：{sql}
执行错误：{error}

请判断问题原因并给出修复建议。如果 SQL 语法错误，指出具体错误；如果表不存在，说明可能是表名有误。
只回复中文简短分析 + 修复建议。"""
        return f"""用户问题：{question}
生成的 SQL：{sql}
执行结果：{json.dumps(result, ensure_ascii=False, default=str)[:2000]}

请判断结果是否正确完整。如果结果正确且完整，只回复 STOP。
判断规则：
1. 必须优先依据真实查询结果判断，不能用 schema sample、常识或主观推测否定真实返回的数据。
2. 凡是真实查询结果中已经出现的年份、月份、指标值，都视为有效事实；不得再把这些已返回的年份或月份称为未来、不存在、通常不会有数据。
3. 对“今年、本年、当前年、上半年、本季度、累计、截至目前、全年各月”这类进行中期间问题，如果当前自然时间尚未走完，但结果已经返回截至最新可用月份的连续真实数据，应视为可以回答。
4. 用户问“2026年全年各月”这类当前年各月问题时，在当前年份只过去部分月份的情况下，只返回已经发生且已入库的月份数据是正常且正确的，不得因为缺少未来月份就判错。
5. 对进行中期间场景，不得仅因为缺少未来月份或尚未出数月份就判定结果错误；正确做法是允许按“截至最新可用月份”回答，并在需要时提示缺失范围。
6. 如果真实结果已经足以支持“截至最新可用月份”的回答，则必须回复 STOP，不要再要求必须拿到未来月份或尚未结束月份的数据。
7. 只有在真实结果无法支持回答、字段明显错误、时间范围明显错位时，才判定不正确。
如果结果不正确，只输出简短中文原因与修复建议，不要包含 STOP 这个词。"""

    def _build_time_fallback_prompt(self, question: str, report: str, result_payload: Any) -> str:
        return f"""用户问题：{question}

当前回答：
{report}

真实结果数据：
{json.dumps(result_payload, ensure_ascii=False, indent=2, default=str)}

请检查这个回答是否错误地把“当前年/今年/本年/上半年/本季度”等进行中期间，当成必须拿未来或尚未出数的期末月份计算。
如果是，请直接重写回答，规则如下：
1. 优先按最新可用月份回答，不要因为目标期末缺失就直接判定“无法计算”。
2. 必须明确写出“截至最新可用月份”。
3. 如果 6 月缺失但 5 月有数据，就应按 5 月回答，而不是直接说上半年无法计算。
4. 保持原有标题结构：问题结果、回答依据；如果有分析解读则保留分析解读。
5. 不要输出代码块、JSON、图表配置。
如果当前回答本来就没有这个问题，则原样重写一版更准确的文字。"""

    def _apply_time_fallback(self, question: str, report: str, result_payload: Any) -> str:
        time_keywords = ["上半年", "下半年", "本年", "今年", "累计", "截至", "季度"]
        if not any(keyword in question for keyword in time_keywords):
            return report
        fallback_prompt = self._build_time_fallback_prompt(question, report, result_payload)
        fallback_report = self._llm("你是时间口径纠偏专家。只输出修正后的回答正文。", fallback_prompt)
        fallback_report = self._clean_report(fallback_report)
        return fallback_report or report

    def _normalize_report(self, report: str, chart: dict[str, Any] | None, enable_analysis: bool) -> str:
        text = self._clean_report(report or "")
        if not text:
            text = "未能生成有效回答。"

        def has_section(title: str) -> bool:
            return title in text

        has_chart = bool(chart and chart.get("chart_needed", True) and (chart.get("$schema") or chart.get("mark")))
        analysis_prompt_text = "请结合业务背景，从指标波动原因、结构变化特征、短期趋势延续性三个方面展开解读，并指出需要持续关注的业务信号。"

        text = text.replace(SECTION_CHART, "")
        text = text.replace(SECTION_ANALYSIS, DISPLAY_ANALYSIS_SECTION)
        text = text.replace("\n\n已生成图表，请结合下方图表查看。", "")
        text = text.replace("\n已生成图表，请结合下方图表查看。", "")
        text = text.replace("\n\n> 已生成数据图表，请查看下方图表区域。", "")
        text = text.replace("\n> 已生成数据图表，请查看下方图表区域。", "")

        if not has_section(SECTION_RESULT):
            parts = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
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
2. 必须分别覆盖：指标波动原因、结构变化特征、短期趋势延续性。
3. 每一段都要结合当前结果里的具体数据变化，不要空泛表述。
4. 最后补一句需要持续关注的业务信号。
5. 不要输出代码块、JSON、图表配置。"""

    def _expand_analysis_section(self, question: str, report: str, result_payload: Any) -> str:
        if DISPLAY_ANALYSIS_SECTION not in report:
            return report
        before, after = report.split(DISPLAY_ANALYSIS_SECTION, 1)
        analysis_body = after.strip()
        if len(analysis_body) > 80 and "请结合业务背景" not in analysis_body:
            return report
        analysis_prompt = self._build_analysis_prompt(question, report, result_payload)
        analysis_text = self._llm("你是银行业务分析专家。只输出分析解读正文。", analysis_prompt)
        analysis_text = self._clean_report(analysis_text)
        if not analysis_text:
            return report
        return f"{before.rstrip()}\n\n{DISPLAY_ANALYSIS_SECTION}\n{analysis_text.strip()}"

    def _build_report_prompt(self, question: str, final_sql: str, final_result: Any, enable_analysis: bool) -> str:
        analysis_rule = f"3. 如果用户开启分析解读，则第三部分固定为“{DISPLAY_ANALYSIS_SECTION}”，至少写 3 段，分别覆盖波动原因、结构变化、趋势判断，并结合具体数据。" if enable_analysis else f"3. 不要输出“{DISPLAY_ANALYSIS_SECTION}”。"
        return f"""用户问题：{question}

SQL：{final_sql}

执行结果：
{json.dumps(final_result, ensure_ascii=False, indent=2, default=str)}

请输出中文数据分析回答正文。
**正文结构要求**：
1. 第一部分固定为“{SECTION_RESULT}”，必须直接回答用户问题，优先给出数值、最值、排名、增量、增速、结论月份等。
2. 第二部分固定为“{SECTION_EVIDENCE}”，必须给出支撑结论的详细数据、明细表或推理依据，优先使用 Markdown 表格。
{analysis_rule}
4. 不要在正文中输出“## 4. 数据图表”标题，图表会在正文下方独立展示；如已生成图表，只需用一句自然语言提示用户查看下方图表区域。
**严格禁止**：
- 不要暴露数据库表名（如 jiceng.xxx、schema.table_name 等），用“数据源”或“数据集”代替
- 不要输出 Vega-Lite JSON、代码块、mermaid、ASCII 图表
- 不要省略“{SECTION_RESULT}”和“{SECTION_EVIDENCE}”两个部分
"""

    def run(self, question: str, datasource_name: str | None, progress_callback: Callable[[str], None] | None = None, enable_analysis: bool = False, chatid: str = "", active_skill_ids: list[int] | None = None) -> dict[str, Any]:

        print("=" * 60)
        print(f"[BI WORKFLOW] 开始处理问题: {question}")
        print(f"[BI WORKFLOW] 数据源: {datasource_name}")
        print("=" * 60)

        # 加载技能注入 prompt（按 agent 分别加载）
        sql_system_prompt = self._build_system_prompt("bi_sql_agent", skill_ids=active_skill_ids) or "你是 PostgreSQL BI 问数 SQL 专家。只输出 Python 代码，不要 markdown。"
        report_system_prompt = self._build_system_prompt("bi_report_agent", skill_ids=active_skill_ids) or "你是 BI 数据分析报告专家。输出结构化分析回答，包含 Markdown 表格。"
        from prompt import VEGALITE_SYSTEM_PROMPT, build_chart_prompt, validate_vegalite_json
        chart_system_prompt = self._build_system_prompt("bi_chart_agent", skill_ids=active_skill_ids) or VEGALITE_SYSTEM_PROMPT

        self._emit_stage(chatid, "understanding", "running", "正在分析问题和数据结构…")
        self._emit(progress_callback, "[system] 正在加载数据结构…")
        schema_context, schema_data = self._schema_context(datasource_name)
        table_count = len(schema_data.get("tables", {})) if isinstance(schema_data, dict) else 0
        print(f"[SCHEMA] 加载到 {table_count} 个表")

        if not schema_context.strip():
            raise ValueError("数据源元数据为空，请先生成元数据")

        tables = list((schema_data.get("tables") or {}).keys()) if isinstance(schema_data, dict) else []

        self._emit_stage(chatid, "understanding", "done", f"已加载 {table_count} 个表")
        self._emit(progress_callback, "[system] 正在生成 SQL…")

        # 带重试的 SQL 生成与执行循环
        messages: list[dict] = []
        final_sql = None
        final_result = None
        final_error = None
        round_num = 0

        for round_num in range(self.max_rounds):
            # 1. 生成 SQL (首轮或修复后)
            print(f"\n{'='*40} 第 {round_num + 1} 轮 {'='*40}")
            self._emit_stage(chatid, "sql_generation", "running", f"第{round_num + 1}轮 SQL 生成中…")
            prompt = self._build_sql_prompt(question, datasource_name or "", schema_context, final_error)
            response = self._llm(sql_system_prompt, prompt, messages)
            self._emit_stage(chatid, "sql_generation", "done", f"第{round_num + 1}轮 SQL 生成完成", self._extract_python_code(response))
            messages.append({"role": "user", "content": prompt})
            messages.append({"role": "assistant", "content": response})

            self._emit(progress_callback, f"[sql] 第{round_num + 1}轮生成的代码:\n{self._extract_python_code(response)[:500]}")

            # 2. 提取并执行 SQL
            code = self._extract_python_code(response)
            print(f"[CODE EXTRACTED] 代码长度: {len(code)} 字符")
            print(f"[CODE EXTRACTED]\n{code[:300]}")
            sql_list = self._extract_sql_from_python(code)
            print(f"[SQL EXTRACTED] 提取到 {len(sql_list)} 条 SQL")

            if not sql_list:
                final_error = "未能从生成的代码中提取到 SQL 语句"
                print(f"[ERROR] {final_error}")
                self._emit(progress_callback, f"[error] {final_error}")
                continue

            raw_sql = _unescape_python_string(sql_list[0])
            print(f"[SQL]\n{raw_sql}")
            try:
                self._safe_sql(raw_sql)
            except ValueError as e:
                final_error = str(e)
                print(f"[SQL VALIDATION FAILED] {final_error}")
                self._emit(progress_callback, f"[error] SQL 校验失败: {final_error}")
                continue

            # 执行所有提取的 SQL（支持多问题回答）
            self._emit_stage(chatid, "sql_execution", "running", f"正在执行 SQL 查询…")
            all_results = []
            all_sqls = []
            sql_errors = []
            for idx, sql in enumerate(sql_list):
                sql_text = _unescape_python_string(sql)
                # 校验每条 SQL
                try:
                    self._safe_sql(sql_text)
                except ValueError as e:
                    sql_errors.append(f"SQL {idx + 1} 校验失败: {e}")
                    print(f"[SQL VALIDATION FAILED] {sql_errors[-1]}")
                    continue

                self._emit(progress_callback, f"[sql] {sql_text}")
                self._emit_stage(chatid, "sql_execution", "running", f"正在执行第 {idx + 1}/{len(sql_list)} 条 SQL", sql_text)
                try:
                    result = run_sql(sql_text, datasource_name)
                    all_results.append({
                        "query_index": idx + 1,
                        "sql": sql_text,
                        "data": result,
                        "count": len(result)
                    })
                    all_sqls.append(sql_text)
                    print(f"[RESULT SQL {idx + 1}] 查询返回 {len(result)} 条记录")
                    self._emit(progress_callback, f"[result] 第 {idx + 1}/{len(sql_list)} 条查询返回 {len(result)} 条记录")
                    self._emit_stage(
                        chatid,
                        "sql_execution",
                        "done",
                        f"第 {idx + 1}/{len(sql_list)} 条查询返回 {len(result)} 条记录",
                        json.dumps(result[:20], ensure_ascii=False, indent=2, default=str),
                    )
                except Exception as e:
                    sql_errors.append(f"SQL {idx + 1} 执行失败: {str(e)}")
                    print(f"[SQL EXECUTION FAILED] {sql_errors[-1]}")
                    self._emit(progress_callback, f"[error] 第 {idx + 1} 条查询失败: {sql_errors[-1]}")

            if not all_results:
                final_error = f"所有 {len(sql_list)} 条 SQL 均执行失败\n" + "\n".join(sql_errors)
                print(f"[ERROR] {final_error}")
                self._emit(progress_callback, f"[error] {final_error}")
                continue

            final_sql = "\n---\n".join(all_sqls)
            final_result = all_results
            final_error = "\n".join(sql_errors) if sql_errors else None

            total_records = sum(r["count"] for r in all_results)
            print(f"[RESULT] 共 {len(all_results)} 条查询，总计 {total_records} 条记录")

            # 3. 验证结果
            if final_result is not None:
                print(f"\n[VALIDATOR] 正在验证结果...")
                # 把真实查询结果明细传给验证器，避免只看记录数摘要
                validator_payload = {
                    "query_count": len(all_results),
                    "total_records": total_records,
                    "queries": all_results,
                    "sql_errors": sql_errors,
                }
                validator_prompt = self._build_validator_prompt(question, final_sql, validator_payload)
                verdict = self._llm("你是工作流验证器。判断结果是否正确完整。", validator_prompt, messages)
                messages.append({"role": "user", "content": validator_prompt})
                messages.append({"role": "assistant", "content": verdict})
                print(f"[VERDICT] {verdict[:200]}")

                if verdict.strip().upper() == "STOP":
                    print("[VALIDATOR] 验证通过")
                    self._emit(progress_callback, "[system] 验证通过")
                    break
                else:
                    print("[VALIDATOR] 验证未通过")
                    self._emit(progress_callback, f"[system] 验证未通过: {verdict[:200]}")
                    final_error = f"结果不完整: {verdict}"

        # 生成报告
        if final_error and final_result is None:
            # 所有轮次都失败了
            print(f"\n[REPORT] 所有轮次都失败，生成错误报告")
            self._emit_stage(chatid, "report_generation", "running", "生成错误报告…")
            self._emit(progress_callback, f"[system] SQL 生成/执行失败，生成错误报告")
            report_prompt = f"用户问题：{question}\n\n最后错误：{final_error}\n\n请说明查询失败原因。"
            report = self._llm(report_system_prompt, report_prompt)
        elif final_result is not None:
            report_prompt = self._build_report_prompt(question, final_sql, final_result, enable_analysis)
            print(f"\n[REPORT] 正在生成分析报告...")
            self._emit_stage(chatid, "report_generation", "running", "正在生成分析报告…")
            self._emit(progress_callback, "[system] 正在生成分析报告…")
            report = self._llm(report_system_prompt, report_prompt)
            report = self._clean_report(report)
            self._emit_stage(chatid, "report_generation", "done", "报告生成完成")
            report = self._apply_time_fallback(question, report, final_result)
            if enable_analysis:
                report = self._expand_analysis_section(question, report, final_result)
        else:
            report = "未能获取到数据。"
            print(f"[REPORT] {report}")

        # 生成图表
        if final_result is not None and len(final_result) > 0:
            # 扁平化所有查询结果用于图表生成
            flat_result = []
            for qr in final_result:
                flat_result.extend(qr.get("data", []))
            chart_prompt = build_chart_prompt(flat_result)
            chart_prompt += f"\n\n用户问题：{question}\n分析报告摘要：{report[:500]}"
            print(f"[CHART] 正在生成图表...")
            self._emit_stage(chatid, "chart_generation", "running", "正在生成图表…")
            self._emit(progress_callback, "[system] 正在生成图表…")
            chart_raw = self._llm(chart_system_prompt, chart_prompt)
            chart = validate_vegalite_json(chart_raw)
            if chart.get("chart_needed") is False:
                self._emit_stage(chatid, "chart_generation", "done", "不需要生成图表")
                print(f"[CHART] 不需要图表: {chart.get('reason')}")
            else:
                self._emit_stage(chatid, "chart_generation", "done", "图表生成完成")
                print(f"[CHART] 图表配置生成成功")
        else:
            chart = {"chart_needed": True, "reason": "无数据可展示"}
            print(f"[CHART] 无数据可展示")

        print(f"\n{'='*60}")
        print(f"[BI WORKFLOW] 完成，共 {round_num + 1} 轮，使用 {table_count} 个表")
        print(f"{'='*60}\n")

        report = self._normalize_report(report, chart if isinstance(chart, dict) else None, enable_analysis)

        return {
            "summary": report,
            "sql": final_sql or "",
            "tables": tables,
            "chart": chart,
            "thoughts": [f"共执行 {round_num + 1} 轮 SQL 生成/重试"],
            "result": final_result,
        }


bi_workflow = BiWorkflow()
