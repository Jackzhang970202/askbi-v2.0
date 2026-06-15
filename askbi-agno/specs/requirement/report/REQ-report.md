# 报表生成模块 - 需求文档

**版本**: v1.0
**模块**: 报表生成 (report)

---

## REQ-report-生成报表

**版本**: v1.0.0 | **状态**: 已完成 | **优先级**: P0

### 需求描述
用户上传明细表和汇总表，系统根据配置的规则生成考勤报表 (人事考勤/部门维度/多月个人/多月部门)。

### 前置条件
- 用户已登录
- 存在启用的报表规则配置

### 输入
- detail_file (明细表 Excel)
- summary_file (汇总表 Excel)
- report_type (报表类型)
- rule (规则，可选，覆盖配置中的规则)
- report_name (报表名称)

### 输出
- report_id
- 报表文件路径
- 统计信息 (行数、列数、标黄数、问题数)
- 预览数据

### 处理规则
1. 根据 report_name 查找启用的报表规则配置
2. 保存上传的明细表与汇总表到 report_files/user_{id}/{report_id}/sources/
3. 根据 report_type 调用对应的报表生成器:
   - 人事考勤报表 → ReportGenerator.generate_hr_attendance_report
   - 部门维度考勤报表 → DeptReportGenerator.generate_dept_report
   - 多月个人维度报表 → MultiMonthReportGenerator.generate_multi_month_report_from_raw
   - 多月部门维度报表 → MultiMonthDeptReportGenerator.generate_multi_month_dept_report_from_raw
4. 生成结果保存到报表目录
5. 记录报表元数据到数据库 (含文件信息、统计信息)
6. 返回 report_id 与报表信息

### 验收标准
- [ ] 四种报表类型均能正确生成
- [ ] 统计信息准确 (行数、列数、标黄、问题数)
- [ ] 报表文件保存到用户目录
- [ ] 报表记录正确存入数据库
- [ ] 规则配置可被用户提供的 rule 覆盖

---

## REQ-report-报表管理

**版本**: v1.0.0 | **状态**: 已完成 | **优先级**: P0

### 需求描述
支持报表的列表查看、预览、下载、删除与重命名。

### 前置条件
- 用户已登录

### 输入
- 列表: 无
- 预览: report_id
- 下载: report_id, desensitized (可选)
- 删除: report_id
- 重命名: report_id, display_file_name
- 全量数据: report_id

### 输出
- 列表: 报表列表
- 预览: 前10行数据 + 列信息
- 下载: Excel 文件流
- 删除: 成功/失败
- 重命名: 成功/失败
- 全量数据: 完整数据

### 处理规则
1. 列表仅返回当前用户的报表 (admin 可查看全部)
2. 预览默认读取脱敏文件 (如果已脱敏)，否则读取原始文件
3. 下载优先返回脱敏版本 (如果 desensitized=true)
4. 下载文件名优先使用 display_file_name
5. 删除时同时删除文件目录与数据库记录
6. 重命名仅更新 display_file_name 字段
7. 全量数据返回所有行 (不限制)

### 验收标准
- [ ] 列表正确过滤用户数据
- [ ] 预览数据格式正确 (NaN 处理)
- [ ] 下载文件可正常打开
- [ ] 删除后文件与记录已清理
- [ ] 重命名后下载文件名正确

---

## REQ-report-数据脱敏

**版本**: v1.0.0 | **状态**: 已完成 | **优先级**: P1

### 需求描述
报表支持列级数据脱敏，保护敏感信息。

### 前置条件
- 报表已生成
- 用户已登录

### 输入
- report_id
- enable (true=开启脱敏, false=关闭)
- column_config (脱敏列配置，可选)

### 输出
- 脱敏状态
- 预览数据
- 列配置

### 处理规则
1. 开启脱敏时:
   - 读取原始 Excel 文件
   - 如无 column_config，自动检测需要脱敏的列
   - 对指定列应用脱敏方法 (隐藏、部分隐藏、哈希等)
   - 保存脱敏文件 (文件名包含"脱敏"标识)
   - 更新数据库记录
2. 关闭脱敏时:
   - 删除所有脱敏文件
   - 更新数据库记录
3. 脱敏方法列表可通过 /report/desensitize/methods 获取
4. 脱敏列预览可通过 /report/desensitize/preview 获取建议配置

