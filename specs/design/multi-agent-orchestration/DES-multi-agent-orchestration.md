# 多智能体编排系统设计总览

**版本**: v2.2
**模块**: multi-agent-orchestration
**状态**: 设计中

> v2.2 变更: 统一会话模型成为主入口。新建对话默认为普通对话，数据源、Excel、团队能力在同一会话内后续挂载。
> v2.1 变更: 引入团队、智能体、工作流、子团队、自定义流程的可组合架构。
> v2.0 变更: 废弃 v1.0 的 DAG 工作流方案，改为基于 Agno Team 概念的团队决策架构。

---

## 一、设计目标

1. **统一会话入口**: 新建对话默认创建普通会话，不预先绑定 BI / Excel / Team 类型
2. **会话内上下文挂载**: 用户可在同一会话内后续选择数据源、Excel 数据源或团队能力
3. **复用现有执行链路**: BI、Excel、Team 保留现有执行能力，仅调整入口与路由模型
4. **图表结果产品化**: 聊天中的图表结果采用卡片化展示、弱化辅助元素、预设主题色板和表单化配置面板，避免默认图表组件的工程态观感
5. **可组合架构**: 团队成员不限于智能体，还可以是子工作流、子团队（子决策），支持任意嵌套
5. **可视化拓扑**: 画布展示团队结构和成员关系
6. **自定义智能体**: 用户可自由新增智能体，后端自动生成 `.py` 文件
7. **无兜底**: 所有环节失败直接报错，不做降级、不做模拟

### 1.1 与现有系统的边界

```
                    ┌──────────────────────────────────┐
                    │           不变的部分              │
                    │                                  │
                    │  bi_workflow.py      ← 不改动    │
                    │  askexcel_workflow.py ← 不改动    │
                    │  bi_api.py           ← 不改动    │
                    │  excel_api.py        ← 不改动    │
                    │  agents/*.py         ← 不改动    │
                    │  /progress/ask       ← 不改动    │
                    │  /excel/ask          ← 不改动    │
                    └──────────────────────────────────┘

                    ┌──────────────────────────────────┐
                    │           新增的部分              │
                    │                                  │
                    │  team_engine/        ← 全新模块   │
                    │  agents_custom/      ← 自建智能体 │
                    │  askbi_teams         ← 新数据表   │
                    │  askbi_team_members  ← 新数据表   │
                    │  TeamEditor.jsx      ← 新页面    │
                    │  /teams/*            ← 新 API    │
                    │  /team/{id}/run      ← 新 API    │
                    └──────────────────────────────────┘
```

**唯一共享的**: 团队成员可以引用 `askbi_agents` 表里的智能体名称（如 `bi_sql_agent`），复用 agent_manager 加载其 prompt。但调用方式和调用链路完全独立。

---

## 二、核心理念

### 2.1 团队 vs 工作流

```
工作流（bi_workflow / askexcel_workflow）:
  预定义路径: 取schema → 生成SQL → 执行SQL → 生成报告 → 生成图表
  执行方式: 硬编码顺序，固定流程
  用途: 默认问数，不需要用户配置

团队（本方案的新功能）:
  定义: 谁在团队里、各自什么角色、什么类型的成员
  运行时: 领导智能体看到问题后，自主决定调用哪些成员、怎么组合结果
  用途: 用户自定义复杂场景（多步分析、多领域协作、自定义路由等）
```

### 2.2 可组合的成员类型

团队成员**不只是智能体**，而是四种可组合的类型：

| 成员类型 | 标识 | 运行时行为 | 用途 |
|---------|------|-----------|------|
| **智能体** | `agent` | 单次 LLM 调用（加载 prompt + 执行） | 简单任务（SQL 生成、文本分析等） |
| **工作流** | `workflow` | 调用现有 workflow.run()（完整多步流程） | 需要完整问数流程（生成SQL→执行→报告→图表） |
| **子团队** | `sub_team` | 创建嵌套 TeamCoordinator，子团队自主决策 | 子决策单元（独立的多智能体协作） |
| **自定义流程** | `custom_flow` | 执行用户定义的步骤序列（轻量级小流程） | 团队内部的固定子流程（如：校验→修正） |

### 2.3 组合示例

```
┌─────────────────────────────────────────────────────────────┐
│  数据分析总团队（Coordinate 模式）                            │
│  领导: 总协调者                                              │
│                                                             │
│  成员:                                                      │
│  ├── [智能体] 意图识别器      ← 单次 LLM，判断问题类型        │
│  ├── [工作流] BI问数流程      ← 调用 bi_workflow.run()       │
│  ├── [工作流] Excel分析流程   ← 调用 askexcel_workflow.run() │
│  ├── [子团队] 深度分析组      ← 嵌套团队，有自己的领导和成员   │
│  │     ├── 领导: 分析主管                                    │
│  │     ├── [智能体] 统计专家                                 │
│  │     ├── [智能体] 趋势分析师                               │
│  │     └── [自定义流程] 数据校验链  ← 校验→修正→再校验        │
│  └── [智能体] 报告汇总员      ← 单次 LLM，整合所有结果        │
└─────────────────────────────────────────────────────────────┘
```

