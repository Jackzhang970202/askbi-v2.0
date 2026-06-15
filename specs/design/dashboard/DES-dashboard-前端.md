# 前端设计文档

**版本**: v1.0
**模块**: 数据大屏 (dashboard)
**关联需求**: REQ-dashboard

---

## 页面清单

| 页面 | 路由 | 类型 | 关联需求 |
|------|------|------|----------|
| 大屏列表 | 主页面 | 列表 | REQ-dashboard-大屏管理 |
| 大屏生成 | 弹窗/页面 | 表单 + 文件上传 | REQ-dashboard-生成大屏 |
| 大屏预览 | iframe / 新窗口 | 嵌入式预览 | REQ-dashboard-大屏管理 |

---

## 大屏列表页设计

### 页面结构
操作按钮 (新建大屏) → 数据表格 (名称、月份、行数、创建时间、操作)

### 交互流程
1. 加载大屏列表 (GET /dashboard/list)
2. 点击"新建"打开大屏生成表单
3. 上传个人维度与部门维度 Excel
4. 选择月份 (可选)
5. 提交生成，等待结果
6. 列表刷新

### 行操作
- **预览**: 在新窗口/iframe 中打开大屏 HTML
- **截图**: 触发截图下载
- **删除**: 确认删除

### 组件
- **Sidebar**: 侧边栏导航
- 大屏列表使用通用表格组件

### 接口
- POST /dashboard/generate — 生成大屏
- GET /dashboard/list — 大屏列表
- GET /dashboard/static/{dashboard_id}/{path} — 静态资源
- GET /dashboard/static/{dashboard_id}/screenshot — 截图
- DELETE /dashboard/{dashboard_id} — 删除

### 预览方式
- 大屏 HTML 通过 /dashboard/static/{dashboard_id}/{html_filename} 访问
- 前端使用 iframe 嵌入或新窗口打开
- 大屏为自包含 HTML，可独立运行
