import React, { useState, useEffect, useCallback, useMemo, createContext, useContext } from 'react';
import ReactFlow, {
    Background,
    Controls,
    MiniMap,
    Handle,
    Position,
    MarkerType,
    useReactFlow,
} from 'reactflow';
import 'reactflow/dist/style.css';
import { Icons } from './Icons';
import { api } from '../services/api';

// ============================================================
// 常量
// ============================================================

const MODE_OPTIONS = [
    { value: 'coordinate', label: '协调模式', desc: '领导按需选成员' },
    { value: 'route', label: '路由模式', desc: '领导选一个成员' },
    { value: 'broadcast', label: '广播模式', desc: '全员并行执行' },
    { value: 'tasks', label: '任务模式', desc: '拆解目标为任务' },
];

const MEMBER_TYPE_META = {
    agent:       { label: '智能体', color: '#3b82f6', bg: '#eff6ff', border: '#93c5fd', icon: 'A' },
    workflow:    { label: '工作流', color: '#10b981', bg: '#ecfdf5', border: '#6ee7b7', icon: 'W' },
    sub_team:    { label: '子团队', color: '#f59e0b', bg: '#fffbeb', border: '#fcd34d', icon: 'T' },
    custom_flow: { label: '流程',   color: '#8b5cf6', bg: '#f5f3ff', border: '#c4b5fd', icon: 'F' },
};

const NODE_W = 200;
const NODE_H = 80;
const GROUP_PAD = 30;
const H_GAP = 40;
const V_GAP = 100;

// ============================================================
// Context — 让自定义节点能访问编辑器回调
// ============================================================

const EditorCtx = createContext(null);

// ============================================================
// 自定义节点: LeaderNode
// ============================================================

const LeaderNode = ({ data, selected }) => {
    const { onSelect } = useContext(EditorCtx);
    return (
        <div
            onClick={() => onSelect?.('leader')}
            style={{
                width: NODE_W,
                padding: '14px 16px',
                background: '#0f172a',
                border: `2px solid ${selected ? '#60a5fa' : '#334155'}`,
                borderRadius: 14,
                color: 'white',
                cursor: 'pointer',
                boxShadow: selected ? '0 0 0 3px rgba(96,165,250,0.3)' : '0 2px 8px rgba(0,0,0,0.2)',
            }}
        >
            <div style={{ fontSize: 10, color: '#94a3b8', fontWeight: 700, letterSpacing: 1 }}>LEADER</div>
            <div style={{ fontSize: 14, fontWeight: 700, marginTop: 4 }}>{data.label || '协调者'}</div>
            <div style={{ fontSize: 11, color: '#64748b', marginTop: 2 }}>{data.modeLabel}</div>
            <Handle type="source" position={Position.Bottom} style={{ background: '#475569' }} />
        </div>
    );
};

// ============================================================
// 自定义节点: MemberNode
// ============================================================

const MemberNode = ({ data, selected }) => {
    const { onSelect, onRemove } = useContext(EditorCtx);
    const meta = MEMBER_TYPE_META[data.memberType] || MEMBER_TYPE_META.agent;

    return (
        <div
            onClick={() => onSelect?.(data.memberId)}
            style={{
                width: NODE_W,
                padding: '12px 14px',
                background: meta.bg,
                border: `2px solid ${selected ? meta.color : meta.border}`,
                borderRadius: 12,
                cursor: 'pointer',
                position: 'relative',
                boxShadow: selected ? `0 0 0 3px ${meta.color}33` : '0 1px 4px rgba(0,0,0,0.08)',
            }}
        >
            <Handle type="target" position={Position.Top} style={{ background: meta.color }} />
            <Handle type="source" position={Position.Bottom} style={{ background: meta.color }} />
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <div style={{
                    width: 28, height: 28, borderRadius: 8,
                    background: meta.color, color: 'white',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    fontSize: 13, fontWeight: 800, flexShrink: 0,
                }}>
                    {meta.icon}
                </div>
                <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontSize: 13, fontWeight: 700, color: '#1e293b', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {data.role || data.memberKey}
                    </div>
                    <div style={{ fontSize: 10, color: '#64748b', marginTop: 1 }}>{data.memberKey}</div>
                </div>
                <button
                    onClick={(e) => { e.stopPropagation(); onRemove?.(data.memberId); }}
                    style={{
                        background: 'none', border: 'none', cursor: 'pointer',
                        color: '#94a3b8', fontSize: 16, lineHeight: 1, padding: 2,
                    }}
                    title="删除成员"
                >
                    x
                </button>
            </div>
            <div style={{
                fontSize: 9, fontWeight: 700, color: meta.color,
                marginTop: 6, textTransform: 'uppercase', letterSpacing: 0.5,
            }}>
                {meta.label}
            </div>
        </div>
    );
};

