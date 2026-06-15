import React, { useMemo } from 'react';

const STAGE_META = {
    starting: { title: '准备分析', icon: '◌', brief: '正在启动问数引擎' },
    understanding: { title: '查询数据', icon: '▦', brief: '正在理解问题和数据结构' },
    sql_generation: { title: '查询数据', icon: '▦', brief: '正在生成查询方案' },
    sql_execution: { title: '查询数据', icon: '▦', brief: '正在执行数据查询' },
    code_generation: { title: '执行分析', icon: '<>', brief: '正在生成分析步骤' },
    code_execution: { title: '执行分析', icon: '<>', brief: '正在运行数据分析' },
    report_generation: { title: '生成回答', icon: '◈', brief: '正在生成分析报告' },
    chart_generation: { title: '创建数据制品', icon: '▦', brief: '正在生成可视化结果' },
    unknown: { title: '执行分析', icon: '◌', brief: '正在处理' },
};

const STATUS_LABEL = {
    running: '进行中',
    done: '已完成',
    error: '异常',
};

const toText = (value = '') => {
    if (value === null || value === undefined) return '';
    if (typeof value === 'string') return value.trim();
    try {
        return JSON.stringify(value, null, 2);
    } catch {
        return String(value);
    }
};

const compactText = (value = '') => {
    const text = toText(value).replace(/\s+/g, ' ').trim();
    return text.length > 110 ? `${text.slice(0, 110)}...` : text;
};

const normalizeStage = (item, index) => {
    const raw = item?.message || item || {};
    const stage = raw.stage || item?.event || 'unknown';
    const status = raw.status || 'running';
    const meta = STAGE_META[stage] || STAGE_META.unknown;
    const message = raw.message || item?.data || raw.text || '';
    const detailPayload = raw.detail || raw.input || raw.output || raw.execution || raw.validation || item?.data || '';
    const brief = compactText(message) || compactText(detailPayload) || meta.brief;
    const detail = toText(detailPayload || message);
    return {
        id: `${stage}_${status}_${index}`,
        stage,
        status,
        title: meta.title,
        icon: meta.icon,
        brief,
        detail,
        time: item?.time || '',
    };
};

const ThinkingPipeline = ({ stages = [], isDone = false, sseError = null, isThinking = false }) => {
    const visibleSteps = useMemo(() => {
        if (!stages.length && (isThinking || !isDone)) {
            return [{
                id: 'starting',
                stage: 'starting',
                status: 'running',
                title: '准备分析',
                icon: '◌',
                brief: '正在连接问数引擎，请稍候...',
                detail: '等待后端返回第一条处理进度',
                time: '',
            }];
        }
        return stages.map(normalizeStage).slice(-3);
    }, [stages, isThinking, isDone]);

    if (!visibleSteps.length && !sseError) return null;

    return (
        <div className="mb-4 w-full space-y-3 text-sm text-slate-500">
            {visibleSteps.map((step) => {
                const isRunning = step.status === 'running';
                const isError = step.status === 'error';
                return (
                    <details key={step.id} className="group rounded-xl transition-colors open:bg-slate-50/70">
                        <summary className="flex cursor-pointer list-none items-center gap-2 rounded-xl px-1 py-1 text-slate-500 outline-none transition-colors hover:bg-slate-50/80 [&::-webkit-details-marker]:hidden">
                            <span className={`w-5 shrink-0 text-center font-mono text-base ${isError ? 'text-red-400' : isRunning ? 'text-slate-400' : 'text-slate-300'}`}>
                                {step.icon}
                            </span>
                            <span className="shrink-0 text-[15px] font-medium text-slate-600">{step.title}</span>
                            <span className="min-w-0 flex-1 truncate text-[13px] text-slate-400">{step.brief}</span>
                            <span className="text-[11px] text-slate-300 transition-transform group-open:rotate-90">›</span>
                        </summary>
                        <div className="ml-7 mt-2 rounded-xl bg-white/80 px-4 py-3 text-xs leading-6 text-slate-500 shadow-sm ring-1 ring-slate-100">
                            <div>阶段：{step.title}</div>
                            <div>状态：{STATUS_LABEL[step.status] || STATUS_LABEL.running}</div>
                            {step.detail && (
                                <div>
                                    <div>详情：</div>
                                    <pre className="mt-2 max-h-80 overflow-auto whitespace-pre-wrap rounded-lg bg-slate-50 p-3 font-mono text-[11px] leading-5 text-slate-700 ring-1 ring-slate-100">
                                        {step.detail}
                                    </pre>
                                </div>
                            )}
                            {step.time && <div>时间：{step.time}</div>}
                        </div>
                    </details>
                );
            })}

            {sseError && (
                <div className="rounded-xl bg-red-50 px-4 py-3 text-xs text-red-500 ring-1 ring-red-100">
                    中间过程连接异常：{sseError}
                </div>
            )}

            {!isDone && (
                <div className="flex items-center gap-2 px-1 text-[15px] text-slate-600">
                    <span className="h-4 w-4 animate-spin rounded-full border-2 border-slate-300 border-t-transparent"></span>
                    <span>分析中...</span>
                </div>
            )}
        </div>
    );
};

export default ThinkingPipeline;