运行时:
1. 用户提问 → 总协调者分析问题
2. 协调者决定先调用**意图识别器**（智能体）判断问题类型
3. 根据意图：
   - 如果是数据库问题 → 委派给 **BI问数流程**（工作流），走完整的 SQL 生成→执行→报告→图表
   - 如果是复杂多维分析 → 委派给 **深度分析组**（子团队），子团队自己决策怎么分工
4. 最后交给**报告汇总员**（智能体）整合输出

---

## 三、Agno Team 模式适配

Agno 原生支持四种团队协作模式，本方案全部适配：

### 3.1 Coordinate 模式（协调模式，默认）

```
用户问题
   │
   ▼
[领导智能体]──分析任务──→ 选择成员 A ──→ 委派任务 ──→ A 执行 ──→ 返回结果
   │                         │
   │                         └→ 选择成员 B ──→ 委派任务 ──→ B 执行 ──→ 返回结果
   │
   ▼
 综合所有成员结果，输出最终答案
```

- 领导智能体: 分析任务 → 选最合适的成员 → 委派任务 → 收集结果 → 综合输出
- 适用: 需要多专家协作的复杂分析

### 3.2 Route 模式（路由模式）

```
用户问题
   │
   ▼
[领导智能体]──分析任务──→ 选择最佳成员 ──→ 委派任务 ──→ 成员执行
                                                            │
                                                            ▼
                                                     直接返回成员结果
```

- 领导智能体: 只做路由判断，选一个最匹配的成员
- 适用: 分类明确的场景（技术问题 → 技术专家，财务问题 → 财务专家）

### 3.3 Broadcast 模式（广播模式）

```
用户问题
   │
   ▼
[领导智能体]──→ 同一任务 ──┬→ 成员 A（并行）──→ 结果 A ─┐
                            ├→ 成员 B（并行）──→ 结果 B ─┤
                            └→ 成员 C（并行）──→ 结果 C ─┤
                                                         ▼
                                                   综合所有结果
```

- 领导智能体: 把同一任务发给所有成员并行执行，收集所有视角后综合
- 适用: 需要多视角分析

### 3.4 Tasks 模式（自主任务模式）

```
用户目标
   │
   ▼
[领导智能体]──拆解目标──→ 创建任务列表（含依赖关系）
   │
   ├── 执行任务 1（委派给成员 A）──→ 完成
   ├── 执行任务 2（委派给成员 B，依赖任务 1）──→ 完成
   └── 所有任务完成 ──→ 汇总输出
```

- 领导智能体: 像项目经理一样拆解目标、分配任务、追踪进度
- 适用: 复杂多步骤目标

### 3.5 模式选择总结

| 模式 | 领导角色 | 成员选择 | 结果处理 | 典型场景 |
|------|---------|---------|---------|---------|
| Coordinate | 协调者 | 按需选 1~N 个 | 综合输出 | 多维分析 |
| Route | 路由器 | 只选 1 个 | 直接转发 | 分类路由 |
| Broadcast | 广播者 | 全部成员 | 比较综合 | 多视角评估 |
| Tasks | 项目经理 | 按任务分配 | 逐项汇总 | 复杂多步目标 |

---

## 四、自定义智能体设计

### 4.1 文件隔离策略

```
backend/ask/
├── agents/                    # 内置智能体（不改动）
│   ├── bi_sql_agent.py
│   ├── bi_report_agent.py
│   ├── bi_chart_agent.py
│   ├── askexcel_code_agent.py
│   ├── askexcel_report_agent.py
│   └── askexcel_chart_agent.py
│
└── agents_custom/             # 用户自建智能体（自动生成）
    ├── __init__.py
    ├── my_data_validator.py
    ├── intent_classifier.py
    └── ...
```

### 4.2 自动生成 `.py` 文件格式

```python
# backend/ask/agents_custom/my_validator.py
# 自动生成 - 通过管理页面修改
from openai import OpenAI
from core import _load_config

INSTRUCTIONS = """
（用户填写的指令内容）
"""

def run(user_input: str, context: dict = None) -> str:
    """执行智能体任务。"""
    conf = _load_config()
    client = OpenAI(api_key=conf["api_key"], base_url=conf["base_url"], timeout=90.0)
    model = conf["model"]

    system_prompt = INSTRUCTIONS
    if context and context.get("skill_prompt"):
        system_prompt = f"{system_prompt}\n{context['skill_prompt']}"

    messages = [{"role": "system", "content": system_prompt}]
    if context and context.get("history"):
        messages.extend(context["history"])
    messages.append({"role": "user", "content": user_input})

    result = client.chat.completions.create(
        model=model, messages=messages, temperature=0.1,
        extra_body={"enable_thinking": False},
    )
    return (result.choices[0].message.content or "").strip()
```

