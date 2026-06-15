# 任务清单

**版本**: v1.0
**模块**: 建议问题 (suggestions)
**关联需求**: REQ-suggestions

---

## 任务列表

| 编号 | 任务 | 关联需求 | 优先级 | 状态 |
|------|------|----------|--------|------|
| TASK-suggestions-生成器-001 | [后端] 实现 SuggestionGenerator | REQ-suggestions-智能建议 | P2 | 已完成 |
| TASK-suggestions-API-002 | [后端] 实现建议生成 API | REQ-suggestions-智能建议 | P2 | 已完成 |
| TASK-suggestions-fallback-003 | [后端] 实现 fallback 默认问题 | REQ-suggestions-智能建议 | P2 | 已完成 |

---

## 任务详情

### TASK-suggestions-生成器-001 SuggestionGenerator

**关联需求**: REQ-suggestions-智能建议
**描述**: 实现 SuggestionGenerator 类，LLM 生成建议问题
**技术要点**: LLM 调用, prompt 工程
**优先级**: P2 | **状态**: 未开始

**涉及文件**:
- `core/suggestion_generator.py`

**验收标准**:
- [ ] LLM 根据列名与样例数据生成问题
- [ ] 异常时正确触发 fallback

---

### TASK-suggestions-API-002 建议生成 API

**关联需求**: REQ-suggestions-智能建议
**描述**: 实现 POST /suggestions 路由
**技术要点**: FastAPI, 参数校验, 异常处理
**优先级**: P2 | **状态**: 未开始

**涉及文件**:
- `backend/legacy_routes.py`

**验收标准**:
- [ ] 请求参数校验正确
- [ ] LLM 成功返回 suggestions
- [ ] LLM 失败返回 fallback 问题
- [ ] fallback 标识正确

---

### TASK-suggestions-fallback-003 Fallback 默认问题

**关联需求**: REQ-suggestions-智能建议
**描述**: 实现 _fallback_questions 函数，基于列名生成默认问题
**技术要点**: 规则匹配
**优先级**: P2 | **状态**: 未开始

**涉及文件**:
- `core/suggestion_generator.py`

**验收标准**:
- [ ] 返回 4 条默认问题
- [ ] 问题与列名无关 (通用问题)
