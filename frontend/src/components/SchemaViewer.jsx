import React, { useState, useEffect, useMemo } from 'react';
import { Icons } from './Icons';
import { api } from '../services/api';

const SchemaViewer = ({ onClose, datasourceName, showAlert }) => {
    const [schemaData, setSchemaData] = useState(null);
    const [loading, setLoading] = useState(false);
    const [searchTerm, setSearchTerm] = useState('');
    const [expandedTables, setExpandedTables] = useState(new Set());

    useEffect(() => {
        if (datasourceName) {
            loadSchemaData();
        }
    }, [datasourceName]);

    const loadSchemaData = async () => {
        if (!datasourceName) {
            if (showAlert) showAlert('缺少数据源名称', '提示', 'warning');
            else alert('缺少数据源名称');
            return;
        }
        try {
            setLoading(true);
            console.log('[SchemaViewer] Loading schema for datasource:', datasourceName);
            const result = await api.getReferSchema(datasourceName);
            console.log('[SchemaViewer] Schema loaded:', result);
            if (result.success) {
                setSchemaData(result.tables);
            } else {
                if (showAlert) showAlert(result.error || '未知错误', '错误', 'error');
                else alert(result.error || '未知错误');
            }
        } catch (e) {
            console.error('[SchemaViewer] Error loading schema:', e);
            if (showAlert) showAlert(e.message, '错误', 'error');
            else alert(e.message);
        } finally {
            setLoading(false);
        }
    };

    // 过滤表名
    const filteredTables = useMemo(() => {
        if (!schemaData) return [];
        if (!searchTerm.trim()) return Object.entries(schemaData);
        
        const term = searchTerm.toLowerCase();
        return Object.entries(schemaData).filter(([tableName]) => 
            tableName.toLowerCase().includes(term)
        );
    }, [schemaData, searchTerm]);

    const toggleTable = (tableName) => {
        const newExpanded = new Set(expandedTables);
        if (newExpanded.has(tableName)) {
            newExpanded.delete(tableName);
        } else {
            newExpanded.add(tableName);
        }
        setExpandedTables(newExpanded);
    };

    return (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 backdrop-blur-sm">
            <div className="bg-white rounded-2xl shadow-2xl w-[95vw] max-w-6xl max-h-[90vh] flex flex-col">
                {/* Header */}
                <div className="p-6 border-b border-gray-200 flex items-center justify-between">
                    <div className="flex-1">
                        <h2 className="text-2xl font-black text-gray-800 mb-2">数据表结构</h2>
                        <p className="text-sm text-gray-500">
                            数据源: <span className="font-semibold">{datasourceName || '未知'}</span> · 
                            显示 refer 文件夹中的表结构和样例数据（每个表前5行）
                        </p>
                    </div>
                    <button onClick={onClose} className="p-2 hover:bg-gray-100 rounded-lg transition-colors">
                        <Icons.X />
                    </button>
                </div>

                {/* Search Bar */}
                <div className="p-4 border-b border-gray-200">
                    <div className="relative">
                        <input
                            type="text"
                            value={searchTerm}
                            onChange={(e) => setSearchTerm(e.target.value)}
                            placeholder="搜索表名（支持模糊搜索）..."
                            className="w-full px-4 py-2 pl-10 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                        />
                        <div className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400">
                            <Icons.Search />
                        </div>
                    </div>
                    {schemaData && (
                        <div className="mt-2 text-sm text-gray-500">
                            共 {Object.keys(schemaData).length} 个表，显示 {filteredTables.length} 个
                        </div>
                    )}
                </div>

                {/* Content */}
                <div className="flex-1 overflow-y-auto p-6">
                    {loading ? (
                        <div className="text-center py-12 text-gray-400">加载中...</div>
                    ) : !schemaData ? (
                        <div className="text-center py-12 text-gray-400">无法加载表结构数据</div>
                    ) : filteredTables.length === 0 ? (
                        <div className="text-center py-12 text-gray-400">
                            <p>未找到匹配的表</p>
                            <p className="text-sm mt-2">请尝试其他搜索关键词</p>
                        </div>
                    ) : (
                        <div className="space-y-4">
                            {filteredTables.map(([tableName, tableInfo]) => {
                                const isExpanded = expandedTables.has(tableName);
                                return (
                                    <div
                                        key={tableName}
                                        className="border border-gray-200 rounded-xl overflow-hidden hover:border-blue-300 transition-all"
                                    >
                                        {/* Table Header */}
                                        <div
                                            className="p-4 bg-gray-50 cursor-pointer hover:bg-gray-100 transition-colors"
                                            onClick={() => toggleTable(tableName)}
                                        >
                                            <div className="flex items-center justify-between">
                                                <div className="flex-1">
                                                    <h3 className="text-lg font-bold text-gray-800">{tableName}</h3>
                                                    {tableInfo.comment && (
                                                        <p className="text-sm text-gray-600 mt-1">{tableInfo.comment}</p>
                                                    )}
                                                </div>
                                                <div className="flex items-center gap-4">
                                                    <span className="text-sm text-gray-500">
                                                        {tableInfo.columns?.length || 0} 列
                                                        {tableInfo.sample_data?.length > 0 && (
                                                            <> · {tableInfo.sample_data.length} 行样例数据</>
                                                        )}
                                                    </span>
                                                    <button className="p-1 hover:bg-gray-200 rounded transition-colors">
                                                        {isExpanded ? <Icons.ChevronDown /> : <Icons.ChevronRight />}
                                                    </button>
                                                </div>
                                            </div>
                                        </div>

                                        {/* Table Details */}
                                        {isExpanded && (
                                            <div className="p-4 bg-white">
                                                {/* Columns */}
                                                <div className="mb-4">
                                                    <h4 className="text-sm font-bold text-gray-700 mb-2">列信息</h4>
                                                    <div className="overflow-x-auto">
                                                        <table className="w-full text-sm border-collapse">
                                                            <thead>
                                                                <tr className="bg-gray-50">
                                                                    <th className="px-3 py-2 text-left border border-gray-200 font-semibold text-gray-700">列名</th>
                                                                    <th className="px-3 py-2 text-left border border-gray-200 font-semibold text-gray-700">类型</th>
                                                                    <th className="px-3 py-2 text-left border border-gray-200 font-semibold text-gray-700">注释</th>
                                                                </tr>
                                                            </thead>
                                                            <tbody>
                                                                {tableInfo.columns?.map((col, idx) => (
                                                                    <tr key={idx} className="hover:bg-gray-50">
                                                                        <td className="px-3 py-2 border border-gray-200 text-gray-800 font-mono text-xs">{col.name}</td>
                                                                        <td className="px-3 py-2 border border-gray-200 text-gray-600">{col.type}</td>
                                                                        <td className="px-3 py-2 border border-gray-200 text-gray-500">{col.comment || '-'}</td>
                                                                    </tr>
                                                                ))}
                                                            </tbody>
                                                        </table>
                                                    </div>
                                                </div>

                                                {/* Sample Data */}
                                                {tableInfo.sample_data && tableInfo.sample_data.length > 0 && (
                                                    <div>
                                                        <h4 className="text-sm font-bold text-gray-700 mb-2">样例数据（前5行）</h4>
                                                        <div className="overflow-x-auto">
                                                            <table className="w-full text-sm border-collapse">
                                                                <thead>
                                                                    <tr className="bg-gray-50">
                                                                        {(tableInfo.sample_data[0] ? Object.keys(tableInfo.sample_data[0]) : []).map((key) => (
                                                                            <th key={key} className="px-3 py-2 text-left border border-gray-200 font-semibold text-gray-700">
                                                                                {key}
                                                                            </th>
                                                                        ))}
                                                                    </tr>
                                                                </thead>
                                                                <tbody>
                                                                    {(tableInfo.sample_data || []).map((row, rowIdx) => (
                                                                        <tr key={rowIdx} className="hover:bg-gray-50">
                                                                            {Object.entries(row || {}).map(([key, value]) => (
                                                                                <td key={key} className="px-3 py-2 border border-gray-200 text-gray-700">
                                                                                    {value !== null && value !== undefined ? String(value) : '-'}
                                                                                </td>
                                                                            ))}
                                                                        </tr>
                                                                    ))}
                                                                </tbody>
                                                            </table>
                                                        </div>
                                                    </div>
                                                )}
                                            </div>
                                        )}
                                    </div>
                                );
                            })}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};

export default SchemaViewer;

