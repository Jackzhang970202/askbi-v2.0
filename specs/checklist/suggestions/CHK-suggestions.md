# 检查清单

**版本**: v1.0
**模块**: 建议问题 (suggestions)
**关联需求**: REQ-suggestions

---

## 检查项列表

| 编号 | 检查项 | 关联需求 | 等级 | 状态 |
|------|--------|----------|------|------|
| CHK-suggestions-LLM-001 | LLM 建议生成 | REQ-suggestions-智能建议 | 重要 | 已完成 |
| CHK-suggestions-fallback-002 | Fallback 默认问题 | REQ-suggestions-智能建议 | 重要 | 已完成 |

---

## 检查项详情

### CHK-suggestions-LLM-001 LLM 建议生成

**关联需求**: REQ-suggestions-智能建议
**目的**: 验证 LLM 根据列信息生成建议问题
**方法**: API 测试
**等级**: 重要

**检查步骤**:
1. 提供列名与样例数据
2. 调用 POST /suggestions
3. 验证返回 success=true, fallback=false
4. 验证 suggestions 包含 4-6 条与数据相关的问题

**预期结果**:
- LLM 成功生成建议
- 问题与列信息相关

### CHK-suggestions-fallback-002 Fallback 默认问题

**关联需求**: REQ-suggestions-智能建议
**目的**: 验证 LLM 失败时的 fallback 机制
**方法**: 模拟失败测试
**等级**: 重要

**检查步骤**:
1. 配置无效模型或模拟 LLM 失败
2. 调用 POST /suggestions
3. 验证返回 success=true, fallback=true
4. 验证 suggestions 包含默认问题

**预期结果**:
- Fallback 返回 4 条默认问题
- fallback 标识为 true

---

## 交付检查

| 编号 | 检查项 | 等级 | 状态 |
|------|--------|------|------|
| CHK-DELIVER-001 | 代码已提交 | 阻塞 | 未开始 |
| CHK-DELIVER-002 | 代码审查通过 | 阻塞 | 未开始 |

---

**文档结束**
