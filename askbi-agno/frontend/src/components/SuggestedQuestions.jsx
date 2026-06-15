import React, { useState, useEffect, useRef } from 'react';
import { Icons } from './Icons';
import { withBase } from '../services/api';

/**
 * 猜你想问 - 推荐问题组件
 * 基于大模型生成推荐问题
 */
const SuggestedQuestions = ({ chatId, onSelectQuestion, visible = true, excelData = null, activeTableTab = 0, messages = [], mode = 'excel' }) => {
    const [suggestions, setSuggestions] = useState([]);
    const [loading, setLoading] = useState(false);
    const [collapsed, setCollapsed] = useState(false);
    const abortControllerRef = useRef(null);

    /**
     * 获取推荐问题
     */
    const fetchSuggestions = async () => {
        if (!chatId || !visible) {
            return;
        }
        if (mode === 'excel' && (!excelData || excelData.length === 0)) {
            return;
        }
        if (mode !== 'excel' && messages.length === 0) {
            return;
        }

        // 取消之前的请求
        if (abortControllerRef.current) {
            abortControllerRef.current.abort();
        }

        // 创建新的 AbortController
        abortControllerRef.current = new AbortController();

        setLoading(true);
        try {
            let filename = 'chat';
            let sheet_name = 'chat';
            let columns = [];
            let data = [];

            if (mode === 'excel') {
                const currentSheetData = excelData[activeTableTab];
                if (!currentSheetData) return;
                filename = currentSheetData.filename;
                sheet_name = currentSheetData.sheet_name;
                columns = currentSheetData.columns || [];
                data = currentSheetData.data || [];
            }

            // 构建问答历史（取最近2轮）
            const qaHistory = [];
            for (let i = messages.length - 1; i >= 0 && qaHistory.length < 2; i--) {
                const msg = messages[i];
                if (msg.role === 'assistant' && !msg.isThinking && i > 0) {
                    const userMsg = messages[i - 1];
                    if (userMsg.role === 'user') {
                        qaHistory.unshift({
                            question: userMsg.content,
                            answer: msg.content?.substring(0, 200) || ''  // 截取前200字符
                        });
                        i--;  // 跳过用户消息
                    }
                }
            }

            console.log('[SuggestedQuestions] 生成推荐问题:', {
                filename,
                sheet_name,
                columns: columns?.length,
                hasData: !!data,
                qaHistoryCount: qaHistory.length
            });

            const token = localStorage.getItem('askbi_token');
            const res = await fetch(withBase('/suggestions'), {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                signal: abortControllerRef.current.signal,
                body: JSON.stringify({
                    chat_id: chatId,
                    file_name: filename,
                    sheet_name: sheet_name,
                    columns: columns || [],
                    sample_data: data ? data.slice(0, 3) : [],  // 前3行样本数据
                    qa_history: qaHistory.length > 0 ? qaHistory : undefined  // 传递问答历史
                })
            });

            if (!res.ok) {
                throw new Error(`HTTP ${res.status}`);
            }

            const result = await res.json();
            console.log('[SuggestedQuestions] 响应:', result);

            if (result.success && result.suggestions) {
                setSuggestions(result.suggestions);
            } else {
                console.error('[SuggestedQuestions] API 返回失败:', result);
                setSuggestions([]);
            }
        } catch (e) {
            if (e.name !== 'AbortError') {
                console.error('[SuggestedQuestions] 请求失败:', e);
                setSuggestions([]);
            }
        } finally {
            setLoading(false);
        }
    };

    /**
     * 处理问题点击
     */
    const handleQuestionClick = (question) => {
        if (onSelectQuestion) {
            onSelectQuestion(question);
        }
    };

    // 当 excelData、activeTableTab 或 messages 变化时，重新获取推荐
    useEffect(() => {
        console.log('[SuggestedQuestions] useEffect 触发:', {
            hasChatId: !!chatId,
            visible,
            hasExcelData: !!excelData,
            excelDataLength: excelData?.length || 0,
            activeTableTab,
            messagesCount: messages.length
        });

        if (visible && excelData && excelData.length > 0) {
            fetchSuggestions();
        }
    }, [chatId, visible, excelData, activeTableTab, messages]);

    // 暴露刷新方法给父组件
    useEffect(() => {
        window.refreshExcelSuggestions = fetchSuggestions;
        return () => {
            window.refreshExcelSuggestions = null;
            if (abortControllerRef.current) {
                abortControllerRef.current.abort();
            }
        };
    }, [chatId, visible, excelData, activeTableTab]);

    if (!visible) {
        return null;
    }
    if (mode === 'excel' && (!excelData || excelData.length === 0)) {
        return null;
    }
    if (mode !== 'excel' && messages.length === 0) {
        return null;
    }

    return (
        <div className="w-full px-3 pt-2 pb-1 animate-fade-in border-b border-gray-100/80">
            <div className="w-full rounded-lg p-2 bg-gray-50/70">
                <button
                    onClick={() => setCollapsed(!collapsed)}
                    className="w-full flex items-center justify-between gap-2 mb-2 pl-1 text-left"
                >
                    <div className="flex items-center gap-2">
                        <Icons.Lightbulb className="w-3.5 h-3.5 text-amber-500" />
                        <span className="text-xs font-medium text-gray-600">猜你想问</span>
                    </div>
                    <Icons.ChevronDown className={`w-4 h-4 text-gray-400 transition-transform ${collapsed ? '' : 'rotate-180'}`} />
                </button>

                {!collapsed && <div className="grid grid-cols-1 sm:grid-cols-2 gap-1.5">
                    {loading ? (
                        // 加载骨架屏
                        Array.from({ length: 4 }).map((_, idx) => (
                            <div
                                key={idx}
                                className="h-10 bg-gray-100/60 rounded-md animate-pulse"
                            />
                        ))
                    ) : suggestions.length > 0 ? (
                        suggestions.map((question, idx) => (
                            <button
                                key={idx}
                                onClick={() => handleQuestionClick(question)}
                                className="group text-left px-2.5 py-2 bg-white/80 hover:bg-blue-50/90 border border-gray-200/60 hover:border-blue-300 rounded-md text-xs text-gray-700 transition-all duration-200 shadow-sm hover:shadow-md"
                            >
                                <span className="flex items-start gap-2">
                                    <span className="text-blue-400 mt-0.5 flex-shrink-0 text-[10px]">💡</span>
                                    <span className="group-hover:text-blue-700 transition-colors">{question}</span>
                                </span>
                            </button>
                        ))
                    ) : null}
                </div>}
            </div>
        </div>
    );
};

export default SuggestedQuestions;