### 验收标准
- [ ] 脱敏文件正确生成
- [ ] 脱敏方法应用于指定列
- [ ] 关闭脱敏后原始文件不受影响
- [ ] 自动检测敏感列功能正常
- [ ] 预览数据正确展示脱敏效果

---

## REQ-report-报表问数

**版本**: v1.0.0 | **状态**: 已完成 | **优先级**: P1

### 需求描述
用户可对已生成的报表进行自然语言提问，系统基于报表数据回答。

### 前置条件
- 报表已生成
- 用户已登录

### 输入
- report_id
- question (自然语言问题)
- memory_count (上下文轮数，可选)

### 输出
- 分析结果 (复用 Excel 问数的回答格式)

### 处理规则
1. 根据 report_id 查找报表目录
2. 使用非脱敏版本的报表文件
3. 创建 Excel 问数会话，复制报表文件到会话目录
4. 创建数据源 (user_{id}:报表数据_{report_id后8位})
5. 调用 Excel 问数接口回答问题
6. 保存报表问数会话的元数据关联

### 验收标准
- [ ] 报表文件正确复制到问数会话
- [ ] 自然语言问题得到正确回答
- [ ] 会话关联到原始报表

---

## REQ-report-报表配置

**版本**: v1.0.0 | **状态**: 已完成 | **优先级**: P1

### 需求描述
管理员可配置报表规则，包括规则内容、表头定义、作用范围等。

### 前置条件
- 用户已登录

### 输入
- category: report_rule
- name: 报表名称
- content: { rule, headers }
- is_enabled: 是否启用
- scope_type / scope_datasources: 作用范围

### 输出
- 保存成功/失败

### 处理规则
1. 报表规则存储在 askbi_global_configs 表
2. content 包含 rule (规则字符串) 与 headers (表头列表)
3. 生成报表时查找匹配的启用规则
4. 支持范围控制 (universal / 特定数据源)
5. 用户级隔离 (同一规则名不同用户可不同配置)

### 验收标准
- [ ] 规则配置正确保存
- [ ] 生成报表时正确加载规则
- [ ] 作用范围正确生效
- [ ] 用户级隔离正常工作

---

## REQ-report-ReportRunner报表

**版本**: v1.0.0 | **状态**: 已完成 | **优先级**: P1

### 需求描述
通过 ReportRunner 与全局配置生成报表，使用 chat_id 关联已有会话。

### 前置条件
- 用户已登录
- 会话已存在
- 存在启用的报表规则配置

### 输入
- chat_id
- report_name
- rule (可选)

### 输出
- 报表文件路径
- 报表元数据

### 处理规则
1. 验证 chat_id 对应会话存在
2. 查找启用的报表规则配置
3. 使用 ReportRunner (core/report_runner.py) 生成报表
4. 支持进度推送 (progress_service.append_text)
5. 保存报表元数据到 askbi_general_metadata
6. 返回文件名与路径

### 验收标准
- [ ] 会话验证正确
- [ ] ReportRunner 生成报表
- [ ] 进度推送正常
- [ ] 元数据保存正确

---

## REQ-report-报表会话管理

**版本**: v1.0.0 | **状态**: 已完成 | **优先级**: P1

### 需求描述
支持报表会话级别的报表列表与下载 (基于 chat_id)。

### 前置条件
- 用户已登录
- 会话已存在

### 输入
- 列表: chat_id
- 下载: chat_id, filename

### 输出
- 列表: 该会话下的报表列表
- 下载: Excel 文件流

### 处理规则
1. /reports/list/{chat_id} 查询该会话下的所有报表元数据
2. /reports/download/{chat_id}/{filename} 下载指定报表文件
3. 文件路径: report_files/user_{user_id}/{chat_id}/{filename}
4. 支持 token 参数用于下载链接分享

### 验收标准
- [ ] 报表列表按会话过滤
- [ ] 文件下载正常
- [ ] token 下载链接有效

---

## REQ-report-AI改表

**版本**: v1.0.0 | **状态**: 未开始 | **优先级**: P2

### 需求描述
通过 AI 辅助编辑报表数据 (当前返回 501 占位)。

### 前置条件
- 路由已注册: POST /report/ai-edit

### 输入
- 报表数据修改请求

### 输出
- 当前返回 501 (暂未实现)

### 处理规则
1. 路由存在，返回 {"success": false, "error": "AI 改表暂未恢复"}
2. 后续实现时复用 Excel 问数流程

### 验收标准
- [ ] 路由返回 501 与提示信息
