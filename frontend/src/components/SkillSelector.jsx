import React, { useState, useEffect, useRef } from 'react';
import { api } from '../services/api';

/**
 * SkillSelector — 对话输入区的技能选择器
 *
 * @param {Array<number>|null} selectedIds  已选技能 ID 列表，null 表示"全部"
 * @param {Function} onChange  选择变化回调 (ids: number[]|null) => void
 * @param {Function} showAlert
 */
const SkillSelector = ({ selectedIds, onChange, showAlert }) => {
    const [open, setOpen] = useState(false);
    const [skills, setSkills] = useState([]);
    const [loading, setLoading] = useState(false);
    const panelRef = useRef(null);

    // 加载可用技能列表
    useEffect(() => {
        if (!open) return;
        const load = async () => {
            setLoading(true);
            try {
                const res = await api.listSkills();
                if (res.success) setSkills(res.skills || []);
            } catch (e) {
                console.error('加载技能失败:', e);
            } finally {
                setLoading(false);
            }
        };
        load();
    }, [open]);

    // 点击外部关闭
    useEffect(() => {
        if (!open) return;
        const handler = (e) => {
            if (panelRef.current && !panelRef.current.contains(e.target)) {
                setOpen(false);
            }
        };
        document.addEventListener('mousedown', handler);
        return () => document.removeEventListener('mousedown', handler);
    }, [open]);

    const activeSkills = skills.filter(s => s.is_active);
    const isAll = selectedIds === null;
    const selectedCount = isAll ? activeSkills.length : (selectedIds || []).length;

    const toggleSkill = (skillId) => {
        if (isAll) {
            // 从"全部"切换到手动选择：取消当前这一个
            const newIds = activeSkills.filter(s => s.id !== skillId).map(s => s.id);
            onChange(newIds);
        } else {
            const current = selectedIds || [];
            if (current.includes(skillId)) {
                onChange(current.filter(id => id !== skillId));
            } else {
                onChange([...current, skillId]);
            }
        }
    };

    const selectAll = () => {
        onChange(null); // null = 使用全部激活技能
    };

    const clearAll = () => {
        onChange([]); // 空数组 = 不使用任何技能
    };

    const isChecked = (skillId) => {
        if (isAll) return true;
        return (selectedIds || []).includes(skillId);
    };

    const label = isAll ? '全部技能' : selectedCount > 0 ? `${selectedCount} 个技能` : '无技能';

    return (
        <div className="relative" ref={panelRef}>
            <button
                onClick={() => setOpen(!open)}
                disabled={loading}
                className={`flex items-center gap-1.5 px-3 py-1 rounded-lg text-[11px] font-bold transition-all border ${
                    selectedCount > 0 && !isAll
                        ? 'bg-indigo-50 border-indigo-200 text-indigo-600 shadow-sm'
                        : selectedCount === 0
                            ? 'bg-gray-50 border-gray-100 text-gray-400'
                            : 'bg-blue-50 border-blue-200 text-blue-600 shadow-sm'
                }`}
                title="选择本次对话使用的技能"
            >
                <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                </svg>
                {label}
            </button>

            {open && (
                <div className="absolute bottom-full left-0 mb-2 w-64 bg-white rounded-xl border border-gray-200 shadow-xl z-50 overflow-hidden animate-fade-in">
                    {/* Header */}
                    <div className="px-3 py-2 bg-gray-50 border-b border-gray-100">
                        <div className="text-[11px] font-bold text-gray-600">选择技能</div>
                        <div className="text-[9px] text-gray-400 mt-0.5">选择本次对话注入的技能规则</div>
                    </div>

                    {loading ? (
                        <div className="p-4 text-center text-xs text-gray-400">加载中...</div>
                    ) : activeSkills.length === 0 ? (
                        <div className="p-4 text-center text-xs text-gray-400">
                            暂无激活技能，请先在"技能管理"中创建并启用
                        </div>
                    ) : (
                        <>
                            {/* Quick actions */}
                            <div className="flex gap-1 px-3 py-2 border-b border-gray-50">
                                <button
                                    onClick={selectAll}
                                    className={`px-2 py-0.5 rounded text-[10px] font-bold transition-all ${
                                        isAll ? 'bg-blue-100 text-blue-600' : 'text-gray-500 hover:bg-gray-100'
                                    }`}
                                >
                                    全选
                                </button>
                                <button
                                    onClick={clearAll}
                                    className={`px-2 py-0.5 rounded text-[10px] font-bold transition-all ${
                                        selectedCount === 0 && !isAll ? 'bg-gray-200 text-gray-600' : 'text-gray-500 hover:bg-gray-100'
                                    }`}
                                >
                                    清空
                                </button>
                            </div>

                            {/* Skill list */}
                            <div className="max-h-48 overflow-y-auto p-2 space-y-1">
                                {activeSkills.map(skill => (
                                    <label
                                        key={skill.id}
                                        className={`flex items-start gap-2 p-2 rounded-lg cursor-pointer transition-all ${
                                            isChecked(skill.id) ? 'bg-indigo-50' : 'hover:bg-gray-50'
                                        }`}
                                    >
                                        <input
                                            type="checkbox"
                                            checked={isChecked(skill.id)}
                                            onChange={() => toggleSkill(skill.id)}
                                            className="mt-0.5 rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
                                        />
                                        <div className="flex-1 min-w-0">
                                            <div className="text-[11px] font-bold text-gray-700 truncate">{skill.name}</div>
                                            <div className="text-[9px] text-gray-400 truncate mt-0.5">{skill.description}</div>
                                        </div>
                                        <span className="text-[8px] font-bold text-gray-300 uppercase mt-0.5">{skill.category}</span>
                                    </label>
                                ))}
                            </div>
                        </>
                    )}
                </div>
            )}
        </div>
    );
};

export default SkillSelector;
