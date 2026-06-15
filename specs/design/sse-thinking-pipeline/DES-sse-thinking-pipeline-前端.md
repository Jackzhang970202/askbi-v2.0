# 前端设计文档

**版本**: v1.0
**模块**: SSE 思考流水线 (sse-thinking-pipeline)
**关联需求**: REQ-sse-thinking-pipeline

---

## 页面清单

| 页面 | 路由 | 类型 | 关联需求 |
|------|------|------|----------|
| 聊天界面（Pipeline 集成） | `#/chat` | 内嵌组件 | REQ-sse-thinking-pipeline-Pipeline展示 |

---

## 页面设计

### 聊天界面 - Pipeline 集成

#### 页面结构
- **聊天消息列表**: 每条用户问题对应的 AI 回复消息中嵌入 ThinkingPipeline 组件
- **实时消息**: 当前正在处理的问答，显示运行中的流水线
- **历史消息**: 已完成的问答，显示完成的流水线回放

#### 交互流程
1. 用户发送问题 → 后端开始工作流 → 前端建立 SSE 连接
2. SSE 事件到达 → 流水线逐阶段渲染（pending → running → completed）
3. 运行中阶段显示脉冲动画，自动滚动到可见区域
4. 完成阶段显示耗时和勾选标记
5. 所有阶段完成或出错 → 流水线停止动画，显示最终状态
6. 历史消息加载 → 从 thoughts 字段解析阶段事件，渲染完成状态流水线

#### 组件

**useProgressStream Hook** (新增)
- 封装 SSE 连接逻辑，返回阶段事件状态
- 使用 fetch + ReadableStream（非 EventSource）以支持 Bearer Token
- 管理连接生命周期（建立、接收、断开、重连）
- 导出：`stages`（阶段数组）、`isStreaming`（是否正在流式传输）、`error`（错误信息）

```javascript
// useProgressStream.js 接口
export function useProgressStream(chatid, type = 'bi') {
  const [stages, setStages] = useState([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState(null);
  
  useEffect(() => {
    const controller = new AbortController();
    const token = getAuthToken();
    const url = type === 'bi' 
      ? `/progress/stream?chatid=${chatid}`
      : `/excel/progress/stream?chatid=${chatid}`;
    
    fetch(url, {
      headers: { 'Authorization': `Bearer ${token}` },
      signal: controller.signal
    }).then(async response => {
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      setIsStreaming(true);
      
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        
        const text = decoder.decode(value);
        const lines = text.split('\n').filter(l => l.startsWith('data: '));
        
        for (const line of lines) {
          const event = JSON.parse(line.slice(6));
          if (event.stage === '__done__' || event.stage === '__error__') {
            setIsStreaming(false);
            break;
          }
          setStages(prev => updateStage(prev, event));
        }
      }
    }).catch(err => {
      if (err.name !== 'AbortError') setError(err.message);
    });
    
    return () => controller.abort();
  }, [chatid, type]);
  
  return { stages, isStreaming, error };
}
```

**ThinkingPipeline 组件** (新增)
- 替代现有 ThinkingProcess.jsx 的终端风格
- 浅色卡片设计 + 垂直时间线布局
- 阶段定义配置：

```javascript
const BI_STAGES = [
  { key: 'understanding', label: '意图理解', icon: '💭' },
  { key: 'knowledge_retrieval', label: '知识检索', icon: '🔍' },
  { key: 'sql_generation', label: 'SQL 生成', icon: '📝' },
  { key: 'execution_validation', label: '执行验证', icon: '▶️' },
  { key: 'chart_generation', label: '图表生成', icon: '📊' },
  { key: 'report_generation', label: '报告生成', icon: '📄' },
  { key: 'summary', label: '总结输出', icon: '✨' }
];

const EXCEL_STAGES = [
  { key: 'understanding', label: '意图理解', icon: '💭' },
  { key: 'code_generation', label: '代码生成', icon: '💻' },
  { key: 'execution_validation', label: '执行验证', icon: '▶️' },
  { key: 'chart_generation', label: '图表生成', icon: '📊' },
  { key: 'report_generation', label: '报告生成', icon: '📄' }
];
```

- 组件 Props：
  - `stages`: 阶段事件数组（来自 useProgressStream）
  - `type`: 'bi' 或 'excel'
  - `isStreaming`: 是否正在流式传输
  - `thoughts`: 历史消息的 thoughts 数据（可选，用于回放）

- 视觉设计：
  - **卡片样式**: 白色背景、圆角、轻微阴影
  - **时间线**: 左侧垂直灰色线条连接各阶段
  - **阶段图标**: 圆形背景，运行中时脉冲动画
  - **状态指示**: 
    - pending: 灰色空心圆
    - running: 蓝色脉冲圆 + 旋转加载图标
    - completed: 绿色勾选圆 + 耗时文本
    - error: 红色感叹号圆 + 红色边框卡片
  - **详情展开**: 点击卡片展开，显示 message 和 metadata
  - **SQL 高亮**: metadata.sql 存在时使用 highlight.js 渲染
  - **动画**: CSS transition + keyframes，新阶段淡入 + 滑入

**MessageItem 集成**
- 在 MessageItem.jsx 中根据消息状态决定是否渲染 ThinkingPipeline
- 实时消息：使用 useProgressStream hook
- 历史消息：从 message.thoughts 解析阶段数据

```jsx
// MessageItem.jsx 关键逻辑
function MessageItem({ message, isLatest }) {
  const { stages, isStreaming } = useProgressStream(
    isLatest ? message.chatid : null,
    message.type || 'bi'
  );
  
  const displayStages = isLatest && isStreaming 
    ? stages 
    : parseThoughts(message.thoughts);
  
  return (
    <div className="message-item">
      {message.role === 'assistant' && displayStages.length > 0 && (
        <ThinkingPipeline 
          stages={displayStages}
          type={message.type || 'bi'}
          isStreaming={isLatest && isStreaming}
        />
      )}
      <div className="message-content">{message.content}</div>
    </div>
  );
}
```

**StreamingManager 协调**
- 管理多个并发 SSE 连接（如果支持多问题并发）
- 提供全局 SSE 连接状态
- 在 App.jsx 生命周期中管理连接建立和清理

**App.jsx 生命周期**
- 组件挂载时初始化 StreamingManager
- 组件卸载时清理所有 SSE 连接
- 路由切换时保持连接（避免中断正在进行的问答）

#### 接口
- `GET /progress/stream?chatid=X` — BI 问数 SSE 流
- `GET /excel/progress/stream?chatid=X` — Excel 分析 SSE 流
- `Authorization: Bearer <token>` — 请求头认证

#### 错误处理
- SSE 连接失败: 显示重试按钮，3 秒后自动重连（最多 3 次）
- 网络断开: 显示"网络连接中断"提示
- 后端错误事件: 显示错误信息和错误详情
- Token 过期: 重定向到登录页

#### 动画效果
- **脉冲动画**: 运行中阶段图标的 scale 和 opacity 循环
- **淡入动画**: 新阶段卡片的 opacity 从 0 到 1
- **滑入动画**: 新阶段卡片的 translateY 从 -10px 到 0
- **进度条**: 可选，显示整体进度百分比
- **平滑滚动**: 新阶段出现时自动滚动到可见区域

#### SQL 高亮集成
- 使用 highlight.js 的 SQL 语言包（轻量级）
- 支持 PostgreSQL 和 MySQL 语法
- 代码块样式：深色背景（与浅色卡片对比）、等宽字体
- 横向滚动：长 SQL 不换行
- 可选复制按钮：点击复制 SQL 到剪贴板