### 4.3 DB 存储

复用 `askbi_agents` 表，新增字段:

| 字段 | 类型 | 说明 |
|------|------|------|
| `is_builtin` | bool | 内置 vs 自建 |
| `agent_type` | varchar | `specialist` / `coordinator` / `router` |
| `file_path` | varchar | 自动生成的 `.py` 文件路径 |
| `role_description` | text | 角色描述（供领导智能体参考） |
| `capabilities` | jsonb | 能力标签列表 |

---

## 五、团队数据模型

### 5.1 数据库表

```sql
CREATE TABLE askbi_teams (
    id              SERIAL PRIMARY KEY,
    name            VARCHAR(100) NOT NULL,
    description     TEXT,
    mode            VARCHAR(20) NOT NULL DEFAULT 'coordinate',
                    -- coordinate / route / broadcast / tasks
    leader_config   JSONB NOT NULL,
                    -- 领导智能体配置:
                    -- { agent_name, instructions, model_override }
    max_iterations  INTEGER DEFAULT 10,
                    -- Tasks 模式最大迭代次数
    is_active       BOOLEAN DEFAULT TRUE,
    created_by      INTEGER REFERENCES askbi_users(id),
    created_at      TIMESTAMP DEFAULT NOW(),
    updated_at      TIMESTAMP DEFAULT NOW()
);

CREATE TABLE askbi_team_members (
    id              SERIAL PRIMARY KEY,
    team_id         INTEGER REFERENCES askbi_teams(id) ON DELETE CASCADE,

    -- 成员标识
    member_key      VARCHAR(100) NOT NULL,
                    -- 成员唯一标识（在同一团队内唯一）

    -- 成员类型（核心: 决定运行时行为）
    member_type     VARCHAR(20) NOT NULL,
                    -- agent / workflow / sub_team / custom_flow

    -- 类型对应的引用
    ref_agent_name  VARCHAR(100),
                    -- member_type=agent 时: askbi_agents.name
    ref_workflow    VARCHAR(50),
                    -- member_type=workflow 时: "bi" | "excel"
    ref_team_id     INTEGER,
                    -- member_type=sub_team 时: askbi_teams.id（嵌套引用）
    ref_custom_flow JSONB,
                    -- member_type=custom_flow 时: 步骤定义 JSON

    -- 角色信息（注入到领导智能体的系统提示中）
    role            VARCHAR(50),
                    -- 角色名（如 "SQL专家", "BI问数流程"）
    description     TEXT,
                    -- 详细能力描述
    capabilities    JSONB DEFAULT '[]',
                    -- 能力标签列表

    -- 委派关系
    can_delegate_to JSONB DEFAULT '[]',
                    -- 可委派任务的目标成员 member_key 列表

    -- 可视化
    position        JSONB,
                    -- 画布坐标 { x, y }
    sort_order      INTEGER DEFAULT 0
);
```

### 5.2 团队配置 JSON 示例（含嵌套组合）

```json
{
  "team": {
    "id": 1,
    "name": "数据分析总团队",
    "description": "处理各类数据查询和深度分析任务",
    "mode": "coordinate"
  },
  "leader": {
    "agent_name": "team_coordinator",
    "instructions": "你是数据分析团队的负责人。根据用户问题性质选择合适成员：简单查询交给BI问数流程，复杂多维分析交给深度分析组，最后让报告汇总员整合输出。",
    "model_override": null
  },
  "members": [
    {
      "member_key": "intent_classifier",
      "member_type": "agent",
      "ref_agent_name": "custom_intent_classifier",
      "role": "意图识别器",
      "description": "分析用户问题，判断属于简单查询、多维分析还是Excel分析",
      "capabilities": ["intent", "classification"],
      "can_delegate_to": []
    },
    {
      "member_key": "bi_workflow",
      "member_type": "workflow",
      "ref_workflow": "bi",
      "role": "BI问数流程",
      "description": "完整的数据库问数流程：自动生成SQL、执行查询、生成报告和图表。适合标准数据库查询问题。",
      "capabilities": ["sql", "database", "query", "report", "chart"],
      "can_delegate_to": []
    },
    {
      "member_key": "excel_workflow",
      "member_type": "workflow",
      "ref_workflow": "excel",
      "role": "Excel分析流程",
      "description": "完整的Excel文件分析流程：自动分析文件结构、生成代码、执行分析、生成报告和图表。",
      "capabilities": ["excel", "file_analysis", "pandas"],
      "can_delegate_to": []
    },
    {
      "member_key": "deep_analysis_team",
      "member_type": "sub_team",
      "ref_team_id": 2,
      "role": "深度分析组",
      "description": "由分析主管领导的深度分析子团队，包含统计专家和趋势分析师，适合需要多维度深入分析的问题。",
      "capabilities": ["deep_analysis", "statistics", "trend"],
      "can_delegate_to": []
    },
    {
      "member_key": "report_summarizer",
      "member_type": "agent",
      "ref_agent_name": "custom_report_summarizer",
      "role": "报告汇总员",
      "description": "整合所有成员/子团队的输出结果，生成最终的统一报告",
      "capabilities": ["summary", "report", "synthesis"],
      "can_delegate_to": []
    }
  ]
}
```

