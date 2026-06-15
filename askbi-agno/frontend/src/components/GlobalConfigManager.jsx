import React, { useState, useEffect, useMemo, useDeferredValue } from 'react';
import { api } from '../services/api';
import { Icons } from './Icons';

// 📅 2026.03.04 新增：报表规则配置功能
// 📝 变更说明：添加报表规则二级页签，支持配置报表生成规则和表头

const GlobalConfigManager = ({ isAdmin = false, showAlert, showConfirm, initialTab = 'vocabulary' }) => {
    const [activeTab, setActiveTab] = useState(initialTab); // vocabulary, knowledge, sql, report_rule
    const [configs, setConfigs] = useState([]);
    const [loading, setLoading] = useState(false);
    const [editingItem, setEditingItem] = useState(null);
    const [showModal, setShowModal] = useState(false);
    const [datasources, setDatasources] = useState([]);
    const [formData, setFormData] = useState({
        name: '',
        content: '',
        is_enabled: true,
        scope_type: 'universal',
        scope_datasources: [],
        // 📅 2026.03.05 报表规则专用字段
        rule: '',           // 报表生成规则（用户配置）
        headers: []         // 表头配置
    });

    const tabs = [
        { id: 'vocabulary', name: '业务词汇', icon: <Icons.Database className="w-4 h-4" />, placeholder: '如：GMV', contentLabel: '词汇解释', contentPlaceholder: '如：指交易总额，包含退款订单' },
        { id: 'knowledge', name: '业务知识', icon: <Icons.Terminal className="w-4 h-4" />, placeholder: '如：会员等级规则', contentLabel: '知识描述', contentPlaceholder: '详细描述该业务逻辑或规则...' },
        { id: 'sql', name: '参考 SQL', icon: <Icons.Settings className="w-4 h-4" />, placeholder: '如：活跃用户定义', contentLabel: 'SQL 代码', contentPlaceholder: 'SELECT ...' },
    ];

    const fetchDatasources = async () => {
        try {
            const res = await api.listDatasources();
            if (res.success) setDatasources(res.datasources || []);
        } catch (err) { console.error(err); }
    };

    const getDsDisplayName = (name) => {
        const ds = datasources.find(d => d.name === name);
        return ds ? (ds.display_name || ds.name) : name;
    };

    const fetchConfigs = async () => {
        setLoading(true);
        try {
            const res = await api.listGlobalConfigs(activeTab);
            if (res.success) setConfigs(res.configs);
        } catch (err) {
            console.error('获取配置失败:', err);
            if (showAlert) showAlert('获取配置失败: ' + err.message, '错误', 'error');
            else alert('获取配置失败: ' + err.message);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchConfigs();
        fetchDatasources();
    }, [activeTab]);

    // 📅 2026.03.20 新增：监听外部传入的 initialTab
    useEffect(() => {
        if (initialTab && initialTab !== activeTab) {
            setActiveTab(initialTab);
        }
    }, [initialTab]);

    const handleSubmit = async (e) => {
        e.preventDefault();
        try {
            // 📅 2026.03.05 更新：报表规则需要特殊处理 content 字段
            let content = formData.content;
            if (activeTab === 'report_rule') {
                // 报表规则的 content 是 JSON 格式（只保存规则和表头，前后提示词由后端硬编码）
                content = JSON.stringify({
                    rule: formData.rule || '',
                    headers: formData.headers || []
                });
            }

            const payload = {
                ...formData,
                content: content,
                category: activeTab,
                id: editingItem?.id
            };
            if (formData.scope_type === 'universal') {
                payload.scope_datasources = [];
            }

            const res = await api.saveGlobalConfig(payload);
            if (res.success) {
                setShowModal(false);
                setEditingItem(null);
                setFormData({
                    name: '',
                    content: '',
                    is_enabled: true,
                    scope_type: 'universal',
                    scope_datasources: [],
                    rule: '',
                    headers: []
                });
                fetchConfigs();
            }
        } catch (err) {
            if (showAlert) showAlert('保存失败: ' + err.message, '错误', 'error');
            else alert('保存失败: ' + err.message);
        }
    };

    const handleDelete = async (id) => {
        if (showConfirm) {
            const confirmed = await new Promise((resolve) => {
                showConfirm('确定要删除吗？', () => resolve(true), '确认删除');
            });
            if (!confirmed) return;
        } else {
            if (!confirm('确定要删除吗？')) return;
        }
        try {
            const res = await api.deleteGlobalConfig(id);
            if (res.success) fetchConfigs();
        } catch (err) {
            if (showAlert) showAlert('删除失败: ' + err.message, '错误', 'error');
            else alert('删除失败: ' + err.message);
        }
    };

    const handleToggle = async (item) => {
        try {
            const res = await api.toggleGlobalConfig(item.id, !item.is_enabled);
            if (res.success) {
                setConfigs(configs.map(c => c.id === item.id ? { ...c, is_enabled: !c.is_enabled } : c));
            }
        } catch (err) {
            if (showAlert) showAlert('切换状态失败: ' + err.message, '错误', 'error');
            else alert('切换状态失败: ' + err.message);
        }
    };

    const handleScopeToggle = (dsName) => {
        setFormData(prev => {
            const isSelected = prev.scope_datasources.includes(dsName);
            const nextDs = isSelected 
                ? prev.scope_datasources.filter(name => name !== dsName)
                : [...prev.scope_datasources, dsName];
            
            return {
                ...prev,
                scope_type: nextDs.length > 0 ? 'specific' : 'universal',
                scope_datasources: nextDs
            };
        });
    };

    const handleSetUniversal = () => {
        setFormData(prev => ({
            ...prev,
            scope_type: 'universal',
            scope_datasources: []
        }));
    };

    const deferredContent = useDeferredValue(formData.content);
    const deferredRule = useDeferredValue(formData.rule);
    const currentTabInfo = tabs.find(t => t.id === activeTab);
    const headerCountLabel = useMemo(() => `${formData.headers.length} 个表头`, [formData.headers.length]);

    return (
        <div className="flex-1 flex flex-col bg-white overflow-hidden h-full">
            {/* Header */}
            <div className="h-16 bg-white border-b border-gray-200/60 flex items-center justify-between px-8 shrink-0">
                <div className="flex items-center gap-4">
                    <div className="p-1.5 bg-indigo-100 text-indigo-600 rounded-lg">
                        <Icons.Terminal className="w-5 h-5" />
                    </div>
                    <div>
                        <h2 className="font-bold text-gray-800 text-sm">{currentTabInfo?.name || '术语规则配置'}</h2>
                        <div className="text-[10px] text-gray-400 font-medium">管理词汇、知识及参考 SQL</div>
                    </div>
                </div>
                <button
                    onClick={() => {
                        setEditingItem(null);
                        setFormData({
                            name: '',
                            content: '',
                            is_enabled: true,
                            scope_type: 'universal',
                            scope_datasources: [],
                            rule: '',
                            headers: []
                        });
                        setShowModal(true);
                    }}
                    className="px-6 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl text-xs font-black shadow-lg shadow-indigo-600/30 transition-all flex items-center gap-2"
                >
                    <Icons.Plus className="w-4 h-4" />
                    新建{currentTabInfo.name}
                </button>
            </div>

            <div className="flex flex-1 overflow-hidden">
                {/* Main Content Area - Table */}
                <div className="flex-1 flex flex-col bg-white overflow-hidden p-8">
                    {loading ? (
                        <div className="flex flex-col items-center justify-center py-20 gap-3">
                            <div className="w-8 h-8 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin"></div>
                            <p className="text-[10px] font-black text-gray-400 uppercase">加载中...</p>
                        </div>
                    ) : configs.length === 0 ? (
                        <div className="text-center py-20 bg-gray-50/50 rounded-3xl border-2 border-dashed border-gray-200">
                            <Icons.Database className="w-12 h-12 mx-auto mb-4 text-gray-200" />
                            <p className="text-sm font-bold text-gray-400">暂无配置记录</p>
                        </div>
                    ) : (
                        <div className="flex-1 flex flex-col min-h-0 bg-white border border-gray-100 rounded-2xl overflow-hidden shadow-sm">
                            <div className="flex-1 overflow-auto custom-scrollbar">
                                <table className="w-full text-left border-collapse">
                                    <thead className="sticky top-0 z-10 bg-gray-50/80 backdrop-blur-md">
                                        <tr>
                                            <th className="px-6 py-4 text-sm font-medium text-gray-500 border-b border-gray-100">术语</th>
                                            <th className="px-6 py-4 text-sm font-medium text-gray-500 border-b border-gray-100">描述</th>
                                            <th className="px-6 py-4 text-sm font-medium text-gray-500 border-b border-gray-100">生效范围</th>
                                            {isAdmin && <th className="px-6 py-4 text-sm font-medium text-gray-500 border-b border-gray-100">创建者</th>}
                                            <th className="px-6 py-4 text-sm font-medium text-gray-500 border-b border-gray-100">修改时间</th>
                                            <th className="px-6 py-4 text-sm font-medium text-gray-500 border-b border-gray-100 text-center">是否启用</th>
                                            <th className="px-6 py-4 text-sm font-medium text-gray-500 border-b border-gray-100 text-right">操作</th>
                                        </tr>
                                    </thead>
                                    <tbody className="divide-y divide-gray-50">
                                        {configs.map(item => {
                                            // 📅 2026.03.04 新增：解析报表规则的 JSON 格式
                                            let displayContent = item.content;
                                            let parsedRule = null;
                                            if (activeTab === 'report_rule' && item.content) {
                                                try {
                                                    parsedRule = JSON.parse(item.content);
                                                    displayContent = parsedRule.rule || item.content;
                                                } catch (e) {
                                                    displayContent = item.content;
                                                }
                                            }

                                            return (
                                                <tr key={item.id} className={`group hover:bg-gray-50/30 transition-colors ${!item.is_enabled ? 'opacity-60' : ''}`}>
                                                    <td className="px-6 py-5 whitespace-nowrap">
                                                        <span className="text-sm font-medium text-gray-900">{item.name}</span>
                                                    </td>
                                                    <td className="px-6 py-5">
                                                        {activeTab === 'report_rule' && parsedRule?.headers ? (
                                                            <div className="text-sm text-gray-600">
                                                                <p className="line-clamp-1 mb-1" title={displayContent}>{displayContent}</p>
                                                                <div className="flex flex-wrap gap-1">
                                                                    {parsedRule.headers.map((h, i) => (
                                                                        <span key={i} className="px-1.5 py-0.5 bg-emerald-50 text-emerald-600 rounded text-xs font-medium border border-emerald-100">
                                                                            {h}
                                                                        </span>
                                                                    ))}
                                                                </div>
                                                            </div>
                                                        ) : (
                                                            <p className="text-sm text-gray-600 line-clamp-1" title={item.content}>{item.content}</p>
                                                        )}
                                                    </td>
                                                    <td className="px-6 py-5">
                                                        <div className="flex flex-wrap gap-1.5">
                                                            {item.scope_type === 'universal' ? (
                                                                <span className="px-2 py-0.5 bg-blue-50 text-blue-600 rounded text-xs font-medium border border-blue-100">通用</span>
                                                            ) : (
                                                                item.scope_datasources?.map(ds => (
                                                                    <span key={ds} className="px-2 py-0.5 bg-gray-100 text-gray-600 rounded text-xs font-medium border border-gray-200">
                                                                        {getDsDisplayName(ds)}
                                                                    </span>
                                                                ))
                                                            )}
                                                        </div>
                                                    </td>
                                                    {isAdmin && (
                                                        <td className="px-6 py-5 whitespace-nowrap">
                                                            <span className="text-[10px] font-bold px-2 py-0.5 rounded-lg bg-blue-50 text-blue-500 flex items-center gap-1 w-fit" title={`创建者: ${item.owner_username || '系统管理员'}`}>
                                                                <Icons.User className="w-3 h-3" />
                                                                {item.owner_username || '系统管理员'}
                                                            </span>
                                                        </td>
                                                    )}
                                                    <td className="px-6 py-5 whitespace-nowrap text-sm text-gray-500">
                                                        {item.update_time}
                                                    </td>
                                                    <td className="px-6 py-5 text-center">
                                                        <button
                                                            onClick={() => handleToggle(item)}
                                                            className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-green-500/20 ${item.is_enabled ? 'bg-green-500' : 'bg-gray-300'}`}
                                                        >
                                                            <span className={`${item.is_enabled ? 'translate-x-6' : 'translate-x-1'} inline-block h-4 w-4 transform rounded-full bg-white transition-transform shadow`} />
                                                        </button>
                                                    </td>
                                                    <td className="px-6 py-5 text-right whitespace-nowrap">
                                                        <div className="flex justify-end gap-3 text-gray-400">
                                                            <button
                                                                onClick={() => {
                                                                    setEditingItem(item);
                                                                    let parsedContent = { rule: '', headers: [] };
                                                                    if (activeTab === 'report_rule' && item.content) {
                                                                        try {
                                                                            parsedContent = JSON.parse(item.content);
                                                                        } catch (e) {
                                                                            parsedContent = { rule: item.content, headers: [] };
                                                                        }
                                                                    }
                                                                    setFormData({
                                                                        name: item.name,
                                                                        content: item.content,
                                                                        is_enabled: item.is_enabled,
                                                                        scope_type: item.scope_type || 'universal',
                                                                        scope_datasources: item.scope_datasources || [],
                                                                        rule: parsedContent.rule || '',
                                                                        headers: parsedContent.headers || []
                                                                    });
                                                                    setShowModal(true);
                                                                }}
                                                                className="hover:text-indigo-600 transition-colors"
                                                                title="编辑"
                                                            >
                                                                <Icons.Edit className="w-5 h-5" />
                                                            </button>
                                                            <button
                                                                onClick={() => handleDelete(item.id)}
                                                                className="hover:text-red-500 transition-colors"
                                                                title="删除"
                                                            >
                                                                <Icons.Trash className="w-5 h-5" />
                                                            </button>
                                                        </div>
                                                    </td>
                                            </tr>
                                            );
                                        })}
                                    </tbody>
                                </table>
                            </div>
                            {/* Table Footer / Pagination */}
                            <div className="px-6 py-4 bg-white border-t border-gray-100 flex items-center justify-between shrink-0">
                                <span className="text-sm text-gray-500">
                                    页码: 1 / 1
                                </span>
                                <div className="flex gap-2">
                                    <button disabled className="p-2 rounded-lg border border-gray-100 text-gray-300 cursor-not-allowed hover:bg-gray-50 transition-all">
                                        <Icons.ChevronLeft className="w-4 h-4" />
                                    </button>
                                    <button disabled className="p-2 rounded-lg border border-gray-100 text-gray-300 cursor-not-allowed hover:bg-gray-50 transition-all">
                                        <Icons.ChevronRight className="w-4 h-4" />
                                    </button>
                                </div>
                            </div>
                        </div>
                    )}
                </div>
            </div>

            {/* Edit/Add Modal */}
            {showModal && (
                <div className="fixed inset-0 bg-black/60 backdrop-blur-md z-[100] flex items-center justify-center p-4">
                    <div className="bg-white rounded-[2rem] w-full max-w-2xl max-h-[90vh] shadow-2xl overflow-hidden flex flex-col animate-slide-up">
                        <div className="p-8 border-b border-gray-100 flex justify-between items-center bg-gray-50/50">
                            <div>
                                <h2 className="text-2xl font-black text-gray-800 tracking-tight">{editingItem ? `编辑${currentTabInfo.name}` : `新建${currentTabInfo.name}`}</h2>
                                <p className="text-sm text-gray-500 font-medium">配置术语规则及其生效范围</p>
                            </div>
                            <button onClick={() => setShowModal(false)} className="p-3 hover:bg-white rounded-2xl transition-all shadow-sm">
                                <Icons.X className="w-6 h-6 text-gray-400" />
                            </button>
                        </div>

                        <div className="p-8 space-y-6 overflow-y-auto flex-1 custom-scrollbar">
                            <div className="space-y-2">
                                <label className="text-xs font-black text-gray-400 uppercase tracking-widest">条目名称</label>
                                <input
                                    type="text"
                                    value={formData.name}
                                    onChange={e => setFormData({ ...formData, name: e.target.value })}
                                    placeholder={currentTabInfo.placeholder}
                                    className="w-full px-5 py-3 bg-gray-50 border border-gray-200 rounded-2xl focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 outline-none transition-all font-bold"
                                    required
                                />
                            </div>

                            <div className="space-y-2">
                                <label className="text-xs font-black text-gray-400 uppercase tracking-widest">{currentTabInfo.contentLabel}</label>
                                {/* 📅 2026.03.04 新增：报表规则专用编辑界面 */}
                                {activeTab === 'report_rule' ? (
                                    <>
                                        <div className="space-y-2">
                                            <label className="text-xs font-bold text-gray-500">处理规则（用户配置的核心规则）</label>
                                            <textarea
                                                value={formData.rule}
                                                onChange={e => setFormData({ ...formData, rule: e.target.value })}
                                                placeholder="统计每个人的出勤天数，计算出勤率，按部门分组..."
                                                className="w-full px-5 py-4 bg-gray-50 border border-gray-200 rounded-2xl focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 outline-none transition-all h-32 resize-none font-mono font-medium"
                                                required
                                            />
                                        </div>
                                        <div className="space-y-2">
                                            <label className="text-xs font-bold text-gray-500 flex items-center justify-between">
                                                表头配置
                                                <span className="text-blue-600 normal-case font-bold">已配置 {formData.headers.length} 个表头</span>
                                            </label>
                                            <div className="border border-gray-100 rounded-2xl overflow-hidden bg-gray-50/30">
                                                <div className="max-h-40 overflow-y-auto p-3 space-y-2 custom-scrollbar">
                                                    {formData.headers.map((header, idx) => (
                                                        <div key={idx} className="flex items-center gap-2">
                                                            <input
                                                                type="text"
                                                                value={header}
                                                                onChange={e => {
                                                                    const newHeaders = [...formData.headers];
                                                                    newHeaders[idx] = e.target.value;
                                                                    setFormData({ ...formData, headers: newHeaders });
                                                                }}
                                                                className="flex-1 px-4 py-2 bg-white border border-gray-200 rounded-xl text-sm font-medium focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 outline-none transition-all"
                                                                placeholder={`表头 ${idx + 1}`}
                                                            />
                                                            <button
                                                                type="button"
                                                                onClick={() => {
                                                                    const newHeaders = formData.headers.filter((_, i) => i !== idx);
                                                                    setFormData({ ...formData, headers: newHeaders });
                                                                }}
                                                                className="p-2 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition-all"
                                                                title="删除此表头"
                                                            >
                                                                <Icons.X className="w-4 h-4" />
                                                            </button>
                                                        </div>
                                                    ))}
                                                    {formData.headers.length === 0 && (
                                                        <div className="text-center py-4 text-gray-400 text-sm">暂无表头配置</div>
                                                    )}
                                                </div>
                                                <div className="p-3 border-t border-gray-100 bg-white">
                                                    <button
                                                        type="button"
                                                        onClick={() => setFormData({ ...formData, headers: [...formData.headers, ''] })}
                                                        className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-blue-50 text-blue-600 rounded-xl text-xs font-bold hover:bg-blue-100 transition-all border border-blue-100"
                                                    >
                                                        <Icons.Plus className="w-4 h-4" />
                                                        添加表头
                                                    </button>
                                                </div>
                                            </div>
                                        </div>
                                    </>
                                ) : (
                                    <textarea
                                        value={formData.content}
                                        onChange={e => setFormData({ ...formData, content: e.target.value })}
                                        placeholder={currentTabInfo.contentPlaceholder}
                                        className="w-full px-5 py-4 bg-gray-50 border border-gray-200 rounded-2xl focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 outline-none transition-all h-32 resize-none font-mono font-medium"
                                        required
                                    />
                                )}
                            </div>

                            <div className="space-y-4">
                                <label className="text-xs font-black text-gray-400 uppercase tracking-widest flex items-center justify-between">
                                    生效范围
                                    {formData.scope_datasources.length > 0 && (
                                        <span className="text-blue-600 normal-case font-bold">已选择 {formData.scope_datasources.length} 个数据源</span>
                                    )}
                                </label>
                                
                                {/* Selected Tags Display */}
                                {formData.scope_type === 'specific' && formData.scope_datasources.length > 0 && (
                                    <div className="flex flex-wrap gap-2 p-3 bg-blue-50/50 rounded-xl border border-blue-100 min-h-[44px]">
                                        {formData.scope_datasources.map(name => (
                                            <span key={name} className="px-2 py-1 bg-white text-blue-600 rounded-lg text-[10px] font-black border border-blue-200 flex items-center gap-1 shadow-sm">
                                                {datasources.find(d => d.name === name)?.display_name || name}
                                                <button type="button" onClick={() => handleScopeToggle(name)} className="hover:text-red-500"><Icons.X className="w-3 h-3" /></button>
                                            </span>
                                        ))}
                                    </div>
                                )}

                                <div className="border border-gray-100 rounded-2xl overflow-hidden bg-gray-50/30">
                                    <div className="max-h-48 overflow-y-auto p-4 space-y-1 custom-scrollbar">
                                        {datasources.map(ds => {
                                            const isSelected = formData.scope_datasources.includes(ds.name);
                                            return (
                                                <button
                                                    key={ds.name}
                                                    type="button"
                                                    onClick={() => handleScopeToggle(ds.name)}
                                                    className={`w-full flex items-center justify-between px-4 py-2.5 rounded-xl transition-all border ${isSelected ? 'bg-blue-50 text-blue-600 border-blue-100 shadow-sm' : 'bg-white text-gray-600 border-transparent hover:bg-gray-50'}`}
                                                >
                                                    <span className="text-xs font-bold">{ds.display_name || ds.name}</span>
                                                    {isSelected && <Icons.Check className="w-4 h-4 text-blue-500" />}
                                                </button>
                                            );
                                        })}
                                    </div>
                                    <div className="p-3 border-t border-gray-100 bg-white flex justify-center">
                                        <button
                                            type="button"
                                            onClick={handleSetUniversal}
                                            className={`flex items-center gap-2 px-12 py-2 rounded-xl text-xs font-black transition-all border ${formData.scope_type === 'universal' ? 'bg-blue-50 text-blue-600 border-blue-100 shadow-sm' : 'bg-gray-100 text-gray-400 border-transparent hover:bg-gray-200'}`}
                                        >
                                            {formData.scope_type === 'universal' && <Icons.Check className="w-4 h-4 text-blue-500" />}
                                            通用 (全部数据源)
                                        </button>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <div className="p-8 border-t border-gray-100 flex justify-end gap-4 bg-gray-50/50">
                            <button onClick={() => setShowModal(false)} className="px-8 py-3 text-gray-500 font-bold hover:bg-white rounded-2xl transition-all">取消</button>
                            <button
                                onClick={handleSubmit}
                                className="px-10 py-3 bg-indigo-600 text-white rounded-2xl font-black shadow-xl shadow-indigo-500/20 hover:bg-indigo-700 hover:scale-[1.02] active:scale-95 transition-all"
                            >
                                {editingItem ? '保存修改' : '立即创建'}
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default GlobalConfigManager;

