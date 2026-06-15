import React, { useState, useEffect, useCallback } from 'react';
import { Icons } from './Icons';
import { api } from '../services/api';
import TeamEditor from './TeamEditor';

const MODE_LABELS = {
    coordinate: '协调模式',
    route: '路由模式',
    broadcast: '广播模式',
    tasks: '任务模式',
};

const MEMBER_TYPE_LABELS = {
    agent: '智能体',
    workflow: '工作流',
    sub_team: '子团队',
    custom_flow: '自定义流程',
};

const MEMBER_TYPE_COLORS = {
    agent: 'bg-blue-100 text-blue-700',
    workflow: 'bg-green-100 text-green-700',
    sub_team: 'bg-orange-100 text-orange-700',
    custom_flow: 'bg-purple-100 text-purple-700',
};

const WORKFLOWS = [
    { key: 'bi', name: 'BI 问数流程', desc: '自然语言 -> SQL -> 执行 -> 图表 -> 回答', needsDatasource: true },
    { key: 'excel', name: 'Excel 分析流程', desc: 'Excel 文件智能分析与可视化', needsDatasource: false },
];

const getMemberLabel = (m) =>
    m.role || m.ref_agent_name || m.ref_workflow || m.ref_custom_flow?.name || MEMBER_TYPE_LABELS[m.member_type] || m.member_key;

const MODES = [
    {
        key: 'coordinate',
        name: '协调模式',
        icon: '🎯',
        shortDesc: '领导按需调用多个成员协作完成',
        longDesc: '领导智能体分析用户问题，选择最合适的成员协作。可以调用多个成员，汇总结果后返回。',
        minMembers: 1,
        useCase: '复杂综合分析任务',
        flow: '用户提问 → 领导(决策) → 成员A/B → 领导(汇总) → 回答',
    },
    {
        key: 'route',
        name: '路由模式',
        icon: '🔀',
        shortDesc: '领导判断后只转交给一个成员',
        longDesc: '领导智能体判断问题属于哪个成员的专业领域，直接转交给该成员处理，结果直接返回。',
        minMembers: 2,
        useCase: '专业分工、单一领域',
        flow: '用户提问 → 领导(判断) → 成员A → 直接返回',
    },
    {
        key: 'broadcast',
        name: '广播模式',
        icon: '📡',
        shortDesc: '所有成员同时并行执行同一问题',
        longDesc: '所有成员同时收到同一问题，各自独立执行，领导汇总所有结果后返回。',
        minMembers: 1,
        useCase: '多角度对比分析',
        flow: '用户提问 → 成员A/B/C(并行) → 领导(汇总) → 回答',
    },
    {
        key: 'tasks',
        name: '任务模式',
        icon: '📋',
        shortDesc: '拆解目标为任务列表逐一分配',
        longDesc: '领导智能体将目标拆解为有序任务列表，每个任务分配给最合适的成员，按顺序执行。',
        minMembers: 1,
        useCase: '多步骤流水线任务',
        flow: '用户提问 → 领导(拆解) → 任务1→成员A → 任务2→成员B → 汇总',
    },
];

