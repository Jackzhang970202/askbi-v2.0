from agno.agent import Agent
from core import get_model

INSTRUCTIONS = """
你是 BI 数据分析报告专家。

你会收到：
1. 用户问题
2. 真实 SQL
3. 真实执行结果

请输出中文报告：
1. 先直接回答问题。
2. 只基于真实结果，不要编造数据。
3. 如果结果是列表，先总结，再提炼重点。
4. 不要输出 SQL、代码、日志。
5. 输出只需要报告正文。
"""

bi_report_agent = Agent(
    name="bi_report_agent",
    instructions=INSTRUCTIONS,
    model=get_model(),
)
