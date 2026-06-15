import React, { useState, useEffect } from 'react';
import { Icons } from './Icons';
import { withBase } from '../services/api';

const Sidebar = ({
    currentUser,
    activeTab,
    globalConfigTab,
    currentChatId,
    biHistory,
    excelHistory,
    reportHistory,
    onDeleteChat,
    onDeleteReport,
    onRenameReport,
    onLogout,
    onNavigate,
    onLoadReport,
    onChatSwitch
}) => {
    const [primaryMenu, setPrimaryMenu] = useState('askbi');
    const [reportHistoryExpanded, setReportHistoryExpanded] = useState(true);
    const [askbiMenuCollapsed, setAskbiMenuCollapsed] = useState(false);
    const [permissionMenuCollapsed, setPermissionMenuCollapsed] = useState(false);
    const [reportMenuCollapsed, setReportMenuCollapsed] = useState(false);
    const [renamingReport, setRenamingReport] = useState(null);
    const [newName, setNewName] = useState('');

    const openChat = (chat) => {
        window.history.pushState({}, '', withBase(`/chat/${chat.id}`));
        onChatSwitch && onChatSwitch(chat);
    };

    useEffect(() => {
        const permissionTabs = ['user_manager'];
        const reportTabs = ['report'];
        const askbiTabs = ['new_chat', 'bi', 'excel', 'datasource', 'global_config', 'knowledge_base', 'history', 'skills', 'agents', 'teams', 'memory'];

        if (permissionTabs.includes(activeTab)) {
            setPrimaryMenu('permission');
        } else if (reportTabs.includes(activeTab)) {
            setPrimaryMenu('report');
        } else if (askbiTabs.includes(activeTab)) {
            setPrimaryMenu('askbi');
        }
    }, [activeTab]);

    const handlePrimaryClick = (menu) => {
        setPrimaryMenu(prev => prev === menu ? null : menu);
    };

    const renderAskBIMenu = () => (
        <div className={`flex flex-col h-full bg-slate-800/95 border-r border-slate-700/50 transition-all duration-300 ${askbiMenuCollapsed ? 'w-12' : 'w-56'}`}>
            <div className="p-4 border-b border-slate-700/50 flex items-center justify-between">
                {!askbiMenuCollapsed && <h2 className="text-sm font-bold text-gray-300">AskBI</h2>}
                <button
                    onClick={() => setAskbiMenuCollapsed(!askbiMenuCollapsed)}
                    className={`p-1.5 rounded-lg hover:bg-slate-700/50 text-gray-400 hover:text-white transition-all ${askbiMenuCollapsed ? 'mx-auto' : ''}`}
                    title={askbiMenuCollapsed ? '展开菜单' : '收起菜单'}
                >
                    <Icons.ChevronLeft className={`w-4 h-4 transition-transform ${askbiMenuCollapsed ? 'rotate-180' : ''}`} />
                </button>
            </div>

            <button
                onClick={() => onNavigate('bi')}
                className={`px-4 py-3 text-left text-sm font-medium transition-all flex items-center gap-2 ${['new_chat', 'bi', 'excel'].includes(activeTab) ? 'bg-blue-600/20 text-blue-400 border-l-2 border-blue-500' : 'text-gray-400 hover:bg-slate-700/50 hover:text-white'} ${askbiMenuCollapsed ? 'justify-center' : ''}`}
                title="新建对话"
            >
                <Icons.Bot className="w-4 h-4 flex-shrink-0" />
                {!askbiMenuCollapsed && '新建对话'}
            </button>

            <div className="px-4 pt-3 pb-1 text-[10px] font-bold text-gray-500 uppercase tracking-wider">
                {!askbiMenuCollapsed && '业务规则配置'}
            </div>

            <button
                onClick={() => onNavigate('global_config', 'vocabulary')}
                className={`px-6 py-3 text-left text-sm font-medium transition-all flex items-center gap-2 ${activeTab === 'global_config' && globalConfigTab === 'vocabulary' ? 'bg-indigo-600/20 text-indigo-400 border-l-2 border-indigo-500' : 'text-gray-400 hover:bg-slate-700/50 hover:text-white'} ${askbiMenuCollapsed ? 'justify-center px-4' : ''}`}
                title="业务词汇"
            >
                <Icons.Database className="w-4 h-4 flex-shrink-0" />
                {!askbiMenuCollapsed && '业务词汇'}
            </button>

            <button
                onClick={() => onNavigate('global_config', 'knowledge')}
                className={`px-6 py-3 text-left text-sm font-medium transition-all flex items-center gap-2 ${activeTab === 'global_config' && globalConfigTab === 'knowledge' ? 'bg-indigo-600/20 text-indigo-400 border-l-2 border-indigo-500' : 'text-gray-400 hover:bg-slate-700/50 hover:text-white'} ${askbiMenuCollapsed ? 'justify-center px-4' : ''}`}
                title="业务知识"
            >
                <Icons.Terminal className="w-4 h-4 flex-shrink-0" />
                {!askbiMenuCollapsed && '业务知识'}
            </button>

            <button
                onClick={() => onNavigate('global_config', 'sql')}
                className={`px-6 py-3 text-left text-sm font-medium transition-all flex items-center gap-2 ${activeTab === 'global_config' && globalConfigTab === 'sql' ? 'bg-indigo-600/20 text-indigo-400 border-l-2 border-indigo-500' : 'text-gray-400 hover:bg-slate-700/50 hover:text-white'} ${askbiMenuCollapsed ? 'justify-center px-4' : ''}`}
                title="参考SQL"
            >
                <Icons.Settings className="w-4 h-4 flex-shrink-0" />
                {!askbiMenuCollapsed && '参考SQL'}
            </button>

            <div className="mx-4 my-2 h-px bg-slate-700/50"></div>

            <button
                onClick={() => onNavigate('datasource')}
                className={`px-4 py-3 text-left text-sm font-medium transition-all flex items-center gap-2 ${activeTab === 'datasource' ? 'bg-cyan-600/20 text-cyan-400 border-l-2 border-cyan-500' : 'text-gray-400 hover:bg-slate-700/50 hover:text-white'} ${askbiMenuCollapsed ? 'justify-center' : ''}`}
                title="数据源管理"
            >
                <Icons.Database className="w-4 h-4 flex-shrink-0" />
                {!askbiMenuCollapsed && '数据源管理'}
            </button>

            <button
                onClick={() => onNavigate('knowledge_base')}
                className={`px-4 py-3 text-left text-sm font-medium transition-all flex items-center gap-2 ${activeTab === 'knowledge_base' ? 'bg-fuchsia-600/20 text-fuchsia-400 border-l-2 border-fuchsia-500' : 'text-gray-400 hover:bg-slate-700/50 hover:text-white'} ${askbiMenuCollapsed ? 'justify-center' : ''}`}
                title="知识库管理"
            >
                <Icons.Database className="w-4 h-4 flex-shrink-0" />
                {!askbiMenuCollapsed && '知识库管理'}
            </button>

            <div className="mx-4 my-2 h-px bg-slate-700/50"></div>

            <div className="px-4 pt-1 pb-1 text-[10px] font-bold text-gray-500 uppercase tracking-wider">
                {!askbiMenuCollapsed && '高级配置'}
            </div>

            <button
                onClick={() => onNavigate('skills')}
                className={`px-4 py-3 text-left text-sm font-medium transition-all flex items-center gap-2 ${activeTab === 'skills' ? 'bg-purple-600/20 text-purple-400 border-l-2 border-purple-500' : 'text-gray-400 hover:bg-slate-700/50 hover:text-white'} ${askbiMenuCollapsed ? 'justify-center' : ''}`}
                title="技能管理"
            >
                <Icons.Terminal className="w-4 h-4 flex-shrink-0" />
                {!askbiMenuCollapsed && '技能管理'}
            </button>

            <button
                onClick={() => onNavigate('agents')}
                className={`px-4 py-3 text-left text-sm font-medium transition-all flex items-center gap-2 ${activeTab === 'agents' ? 'bg-indigo-600/20 text-indigo-400 border-l-2 border-indigo-500' : 'text-gray-400 hover:bg-slate-700/50 hover:text-white'} ${askbiMenuCollapsed ? 'justify-center' : ''}`}
                title="智能体管理"
            >
                <Icons.Bot className="w-4 h-4 flex-shrink-0" />
                {!askbiMenuCollapsed && '智能体管理'}
            </button>

            <button
                onClick={() => onNavigate('teams')}
                className={`px-4 py-3 text-left text-sm font-medium transition-all flex items-center gap-2 ${activeTab === 'teams' ? 'bg-cyan-600/20 text-cyan-400 border-l-2 border-cyan-500' : 'text-gray-400 hover:bg-slate-700/50 hover:text-white'} ${askbiMenuCollapsed ? 'justify-center' : ''}`}
                title="团队管理"
            >
                <Icons.Terminal className="w-4 h-4 flex-shrink-0" />
                {!askbiMenuCollapsed && '团队管理'}
            </button>

            <button
                onClick={() => onNavigate('history')}
                className={`px-4 py-3 text-left text-sm font-medium transition-all flex items-center gap-2 ${activeTab === 'history' ? 'bg-amber-600/20 text-amber-400 border-l-2 border-amber-500' : 'text-gray-400 hover:bg-slate-700/50 hover:text-white'} ${askbiMenuCollapsed ? 'justify-center' : ''}`}
                title="历史记录"
            >
                <Icons.History className="w-4 h-4 flex-shrink-0" />
                {!askbiMenuCollapsed && '历史记录'}
            </button>

            <button
                onClick={() => onNavigate('memory')}
                className={`px-4 py-3 text-left text-sm font-medium transition-all flex items-center gap-2 ${activeTab === 'memory' ? 'bg-violet-600/20 text-violet-400 border-l-2 border-violet-500' : 'text-gray-400 hover:bg-slate-700/50 hover:text-white'} ${askbiMenuCollapsed ? 'justify-center' : ''}`}
                title="记忆管理"
            >
                <Icons.Database className="w-4 h-4 flex-shrink-0" />
                {!askbiMenuCollapsed && '记忆管理'}
            </button>

            <div className="mx-4 my-2 h-px bg-slate-700/50"></div>

            <div className="px-4 pt-1 pb-1 text-[10px] font-bold text-gray-500 uppercase tracking-wider">
                {!askbiMenuCollapsed && '会话记录'}
            </div>

            {!askbiMenuCollapsed && (
                <div className="flex-1 overflow-y-auto sidebar-scrollbar space-y-1 px-2 pb-2">
                    {(biHistory || []).map((chat) => {
                        const contextType = chat.context?.type || (chat.teamId ? 'team' : 'bi');
                        const icon = contextType === 'team' ? <Icons.Terminal className="w-3 h-3 text-cyan-400" /> : contextType === 'general' ? <Icons.MessageCircle className="w-3 h-3 text-slate-400" /> : <Icons.Bot className="w-3 h-3 text-blue-400" />;
                        const activeClass = contextType === 'team' ? 'bg-cyan-900/30 border-cyan-500/30 text-white' : contextType === 'general' ? 'bg-slate-700/60 border-slate-500/30 text-white' : 'bg-blue-900/30 border-blue-500/30 text-white';
                        return (
                        <div key={`bi_${chat.id}`} onClick={() => openChat(chat)} className={`group relative p-2 rounded-lg cursor-pointer transition-all border border-transparent ${currentChatId === chat.id ? activeClass : 'hover:bg-slate-700/50 text-gray-400 hover:text-gray-200'}`}>
                            <div className="flex items-center gap-2 pr-8">
                                {icon}
                                <div className="font-medium text-xs truncate flex-1">{chat.title || chat.id}</div>
                            </div>
                            {chat.context?.type && <div className="mt-1 pl-5 text-[9px] uppercase tracking-wide opacity-60">{chat.context.type}</div>}
                            <button onClick={(e) => onDeleteChat && onDeleteChat(e, chat)} className="absolute right-1 top-1/2 -translate-y-1/2 p-1 rounded hover:bg-red-500/20 hover:text-red-400 transition-all text-gray-500 opacity-0 group-hover:opacity-100" title="删除">
                                <Icons.Trash className="w-3 h-3" />
                            </button>
                        </div>
                    )})}
                    {(excelHistory || []).map((chat) => (
                        <div key={`excel_${chat.id}`} onClick={() => openChat(chat)} className={`group relative p-2 rounded-lg cursor-pointer transition-all border border-transparent ${currentChatId === chat.id ? 'bg-emerald-900/30 border-emerald-500/30 text-white' : 'hover:bg-slate-700/50 text-gray-400 hover:text-gray-200'}`}>
                            <div className="flex items-center gap-2 pr-8">
                                <Icons.Table className="w-3 h-3 text-emerald-400" />
                                <div className="font-medium text-xs truncate flex-1">{chat.title || chat.id}</div>
                            </div>
                            <button onClick={(e) => onDeleteChat && onDeleteChat(e, chat)} className="absolute right-1 top-1/2 -translate-y-1/2 p-1 rounded hover:bg-red-500/20 hover:text-red-400 transition-all text-gray-500 opacity-0 group-hover:opacity-100" title="删除">
                                <Icons.Trash className="w-3 h-3" />
                            </button>
                        </div>
                    ))}
                    {(biHistory || []).length === 0 && (excelHistory || []).length === 0 && (
                        <div className="px-2 py-6 text-center text-gray-500 text-xs">暂无会话记录</div>
                    )}
                </div>
            )}
        </div>
    );

    const renderPermissionMenu = () => (
        <div className={`flex flex-col h-full bg-slate-800/95 border-r border-slate-700/50 transition-all duration-300 ${permissionMenuCollapsed ? 'w-12' : 'w-56'}`}>
            <div className="p-4 border-b border-slate-700/50 flex items-center justify-between">
                {!permissionMenuCollapsed && <h2 className="text-sm font-bold text-gray-300">权限管理</h2>}
                <button onClick={() => setPermissionMenuCollapsed(!permissionMenuCollapsed)} className={`p-1.5 rounded-lg hover:bg-slate-700/50 text-gray-400 hover:text-white transition-all ${permissionMenuCollapsed ? 'mx-auto' : ''}`} title={permissionMenuCollapsed ? '展开菜单' : '收起菜单'}>
                    <Icons.ChevronLeft className={`w-4 h-4 transition-transform ${permissionMenuCollapsed ? 'rotate-180' : ''}`} />
                </button>
            </div>
            {currentUser?.role === 'admin' && (
                <button onClick={() => onNavigate('users')} className={`px-4 py-3 text-left text-sm font-medium transition-all flex items-center gap-2 ${activeTab === 'user_manager' ? 'bg-amber-600/20 text-amber-400 border-l-2 border-amber-500' : 'text-gray-400 hover:bg-slate-700/50 hover:text-white'} ${permissionMenuCollapsed ? 'justify-center' : ''}`} title="用户管理">
                    <Icons.User className="w-4 h-4 flex-shrink-0" />
                    {!permissionMenuCollapsed && '用户管理'}
                </button>
            )}
            {currentUser?.role !== 'admin' && !permissionMenuCollapsed && <div className="p-4 text-center text-gray-500 text-xs">暂无可用功能</div>}
        </div>
    );

    const renderReportMenu = () => (
        <div className={`flex flex-col h-full bg-slate-800/95 border-r border-slate-700/50 transition-all duration-300 ${reportMenuCollapsed ? 'w-12' : 'w-56'}`}>
            <div className="p-4 border-b border-slate-700/50 flex items-center justify-between">
                {!reportMenuCollapsed && <h2 className="text-sm font-bold text-gray-300">报表管理</h2>}
                <button onClick={() => setReportMenuCollapsed(!reportMenuCollapsed)} className={`p-1.5 rounded-lg hover:bg-slate-700/50 text-gray-400 hover:text-white transition-all ${reportMenuCollapsed ? 'mx-auto' : ''}`} title={reportMenuCollapsed ? '展开菜单' : '收起菜单'}>
                    <Icons.ChevronLeft className={`w-4 h-4 transition-transform ${reportMenuCollapsed ? 'rotate-180' : ''}`} />
                </button>
            </div>

            <button onClick={() => onNavigate('report', 'report')} className={`px-4 py-3 text-left text-sm font-medium transition-all flex items-center gap-2 text-gray-400 hover:bg-slate-700/50 hover:text-white ${reportMenuCollapsed ? 'justify-center' : ''}`} title="新建报表">
                <Icons.Plus className="w-4 h-4 flex-shrink-0" />
                {!reportMenuCollapsed && '新建报表'}
            </button>

            <button onClick={() => onNavigate('report', 'dashboard')} className={`px-4 py-3 text-left text-sm font-medium transition-all flex items-center gap-2 text-gray-400 hover:bg-slate-700/50 hover:text-white ${reportMenuCollapsed ? 'justify-center' : ''}`} title="新建大屏">
                <svg className="w-4 h-4 flex-shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <rect x="2" y="3" width="20" height="14" rx="2" ry="2"></rect>
                    <line x1="8" y1="21" x2="16" y2="21"></line>
                    <line x1="12" y1="17" x2="12" y2="21"></line>
                </svg>
                {!reportMenuCollapsed && '新建大屏'}
            </button>

            {!reportMenuCollapsed && <div className="mx-4 my-2 h-px bg-slate-700/50"></div>}

            {!reportMenuCollapsed && (
                <div className="flex-1 overflow-hidden flex flex-col">
                    <button onClick={() => setReportHistoryExpanded(!reportHistoryExpanded)} className="px-4 py-2 text-left text-[10px] font-bold text-gray-500 uppercase tracking-wider flex items-center justify-between hover:text-gray-400">
                        <span>历史记录</span>
                        <Icons.ChevronDown className={`w-3 h-3 transition-transform ${reportHistoryExpanded ? 'rotate-180' : ''}`} />
                    </button>
                    {reportHistoryExpanded && (
                        <div className="flex-1 overflow-y-auto sidebar-scrollbar space-y-1 px-2 pb-2">
                            {(reportHistory || []).map((report) => (
                                <div key={report.report_id} onClick={() => onLoadReport && onLoadReport(report)} className={`group relative p-2 rounded-lg cursor-pointer transition-all border border-transparent ${currentChatId === report.report_id ? (report.report_type === 'dashboard' ? 'bg-teal-900/30 border-teal-500/30 text-white' : 'bg-emerald-900/30 border-emerald-500/30 text-white') : 'hover:bg-slate-700/50 text-gray-400 hover:text-gray-200'}`}>
                                    <div className="flex items-center gap-2 pr-10">
                                        {report.report_type === 'dashboard' ? (
                                            <svg className="w-3 h-3 text-teal-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                                <rect x="2" y="3" width="20" height="14" rx="2" ry="2"></rect>
                                                <line x1="8" y1="21" x2="16" y2="21"></line>
                                                <line x1="12" y1="17" x2="12" y2="21"></line>
                                            </svg>
                                        ) : (
                                            <Icons.Table className="w-3 h-3 text-emerald-500" />
                                        )}
                                        <div className="font-medium text-xs truncate flex-1">{report.display_file_name || report.report_type || '报表'}</div>
                                    </div>
                                    <div className="text-[10px] opacity-60 mt-0.5 pl-5 truncate">
                                        {report.row_count || 0} {report.report_type === 'dashboard' ? '条' : '行'} · {new Date(report.created_at || report.timestamp).toLocaleDateString()}
                                    </div>
                                    {report.is_desensitized && <span className="ml-5 mt-1 text-[9px] text-amber-500">🔒 已脱敏</span>}
                                    <div className="absolute right-1 top-1/2 -translate-y-1/2 flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition-all">
                                        <button onClick={(e) => { e.stopPropagation(); setRenamingReport(report); setNewName(report.display_file_name || ''); }} className="p-1 rounded hover:bg-blue-500/20 hover:text-blue-400 transition-all text-gray-500" title="重命名">
                                            <Icons.Edit className="w-3 h-3" />
                                        </button>
                                        <button onClick={(e) => { e.stopPropagation(); onDeleteReport && onDeleteReport(e, report); }} className="p-1 rounded hover:bg-red-500/20 hover:text-red-400 transition-all text-gray-500" title="删除">
                                            <Icons.Trash className="w-3 h-3" />
                                        </button>
                                    </div>
                                </div>
                            ))}
                            {(reportHistory || []).length === 0 && <div className="text-center text-gray-600 text-xs py-4">暂无报表记录</div>}
                        </div>
                    )}
                </div>
            )}
        </div>
    );

    return (
        <div className="flex h-full">
            <div className="w-16 bg-slate-900 flex flex-col border-r border-slate-800 shadow-xl">
                <div className="p-3 border-b border-slate-800/60 bg-slate-900">
                    <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-xl flex items-center justify-center text-white">
                        <Icons.Bot className="w-5 h-5" />
                    </div>
                </div>

                <div className="flex flex-col p-2 space-y-2 flex-1">
                    <button onClick={() => handlePrimaryClick('askbi')} className={`w-12 h-12 rounded-xl flex items-center justify-center transition-all ${primaryMenu === 'askbi' ? 'bg-blue-600 text-white shadow-lg shadow-blue-900/30' : 'text-gray-400 hover:bg-slate-800 hover:text-white'}`} title="AskBI">
                        <Icons.Bot className="w-5 h-5" />
                    </button>
                    <button onClick={() => handlePrimaryClick('report')} className={`w-12 h-12 rounded-xl flex items-center justify-center transition-all ${primaryMenu === 'report' ? 'bg-emerald-600 text-white shadow-lg shadow-emerald-900/30' : 'text-gray-400 hover:bg-slate-800 hover:text-white'}`} title="报表">
                        <Icons.Table className="w-5 h-5" />
                    </button>
                    <button onClick={() => handlePrimaryClick('permission')} className={`w-12 h-12 rounded-xl flex items-center justify-center transition-all ${primaryMenu === 'permission' ? 'bg-amber-600 text-white shadow-lg shadow-amber-900/30' : 'text-gray-400 hover:bg-slate-800 hover:text-white'}`} title="权限">
                        <Icons.User className="w-5 h-5" />
                    </button>
                </div>

                <div className="p-2 border-t border-slate-800/60">
                    <button onClick={onLogout} className={`w-12 h-12 rounded-xl flex items-center justify-center text-white font-black text-sm hover:opacity-80 transition-all ${currentUser?.role === 'admin' ? 'bg-gradient-to-br from-amber-500 to-orange-600' : 'bg-gradient-to-br from-blue-500 to-indigo-600'}`} title={`${currentUser?.username} (${currentUser?.role === 'admin' ? '管理员' : '普通用户'}) - 点击退出`}>
                        {currentUser?.username?.charAt(0).toUpperCase()}
                    </button>
                </div>
            </div>

            <div className="flex overflow-hidden">
                {primaryMenu === 'askbi' && renderAskBIMenu()}
                {primaryMenu === 'permission' && renderPermissionMenu()}
                {primaryMenu === 'report' && renderReportMenu()}
            </div>

            {renamingReport && (
                <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-[200]" onClick={() => setRenamingReport(null)}>
                    <div className="bg-white rounded-xl shadow-2xl w-80 overflow-hidden" onClick={e => e.stopPropagation()}>
                        <div className="p-4 border-b border-gray-200 bg-gray-50">
                            <h3 className="font-bold text-gray-800">重命名</h3>
                        </div>
                        <div className="p-4">
                            <input type="text" value={newName} onChange={e => setNewName(e.target.value)} onKeyDown={e => {
                                if (e.key === 'Enter' && newName.trim()) {
                                    onRenameReport && onRenameReport(renamingReport.report_id, newName.trim());
                                    setRenamingReport(null);
                                }
                                if (e.key === 'Escape') setRenamingReport(null);
                            }} placeholder="请输入新名称" className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none" autoFocus />
                        </div>
                        <div className="p-4 border-t border-gray-200 flex justify-end gap-2">
                            <button onClick={() => setRenamingReport(null)} className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-lg transition-all">取消</button>
                            <button onClick={() => {
                                if (newName.trim()) {
                                    onRenameReport && onRenameReport(renamingReport.report_id, newName.trim());
                                    setRenamingReport(null);
                                }
                            }} disabled={!newName.trim()} className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-300 disabled:text-gray-500 transition-all">确定</button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default React.memo(Sidebar);