/* ── 步骤指示器 ── */
const StepIndicator = ({ current, total, labels }) => (
    <div className="flex items-center justify-center gap-2 mb-8">
        {Array.from({ length: total }, (_, i) => (
            <React.Fragment key={i}>
                <div className="flex items-center gap-2">
                    <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold transition-colors ${
                        i + 1 < current ? 'bg-cyan-600 text-white' :
                        i + 1 === current ? 'bg-cyan-600 text-white' :
                        'bg-gray-100 text-gray-400'
                    }`}>
                        {i + 1 < current ? '✓' : i + 1}
                    </div>
                    <span className={`text-xs font-medium hidden sm:inline ${
                        i + 1 <= current ? 'text-cyan-700' : 'text-gray-400'
                    }`}>{labels[i]}</span>
                </div>
                {i < total - 1 && (
                    <div className={`w-8 h-0.5 ${i + 1 < current ? 'bg-cyan-400' : 'bg-gray-200'}`} />
                )}
            </React.Fragment>
        ))}
    </div>
);

/* ── 数据流图 ── */
const DataFlowDiagram = ({ mode }) => {
    const m = MODES.find(x => x.key === mode);
    if (!m) return null;
    return (
        <div className="mt-4 p-3 bg-gray-50 rounded-xl border border-gray-100">
            <p className="text-xs text-gray-400 mb-1">数据流示意</p>
            <p className="text-sm font-mono text-gray-600">{m.flow}</p>
        </div>
    );
};

/* ── 成员类型专属面板 ── */
const AgentMemberPanel = ({ member, index, agents, allMembers, onUpdate }) => {
    const selected = agents.find(a => a.name === member.ref_agent_name);
    return (
        <div className="space-y-3">
            <div>
                <label className="block text-xs text-gray-500 mb-1">选择智能体 *</label>
                <select
                    value={member.ref_agent_name || ''}
                    onChange={e => onUpdate(index, 'ref_agent_name', e.target.value)}
                    className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-blue-400 outline-none"
                >
                    <option value="">-- 选择智能体 --</option>
                    {agents.map(a => (
                        <option key={a.name} value={a.name}>{a.display_name} ({a.name})</option>
                    ))}
                </select>
            </div>
            {selected && (
                <div className="p-3 bg-blue-50 rounded-lg border border-blue-100 text-xs space-y-1">
                    <p className="text-blue-700 font-medium">{selected.display_name}</p>
                    {selected.description && <p className="text-blue-600">{selected.description}</p>}
                    {selected.base_instructions && (
                        <p className="text-blue-500 truncate">指令: {selected.base_instructions}</p>
                    )}
                    {selected.bound_skills?.length > 0 && (
                        <p className="text-blue-500">技能: {selected.bound_skills.map(s => s.name || s).join(', ')}</p>
                    )}
                </div>
            )}
            <div className="grid grid-cols-2 gap-3">
                <div>
                    <label className="block text-xs text-gray-500 mb-1">角色名称</label>
                    <input type="text" value={member.role || ''} onChange={e => onUpdate(index, 'role', e.target.value)}
                        placeholder="如：SQL专家" className="w-full px-3 py-1.5 border border-gray-200 rounded-lg text-sm" />
                </div>
                <div>
                    <label className="block text-xs text-gray-500 mb-1">能力描述</label>
                    <input type="text" value={member.description || ''} onChange={e => onUpdate(index, 'description', e.target.value)}
                        placeholder="供领导参考的能力说明" className="w-full px-3 py-1.5 border border-gray-200 rounded-lg text-sm" />
                </div>
            </div>
            {allMembers.length > 1 && (
                <div>
                    <label className="block text-xs text-gray-500 mb-1">可委托给</label>
                    <div className="flex flex-wrap gap-2">
                        {allMembers.filter((_, i) => i !== index).map((m, i) => (
                            <label key={i} className="flex items-center gap-1.5 text-xs cursor-pointer">
                                <input type="checkbox"
                                    checked={(member.can_delegate_to || []).includes(m.member_key)}
                                    onChange={e => {
                                        const cur = member.can_delegate_to || [];
                                        onUpdate(index, 'can_delegate_to',
                                            e.target.checked ? [...cur, m.member_key] : cur.filter(k => k !== m.member_key));
                                    }}
                                    className="w-3.5 h-3.5 rounded text-blue-600" />
                                <span className="text-gray-600">{getMemberLabel(m)}</span>
                            </label>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
};

const WorkflowMemberPanel = ({ member, index, datasources, allMembers, onUpdate }) => {
    const wf = WORKFLOWS.find(w => w.key === member.ref_workflow);
    return (
        <div className="space-y-3">
            <div>
                <label className="block text-xs text-gray-500 mb-1">选择工作流 *</label>
                <div className="grid grid-cols-2 gap-2">
                    {WORKFLOWS.map(w => (
                        <button key={w.key} type="button"
                            onClick={() => onUpdate(index, 'ref_workflow', w.key)}
                            className={`p-3 rounded-lg border text-left transition-colors ${
                                member.ref_workflow === w.key
                                    ? 'border-green-400 bg-green-50'
                                    : 'border-gray-200 bg-white hover:border-green-200'
                            }`}>
                            <p className="text-sm font-medium text-gray-800">{w.name}</p>
                            <p className="text-xs text-gray-500 mt-0.5">{w.desc}</p>
                        </button>
                    ))}
                </div>
            </div>
            {wf?.needsDatasource && (
                <div>
                    <label className="block text-xs text-gray-500 mb-1">数据源 *</label>
                    <select
                        value={member.datasource_name || ''}
                        onChange={e => onUpdate(index, 'datasource_name', e.target.value)}
                        className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-green-400 outline-none"
                    >
                        <option value="">-- 选择数据源 --</option>
                        {datasources.map(ds => (
                            <option key={ds.name} value={ds.name}>{ds.name} ({ds.type})</option>
                        ))}
                    </select>
                    <p className="text-xs text-gray-400 mt-1">该工作流需要连接数据库执行查询</p>
                </div>
            )}
            <div className="grid grid-cols-2 gap-3">
                <div>
                    <label className="block text-xs text-gray-500 mb-1">角色名称</label>
                    <input type="text" value={member.role || ''} onChange={e => onUpdate(index, 'role', e.target.value)}
                        placeholder="如：数据查询" className="w-full px-3 py-1.5 border border-gray-200 rounded-lg text-sm" />
                </div>
                <div>
                    <label className="block text-xs text-gray-500 mb-1">能力描述</label>
                    <input type="text" value={member.description || ''} onChange={e => onUpdate(index, 'description', e.target.value)}
                        placeholder="供领导参考" className="w-full px-3 py-1.5 border border-gray-200 rounded-lg text-sm" />
                </div>
            </div>
            <div className="p-2.5 bg-green-50 rounded-lg border border-green-100 text-xs text-green-700">
                输入: 领导将用户问题传递给此工作流 → 输出: 工作流结果返回给领导汇总
            </div>
            {allMembers.length > 1 && (
                <div>
                    <label className="block text-xs text-gray-500 mb-1">可委托给</label>
                    <div className="flex flex-wrap gap-2">
                        {allMembers.filter((_, i) => i !== index).map((m, i) => (
                            <label key={i} className="flex items-center gap-1.5 text-xs cursor-pointer">
                                <input type="checkbox"
                                    checked={(member.can_delegate_to || []).includes(m.member_key)}
                                    onChange={e => {
                                        const cur = member.can_delegate_to || [];
                                        onUpdate(index, 'can_delegate_to',
                                            e.target.checked ? [...cur, m.member_key] : cur.filter(k => k !== m.member_key));
                                    }}
                                    className="w-3.5 h-3.5 rounded text-green-600" />
                                <span className="text-gray-600">{getMemberLabel(m)}</span>
                            </label>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
};

const SubTeamMemberPanel = ({ member, index, teams, editingTeam, allMembers, onUpdate }) => {
    const filteredTeams = teams.filter(t => !editingTeam || t.id !== editingTeam.id);
    const selected = filteredTeams.find(t => t.id === member.ref_team_id);
    return (
        <div className="space-y-3">
            <div>
                <label className="block text-xs text-gray-500 mb-1">选择子团队 *</label>
                <select
                    value={member.ref_team_id || ''}
                    onChange={e => onUpdate(index, 'ref_team_id', e.target.value ? parseInt(e.target.value) : null)}
                    className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:ring-2 focus:ring-orange-400 outline-none"
                >
                    <option value="">-- 选择团队 --</option>
                    {filteredTeams.map(t => (
                        <option key={t.id} value={t.id}>{t.name} ({MODE_LABELS[t.mode] || t.mode})</option>
                    ))}
                </select>
            </div>
            {selected && (
                <div className="p-3 bg-orange-50 rounded-lg border border-orange-100 text-xs space-y-1">
                    <p className="text-orange-700 font-medium">{selected.name}</p>
                    <p className="text-orange-600">模式: {MODE_LABELS[selected.mode]} | {selected.description || '无描述'}</p>
                </div>
            )}
            <div className="grid grid-cols-2 gap-3">
                <div>
                    <label className="block text-xs text-gray-500 mb-1">角色名称</label>
                    <input type="text" value={member.role || ''} onChange={e => onUpdate(index, 'role', e.target.value)}
                        placeholder="如：财务分析子团队" className="w-full px-3 py-1.5 border border-gray-200 rounded-lg text-sm" />
                </div>
                <div>
                    <label className="block text-xs text-gray-500 mb-1">能力描述</label>
                    <input type="text" value={member.description || ''} onChange={e => onUpdate(index, 'description', e.target.value)}
                        placeholder="供领导参考" className="w-full px-3 py-1.5 border border-gray-200 rounded-lg text-sm" />
                </div>
            </div>
            {allMembers.length > 1 && (
                <div>
                    <label className="block text-xs text-gray-500 mb-1">可委托给</label>
                    <div className="flex flex-wrap gap-2">
                        {allMembers.filter((_, i) => i !== index).map((m, i) => (
                            <label key={i} className="flex items-center gap-1.5 text-xs cursor-pointer">
                                <input type="checkbox"
                                    checked={(member.can_delegate_to || []).includes(m.member_key)}
                                    onChange={e => {
                                        const cur = member.can_delegate_to || [];
                                        onUpdate(index, 'can_delegate_to',
                                            e.target.checked ? [...cur, m.member_key] : cur.filter(k => k !== m.member_key));
                                    }}
                                    className="w-3.5 h-3.5 rounded text-orange-600" />
                                <span className="text-gray-600">{getMemberLabel(m)}</span>
                            </label>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
};

const CustomFlowMemberPanel = ({ member, index, agents, allMembers, onUpdate }) => {
    const flow = member.ref_custom_flow || { name: '', steps: [] };
    const updateFlow = (field, value) => onUpdate(index, 'ref_custom_flow', { ...flow, [field]: value });
    const updateStep = (si, field, value) => {
        const steps = [...flow.steps];
        steps[si] = { ...steps[si], [field]: value };
        updateFlow('steps', steps);
    };
    const addStep = () => updateFlow('steps', [...flow.steps, { ref_agent_name: '', instruction: '' }]);
    const removeStep = (si) => updateFlow('steps', flow.steps.filter((_, i) => i !== si));

    return (
        <div className="space-y-3">
            <div>
                <label className="block text-xs text-gray-500 mb-1">流程名称 *</label>
                <input type="text" value={flow.name} onChange={e => updateFlow('name', e.target.value)}
                    placeholder="如：数据清洗流程" className="w-full px-3 py-1.5 border border-gray-200 rounded-lg text-sm" />
            </div>
            <div>
                <div className="flex items-center justify-between mb-2">
                    <label className="text-xs text-gray-500">步骤列表</label>
                    <button type="button" onClick={addStep}
                        className="text-xs px-2 py-1 bg-purple-50 text-purple-700 rounded-lg hover:bg-purple-100 border border-purple-200">
                        + 添加步骤
                    </button>
                </div>
                {flow.steps.length === 0 ? (
                    <p className="text-xs text-gray-400 italic py-3 text-center border border-dashed border-gray-200 rounded-lg">
                        点击添加步骤，每步选择一个智能体执行
                    </p>
                ) : (
                    <div className="space-y-2">
                        {flow.steps.map((step, si) => (
                            <div key={si} className="flex items-start gap-2 p-2.5 bg-gray-50 rounded-lg border border-gray-100">
                                <span className="text-xs font-bold text-purple-600 mt-1.5 w-5 flex-shrink-0">{si + 1}</span>
                                <div className="flex-1 space-y-1.5">
                                    <select value={step.ref_agent_name || ''}
                                        onChange={e => updateStep(si, 'ref_agent_name', e.target.value)}
                                        className="w-full px-2 py-1.5 border border-gray-200 rounded-lg text-xs">
                                        <option value="">-- 选择智能体 --</option>
                                        {agents.map(a => (
                                            <option key={a.name} value={a.name}>{a.display_name}</option>
                                        ))}
                                    </select>
                                    <input type="text" value={step.instruction || ''}
                                        onChange={e => updateStep(si, 'instruction', e.target.value)}
                                        placeholder="该步骤的指令说明"
                                        className="w-full px-2 py-1.5 border border-gray-200 rounded-lg text-xs" />
                                </div>
                                <button type="button" onClick={() => removeStep(si)}
                                    className="text-red-400 hover:text-red-600 text-xs mt-1">x</button>
                            </div>
                        ))}
                    </div>
                )}
            </div>
            <div className="grid grid-cols-2 gap-3">
                <div>
                    <label className="block text-xs text-gray-500 mb-1">角色名称</label>
                    <input type="text" value={member.role || ''} onChange={e => onUpdate(index, 'role', e.target.value)}
                        placeholder="如：数据清洗" className="w-full px-3 py-1.5 border border-gray-200 rounded-lg text-sm" />
                </div>
                <div>
                    <label className="block text-xs text-gray-500 mb-1">能力描述</label>
                    <input type="text" value={member.description || ''} onChange={e => onUpdate(index, 'description', e.target.value)}
                        placeholder="供领导参考" className="w-full px-3 py-1.5 border border-gray-200 rounded-lg text-sm" />
                </div>
            </div>
            {allMembers.length > 1 && (
                <div>
                    <label className="block text-xs text-gray-500 mb-1">可委托给</label>
                    <div className="flex flex-wrap gap-2">
                        {allMembers.filter((_, i) => i !== index).map((m, i) => (
                            <label key={i} className="flex items-center gap-1.5 text-xs cursor-pointer">
                                <input type="checkbox"
                                    checked={(member.can_delegate_to || []).includes(m.member_key)}
                                    onChange={e => {
                                        const cur = member.can_delegate_to || [];
                                        onUpdate(index, 'can_delegate_to',
                                            e.target.checked ? [...cur, m.member_key] : cur.filter(k => k !== m.member_key));
                                    }}
                                    className="w-3.5 h-3.5 rounded text-purple-600" />
                                <span className="text-gray-600">{getMemberLabel(m)}</span>
                            </label>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
};


/* ══════════════════════════════════════════════════════ */
/* TeamList 主组件                                        */
/* ══════════════════════════════════════════════════════ */

const TeamList = ({ showAlert }) => {
    const [teams, setTeams] = useState([]);
    const [loading, setLoading] = useState(true);
    const [editingTeam, setEditingTeam] = useState(null);
    const [showCreate, setShowCreate] = useState(false);
    const [visualEditingId, setVisualEditingId] = useState(null);

    // 分步表单
    const [formStep, setFormStep] = useState(1);
    const [formName, setFormName] = useState('');
    const [formDescription, setFormDescription] = useState('');
    const [formMode, setFormMode] = useState('');
    const [formLeaderInstructions, setFormLeaderInstructions] = useState('');
    const [formMembers, setFormMembers] = useState([]);

    // 引用数据
    const [availableAgents, setAvailableAgents] = useState([]);
    const [availableTeams, setAvailableTeams] = useState([]);
    const [availableDatasources, setAvailableDatasources] = useState([]);

    const loadData = useCallback(async () => {
        try {
            setLoading(true);
            const [teamsRes, agentsRes, dsRes] = await Promise.all([
                api.listTeams(),
                api.listAgents(),
                api.listDatasources(),
            ]);
            setTeams(teamsRes.teams || []);
            setAvailableAgents(agentsRes.agents || []);
            setAvailableDatasources(dsRes.datasources || dsRes || []);
        } catch (e) {
            showAlert?.('加载失败: ' + e.message, '错误', 'error');
        } finally {
            setLoading(false);
        }
    }, [showAlert]);

    useEffect(() => { loadData(); }, [loadData]);

    const resetForm = () => {
        setFormStep(1);
        setFormName('');
        setFormDescription('');
        setFormMode('');
        setFormLeaderInstructions('');
        setFormMembers([]);
        setEditingTeam(null);
        setShowCreate(false);
    };

    const openCreate = () => {
        resetForm();
        setShowCreate(true);
    };

    const openEdit = async (team) => {
        try {
            const res = await api.getTeam(team.id);
            const fullTeam = res.team;
            setEditingTeam(fullTeam);
            setFormName(fullTeam.name);
            setFormDescription(fullTeam.description || '');
            setFormMode(fullTeam.mode);
            setFormLeaderInstructions(fullTeam.leader_config?.instructions || '');
            setFormMembers(fullTeam.members || []);
            setFormStep(1);
            setShowCreate(true);
        } catch (e) {
            showAlert?.('加载团队详情失败: ' + e.message, '错误', 'error');
        }
    };

    const closeForm = () => resetForm();

    const handleSave = async () => {
        if (!formName.trim()) {
            showAlert?.('请填写团队名称', '提示', 'warning');
            return;
        }
        if (!formMode) {
            showAlert?.('请选择协作模式', '提示', 'warning');
            return;
        }
        const payload = {
            name: formName,
            description: formDescription,
            mode: formMode,
            leader_config: { instructions: formLeaderInstructions },
            members: formMembers,
        };
        try {
            if (editingTeam) {
                await api.updateTeam(editingTeam.id, payload);
                showAlert?.('团队已更新', '成功', 'success');
            } else {
                await api.createTeam(payload);
                showAlert?.('团队已创建', '成功', 'success');
            }
            closeForm();
            loadData();
        } catch (e) {
            showAlert?.(e.message || '保存失败', '错误', 'error');
        }
    };

    const handleDelete = async (team) => {
        if (!window.confirm(`确定删除团队「${team.name}」？此操作不可撤销。`)) return;
        try {
            await api.deleteTeam(team.id);
            showAlert?.('团队已删除', '成功', 'success');
            loadData();
        } catch (e) {
            showAlert?.(e.message || '删除失败', '错误', 'error');
        }
    };

    const addMember = (type) => {
        const prefix = { agent: 'agent', workflow: 'wf', sub_team: 'team', custom_flow: 'flow' };
        const count = formMembers.filter(m => m.member_type === type).length + 1;
        const newMember = {
            member_key: `${prefix[type] || type}_${count}`,
            member_type: type,
            ref_agent_name: type === 'agent' ? '' : undefined,
            ref_workflow: type === 'workflow' ? '' : undefined,
            datasource_name: type === 'workflow' ? '' : undefined,
            ref_team_id: type === 'sub_team' ? null : undefined,
            ref_custom_flow: type === 'custom_flow' ? { name: '', steps: [] } : undefined,
            role: '',
            description: '',
            capabilities: [],
            can_delegate_to: [],
        };
        setFormMembers(prev => [...prev, newMember]);
    };

    const updateMember = (index, field, value) => {
        setFormMembers(prev => {
            const updated = [...prev];
            updated[index] = { ...updated[index], [field]: value };
            return updated;
        });
    };

    const removeMember = (index) => {
        setFormMembers(prev => prev.filter((_, i) => i !== index));
    };

    const handleTest = async (team) => {
        const message = window.prompt('输入测试消息:');
        if (!message) return;
        try {
            const res = await api.testTeam(team.id, message);
            if (res.success) {
                showAlert?.(res.result?.answer || '测试完成（无返回）', '测试结果', 'success');
            } else {
                showAlert?.(res.error || '测试失败', '错误', 'error');
            }
        } catch (e) {
            showAlert?.(e.message || '测试失败', '错误', 'error');
        }
    };

    /* ── 步骤验证 ── */
    const canGoNext = () => {
        if (formStep === 1) return !!formMode;
        if (formStep === 2) return !!formName.trim();
        if (formStep === 3) return formMembers.length >= (MODES.find(m => m.key === formMode)?.minMembers || 1);
        return true;
    };

    const stepLabels = ['选择模式', '基本信息', '配置成员', '确认创建'];
    const showForm = showCreate || editingTeam;

    // 可视化编辑模式
    if (visualEditingId) {
        return (
            <TeamEditor
                teamId={visualEditingId}
                onBack={() => { setVisualEditingId(null); loadData(); }}
                showAlert={showAlert}
            />
        );
    }

    return (
        <div className="flex-1 flex flex-col bg-[#f8fafc] overflow-hidden">
            {/* Header */}
            <div className="h-16 bg-white/80 backdrop-blur border-b border-gray-200/60 flex items-center justify-between px-8 shadow-sm">
                <div className="flex items-center gap-3">
                    <div className="p-1.5 rounded-lg bg-cyan-100 text-cyan-600">
                        <Icons.Terminal className="w-5 h-5" />
                    </div>
                    <h2 className="text-lg font-bold text-gray-800">团队管理</h2>
                    <span className="text-sm text-gray-400">({teams.length})</span>
                </div>
                {!showForm && (
                    <button onClick={openCreate}
                        className="px-4 py-2 bg-cyan-600 text-white text-sm font-medium rounded-xl hover:bg-cyan-700 transition-colors">
                        + 新建团队
                    </button>
                )}
            </div>

            <div className="flex-1 overflow-auto p-6">
                {showForm ? (
                    <div className="max-w-4xl mx-auto">
                        <StepIndicator current={formStep} total={4} labels={stepLabels} />

                        <div className="bg-white rounded-2xl shadow-lg border border-gray-200 p-8">
                            {/* ═══ 步骤1: 选择模式 ═══ */}
                            {formStep === 1 && (
                                <div>
                                    <h3 className="text-lg font-bold text-gray-800 mb-2">选择协作模式</h3>
                                    <p className="text-sm text-gray-500 mb-6">
                                        模式决定了领导智能体如何协调团队成员处理用户问题
                                    </p>
                                    <div className="grid grid-cols-2 gap-4">
                                        {MODES.map(m => (
                                            <button key={m.key} type="button"
                                                onClick={() => setFormMode(m.key)}
                                                className={`p-5 rounded-xl border-2 text-left transition-all ${
                                                    formMode === m.key
                                                        ? 'border-cyan-500 bg-cyan-50 shadow-sm'
                                                        : 'border-gray-200 hover:border-cyan-200 hover:bg-gray-50'
                                                }`}>
                                                <div className="flex items-center gap-2 mb-2">
                                                    <span className="text-xl">{m.icon}</span>
                                                    <span className="font-bold text-gray-800">{m.name}</span>
                                                </div>
                                                <p className="text-sm text-gray-600 mb-3">{m.longDesc}</p>
                                                <div className="flex items-center justify-between text-xs text-gray-400">
                                                    <span>最少 {m.minMembers} 个成员</span>
                                                    <span className="px-2 py-0.5 bg-gray-100 rounded-full">适用: {m.useCase}</span>
                                                </div>
                                            </button>
                                        ))}
                                    </div>
                                    {formMode && <DataFlowDiagram mode={formMode} />}
                                </div>
                            )}

                            {/* ═══ 步骤2: 基本信息 ═══ */}
                            {formStep === 2 && (
                                <div>
                                    <h3 className="text-lg font-bold text-gray-800 mb-2">团队基本信息</h3>
                                    <p className="text-sm text-gray-500 mb-6">
                                        配置团队名称和领导智能体的协调指令
                                    </p>
                                    <div className="space-y-5">
                                        <div>
                                            <label className="block text-sm font-medium text-gray-700 mb-1">
                                                团队名称 <span className="text-red-400">*</span>
                                            </label>
                                            <input type="text" value={formName} onChange={e => setFormName(e.target.value)}
                                                placeholder="如：数据分析总团队"
                                                className="w-full px-4 py-2.5 border border-gray-200 rounded-xl focus:ring-2 focus:ring-cyan-500 outline-none text-sm" />
                                        </div>
                                        <div>
                                            <label className="block text-sm font-medium text-gray-700 mb-1">团队描述</label>
                                            <input type="text" value={formDescription} onChange={e => setFormDescription(e.target.value)}
                                                placeholder="团队的用途和职责说明"
                                                className="w-full px-4 py-2.5 border border-gray-200 rounded-xl focus:ring-2 focus:ring-cyan-500 outline-none text-sm" />
                                        </div>
                                        <div>
                                            <label className="block text-sm font-medium text-gray-700 mb-1">
                                                领导智能体指令
                                                <span className="text-gray-400 font-normal ml-2">（系统提示词，描述如何协调团队）</span>
                                            </label>
                                            <textarea value={formLeaderInstructions}
                                                onChange={e => setFormLeaderInstructions(e.target.value)}
                                                rows={8}
                                                placeholder={`你是${formName || '团队'}的负责人。\n\n根据用户问题的性质，你应该：\n1. 分析问题属于哪个成员的专业领域\n2. 选择合适的成员执行任务\n3. 汇总成员的执行结果给出完整回答`}
                                                className="w-full px-4 py-3 border border-gray-200 rounded-xl focus:ring-2 focus:ring-cyan-500 outline-none text-sm font-mono resize-y leading-relaxed" />
                                        </div>
                                    </div>
                                    <DataFlowDiagram mode={formMode} />
                                </div>
                            )}

                            {/* ═══ 步骤3: 配置成员 ═══ */}
                            {formStep === 3 && (
                                <div>
                                    <div className="flex items-center justify-between mb-2">
                                        <div>
                                            <h3 className="text-lg font-bold text-gray-800">配置团队成员</h3>
                                            <p className="text-sm text-gray-500 mt-1">
                                                {MODES.find(m => m.key === formMode)?.name} 需要至少{' '}
                                                {MODES.find(m => m.key === formMode)?.minMembers} 个成员
                                            </p>
                                        </div>
                                    </div>

                                    {/* 添加按钮 */}
                                    <div className="flex gap-2 mb-4">
                                        <button type="button" onClick={() => addMember('agent')}
                                            className="flex-1 py-2.5 text-xs font-medium bg-blue-50 text-blue-700 rounded-xl hover:bg-blue-100 border border-blue-200 transition-colors">
                                            + 🤖 智能体
                                        </button>
                                        <button type="button" onClick={() => addMember('workflow')}
                                            className="flex-1 py-2.5 text-xs font-medium bg-green-50 text-green-700 rounded-xl hover:bg-green-100 border border-green-200 transition-colors">
                                            + ⚙️ 工作流
                                        </button>
                                        <button type="button" onClick={() => addMember('sub_team')}
                                            className="flex-1 py-2.5 text-xs font-medium bg-orange-50 text-orange-700 rounded-xl hover:bg-orange-100 border border-orange-200 transition-colors">
                                            + 👥 子团队
                                        </button>
                                        <button type="button" onClick={() => addMember('custom_flow')}
                                            className="flex-1 py-2.5 text-xs font-medium bg-purple-50 text-purple-700 rounded-xl hover:bg-purple-100 border border-purple-200 transition-colors">
                                            + 🔧 自定义流程
                                        </button>
                                    </div>

                                    {formMembers.length === 0 ? (
                                        <div className="py-12 text-center border-2 border-dashed border-gray-200 rounded-xl">
                                            <p className="text-gray-400 text-sm">点击上方按钮添加团队成员</p>
                                            <p className="text-gray-300 text-xs mt-1">每种类型有不同的配置面板</p>
                                        </div>
                                    ) : (
                                        <div className="space-y-4 max-h-[60vh] overflow-y-auto pr-1">
                                            {formMembers.map((member, idx) => (
                                                <div key={idx} className="border border-gray-200 rounded-xl overflow-hidden">
                                                    {/* 成员头部 */}
                                                    <div className={`px-4 py-2.5 flex items-center justify-between ${
                                                        member.member_type === 'agent' ? 'bg-blue-50' :
                                                        member.member_type === 'workflow' ? 'bg-green-50' :
                                                        member.member_type === 'sub_team' ? 'bg-orange-50' :
                                                        'bg-purple-50'
                                                    }`}>
                                                        <div className="flex items-center gap-2">
                                                            <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${MEMBER_TYPE_COLORS[member.member_type]}`}>
                                                                {MEMBER_TYPE_LABELS[member.member_type]}
                                                            </span>
                                                            <span className="text-xs text-gray-500">
                                                                {member.role || member.ref_agent_name || member.ref_workflow || member.ref_custom_flow?.name || '未配置'}
                                                            </span>
                                                        </div>
                                                        <button type="button" onClick={() => removeMember(idx)}
                                                            className="text-red-400 hover:text-red-600 text-xs">删除</button>
                                                    </div>
                                                    {/* 成员配置面板 */}
                                                    <div className="p-4">
                                                        {member.member_type === 'agent' && (
                                                            <AgentMemberPanel member={member} index={idx}
                                                                agents={availableAgents} allMembers={formMembers} onUpdate={updateMember} />
                                                        )}
                                                        {member.member_type === 'workflow' && (
                                                            <WorkflowMemberPanel member={member} index={idx}
                                                                datasources={availableDatasources} allMembers={formMembers} onUpdate={updateMember} />
                                                        )}
                                                        {member.member_type === 'sub_team' && (
                                                            <SubTeamMemberPanel member={member} index={idx}
                                                                teams={teams} editingTeam={editingTeam} allMembers={formMembers} onUpdate={updateMember} />
                                                        )}
                                                        {member.member_type === 'custom_flow' && (
                                                            <CustomFlowMemberPanel member={member} index={idx}
                                                                agents={availableAgents} allMembers={formMembers} onUpdate={updateMember} />
                                                        )}
                                                    </div>
                                                </div>
                                            ))}
                                        </div>
                                    )}
                                </div>
                            )}

                            {/* ═══ 步骤4: 确认 ═══ */}
                            {formStep === 4 && (
                                <div>
                                    <h3 className="text-lg font-bold text-gray-800 mb-2">确认团队配置</h3>
                                    <p className="text-sm text-gray-500 mb-6">请检查以下配置是否正确</p>

                                    {/* 概览 */}
                                    <div className="space-y-4">
                                        <div className="p-4 bg-gray-50 rounded-xl border border-gray-100">
                                            <div className="flex items-center gap-3 mb-3">
                                                <span className="text-xl">{MODES.find(m => m.key === formMode)?.icon}</span>
                                                <div>
                                                    <h4 className="font-bold text-gray-800">{formName}</h4>
                                                    <p className="text-xs text-gray-500">{MODES.find(m => m.key === formMode)?.name} | {formDescription || '无描述'}</p>
                                                </div>
                                            </div>
                                            <DataFlowDiagram mode={formMode} />
                                        </div>

                                        {/* 领导指令预览 */}
                                        <div className="p-4 bg-gray-50 rounded-xl border border-gray-100">
                                            <p className="text-xs font-medium text-gray-500 mb-2">领导智能体指令</p>
                                            <p className="text-sm text-gray-700 font-mono whitespace-pre-wrap max-h-24 overflow-y-auto">
                                                {formLeaderInstructions || '(未填写，使用默认行为)'}
                                            </p>
                                        </div>

                                        {/* 成员拓扑 */}
                                        <div className="p-4 bg-gray-50 rounded-xl border border-gray-100">
                                            <p className="text-xs font-medium text-gray-500 mb-3">
                                                团队成员 ({formMembers.length} 个)
                                            </p>
                                            {/* 领导节点 */}
                                            <div className="flex flex-col items-center">
                                                <div className="px-4 py-2 bg-gray-800 text-white rounded-lg text-sm font-medium">
                                                    👑 领导智能体
                                                </div>
                                                <div className="w-0.5 h-4 bg-gray-300" />
                                                <div className="flex gap-3 flex-wrap justify-center">
                                                    {formMembers.map((m, i) => (
                                                        <div key={i} className={`px-3 py-2 rounded-lg text-xs font-medium border ${
                                                            m.member_type === 'agent' ? 'bg-blue-50 text-blue-700 border-blue-200' :
                                                            m.member_type === 'workflow' ? 'bg-green-50 text-green-700 border-green-200' :
                                                            m.member_type === 'sub_team' ? 'bg-orange-50 text-orange-700 border-orange-200' :
                                                            'bg-purple-50 text-purple-700 border-purple-200'
                                                        }`}>
                                                            {MEMBER_TYPE_LABELS[m.member_type]}: {m.role || m.ref_agent_name || m.ref_workflow || m.ref_custom_flow?.name || m.member_key}
                                                        </div>
                                                    ))}
                                                </div>
                                            </div>
                                        </div>

                                        {/* 验证清单 */}
                                        <div className="p-4 rounded-xl border border-gray-200">
                                            <p className="text-xs font-medium text-gray-500 mb-2">验证清单</p>
                                            <div className="space-y-1.5">
                                                {[
                                                    { ok: !!formName.trim(), msg: '团队名称已填写' },
                                                    { ok: !!formMode, msg: '协作模式已选择' },
                                                    { ok: formMembers.length >= (MODES.find(m => m.key === formMode)?.minMembers || 1),
                                                        msg: `成员数量满足要求 (至少 ${MODES.find(m => m.key === formMode)?.minMembers || 1} 个)` },
                                                    { ok: !!formLeaderInstructions.trim(), msg: '领导指令已填写', warn: true },
                                                    { ok: formMembers.every(m => {
                                                        if (m.member_type === 'agent') return !!m.ref_agent_name;
                                                        if (m.member_type === 'workflow') return !!m.ref_workflow;
                                                        if (m.member_type === 'sub_team') return !!m.ref_team_id;
                                                        if (m.member_type === 'custom_flow') return m.ref_custom_flow?.steps?.length > 0;
                                                        return true;
                                                    }), msg: '所有成员已配置引用目标' },
                                                    { ok: formMembers.filter(m => m.member_type === 'workflow')
                                                        .every(m => !WORKFLOWS.find(w => w.key === m.ref_workflow)?.needsDatasource || !!m.datasource_name),
                                                        msg: '工作流成员已选择数据源' },
                                                ].map((item, i) => (
                                                    <div key={i} className={`flex items-center gap-2 text-xs ${
                                                        item.ok ? 'text-green-600' : item.warn ? 'text-amber-500' : 'text-red-500'
                                                    }`}>
                                                        <span>{item.ok ? '✅' : item.warn ? '⚠️' : '❌'}</span>
                                                        <span>{item.msg}</span>
                                                    </div>
                                                ))}
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            )}

                            {/* ═══ 底部按钮 ═══ */}
                            <div className="flex justify-between mt-8 pt-6 border-t border-gray-100">
                                <div className="flex gap-3">
                                    {formStep > 1 ? (
                                        <button onClick={() => setFormStep(s => s - 1)}
                                            className="px-5 py-2.5 text-sm text-gray-600 hover:bg-gray-100 rounded-xl transition-colors">
                                            上一步
                                        </button>
                                    ) : (
                                        <button onClick={closeForm}
                                            className="px-5 py-2.5 text-sm text-gray-600 hover:bg-gray-100 rounded-xl transition-colors">
                                            取消
                                        </button>
                                    )}
                                </div>
                                <div>
                                    {formStep < 4 ? (
                                        <button onClick={() => setFormStep(s => s + 1)} disabled={!canGoNext()}
                                            className="px-5 py-2.5 bg-cyan-600 text-white text-sm font-medium rounded-xl hover:bg-cyan-700 transition-colors disabled:opacity-40 disabled:cursor-not-allowed">
                                            下一步
                                        </button>
                                    ) : (
                                        <button onClick={handleSave}
                                            className="px-5 py-2.5 bg-cyan-600 text-white text-sm font-medium rounded-xl hover:bg-cyan-700 transition-colors">
                                            {editingTeam ? '保存修改' : '创建团队'}
                                        </button>
                                    )}
                                </div>
                            </div>
                        </div>
                    </div>
                ) : loading ? (
                    <div className="flex items-center justify-center py-20">
                        <div className="animate-spin w-8 h-8 border-3 border-cyan-500 border-t-transparent rounded-full"></div>
                    </div>
                ) : (
                    /* 团队列表 */
                    <div className="max-w-4xl mx-auto grid grid-cols-1 md:grid-cols-2 gap-4">
                        {teams.length === 0 ? (
                            <div className="col-span-2 text-center py-16 text-gray-400">
                                <p className="text-lg mb-2">暂无团队</p>
                                <p className="text-sm">点击「+ 新建团队」开始创建</p>
                            </div>
                        ) : teams.map(team => (
                            <div key={team.id}
                                className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm hover:shadow-md transition-all cursor-pointer group"
                                onClick={() => openEdit(team)}>
                                <div className="flex items-start justify-between">
                                    <div>
                                        <h4 className="font-bold text-gray-800">{team.name}</h4>
                                        <p className="text-xs text-gray-500 mt-1">{MODE_LABELS[team.mode] || team.mode}</p>
                                    </div>
                                    <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                                        <button onClick={(e) => { e.stopPropagation(); setVisualEditingId(team.id); }}
                                            className="p-1.5 text-gray-400 hover:text-cyan-600 hover:bg-cyan-50 rounded-lg transition-colors" title="可视化编辑">
                                            <Icons.Database className="w-4 h-4" />
                                        </button>
                                        <button onClick={(e) => { e.stopPropagation(); handleTest(team); }}
                                            className="p-1.5 text-gray-400 hover:text-green-600 hover:bg-green-50 rounded-lg transition-colors" title="测试">
                                            <Icons.Terminal className="w-4 h-4" />
                                        </button>
                                        <button onClick={(e) => { e.stopPropagation(); handleDelete(team); }}
                                            className="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors" title="删除">
                                            <Icons.Trash className="w-4 h-4" />
                                        </button>
                                    </div>
                                </div>
                                {team.description && (
                                    <p className="text-sm text-gray-500 mt-2 line-clamp-2">{team.description}</p>
                                )}
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
};

export default TeamList;
