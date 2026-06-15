import React, { useState, useEffect } from 'react';
import { Icons } from './Icons';
import { api } from '../services/api';
import KnowledgeEditor from './KnowledgeEditor';

const DataSourceConfig = ({ onConfigChange, onSelect, isAdmin, showAlert, showConfirm }) => {
    const [datasources, setDatasources] = useState([]);
    const [showForm, setShowForm] = useState(false);
    const [loading, setLoading] = useState(false);
    const [metadataLoading, setMetadataLoading] = useState(false);
    const [testLoading, setTestLoading] = useState(false);
    const [showKnowledge, setShowKnowledge] = useState(false);
    const [knowledgeType, setKnowledgeType] = useState('knowledge');
    const [activeDsName, setActiveDsName] = useState('');
    const [editMode, setEditMode] = useState(false);
    const [knowledgeBases, setKnowledgeBases] = useState([]);
    // 📅 2026.03.26 新增：批量选择状态
    const [selectedDs, setSelectedDs] = useState(new Set());
    const [batchDeleteLoading, setBatchDeleteLoading] = useState(false);

    const [formData, setFormData] = useState({
        name: '',
        type: 'excel',
        host: '',
        port: 5432,
        dbname: '',
        user: '',
        password: '',
        database_schema: 'public',
        is_cross_schema: false,
        knowledge_id: '0'
    });
    const [excelFiles, setExcelFiles] = useState([]);
    const [fileConfigs, setFileConfigs] = useState({});

    useEffect(() => {
        loadDatasources();
        loadKnowledgeBases();
    }, []);

    const handleFileChange = (e) => {
        const files = Array.from(e.target.files);
        setExcelFiles(files);
        
        // 初始化每个文件的配置
        const newConfigs = {};
        files.forEach((f, i) => {
            newConfigs[i] = { table_header_rows: '1', sub_name_rows: '' };
        });
        setFileConfigs(newConfigs);
    };

    const updateRangeConfig = (idx, field, type, value) => {
        setFileConfigs(prev => {
            const currentVal = prev[idx]?.[field] || '';
            let [start, end] = currentVal.includes('-') ? currentVal.split('-') : [currentVal, currentVal];
            
            if (type === 'start') start = value;
            else end = value;
            
            const newVal = start === end || !end ? start : `${start}-${end}`;
            return {
                ...prev,
                [idx]: { ...prev[idx], [field]: newVal }
            };
        });
    };

    const renderRangeInput = (idx, field, label) => {
        const value = fileConfigs[idx]?.[field] || '';
        const [start, end] = value.includes('-') ? value.split('-') : [value, value];
        
        return (
            <div className="flex flex-col gap-1">
                <label className="text-[10px] font-black text-gray-400 uppercase">{label}</label>
                <div className="flex items-center gap-1 text-xs text-gray-500 font-bold">
                    从
                    <input 
                        type="number" 
                        min="1"
                        value={start || ''}
                        onChange={(e) => updateRangeConfig(idx, field, 'start', e.target.value)}
                        className="w-12 bg-gray-50 border border-gray-200 rounded-lg px-2 py-1 text-center outline-none focus:border-emerald-500 font-bold"
                    />
                    到
                    <input 
                        type="number" 
                        min="1"
                        value={end || ''}
                        onChange={(e) => updateRangeConfig(idx, field, 'end', e.target.value)}
                        className="w-12 bg-gray-50 border border-gray-200 rounded-lg px-2 py-1 text-center outline-none focus:border-emerald-500 font-bold"
                    />
                    行
                </div>
            </div>
        );
    };

    const handleEdit = (ds) => {
        setFormData({
            name: ds.display_name || ds.name,
            type: ds.type,
            host: ds.config?.host || '',
            port: ds.config?.port || (ds.type === 'mysql' ? 3306 : 5432),
            dbname: ds.config?.dbname || '',
            user: ds.config?.user || '',
            password: ds.config?.password || '',
            database_schema: ds.config?.database_schema || 'public',
            is_cross_schema: ds.config?.is_cross_schema || false,
            knowledge_id: ds.knowledge_id || '0'
        });

        if (ds.type === 'excel') {
            const configs = {};
            const files = ds.config?.files || [];
            if (ds.config?.file_configs) {
                files.forEach((fname, idx) => {
                    configs[idx] = ds.config.file_configs[fname];
                });
            }
            setFileConfigs(configs);
            setExcelFiles(files.map(f => ({ name: f, isExisting: true })));
        }

        setEditMode(true);
        setShowForm(true);
    };

    const loadKnowledgeBases = async () => {
        try {
            const result = await api.listKnowledgeBases();
            if (result.success) {
                setKnowledgeBases(result.knowledge_bases || []);
            }
        } catch (e) {
            console.error('加载知识库列表失败:', e);
        }
    };

    const loadDatasources = async () => {
        try {
            setLoading(true);
            const result = await api.listDatasources();
            if (result.success) {
                setDatasources(result.datasources || []);
            }
        } catch (e) {
            if (showAlert) showAlert('加载数据源失败: ' + e.message, '错误', 'error');
            else alert('加载数据源失败: ' + e.message);
        } finally {
            setLoading(false);
        }
    };

    const handleTest = async (name) => {
        try {
            setTestLoading(true);
            const result = await api.testDatasource(name);
            if (result.success) {
                let msg = '连接成功！';
                if (result.metadata_refreshed) {
                    msg = `连接成功，已刷新元数据（${result.tables_count} 个表）`;
                } else if (result.message) {
                    msg = result.message;
                }
                if (showAlert) showAlert(msg, '成功', 'success');
                else alert(msg);
            } else {
                if (showAlert) showAlert('连接失败: ' + result.message, '失败', 'error');
                else alert('连接失败: ' + result.message);
            }
        } catch (e) {
            if (showAlert) showAlert('测试出错: ' + e.message, '错误', 'error');
            else alert('测试出错: ' + e.message);
        } finally {
            setTestLoading(false);
        }
    };

    const handleSave = async () => {
        // 必填项校验
        const showError = (msg) => showAlert ? showAlert(msg, '提示', 'warning') : alert(msg);
        if (!formData.name.trim()) return showError('请输入显示名称');
        
        if (formData.type === 'excel') {
            if (!editMode && excelFiles.length === 0) {
                return showError('请至少上传一个 Excel 文件');
            }
        } else {
            if (!formData.host) return showError('请输入主机地址');
            if (!formData.port) return showError('请输入端口号');
            if (!formData.dbname) return showError('请输入数据库名');
            if (!formData.user) return showError('请输入用户名');
            if (!editMode && !formData.password) return showError('请输入密码'); // 新建时密码必填
        }

        try {
            setLoading(true);
            
            // 准备配置
            const config = formData.type === 'excel'
                ? {
                    files: excelFiles.map(f => f.name),
                    file_configs: Object.fromEntries(
                        excelFiles.map((f, i) => [f.name, fileConfigs[i]])
                    )
                }
                : {
                    host: formData.host,
                    port: parseInt(formData.port),
                    dbname: formData.dbname,
                    user: formData.user,
                    password: formData.password,
                    database_schema: formData.is_cross_schema ? '' : formData.database_schema,
                    is_cross_schema: formData.is_cross_schema
                    // schemas 字段由后端根据 is_cross_schema 自动获取
                };
                
            // 提取真正需要上传的文件对象
            const filesToUpload = excelFiles.filter(f => !f.isExisting);
            
            // 构造上传时需要的配置映射 (如果是混合模式，api.js 需要处理)
            // 这里为了简单，我们让 api.js 能够通过文件名匹配配置
            const uploadFileConfigs = {};
            excelFiles.forEach((f, i) => {
                uploadFileConfigs[f.name] = fileConfigs[i];
            });

            const result = await api.addDatasource(
                formData.name, 
                formData.type, 
                config, 
                formData.knowledge_id, 
                filesToUpload,
                uploadFileConfigs
            );
            
            if (result.success) {
                const dsId = result.id; // 获取后端返回的唯一 ID
                
                // 如果不是 Excel 类型，自动触发元数据生成
                if (formData.type !== 'excel') {
                    try {
                        setMetadataLoading(true);
                        await api.generateMetadata(dsId);
                    } catch (metaErr) {
                        console.error('自动生成元数据失败:', metaErr);
                        // 元数据失败不影响数据源本身的保存，所以这里不弹窗
                    } finally {
                        setMetadataLoading(false);
                    }
                }

                if (showAlert) showAlert('保存成功并已自动更新元数据！', '成功', 'success');
                else alert('保存成功并已自动更新元数据！');
                setShowForm(false);
                loadDatasources();
                if (onConfigChange) onConfigChange();
            } else {
                if (showAlert) showAlert('保存失败: ' + result.message, '错误', 'error');
                else alert('保存失败: ' + result.message);
            }
        } catch (e) {
            if (showAlert) showAlert('操作出错: ' + e.message, '错误', 'error');
            else alert('操作出错: ' + e.message);
        } finally {
            setLoading(false);
        }
    };

    const handleDelete = async (ds) => {
        const displayName = ds.display_name || ds.name || '未命名数据源';
        if (showConfirm) {
            const confirmed = await new Promise((resolve) => {
                showConfirm(`确定要删除数据源 "${displayName}" 吗？`, () => resolve(true), '确认删除');
            });
            if (!confirmed) return;
        } else {
            if (!window.confirm(`确定要删除数据源 "${displayName}" 吗？`)) return;
        }
        try {
            const result = await api.deleteDatasource(ds.name);
            if (result.success) {
                loadDatasources();
                if (onConfigChange) onConfigChange();
            } else {
                if (showAlert) showAlert('删除失败: ' + (result.message || '未知错误'), '错误', 'error');
                else alert('删除失败: ' + (result.message || '未知错误'));
            }
        } catch (e) {
            if (showAlert) showAlert('删除操作出错: ' + e.message, '错误', 'error');
            else alert('删除操作出错: ' + e.message);
        }
    };

    // 📅 2026.03.26 新增：批量选择和删除功能
    const toggleSelectDs = (dsName) => {
        setSelectedDs(prev => {
            const newSet = new Set(prev);
            if (newSet.has(dsName)) {
                newSet.delete(dsName);
            } else {
                newSet.add(dsName);
            }
            return newSet;
        });
    };

    const toggleSelectAll = () => {
        if (selectedDs.size === datasources.length) {
            setSelectedDs(new Set());
        } else {
            setSelectedDs(new Set(datasources.map(ds => ds.name)));
        }
    };

    const handleBatchDelete = async () => {
        if (selectedDs.size === 0) {
            if (showAlert) showAlert('请先选择要删除的数据源', '提示', 'warning');
            else alert('请先选择要删除的数据源');
            return;
        }

        const confirmed = showConfirm
            ? await new Promise((resolve) => {
                showConfirm(`确定要删除选中的 ${selectedDs.size} 个数据源吗？`, () => resolve(true), '批量删除确认');
            })
            : window.confirm(`确定要删除选中的 ${selectedDs.size} 个数据源吗？`);

        if (!confirmed) return;

        try {
            setBatchDeleteLoading(true);
            const result = await api.batchDeleteDatasources(Array.from(selectedDs));

            if (result.success) {
                if (showAlert) showAlert(result.message, '成功', 'success');
                else alert(result.message);
                setSelectedDs(new Set());
                loadDatasources();
                if (onConfigChange) onConfigChange();
            } else {
                if (showAlert) showAlert(result.error || '批量删除失败', '错误', 'error');
                else alert(result.error || '批量删除失败');
            }
        } catch (e) {
            if (showAlert) showAlert('批量删除出错: ' + e.message, '错误', 'error');
            else alert('批量删除出错: ' + e.message);
        } finally {
            setBatchDeleteLoading(false);
        }
    };

    const openKnowledge = (dsName, type) => {
        setActiveDsName(dsName);
        setKnowledgeType(type);
        setShowKnowledge(true);
    };

    const handleSelectDataSource = (dsName) => {
        if (onSelect) {
            onSelect(dsName);
        }
    };

    return (
        <div className="flex-1 flex flex-col bg-gray-50/50 p-8 overflow-y-auto min-h-screen">
            <div className="max-w-6xl mx-auto w-full">
                <div className="flex justify-between items-center mb-8">
                    <div>
                        <h1 className="text-3xl font-black text-gray-800 tracking-tight">数据源管理</h1>
                        <p className="text-gray-500 mt-1 font-medium">配置您的数据库连接、业务词汇及 SQL 范例</p>
                    </div>
                    <div className="flex items-center gap-3">
                        {/* 📅 2026.03.26 新增：批量操作按钮 */}
                        {datasources.length > 0 && (
                            <>
                                <label className="flex items-center gap-2 text-sm text-gray-600 font-bold cursor-pointer hover:text-gray-800 transition-colors">
                                    <input
                                        type="checkbox"
                                        checked={selectedDs.size === datasources.length && datasources.length > 0}
                                        onChange={toggleSelectAll}
                                        className="w-4 h-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                                    />
                                    全选
                                </label>
                                {selectedDs.size > 0 && (
                                    <button
                                        onClick={handleBatchDelete}
                                        disabled={batchDeleteLoading}
                                        className="px-4 py-2 bg-red-500 text-white rounded-xl font-bold shadow-lg shadow-red-500/20 hover:bg-red-600 hover:scale-[1.02] active:scale-95 transition-all disabled:opacity-50 flex items-center gap-2"
                                    >
                                        {batchDeleteLoading ? (
                                            <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                                        ) : (
                                            <Icons.Trash className="w-4 h-4" />
                                        )}
                                        删除 ({selectedDs.size})
                                    </button>
                                )}
                            </>
                        )}
                        <button
                            onClick={() => {
                                setFormData({ name: '', type: 'excel', host: '', port: 5432, dbname: '', user: '', password: '', database_schema: '', knowledge_id: '0' });
                                setExcelFiles([]);
                                setFileConfigs({});
                                setEditMode(false);
                                setShowForm(true);
                            }}
                            className="px-6 py-3 bg-blue-600 text-white rounded-2xl font-bold shadow-xl shadow-blue-500/20 hover:bg-blue-700 hover:scale-[1.02] active:scale-95 transition-all flex items-center gap-2"
                        >
                            <Icons.Plus className="w-5 h-5" />
                            添加数据源
                        </button>
                    </div>
                </div>

                {loading && datasources.length === 0 ? (
                    <div className="flex items-center justify-center py-20">
                        <div className="animate-spin text-blue-500 text-3xl">↻</div>
                    </div>
                ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                        {datasources.map(ds => (
                            <div key={ds.name} className={`bg-white rounded-3xl border shadow-sm hover:shadow-2xl transition-all p-8 flex flex-col group relative ${selectedDs.has(ds.name) ? 'ring-2 ring-blue-500 border-blue-200' : ''} ${ds.type === 'excel' ? 'border-emerald-100 hover:shadow-emerald-200/50' : 'border-gray-100 hover:shadow-gray-200/50'}`}>
                                {/* 📅 2026.03.26 新增：复选框 */}
                                <div className="absolute top-4 left-4">
                                    <input
                                        type="checkbox"
                                        checked={selectedDs.has(ds.name)}
                                        onChange={() => toggleSelectDs(ds.name)}
                                        className="w-5 h-5 rounded border-gray-300 text-blue-600 focus:ring-blue-500 cursor-pointer"
                                        onClick={(e) => e.stopPropagation()}
                                    />
                                </div>
                                <div className="flex justify-between items-start mb-6 gap-4">
                                    <div className="flex items-center gap-4 min-w-0 ml-6">
                                        <div className={`p-3.5 rounded-2xl shadow-inner flex-shrink-0 ${
                                            ds.type === 'mysql' ? 'bg-orange-50 text-orange-600' :
                                            ds.type === 'pgsql' ? 'bg-blue-50 text-blue-600' :
                                            'bg-emerald-50 text-emerald-600'
                                        }`}>
                                            {ds.type === 'excel' ? <Icons.Table className="w-7 h-7" /> : <Icons.Database className="w-7 h-7" />}
                                        </div>
                                        <div className="min-w-0">
                                            <h3 className="font-black text-gray-800 text-xl group-hover:text-blue-600 transition-colors truncate" title={ds.display_name || ds.name}>
                                                {ds.display_name || ds.name}
                                            </h3>
                                            <div className="flex items-center gap-2 mt-1 flex-wrap">
                                                <span className={`text-[10px] font-black px-2 py-0.5 rounded-lg uppercase tracking-wider flex-shrink-0 ${
                                                    ds.type === 'excel' ? 'bg-emerald-100 text-emerald-600' : 'bg-gray-100 text-gray-500'
                                                }`}>{ds.type}</span>
                                                {isAdmin && ds.owner_username && (
                                                    <span className="text-[10px] font-bold px-2 py-0.5 rounded-lg bg-blue-50 text-blue-500 flex items-center gap-1" title={`创建者: ${ds.owner_username}`}>
                                                        <Icons.User className="w-3 h-3 flex-shrink-0" />
                                                        {ds.owner_username}
                                                    </span>
                                                )}
                                            </div>
                                        </div>
                                    </div>
                                    <div className="flex gap-2 flex-shrink-0">
                                        {ds.type !== 'excel' && (
                                            <button onClick={(e) => { e.stopPropagation(); handleTest(ds.name); }} className={`text-gray-200 hover:text-blue-500 transition-colors p-2 hover:bg-blue-50 rounded-xl ${testLoading ? 'animate-spin' : ''}`} title="测试连接">
                                                <Icons.RefreshCw className="w-5 h-5" />
                                            </button>
                                        )}
                                        <button onClick={(e) => { e.stopPropagation(); handleEdit(ds); }} className="text-gray-200 hover:text-blue-500 transition-colors p-2 hover:bg-blue-50 rounded-xl" title="编辑">
                                            <Icons.Edit className="w-5 h-5" />
                                        </button>
                                        <button onClick={(e) => { e.stopPropagation(); handleDelete(ds); }} className="text-gray-200 hover:text-red-500 transition-colors p-2 hover:bg-red-50 rounded-xl" title="删除">
                                            <Icons.Trash className="w-5 h-5" />
                                        </button>
                                    </div>
                                </div>
                                
                                <div className={`space-y-3 p-4 rounded-2xl border ${ds.type === 'excel' ? 'bg-emerald-50/30 border-emerald-100' : 'bg-gray-50/50 border-gray-100'}`}>
                                    {ds.type === 'excel' ? (
                                        <div className="text-emerald-600 text-[10px] font-bold uppercase tracking-tight max-h-20 overflow-y-auto custom-scrollbar pr-2">
                                            {ds.config.files?.length > 0 ? (
                                                <div className="space-y-1">
                                                    {ds.config.files.map((fname, idx) => (
                                                        <div key={idx} className="flex items-center gap-1.5">
                                                            <span className="w-1 h-1 bg-emerald-400 rounded-full flex-shrink-0"></span>
                                                            <span className="truncate" title={fname}>{fname}</span>
                                                        </div>
                                                    ))}
                                                </div>
                                            ) : '未上传文件'}
                                        </div>
                                    ) : (
                                        <>
                                            <div className="flex justify-between text-xs">
                                                <span className="text-gray-400 font-bold">HOST</span>
                                                <span className="text-gray-600 font-black">{ds.config.host}:{ds.config.port}</span>
                                            </div>
                                            <div className="flex justify-between text-xs">
                                                <span className="text-gray-400 font-bold">DB</span>
                                                <span className="text-gray-600 font-black">{ds.config.dbname}</span>
                                            </div>
                                        </>
                                    )}
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>

            {showForm && (
                <div className="fixed inset-0 bg-black/60 backdrop-blur-md z-[100] flex items-center justify-center p-4 animate-fade-in overflow-hidden">
                    <div className="bg-white rounded-[2rem] w-full max-w-xl max-h-[90vh] shadow-2xl overflow-hidden animate-slide-up flex flex-col">
                        <div className="p-8 border-b border-gray-100 flex justify-between items-center bg-gray-50/50 flex-shrink-0">
                            <div>
                                <h2 className="text-2xl font-black text-gray-800 tracking-tight">{editMode ? '修改数据源' : '配置数据源'}</h2>
                                <p className="text-sm text-gray-500 font-medium">{editMode ? '您可以查看并修改现有的数据源连接信息' : '请填写数据库连接信息'}</p>
                            </div>
                            <button onClick={() => setShowForm(false)} className="p-3 hover:bg-white rounded-2xl transition-all shadow-sm">
                                <Icons.X className="w-6 h-6 text-gray-400" />
                            </button>
                        </div>
                        
                        <div className="p-8 space-y-6 overflow-y-auto flex-1 custom-scrollbar">
                                        <div>
                                            <label className="block text-xs font-black text-gray-400 uppercase tracking-widest mb-2">
                                                显示名称 <span className="text-red-500">*</span>
                                            </label>
                                            <input
                                                type="text"
                                                value={formData.name}
                                                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                                                className="w-full px-5 py-3 bg-gray-50 border border-gray-200 rounded-2xl focus:ring-4 focus:ring-blue-500/10 focus:border-blue-500 outline-none transition-all font-bold"
                                                placeholder="例如: 财务报表分析"
                                                disabled={editMode}
                                            />
                                        </div>
                                        <div>
                                            <label className="block text-xs font-black text-gray-400 uppercase tracking-widest mb-2">
                                                数据源类型 <span className="text-red-500">*</span>
                                            </label>
                                            <select
                                                value={formData.type}
                                                onChange={(e) => setFormData({ ...formData, type: e.target.value, port: e.target.value === 'mysql' ? 3306 : (e.target.value === 'pgsql' ? 5432 : 0) })}
                                                className="w-full px-5 py-3 bg-gray-50 border border-gray-200 rounded-2xl focus:ring-4 focus:ring-blue-500/10 focus:border-blue-500 outline-none transition-all font-bold appearance-none"
                                                disabled={editMode}
                                            >
                                                <option value="excel">Excel 本地文件</option>
                                                <option value="pgsql">PostgreSQL</option>
                                                <option value="mysql">MySQL</option>
                                            </select>
                                        </div>

                                    {formData.type !== 'excel' && (
                                <>
                                    <div className="grid grid-cols-4 gap-6">
                                        <div className="col-span-3">
                                            <label className="block text-xs font-black text-gray-400 uppercase tracking-widest mb-2">
                                                主机地址 <span className="text-red-500">*</span>
                                            </label>
                                            <input
                                                type="text"
                                                value={formData.host}
                                                onChange={(e) => setFormData({ ...formData, host: e.target.value })}
                                                className="w-full px-5 py-3 bg-gray-50 border border-gray-200 rounded-2xl focus:ring-4 focus:ring-blue-500/10 focus:border-blue-500 outline-none transition-all font-bold"
                                                placeholder="localhost"
                                            />
                                        </div>
                                        <div>
                                            <label className="block text-xs font-black text-gray-400 uppercase tracking-widest mb-2">
                                                端口 <span className="text-red-500">*</span>
                                            </label>
                                            <input
                                                type="number"
                                                value={formData.port}
                                                onChange={(e) => setFormData({ ...formData, port: e.target.value })}
                                                className="w-full px-5 py-3 bg-gray-50 border border-gray-200 rounded-2xl focus:ring-4 focus:ring-blue-500/10 focus:border-blue-500 outline-none transition-all font-bold"
                                            />
                                        </div>
                                    </div>

                                    <div className="grid grid-cols-2 gap-6">
                                        <div>
                                            <label className="block text-xs font-black text-gray-400 uppercase tracking-widest mb-2">
                                                数据库名 <span className="text-red-500">*</span>
                                            </label>
                                            <input
                                                type="text"
                                                value={formData.dbname}
                                                onChange={(e) => setFormData({ ...formData, dbname: e.target.value })}
                                                className="w-full px-5 py-3 bg-gray-50 border border-gray-200 rounded-2xl focus:ring-4 focus:ring-blue-500/10 focus:border-blue-500 outline-none transition-all font-bold"
                                            />
                                        </div>
                                    </div>

                                    {/* 跨 Schema 选项 - 仅 PostgreSQL */}
                                    {formData.type === 'pgsql' && (
                                        <div className="bg-blue-50 p-4 rounded-2xl border border-blue-100">
                                            <div className="flex items-center justify-between mb-3">
                                                <div>
                                                    <label className="text-sm font-black text-blue-900">跨 Schema 模式</label>
                                                    <p className="text-xs text-blue-600 mt-1">
                                                        {formData.is_cross_schema ? '自动获取数据库中所有 Schema' : '仅使用单个默认 Schema'}
                                                    </p>
                                                </div>
                                                <button
                                                    type="button"
                                                    onClick={() => setFormData({
                                                        ...formData,
                                                        is_cross_schema: !formData.is_cross_schema
                                                    })}
                                                    className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${formData.is_cross_schema ? 'bg-blue-600' : 'bg-gray-200'}`}
                                                >
                                                    <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${formData.is_cross_schema ? 'translate-x-6' : 'translate-x-1'}`} />
                                                </button>
                                            </div>

                                            {/* 非跨 Schema 模式时显示默认 Schema 输入 */}
                                            {!formData.is_cross_schema && (
                                                <div className="mt-3">
                                                    <label className="block text-xs font-black text-gray-400 uppercase tracking-widest mb-2">默认模式 (可选)</label>
                                                    <input
                                                        type="text"
                                                        value={formData.database_schema}
                                                        onChange={(e) => setFormData({ ...formData, database_schema: e.target.value })}
                                                        className="w-full px-5 py-3 bg-gray-50 border border-gray-200 rounded-2xl focus:ring-4 focus:ring-blue-500/10 focus:border-blue-500 outline-none transition-all font-bold"
                                                        placeholder="public"
                                                    />
                                                    <p className="text-xs text-gray-500 mt-1">不填写则使用数据库默认模式</p>
                                                </div>
                                            )}

                                            {/* 跨 Schema 模式提示 */}
                                            {formData.is_cross_schema && (
                                                <div className="mt-3 p-3 bg-blue-100 rounded-xl">
                                                    <p className="text-xs text-blue-700 flex items-center gap-2">
                                                        <Icons.Database className="w-4 h-4" />
                                                        保存时会自动获取数据库中所有 Schema，无需手动配置
                                                    </p>
                                                </div>
                                            )}
                                        </div>
                                    )}

                                    <div className="grid grid-cols-2 gap-6">
                                        <div>
                                            <label className="block text-xs font-black text-gray-400 uppercase tracking-widest mb-2">
                                                用户名 <span className="text-red-500">*</span>
                                            </label>
                                            <input
                                                type="text"
                                                value={formData.user}
                                                onChange={(e) => setFormData({ ...formData, user: e.target.value })}
                                                className="w-full px-5 py-3 bg-gray-50 border border-gray-200 rounded-2xl focus:ring-4 focus:ring-blue-500/10 focus:border-blue-500 outline-none transition-all font-bold"
                                            />
                                        </div>
                                        <div>
                                            <label className="block text-xs font-black text-gray-400 uppercase tracking-widest mb-2">
                                                密码 {!editMode && <span className="text-red-500">*</span>}
                                            </label>
                                            <input
                                                type="password"
                                                value={formData.password}
                                                onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                                                className="w-full px-5 py-3 bg-gray-50 border border-gray-200 rounded-2xl focus:ring-4 focus:ring-blue-500/10 focus:border-blue-500 outline-none transition-all font-bold"
                                                placeholder={editMode ? "留空表示不修改密码" : "请输入数据库密码"}
                                            />
                                        </div>
                                    </div>
                                </>
                            )}
                            {formData.type === 'excel' && (
                                <div className="space-y-4">
                                    <div className="bg-emerald-50 p-6 rounded-2xl border border-emerald-100">
                                        <p className="text-emerald-800 text-sm font-bold flex items-center gap-2">
                                            <Icons.Table className="w-5 h-5" />
                                            Excel 数据上传 <span className="text-red-500">*</span>
                                        </p>
                                        <p className="text-emerald-600 text-xs mt-2 leading-relaxed">
                                            请上传需要分析的 Excel 文件（支持 .xlsx, .csv）。这些文件将持久化存储在该数据源下。
                                        </p>
                                    </div>
                                    <input 
                                        type="file" 
                                        multiple 
                                        accept=".xlsx,.xls,.csv" 
                                        onChange={handleFileChange}
                                        className="block w-full text-sm text-gray-500 file:mr-4 file:py-3 file:px-6 file:rounded-xl file:border-0 file:text-sm file:font-bold file:bg-emerald-50 file:text-emerald-700 border-2 border-dashed border-gray-300 rounded-xl p-2 cursor-pointer bg-gray-50/50" 
                                    />
                                    {excelFiles.length > 0 && (
                                        <div className="space-y-3">
                                            {excelFiles.map((f, i) => (
                                                <div key={i} className="bg-white p-4 rounded-2xl border border-gray-100 space-y-3">
                                                    <div className="flex items-center gap-2 text-xs font-bold text-gray-700">
                                                        <Icons.Table className="w-4 h-4 text-emerald-500" />
                                                        {f.name}
                                                    </div>
                                                    <div className="grid grid-cols-1 gap-4">
                                                        {renderRangeInput(i, 'table_header_rows', '表头行范围')}
                                                        {renderRangeInput(i, 'sub_name_rows', '子表名行范围')}
                                                    </div>
                                                </div>
                                            ))}
                                        </div>
                                    )}
                                </div>
                            )}
                        </div>

                        <div className="p-8 border-t border-gray-100 flex justify-end gap-4 bg-gray-50/50 flex-shrink-0">
                            <button onClick={() => setShowForm(false)} className="px-8 py-3 text-gray-500 font-bold hover:bg-white rounded-2xl transition-all">取消</button>
                            <button
                                onClick={handleSave}
                                disabled={loading || metadataLoading}
                                className="px-10 py-3 bg-blue-600 text-white rounded-2xl font-black shadow-xl shadow-blue-500/20 hover:bg-blue-700 hover:scale-[1.02] active:scale-95 transition-all disabled:opacity-50 flex items-center gap-2"
                            >
                                {(loading || metadataLoading) && <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>}
                                {loading ? '保存中...' : (metadataLoading ? '生成元数据...' : '确认保存')}
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {showKnowledge && (
                <KnowledgeEditor
                    onClose={() => setShowKnowledge(false)}
                    datasourceName={activeDsName}
                    type={knowledgeType}
                    isExcel={datasources.find(d => d.name === activeDsName)?.type === 'excel'}
                />
            )}
        </div>
    );
};

export default DataSourceConfig;
