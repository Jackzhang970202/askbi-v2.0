// 📅 2026.03.20 新增：独立的聊天输入组件
// 📝 变更说明：将输入框拆分为独立组件，避免父组件状态更新导致输入卡顿
import React, { useState, useCallback } from 'react';
import { Icons } from './Icons';

const ChatInput = ({
    hasReport,
    chatMode,
    isLoading,
    onSend,
    onModeChange
}) => {
    const [inputValue, setInputValue] = useState('');

    const handleSend = useCallback(() => {
        if (!inputValue.trim() || isLoading || !hasReport) return;
        onSend(inputValue.trim(), chatMode);
        setInputValue('');
    }, [inputValue, isLoading, hasReport, onSend, chatMode]);

    const handleKeyDown = useCallback((e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSend();
        }
    }, [handleSend]);

    return (
        <div className="border-t border-gray-200 bg-white">
            <div className="p-3">
                <textarea
                    value={inputValue}
                    onChange={(e) => setInputValue(e.target.value)}
                    onKeyDown={handleKeyDown}
                    placeholder={
                        !hasReport
                            ? '请先生成报表'
                            : chatMode === 'chat'
                                ? '输入您的问题...'
                                : '描述您想要的修改...'
                    }
                    disabled={!hasReport}
                    rows={3}
                    className="w-full px-4 py-3 bg-gray-50 border border-gray-200 rounded-xl focus:ring-0 focus:border-blue-500 outline-none text-sm disabled:opacity-50 resize-none"
                />
            </div>
            <div className="flex justify-between items-center px-4 pb-3">
                <div className="flex items-center gap-2">
                    <button
                        onClick={() => onModeChange('chat')}
                        disabled={!hasReport}
                        className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition-all border ${
                            chatMode === 'chat'
                                ? 'bg-blue-50 border-blue-200 text-blue-600 shadow-sm'
                                : 'bg-gray-50 border-gray-200 text-gray-500 hover:bg-gray-100'
                        }`}
                        title="问数模式"
                    >
                        💬 问数
                    </button>
                    <button
                        onClick={() => onModeChange('edit')}
                        disabled={!hasReport}
                        className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition-all border ${
                            chatMode === 'edit'
                                ? 'bg-purple-50 border-purple-200 text-purple-600 shadow-sm'
                                : 'bg-gray-50 border-gray-200 text-gray-500 hover:bg-gray-100'
                        }`}
                        title="改表模式"
                    >
                        ✨ 改表
                    </button>
                </div>
                <button
                    onClick={handleSend}
                    disabled={!inputValue.trim() || isLoading || !hasReport}
                    className={`px-4 py-2 rounded-xl font-bold text-sm transition-all flex items-center gap-2 ${
                        chatMode === 'chat'
                            ? 'bg-blue-600 text-white hover:bg-blue-700 disabled:bg-gray-200 disabled:text-gray-400'
                            : 'bg-purple-600 text-white hover:bg-purple-700 disabled:bg-gray-200 disabled:text-gray-400'
                    }`}
                >
                    <Icons.Send className="w-4 h-4" />
                    发送
                </button>
            </div>
        </div>
    );
};

export default React.memo(ChatInput);