### 5.3 子团队配置示例（被嵌套引用）

```json
{
  "team": {
    "id": 2,
    "name": "深度分析组",
    "description": "多维度深入分析子团队",
    "mode": "coordinate"
  },
  "leader": {
    "agent_name": "analysis_manager",
    "instructions": "你是深度分析组的主管。根据分析任务分配给统计专家或趋势分析师，复杂任务可以同时委派再综合。",
    "model_override": null
  },
  "members": [
    {
      "member_key": "stat_expert",
      "member_type": "agent",
      "ref_agent_name": "custom_stat_expert",
      "role": "统计专家",
      "description": "擅长统计分析、假设检验、相关性分析",
      "capabilities": ["statistics", "hypothesis_testing"],
      "can_delegate_to": []
    },
    {
      "member_key": "trend_analyst",
      "member_type": "agent",
      "ref_agent_name": "custom_trend_analyst",
      "role": "趋势分析师",
      "description": "擅长时间序列分析、趋势预测、异常检测",
      "capabilities": ["trend", "time_series", "forecast"],
      "can_delegate_to": []
    },
    {
      "member_key": "validation_flow",
      "member_type": "custom_flow",
      "ref_custom_flow": {
        "name": "数据校验链",
        "steps": [
          {
            "step_name": "validate",
            "agent_name": "custom_validator",
            "instruction": "校验数据分析结果的合理性和一致性"
          },
          {
            "step_name": "fix",
            "agent_name": "custom_stat_expert",
            "instruction": "如果校验发现问题，修正分析方法和结论",
            "condition": "if_previous_has_issues"
          }
        ]
      },
      "role": "数据校验链",
      "description": "先校验分析结果，如有问题则修正，确保输出质量",
      "capabilities": ["validation", "quality_check"],
      "can_delegate_to": []
    }
  ]
}
```

---

## 六、团队协调器（后端核心）

### 6.1 架构概览

```
backend/ask/team_engine/
├── __init__.py
├── coordinator.py       # 团队协调器: 领导智能体的决策循环
├── delegation.py        # 委派执行: 根据成员类型分发执行
├── context.py           # 共享上下文: 团队对话历史、中间结果
├── team_loader.py       # 团队加载: 从 DB 读取团队配置（含嵌套解析）
├── custom_flow.py       # 自定义流程: 执行 custom_flow 类型的步骤序列
└── task_board.py        # 任务看板: Tasks 模式的任务管理
```

### 6.2 coordinator.py — 核心决策循环