// ============================================================
// 自定义节点: SubTeamGroupNode — 子团队容器，内含子成员
// ============================================================

const SubTeamGroupNode = ({ data, selected }) => {
    const { onSelect, onRemove } = useContext(EditorCtx);
    const meta = MEMBER_TYPE_META.sub_team;

    return (
        <div
            onClick={() => onSelect?.(data.memberId)}
            style={{
                minWidth: NODE_W + 40,
                padding: `${GROUP_PAD}px 16px 16px`,
                background: '#fffbeb40',
                border: `2px dashed ${selected ? meta.color : meta.border}`,
                borderRadius: 16,
                cursor: 'pointer',
                position: 'relative',
                boxShadow: selected ? `0 0 0 3px ${meta.color}33` : 'none',
            }}
        >
            <Handle type="target" position={Position.Top} style={{ background: meta.color }} />
            <div style={{
                position: 'absolute', top: -12, left: 16,
                background: meta.color, color: 'white',
                fontSize: 10, fontWeight: 700, padding: '2px 10px',
                borderRadius: 8, letterSpacing: 0.5,
            }}>
                SUB-TEAM
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 10 }}>
                <div style={{ flex: 1 }}>
                    <div style={{ fontSize: 13, fontWeight: 700, color: '#92400e' }}>
                        {data.role || data.memberKey}
                    </div>
                    <div style={{ fontSize: 10, color: '#b45309', marginTop: 1 }}>{data.memberKey}</div>
                </div>
                <button
                    onClick={(e) => { e.stopPropagation(); onRemove?.(data.memberId); }}
                    style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#d97706', fontSize: 16, padding: 2 }}
                >
                    x
                </button>
            </div>
            {/* 嵌套子成员 */}
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                {(data.children || []).map(child => {
                    const cm = MEMBER_TYPE_META[child.member_type] || MEMBER_TYPE_META.agent;
                    return (
                        <div key={child.member_key} style={{
                            padding: '6px 10px', background: 'white',
                            border: `1.5px solid ${cm.border}`, borderRadius: 8,
                            fontSize: 11, color: cm.color, fontWeight: 600,
                        }}>
                            {child.role || child.member_key}
                        </div>
                    );
                })}
                {(!data.children || data.children.length === 0) && (
                    <div style={{ fontSize: 11, color: '#d97706', fontStyle: 'italic' }}>
                        点击编辑查看子成员
                    </div>
                )}
            </div>
        </div>
    );
};

const nodeTypes = {
    leader: LeaderNode,
    member: MemberNode,
    sub_team_group: SubTeamGroupNode,
};

// ============================================================
// 布局算法
// ============================================================

