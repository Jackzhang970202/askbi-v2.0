import React, { useState, useEffect, useCallback } from 'react';
import { Icons } from './Icons';
import { api } from '../services/api';

const AGENT_DISPLAY = {
    bi_sql_agent:      { icon: '🗄️', color: 'blue' },
    bi_report_agent:   { icon: '📊', color: 'indigo' },
    bi_chart_agent:    { icon: '📈', color: 'green' },
    askexcel_code_agent:   { icon: '🐍', color: 'emerald' },
    askexcel_report_agent: { icon: '📋', color: 'teal' },
    askexcel_chart_agent:  { icon: '📉', color: 'cyan' },
};

const AgentManager = ({ showAlert }) => {
    const [agents, setAgents] = useState([]);
    const [skills, setSkills] = useState([]);
    const [loading, setLoading] = useState(true);
    const [editingAgent, setEditingAgent] = useState(null);
    const [showCreateForm, setShowCreateForm] = useState(false);

    // 表单状态
    const [formInstructions, setFormInstructions] = useState('');
    const [formDescription, setFormDescription] = useState('');
    const [formModel, setFormModel] = useState('');
    const [formTemperature, setFormTemperature] = useState(0.1);
    const [formBoundSkills, setFormBoundSkills] = useState([]);

    // 新建智能体表单
    const [newName, setNewName] = useState('');
    const [newDisplayName, setNewDisplayName] = useState('');
    const [newInstructions, setNewInstructions] = useState('');
    const [newRoleDesc, setNewRoleDesc] = useState('');
    const [newCapabilities, setNewCapabilities] = useState('');
    const [creating, setCreating] = useState(false);

    const loadData = useCallback(async () => {
        try {
            setLoading(true);
            const [agentsRes, skillsRes] = await Promise.all([
                api.listAgents(),
                api.listSkills(),
            ]);
            setAgents(agentsRes.agents || []);
            setSkills(skillsRes.skills || []);
        } catch (e) {
            showAlert?.('加载数据失败: ' + e.message, '错误', 'error');
        } finally {
            setLoading(false);
        }
    }, [showAlert]);

    useEffect(() => { loadData(); }, [loadData]);

    const openEdit = (agent) => {
        setEditingAgent(agent);
        setFormInstructions(agent.base_instructions || '');
        setFormDescription(agent.description || '');
        const mc = agent.model_config || {};
        setFormModel(mc.model || '');
        setFormTemperature(mc.temperature ?? 0.1);
        setFormBoundSkills(agent.bound_skills || []);
    };

    const closeEdit = () => {
        setEditingAgent(null);
        setFormInstructions('');
        setFormDescription('');
        setFormModel('');
        setFormTemperature(0.1);
        setFormBoundSkills([]);
    };

    const handleSave = async () => {
        if (!editingAgent) return;
        try {
            const payload = {
                description: formDescription,
                base_instructions: formInstructions,
                model_config: {
                    model: formModel || undefined,
                    temperature: formTemperature,
                },
            };
            await api.updateAgent(editingAgent.id, payload);

            // 更新技能绑定
            const currentSkills = editingAgent.bound_skills || [];
            const skillsChanged = JSON.stringify([...currentSkills].sort()) !== JSON.stringify([...formBoundSkills].sort());
            if (skillsChanged) {
                await api.bindSkillsToAgent(editingAgent.id, formBoundSkills);
            }

            showAlert?.('智能体已更新', '成功', 'success');
            closeEdit();
            loadData();
        } catch (e) {
            showAlert?.(e.message || '保存失败', '错误', 'error');
        }
    };

    const handleReset = async (agent) => {
        if (!window.confirm(`确定将「${agent.display_name || agent.name}」重置为默认配置？`)) return;
        try {
            const res = await fetch(`/agents/${encodeURIComponent(agent.name)}/reset`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${localStorage.getItem('askbi_token')}`,
                },
            });
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            showAlert?.('已重置为默认配置', '成功', 'success');
            loadData();
        } catch (e) {
            showAlert?.(e.message || '重置失败', '错误', 'error');
        }
    };

    const toggleSkill = (skillId) => {
        setFormBoundSkills(prev =>
            prev.includes(skillId) ? prev.filter(id => id !== skillId) : [...prev, skillId]
        );
    };

    const activeSkills = skills.filter(s => s.is_active);

    const resetCreateForm = () => {
        setNewName('');
        setNewDisplayName('');
        setNewInstructions('');
        setNewRoleDesc('');
        setNewCapabilities('');
        setShowCreateForm(false);
    };

    const handleCreate = async () => {
        if (!newName.trim() || !newDisplayName.trim() || !newInstructions.trim()) {
            showAlert?.('名称、显示名称和基础指令为必填项', '提示', 'error');
            return;
        }
        setCreating(true);
        try {
            const payload = {
                name: newName.trim(),
                display_name: newDisplayName.trim(),
                base_instructions: newInstructions.trim(),
            };
            if (newRoleDesc.trim()) payload.role_description = newRoleDesc.trim();
            if (newCapabilities.trim()) {
                payload.capabilities = newCapabilities.split(',').map(s => s.trim()).filter(Boolean);
            }
            const res = await api.createCustomAgent(payload);
            if (res.success) {
                showAlert?.('自定义智能体已创建', '成功', 'success');
                resetCreateForm();
                loadData();
            } else {
                showAlert?.(res.error || '创建失败', '错误', 'error');
            }
        } catch (e) {
            showAlert?.(e.message || '创建失败', '错误', 'error');
        } finally {
            setCreating(false);
        }
    };

    return (
        <div className="flex-1 flex flex-col bg-[#f8fafc] overflow-hidden">
            {/* Header */}
            <div className="h-16 bg-white/80 backdrop-blur border-b border-gray-200/60 flex items-center justify-between px-8 shadow-sm">
                <div className="flex items-center gap-3">
                    <div className="p-1.5 rounded-lg bg-indigo-100 text-indigo-600">
                        <Icons.Bot className="w-5 h-5" />
                    </div>
                    <h2 className="text-lg font-bold text-gray-800">智能体管理</h2>
                    <span className="text-sm text-gray-400">({agents.length})</span>
                </div>
                {!editingAgent && !showCreateForm && (
                    <button
                        onClick={() => setShowCreateForm(true)}
                        className="px-4 py-2 bg-indigo-600 text-white text-sm font-medium rounded-xl hover:bg-indigo-700 transition-all flex items-center gap-2"
                    >
                        <Icons.Plus className="w-4 h-4" />
                        新建智能体
                    </button>
                )}
            </div>

            <div className="flex-1 overflow-auto p-6">
                {showCreateForm ? (
                    /* 新建智能体表单 */
                    <div className="max-w-3xl mx-auto bg-white rounded-2xl shadow-lg border border-gray-200 p-8">
                        <div className="flex items-center gap-3 mb-6">
                            <div className="w-10 h-10 rounded-xl bg-indigo-100 text-indigo-600 flex items-center justify-center">
                                <Icons.Plus className="w-5 h-5" />
                            </div>
                            <div>
                                <h3 className="text-lg font-bold text-gray-800">新建自定义智能体</h3>
                                <p className="text-sm text-gray-500">创建后可在团队编排中作为成员使用</p>
                            </div>
                        </div>

                        <div className="space-y-5">
                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-1">
                                        标识名 <span className="text-red-400">*</span>
                                        <span className="text-gray-400 font-normal ml-1">(英文，如 data_analyst)</span>
                                    </label>
                                    <input
                                        type="text"
                                        value={newName}
                                        onChange={(e) => setNewName(e.target.value)}
                                        className="w-full px-4 py-2.5 border border-gray-200 rounded-xl focus:ring-2 focus:ring-indigo-500 outline-none text-sm"
                                        placeholder="data_analyst"
                                    />
                                </div>
                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-1">
                                        显示名称 <span className="text-red-400">*</span>
                                    </label>
                                    <input
                                        type="text"
                                        value={newDisplayName}
                                        onChange={(e) => setNewDisplayName(e.target.value)}
                                        className="w-full px-4 py-2.5 border border-gray-200 rounded-xl focus:ring-2 focus:ring-indigo-500 outline-none text-sm"
                                        placeholder="数据分析专家"
                                    />
                                </div>
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">
                                    角色描述
                                    <span className="text-gray-400 font-normal ml-2">(一句话说明该智能体的角色定位)</span>
                                </label>
                                <input
                                    type="text"
                                    value={newRoleDesc}
                                    onChange={(e) => setNewRoleDesc(e.target.value)}
                                    className="w-full px-4 py-2.5 border border-gray-200 rounded-xl focus:ring-2 focus:ring-indigo-500 outline-none text-sm"
                                    placeholder="擅长从数据中提取关键洞察并生成分析报告"
                                />
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">
                                    基础指令 <span className="text-red-400">*</span>
                                    <span className="text-gray-400 font-normal ml-2">(系统提示词)</span>
                                </label>
                                <textarea
                                    value={newInstructions}
                                    onChange={(e) => setNewInstructions(e.target.value)}
                                    rows={10}
                                    className="w-full px-4 py-3 border border-gray-200 rounded-xl focus:ring-2 focus:ring-indigo-500 outline-none text-sm font-mono resize-y leading-relaxed"
                                    placeholder="你是一个专业的数据分析专家，擅长..."
                                />
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">
                                    能力标签
                                    <span className="text-gray-400 font-normal ml-2">(逗号分隔，如: SQL, 数据清洗, 可视化)</span>
                                </label>
                                <input
                                    type="text"
                                    value={newCapabilities}
                                    onChange={(e) => setNewCapabilities(e.target.value)}
                                    className="w-full px-4 py-2.5 border border-gray-200 rounded-xl focus:ring-2 focus:ring-indigo-500 outline-none text-sm"
                                    placeholder="SQL, 数据分析, 可视化"
                                />
                            </div>
                        </div>

                        <div className="flex justify-end mt-8 pt-6 border-t border-gray-100 gap-3">
                            <button
                                onClick={resetCreateForm}
                                className="px-5 py-2.5 text-sm text-gray-600 hover:bg-gray-100 rounded-xl transition-colors"
                            >
                                取消
                            </button>
                            <button
                                onClick={handleCreate}
                                disabled={creating}
                                className="px-5 py-2.5 bg-indigo-600 text-white text-sm font-medium rounded-xl hover:bg-indigo-700 transition-colors disabled:opacity-50"
                            >
                                {creating ? '创建中...' : '创建智能体'}
                            </button>
                        </div>
                    </div>
                ) : editingAgent ? (
                    /* 编辑面板 */
                    <div className="max-w-3xl mx-auto bg-white rounded-2xl shadow-lg border border-gray-200 p-8">
                        <div className="flex items-center gap-3 mb-6">
                            <span className="text-2xl">{AGENT_DISPLAY[editingAgent.name]?.icon || '🤖'}</span>
                            <div>
                                <h3 className="text-lg font-bold text-gray-800">{editingAgent.display_name || editingAgent.name}</h3>
                                <p className="text-sm text-gray-500">{editingAgent.name}</p>
                            </div>
                        </div>

                        <div className="space-y-5">
                            {/* 描述 */}
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">描述</label>
                                <input
                                    type="text"
                                    value={formDescription}
                                    onChange={(e) => setFormDescription(e.target.value)}
                                    className="w-full px-4 py-2.5 border border-gray-200 rounded-xl focus:ring-2 focus:ring-indigo-500 outline-none text-sm"
                                />
                            </div>

                            {/* 基础指令 */}
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">
                                    基础指令
                                    <span className="text-gray-400 font-normal ml-2">（Agent 的系统提示词）</span>
                                </label>
                                <textarea
                                    value={formInstructions}
                                    onChange={(e) => setFormInstructions(e.target.value)}
                                    rows={14}
                                    className="w-full px-4 py-3 border border-gray-200 rounded-xl focus:ring-2 focus:ring-indigo-500 outline-none text-sm font-mono resize-y leading-relaxed"
                                />
                            </div>

                            {/* 模型配置（当前不可用） */}
                            <div className="grid grid-cols-2 gap-4 opacity-50">
                                <div>
                                    <label className="block text-sm font-medium text-gray-400 mb-1">
                                        模型
                                        <span className="text-gray-300 font-normal ml-1">（暂不可用，使用全局 config.json）</span>
                                    </label>
                                    <input
                                        type="text"
                                        value={formModel}
                                        disabled
                                        className="w-full px-4 py-2.5 border border-gray-100 rounded-xl bg-gray-50 text-gray-400 text-sm cursor-not-allowed"
                                        placeholder="例如 qwen-plus"
                                    />
                                </div>
                                <div>
                                    <label className="block text-sm font-medium text-gray-400 mb-1">Temperature</label>
                                    <input
                                        type="number"
                                        step="0.1"
                                        min="0"
                                        max="2"
                                        value={formTemperature}
                                        disabled
                                        className="w-full px-4 py-2.5 border border-gray-100 rounded-xl bg-gray-50 text-gray-400 text-sm cursor-not-allowed"
                                    />
                                </div>
                            </div>

                            {/* 技能绑定 */}
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-2">
                                    绑定技能
                                    <span className="text-gray-400 font-normal ml-2">（选中的技能会自动注入到系统提示词）</span>
                                </label>
                                {activeSkills.length === 0 ? (
                                    <p className="text-sm text-gray-400 italic">暂无可用技能，请先在技能管理中创建</p>
                                ) : (
                                    <div className="space-y-2 max-h-48 overflow-y-auto border border-gray-100 rounded-xl p-3">
                                        {activeSkills.map(skill => (
                                            <label
                                                key={skill.id}
                                                className="flex items-center gap-3 p-2 rounded-lg hover:bg-gray-50 cursor-pointer"
                                            >
                                                <input
                                                    type="checkbox"
                                                    checked={formBoundSkills.includes(skill.id)}
                                                    onChange={() => toggleSkill(skill.id)}
                                                    className="w-4 h-4 text-indigo-600 rounded focus:ring-indigo-500"
                                                />
                                                <div className="flex-1 min-w-0">
                                                    <span className="text-sm font-medium text-gray-700">{skill.name}</span>
                                                    {skill.description && (
                                                        <span className="text-xs text-gray-400 ml-2">{skill.description}</span>
                                                    )}
                                                </div>
                                                <span className={`text-[10px] px-1.5 py-0.5 rounded-full ${
                                                    skill.category === 'sql' ? 'bg-blue-100 text-blue-600' :
                                                    skill.category === 'chart' ? 'bg-green-100 text-green-600' :
                                                    skill.category === 'report' ? 'bg-amber-100 text-amber-600' :
                                                    'bg-gray-100 text-gray-500'
                                                }`}>
                                                    {skill.category || 'general'}
                                                </span>
                                            </label>
                                        ))}
                                    </div>
                                )}
                            </div>
                        </div>

                        {/* 按钮 */}
                        <div className="flex justify-between mt-8 pt-6 border-t border-gray-100">
                            <button
                                onClick={() => handleReset(editingAgent)}
                                className="px-4 py-2.5 text-sm text-amber-600 hover:bg-amber-50 rounded-xl transition-colors border border-amber-200"
                            >
                                恢复默认
                            </button>
                            <div className="flex gap-3">
                                <button
                                    onClick={closeEdit}
                                    className="px-5 py-2.5 text-sm text-gray-600 hover:bg-gray-100 rounded-xl transition-colors"
                                >
                                    取消
                                </button>
                                <button
                                    onClick={handleSave}
                                    className="px-5 py-2.5 bg-indigo-600 text-white text-sm font-medium rounded-xl hover:bg-indigo-700 transition-colors"
                                >
                                    保存修改
                                </button>
                            </div>
                        </div>
                    </div>
                ) : loading ? (
                    <div className="flex items-center justify-center py-20">
                        <div className="animate-spin w-8 h-8 border-3 border-indigo-500 border-t-transparent rounded-full"></div>
                    </div>
                ) : (
                    /* 智能体列表 */
                    <div className="max-w-4xl mx-auto grid grid-cols-1 md:grid-cols-2 gap-4">
                        {agents.map(agent => {
                            const meta = AGENT_DISPLAY[agent.name] || { icon: '🤖', color: 'gray' };
                            const boundCount = (agent.bound_skills || []).length;
                            return (
                                <div
                                    key={agent.id}
                                    onClick={() => openEdit(agent)}
                                    className={`bg-white rounded-xl border border-gray-200 p-5 shadow-sm hover:shadow-md hover:border-${meta.color}-300 transition-all cursor-pointer group`}
                                >
                                    <div className="flex items-start gap-3">
                                        <div className={`w-10 h-10 rounded-xl bg-${meta.color}-100 text-${meta.color}-600 flex items-center justify-center text-lg flex-shrink-0`}>
                                            {meta.icon}
                                        </div>
                                        <div className="flex-1 min-w-0">
                                            <div className="flex items-center gap-2 mb-1">
                                                <h4 className="font-bold text-gray-800 truncate">{agent.display_name || agent.name}</h4>
                                                {agent.is_builtin && (
                                                    <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-purple-100 text-purple-600 font-medium">内置</span>
                                                )}
                                            </div>
                                            <p className="text-xs text-gray-500 mb-2">{agent.name}</p>
                                            {agent.description && (
                                                <p className="text-sm text-gray-500 line-clamp-2">{agent.description}</p>
                                            )}
                                            <div className="flex items-center gap-3 mt-3 text-xs text-gray-400">
                                                <span>{boundCount} 个技能</span>
                                                <span>·</span>
                                                <span>{agent.model_config?.model || '全局模型'}</span>
                                            </div>
                                        </div>
                                        <div className="opacity-0 group-hover:opacity-100 transition-opacity">
                                            <Icons.ChevronRight className="w-5 h-5 text-gray-400" />
                                        </div>
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                )}
            </div>
        </div>
    );
};

export default AgentManager;
