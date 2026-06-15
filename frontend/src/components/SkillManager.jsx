import React, { useState, useEffect, useCallback } from 'react';
import { Icons } from './Icons';
import { api } from '../services/api';

const CATEGORIES = ['sql', 'report', 'chart', 'general'];
const SCOPE_TYPES = ['global', 'datasource'];

const SkillManager = ({ showAlert }) => {
    const [skills, setSkills] = useState([]);
    const [loading, setLoading] = useState(true);
    const [editingSkill, setEditingSkill] = useState(null);
    const [isCreating, setIsCreating] = useState(false);

    // 表单状态
    const [formName, setFormName] = useState('');
    const [formDesc, setFormDesc] = useState('');
    const [formInstructions, setFormInstructions] = useState('');
    const [formCategory, setFormCategory] = useState('general');
    const [formPriority, setFormPriority] = useState(100);
    const [formScopeType, setFormScopeType] = useState('global');

    const loadSkills = useCallback(async () => {
        try {
            setLoading(true);
            const res = await api.listSkills();
            setSkills(res.skills || []);
        } catch (e) {
            showAlert?.('加载技能列表失败: ' + e.message, '错误', 'error');
        } finally {
            setLoading(false);
        }
    }, [showAlert]);

    useEffect(() => { loadSkills(); }, [loadSkills]);

    const resetForm = () => {
        setFormName('');
        setFormDesc('');
        setFormInstructions('');
        setFormCategory('general');
        setFormPriority(100);
        setFormScopeType('global');
        setEditingSkill(null);
        setIsCreating(false);
    };

    const openEdit = (skill) => {
        setEditingSkill(skill);
        setFormName(skill.name);
        setFormDesc(skill.description || '');
        setFormInstructions(skill.instructions || '');
        setFormCategory(skill.category || 'general');
        setFormPriority(skill.priority ?? 100);
        setFormScopeType(skill.scope_type || 'global');
        setIsCreating(false);
    };

    const openCreate = () => {
        resetForm();
        setIsCreating(true);
    };

    const handleSave = async () => {
        if (!formName.trim()) {
            showAlert?.('请输入技能名称', '提示', 'warning');
            return;
        }
        if (!formInstructions.trim()) {
            showAlert?.('请输入技能指令内容', '提示', 'warning');
            return;
        }

        const payload = {
            name: formName.trim(),
            description: formDesc.trim(),
            instructions: formInstructions,
            category: formCategory,
            priority: formPriority,
            scope_type: formScopeType,
        };

        try {
            if (editingSkill) {
                await api.updateSkill(editingSkill.id, payload);
                showAlert?.('技能已更新', '成功', 'success');
            } else {
                await api.createSkill(payload);
                showAlert?.('技能已创建', '成功', 'success');
            }
            resetForm();
            loadSkills();
        } catch (e) {
            showAlert?.(e.message || '保存失败', '错误', 'error');
        }
    };

    const handleDelete = async (skill) => {
        if (skill.is_builtin) {
            showAlert?.('内置技能不可删除', '提示', 'warning');
            return;
        }
        if (!window.confirm(`确定删除技能「${skill.name}」？`)) return;
        try {
            await api.deleteSkill(skill.id);
            showAlert?.('技能已删除', '成功', 'success');
            loadSkills();
        } catch (e) {
            showAlert?.(e.message || '删除失败', '错误', 'error');
        }
    };

    const handleToggle = async (skill) => {
        try {
            await api.toggleSkill(skill.id);
            loadSkills();
        } catch (e) {
            showAlert?.(e.message || '切换失败', '错误', 'error');
        }
    };

    const showForm = isCreating || editingSkill;

    return (
        <div className="flex-1 flex flex-col bg-[#f8fafc] overflow-hidden">
            {/* Header */}
            <div className="h-16 bg-white/80 backdrop-blur border-b border-gray-200/60 flex items-center justify-between px-8 shadow-sm">
                <div className="flex items-center gap-3">
                    <div className="p-1.5 rounded-lg bg-purple-100 text-purple-600">
                        <Icons.Terminal className="w-5 h-5" />
                    </div>
                    <h2 className="text-lg font-bold text-gray-800">技能管理</h2>
                    <span className="text-sm text-gray-400">({skills.length})</span>
                </div>
                {!showForm && (
                    <button
                        onClick={openCreate}
                        className="px-4 py-2 bg-purple-600 text-white rounded-xl text-sm font-medium hover:bg-purple-700 transition-colors flex items-center gap-2"
                    >
                        <span>+</span> 新建技能
                    </button>
                )}
            </div>

            <div className="flex-1 overflow-auto p-6">
                {showForm ? (
                    /* 编辑/创建表单 */
                    <div className="max-w-3xl mx-auto bg-white rounded-2xl shadow-lg border border-gray-200 p-8">
                        <h3 className="text-lg font-bold text-gray-800 mb-6">
                            {editingSkill ? '编辑技能' : '新建技能'}
                        </h3>

                        <div className="space-y-5">
                            {/* 名称 */}
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">名称 <span className="text-red-500">*</span></label>
                                <input
                                    type="text"
                                    value={formName}
                                    onChange={(e) => setFormName(e.target.value)}
                                    disabled={!!editingSkill}
                                    className="w-full px-4 py-2.5 border border-gray-200 rounded-xl focus:ring-2 focus:ring-purple-500 outline-none text-sm disabled:bg-gray-50 disabled:text-gray-500"
                                    placeholder="例如：sql_safety_rules"
                                />
                            </div>

                            {/* 描述 */}
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">描述</label>
                                <input
                                    type="text"
                                    value={formDesc}
                                    onChange={(e) => setFormDesc(e.target.value)}
                                    className="w-full px-4 py-2.5 border border-gray-200 rounded-xl focus:ring-2 focus:ring-purple-500 outline-none text-sm"
                                    placeholder="技能用途简要说明"
                                />
                            </div>

                            {/* 分类 + 优先级 */}
                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-1">分类</label>
                                    <select
                                        value={formCategory}
                                        onChange={(e) => setFormCategory(e.target.value)}
                                        className="w-full px-4 py-2.5 border border-gray-200 rounded-xl focus:ring-2 focus:ring-purple-500 outline-none text-sm bg-white"
                                    >
                                        {CATEGORIES.map(c => <option key={c} value={c}>{c}</option>)}
                                    </select>
                                </div>
                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-1">优先级</label>
                                    <input
                                        type="number"
                                        value={formPriority}
                                        onChange={(e) => setFormPriority(Number(e.target.value))}
                                        className="w-full px-4 py-2.5 border border-gray-200 rounded-xl focus:ring-2 focus:ring-purple-500 outline-none text-sm"
                                        min={0}
                                        max={999}
                                    />
                                </div>
                            </div>

                            {/* 作用范围 */}
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">作用范围</label>
                                <select
                                    value={formScopeType}
                                    onChange={(e) => setFormScopeType(e.target.value)}
                                    className="w-full px-4 py-2.5 border border-gray-200 rounded-xl focus:ring-2 focus:ring-purple-500 outline-none text-sm bg-white"
                                >
                                    {SCOPE_TYPES.map(s => <option key={s} value={s}>{s === 'global' ? '全局' : '指定数据源'}</option>)}
                                </select>
                            </div>

                            {/* 指令内容 (textarea) */}
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">
                                    指令内容 <span className="text-red-500">*</span>
                                    <span className="text-gray-400 font-normal ml-2">（将注入到 Agent 的系统提示词中）</span>
                                </label>
                                <textarea
                                    value={formInstructions}
                                    onChange={(e) => setFormInstructions(e.target.value)}
                                    rows={16}
                                    className="w-full px-4 py-3 border border-gray-200 rounded-xl focus:ring-2 focus:ring-purple-500 outline-none text-sm font-mono resize-y leading-relaxed"
                                    placeholder="输入技能的指令内容，例如：&#10;- 所有查询必须包含 LIMIT 限制&#10;- 禁止使用 DELETE/UPDATE 语句&#10;- 日期范围默认限制在最近 90 天"
                                />
                            </div>
                        </div>

                        {/* 按钮 */}
                        <div className="flex justify-end gap-3 mt-8 pt-6 border-t border-gray-100">
                            <button
                                onClick={resetForm}
                                className="px-5 py-2.5 text-sm text-gray-600 hover:bg-gray-100 rounded-xl transition-colors"
                            >
                                取消
                            </button>
                            <button
                                onClick={handleSave}
                                className="px-5 py-2.5 bg-purple-600 text-white text-sm font-medium rounded-xl hover:bg-purple-700 transition-colors"
                            >
                                {editingSkill ? '保存修改' : '创建技能'}
                            </button>
                        </div>
                    </div>
                ) : loading ? (
                    <div className="flex items-center justify-center py-20">
                        <div className="animate-spin w-8 h-8 border-3 border-purple-500 border-t-transparent rounded-full"></div>
                    </div>
                ) : (
                    /* 技能列表 */
                    <div className="max-w-4xl mx-auto space-y-3">
                        {skills.length === 0 && (
                            <div className="text-center py-16 text-gray-400">
                                <Icons.Terminal className="w-12 h-12 mx-auto mb-3 opacity-30" />
                                <p>暂无技能，点击右上角新建</p>
                            </div>
                        )}
                        {skills.map((skill) => (
                            <div
                                key={skill.id}
                                className={`bg-white rounded-xl border p-5 shadow-sm hover:shadow-md transition-shadow ${skill.is_active ? 'border-gray-200' : 'border-gray-100 opacity-60'}`}
                            >
                                <div className="flex items-start justify-between gap-4">
                                    <div className="flex-1 min-w-0">
                                        <div className="flex items-center gap-2 mb-1">
                                            <h4 className="font-bold text-gray-800 truncate">{skill.name}</h4>
                                            <span className={`text-[10px] px-1.5 py-0.5 rounded-full font-medium ${
                                                skill.category === 'sql' ? 'bg-blue-100 text-blue-600' :
                                                skill.category === 'chart' ? 'bg-green-100 text-green-600' :
                                                skill.category === 'report' ? 'bg-amber-100 text-amber-600' :
                                                'bg-gray-100 text-gray-500'
                                            }`}>
                                                {skill.category || 'general'}
                                            </span>
                                            {skill.is_builtin && (
                                                <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-purple-100 text-purple-600 font-medium">内置</span>
                                            )}
                                        </div>
                                        {skill.description && (
                                            <p className="text-sm text-gray-500 mb-2">{skill.description}</p>
                                        )}
                                        <pre className="text-xs text-gray-400 font-mono whitespace-pre-wrap line-clamp-2 max-h-10 overflow-hidden">
                                            {skill.instructions}
                                        </pre>
                                    </div>

                                    <div className="flex items-center gap-2 flex-shrink-0">
                                        {/* Toggle */}
                                        <button
                                            onClick={() => handleToggle(skill)}
                                            className={`relative w-10 h-5 rounded-full transition-colors ${skill.is_active ? 'bg-green-500' : 'bg-gray-300'}`}
                                            title={skill.is_active ? '已启用' : '已禁用'}
                                        >
                                            <span className={`absolute top-0.5 w-4 h-4 rounded-full bg-white shadow transition-transform ${skill.is_active ? 'left-5' : 'left-0.5'}`} />
                                        </button>
                                        {/* Edit */}
                                        <button
                                            onClick={() => openEdit(skill)}
                                            className="p-1.5 text-gray-400 hover:text-purple-600 hover:bg-purple-50 rounded-lg transition-colors"
                                            title="编辑"
                                        >
                                            <Icons.Edit className="w-4 h-4" />
                                        </button>
                                        {/* Delete */}
                                        {!skill.is_builtin && (
                                            <button
                                                onClick={() => handleDelete(skill)}
                                                className="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                                                title="删除"
                                            >
                                                <Icons.X className="w-4 h-4" />
                                            </button>
                                        )}
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
};

export default SkillManager;