function autoLayout(members, subTeamDetails) {
    const nodes = [];
    const edges = [];

    // Leader 节点
    nodes.push({
        id: 'leader',
        type: 'leader',
        position: { x: 0, y: 0 },
        data: {},
    });

    // 成员节点
    const regularMembers = members.filter(m => m.member_type !== 'sub_team');
    const subTeamMembers = members.filter(m => m.member_type === 'sub_team');
    const allMembers = [...regularMembers, ...subTeamMembers];

    let offsetX = 0;
    const memberPositions = [];

    for (const member of allMembers) {
        if (member.member_type === 'sub_team') {
            // 子团队 — 用 GroupNode
            const detail = subTeamDetails[member.ref_team_id];
            const children = detail?.members || [];
            const childCount = children.length;
            const groupW = Math.max(NODE_W + 40, childCount * (140 + 10) + 32);
            const groupH = NODE_H + GROUP_PAD + 60;

            const pos = { x: offsetX, y: NODE_H + V_GAP };
            nodes.push({
                id: member.member_key,
                type: 'sub_team_group',
                position: pos,
                data: {
                    memberId: member.member_key,
                    memberKey: member.member_key,
                    memberType: 'sub_team',
                    role: member.role,
                    children,
                },
            });
            memberPositions.push({ key: member.member_key, x: pos.x + groupW / 2, w: groupW });
            offsetX += groupW + H_GAP;
        } else {
            const pos = { x: offsetX, y: NODE_H + V_GAP };
            nodes.push({
                id: member.member_key,
                type: 'member',
                position: pos,
                data: {
                    memberId: member.member_key,
                    memberKey: member.member_key,
                    memberType: member.member_type,
                    role: member.role,
                },
            });
            memberPositions.push({ key: member.member_key, x: pos.x + NODE_W / 2, w: NODE_W });
            offsetX += NODE_W + H_GAP;
        }
    }

    // 居中 leader
    if (memberPositions.length > 0) {
        const totalW = offsetX - H_GAP;
        const leaderX = totalW / 2 - NODE_W / 2;
        nodes[0].position = { x: Math.max(0, leaderX), y: 0 };
    } else {
        nodes[0].position = { x: 200, y: 0 };
    }

    // Leader → Member 委派边
    for (const member of allMembers) {
        edges.push({
            id: `leader-${member.member_key}`,
            source: 'leader',
            target: member.member_key,
            type: 'smoothstep',
            animated: true,
            style: { stroke: '#94a3b8', strokeWidth: 1.5 },
            markerEnd: { type: MarkerType.ArrowClosed, color: '#94a3b8' },
        });
    }

    // can_delegate_to 对等委派边
    for (const member of allMembers) {
        for (const targetKey of (member.can_delegate_to || [])) {
            if (allMembers.find(m => m.member_key === targetKey)) {
                edges.push({
                    id: `del-${member.member_key}-${targetKey}`,
                    source: member.member_key,
                    target: targetKey,
                    type: 'smoothstep',
                    style: { stroke: '#e2e8f0', strokeWidth: 1, strokeDasharray: '5 5' },
                    markerEnd: { type: MarkerType.ArrowClosed, color: '#e2e8f0' },
                });
            }
        }
    }

    return { nodes, edges };
}

// ============================================================
// 右侧属性面板
// ============================================================

