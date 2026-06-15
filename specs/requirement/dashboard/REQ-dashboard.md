# 数据大屏模块 - 需求文档

**版本**: v1.0
**模块**: 数据大屏 (dashboard)

---

## REQ-dashboard-生成大屏

**版本**: v1.0.0 | **状态**: 已完成 | **优先级**: P0

### 需求描述
用户上传个人维度与部门维度 Excel 文件，系统生成基于 ECharts 的数据可视化大屏。

### 前置条件
- 用户已登录

### 输入
- personal_file (个人维度 Excel)
- dept_file (部门维度 Excel)
- month (月份，可选)

### 输出
- dashboard_id
- 统计信息 (行数、月份)
- 展示文件名

### 处理规则
1. 保存上传文件到 dashboard_files/user_{id}/{dashboard_id}/sources/
2. 解析个人维度与部门维度数据
3. 从文件名提取月份 (如未手动指定)
4. 生成 data.js 数据文件到 dashboard 目录
5. 使用模板 (style4_business_cyan) 生成大屏 HTML
6. 将 CSS、JS、数据内联到 HTML 形成独立文件
7. 记录大屏元数据到数据库 (report_type=dashboard)

### 验收标准
- [ ] 大屏 HTML 文件正确生成
- [ ] 数据正确解析与写入 data.js
- [ ] 月份正确提取与展示
- [ ] 大屏元数据正确记录到数据库
- [ ] 生成的 HTML 可在浏览器中正常打开

---

## REQ-dashboard-大屏管理

**版本**: v1.0.0 | **状态**: 已完成 | **优先级**: P0

### 需求描述
支持大屏的列表查看、静态资源服务、截图与删除。

### 前置条件
- 用户已登录

### 输入
- 列表: 无
- 静态资源: dashboard_id, path
- 截图: dashboard_id, title (可选)
- 删除: dashboard_id

### 输出
- 列表: 大屏列表 (report_type=dashboard)
- 静态资源: 对应文件 (HTML/CSS/JS/图片)
- 截图: PNG 图片
- 删除: 成功/失败

### 处理规则
1. 列表仅返回当前用户的大屏
2. 静态资源服务限制在大屏目录内，防止路径穿越
3. 使用 mimetypes 自动识别 Content-Type
4. 截图使用 Playwright (Chromium) 渲染并截取
5. 截图时可自定义标题文字
6. 删除时同时清理目录与数据库记录

### 验收标准
- [ ] 列表正确过滤用户数据
- [ ] 静态资源正确返回 (含正确的 Content-Type)
- [ ] 路径穿越攻击被阻止
- [ ] 截图功能正常生成 PNG
- [ ] 删除后文件与记录已清理

---

## REQ-dashboard-截图功能

**版本**: v1.0.0 | **状态**: 已完成 | **优先级**: P1

### 需求描述
通过 Playwright 对大屏进行高质量截图，支持自定义标题。

### 前置条件
- 大屏已生成
- Playwright 与 Chromium 已安装

### 输入
- dashboard_id
- title (可选)

### 输出
- PNG 图片流 (2560x1440)

### 处理规则
1. 查找大屏 HTML 文件
2. 使用 Playwright 启动 Chromium
3. 以 2560x1440 视口打开 HTML 文件
4. 等待页面加载完成 (networkidle + 2秒)
5. 替换标题文字 (如果提供了 title)
6. 截取全屏截图
7. 返回 PNG 数据流

### 验收标准
- [ ] 截图分辨率正确 (2560x1440)
- [ ] 图表渲染完整
- [ ] 标题文字正确替换
- [ ] 截图为有效 PNG 格式
