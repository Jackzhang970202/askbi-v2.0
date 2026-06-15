"""团队协调器: 领导智能体的决策循环。

支持四种模式: coordinate / route / broadcast / tasks
支持嵌套: 成员可以是子团队（递归创建 TeamCoordinator）
支持混合: 成员可以是智能体、工作流、子团队、自定义流程
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any, Callable, Dict, List, Optional

from openai import OpenAI

from backend.ask.team_engine.context import TeamContext
from backend.ask.team_engine.task_board import TaskBoard
from backend.ask.team_engine.custom_flow import execute_custom_flow

logger = logging.getLogger(__name__)

MAX_NESTING_DEPTH = 3


def _load_config() -> dict:
    from config.config_db import _load_config as _cfg
    return _cfg()


class TeamCoordinator:
    """团队协调器 — 领导智能体的决策循环。"""

    def __init__(
        self,
        team_config: Dict[str, Any],
        chatid: str,
        datasource_name: Optional[str] = None,
        skill_ids: Optional[List[int]] = None,
        progress_callback: Optional[Callable] = None,
        depth: int = 0,
    ):
        self.team = team_config
        self.chatid = chatid
        self.datasource_name = datasource_name
        self.skill_ids = skill_ids
        self.progress = progress_callback
        self.depth = depth
        self.context = TeamContext()
        self.members: Dict[str, Dict[str, Any]] = {}
        for m in team_config.get("members", []):
            self.members[m["member_key"]] = m

        # OpenAI 客户端（复用全局配置）
        conf = _load_config()
        self.client = OpenAI(
            api_key=conf.get("api_key", ""),
            base_url=conf.get("base_url", ""),
            timeout=90.0,
        )
        self.model = conf.get("model", "")

    # ── 入口 ──

    def run(self, user_input: str) -> Dict[str, Any]:
        mode = self.team.get("mode", "coordinate")
        if mode == "route":
            return self._run_route(user_input)
        elif mode == "broadcast":
            return self._run_broadcast(user_input)
        elif mode == "tasks":
            return self._run_tasks(user_input)
        else:
            return self._run_coordinate(user_input)

    # ── 四种模式 ──

    def _run_coordinate(self, user_input: str) -> Dict[str, Any]:
        """协调模式: 领导智能体循环决策，直到任务完成。"""
        leader_system = self._build_leader_prompt()
        messages: List[Dict[str, str]] = [
            {"role": "system", "content": leader_system},
            {"role": "user", "content": user_input},
        ]

        max_rounds = self.team.get("max_iterations", 10)
        for round_num in range(max_rounds):
            self._emit_stage("团队协调者正在思考...", "team_thinking", round_num)
            response = self._llm(messages)
            decision = self._parse_decision(response)

            if decision["action"] == "delegate":
                member_key = decision["member"]
                task = decision["task"]
                self._emit_stage(f"委派给 {member_key}: {task[:80]}", "delegation", round_num, member_key)

                result = self._delegate(member_key, task)
                self.context.add_interaction(member_key, task, result)

                messages.append({"role": "assistant", "content": response})
                messages.append({
                    "role": "user",
                    "content": f"[{member_key} 的执行结果]:\n{result}",
                })

            elif decision["action"] == "respond":
                self._emit_stage("团队协调者正在综合结果...", "team_synthesis")
                return {
                    "answer": decision["response"],
                    "interactions": self.context.get_all(),
                }
            else:
                raise ValueError(f"领导智能体返回未知动作: {decision['action']}")

        raise RuntimeError(f"团队协调超过最大轮次 ({max_rounds})")

    def _run_route(self, user_input: str) -> Dict[str, Any]:
        """路由模式: 领导智能体选一个成员，直接返回其结果。"""
        leader_system = self._build_leader_prompt()
        messages = [
            {"role": "system", "content": leader_system},
            {"role": "user", "content": (
                f"用户问题: {user_input}\n\n"
                '请分析并选择最合适的成员。输出 JSON: {"member": "member_key", "reason": "原因"}'
            )},
        ]

        self._emit_stage("团队协调者正在路由...", "team_thinking")
        response = self._llm(messages)
        decision = json.loads(self._extract_json(response))
        member_key = decision["member"]

        if member_key not in self.members:
            raise ValueError(f"领导选择了不存在的成员: {member_key}")

        self._emit_stage(f"路由到 {member_key}", "routing", member_key=member_key)
        result = self._delegate(member_key, user_input)
        return {"answer": result, "routed_to": member_key}

    def _run_broadcast(self, user_input: str) -> Dict[str, Any]:
        """广播模式: 同一任务发给所有成员并行执行。"""
        member_keys = list(self.members.keys())
        self._emit_stage(f"广播给所有成员: {', '.join(member_keys)}", "broadcasting")

        results: Dict[str, str] = {}
        for key in member_keys:
            results[key] = self._delegate(key, user_input)
            self._emit_stage(f"成员 {key} 完成", "member_result", member_key=key)

        summary_prompt = "以下是团队成员对同一问题的不同回答:\n"
        for key, result in results.items():
            summary_prompt += f"\n【{key}】:\n{result}\n"
        summary_prompt += "\n请综合所有回答，给出最终答案。"

        self._emit_stage("团队协调者正在综合所有结果...", "team_synthesis")
        leader_system = self._build_leader_prompt()
        messages = [
            {"role": "system", "content": leader_system},
            {"role": "user", "content": summary_prompt},
        ]
        final = self._llm(messages)
        return {"answer": final, "member_results": results}

    def _run_tasks(self, user_input: str) -> Dict[str, Any]:
        """任务模式: 领导拆解目标为任务列表，逐个/并行委派。"""
        leader_system = self._build_leader_prompt()
        task_board = TaskBoard()

        self._emit_stage("团队协调者正在拆解任务...", "team_thinking")
        decompose_msg = (
            f"请将以下目标拆解为具体任务:\n{user_input}\n\n"
            '输出 JSON 数组: [{"title": "...", "assignee": "member_key", "depends_on": []}]'
        )
        messages = [
            {"role": "system", "content": leader_system},
            {"role": "user", "content": decompose_msg},
        ]
        response = self._llm(messages)
        tasks = json.loads(self._extract_json(response))
        for t in tasks:
            task_board.add(t)

        max_iter = self.team.get("max_iterations", 10)
        for iteration in range(max_iter):
            pending = task_board.get_executable()
            if not pending:
                break

            for task in pending:
                task_board.update_status(task["id"], "in_progress")
                self._emit_stage(
                    f"执行任务: {task['title']}", "executing",
                    member_key=task["assignee"],
                )

                try:
                    result = self._delegate(task["assignee"], task.get("title", ""))
                    task_board.complete(task["id"], result)
                except Exception as e:
                    task_board.fail(task["id"], str(e))

            if not task_board.has_pending():
                break

        self._emit_stage("团队协调者正在汇总所有结果...", "team_synthesis")
        all_results = task_board.get_all_results()
        summary_prompt = "所有任务执行结果:\n"
        for tid, r in all_results.items():
            summary_prompt += f"\n任务: {r['title']}\n结果: {r['result']}\n状态: {r['status']}\n"
        summary_prompt += "\n请汇总所有结果，给出最终答案。"

        messages = [
            {"role": "system", "content": leader_system},
            {"role": "user", "content": summary_prompt},
        ]
        final = self._llm(messages)
        return {"answer": final, "tasks": task_board.to_dict()}

    # ── 委派（按成员类型分发）──

    def _delegate(self, member_key: str, task: str) -> str:
        """委派任务给指定成员 — 根据成员类型分发不同的执行逻辑。"""
        member = self.members.get(member_key)
        if not member:
            raise ValueError(f"成员不存在: {member_key}")

        member_type = member["member_type"]

        if member_type == "agent":
            return self._exec_agent(member, task)
        elif member_type == "workflow":
            return self._exec_workflow(member, task)
        elif member_type == "sub_team":
            return self._exec_sub_team(member, task)
        elif member_type == "custom_flow":
            return self._exec_custom_flow(member, task)
        else:
            raise ValueError(f"未知成员类型: {member_type}")

    def _exec_agent(self, member: Dict[str, Any], task: str) -> str:
        """执行智能体成员: 单次 LLM 调用。"""
        agent_name = member["ref_agent_name"]
        from backend.ask.agents_config.agent_manager import agent_manager
        agent_config = agent_manager.get_agent_config(agent_name, skill_ids=self.skill_ids)
        system_prompt = agent_config["instructions"]
        if agent_config.get("skill_prompt"):
            system_prompt = f"{system_prompt}\n{agent_config['skill_prompt']}"

        context_parts = []
        if self.datasource_name:
            try:
                from backend.ask.sql.schema_loader import load_schema_info
                schema_info = load_schema_info(self.datasource_name)
                context_parts.append(f"数据源信息:\n{schema_info}")
            except Exception:
                pass

        history = self.context.get_relevant_history(member["member_key"])
        if history:
            context_parts.append(f"相关历史:\n{history}")

        user_content = "\n\n".join(context_parts + [f"任务: {task}"]) if context_parts else task

        return self._llm([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ])

    def _exec_workflow(self, member: Dict[str, Any], task: str) -> str:
        """执行工作流成员: 调用现有 workflow.run()。"""
        workflow_name = member["ref_workflow"]

        if workflow_name == "bi":
            from backend.ask.workflows.bi_workflow import BiWorkflow
            wf = BiWorkflow()
            result = wf.run(
                question=task,
                datasource_name=self.datasource_name,
                progress_callback=self.progress,
                chatid=self.chatid,
                active_skill_ids=self.skill_ids,
            )
            return self._extract_workflow_result(result)

        elif workflow_name == "excel":
            from backend.ask.workflows.askexcel_workflow import AskExcelWorkflow
            wf = AskExcelWorkflow()
            result = wf.run(
                question=task,
                progress_callback=self.progress,
                chatid=self.chatid,
            )
            return self._extract_workflow_result(result)

        else:
            raise ValueError(f"未知工作流: {workflow_name}")

    def _exec_sub_team(self, member: Dict[str, Any], task: str) -> str:
        """执行子团队成员: 创建嵌套 TeamCoordinator，递归执行。"""
        if self.depth >= MAX_NESTING_DEPTH:
            raise RuntimeError(f"团队嵌套深度超过限制 ({MAX_NESTING_DEPTH})")

        from backend.ask.team_engine.team_loader import load_team
        sub_team_id = member["ref_team_id"]
        sub_team_config = load_team(sub_team_id)
        if not sub_team_config:
            raise ValueError(f"子团队不存在: id={sub_team_id}")

        sub_coordinator = TeamCoordinator(
            team_config=sub_team_config,
            chatid=self.chatid,
            datasource_name=self.datasource_name,
            skill_ids=self.skill_ids,
            progress_callback=self.progress,
            depth=self.depth + 1,
        )

        result = sub_coordinator.run(task)
        self._emit_stage(
            f"子团队 [{member.get('role', member['member_key'])}] 完成",
            "sub_team_done",
        )
        return result.get("answer", str(result))

    def _exec_custom_flow(self, member: Dict[str, Any], task: str) -> str:
        """执行自定义流程成员: 按步骤序列依次执行。"""
        flow_config = member.get("ref_custom_flow", {})

        def get_instructions(agent_name: str) -> str:
            from backend.ask.agents_config.agent_manager import agent_manager
            config = agent_manager.get_agent_config(agent_name, skill_ids=self.skill_ids)
            instructions = config["instructions"]
            if config.get("skill_prompt"):
                instructions = f"{instructions}\n{config['skill_prompt']}"
            return instructions

        def on_step(msg: str, event_type: str):
            self._emit_stage(msg, event_type)

        return execute_custom_flow(
            flow_config=flow_config,
            task=task,
            llm_call=self._llm,
            get_agent_instructions=get_instructions,
            progress_callback=on_step,
        )

    # ── 工具方法 ──

    def _llm(self, messages: List[Dict[str, str]]) -> str:
        """调用 LLM。"""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.1,
            extra_body={"enable_thinking": False},
        )
        return (response.choices[0].message.content or "").strip()

    def _emit_stage(self, message: str, stage: str, round_num: int = 0, member_key: str = "") -> None:
        """推送 SSE 进度事件。"""
        if self.progress:
            payload: Dict[str, Any] = {
                "stage": stage,
                "message": message,
                "depth": self.depth,
                "round": round_num,
            }
            if member_key:
                member = self.members.get(member_key, {})
                payload["member_key"] = member_key
                payload["member_type"] = member.get("member_type", "")
            try:
                self.progress(json.dumps(payload, ensure_ascii=False))
            except Exception:
                pass

    def _build_leader_prompt(self) -> str:
        """构建领导智能体的系统提示，包含所有成员信息。"""
        leader_cfg = self.team.get("leader_config", {})
        base = leader_cfg.get("instructions", "你是一个团队协调者。")

        type_labels = {
            "agent": "智能体（单次LLM调用）",
            "workflow": "工作流（完整多步流程）",
            "sub_team": "子团队（独立决策的多智能体组）",
            "custom_flow": "自定义流程（固定步骤序列）",
        }

        member_info = "## 团队成员\n\n"
        for m in self.team.get("members", []):
            caps = ", ".join(m.get("capabilities", []))
            type_label = type_labels.get(m["member_type"], m["member_type"])
            member_info += f"- **{m['member_key']}** [{type_label}] (角色: {m.get('role', '未知')})\n"
            member_info += f"  能力: {caps}\n"
            member_info += f"  描述: {m.get('description', '无')}\n\n"

        mode = self.team.get("mode", "coordinate")
        mode_instructions = {
            "coordinate": (
                "你运行在协调模式。根据任务需要选择合适的成员委派任务。"
                '每次委派时输出 JSON: {"action": "delegate", "member": "member_key", "task": "任务描述"}。'
                '当所有工作完成后，输出: {"action": "respond", "response": "最终答案"}。'
            ),
            "route": (
                "你运行在路由模式。分析问题后选择最合适的一个成员。"
                '输出 JSON: {"member": "member_key", "reason": "选择原因"}。'
            ),
            "broadcast": "你运行在广播模式。将任务广播给所有成员，然后综合他们的回答。",
            "tasks": (
                "你运行在任务模式。将目标拆解为任务列表，分配给合适的成员。"
                '任务 JSON 格式: [{"title": "...", "assignee": "member_key", "depends_on": []}]。'
            ),
        }

        return f"{base}\n\n{member_info}\n## 运行模式\n{mode_instructions.get(mode, mode_instructions['coordinate'])}"

    def _parse_decision(self, response: str) -> Dict[str, Any]:
        """解析领导智能体的 JSON 决策。"""
        json_str = self._extract_json(response)
        decision = json.loads(json_str)

        action = decision.get("action", "")
        if not action:
            # 如果有 member 字段，推断为 delegate
            if "member" in decision:
                decision["action"] = "delegate"
                decision["task"] = decision.get("task", response)
            elif "response" in decision:
                decision["action"] = "respond"
            else:
                # 默认为 respond
                decision["action"] = "respond"
                decision["response"] = response

        return decision

    @staticmethod
    def _extract_json(text: str) -> str:
        """从 LLM 响应中提取 JSON 字符串。"""
        # 尝试直接解析
        text = text.strip()
        if text.startswith("{") or text.startswith("["):
            try:
                json.loads(text)
                return text
            except json.JSONDecodeError:
                pass

        # 从 markdown 代码块提取
        match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
        if match:
            return match.group(1).strip()

        # 从文本中找到第一个 { 或 [ 到最后一个 } 或 ]
        for start_char, end_char in [("{", "}"), ("[", "]")]:
            start = text.find(start_char)
            end = text.rfind(end_char)
            if start != -1 and end != -1 and end > start:
                candidate = text[start:end + 1]
                try:
                    json.loads(candidate)
                    return candidate
                except json.JSONDecodeError:
                    continue

        raise ValueError(f"无法从响应中提取 JSON: {text[:200]}")

    @staticmethod
    def _extract_workflow_result(result: Any) -> str:
        """从工作流返回值中提取关键结果文本。"""
        if isinstance(result, dict):
            # bi_workflow 返回格式
            summary = result.get("summary", "")
            report = result.get("report", "")
            if summary:
                return summary
            if report:
                return report
            # 取 result 字段
            if "result" in result:
                r = result["result"]
                return r if isinstance(r, str) else json.dumps(r, ensure_ascii=False)
            return json.dumps(result, ensure_ascii=False)[:2000]
        return str(result)
