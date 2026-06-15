from autogen_agentchat.agents import AssistantAgent
from core.global_knowledge import get_global_knowledge

# 获取全局知识
global_knowledge = get_global_knowledge()

def create_agent_template(model_client, tools=None):
    """
    创建问题改写智能体模板
    """
    system_message = f"""你是一个问题改写助手。你的任务是改写用户的问题，使其更适合数据分析和SQL查询生成。

# 全局知识规则
{global_knowledge}

**改写指南:**
1. 保持问题的核心意图不变
2. 使用更明确、更具体的词汇
3. 突出问题中的关键实体和属性
4. 去除冗余的修饰词
5. 确保改写后的问题简洁明了
6. 直接返回改写后的问题，不要添加任何其他说明或解释
"""
    
    return AssistantAgent(
        name="question_rewriter",
        model_client=model_client,
        system_message=system_message
    )
