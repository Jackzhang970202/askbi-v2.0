import React, { useState, useEffect } from 'react';
import { Icons } from './Icons';
import { api } from '../services/api';

const KnowledgeBaseManager = ({ showAlert, showConfirm }) => {
    const [kbs, setKbs] = useState([]);
    const [loading, setLoading] = useState(false);
    const [showForm, setShowForm] = useState(false);
    const [formData, setFormData] = useState({ id: '', name: '', type: 'rag', description: '', api_url: '', headers: '{}' });

    useEffect(() => {
        loadKbs();
    }, []);

    const loadKbs = async () => {
        try {
            setLoading(true);
            const result = await api.listKnowledgeBases();
            if (result.success) setKbs(result.knowledge_bases || []);
        } catch (e) {
            if (showAlert) showAlert('加载知识库失败: ' + e.message, '错误', 'error');
            else alert('加载知识库失败: ' + e.message);
        } finally {
            setLoading(false);
        }
    };

    const handleSave = async () => {
        if (!formData.id || !formData.name) {
            if (showAlert) showAlert('ID 和名称必填', '提示', 'warning');
            else alert('ID 和名称必填');
            return;
        }
        try {
            const headersObj = JSON.parse(formData.headers || '{}');
            const result = await api.addKnowledgeBase(formData.id, formData.name, formData.type, formData.description, formData.api_url, headersObj);
            if (result.success) {
                setShowForm(false);
                loadKbs();
            }
        } catch (e) {
            if (showAlert) showAlert('保存失败 (请检查 Headers 是否为有效 JSON): ' + e.message, '错误', 'error');
            else alert('保存失败 (请检查 Headers 是否为有效 JSON): ' + e.message);
        }
    };

    const handleDelete = async (id) => {
        if (showConfirm) {
            const confirmed = await new Promise((resolve) => {
                showConfirm('确定要删除该知识库吗？', () => resolve(true), '确认删除');
            });
            if (!confirmed) return;
        } else {
            if (!window.confirm('确定要删除该知识库吗？')) return;
        }
        try {
            const result = await api.deleteKnowledgeBase(id);
            if (result.success) loadKbs();
        } catch (e) {
            if (showAlert) showAlert('删除失败: ' + e.message, '错误', 'error');
            else alert('删除失败: ' + e.message);
        }
    };

    return (
        <div className="flex-1 flex flex-col bg-gray-50/50 p-8 overflow-y-auto min-h-screen">
            <div className="max-w-6xl mx-auto w-full">
                <div className="flex justify-between items-center mb-8">
                    <div>
                        <h1 className="text-3xl font-black text-gray-800 tracking-tight">外接知识库管理</h1>
                        <p className="text-gray-500 mt-1 font-medium">配置 RAG 检索系统或外部知识源，用于对话时的背景增强</p>
                    </div>
                    <button
                        onClick={() => {
                            setFormData({ id: '', name: '', type: 'rag', description: '' });
                            setShowForm(true);
                        }}
                        className="px-6 py-3 bg-indigo-600 text-white rounded-2xl font-bold shadow-xl shadow-indigo-500/20 hover:bg-indigo-700 transition-all flex items-center gap-2"
                    >
                        <Icons.Plus className="w-5 h-5" />
                        添加知识库
                    </button>
                </div>

                {loading ? (
                    <div className="flex justify-center py-20 animate-spin text-indigo-500 text-3xl">↻</div>
                ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                        {kbs.map(kb => (
                            <div key={kb.id} className="bg-white rounded-3xl border border-gray-100 shadow-sm p-8 flex flex-col group hover:shadow-xl transition-all">
                                <div className="flex justify-between items-start mb-6">
                                    <div className="p-4 bg-indigo-50 text-indigo-600 rounded-2xl">
                                        <Icons.Database className="w-8 h-8" />
                                    </div>
                                    <button onClick={() => handleDelete(kb.id)} className="text-gray-300 hover:text-red-500 transition-colors">
                                        <Icons.Trash className="w-5 h-5" />
                                    </button>
                                </div>
                                <h3 className="font-black text-gray-800 text-xl mb-2">{kb.name}</h3>
                                <div className="flex items-center gap-2 mb-4">
                                    <span className="px-2 py-0.5 bg-indigo-100 text-indigo-600 text-[10px] font-black rounded uppercase tracking-wider">ID: {kb.id}</span>
                                    <span className="px-2 py-0.5 bg-gray-100 text-gray-500 text-[10px] font-black rounded uppercase tracking-wider">{kb.type}</span>
                                </div>
                                <p className="text-gray-500 text-sm font-medium line-clamp-2">{kb.description || '无描述'}</p>
                            </div>
                        ))}
                    </div>
                )}
            </div>

            {showForm && (
                <div className="fixed inset-0 bg-black/60 backdrop-blur-md z-[100] flex items-center justify-center p-4">
                    <div className="bg-white rounded-[2rem] w-full max-w-lg shadow-2xl overflow-hidden">
                        <div className="p-8 border-b border-gray-100 flex justify-between items-center">
                            <h2 className="text-2xl font-black text-gray-800">配置新知识库</h2>
                            <button onClick={() => setShowForm(false)}><Icons.X className="w-6 h-6 text-gray-400" /></button>
                        </div>
                        <div className="p-8 space-y-6">
                            <div>
                                <label className="block text-xs font-black text-gray-400 uppercase mb-2">知识库 ID (必须与后端对接代码一致)</label>
                                <input
                                    type="text"
                                    value={formData.id}
                                    onChange={e => setFormData({ ...formData, id: e.target.value })}
                                    className="w-full px-5 py-3 bg-gray-50 border border-gray-200 rounded-2xl outline-none focus:border-indigo-500 font-bold"
                                    placeholder="例如: 1"
                                />
                            </div>
                            <div>
                                <label className="block text-xs font-black text-gray-400 uppercase mb-2">显示名称</label>
                                <input
                                    type="text"
                                    value={formData.name}
                                    onChange={e => setFormData({ ...formData, name: e.target.value })}
                                    className="w-full px-5 py-3 bg-gray-50 border border-gray-200 rounded-2xl outline-none focus:border-indigo-500 font-bold"
                                    placeholder="例如: 企业规章制度"
                                />
                            </div>
                            <div>
                                <label className="block text-xs font-black text-gray-400 uppercase mb-2">API URL (RAG 检索接口地址)</label>
                                <input
                                    type="text"
                                    value={formData.api_url}
                                    onChange={e => setFormData({ ...formData, api_url: e.target.value })}
                                    className="w-full px-5 py-3 bg-gray-50 border border-gray-200 rounded-2xl outline-none focus:border-indigo-500 font-bold"
                                    placeholder="http://example.com/api/search"
                                />
                            </div>
                            <div>
                                <label className="block text-xs font-black text-gray-400 uppercase mb-2">Headers (JSON 格式)</label>
                                <textarea
                                    value={formData.headers}
                                    onChange={e => setFormData({ ...formData, headers: e.target.value })}
                                    className="w-full px-5 py-3 bg-gray-50 border border-gray-200 rounded-2xl outline-none focus:border-indigo-500 font-mono text-sm h-24 resize-none"
                                    placeholder='{"Authorization": "Bearer ..."}'
                                />
                            </div>
                            <div>
                                <label className="block text-xs font-black text-gray-400 uppercase mb-2">描述</label>
                                <textarea
                                    value={formData.description}
                                    onChange={e => setFormData({ ...formData, description: e.target.value })}
                                    className="w-full px-5 py-3 bg-gray-50 border border-gray-200 rounded-2xl outline-none focus:border-indigo-500 font-bold h-24 resize-none"
                                />
                            </div>
                        </div>
                        <div className="p-8 border-t border-gray-100 flex justify-end gap-4">
                            <button onClick={() => setShowForm(false)} className="px-8 py-3 text-gray-500 font-bold">取消</button>
                            <button onClick={handleSave} className="px-10 py-3 bg-indigo-600 text-white rounded-2xl font-black shadow-lg">确认保存</button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default KnowledgeBaseManager;

