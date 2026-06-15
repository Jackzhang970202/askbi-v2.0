import React, { useMemo } from 'react';
import { Icons } from './Icons';

const ThinkingProcess = ({ thoughts, isWaiting, open, onOpenChange }) => {

    /**
     * 检测并转换 markdown 表格为 HTML 表格
     */
    const renderMarkdownTable = (text) => {
        if (!text || typeof text !== 'string') return text;

        // 检测是否包含 markdown 表格（以 | 开头的行，且至少有3行）
        const lines = text.split('\n');
        const tableStartIndex = lines.findIndex(line => line.trim().startsWith('|'));

        if (tableStartIndex === -1) return text;

        // 找到表格的结束位置
        let tableEndIndex = tableStartIndex;
        for (let i = tableStartIndex; i < lines.length; i++) {
            if (!lines[i].trim().startsWith('|') && lines[i].trim() !== '') {
                break;
            }
            tableEndIndex = i;
        }

        // 如果表格行数少于2行，不渲染为表格
        if (tableEndIndex - tableStartIndex < 2) return text;

        // 提取表格行
        const tableLines = lines.slice(tableStartIndex, tableEndIndex + 1);

        // 解析表格
        const parseTableRow = (line) => {
            return line.split('|').map(cell => cell.trim()).filter(cell => cell !== '');
        };

        const rows = tableLines.map(parseTableRow);

        // 构建表格 HTML
        let tableHtml = '<div class="overflow-x-auto my-3"><table class="min-w-full divide-y divide-gray-700 text-xs">';

        // 表头
        if (rows.length > 0) {
            tableHtml += '<thead><tr>';
            rows[0].forEach(cell => {
                tableHtml += `<th class="px-3 py-2 text-left text-xs font-medium text-gray-300 uppercase tracking-wider bg-gray-800/50 whitespace-nowrap">${cell}</th>`;
            });
            tableHtml += '</tr></thead>';
        }

        // 表体
        tableHtml += '<tbody class="divide-y divide-gray-700">';
        for (let i = 2; i < rows.length; i++) {  // 跳过分隔行（第二行）
            tableHtml += '<tr>';
            rows[i].forEach((cell, cellIndex) => {
                tableHtml += `<td class="px-3 py-2 text-gray-300 whitespace-nowrap">${cell}</td>`;
            });
            tableHtml += '</tr>';
        }
        tableHtml += '</tbody></table></div>';

        // 组合结果：表格前的文本 + 表格 + 表格后的文本
        const beforeTable = lines.slice(0, tableStartIndex).join('\n');
        const afterTable = lines.slice(tableEndIndex + 1).join('\n');

        return (
            <div>
                {beforeTable && <pre className="whitespace-pre-wrap m-0 bg-transparent p-0 border-0 font-mono text-[11px] leading-relaxed break-all text-gray-300">{beforeTable}</pre>}
                <div dangerouslySetInnerHTML={{ __html: tableHtml }} />
                {afterTable && <pre className="whitespace-pre-wrap m-0 bg-transparent p-0 border-0 font-mono text-[11px] leading-relaxed break-all text-gray-300 mt-2">{afterTable}</pre>}
            </div>
        );
    };

    const sanitizeLog = (text) => {
        if (!text) return "";
        let s = String(text);

        // Remove TERMINATE
        s = s.replace(/TERMINATE/g, "").trim();
        // Hide file paths
        s = s.replace(/\/app\/user_upload_files\/[^\s]+/gi, "数据文件");
        s = s.replace(/[^\s]+?\.(xlsx|xls|csv)/gi, "数据文件");
        // Hide internal table/column naming
        s = s.replace(/["']?[\w\u4e00-\u9fa5]+__Sheet\d+(_[\w\u4e00-\u9fa5]+)?["']?/g, (m) => {
            if (m.includes("列") || m.includes("层次") || m.includes("类型")) return "相关列";
            return "数据表";
        });
        // Hide code blocks
        if (s.includes("```")) {
            s = s.replace(/```[\s\S]*?```/g, "（已省略代码细节）");
        }
        // Compress python/sql code fragments
        const looksLikeCode = /\b(import|def|class|print|SELECT|FROM|WHERE|JOIN)\b/.test(s);
        if (looksLikeCode && s.length > 120) {
            s = "（已省略代码细节）";
        }
        return s.trim();
    };

    const visibleThoughts = useMemo(() => (thoughts || []).map(sanitizeLog).filter(Boolean), [thoughts]);

    if (isWaiting) {
        return (
            <details className="group mb-4 w-full" open={open} onToggle={(e) => onOpenChange?.(e.target.open)}>
                <summary className="flex items-center gap-2 cursor-pointer select-none mb-2">
                    <div className="flex items-center gap-2 px-3 py-1.5 rounded-full transition-all text-xs font-medium border bg-blue-50 text-blue-600 border-blue-200 animate-pulse">
                        <Icons.Terminal />
                        <span>正在分析中...</span>
                        <span className="group-open:rotate-180 transition-transform duration-200 text-[10px]">▼</span>
                    </div>
                </summary>
                <div className="bg-[#1e1e1e] rounded-xl p-5 text-xs text-gray-300 font-mono overflow-hidden animate-slide-up border border-gray-800 shadow-2xl relative">
                    <div className="absolute top-0 left-0 right-0 h-6 bg-[#2d2d2d] flex items-center px-3 gap-1.5 border-b border-gray-700">
                        <div className="w-2.5 h-2.5 rounded-full bg-red-500/80"></div>
                        <div className="w-2.5 h-2.5 rounded-full bg-yellow-500/80"></div>
                        <div className="w-2.5 h-2.5 rounded-full bg-green-500/80"></div>
                        <span className="ml-2 text-gray-500">Analysis Terminal</span>
                        <span className="ml-auto text-green-400 animate-pulse">● Live</span>
                    </div>
                    <div className="mt-4 space-y-1.5 max-h-80 overflow-y-auto custom-scrollbar pr-2 scroll-smooth">
                        {visibleThoughts.map((log, i) => (
                            <div key={i} className="p-2.5 rounded border-l-4 border-blue-500 bg-blue-900/20 animate-fade-in mb-2 shadow-sm">
                                <div className="text-[10px] text-blue-400 font-bold mb-1 opacity-80 uppercase tracking-tight">Step {i+1}</div>
                                {(() => {
                                    const rendered = renderMarkdownTable(log);
                                    // 如果返回的是字符串（普通文本），用pre包裹；如果是React节点（包含表格），直接渲染
                                    if (typeof rendered === 'string') {
                                        return <pre className="whitespace-pre-wrap m-0 bg-transparent p-0 border-0 font-mono text-[11px] leading-relaxed break-all text-gray-100">{rendered}</pre>;
                                    } else {
                                        return rendered;
                                    }
                                })()}
                            </div>
                        ))}
                        <div className="text-gray-500 animate-pulse pl-2 py-2 flex items-center gap-2">
                            <span className="w-1.5 h-1.5 bg-blue-500 rounded-full animate-ping"></span>
                            处理中，请稍候…
                        </div>
                    </div>
                </div>
            </details>
        );
    }

    const hasThoughts = visibleThoughts && visibleThoughts.length > 0;
    if (!hasThoughts) return null;

    return (
        <details className="group mb-4 w-full" open={open} onToggle={(e) => onOpenChange?.(e.target.open)}>
            <summary className="flex items-center gap-2 cursor-pointer select-none mb-2">
                <div className="flex items-center gap-2 px-3 py-1.5 rounded-full transition-all text-xs font-medium border bg-gray-100 hover:bg-gray-200 text-gray-500 border-gray-200">
                    <Icons.Terminal />
                    <span>中间过程（问题思考 / RAG / 智能体通讯）</span>
                    <span className="group-open:rotate-180 transition-transform duration-200 text-[10px]">▼</span>
                </div>
            </summary>
            <div className="bg-[#1e1e1e] rounded-xl p-5 text-xs text-gray-300 font-mono overflow-hidden animate-slide-up border border-gray-800 shadow-2xl relative">
                <div className="absolute top-0 left-0 right-0 h-6 bg-[#2d2d2d] flex items-center px-3 gap-1.5 border-b border-gray-700">
                    <div className="w-2.5 h-2.5 rounded-full bg-red-500/80"></div>
                    <div className="w-2.5 h-2.5 rounded-full bg-yellow-500/80"></div>
                    <div className="w-2.5 h-2.5 rounded-full bg-green-500/80"></div>
                    <span className="ml-2 text-gray-500">Analysis Terminal</span>
                </div>
                <div className="mt-4 space-y-1.5 max-h-80 overflow-y-auto custom-scrollbar pr-2 scroll-smooth">
                    {visibleThoughts.map((log, i) => (
                        <div key={i} className="p-2 rounded border-l-2 border-gray-600 bg-gray-800/30 animate-fade-in">
                            {(() => {
                                const rendered = renderMarkdownTable(log);
                                // 如果返回的是字符串（普通文本），用pre包裹；如果是React节点（包含表格），直接渲染
                                if (typeof rendered === 'string') {
                                    return <pre className="whitespace-pre-wrap m-0 bg-transparent p-0 border-0 font-mono text-[11px] leading-relaxed break-all text-gray-300">{rendered}</pre>;
                                } else {
                                    return <div className="text-gray-300">{rendered}</div>;
                                }
                            })()}
                        </div>
                    ))}
                    <div className="text-gray-500 animate-pulse pl-2">_</div>
                </div>
            </div>
        </details>
    );
};

export default ThinkingProcess;