```python
class TeamCoordinator:
    """团队协调器 — 领导智能体的决策循环。

    支持嵌套: 成员可以是子团队（递归创建 TeamCoordinator）。
    支持混合: 成员可以是智能体、工作流、子团队、自定义流程。
    """

    def __init__(self, team_config: dict, chatid: str,
                 datasource_name: str = None,
                 skill_ids: list = None,
                 progress_callback=None,
                 depth: int = 0):
        self.team = team_config
        self.chatid = chatid
        self.datasource_name = datasource_name
        self.skill_ids = skill_ids
        self.progress = progress_callback
        self.depth = depth  # 嵌套深度
        self.context = TeamContext()
        self.members = {}
        for m in team_config["members"]:
            self.members[m["member_key"]] = m

    def run(self, user_input: str) -> dict:
        mode = self.team["mode"]
        if mode == "route":
            return self._run_route(user_input)
        elif mode == "broadcast":
            return self._run_broadcast(user_input)
        elif mode == "tasks":
            return self._run_tasks(user_input)
        else:
            return self._run_coordinate(user_input)

    def _run_coordinate(self, user_input):
        """协调模式: 领导智能体循环决策，直到任务完成。"""
        leader_system = self._build_leader_prompt()
        messages = [
            {"role": "system", "content": leader_system},
            {"role": "user", "content": user_input},
        ]

        max_rounds = self.team.get("max_iterations", 10)
        for round_num in range(max_rounds):
            response = self._llm(messages)
            decision = self._parse_decision(response)

            if decision["action"] == "delegate":
                member_key = decision["member"]
                task = decision["task"]
                self._emit_stage(f"委派给 {member_key}", "delegating", round_num)

                result = self._delegate(member_key, task)
                self.context.add_interaction(member_key, task, result)

                messages.append({"role": "assistant", "content": response})
                messages.append({
                    "role": "user",
                    "content": f"[{member_key} 的执行结果]:\n{result}"
                })

            elif decision["action"] == "respond":
                return {
                    "answer": decision["response"],
                    "interactions": self.context.get_all(),
                }
            else:
                raise ValueError(f"未知动作: {decision['action']}")

        raise RuntimeError(f"团队协调超过最大轮次 ({max_rounds})")

    def _run_route(self, user_input):
        """路由模式: 领导智能体选一个成员，直接返回其结果。"""
        leader_system = self._build_leader_prompt()
        messages = [
            {"role": "system", "content": leader_system},
            {"role": "user", "content": (
                f"用户问题: {user_input}\n\n"
                "请分析并选择最合适的成员。输出 JSON: "
                '{"member": "member_key", "reason": "原因"}'
            )},
        ]

        response = self._llm(messages)
        decision = json.loads(self._extract_json(response))
        member_key = decision["member"]

        if member_key not in self.members:
            raise ValueError(f"领导选择了不存在的成员: {member_key}")

        self._emit_stage(f"路由到 {member_key}", "routing")
        result = self._delegate(member_key, user_input)
        return {"answer": result, "routed_to": member_key}

    def _run_broadcast(self, user_input):
        """广播模式: 同一任务发给所有成员并行执行。"""
        member_keys = list(self.members.keys())
        self._emit_stage(f"广播给所有成员", "broadcasting")

        results = {}
        for key in member_keys:
            results[key] = self._delegate(key, user_input)

        summary_prompt = "以下是团队成员对同一问题的不同回答:\n"
        for key, result in results.items():
            summary_prompt += f"\n【{key}】:\n{result}\n"
        summary_prompt += "\n请综合所有回答，给出最终答案。"

        leader_system = self._build_leader_prompt()
        messages = [
            {"role": "system", "content": leader_system},
            {"role": "user", "content": summary_prompt},
        ]
        final = self._llm(messages)
        return {"answer": final, "member_results": results}

    def _run_tasks(self, user_input):
        """任务模式: 领导拆解目标为任务列表，逐个/并行委派。"""
        leader_system = self._build_leader_prompt()
        task_board = TaskBoard()

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
        for _ in range(max_iter):
            pending = task_board.get_executable()
            if not pending:
                break

            for task in pending:
                task_board.update_status(task["id"], "in_progress")
                self._emit_stage(f"执行任务: {task['title']}", "executing")

                result = self._delegate(task["assignee"], task.get("title", ""))
                task_board.complete(task["id"], result)

            if not task_board.has_pending():
                break

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
```

### 6.3 delegation.py — 按成员类型分发执行（核心）

```python
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


def _exec_agent(self, member: dict, task: str) -> str:
    """执行智能体成员: 单次 LLM 调用。"""
    agent_name = member["ref_agent_name"]
    agent_config = agent_manager.get_agent_config(agent_name, skill_ids=self.skill_ids)
    system_prompt = agent_config["instructions"]

    context_parts = self._build_context_parts(member)
    user_content = "\n\n".join(context_parts + [f"任务: {task}"]) if context_parts else task

    return self._llm([
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content},
    ])


def _exec_workflow(self, member: dict, task: str) -> str:
    """执行工作流成员: 调用现有 workflow.run()。

    注意: 这里调用的是完整的 bi_workflow / askexcel_workflow，
    和默认问数页面的执行方式完全一致，只是入口不同。
    """
    workflow_name = member["ref_workflow"]

    if workflow_name == "bi":
        from workflows.bi_workflow import BiWorkflow
        wf = BiWorkflow()
        result = wf.run(
            question=task,
            datasource_name=self.datasource_name,
            chatid=self.chatid,
            progress_callback=self.progress,
            active_skill_ids=self.skill_ids,
        )
        # 提取关键结果
        return self._extract_workflow_result(result)

    elif workflow_name == "excel":
        from workflows.askexcel_workflow import AskExcelWorkflow
        wf = AskExcelWorkflow()
        result = wf.run(
            question=task,
            chatid=self.chatid,
            progress_callback=self.progress,
        )
        return self._extract_workflow_result(result)

    else:
        raise ValueError(f"未知工作流: {workflow_name}")


def _exec_sub_team(self, member: dict, task: str) -> str:
    """执行子团队成员: 创建嵌套 TeamCoordinator，递归执行。"""
    if self.depth >= MAX_NESTING_DEPTH:
        raise RuntimeError(f"团队嵌套深度超过限制 ({MAX_NESTING_DEPTH})")

    sub_team_id = member["ref_team_id"]
    sub_team_config = team_loader.load_team(sub_team_id)

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
        f"子团队 [{member['role']}] 完成",
        "sub_team_done",
    )
    return result.get("answer", str(result))


def _exec_custom_flow(self, member: dict, task: str) -> str:
    """执行自定义流程成员: 按步骤序列依次执行。"""
    flow_config = member["ref_custom_flow"]
    steps = flow_config.get("steps", [])

    step_results = []
    for i, step in enumerate(steps):
        step_name = step.get("step_name", f"step_{i}")
        agent_name = step["agent_name"]
        instruction = step.get("instruction", task)

        self._emit_stage(f"流程 [{member['role']}] 步骤: {step_name}", "custom_flow_step")

        agent_config = agent_manager.get_agent_config(agent_name, skill_ids=self.skill_ids)
        # 注入前序步骤的结果作为上下文
        prev_context = ""
        if step_results:
            prev_context = "前序步骤结果:\n" + "\n".join(step_results) + "\n\n"

        result = self._llm([
            {"role": "system", "content": agent_config["instructions"]},
            {"role": "user", "content": f"{prev_context}{instruction}"},
        ])
        step_results.append(f"[{step_name}]: {result}")

    return "\n".join(step_results)
```

