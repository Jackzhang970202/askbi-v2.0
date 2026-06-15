// 📅 2026.03.26 新增：历史记录管理组件
// 📝 功能说明：统一管理BI会话、Excel会话、报表历史记录

import React, { useState, useEffect, useMemo } from 'react';

const HISTORY_REFRESH_EVENT = 'askbi-history-refresh';
import { Icons } from './Icons';
import { api } from '../services/api';

const HistoryManager = ({ onChatSwitch, onLoadReport, showAlert, showConfirm, isAdmin, currentUser }) => {
    const [biHistory, setBiHistory] = useState([]);
    const [excelHistory, setExcelHistory] = useState([]);
    const [reportHistory, setReportHistory] = useState([]);
    const [loading, setLoading] = useState(true);
    const [activeTab, setActiveTab] = useState('all'); // all | bi | excel | report
    const [searchTerm, setSearchTerm] = useState('');
    const [selectedItems, setSelectedItems] = useState(new Set());
    const [deleteLoading, setDeleteLoading] = useState(false);

    useEffect(() => {
        if (!currentUser) return;
        loadAllHistory();
        const handler = () => loadAllHistory();
        window.addEventListener(HISTORY_REFRESH_EVENT, handler);
        return () => window.removeEventListener(HISTORY_REFRESH_EVENT, handler);
    }, [currentUser?.id]);

    const loadAllHistory = async () => {
        setLoading(true);
        try {
            const [biRes, excelRes, reportRes] = await Promise.all([
                api.listBiSessions(),
                api.listExcelSessions(),
                api.listUserReports()
            ]);

            if (biRes.success) setBiHistory((biRes.sessions || []).filter(Boolean));
            if (excelRes.status === 'success') setExcelHistory((excelRes.sessions || []).filter(Boolean));
            if (reportRes.success) setReportHistory(reportRes.reports || []);
        } catch (e) {
            console.error('加载历史记录失败:', e);
            if (currentUser && showAlert) showAlert('加载历史记录失败: ' + e.message, '错误', 'error');
        } finally {
            setLoading(false);
        }
    };

    // 合并并过滤历史记录
    const filteredHistory = useMemo(() => {
        let result = [];

        if (activeTab === 'all' || activeTab === 'bi') {
            result.push(...(biHistory || []).map(h => ({ ...h, itemType: 'bi' })));
        }
        if (activeTab === 'all' || activeTab === 'excel') {
            result.push(...(excelHistory || []).map(h => ({ ...h, itemType: 'excel' })));
        }
        if (activeTab === 'all' || activeTab === 'report') {
            result.push(...(reportHistory || []).map(h => ({ ...h, itemType: 'report' })));
        }

        // 按时间排序
        result.sort((a, b) => {
            const timeA = a.timestamp || new Date(a.created_at || 0).getTime() || 0;
            const timeB = b.timestamp || new Date(b.created_at || 0).getTime() || 0;
            return timeB - timeA;
        });

        // 搜索过滤
        if (searchTerm) {
            const term = searchTerm.toLowerCase();
            result = result.filter(item => {
                const title = item.title || item.display_file_name || item.report_type || '';
                const dsName = item.datasource_name || item.datasourceName || '';
                return title.toLowerCase().includes(term) || dsName.toLowerCase().includes(term);
            });
        }

        return result;
    }, [biHistory, excelHistory, reportHistory, activeTab, searchTerm]);

    const toggleSelectItem = (item) => {
        // 📅 2026.03.26 修复：报表优先使用 report_id，而不是自增 id
        const itemId = item.itemType === 'report' ? item.report_id : item.id;
        const key = `${item.itemType}_${itemId}`;
        setSelectedItems(prev => {
            const newSet = new Set(prev);
            if (newSet.has(key)) {
                newSet.delete(key);
            } else {
                newSet.add(key);
            }
            return newSet;
        });
    };

    const toggleSelectAll = () => {
        if (selectedItems.size === filteredHistory.length) {
            setSelectedItems(new Set());
        } else {
            setSelectedItems(new Set(filteredHistory.map(item => {
                // 📅 2026.03.26 修复：报表优先使用 report_id
                const itemId = item.itemType === 'report' ? item.report_id : item.id;
                return `${item.itemType}_${itemId}`;
            })));
        }
    };

    const handleDeleteSelected = async () => {
        if (selectedItems.size === 0) {
            if (showAlert) showAlert('请先选择要删除的记录', '提示', 'warning');
            return;
        }

        const confirmed = showConfirm
            ? await new Promise((resolve) => {
                showConfirm(`确定要删除选中的 ${selectedItems.size} 条记录吗？此操作不可恢复。`, () => resolve(true), '批量删除确认');
            })
            : window.confirm(`确定要删除选中的 ${selectedItems.size} 条记录吗？此操作不可恢复。`);

        if (!confirmed) return;

        setDeleteLoading(true);
        let successCount = 0;
        let failCount = 0;

        for (const key of selectedItems) {
            // 📅 2026.03.26 修复：使用 indexOf 只分割第一个下划线，避免ID中包含下划线导致问题
            const underscoreIndex = key.indexOf('_');
            const type = key.substring(0, underscoreIndex);
            const id = key.substring(underscoreIndex + 1);
            try {
                if (type === 'bi') {
                    await api.deleteBiSession(id);
                } else if (type === 'excel') {
                    await api.deleteExcelChat(id);
                } else if (type === 'report') {
                    await api.deleteReport(id);
                }
                if (type === 'bi') setBiHistory(prev => prev.filter(item => item.id !== id));
                else if (type === 'excel') setExcelHistory(prev => prev.filter(item => item.id !== id));
                else if (type === 'report') setReportHistory(prev => prev.filter(item => item.report_id !== id));
                successCount++;
            } catch (e) {
                console.error(`删除 ${key} 失败:`, e);
                failCount++;
            }
        }

        setDeleteLoading(false);
        setSelectedItems(new Set());

        if (showAlert) {
            showAlert(`删除完成：成功 ${successCount} 条，失败 ${failCount} 条`, '操作结果', failCount > 0 ? 'warning' : 'success');
        }
        window.dispatchEvent(new Event(HISTORY_REFRESH_EVENT));
        loadAllHistory();
    };

    const handleDeleteSingle = async (item) => {
        const itemName = item.title || item.display_file_name || item.id || item.report_id;
        const confirmed = showConfirm
            ? await new Promise((resolve) => {
                showConfirm(`确定要删除 "${itemName}" 吗？`, () => resolve(true), '确认删除');
            })
            : window.confirm(`确定要删除 "${itemName}" 吗？`);

        if (!confirmed) return;

        try {
            if (item.itemType === 'bi') {
                await api.deleteBiSession(item.id);
            } else if (item.itemType === 'excel') {
                await api.deleteExcelChat(item.id);
            } else if (item.itemType === 'report') {
                await api.deleteReport(item.report_id);
            }
            if (item.itemType === 'bi') setBiHistory(prev => prev.filter(history => history.id !== item.id));
            else if (item.itemType === 'excel') setExcelHistory(prev => prev.filter(history => history.id !== item.id));
            else if (item.itemType === 'report') setReportHistory(prev => prev.filter(history => history.report_id !== item.report_id));
            window.dispatchEvent(new Event(HISTORY_REFRESH_EVENT));
            loadAllHistory();
        } catch (e) {
            if (showAlert) showAlert('删除失败: ' + e.message, '错误', 'error');
        }
    };

    const handleItemClick = (item) => {
        if (item.itemType === 'report') {
            if (onLoadReport) onLoadReport(item);
        } else {
            if (onChatSwitch) onChatSwitch(item);
        }
    };

    const getItemIcon = (item) => {
        if (item.itemType === 'bi') {
            return <Icons.Database className="w-5 h-5 text-blue-500" />;
        } else if (item.itemType === 'excel') {
            return <Icons.Table className="w-5 h-5 text-emerald-500" />;
        } else if (item.itemType === 'report') {
            if (item.report_type === 'dashboard') {
                return (
                    <svg className="w-5 h-5 text-teal-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <rect x="2" y="3" width="20" height="14" rx="2" ry="2"></rect>
                        <line x1="8" y1="21" x2="16" y2="21"></line>
                        <line x1="12" y1="17" x2="12" y2="21"></line>
                    </svg>
                );
            }
            return <Icons.Table className="w-5 h-5 text-purple-500" />;
        }
    };

    const getItemTypeLabel = (item) => {
        if (item.itemType === 'bi') return 'BI会话';
        if (item.itemType === 'excel') return 'Excel会话';
        if (item.itemType === 'report') {
            return item.report_type === 'dashboard' ? '大屏' : '报表';
        }
        return '未知';
    };

    const getItemTime = (item) => {
        const ts = item.timestamp || new Date(item.created_at || 0).getTime() || 0;
        return ts ? new Date(ts).toLocaleString() : '未知时间';
    };

    // 📅 2026.03.26 修复：报表优先使用 report_id，避免使用自增 id
    const getItemKey = (item) => {
        const itemId = item.itemType === 'report' ? item.report_id : item.id;
        return `${item.itemType}_${itemId}`;
    };

    return (
        <div className="flex-1 flex flex-col bg-gray-50/50 p-8 overflow-y-auto min-h-screen">
            <div className="max-w-6xl mx-auto w-full">
                {/* 标题区域 */}
                <div className="flex justify-between items-center mb-8">
                    <div>
                        <h1 className="text-3xl font-black text-gray-800 tracking-tight">历史记录管理</h1>
                        <p className="text-gray-500 mt-1 font-medium">查看和管理您的所有会话与报表记录</p>
                    </div>
                    <button
                        onClick={loadAllHistory}
                        className="px-4 py-2 text-gray-600 hover:text-blue-600 font-bold flex items-center gap-2 transition-all"
                    >
                        <Icons.RefreshCw className="w-4 h-4" />
                        刷新
                    </button>
                </div>

                {/* 筛选区域 */}
                <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-6 mb-6">
                    <div className="flex flex-wrap items-center gap-4">
                        {/* 类型筛选 */}
                        <div className="flex items-center gap-2">
                            <span className="text-sm font-bold text-gray-500">类型：</span>
                            <div className="flex bg-gray-100 rounded-xl p-1">
                                {[
                                    { key: 'all', label: '全部' },
                                    { key: 'bi', label: 'BI会话' },
                                    { key: 'excel', label: 'Excel' },
                                    { key: 'report', label: '报表' },
                                ].map(tab => (
                                    <button
                                        key={tab.key}
                                        onClick={() => setActiveTab(tab.key)}
                                        className={`px-4 py-2 rounded-lg text-sm font-bold transition-all ${
                                            activeTab === tab.key
                                                ? 'bg-white text-blue-600 shadow-sm'
                                                : 'text-gray-500 hover:text-gray-700'
                                        }`}
                                    >
                                        {tab.label}
                                    </button>
                                ))}
                            </div>
                        </div>

                        {/* 搜索框 */}
                        <div className="flex-1 min-w-[200px]">
                            <div className="relative">
                                <Icons.Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                                <input
                                    type="text"
                                    placeholder="搜索标题或数据源名称..."
                                    value={searchTerm}
                                    onChange={(e) => setSearchTerm(e.target.value)}
                                    className="w-full pl-10 pr-4 py-2.5 bg-gray-50 border border-gray-200 rounded-xl focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 outline-none transition-all font-medium text-sm"
                                />
                            </div>
                        </div>

                        {/* 批量操作 */}
                        {filteredHistory.length > 0 && (
                            <div className="flex items-center gap-3">
                                <label className="flex items-center gap-2 text-sm text-gray-600 font-bold cursor-pointer hover:text-gray-800 transition-colors">
                                    <input
                                        type="checkbox"
                                        checked={selectedItems.size === filteredHistory.length}
                                        onChange={toggleSelectAll}
                                        className="w-4 h-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                                    />
                                    全选
                                </label>
                                {selectedItems.size > 0 && (
                                    <button
                                        onClick={handleDeleteSelected}
                                        disabled={deleteLoading}
                                        className="px-4 py-2 bg-red-500 text-white rounded-xl font-bold shadow-lg shadow-red-500/20 hover:bg-red-600 hover:scale-[1.02] active:scale-95 transition-all disabled:opacity-50 flex items-center gap-2"
                                    >
                                        {deleteLoading ? (
                                            <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                                        ) : (
                                            <Icons.Trash className="w-4 h-4" />
                                        )}
                                        删除 ({selectedItems.size})
                                    </button>
                                )}
                            </div>
                        )}
                    </div>

                    {/* 统计信息 */}
                    <div className="mt-4 pt-4 border-t border-gray-100 flex items-center gap-6 text-sm text-gray-500 font-medium">
                        <span>BI会话: <span className="text-blue-600 font-bold">{biHistory.length}</span></span>
                        <span>Excel会话: <span className="text-emerald-600 font-bold">{excelHistory.length}</span></span>
                        <span>报表: <span className="text-purple-600 font-bold">{reportHistory.length}</span></span>
                        <span className="ml-auto">共 <span className="text-gray-800 font-bold">{filteredHistory.length}</span> 条记录</span>
                    </div>
                </div>

                {/* 列表区域 */}
                {loading ? (
                    <div className="flex items-center justify-center py-20">
                        <div className="animate-spin text-blue-500 text-3xl">↻</div>
                    </div>
                ) : filteredHistory.length === 0 ? (
                    <div className="text-center py-20 bg-white rounded-3xl border border-gray-100">
                        <div className="w-16 h-16 bg-gray-50 rounded-full flex items-center justify-center mx-auto mb-4 text-gray-400">
                            <Icons.Clock className="w-8 h-8" />
                        </div>
                        <h3 className="text-lg font-bold text-gray-800">暂无历史记录</h3>
                        <p className="text-gray-500 text-sm mt-1">开始您的第一次对话或创建报表吧</p>
                    </div>
                ) : (
                    <div className="bg-white rounded-3xl border border-gray-100 shadow-sm overflow-hidden">
                        <table className="w-full">
                            <thead className="bg-gray-50 border-b border-gray-100">
                                <tr>
                                    <th className="w-12 px-4 py-3"></th>
                                    <th className="text-left px-4 py-3 text-xs font-bold text-gray-500 uppercase tracking-wider">类型</th>
                                    <th className="text-left px-4 py-3 text-xs font-bold text-gray-500 uppercase tracking-wider">标题</th>
                                    <th className="text-left px-4 py-3 text-xs font-bold text-gray-500 uppercase tracking-wider">数据源</th>
                                    <th className="text-left px-4 py-3 text-xs font-bold text-gray-500 uppercase tracking-wider">创建时间</th>
                                    <th className="text-right px-4 py-3 text-xs font-bold text-gray-500 uppercase tracking-wider">操作</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-gray-50">
                                {filteredHistory.map((item) => {
                                    const isSelected = selectedItems.has(getItemKey(item));
                                    return (
                                        <tr
                                            key={getItemKey(item)}
                                            className={`hover:bg-gray-50/50 transition-colors cursor-pointer ${isSelected ? 'bg-blue-50/50' : ''}`}
                                            onClick={() => handleItemClick(item)}
                                        >
                                            <td className="px-4 py-4" onClick={(e) => e.stopPropagation()}>
                                                <input
                                                    type="checkbox"
                                                    checked={isSelected}
                                                    onChange={() => toggleSelectItem(item)}
                                                    className="w-4 h-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500 cursor-pointer"
                                                />
                                            </td>
                                            <td className="px-4 py-4">
                                                <div className="flex items-center gap-2">
                                                    {getItemIcon(item)}
                                                    <span className="text-xs font-bold text-gray-600">{getItemTypeLabel(item)}</span>
                                                </div>
                                            </td>
                                            <td className="px-4 py-4">
                                                <div className="font-bold text-gray-800 text-sm truncate max-w-[200px]" title={item.title || item.display_file_name || '-'}>
                                                    {item.title || item.display_file_name || '-'}
                                                </div>
                                                {item.is_desensitized && (
                                                    <span className="text-[9px] text-amber-500 font-bold">🔒 已脱敏</span>
                                                )}
                                            </td>
                                            <td className="px-4 py-4">
                                                <span className="text-sm text-gray-500 truncate max-w-[150px] block">
                                                    {item.datasource_name || item.datasourceName || '-'}
                                                </span>
                                            </td>
                                            <td className="px-4 py-4">
                                                <span className="text-sm text-gray-500">{getItemTime(item)}</span>
                                            </td>
                                            <td className="px-4 py-4 text-right" onClick={(e) => e.stopPropagation()}>
                                                <button
                                                    onClick={() => handleDeleteSingle(item)}
                                                    className="p-2 text-gray-300 hover:text-red-500 hover:bg-red-50 rounded-lg transition-all"
                                                    title="删除"
                                                >
                                                    <Icons.Trash className="w-4 h-4" />
                                                </button>
                                            </td>
                                        </tr>
                                    );
                                })}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>
        </div>
    );
};

export default HistoryManager;