// 📅 2026.03.19 新增：报表编辑弹窗组件
// 📝 变更说明：支持在弹窗中编辑报表数据并保存
// 📅 2026.03.19 更新：新增AI智能改表功能
// 📝 变更说明：支持通过自然语言描述自动修改表格数据
import React, { useState, useEffect, useRef } from 'react';
import { Icons } from './Icons';
import { api } from '../services/api';

const ReportEditor = ({ isOpen, onClose, reportId, reportName, onSaveSuccess, showAlert }) => {
    const [data, setData] = useState([]);
    const [columns, setColumns] = useState([]);
    const [isLoading, setIsLoading] = useState(false);
    const [isSaving, setIsSaving] = useState(false);
    const [editedCells, setEditedCells] = useState({});
    const tableRef = useRef(null);

    // AI改表相关状态
    const [showAIDialog, setShowAIDialog] = useState(false);
    const [aiRequest, setAiRequest] = useState('');
    const [isAIProcessing, setIsAIProcessing] = useState(false);
    const [aiPreviewData, setAiPreviewData] = useState(null);
    const [aiModifiedCells, setAiModifiedCells] = useState([]);
    const [aiDescription, setAiDescription] = useState('');

    // 加载报表数据
    useEffect(() => {
        if (isOpen && reportId) {
            loadReportData();
        }
    }, [isOpen, reportId]);

    const loadReportData = async () => {
        setIsLoading(true);
        try {
            const result = await api.getReportFullData(reportId);
            if (result.success) {
                setData(result.data);
                setColumns(result.columns);
                setEditedCells({});
                setShowAIDialog(false);
                setAiRequest('');
                setAiPreviewData(null);
                setAiModifiedCells([]);
            } else {
                showAlert(result.error || '加载报表数据失败', '错误', 'error');
            }
        } catch (error) {
            showAlert(error.message || '加载报表数据失败', '错误', 'error');
        } finally {
            setIsLoading(false);
        }
    };

    const handleCellChange = (rowIndex, column, value) => {
        setData(prevData => {
            const newData = [...prevData];
            newData[rowIndex] = { ...newData[rowIndex], [column]: value };
            return newData;
        });
        setEditedCells(prev => ({ ...prev, [`${rowIndex}-${column}`]: true }));
    };

    const handleSave = async () => {
        setIsSaving(true);
        try {
            const result = await api.updateReportData(reportId, data, columns);
            if (result.success) {
                showAlert('报表保存成功！', '成功', 'success');
                setEditedCells({});
                if (onSaveSuccess) onSaveSuccess(result);
                onClose();
            } else {
                showAlert(result.error || '保存失败', '错误', 'error');
            }
        } catch (error) {
            showAlert(error.message || '保存失败', '错误', 'error');
        } finally {
            setIsSaving(false);
        }
    };

    const handleAIEdit = async () => {
        if (!aiRequest.trim()) {
            showAlert('请描述您想要的修改', '提示', 'warning');
            return;
        }
        setIsAIProcessing(true);
        try {
            const sampleData = data.slice(0, 100);
            const result = await api.aiEditReport(reportId, sampleData, columns, aiRequest);
            if (result.success) {
                setAiPreviewData(result.data);
                setAiModifiedCells(result.modified_cells || []);
                setAiDescription(result.description || 'AI修改');
                setColumns(result.columns || columns);
                setShowAIDialog(false);
                showAlert(`AI分析完成，共 ${result.modified_count || 0} 处修改待确认`, '成功', 'success');
            } else {
                showAlert(result.error || 'AI改表失败', '错误', 'error');
            }
        } catch (error) {
            showAlert(error.message || 'AI改表失败', '错误', 'error');
        } finally {
            setIsAIProcessing(false);
        }
    };

    const handleConfirmAIEdit = () => {
        if (aiPreviewData) {
            setData(aiPreviewData);
            const newEditedCells = { ...editedCells };
            aiModifiedCells.forEach(cell => {
                newEditedCells[`${cell.row}-${cell.column}`] = true;
            });
            setEditedCells(newEditedCells);
            setAiPreviewData(null);
            setAiModifiedCells([]);
            setAiDescription('');
            setAiRequest('');
            showAlert('AI修改已应用，请检查后保存', '成功', 'success');
        }
    };

    const handleCancelAIEdit = () => {
        setAiPreviewData(null);
        setAiModifiedCells([]);
        setAiDescription('');
        setAiRequest('');
    };

    // 限制显示行数
    const displayData = (aiPreviewData || data).slice(0, 100);
    const totalRows = (aiPreviewData || data).length;

    // 构建 AI 修改单元格的 Set
    const aiModifiedSet = new Set(aiModifiedCells.map(c => `${c.row}-${c.column}`));

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 z-[9999] flex items-center justify-center">
            <div className="absolute inset-0 bg-black bg-opacity-50" onClick={onClose} />
            <div className="relative bg-white rounded-2xl shadow-2xl w-[95vw] h-[90vh] flex flex-col overflow-hidden">
                {/* 头部 */}
                <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 bg-gray-50">
                    <div className="flex items-center gap-3">
                        <Icons.Table className="w-6 h-6 text-emerald-600" />
                        <div>
                            <h3 className="text-lg font-bold text-gray-800">编辑报表</h3>
                            <p className="text-sm text-gray-500">{reportName || '报表'}</p>
                        </div>
                    </div>
                    <div className="flex items-center gap-3">
                        {Object.keys(editedCells).length > 0 && (
                            <span className="text-sm text-amber-600 bg-amber-50 px-3 py-1 rounded-full">
                                已修改 {Object.keys(editedCells).length} 个单元格
                            </span>
                        )}
                        <button
                            onClick={() => setShowAIDialog(true)}
                            className="flex items-center gap-2 px-4 py-1.5 bg-gradient-to-r from-purple-500 to-indigo-500 hover:from-purple-600 hover:to-indigo-600 text-white rounded-full text-sm font-medium transition-all shadow-lg"
                        >
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z" />
                            </svg>
                            AI改表
                        </button>
                        <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
                            <Icons.X className="w-6 h-6" />
                        </button>
                    </div>
                </div>

                {/* AI预览提示条 */}
                {aiPreviewData && (
                    <div className="px-6 py-3 bg-purple-50 border-b border-purple-200 flex items-center justify-between">
                        <div className="flex items-center gap-2 text-purple-700">
                            <span className="font-medium">预览模式：</span>
                            <span>{aiDescription}，共 {aiModifiedCells.length} 处修改</span>
                            <span className="text-purple-500 text-sm">（紫色背景为修改项）</span>
                        </div>
                        <div className="flex gap-2">
                            <button onClick={handleCancelAIEdit} className="px-3 py-1 text-sm text-gray-600 hover:text-gray-800">取消预览</button>
                            <button onClick={handleConfirmAIEdit} className="px-4 py-1 text-sm bg-purple-600 hover:bg-purple-700 text-white rounded-lg">确认应用</button>
                        </div>
                    </div>
                )}

                {/* 表格区域 */}
                <div className="flex-1 overflow-auto p-4 bg-gray-100">
                    {isLoading ? (
                        <div className="flex items-center justify-center h-full text-gray-500">加载中...</div>
                    ) : displayData.length === 0 ? (
                        <div className="flex items-center justify-center h-full text-gray-500">暂无数据</div>
                    ) : (
                        <table className="min-w-full border-collapse border border-gray-300 bg-white" ref={tableRef}>
                            <thead className="sticky top-0 z-10">
                                <tr className="bg-emerald-600 text-white">
                                    <th className="px-3 py-2 text-sm font-bold border border-gray-300 w-12">#</th>
                                    {columns.map((col, idx) => (
                                        <th key={idx} className="px-3 py-2 text-sm font-bold border border-gray-300 min-w-[120px]">{col}</th>
                                    ))}
                                </tr>
                            </thead>
                            <tbody>
                                {displayData.map((row, rowIndex) => (
                                    <tr key={rowIndex} className="hover:bg-gray-50">
                                        <td className="px-3 py-2 text-sm border border-gray-200 bg-gray-100 text-gray-500 font-mono">{rowIndex + 1}</td>
                                        {columns.map((col, colIdx) => {
                                            const cellKey = `${rowIndex}-${col}`;
                                            const isAIModified = aiModifiedSet.has(cellKey);
                                            const isEdited = editedCells[cellKey];
                                            let cellClass = 'px-3 py-2 text-sm border-b border-r border-gray-200 bg-white';
                                            if (isAIModified) cellClass = 'px-3 py-2 text-sm border-b border-r border-gray-200 bg-purple-100';
                                            else if (isEdited) cellClass = 'px-3 py-2 text-sm border-b border-r border-gray-200 bg-amber-50';
                                            return (
                                                <td key={colIdx} className={cellClass}>
                                                    <input
                                                        type="text"
                                                        value={row[col] ?? ''}
                                                        onChange={(e) => handleCellChange(rowIndex, col, e.target.value)}
                                                        className="w-full bg-transparent outline-none focus:bg-blue-50 focus:ring-1 focus:ring-blue-300 rounded px-1 py-0.5"
                                                        disabled={!!aiPreviewData}
                                                    />
                                                </td>
                                            );
                                        })}
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    )}
                </div>

                {/* 底部按钮 */}
                <div className="flex items-center justify-between px-6 py-4 border-t border-gray-200 bg-gray-50">
                    <div className="text-sm text-gray-500">
                        共 {totalRows} 行 × {columns.length} 列
                        {totalRows > 100 && <span className="text-amber-500 ml-2">（显示前100行）</span>}
                    </div>
                    <div className="flex gap-3">
                        <button onClick={onClose} className="px-6 py-2 bg-gray-200 text-gray-700 rounded-xl font-bold hover:bg-gray-300">取消</button>
                        <button
                            onClick={handleSave}
                            disabled={isSaving || Object.keys(editedCells).length === 0}
                            className={`px-6 py-2 rounded-xl font-bold transition-all flex items-center gap-2 ${
                                isSaving || Object.keys(editedCells).length === 0
                                    ? 'bg-gray-200 text-gray-400 cursor-not-allowed'
                                    : 'bg-emerald-600 text-white hover:bg-emerald-700 shadow-lg'
                            }`}
                        >
                            {isSaving ? '保存中...' : '保存修改'}
                        </button>
                    </div>
                </div>
            </div>

            {/* AI改表对话框 */}
            {showAIDialog && (
                <div className="fixed inset-0 z-[10000] flex items-center justify-center">
                    <div className="absolute inset-0 bg-black bg-opacity-50" onClick={() => !isAIProcessing && setShowAIDialog(false)} />
                    <div className="relative bg-white rounded-2xl shadow-2xl w-full max-w-lg mx-4 overflow-hidden">
                        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 bg-gradient-to-r from-purple-500 to-indigo-500">
                            <div className="flex items-center gap-2 text-white">
                                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z" />
                                </svg>
                                <span className="font-bold">AI智能改表</span>
                            </div>
                            <button onClick={() => !isAIProcessing && setShowAIDialog(false)} className="text-white/80 hover:text-white" disabled={isAIProcessing}>
                                <Icons.X className="w-5 h-5" />
                            </button>
                        </div>
                        <div className="p-6">
                            {!isAIProcessing ? (
                                <>
                                    <label className="block text-sm font-medium text-gray-700 mb-2">请描述您想要的修改：</label>
                                    <textarea
                                        value={aiRequest}
                                        onChange={(e) => setAiRequest(e.target.value)}
                                        placeholder="例如：将所有空值替换为0"
                                        className="w-full h-32 px-4 py-3 border border-gray-300 rounded-xl resize-none focus:ring-2 focus:ring-purple-500 focus:border-transparent outline-none"
                                    />
                                    <div className="mt-4 text-sm text-gray-500">
                                        <div className="mb-1">示例：</div>
                                        <ul className="list-disc list-inside text-gray-400 space-y-1">
                                            <li>将所有空值替换为0</li>
                                            <li>把出勤天数小于20的行标记异常</li>
                                            <li>删除工号列</li>
                                        </ul>
                                    </div>
                                </>
                            ) : (
                                <div className="flex flex-col items-center justify-center py-8">
                                    <svg className="animate-spin h-12 w-12 text-purple-500 mb-4" viewBox="0 0 24 24">
                                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none"></circle>
                                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
                                    </svg>
                                    <p className="text-gray-600 font-medium">AI分析中...</p>
                                </div>
                            )}
                        </div>
                        {!isAIProcessing && (
                            <div className="flex justify-end gap-3 px-6 py-4 border-t border-gray-200 bg-gray-50">
                                <button onClick={() => setShowAIDialog(false)} className="px-4 py-2 text-gray-600 hover:text-gray-800">取消</button>
                                <button
                                    onClick={handleAIEdit}
                                    disabled={!aiRequest.trim()}
                                    className={`px-6 py-2 rounded-xl font-bold ${
                                        !aiRequest.trim()
                                            ? 'bg-gray-200 text-gray-400 cursor-not-allowed'
                                            : 'bg-gradient-to-r from-purple-500 to-indigo-500 hover:from-purple-600 hover:to-indigo-600 text-white shadow-lg'
                                    }`}
                                >
                                    开始改表
                                </button>
                            </div>
                        )}
                    </div>
                </div>
            )}
        </div>
    );
};

export default ReportEditor;