### 6.4 领导智能体提示构建

```python
def _build_leader_prompt(self) -> str:
    """构建领导智能体的系统提示，包含所有成员信息（含类型标识）。"""
    leader_cfg = self.team["leader_config"]
    base = leader_cfg.get("instructions", "你是一个团队协调者。")

    member_info = "## 团队成员\n\n"
    for m in self.team["members"]:
        caps = ", ".join(m.get("capabilities", []))
        type_label = {
            "agent": "智能体（单次LLM调用）",
            "workflow": "工作流（完整多步流程）",
            "sub_team": "子团队（独立决策的多智能体组）",
            "custom_flow": "自定义流程（固定步骤序列）",
        }.get(m["member_type"], m["member_type"])

        member_info += f"- **{m['member_key']}** [{type_label}] (角色: {m['role']})\n"
        member_info += f"  能力: {caps}\n"
        member_info += f"  描述: {m.get('description', '无')}\n\n"

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

    return (
        f"{base}\n\n{member_info}\n"
        f"## 运行模式\n{mode_instructions[self.team['mode']]}"
    )
```

---

## 七、前端页面设计

### 7.1 页面结构

```
侧边栏新增:
├── 团队管理      → #/teams         （团队列表）
└── 团队编辑器    → #/team/:id      （可视化编辑）
```

### 7.2 团队编辑器 UI

画布展示团队结构和成员关系：

```
┌──────────────────────────────────────────────────────────────────────┐
│  ← 返回  │  团队: [数据分析总团队]  │  模式: [协调模式 ▾]  │ [保存]  │
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  添加成员           画布区域（团队拓扑）                               │
│  ┌────────────┐    ┌──────────────────────────────────────────────┐  │
│  │ 类型:       │    │                                              │  │
│  │ [智能体  ▾] │    │         ┌──────────────────┐                 │  │
│  │             │    │         │  总协调者(领导)   │                 │  │
│  │ 引用:       │    │         └──┬───┬───┬──┬──┘                 │  │
│  │ [选择  ▾]   │    │        委派│ 委派│ 委派│委派│                │  │
│  │             │    │     ┌─────▼┐ ┌▼─────▼┐ │ ┌▼──────┐         │  │
│  │ [添加到画布]│    │     │意图  │ │BI问数  │ │ │报告    │         │  │
│  │             │    │     │识别器│ │流程    │ │ │汇总员  │         │  │
│  │ ──────────  │    │     │[智能]│ │[工作流]│ │ │[智能]  │         │  │
│  │ 已有成员:   │    │     └──────┘ └───────┘ │ └────────┘         │  │
│  │ ☑ 意图识别  │    │                    委派│                     │  │
│  │ ☑ BI问数流程│    │                ┌───────▼───────┐             │  │
│  │ ☑ 深度分析组│    │                │ 深度分析组    │             │  │
│  │ ☑ 报告汇总  │    │                │ [子团队]      │             │  │
│  │ ☑ Excel流程 │    │                │ ┌─────┬────┐ │             │  │
│  └────────────┘    │                │ │统计 │趋势│ │             │  │
│                     │                │ │专家 │分析│ │             │  │
│  属性面板           │                │ └─────┴────┘ │             │  │
│  ┌──────────────┐  │                └───────────────┘             │  │
│  │ BI问数流程    │  │                                              │  │
│  │ 类型: 工作流  │  └──────────────────────────────────────────────┘  │
│  │ 引用: bi     │                                                    │
│  │ 角色: BI问数 │                                                    │
│  │ 描述: [完整..]│                                                    │
│  │ 能力: [sql..]│                                                    │
│  └──────────────┘                                                    │
└──────────────────────────────────────────────────────────────────────┘
```

