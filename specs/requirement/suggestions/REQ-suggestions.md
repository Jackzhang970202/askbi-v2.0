# 建议问题模块 - 需求文档

**版本**: v1.0
**模块**: 建议问题 (suggestions)

---

## REQ-suggestions-智能建议

**版本**: v1.0.0 | **状态**: 已完成 | **优先级**: P2

### 需求描述
根据 Excel 文件的列信息与样例数据，LLM 自动生成建议问题列表，辅助用户快速上手分析。

### 前置条件
- 用户已上传 Excel 文件或已选择数据源

### 输入
- chat_id
- file_name
- sheet_name
- columns (列名列表)
- sample_data (样例数据，可选)
- qa_history (历史问答，可选)

### 输出
- 建议问题列表 (字符串数组)
- fallback 标识 (如果使用默认问题)

### 处理规则
1. 通过 SuggestionGenerator (core/suggestion_generator.py) 生成
2. 优先使用 LLM 根据列名与样例数据生成问题
3. 如果 LLM 调用失败，使用基于列名的规则生成默认问题
4. 默认问题示例: "这张表有多少行数据？", "可以先做一个数据概览吗？"
5. 建议问题数量控制在 4-6 条

### 验收标准
- [ ] LLM 成功时生成相关建议问题
- [ ] LLM 失败时使用 fallback 默认问题
- [ ] 建议问题与数据列相关
- [ ] 返回格式正确 (success, suggestions, fallback)
