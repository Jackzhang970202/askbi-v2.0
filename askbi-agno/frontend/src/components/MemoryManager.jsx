import React, { useEffect, useMemo, useState } from 'react';
import { api } from '../services/api';
import { Icons } from './Icons';

const TABS = [
    { key: 'user', label: '用户画像' },
    { key: 'session', label: '会话记忆' },
    { key: 'events', label: '事件审计' },
];

const emptyEdit = { scope: '', id: null, summary: '', profile_text: '', memory_kind: '', status: 'active' };

export default function MemoryManager({ currentUser, currentChatId, showAlert }) {
    const [tab, setTab] = useState('user');
    const [loading, setLoading] = useState(false);
    const [userMemories, setUserMemories] = useState([]);
    const [sessionMemories, setSessionMemories] = useState([]);
    const [events, setEvents] = useState([]);
    const [keyword, setKeyword] = useState('');
    const [editor, setEditor] = useState(emptyEdit);

    const load = async () => {
        setLoading(true);
        try {
            if (tab === 'user') {
                const res = await api.listUserMemories(keyword);
                if (res.success) setUserMemories(res.memories || []);
            } else if (tab === 'session') {
                const res = await api.listSessionMemories(currentChatId || null);
                if (res.success) setSessionMemories(res.memories || []);
            } else {
                const res = await api.listMemoryEvents(currentChatId);
                if (res.success) setEvents(res.events || []);
            }
        } catch (e) {
            showAlert?.(`加载记忆失败: ${e.message}`, '错误', 'error');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        if (!currentUser) return;
        load();
    }, [currentUser?.id, currentChatId, tab]);

    const rows = useMemo(() => {
        if (tab === 'user') return userMemories;
        if (tab === 'session') return sessionMemories;
        return events;
    }, [tab, userMemories, sessionMemories, events]);

    const beginEdit = (item, scope) => setEditor({
        scope,
        id: item.id,
        summary: item.summary || '',
        profile_text: item.profile_text || '',
        memory_kind: item.memory_kind || '',
        status: item.status || 'active',
    });

    const saveEdit = async () => {
        try {
            const res = await api.updateMemory(editor.scope, editor.id, {
                summary: editor.summary,
                profile_text: editor.profile_text,
                memory_kind: editor.memory_kind,
                status: editor.status,
                chat_id: editor.scope === 'session' ? currentChatId : undefined,
            });
            if (!res.success) throw new Error(res.error || '保存失败');
            setEditor(emptyEdit);
            await load();
        } catch (e) {
            showAlert?.(`保存记忆失败: ${e.message}`, '错误', 'error');
        }
    };

    const archiveMemory = async (scope, id) => {
        try {
            const res = await api.archiveMemory(scope, id);
            if (!res.success) throw new Error(res.error || '归档失败');
            await load();
        } catch (e) {
            showAlert?.(`归档记忆失败: ${e.message}`, '错误', 'error');
        }
    };

    const deleteMemory = async (scope, id) => {
        try {
            const res = await api.deleteMemory(scope, id);
            if (!res.success) throw new Error(res.error || '删除失败');
            await load();
        } catch (e) {
            showAlert?.(`删除记忆失败: ${e.message}`, '错误', 'error');
        }
    };

    return (
        <div className="h-full overflow-y-auto p-6">
            <div className="mx-auto max-w-6xl space-y-5">
                <div className="flex items-center justify-between">
                    <div>
                        <h1 className="text-2xl font-black text-gray-800">记忆管理</h1>
                        <p className="mt-1 text-sm text-gray-500">管理用户画像记忆与会话摘要记忆。</p>
                    </div>
                    {tab === 'user' && (
                        <input value={keyword} onChange={(e) => setKeyword(e.target.value)} placeholder="搜索记忆..." className="rounded-xl border border-gray-200 px-3 py-2 text-sm outline-none focus:border-blue-400" />
                    )}
                </div>

                <div className="flex gap-2">
                    {TABS.map(item => (
                        <button key={item.key} onClick={() => setTab(item.key)} className={`rounded-xl px-4 py-2 text-sm font-bold ${tab === item.key ? 'bg-blue-600 text-white' : 'bg-white text-gray-500 border border-gray-200'}`}>
                            {item.label}
                        </button>
                    ))}
                </div>

                {editor.id && (
                    <div className="rounded-2xl border border-blue-100 bg-blue-50/60 p-4 space-y-3">
                        <div className="text-sm font-bold text-blue-700">编辑记忆</div>
                        <input value={editor.summary} onChange={(e) => setEditor(prev => ({ ...prev, summary: e.target.value }))} placeholder="摘要" className="w-full rounded-xl border border-blue-200 bg-white px-3 py-2 text-sm outline-none" />
                        <input value={editor.memory_kind} onChange={(e) => setEditor(prev => ({ ...prev, memory_kind: e.target.value }))} placeholder="类型" className="w-full rounded-xl border border-blue-200 bg-white px-3 py-2 text-sm outline-none" />
                        <textarea value={editor.profile_text} onChange={(e) => setEditor(prev => ({ ...prev, profile_text: e.target.value }))} placeholder="记忆内容" rows={6} className="w-full rounded-xl border border-blue-200 bg-white px-3 py-2 text-sm outline-none resize-y" />
                        <div className="flex justify-end gap-2">
                            <button onClick={() => setEditor(emptyEdit)} className="rounded-xl border border-gray-200 px-4 py-2 text-sm text-gray-500">取消</button>
                            <button onClick={saveEdit} className="rounded-xl bg-blue-600 px-4 py-2 text-sm font-bold text-white">保存</button>
                        </div>
                    </div>
                )}

                <div className="overflow-hidden rounded-2xl border border-gray-100 bg-white shadow-sm">
                    {loading ? (
                        <div className="p-8 text-center text-sm text-gray-400">加载中...</div>
                    ) : rows.length === 0 ? (
                        <div className="p-8 text-center text-sm text-gray-400">暂无数据</div>
                    ) : (
                        <div className="divide-y divide-gray-100">
                            {rows.map((item) => (
                                <div key={`${tab}_${item.id}`} className="p-4">
                                    {tab === 'events' ? (
                                        <div className="space-y-1 text-sm">
                                            <div className="font-bold text-gray-700">{item.event_type}</div>
                                            <div className="text-gray-500">{item.memory_scope} / 会话: {item.chat_id || '-'} / 用户: {item.user_id || '-'}</div>
                                            <pre className="mt-2 overflow-auto rounded-xl bg-gray-50 p-3 text-xs text-gray-600">{JSON.stringify(item.event_payload || {}, null, 2)}</pre>
                                        </div>
                                    ) : (
                                        <div className="space-y-2">
                                            <div className="flex items-start justify-between gap-3">
                                                <div className="min-w-0 flex-1">
                                                    <div className="text-sm font-bold text-gray-800">{item.summary || '未命名记忆'}</div>
                                                    <div className="mt-1 text-xs text-gray-500">{item.memory_kind} · {item.status}{item.chat_id ? ` · 会话: ${item.chat_id}` : ''}</div>
                                                    <div className="mt-2 whitespace-pre-wrap text-sm text-gray-600">{item.profile_text}</div>
                                                </div>
                                                <div className="flex shrink-0 gap-2">
                                                    <button onClick={() => beginEdit(item, tab === 'user' ? 'user' : 'session')} className="rounded-lg border border-gray-200 px-3 py-1.5 text-xs text-gray-600 hover:bg-gray-50">编辑</button>
                                                    <button onClick={() => archiveMemory(tab === 'user' ? 'user' : 'session', item.id)} className="rounded-lg border border-amber-200 px-3 py-1.5 text-xs text-amber-700 hover:bg-amber-50">归档</button>
                                                    <button onClick={() => deleteMemory(tab === 'user' ? 'user' : 'session', item.id)} className="rounded-lg border border-red-200 px-3 py-1.5 text-xs text-red-600 hover:bg-red-50">删除</button>
                                                </div>
                                            </div>
                                        </div>
                                    )}
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