**节点视觉区分**（按 member_type）：

| 类型 | 节点样式 | 标注 |
|------|---------|------|
| `agent` | 蓝色矩形 | `[智能体]` |
| `workflow` | 绿色圆角矩形 | `[工作流]` |
| `sub_team` | 橙色虚线框（内含子节点） | `[子团队]` |
| `custom_flow` | 紫色矩形 | `[流程]` |
| 领导节点 | 深色加粗边框 | `(领导)` |

### 7.3 技术选型

| 功能 | 方案 | 理由 |
|------|------|------|
| 画布引擎 | **ReactFlow** | React 生态、轻量、支持自定义节点、MIT 开源 |
| 子团队展示 | ReactFlow Group Node | 子团队节点用分组节点包裹子成员 |
| 连线 | ReactFlow Edge | 委派关系线 |

安装:
```bash
cd frontend && npm install reactflow
```

### 7.4 对话页面集成

```
┌──────────────────────────────────┐
│       新建对话                    │
│                                  │
│  选择数据源: [my_pg_db ▾]        │
│                                  │
│  选择模式:                       │
│  ○ 默认 BI 问数（内置）          │  ← 走 bi_workflow，不变
│  ○ 默认 Excel 分析（内置）       │  ← 走 askexcel_workflow，不变
│  ○ 团队: 数据分析总团队          │  ← 走 TeamCoordinator（新功能）
│  ○ 团队: 财务报表分析组          │  ← 走 TeamCoordinator（新功能）
│  ○ + 新建团队                    │
│                                  │
│  [开始对话]                       │
└──────────────────────────────────┘
```

选择"默认 BI 问数" → 走 `/progress/ask` → `bi_workflow.run()`（原有链路，零改动）
选择"团队: XXX" → 走 `/team/{id}/run` → `TeamCoordinator.run()`（新链路）

---

## 八、后端 API 设计

### 8.1 团队 CRUD

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/teams` | 列出所有团队 |
| `GET` | `/teams/{id}` | 获取单个团队（含成员列表，含子团队配置） |
| `POST` | `/teams` | 创建团队 |
| `PUT` | `/teams/{id}` | 更新团队配置和成员 |
| `DELETE` | `/teams/{id}` | 删除团队（检查是否被其他团队引用为子团队） |
| `POST` | `/teams/{id}/test` | 测试运行（单次对话） |

### 8.2 自定义智能体

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/agents` | 创建（自动生成 .py + DB 记录） |
| `PUT` | `/agents/{id}` | 更新（同步更新 .py 文件） |
| `DELETE` | `/agents/{id}` | 删除（删除 .py + DB 记录） |
| `POST` | `/agents/{id}/test` | 测试运行 |

### 8.3 对话集成

**现有 API 不变:**
- `POST /progress/ask` → bi_workflow（默认 BI 问数）
- `POST /excel/ask` → askexcel_workflow（默认 Excel 分析）
- `GET /progress/stream` → SSE（默认问数进度）

**新增:**
| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/team/{id}/run` | 与团队对话（走 TeamCoordinator） |
| `GET` | `/team/{id}/stream` | SSE 流式推送团队决策过程 |

---

## 九、SSE 事件设计

团队模式的 SSE 事件推送**决策过程**，并标注成员类型：

```json
{
  "type": "stage",
  "data": {
    "stage": "team_thinking",
    "status": "running",
    "message": "团队协调者正在分析问题...",
    "depth": 0,
    "round": 1
  }
}
```

```json
{
  "type": "stage",
  "data": {
    "stage": "delegation",
    "status": "running",
    "message": "委派给 BI问数流程: 查询2024年销售数据",
    "member_key": "bi_workflow",
    "member_type": "workflow",
    "task": "查询2024年各月销售额",
    "depth": 0,
    "round": 1
  }
}
```

```json
{
  "type": "stage",
  "data": {
    "stage": "delegation",
    "status": "running",
    "message": "委派给 深度分析组（子团队）: 多维分析销售趋势",
    "member_key": "deep_analysis_team",
    "member_type": "sub_team",
    "depth": 0,
    "round": 2
  }
}
```

```json
{
  "type": "stage",
  "data": {
    "stage": "sub_team_thinking",
    "status": "running",
    "message": "深度分析组 - 分析主管正在决策...",
    "depth": 1,
    "parent_member": "deep_analysis_team"
  }
}
```

```json
{
  "type": "stage",
  "data": {
    "stage": "member_result",
    "status": "done",
    "message": "BI问数流程 完成",
    "member_key": "bi_workflow",
    "member_type": "workflow",
    "depth": 0
  }
}
```

前端 ThinkingPipeline 映射:
```
team_thinking      → 思考图标
delegation         → 委派箭头（按 member_type 显示不同图标）
  agent            → 智能体图标
  workflow         → 流程图标
  sub_team         → 团队图标
  custom_flow      → 步骤图标
