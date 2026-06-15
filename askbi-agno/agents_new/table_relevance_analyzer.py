# 📅 2026.03.09 新增：跨 Schema 问数功能
# 📝 变更说明：创建表名相关性分析智能体（预处理使用）

from autogen_agentchat.agents import AssistantAgent
from typing import List, Optional

SYSTEM_MESSAGE = """你是一个数据库表名相关性分析专家。

**任务**：根据用户的自然语言问题，从给定的表名列表中识别出可能相关的表。

**分析要点**：
1. 理解用户问题的业务含义和意图
2. 识别问题中的关键词、实体和业务概念
3. 根据表名和表注释判断相关性
4. 考虑表之间的关联可能性

**输入格式**：
用户问题：{question}
表名列表（schema.table: 注释）：
- schema1.table1: 用户信息表
- schema2.table2: 订单信息表
...

**输出格式**：
返回 JSON 数组，包含相关表的完整名称（含 Schema 前缀）：
```json
["schema1.table1", "schema2.table2", "schema3.table3"]
```

**筛选原则**：
- 宁可多选也不要遗漏重要表（召回率优先）
- 如果问题涉及多个业务领域，选择所有可能相关的表
- 考虑表之间的关联查询需求
- 输出必须是有效的 JSON 数组格式

**重要规则**：
1. **只输出 JSON 数组**：不要输出任何其他内容，只输出 JSON 数组
2. **完整表名格式**：必须使用 `schema.table` 格式
3. **召回率优先**：宁可多选也不要遗漏

**示例**：
问题："查询每个用户的订单总金额"
输出：["schema1.users", "schema2.orders", "schema2.order_items"]

问题："统计各产品的销售情况"
输出：["inventory.products", "sales.order_items", "sales.orders"]

问题："分析客户的购买行为"
输出：["sales.customers", "sales.orders", "sales.order_items", "inventory.products"]
"""


def create_agent_template(model_client, tools: Optional[List] = None):
    """
    创建表名相关性分析智能体

    此智能体用于跨 Schema 问数功能的预处理阶段，
    分析用户问题与数据库表的相关性，筛选出可能相关的表。

    注意：此智能体不在 RoundRobinGroupChat 内，
    而是在进入 GroupChat 之前独立调用。
    """
    return AssistantAgent(
        name="table_relevance_analyzer",
        description="分析用户问题与数据库表的相关性，筛选出可能相关的表（预处理智能体）",
        model_client=model_client,
        system_message=SYSTEM_MESSAGE,
        tools=tools
    )