const PropertyPanel = ({ selectedId, team, members, setMembers, availableAgents, teams, onUpdateLeader }) => {
    if (!selectedId) {
        return (
            <div style={{ padding: 24, textAlign: 'center', color: '#94a3b8' }}>
                <div style={{ fontSize: 32, marginBottom: 8, opacity: 0.3 }}>
                    <Icons.Bot />
                </div>
                <p style={{ fontSize: 13 }}>点击画布上的节点编辑属性</p>
            </div>
        );
    }

    if (selectedId === 'leader') {
        return (
            <div style={{ padding: 16 }}>
                <h4 style={{ fontSize: 14, fontWeight: 700, color: '#0f172a', marginBottom: 16 }}>
                    Leader 配置
                </h4>
                <div style={{ marginBottom: 12 }}>
                    <label style={{ fontSize: 11, color: '#64748b', fontWeight: 600, display: 'block', marginBottom: 4 }}>
                        协调模式
                    </label>
                    <select
                        value={team.mode}
                        onChange={e => onUpdateLeader('mode', e.target.value)}
                        style={{ width: '100%', padding: '8px 10px', border: '1px solid #e2e8f0', borderRadius: 8, fontSize: 13 }}
                    >
                        {MODE_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
                    </select>
                </div>
                <div>
                    <label style={{ fontSize: 11, color: '#64748b', fontWeight: 600, display: 'block', marginBottom: 4 }}>
                        系统指令
                    </label>
                    <textarea
                        value={team.leaderInstructions}
                        onChange={e => onUpdateLeader('leaderInstructions', e.target.value)}
                        rows={8}
                        placeholder="领导智能体的系统提示词..."
                        style={{
                            width: '100%', padding: '8px 10px',
                            border: '1px solid #e2e8f0', borderRadius: 8,
                            fontSize: 12, fontFamily: 'monospace', resize: 'vertical',
                        }}
                    />
                </div>
            </div>
        );
    }

    // 成员属性编辑
    const idx = members.findIndex(m => m.member_key === selectedId);
    if (idx === -1) return null;
    const member = members[idx];
    const meta = MEMBER_TYPE_META[member.member_type];

    const update = (field, value) => {
        setMembers(prev => {
            const next = [...prev];
            next[idx] = { ...next[idx], [field]: value };
            return next;
        });
    };

    return (
        <div style={{ padding: 16, overflowY: 'auto' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 16 }}>
                <div style={{
                    width: 28, height: 28, borderRadius: 8,
                    background: meta.color, color: 'white',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    fontSize: 13, fontWeight: 800,
                }}>
                    {meta.icon}
                </div>
                <div>
                    <h4 style={{ fontSize: 14, fontWeight: 700, color: '#0f172a' }}>{meta.label}</h4>
                    <span style={{ fontSize: 11, color: '#64748b' }}>{member.member_key}</span>
                </div>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                <div>
                    <label style={{ fontSize: 11, color: '#64748b', fontWeight: 600, display: 'block', marginBottom: 4 }}>成员标识</label>
                    <input
                        value={member.member_key}
                        onChange={e => update('member_key', e.target.value)}
                        style={{ width: '100%', padding: '7px 10px', border: '1px solid #e2e8f0', borderRadius: 8, fontSize: 13 }}
                    />
                </div>
                <div>
                    <label style={{ fontSize: 11, color: '#64748b', fontWeight: 600, display: 'block', marginBottom: 4 }}>角色名称</label>
                    <input
                        value={member.role || ''}
                        onChange={e => update('role', e.target.value)}
                        placeholder="如：SQL专家"
                        style={{ width: '100%', padding: '7px 10px', border: '1px solid #e2e8f0', borderRadius: 8, fontSize: 13 }}
                    />
                </div>
                <div>
                    <label style={{ fontSize: 11, color: '#64748b', fontWeight: 600, display: 'block', marginBottom: 4 }}>能力描述</label>
                    <textarea
                        value={member.description || ''}
                        onChange={e => update('description', e.target.value)}
                        rows={3}
                        placeholder="供领导智能体参考的能力说明"
                        style={{ width: '100%', padding: '7px 10px', border: '1px solid #e2e8f0', borderRadius: 8, fontSize: 12, resize: 'vertical' }}
                    />
                </div>
                <div>
                    <label style={{ fontSize: 11, color: '#64748b', fontWeight: 600, display: 'block', marginBottom: 4 }}>能力标签（逗号分隔）</label>
                    <input
                        value={(member.capabilities || []).join(', ')}
                        onChange={e => update('capabilities', e.target.value.split(',').map(s => s.trim()).filter(Boolean))}
                        placeholder="sql, database, query"
                        style={{ width: '100%', padding: '7px 10px', border: '1px solid #e2e8f0', borderRadius: 8, fontSize: 13 }}
                    />
                </div>

                {/* 类型特定引用 */}
                {member.member_type === 'agent' && (
                    <div>
                        <label style={{ fontSize: 11, color: '#64748b', fontWeight: 600, display: 'block', marginBottom: 4 }}>引用智能体</label>
                        <select
                            value={member.ref_agent_name || ''}
                            onChange={e => update('ref_agent_name', e.target.value)}
                            style={{ width: '100%', padding: '7px 10px', border: '1px solid #e2e8f0', borderRadius: 8, fontSize: 13 }}
                        >
                            <option value="">-- 选择 --</option>
                            {availableAgents.map(a => (
                                <option key={a.name} value={a.name}>{a.display_name} ({a.name})</option>
                            ))}
                        </select>
                    </div>
                )}
                {member.member_type === 'workflow' && (
                    <div>
                        <label style={{ fontSize: 11, color: '#64748b', fontWeight: 600, display: 'block', marginBottom: 4 }}>引用工作流</label>
                        <select
                            value={member.ref_workflow || ''}
                            onChange={e => update('ref_workflow', e.target.value)}
                            style={{ width: '100%', padding: '7px 10px', border: '1px solid #e2e8f0', borderRadius: 8, fontSize: 13 }}
                        >
                            <option value="">-- 选择 --</option>
                            <option value="bi">BI 问数流程</option>
                            <option value="excel">Excel 分析流程</option>
                        </select>
                    </div>
                )}
                {member.member_type === 'sub_team' && (
                    <div>
                        <label style={{ fontSize: 11, color: '#64748b', fontWeight: 600, display: 'block', marginBottom: 4 }}>引用子团队</label>
                        <select
                            value={member.ref_team_id || ''}
                            onChange={e => update('ref_team_id', e.target.value ? parseInt(e.target.value) : null)}
                            style={{ width: '100%', padding: '7px 10px', border: '1px solid #e2e8f0', borderRadius: 8, fontSize: 13 }}
                        >
                            <option value="">-- 选择 --</option>
                            {teams.filter(t => t.id !== team.id).map(t => (
                                <option key={t.id} value={t.id}>{t.name}</option>
                            ))}
                        </select>
                    </div>
                )}
            </div>
        </div>
    );
};

// ============================================================
// TeamEditor 主组件
// ============================================================

const TeamEditor = ({ teamId, onBack, showAlert }) => {
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);

    // 团队数据
    const [teamName, setTeamName] = useState('');
    const [teamDescription, setTeamDescription] = useState('');
    const [teamMode, setTeamMode] = useState('coordinate');
    const [leaderInstructions, setLeaderInstructions] = useState('');
    const [members, setMembers] = useState([]);

    // 引用数据
    const [availableAgents, setAvailableAgents] = useState([]);
    const [allTeams, setAllTeams] = useState([]);
    const [subTeamDetails, setSubTeamDetails] = useState({});

    // UI 状态
    const [selectedId, setSelectedId] = useState(null);

    // 加载数据
    useEffect(() => {
        const load = async () => {
            try {
                setLoading(true);
                const [teamRes, agentsRes, teamsRes] = await Promise.all([
                    api.getTeam(teamId),
                    api.listAgents(),
                    api.listTeams(),
                ]);
                const t = teamRes.team;
                setTeamName(t.name);
                setTeamDescription(t.description || '');
                setTeamMode(t.mode);
                setLeaderInstructions(t.leader_config?.instructions || '');
                setMembers(t.members || []);
                setAvailableAgents(agentsRes.agents || []);
                setAllTeams(teamsRes.teams || []);

                // 加载子团队详情
                const subTeams = (t.members || []).filter(m => m.member_type === 'sub_team' && m.ref_team_id);
                if (subTeams.length > 0) {
                    const details = {};
                    await Promise.all(
                        subTeams.map(async m => {
                            try {
                                const res = await api.getTeam(m.ref_team_id);
                                details[m.ref_team_id] = res.team;
                            } catch (e) { /* ignore */ }
                        })
                    );
                    setSubTeamDetails(details);
                }
            } catch (e) {
                showAlert?.('加载团队失败: ' + e.message, '错误', 'error');
            } finally {
                setLoading(false);
            }
        };
        load();
    }, [teamId]);

    // 构建节点和边
    const { nodes, edges } = useMemo(() => {
        if (loading) return { nodes: [], edges: [] };
        const layout = autoLayout(members, subTeamDetails);
        // 注入 leader data
        if (layout.nodes.length > 0) {
            layout.nodes[0].data = {
                label: teamName || '协调者',
                modeLabel: MODE_OPTIONS.find(o => o.value === teamMode)?.label || teamMode,
            };
        }
        return layout;
    }, [members, subTeamDetails, teamName, teamMode, loading]);

    // 添加成员
    const addMember = (type) => {
        const newMember = {
            member_key: `member_${Date.now()}`,
            member_type: type,
            ref_agent_name: type === 'agent' ? '' : undefined,
            ref_workflow: type === 'workflow' ? '' : undefined,
            ref_team_id: type === 'sub_team' ? null : undefined,
            ref_custom_flow: type === 'custom_flow' ? { name: '', steps: [] } : undefined,
            role: '',
            description: '',
            capabilities: [],
            can_delegate_to: [],
        };
        setMembers(prev => [...prev, newMember]);
        setSelectedId(newMember.member_key);
    };

    // 删除成员
    const removeMember = (memberKey) => {
        setMembers(prev => prev.filter(m => m.member_key !== memberKey));
        if (selectedId === memberKey) setSelectedId(null);
    };

    // Leader 属性更新
    const updateLeader = (field, value) => {
        if (field === 'mode') setTeamMode(value);
        if (field === 'leaderInstructions') setLeaderInstructions(value);
    };

    // 保存
    const handleSave = async () => {
        if (!teamName.trim()) {
            showAlert?.('请填写团队名称', '提示', 'warning');
            return;
        }
        setSaving(true);
        try {
            await api.updateTeam(teamId, {
                name: teamName,
                description: teamDescription,
                mode: teamMode,
                leader_config: { instructions: leaderInstructions },
                members,
            });
            showAlert?.('团队已保存', '成功', 'success');
        } catch (e) {
            showAlert?.(e.message || '保存失败', '错误', 'error');
        } finally {
            setSaving(false);
        }
    };

    // Context value
    const ctxValue = useMemo(() => ({
        onSelect: setSelectedId,
        onRemove: removeMember,
    }), [selectedId]);

    if (loading) {
        return (
            <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#f8fafc' }}>
                <div className="animate-spin" style={{ width: 32, height: 32, border: '3px solid #06b6d4', borderTopColor: 'transparent', borderRadius: '50%' }} />
            </div>
        );
    }

    return (
        <EditorCtx.Provider value={ctxValue}>
            <div style={{ flex: 1, display: 'flex', flexDirection: 'column', background: '#f8fafc', height: '100%' }}>
                {/* Header */}
                <div style={{
                    height: 56, display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                    padding: '0 20px', borderBottom: '1px solid #e2e8f0', background: 'white', flexShrink: 0,
                }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                        <button
                            onClick={onBack}
                            style={{
                                background: 'none', border: 'none', cursor: 'pointer',
                                display: 'flex', alignItems: 'center', gap: 4, color: '#64748b', fontSize: 13,
                            }}
                        >
                            <Icons.ArrowLeft />
                            <span>返回</span>
                        </button>
                        <div style={{ width: 1, height: 24, background: '#e2e8f0' }} />
                        <input
                            value={teamName}
                            onChange={e => setTeamName(e.target.value)}
                            style={{
                                border: 'none', outline: 'none', fontSize: 16,
                                fontWeight: 700, color: '#0f172a', background: 'transparent',
                            }}
                        />
                        <span style={{
                            fontSize: 10, fontWeight: 700, color: '#06b6d4',
                            background: '#ecfeff', padding: '2px 8px', borderRadius: 6,
                        }}>
                            {MODE_OPTIONS.find(o => o.value === teamMode)?.label}
                        </span>
                    </div>
                    <button
                        onClick={handleSave}
                        disabled={saving}
                        style={{
                            padding: '8px 20px', background: '#0891b2', color: 'white',
                            border: 'none', borderRadius: 10, fontSize: 13, fontWeight: 600,
                            cursor: saving ? 'not-allowed' : 'pointer', opacity: saving ? 0.6 : 1,
                        }}
                    >
                        {saving ? '保存中...' : '保存'}
                    </button>
                </div>

                {/* Body: left + canvas + right */}
                <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
                    {/* Left Panel */}
                    <div style={{
                        width: 220, flexShrink: 0, borderRight: '1px solid #e2e8f0',
                        background: 'white', display: 'flex', flexDirection: 'column', overflow: 'hidden',
                    }}>
                        {/* 基本信息 */}
                        <div style={{ padding: '12px 14px', borderBottom: '1px solid #f1f5f9' }}>
                            <label style={{ fontSize: 10, color: '#94a3b8', fontWeight: 700, textTransform: 'uppercase', letterSpacing: 1 }}>
                                团队描述
                            </label>
                            <textarea
                                value={teamDescription}
                                onChange={e => setTeamDescription(e.target.value)}
                                rows={2}
                                style={{
                                    width: '100%', padding: '6px 8px', border: '1px solid #e2e8f0',
                                    borderRadius: 6, fontSize: 12, resize: 'none', marginTop: 4,
                                }}
                            />
                        </div>

                        {/* 添加成员 */}
                        <div style={{ padding: '12px 14px', borderBottom: '1px solid #f1f5f9' }}>
                            <label style={{ fontSize: 10, color: '#94a3b8', fontWeight: 700, textTransform: 'uppercase', letterSpacing: 1, marginBottom: 8, display: 'block' }}>
                                添加成员
                            </label>
                            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6 }}>
                                {Object.entries(MEMBER_TYPE_META).map(([type, meta]) => (
                                    <button
                                        key={type}
                                        onClick={() => addMember(type)}
                                        style={{
                                            padding: '8px 6px', background: meta.bg,
                                            border: `1px solid ${meta.border}`, borderRadius: 8,
                                            color: meta.color, fontSize: 11, fontWeight: 600,
                                            cursor: 'pointer', textAlign: 'center',
                                        }}
                                    >
                                        + {meta.label}
                                    </button>
                                ))}
                            </div>
                        </div>

                        {/* 已有成员列表 */}
                        <div style={{ flex: 1, overflowY: 'auto', padding: '12px 14px' }}>
                            <label style={{ fontSize: 10, color: '#94a3b8', fontWeight: 700, textTransform: 'uppercase', letterSpacing: 1, marginBottom: 8, display: 'block' }}>
                                成员列表 ({members.length})
                            </label>
                            {members.length === 0 ? (
                                <p style={{ fontSize: 12, color: '#cbd5e1', fontStyle: 'italic', textAlign: 'center', marginTop: 16 }}>
                                    暂无成员，点击上方添加
                                </p>
                            ) : (
                                <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                                    {members.map(m => {
                                        const meta = MEMBER_TYPE_META[m.member_type] || MEMBER_TYPE_META.agent;
                                        const isSelected = selectedId === m.member_key;
                                        return (
                                            <div
                                                key={m.member_key}
                                                onClick={() => setSelectedId(m.member_key)}
                                                style={{
                                                    padding: '8px 10px', borderRadius: 8,
                                                    background: isSelected ? meta.bg : '#f8fafc',
                                                    border: `1px solid ${isSelected ? meta.color : '#e2e8f0'}`,
                                                    cursor: 'pointer', display: 'flex',
                                                    alignItems: 'center', gap: 8,
                                                }}
                                            >
                                                <div style={{
                                                    width: 22, height: 22, borderRadius: 6,
                                                    background: meta.color, color: 'white',
                                                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                                                    fontSize: 11, fontWeight: 800, flexShrink: 0,
                                                }}>
                                                    {meta.icon}
                                                </div>
                                                <div style={{ flex: 1, minWidth: 0 }}>
                                                    <div style={{ fontSize: 12, fontWeight: 600, color: '#1e293b', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                                                        {m.role || m.member_key}
                                                    </div>
                                                    <div style={{ fontSize: 10, color: '#94a3b8' }}>{m.member_key}</div>
                                                </div>
                                            </div>
                                        );
                                    })}
                                </div>
                            )}
                        </div>
                    </div>

                    {/* Canvas */}
                    <div style={{ flex: 1, position: 'relative' }}>
                        <ReactFlow
                            nodes={nodes}
                            edges={edges}
                            nodeTypes={nodeTypes}
                            fitView
                            fitViewOptions={{ padding: 0.3 }}
                            nodesDraggable={true}
                            nodesConnectable={false}
                            proOptions={{ hideAttribution: true }}
                        >
                            <Background color="#e2e8f0" gap={20} />
                            <Controls showInteractive={false} />
                            <MiniMap
                                nodeStrokeWidth={3}
                                style={{ width: 120, height: 80 }}
                            />
                        </ReactFlow>
                    </div>

                    {/* Right Panel */}
                    <div style={{
                        width: 280, flexShrink: 0, borderLeft: '1px solid #e2e8f0',
                        background: 'white', overflow: 'hidden', display: 'flex', flexDirection: 'column',
                    }}>
                        <div style={{
                            padding: '12px 16px', borderBottom: '1px solid #f1f5f9',
                            fontSize: 10, color: '#94a3b8', fontWeight: 700,
                            textTransform: 'uppercase', letterSpacing: 1,
                        }}>
                            属性面板
                        </div>
                        <div style={{ flex: 1, overflowY: 'auto' }}>
                            <PropertyPanel
                                selectedId={selectedId}
                                team={{ id: teamId, mode: teamMode, leaderInstructions }}
                                members={members}
                                setMembers={setMembers}
                                availableAgents={availableAgents}
                                teams={allTeams}
                                onUpdateLeader={updateLeader}
                            />
                        </div>
                    </div>
                </div>
            </div>
        </EditorCtx.Provider>
    );
};

export default TeamEditor;