sub_team_thinking  → 子团队思考（缩进显示）
member_result      → 完成标记
team_synthesis     → 综合图标
```

---

## 十、与现有系统的关系

```
┌───────────────────────────────────────────────────────────────┐
│                        对话页面                                │
│                                                               │
│  ┌───────────────┐  ┌──────────────┐  ┌────────────────────┐  │
│  │ 默认 BI 问数   │  │默认Excel分析  │  │ 自定义团队（新）    │  │
│  │ /progress/ask  │  │ /excel/ask   │  │ /team/{id}/run     │  │
│  │                │  │              │  │                    │  │
│  │ bi_workflow    │  │askexcel_wf   │  │ TeamCoordinator    │  │
│  │ ← 完全不变     │  │← 完全不变     │  │ ← 全新模块         │  │
│  └───────┬───────┘  └──────┬───────┘  └────────┬───────────┘  │
│          │                 │                   │              │
│          │                 │                   │ 成员类型:      │
│          │                 │          ┌────────┤              │
│          │                 │          │        │              │
│          ▼                 ▼          ▼        ▼              │
│  ┌─────────────┐  ┌────────────┐  ┌──────┐  ┌───────┐        │
│  │bi_workflow  │  │askexcel_wf │  │Agent │  │Sub-   │        │
│  │.run()       │  │.run()      │  │LLM   │  │Team   │        │
│  │(SQL→执行→   │  │(代码→执行→ │  │调用   │  │递归   │        │
│  │ 报告→图表)  │  │ 报告→图表) │  │      │  │协调   │        │
│  └─────────────┘  └────────────┘  └──────┘  └───────┘        │
│                                                               │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │                    共享基础设施                           │ │
│  │  - agent_manager (智能体加载 + 技能注入)                  │ │
│  │  - progress_service (SSE 推送)                           │ │
│  │  - session_service (会话存储)                             │ │
│  │  - skill_registry (技能管理)                              │ │
│  └──────────────────────────────────────────────────────────┘ │
└───────────────────────────────────────────────────────────────┘
```

**关键原则:**
- 默认问数流程（bi_workflow / askexcel_workflow）**零改动**
- 团队系统可以**调用**现有工作流（作为 `workflow` 类型成员），但不修改工作流代码
- 团队系统可以**复用**现有智能体（作为 `agent` 类型成员），通过 agent_manager 加载 prompt
- 智能体、技能、SSE 均为共享基础设施

---

## 十一、实施步骤

### Phase 1: 自定义智能体
- 创建 `agents_custom/` 目录
- 扩展 `agent_manager.py`: 支持自建智能体的 `.py` 文件自动生成
- 扩展 `AgentManager.jsx`: 新增"新建智能体"表单
- DB migration: `askbi_agents` 表增加 `agent_type`, `file_path`, `role_description`, `capabilities`

### Phase 2: 团队数据层
- DB table: `askbi_teams` + `askbi_team_members`
- 后端 `team_engine/` 模块: coordinator + delegation + context + team_loader + custom_flow + task_board
- `/teams` CRUD API

### Phase 3: 团队协调器实现
- `TeamCoordinator` 核心决策循环（4 种模式）
- `delegation.py` 按成员类型分发执行（agent / workflow / sub_team / custom_flow）
- 嵌套团队支持（递归 TeamCoordinator）
- SSE 事件推送（含嵌套深度标识）

### Phase 4: 可视化编辑器
- 安装 `reactflow`
- `TeamEditor.jsx`: 画布 + 成员面板 + 属性面板
- `TeamList.jsx`: 团队列表管理页
- 自定义 ReactFlow 节点（按 member_type 区分样式）
- 子团队的分组节点（Group Node）

### Phase 5: 对话集成
- 新建对话增加团队选择
- `POST /team/{id}/run` + SSE 端点
- ThinkingPipeline 扩展团队事件类型（含嵌套层级展示）

---

## 十二、安全约束

1. **智能体文件生成**: 仅允许生成 `.py` 到 `agents_custom/`，禁止路径遍历
2. **LLM 调用限制**: 协调模式最大迭代 10 次，任务模式最大 20 个任务
3. **团队规模限制**: 单团队最多 10 个成员
4. **嵌套深度限制**: 子团队最多嵌套 3 层（`MAX_NESTING_DEPTH = 3`）
5. **工作流调用**: 团队中的工作流成员调用的是原始 workflow.run()，不做任何包装或修改
