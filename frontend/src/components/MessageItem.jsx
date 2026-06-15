import React, { useState, useEffect, useMemo } from 'react';
import { Icons } from './Icons';
import ThinkingProcess from './ThinkingProcess';
import ThinkingPipeline from './ThinkingPipeline';
import ChartCard from './ChartCard';
import VegaChart from './VegaChart';
import StreamingManager from '../utils/StreamingManager';

const shortChartTitle = (summaryHtml) => {
    if (!summaryHtml) return '数据图表';
    const plainText = String(summaryHtml).replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim();
    return plainText.slice(0, 32) || '数据图表';
};

const MessageItem = React.memo(({ msg, idx, activeTab, onUpdateMessage, currentChatId, showAlert, showConfirm }) => {
    const isUser = msg.role === 'user';
    const [isEditing, setIsEditing] = useState(false);
    const [editContent, setEditContent] = useState('');
    const [isCopied, setIsCopied] = useState(false);
    const [terminalOpen, setTerminalOpen] = useState(false);
    const [, forceUpdate] = useState({});

    // 报表生成消息的特殊处理
    const isReportGeneration = msg.isReportGeneration || false;

    // Use global StreamingManager to manage state
    const streamingState = useMemo(() => {
        if (!currentChatId) return null;
        return StreamingManager.getState(currentChatId, idx);
    }, [currentChatId, idx, msg._streamStage, msg._displayedSummary]);

    // 刷新后不要被旧的 _displayedSummary / _streamStage 影响（否则会出现"内容不全"和"光标常驻"）
    const shouldStream = !!msg._shouldStream;
    const streamStage = streamingState?.stage || (shouldStream ? (msg._streamStage || 'pending') : 'done');

    // 非流式状态下永远使用完整内容（忽略旧的 _displayedSummary）
    const displayedSummary = shouldStream
        ? (msg._displayedSummary !== undefined ? msg._displayedSummary : '')
        : (msg.structuredData?.summary || msg.content || '');

    const showChart = !shouldStream || streamStage === 'done';
    
    useEffect(() => {
        if (!isUser && msg._shouldStream && currentChatId) {
            StreamingManager.startStreaming(currentChatId, idx, msg, () => {
                forceUpdate({});
            });
        }
    }, [currentChatId, idx, msg._shouldStream, isUser, msg]);

    useEffect(() => {
        if (isEditing) {
            const initialText = msg.structuredData ? msg.structuredData.summary : msg.content;
            setEditContent(initialText || "");
        }
    }, [isEditing, msg]);

    const handleSave = () => {
        onUpdateMessage(idx, editContent);
        setIsEditing(false);
    };

    const handleCopy = () => {
        const text = msg.structuredData ? msg.structuredData.summary : msg.content;
        navigator.clipboard.writeText(text);
        setIsCopied(true);
        setTimeout(() => setIsCopied(false), 2000);
    };

    const handleDownload = () => {
        const text = msg.structuredData ? msg.structuredData.summary : msg.content;
        const blob = new Blob([text], { type: 'text/markdown;charset=utf-8' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `报告_${new Date().toISOString().slice(0, 10)}.md`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    };
    
    const parsedData = useMemo(() => {
        if (!isUser && msg.structuredData) {
            const { summary, sql, tables, chart, thoughts, code } = msg.structuredData;
            let cleanSummary = isEditing ? summary : (streamStage === 'done' || streamStage === 'typing' ? (isEditing ? summary : displayedSummary) : "");
            
            if (cleanSummary && !isEditing) {
                cleanSummary = cleanSummary.replace(/\/app\/user_upload_files\/[^\s\u4e00-\u9fa5]+\.(xlsx|xls|csv)/gi, "数据文件");
                cleanSummary = cleanSummary.replace(/user_upload_files\/[\w\u4e00-\u9fa5]+\.(xlsx|xls|csv)/gi, "数据文件");
                cleanSummary = cleanSummary.replace(/["']?[\w\u4e00-\u9fa5]+__Sheet\d+(_[\w\u4e00-\u9fa5]+)?["']?/g, (match) => {
                     if (match.includes("列") || match.includes("层次") || match.includes("类型")) return "相关列";
                     return "数据表";
                });
            }

            // Assume marked is available via window or import
            const summaryHtml = window.marked ? window.marked.parse(cleanSummary || "") : cleanSummary; 
            
            let chartOptions = null;
            if (chart) {
                try {
                    // 检查 chart_needed 字段
                    let chartObj = chart;
                    if (typeof chart === 'string') {
                        let chartStr = chart.replace(/```json/g, '').replace(/```/g, '');
                        try { chartObj = JSON.parse(chartStr); } catch(e) { chartObj = eval(`(${chartStr})`); }
                    }
                    // 检查是否需要图表
                    if (chartObj && chartObj.chart_needed === false) {
                        console.log("[CHART] 图表不需要:", chartObj.reason);
                    } else if (chartObj && (chartObj.$schema || chartObj.mark)) {
                        // 有有效的 Vega-Lite 配置
                        chartOptions = chartObj;
                    } else if (chartObj && chartObj.chart_needed === true) {
                        console.log("[CHART] 需要图表但无数据:", chartObj.reason);
                    } else {
                        console.log("[CHART] 无效的图表配置:", chartObj);
                    }
                } catch (e) { console.error("Chart parsing failed", e); }
            }
            const hasAnalysisSection = typeof cleanSummary === 'string' && cleanSummary.includes('分析解读');
            const sseStages = msg.structuredData?.sseStages || [];
            const sseError = msg.structuredData?.sseError || null;
            return { summaryHtml, sql, tables, chartOptions, thoughts, code, hasAnalysisSection, sseStages, sseError };
        }
        return null;
    }, [msg.structuredData, isUser, displayedSummary, streamStage, isEditing]);

    const Avatar = () => (
        <div className={`w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0 shadow-sm border border-white ${isUser ? 'bg-gradient-to-br from-blue-500 to-indigo-600 text-white' : (activeTab === 'bi' ? 'bg-gradient-to-br from-indigo-50 to-blue-100 text-blue-600' : 'bg-gradient-to-br from-emerald-50 to-teal-100 text-emerald-600')}`}>
            {isUser ? <Icons.User /> : (activeTab === 'bi' ? <Icons.Bot /> : <Icons.Excel />)}
        </div>
    );

    if (!isUser) {
        return (
            <div className="flex items-start gap-4 w-full px-4 animate-fade-in group">
                <Avatar />
                <div className="flex-1 min-w-0">
                    <div className="bg-white p-6 rounded-2xl rounded-tl-sm shadow-[0_2px_15px_-3px_rgba(0,0,0,0.07),0_10px_20px_-2px_rgba(0,0,0,0.04)] border border-gray-100 relative overflow-hidden">
                        <div className={`absolute top-0 left-0 right-0 h-1 ${activeTab === 'bi' ? 'bg-gradient-to-r from-blue-400 to-indigo-500' : 'bg-gradient-to-r from-emerald-400 to-teal-500'}`}></div>
                        
                        {streamStage === 'done' && (
                            <div className="absolute top-4 right-4 flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity bg-white/80 backdrop-blur rounded-lg p-1 shadow-sm border border-gray-100 z-10">
                                <button onClick={handleCopy} className="p-1.5 text-gray-400 hover:text-blue-500 hover:bg-blue-50 rounded-md transition-colors" title="复制">
                                    {isCopied ? <Icons.Check className="text-green-500" /> : <Icons.Copy />}
                                </button>
                                <button onClick={() => setIsEditing(!isEditing)} className="p-1.5 text-gray-400 hover:text-blue-500 hover:bg-blue-50 rounded-md transition-colors" title="编辑报告">
                                    <Icons.Edit />
                                </button>
                                <button onClick={handleDownload} className="p-1.5 text-gray-400 hover:text-blue-500 hover:bg-blue-50 rounded-md transition-colors" title="下载为Markdown">
                                    <Icons.Download />
                                </button>
                            </div>
                        )}

                        {parsedData ? (
                            <>
                                {(parsedData.sseStages?.length > 0 || parsedData.sseError || msg.isThinking) && (
                                    <ThinkingPipeline
                                        stages={parsedData.sseStages || []}
                                        isDone={!msg.isThinking}
                                        sseError={parsedData.sseError}
                                        isThinking={!!msg.isThinking}
                                    />
                                )}
                                
                                {isEditing ? (
                                    <div className="mt-2 animate-fade-in">
                                        <textarea 
                                            value={editContent}
                                            onChange={(e) => setEditContent(e.target.value)}
                                            className="w-full h-64 p-4 border border-blue-200 rounded-xl focus:ring-2 focus:ring-blue-500 outline-none text-sm font-mono text-gray-700 bg-gray-50 resize-y"
                                        />
                                        <div className="flex justify-end gap-2 mt-3">
                                            <button onClick={() => setIsEditing(false)} className="px-3 py-1.5 text-xs text-gray-500 hover:bg-gray-100 rounded-lg">取消</button>
                                            <button onClick={handleSave} className="px-3 py-1.5 text-xs bg-blue-600 text-white rounded-lg hover:bg-blue-700 flex items-center gap-1">
                                                <Icons.Save /> 保存修改
                                            </button>
                                        </div>
                                    </div>
                                ) : (
                                    <div className="markdown-body">
                                        {/* 报表生成消息：只显示代码和图表，不显示总结 */}
                                        {isReportGeneration ? (
                                            <>
                                                {/* 显示简化的提示 */}
                                                <div className="text-sm text-gray-600 mb-4">
                                                    <span className="inline-flex items-center gap-2">
                                                        <Icons.Table className="w-4 h-4 text-emerald-600" />
                                                        <span>报表已生成完成，可查看下方数据可视化或下载分析代码</span>
                                                    </span>
                                                </div>

                                                {/* 显示代码块 */}
                                                {parsedData.code && (
                                                    <details className="mt-4 group border border-gray-100 rounded-xl overflow-hidden" open>
                                                        <summary className="flex items-center gap-2 px-4 py-2 bg-gray-50 cursor-pointer select-none text-[11px] font-bold text-gray-500 hover:bg-gray-100 transition-colors">
                                                            <Icons.Terminal />
                                                            <span>分析代码</span>
                                                            <span className="ml-auto group-open:rotate-180 transition-transform duration-200 text-[10px]">▼</span>
                                                        </summary>
                                                        <div className="p-0">
                                                            <pre className="!m-0 !rounded-none !text-[11px] !leading-relaxed">
                                                                <code>{parsedData.code}</code>
                                                            </pre>
                                                        </div>
                                                    </details>
                                                )}
                                            </>
                                        ) : (
                                            <>
                                                {/* 正常消息：显示完整内容 */}
                                                <div dangerouslySetInnerHTML={{ __html: parsedData.summaryHtml }} />

                                                {parsedData.code && (
                                                    <details className="mt-4 group border border-gray-100 rounded-xl overflow-hidden">
                                                        <summary className="flex items-center gap-2 px-4 py-2 bg-gray-50 cursor-pointer select-none text-[11px] font-bold text-gray-500 hover:bg-gray-100 transition-colors">
                                                            <Icons.Terminal />
                                                            <span>查看分析代码</span>
                                                            <span className="ml-auto group-open:rotate-180 transition-transform duration-200 text-[10px]">▼</span>
                                                        </summary>
                                                        <div className="p-0">
                                                            <pre className="!m-0 !rounded-none !text-[11px] !leading-relaxed">
                                                                <code>{parsedData.code}</code>
                                                            </pre>
                                                        </div>
                                                    </details>
                                                )}
                                            </>
                                        )}

                                        {streamStage === 'typing' && (
                                            <span className="inline-block w-1.5 h-4 bg-blue-500 ml-1 animate-pulse align-middle"></span>
                                        )}
                                    </div>
                                )}

                                {parsedData.chartOptions && !isEditing && showChart && (
                                    <div className="mt-6 pt-6 border-t border-gray-100 animate-fade-in">
                                        <div className="mb-4">
                                            <h3 className="text-2xl font-black text-gray-800">
                                                {parsedData.hasAnalysisSection ? '4. 数据图表' : '3. 数据图表'}
                                            </h3>
                                        </div>
                                        <ChartCard spec={parsedData.chartOptions} title={parsedData.chartOptions?.title || shortChartTitle(parsedData.summaryHtml)} />
                                    </div>
                                )}
                            </>
                        ) : (
                            <div className="markdown-body">
                                 <div dangerouslySetInnerHTML={{ __html: window.marked ? window.marked.parse(streamStage === 'done' ? msg.content : displayedSummary) : (streamStage === 'done' ? msg.content : displayedSummary) }} />
                                 {streamStage === 'typing' && <span className="inline-block w-1.5 h-4 bg-blue-500 ml-1 animate-pulse"></span>}
                            </div>
                        )}
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div className="flex flex-row-reverse items-end gap-3 max-w-4xl ml-auto animate-fade-in">
            <Avatar />
            <div className="bg-gradient-to-br from-blue-600 to-blue-700 text-white px-6 py-3.5 rounded-2xl rounded-tr-sm shadow-lg shadow-blue-900/10 text-sm leading-relaxed tracking-wide">
                {msg.content}
            </div>
        </div>
    );
});

export default MessageItem;


