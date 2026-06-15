import React, { useState, useEffect, useRef, useMemo, useCallback } from 'react';
import { Icons } from './components/Icons';
import LoginPage from './components/LoginPage';
import UserManager from './components/UserManager';
import ReportManager from './components/ReportManager';
import Sidebar from './components/Sidebar';
import DataSourceConfig from './components/DataSourceConfig';
import GlobalConfigManager from './components/GlobalConfigManager';
import KnowledgeBaseManager from './components/KnowledgeBaseManager';
import HistoryManager from './components/HistoryManager';
import { api, withBase, APP_BASE } from './services/api';
import Modal from './components/Modal';
import MessageItem from './components/MessageItem';
import SuggestedQuestions from './components/SuggestedQuestions';
import LoadingDots from './components/LoadingDots';
import SchemaViewer from './components/SchemaViewer';
import KnowledgeEditor from './components/KnowledgeEditor';
import SkillManager from './components/SkillManager';
import AgentManager from './components/AgentManager';
import TeamList from './components/TeamList';
import MemoryManager from './components/MemoryManager';
import SkillSelector from './components/SkillSelector';
import useProgressStream from './hooks/useProgressStream';

const DEFAULT_CONTEXT = { type: 'general', ref_id: null, ref_name: null, datasource_name: null };
const normalizeAppPath = (pathname) => {
    if (!pathname) return '/';
    return pathname.startsWith(APP_BASE) ? (pathname.slice(APP_BASE.length) || '/') : pathname;
};
const navigateTo = (path, { replace = false } = {}) => {
    const normalized = path.startsWith('/') ? path : `/${path}`;
    const target = withBase(normalized);
    if (`${window.location.pathname}${window.location.search}` === target) return;
    window.history[replace ? 'replaceState' : 'pushState']({}, '', target);
    window.dispatchEvent(new PopStateEvent('popstate'));
};

const App = () => {
    const [currentUser, setCurrentUser] = useState(() => {
        try {
            const user = sessionStorage.getItem('askbi_user') || localStorage.getItem('askbi_user');
            return user ? JSON.parse(user) : null;
        } catch {
            return null;
        }
    });
    const [authToken, setAuthToken] = useState(() => sessionStorage.getItem('askbi_token') || localStorage.getItem('askbi_token'));
    const [authChecking, setAuthChecking] = useState(true);

    const [activeTab, setActiveTab] = useState('new_chat');
    const [globalConfigTab, setGlobalConfigTab] = useState('vocabulary');
    const [reportCreateMode, setReportCreateMode] = useState(null);
    const [pendingLoadReport, setPendingLoadReport] = useState(null);
    const [reportHistory, setReportHistory] = useState([]);

    const [currentChatId, setCurrentChatId] = useState(null);
    const [chatContext, setChatContext] = useState(DEFAULT_CONTEXT);
    const [biHistory, setBiHistory] = useState([]);
    const [excelHistory, setExcelHistory] = useState([]);
    const [availableTeams, setAvailableTeams] = useState([]);
    const [datasources, setDatasources] = useState([]);

    const [messages, setMessages] = useState([]);
    const [input, setInput] = useState('');
    const [messageLoading, setMessageLoading] = useState(false);
    const [uploadLoading, setUploadLoading] = useState(false);
    const [memoryEnabled, setMemoryEnabled] = useState(true);
    const [analysisEnabled, setAnalysisEnabled] = useState(false);
    const [selectedSkillIds, setSelectedSkillIds] = useState([]);
    const [contextMenuOpen, setContextMenuOpen] = useState(false);

    const [excelViewMode, setExcelViewMode] = useState('chat');
    const [dataViewType, setDataViewType] = useState('processed');
    const [excelData, setExcelData] = useState([]);
    const [editingData, setEditingData] = useState({});
    const [activeTableTab, setActiveTableTab] = useState(0);
    const [selectedFiles, setSelectedFiles] = useState([]);
    const [fileConfigs, setFileConfigs] = useState({});
    const [loadingData, setLoadingData] = useState(false);
    const [loadingReports, setLoadingReports] = useState(false);
    const [reportFiles, setReportFiles] = useState([]);

    const [showSchemaViewer, setShowSchemaViewer] = useState(false);
    const [showKnowledgeEditor, setShowKnowledgeEditor] = useState(false);

    const [modalState, setModalState] = useState({ isOpen: false, title: '', message: '', type: 'alert', onConfirm: null, onCancel: null });

    const messagesCache = useRef({});
    const activeChatRef = useRef(null);
    const messageLoadingCache = useRef({});
    const messagesEndRef = useRef(null);

    const [sseChatId, setSseChatId] = useState(null);
    const sseOpts = useMemo(() => ({ teamId: chatContext.type === 'team' ? chatContext.ref_id : null }), [chatContext]);
    const { stages: sseStages, error: sseError, stop: stopSSE } = useProgressStream(sseChatId, chatContext.type || 'general', sseOpts);

    const showAlert = useCallback((message, title = '提示', type = 'alert') => {
        setModalState({ isOpen: true, title, message, type, onConfirm: null, onCancel: null });
    }, []);

    const closeModal = useCallback(() => {
        if (modalState.type === 'confirm' && modalState.onCancel) modalState.onCancel();
        setModalState(prev => ({ ...prev, isOpen: false }));
    }, [modalState]);

    const normalizeContext = useCallback((ctx) => ({ ...DEFAULT_CONTEXT, ...(ctx || {}) }), []);
    const applyChatContext = useCallback((ctx) => setChatContext(normalizeContext(ctx)), [normalizeContext]);

    const normalizeSession = useCallback((chat) => {
        if (!chat) return null;
        return {
            ...chat,
            context: normalizeContext(chat.context || (chat.datasourceName ? { type: 'bi', ref_name: chat.datasourceName, datasource_name: chat.datasourceName } : DEFAULT_CONTEXT)),
        };
    }, [normalizeContext]);

    const allChatHistory = useMemo(() => [...biHistory, ...excelHistory].map(normalizeSession).filter(Boolean), [biHistory, excelHistory, normalizeSession]);
    const currentChatMeta = useMemo(() => allChatHistory.find(item => item.id === currentChatId) || null, [allChatHistory, currentChatId]);
    const currentContext = chatContext;
    const currentMode = currentContext.type || 'general';
    const currentDatasourceName = currentChatMeta?.datasourceName || chatContext.datasource_name || (chatContext.type === 'bi' || chatContext.type === 'excel' ? chatContext.ref_name : null) || null;
    const currentTeamId = chatContext.type === 'team' ? chatContext.ref_id : null;
    const currentTeamName = chatContext.type === 'team' ? (chatContext.ref_name || '') : '';

    const headerTone = currentMode === 'team' ? 'team' : currentMode === 'bi' ? 'bi' : currentMode === 'excel' ? 'excel' : 'general';
    const headerIconTone = headerTone === 'team' ? 'bg-cyan-100 text-cyan-600' : headerTone === 'bi' ? 'bg-blue-100 text-blue-600' : headerTone === 'excel' ? 'bg-emerald-100 text-emerald-600' : 'bg-slate-100 text-slate-600';
    const headerPulseTone = headerTone === 'team' ? 'bg-cyan-500' : headerTone === 'bi' ? 'bg-blue-500' : headerTone === 'excel' ? 'bg-green-500' : 'bg-slate-500';
    const headerTitle = currentMode === 'team' ? (currentTeamName || '团队协作') : currentMode === 'bi' ? (currentDatasourceName || '智能分析助手') : currentMode === 'excel' ? (currentDatasourceName || 'Excel 数据洞察') : '智能分析助手';
    const contextTagText = currentMode === 'team' ? `团队：${currentTeamName}` : currentMode === 'bi' ? `数据源：${currentDatasourceName}` : currentMode === 'excel' ? `Excel：${currentDatasourceName}` : '';
    const contextTagClass = headerTone === 'team' ? 'bg-cyan-50 text-cyan-700 border-cyan-200' : headerTone === 'bi' ? 'bg-blue-50 text-blue-700 border-blue-200' : headerTone === 'excel' ? 'bg-emerald-50 text-emerald-700 border-emerald-200' : 'bg-slate-50 text-slate-700 border-slate-200';
    const sendButtonClass = headerTone === 'team' ? 'bg-cyan-600 text-white shadow-cyan-600/30' : headerTone === 'bi' ? 'bg-blue-600 text-white shadow-blue-600/30' : headerTone === 'excel' ? 'bg-emerald-600 text-white shadow-emerald-600/30' : 'bg-slate-700 text-white shadow-slate-700/30';
    const assistantAvatarTone = headerTone === 'team' ? 'bg-cyan-50 text-cyan-500' : headerTone === 'bi' ? 'bg-blue-50 text-blue-500' : headerTone === 'excel' ? 'bg-emerald-50 text-emerald-500' : 'bg-slate-50 text-slate-500';
    const headerIconNode = headerTone === 'team' ? <Icons.Terminal /> : headerTone === 'bi' ? <Icons.Bot /> : headerTone === 'excel' ? <Icons.Table /> : <Icons.MessageCircle />;
    const contextIconNode = headerTone === 'team' ? <Icons.Terminal className="w-3.5 h-3.5" /> : headerTone === 'bi' ? <Icons.Database className="w-3.5 h-3.5" /> : headerTone === 'excel' ? <Icons.Table className="w-3.5 h-3.5" /> : <Icons.MessageCircle className="w-3.5 h-3.5" />;

    const shouldShowNewChatLanding = activeTab === 'new_chat' && !currentChatId;
    const shouldShowExcelTabs = currentMode === 'excel' && !!currentChatId;
    const shouldShowExcelDataPane = shouldShowExcelTabs && excelViewMode === 'data';
    const shouldShowComposer = (!shouldShowExcelTabs || excelViewMode === 'chat');
    const shouldCenterComposer = !!currentChatId && messages.length === 0;
    const shouldShowEmptyPrompt = !!currentChatId && messages.length === 0;
    const centeredComposerPlaceholder = currentMode === 'bi' ? '输入您的问数问题...' : currentMode === 'excel' ? '关于这份 Excel，您想了解什么？' : '请输入内容...';
    const shouldShowAnalysisToggle = !!currentChatId && currentMode !== 'general';

    const composerPlaceholder = !currentChatId ? '请输入内容...' : currentMode === 'team' ? '向团队提问...' : currentMode === 'bi' ? '输入您的问数问题...' : currentMode === 'excel' ? '关于这份 Excel，您想了解什么？' : '请输入内容...';

    const handleLogin = useCallback((user, token) => {
        setCurrentUser(user);
        setAuthToken(token);
        setActiveTab('new_chat');
        setCurrentChatId(null);
        setMessages([]);
        setBiHistory([]);
        setExcelHistory([]);
        messagesCache.current = {};
        activeChatRef.current = null;
        applyChatContext(DEFAULT_CONTEXT);
        sessionStorage.setItem('askbi_user', JSON.stringify(user));
        sessionStorage.setItem('askbi_token', token);
        localStorage.setItem('askbi_user', JSON.stringify(user));
        localStorage.setItem('askbi_token', token);
        navigateTo('/chat', { replace: true });
    }, [applyChatContext]);

    const handleLogout = useCallback(async () => {
        try {
            await fetch(withBase('/auth/logout'), { method: 'POST', headers: { Authorization: `Bearer ${authToken}` } });
        } catch {}
        setCurrentUser(null);
        setAuthToken(null);
        setBiHistory([]);
        setExcelHistory([]);
        setReportHistory([]);
        setDatasources([]);
        setCurrentChatId(null);
        applyChatContext(DEFAULT_CONTEXT);
        sessionStorage.removeItem('askbi_user');
        sessionStorage.removeItem('askbi_token');
        localStorage.removeItem('askbi_user');
        localStorage.removeItem('askbi_token');
        navigateTo('/', { replace: true });
    }, [authToken, applyChatContext]);

    useEffect(() => {
        const checkAuth = async () => {
            if (!authToken) {
                const path = normalizeAppPath(window.location.pathname);
                if (path !== '/' && path !== '/chat') navigateTo('/', { replace: true });
                setAuthChecking(false);
                return;
            }
            try {
                const res = await fetch(withBase('/auth/me'), { headers: { Authorization: `Bearer ${authToken}` } });
                const data = await res.json();
                if (data.success && data.user) setCurrentUser(data.user);
                else handleLogout();
            } catch {
            } finally {
                setAuthChecking(false);
            }
        };
        checkAuth();
    }, [authToken, handleLogout]);

    const loadBiHistory = useCallback(async () => {
        try {
            const data = await api.listBiSessions();
            if (data?.success && Array.isArray(data.sessions)) {
                setBiHistory(data.sessions.map(session => normalizeSession({
                    id: session.id,
                    title: session.title || '新对话',
                    timestamp: session.timestamp,
                    datasourceName: session.datasource_name,
                    knowledgeId: session.knowledge_id || '0',
                    owner_username: session.owner_username,
                    context: session.context,
                    messages: [],
                })));
            }
        } catch {}
    }, [normalizeSession]);

    const loadExcelHistory = useCallback(async () => {
        try {
            const data = await api.listExcelSessions();
            if (data?.status === 'success' && Array.isArray(data.sessions)) {
                setExcelHistory(data.sessions.map(session => normalizeSession({
                    id: session.id,
                    title: session.title || 'Excel 分析',
                    timestamp: session.timestamp,
                    datasourceName: session.datasource_name || session.datasourceName || session.real_datasource_name,
                    owner_username: session.owner_username,
                    context: session.context,
                    messages: [],
                })));
            }
        } catch {}
    }, [normalizeSession]);

    const loadReportHistory = useCallback(async () => {
        if (!currentUser) return;
        try {
            const res = await fetch(withBase('/report/list'), { headers: { Authorization: `Bearer ${authToken}` } });
            const data = await res.json();
            if (data.success) setReportHistory(data.reports || []);
        } catch {}
    }, [authToken, currentUser]);

    const loadDatasources = useCallback(async () => {
        if (!currentUser) return;
        try {
            const res = await api.listDatasources();
            if (res.success) setDatasources(res.datasources || []);
        } catch {}
    }, [currentUser]);

    useEffect(() => {
        if (!currentUser) return;
        loadBiHistory();
        loadExcelHistory();
        loadReportHistory();
        loadDatasources();
        api.listTeams().then(res => setAvailableTeams((res.teams || []).filter(team => team.is_active !== false))).catch(() => {});
    }, [currentUser, loadBiHistory, loadExcelHistory, loadReportHistory, loadDatasources]);

    useEffect(() => {
        if (!currentUser) return;
        const refreshHistory = () => {
            loadBiHistory();
            loadExcelHistory();
            loadReportHistory();
        };
        window.addEventListener('askbi-history-refresh', refreshHistory);
        return () => window.removeEventListener('askbi-history-refresh', refreshHistory);
    }, [currentUser, loadBiHistory, loadExcelHistory, loadReportHistory]);

    const loadExcelDataByChatId = useCallback(async (chatId) => {
        if (!chatId) return;
        setLoadingData(true);
        try {
            const data = await api.getExcelFileData(chatId);
            if (data.status === 'success') {
                const loadedData = data.data || [];
                setExcelData(loadedData);
                const nextEditing = {};
                loadedData.forEach((fileData, idx) => {
                    nextEditing[idx] = { data: [...fileData.data], originalData: [...fileData.data] };
                });
                setEditingData(nextEditing);
                const firstProcessedIdx = loadedData.findIndex(item => !item.is_original);
                setActiveTableTab(firstProcessedIdx !== -1 ? firstProcessedIdx : 0);
            }
        } catch {
        } finally {
            setLoadingData(false);
        }
    }, []);

    const loadMessagesForChat = useCallback(async (chat) => {
        const mode = chat?.context?.type || 'general';
        if (mode === 'excel') return api.getExcelMessages(chat.id);
        if (mode === 'general') return api.getGeneralMessages(chat.id);
        return api.getBiMessages(chat.id);
    }, []);

    const handleChatSwitch = useCallback(async (chat) => {
        if (!chat) return;
        const newChatId = chat.id;
        if (currentChatId) messagesCache.current[currentChatId] = messages;
        setCurrentChatId(newChatId);
        activeChatRef.current = newChatId;
        setMessageLoading(true);
        try {
            const sessionRes = await api.getChatSession(newChatId);
            const serverSession = sessionRes?.session ? normalizeSession({
                id: sessionRes.session.chat_id || newChatId,
                title: chat.title,
                timestamp: chat.timestamp,
                datasourceName: sessionRes.session.datasource_name,
                knowledgeId: sessionRes.session.knowledge_id || '0',
                context: sessionRes.context || sessionRes.session.context,
                messages: []
            }) : normalizeSession(chat);
            applyChatContext(serverSession.context);
            setActiveTab(serverSession.context.type === 'excel' ? 'excel' : serverSession.context.type === 'general' ? 'new_chat' : 'bi');
            const res = await loadMessagesForChat(serverSession);
            const nextMessages = (res.messages || []).map(msg => {
                const structuredData = msg.role === 'assistant'
                    ? { summary: msg.content || msg.structuredData?.summary || '', ...(msg.structuredData || {}) }
                    : msg.structuredData;
                return { ...msg, structuredData, _shouldStream: false, isThinking: false };
            });
            messagesCache.current[newChatId] = nextMessages;
            setMessages(nextMessages);
            if (serverSession.context.type === 'excel') {
                setExcelViewMode('chat');
                await loadExcelDataByChatId(newChatId);
            }
        } catch {
            setMessages(messagesCache.current[newChatId] || []);
        } finally {
            setMessageLoading(false);
        }
    }, [applyChatContext, currentChatId, loadExcelDataByChatId, loadMessagesForChat, messages, normalizeSession]);

    const createGeneralChat = useCallback(async () => {
        setUploadLoading(true);
        try {
            const data = await api.createGeneralChat();
            const chatId = data.chat_id || data.chatid || data.id;
            const context = normalizeContext(data.context);
            const chat = normalizeSession({ id: chatId, title: '新对话', timestamp: Date.now(), knowledgeId: '0', context, messages: [] });
            setBiHistory(prev => [chat, ...prev.filter(item => item.id !== chatId)]);
            setCurrentChatId(chatId);
            setMessages([]);
            messagesCache.current[chatId] = [];
            activeChatRef.current = chatId;
            applyChatContext(context);
            setActiveTab('bi');
            navigateTo(`/chat/${chatId}`);
            return chatId;
        } catch (e) {
            showAlert(`创建失败: ${e.message}`, '错误', 'error');
            return null;
        } finally {
            setUploadLoading(false);
        }
    }, [applyChatContext, normalizeContext, normalizeSession, showAlert]);

    useEffect(() => {
        if (!currentUser || currentChatId || normalizeAppPath(window.location.pathname) !== '/chat') return;
        createGeneralChat();
    }, [currentUser, currentChatId, createGeneralChat]);

    const bindDatasourceContext = useCallback(async (chatId, datasourceName) => {
        const datasource = datasources.find(item => item.name === datasourceName);
        if (!datasource) throw new Error('数据源不存在');
        const contextType = datasource.type === 'excel' ? 'excel' : 'bi';
        const updated = await api.updateChatContext(chatId, contextType, { contextRefName: datasourceName, datasourceName });
        const nextContext = normalizeContext(updated?.context || { type: contextType, ref_name: datasourceName, datasource_name: datasourceName });
        nextContext.datasource_name = datasourceName;
        nextContext.ref_name = datasourceName;
        setContextMenuOpen(false);
        applyChatContext(nextContext);
        setCurrentChatId(chatId);
        activeChatRef.current = chatId;
        navigateTo(`/chat/${chatId}`);
        setActiveTab(contextType === 'excel' ? 'excel' : 'bi');
        if (contextType === 'excel') {
            await api.initExcelFromDatasource(datasourceName, chatId);
            await loadExcelDataByChatId(chatId);
        }
        if (contextType === 'excel') {
            setBiHistory(prev => prev.filter(item => item.id !== chatId));
            setExcelHistory(prev => {
                const exists = prev.some(item => item.id === chatId);
                if (exists) return prev.map(item => item.id === chatId ? { ...item, context: nextContext, datasourceName } : item);
                return [{ id: chatId, title: datasourceName || '新对话', timestamp: Date.now(), datasourceName, context: nextContext, messages: [] }, ...prev];
            });
        } else {
            setExcelHistory(prev => prev.filter(item => item.id !== chatId));
            setBiHistory(prev => {
                const exists = prev.some(item => item.id === chatId);
                if (exists) return prev.map(item => item.id === chatId ? { ...item, context: nextContext, datasourceName } : item);
                return [{ id: chatId, title: '新对话', timestamp: Date.now(), datasourceName, context: nextContext, messages: [] }, ...prev];
            });
        }
    }, [applyChatContext, datasources, loadExcelDataByChatId, normalizeContext]);

    const bindTeamContext = useCallback(async (chatId, teamId, teamName) => {
        const updated = await api.updateChatContext(chatId, 'team', { contextRefId: teamId, contextRefName: teamName });
        const nextContext = normalizeContext(updated.context || { type: 'team', ref_id: String(teamId), ref_name: teamName });
        applyChatContext(nextContext);
        setCurrentChatId(chatId);
        activeChatRef.current = chatId;
        navigateTo(`/chat/${chatId}`);
        setActiveTab('bi');
        setBiHistory(prev => {
            const exists = prev.some(item => item.id === chatId);
            if (exists) return prev.map(item => item.id === chatId ? { ...item, context: nextContext } : item);
            return [{ id: chatId, title: '新对话', timestamp: Date.now(), context: nextContext, messages: [] }, ...prev];
        });
    }, [applyChatContext, normalizeContext]);

    const clearCurrentContext = useCallback(async () => {
        if (!currentChatId) return;
        await api.clearChatContext(currentChatId);
        const nextContext = normalizeContext(DEFAULT_CONTEXT);
        applyChatContext(nextContext);
        setBiHistory(prev => prev.map(item => item.id === currentChatId ? { ...item, context: nextContext, datasourceName: null } : item));
        setExcelHistory(prev => prev.map(item => item.id === currentChatId ? { ...item, context: nextContext, datasourceName: null } : item));
    }, [applyChatContext, currentChatId, normalizeContext]);

    const shouldUseFirstQuestionTitle = useCallback((item) => {
        if (!item) return true;
        const currentTitle = (item.title || '').trim();
        const contextType = item.context?.type || 'general';
        const datasourceName = (item.datasourceName || item.context?.datasource_name || item.context?.ref_name || '').trim();
        const reservedTitles = new Set(['', '新对话', 'Excel 分析', '智能分析助手']);
        if (reservedTitles.has(currentTitle)) return true;
        if (currentTitle.endsWith('分析')) return true;
        if (datasourceName && (currentTitle === datasourceName || currentTitle === `${datasourceName}分析` || currentTitle === `${datasourceName} 分析`)) return true;
        if (contextType === 'general' && currentTitle === '普通对话') return true;
        return false;
    }, []);

    const sendMessage = useCallback(async (questionOverride = null) => {
        const nextQuestion = typeof questionOverride === 'string' ? questionOverride : input;
        if (!currentChatId || !nextQuestion.trim() || messageLoading) return;
        const chatId = currentChatId;
        const userText = nextQuestion;
        const optimistic = [...(messagesCache.current[chatId] || []), { role: 'user', content: userText }, { role: 'assistant', content: '', isThinking: true, _shouldStream: true, structuredData: { thoughts: [], sseStages: [] } }];
        messagesCache.current[chatId] = optimistic;
        setMessages(optimistic);
        setInput('');
        setMessageLoading(true);
        setSseChatId(null);
        setTimeout(() => setSseChatId(chatId), 0);
        try {
            const payload = {
                chatId,
                question: userText,
                knowledgeId: currentChatMeta?.knowledgeId || '0',
                datasourceName: currentDatasourceName,
                teamId: currentTeamId,
                memoryCount: memoryEnabled ? 5 : 0,
                enableAnalysis: analysisEnabled,
                skillIds: selectedSkillIds,
            };
            let result;
            if (currentMode === 'team') {
                result = await api.runTeam(currentTeamId, chatId, userText, currentDatasourceName, selectedSkillIds);
            } else if (currentMode === 'excel') {
                result = await api.excelAsk(chatId, userText, payload.memoryCount, currentDatasourceName || '__excel__', analysisEnabled, selectedSkillIds);
            } else if (currentDatasourceName) {
                result = await api.biAsk(chatId, userText, payload.knowledgeId, currentDatasourceName, payload.memoryCount, analysisEnabled, selectedSkillIds);
            } else {
                result = await api.askGeneral(chatId, userText, selectedSkillIds);
            }

            let botText = result.answer || result.summary || result.content || '已回复';
            let structured = { summary: botText };
            if (currentMode === 'bi') {
                const data = result.question_response?.data || result.data || result;
                botText = data.summary || data.content || '分析完成';
                structured = { summary: botText, sql: data.sql, tables: data.tables, chart: data.chart, thoughts: result.question_response?.thoughts || result.thoughts || [] };
            } else if (currentMode === 'excel') {
                structured = { summary: botText, chart: result.chart, code: result.code || result.python_code, result: result.result, thoughts: result.question_response?.thoughts || result.thoughts || [] };
            } else if (currentMode === 'team') {
                structured = { summary: botText, team_name: result.team_name || currentTeamName, thoughts: [] };
            }

            const finalMessages = optimistic.map((item, idx, arr) => idx === arr.length - 1 ? { role: 'assistant', content: botText, structuredData: { ...structured, sseStages: item.structuredData?.sseStages || [] }, _shouldStream: true, isThinking: false } : item);
            messagesCache.current[chatId] = finalMessages;
            const firstQuestionTitle = userText.trim().slice(0, 30) || '新对话';
            const historyItem = {
                id: chatId,
                title: firstQuestionTitle,
                timestamp: Date.now(),
                datasourceName: currentDatasourceName,
                knowledgeId: currentChatMeta?.knowledgeId || '0',
                context: normalizeContext(chatContext),
                messages: []
            };
            if (chatContext.type === 'excel') {
                setBiHistory(prev => prev.filter(item => item.id !== chatId));
                setExcelHistory(prev => {
                    const exists = prev.some(item => item.id === chatId);
                    if (exists) {
                        return prev.map(item => item.id === chatId
                            ? { ...item, ...historyItem, title: shouldUseFirstQuestionTitle(item) ? firstQuestionTitle : item.title }
                            : item);
                    }
                    return [{ ...historyItem, title: firstQuestionTitle }, ...prev];
                });
            } else {
                setExcelHistory(prev => prev.filter(item => item.id !== chatId));
                setBiHistory(prev => {
                    const exists = prev.some(item => item.id === chatId);
                    if (exists) {
                        return prev.map(item => item.id === chatId
                            ? { ...item, ...historyItem, title: shouldUseFirstQuestionTitle(item) ? firstQuestionTitle : item.title }
                            : item);
                    }
                    return [{ ...historyItem, title: firstQuestionTitle }, ...prev];
                });
            }
            if (activeChatRef.current === chatId) setMessages(finalMessages);
            loadBiHistory();
            loadExcelHistory();
        } catch (e) {
            const failedMessages = optimistic.map((item, idx, arr) => idx === arr.length - 1 ? { role: 'assistant', content: `错误: ${e.message}`, isThinking: false } : item);
            messagesCache.current[chatId] = failedMessages;
            if (activeChatRef.current === chatId) setMessages(failedMessages);
        } finally {
            setMessageLoading(false);
            stopSSE();
        }
    }, [analysisEnabled, chatContext, currentChatId, currentChatMeta, currentDatasourceName, currentMode, currentTeamId, currentTeamName, input, loadBiHistory, loadExcelHistory, memoryEnabled, messageLoading, normalizeContext, selectedSkillIds, shouldUseFirstQuestionTitle, sseStages, stopSSE]);

    useEffect(() => {
        if (!sseChatId || (!sseStages.length && !sseError)) return;
        const current = messagesCache.current[sseChatId] || [];
        const next = current.map((item, idx, arr) => idx === arr.length - 1 && item.isThinking ? { ...item, structuredData: { ...(item.structuredData || {}), sseStages, sseError } } : item);
        messagesCache.current[sseChatId] = next;
        if (activeChatRef.current === sseChatId) setMessages(next);
    }, [sseChatId, sseStages, sseError]);

    useEffect(() => {
        const handleRouteChange = () => {
            const path = normalizeAppPath(window.location.pathname);
            if (path === '/datasource') setActiveTab('datasource');
            else if (path === '/global_config') setActiveTab('global_config');
            else if (path === '/knowledge_base') setActiveTab('knowledge_base');
            else if (path === '/history') setActiveTab('history');
            else if (path === '/report') setActiveTab('report');
            else if (path === '/users') setActiveTab('user_manager');
            else if (path === '/skills') setActiveTab('skills');
            else if (path === '/agents') setActiveTab('agents');
            else if (path === '/teams') setActiveTab('teams');
            else if (path === '/memory') setActiveTab('memory');
            else if (path.startsWith('/chat/')) {
                const id = path.split('/')[2];
                if (id === activeChatRef.current) return;
                const chat = allChatHistory.find(item => item.id === id) || { id, title: '新对话', timestamp: Date.now(), context: DEFAULT_CONTEXT, messages: [] };
                handleChatSwitch(chat);
            } else if (path === '/chat') {
                setActiveTab('new_chat');
                setMessages([]);
                activeChatRef.current = null;
                applyChatContext(DEFAULT_CONTEXT);
            } else {
                setActiveTab('new_chat');
                setMessages([]);
                activeChatRef.current = null;
                applyChatContext(DEFAULT_CONTEXT);
                setCurrentChatId(null);
            }
        };
        const clickAway = (e) => {
            if (!e.target.closest('[data-context-menu-root]')) setContextMenuOpen(false);
        };
        window.addEventListener('popstate', handleRouteChange);
        document.addEventListener('mousedown', clickAway);
        handleRouteChange();
        return () => {
            window.removeEventListener('popstate', handleRouteChange);
            document.removeEventListener('mousedown', clickAway);
        };
    }, [allChatHistory, applyChatContext, handleChatSwitch]);

    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages, messageLoading]);

    const updateRangeConfig = (idx, field, type, value) => {
        setFileConfigs(prev => {
            const currentVal = prev[idx]?.[field] || '';
            let [start, end] = currentVal.includes('-') ? currentVal.split('-') : [currentVal, currentVal];
            if (type === 'start') start = value;
            else end = value;
            const newVal = start === end || !end ? start : `${start}-${end}`;
            return { ...prev, [idx]: { ...prev[idx], [field]: newVal } };
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
                    <input type="number" min="1" value={start || ''} onChange={(e) => updateRangeConfig(idx, field, 'start', e.target.value)} className="w-12 bg-white border border-gray-200 rounded-lg px-2 py-1 text-center outline-none focus:border-emerald-500 font-bold" />
                    到
                    <input type="number" min="1" value={end || ''} onChange={(e) => updateRangeConfig(idx, field, 'end', e.target.value)} className="w-12 bg-white border border-gray-200 rounded-lg px-2 py-1 text-center outline-none focus:border-emerald-500 font-bold" />
                    行
                </div>
            </div>
        );
    };

    const handleNavigate = async (tab, subTab) => {
        if (tab === 'users') setActiveTab('user_manager');
        else if (tab === 'report') {
            setActiveTab('report');
            if (subTab) setReportCreateMode(subTab);
        } else if (tab === 'global_config') {
            setActiveTab('global_config');
            if (subTab) setGlobalConfigTab(subTab);
        } else if (['datasource', 'knowledge_base', 'history', 'skills', 'agents', 'teams', 'memory'].includes(tab)) {
            const nextTab = tab === 'knowledge_base' ? 'knowledge_base' : tab;
            navigateTo(`/${nextTab}`);
            setCurrentChatId(null);
            setActiveTab(nextTab);
        } else if (tab === 'bi' || tab === 'excel') {
            navigateTo('/chat');
            setCurrentChatId(null);
            applyChatContext(DEFAULT_CONTEXT);
            setActiveTab('bi');
            await createGeneralChat();
        }
    };

    const deleteChat = async (e, chat) => {
        e.stopPropagation();
        const confirmed = window.confirm('确定要删除这条对话记录吗？');
        if (!confirmed) return;
        try {
            const normalized = normalizeSession(chat);
            if (normalized.context.type === 'excel') {
                await api.deleteExcelChat(normalized.id);
            } else if (normalized.context.type === 'general') {
                await api.deleteChatSession(normalized.id);
            } else {
                await api.deleteBiSession(normalized.id);
            }
            setBiHistory(prev => prev.filter(item => item.id !== normalized.id));
            setExcelHistory(prev => prev.filter(item => item.id !== normalized.id));
            window.dispatchEvent(new Event('askbi-history-refresh'));
            if (currentChatId === normalized.id) {
                setCurrentChatId(null);
                setMessages([]);
                applyChatContext(DEFAULT_CONTEXT);
                navigateTo('/chat');
            }
        } catch (error) {
            showAlert(`删除失败: ${error.message}`, '错误', 'error');
        }
    };

    const handleDeleteReport = async (e, report) => {
        e.stopPropagation();
        if (!window.confirm(`确定要删除报表 "${report.display_file_name || report.report_type}" 吗？`)) return;
        try {
            const data = await api.deleteReport(report.report_id);
            if (data.success) setReportHistory(prev => prev.filter(item => item.report_id !== report.report_id));
        } catch {}
    };

    const handleLoadReport = (report) => {
        setActiveTab('report');
        setPendingLoadReport(report);
    };

    const handleRenameReport = async (reportId, newName) => {
        try {
            const data = await api.renameReport(reportId, newName);
            if (data.success) setReportHistory(prev => prev.map(item => item.report_id === reportId ? { ...item, display_file_name: newName } : item));
        } catch {}
    };

    const renderSidebar = () => (
        <Sidebar
            currentUser={currentUser}
            activeTab={activeTab}
            globalConfigTab={globalConfigTab}
            currentChatId={currentChatId}
            biHistory={biHistory}
            excelHistory={excelHistory}
            reportHistory={reportHistory}
            onDeleteChat={deleteChat}
            onDeleteReport={handleDeleteReport}
            onRenameReport={handleRenameReport}
            onLogout={handleLogout}
            onNavigate={async (tab, subTab) => {
                if (tab === 'bi') {
                    await createGeneralChat();
                    return;
                }
                await handleNavigate(tab, subTab);
            }}
            onLoadReport={handleLoadReport}
            onChatSwitch={handleChatSwitch}
        />
    );

    if (authChecking) {
        return <div className="min-h-screen bg-slate-900 flex items-center justify-center"><div className="w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full animate-spin"></div></div>;
    }
    if (!currentUser) return <LoginPage onLogin={handleLogin} />;

    const isAdmin = currentUser?.role === 'admin';
    const canViewAll = ['admin', 'manager'].includes(currentUser?.role);

    const openContextWithDatasource = async (name) => {
        setContextMenuOpen(false);
        const chatId = currentChatId || await createGeneralChat();
        if (chatId) {
            setCurrentChatId(chatId);
            applyChatContext({ ...chatContext, ref_name: name, datasource_name: name });
            await bindDatasourceContext(chatId, name);
        }
    };

    const openContextWithTeam = async (teamId, teamName) => {
        setContextMenuOpen(false);
        const chatId = currentChatId || await createGeneralChat();
        if (chatId) await bindTeamContext(chatId, teamId, teamName);
    };

    const uploadExcelFile = async (e) => {
        e.preventDefault();
        if (!selectedFiles.length) return;
        const chatId = currentChatId || await createGeneralChat();
        if (!chatId) return;
        setUploadLoading(true);
        try {
            await api.updateChatContext(chatId, 'excel', { contextRefName: '本地上传 Excel', datasourceName: '__excel__' });
            await api.uploadExcelFiles(chatId, selectedFiles, fileConfigs, false);
            const nextContext = { type: 'excel', ref_id: null, ref_name: '本地上传 Excel', datasource_name: '__excel__' };
            applyChatContext(nextContext);
            setCurrentChatId(chatId);
            setActiveTab('excel');
            setBiHistory(prev => prev.filter(item => item.id !== chatId));
            setExcelHistory(prev => {
                const exists = prev.some(item => item.id === chatId);
                if (exists) return prev.map(item => item.id === chatId ? { ...item, context: nextContext, datasourceName: '__excel__' } : item);
                return [{ id: chatId, title: 'Excel 分析', timestamp: Date.now(), datasourceName: '__excel__', context: nextContext, messages: [] }, ...prev];
            });
            await loadExcelDataByChatId(chatId);
            setSelectedFiles([]);
            setFileConfigs({});
            navigateTo(`/chat/${chatId}`);
        } catch (e2) {
            showAlert(`上传失败: ${e2.message}`, '错误', 'error');
        } finally {
            setUploadLoading(false);
        }
    };

    return (
        <div className="flex h-screen font-sans bg-gray-50 overflow-hidden">
            {renderSidebar()}
            <div className="flex-1 flex flex-col relative bg-transparent overflow-hidden h-full">
                {activeTab === 'datasource' ? (
                    <DataSourceConfig onSelect={openContextWithDatasource} onConfigChange={loadDatasources} isAdmin={canViewAll} showAlert={showAlert} />
                ) : activeTab === 'knowledge_base' ? (
                    <KnowledgeBaseManager showAlert={showAlert} />
                ) : activeTab === 'global_config' ? (
                    <GlobalConfigManager isAdmin={canViewAll} showAlert={showAlert} initialTab={globalConfigTab} />
                ) : activeTab === 'history' ? (
                    <HistoryManager currentUser={currentUser} onChatSwitch={handleChatSwitch} onLoadReport={handleLoadReport} showAlert={showAlert} isAdmin={canViewAll} />
                ) : activeTab === 'report' ? (
                    <ReportManager showAlert={showAlert} initialCreateMode={reportCreateMode} onCreateModeConsumed={() => setReportCreateMode(null)} pendingLoadReport={pendingLoadReport} onPendingLoadConsumed={() => setPendingLoadReport(null)} onReportCreated={loadReportHistory} />
                ) : activeTab === 'user_manager' && isAdmin ? (
                    <UserManager token={authToken} showAlert={showAlert} />
                ) : activeTab === 'skills' ? (
                    <SkillManager showAlert={showAlert} />
                ) : activeTab === 'agents' ? (
                    <AgentManager showAlert={showAlert} />
                ) : activeTab === 'teams' ? (
                    <TeamList showAlert={showAlert} />
                ) : activeTab === 'memory' ? (
                    <MemoryManager currentUser={currentUser} currentChatId={currentChatId} showAlert={showAlert} />
                ) : (
                    <>
                        <div className="h-16 bg-white/80 backdrop-blur border-b border-gray-200/60 flex items-center justify-between px-8 shadow-sm z-10">
                            <div className="flex items-center gap-4">
                                <div className={`p-1.5 rounded-lg ${headerIconTone}`}>{headerIconNode}</div>
                                <div>
                                    <h2 className="font-bold text-gray-800 text-sm">{headerTitle}</h2>
                                    {currentChatId && <div className="text-[10px] text-gray-400 font-mono flex items-center gap-2"><span className={`w-1.5 h-1.5 rounded-full ${headerPulseTone} animate-pulse`}></span>ID: {currentChatId}</div>}
                                </div>
                            </div>
                            <div className="flex gap-3 items-center">
                                {currentChatId && !!contextTagText && <div className={`px-3 py-1.5 rounded-full border text-xs font-bold flex items-center gap-2 ${contextTagClass}`}>{contextIconNode}<span>{contextTagText}</span>{currentMode !== 'general' && <button onClick={clearCurrentContext}><Icons.X /></button>}</div>}
                                {currentMode === 'bi' && currentChatId && <button onClick={() => setShowSchemaViewer(true)} className="px-4 py-1.5 bg-indigo-50 text-indigo-600 rounded-lg text-xs font-bold hover:bg-indigo-100 transition-all flex items-center gap-2"><Icons.Database className="w-4 h-4" />数据详情</button>}
                                <div className="px-3 py-1 rounded-full bg-gray-100 border border-gray-200 text-xs font-mono font-bold text-gray-500">AskBI</div>
                            </div>
                        </div>

                        {shouldShowExcelTabs && (
                            <div className="px-8 py-3 border-b border-gray-200/60 bg-white/50 flex gap-4 items-center">
                                <div className="flex gap-2 bg-gray-100 rounded-lg p-1">
                                    <button onClick={() => setExcelViewMode('chat')} className={`px-4 py-1.5 rounded-md text-sm font-medium transition-all ${excelViewMode === 'chat' ? 'bg-white text-emerald-600 shadow-sm' : 'text-gray-600 hover:text-gray-800'}`}>问答</button>
                                    <button onClick={() => { setExcelViewMode('data'); loadExcelDataByChatId(currentChatId); }} className={`px-4 py-1.5 rounded-md text-sm font-medium transition-all ${excelViewMode === 'data' ? 'bg-white text-emerald-600 shadow-sm' : 'text-gray-600 hover:text-gray-800'}`}>数据</button>
                                </div>
                            </div>
                        )}

                        <div className="flex-1 relative overflow-y-auto overflow-x-hidden flex flex-col main-scrollbar">
                            <div className="absolute inset-0 opacity-[0.03] pointer-events-none" style={{ backgroundImage: 'radial-gradient(#64748b 1px, transparent 1px)', backgroundSize: '24px 24px' }}></div>
                            {shouldShowExcelDataPane ? (
                                <div className="flex-1 overflow-y-auto p-6 main-scrollbar relative z-10">
                                    {loadingData ? <div className="flex items-center justify-center h-full"><LoadingDots /></div> : <div className="max-w-7xl mx-auto"><div className="text-sm text-gray-500">已加载 Excel 数据。</div></div>}
                                </div>
                            ) : (
                                <div className={`flex-1 ${shouldShowEmptyPrompt ? 'overflow-hidden p-6' : 'overflow-y-auto p-6 pb-40 space-y-8 scroll-smooth main-scrollbar'} relative z-10 bg-transparent`}>
                                    {shouldShowEmptyPrompt && <div className="absolute inset-0 -translate-y-20 flex flex-col items-center justify-center text-center select-none pointer-events-none"><div className="mb-8 text-6xl font-black tracking-tight bg-gradient-to-r from-blue-600 via-indigo-600 to-cyan-500 bg-clip-text text-transparent drop-shadow-sm">AskBI</div><div className="text-sm font-medium text-gray-400">统一会话驱动的智能分析平台</div></div>}
                                    {messages.map((msg, idx) => <MessageItem key={idx} idx={idx} msg={msg} activeTab={currentMode === 'general' ? 'bi' : currentMode} currentChatId={currentChatId} showAlert={showAlert} onUpdateMessage={(i, content) => {
                                        const next = [...messages];
                                        if (next[i].structuredData) next[i].structuredData.summary = content;
                                        else next[i].content = content;
                                        setMessages(next);
                                        messagesCache.current[currentChatId] = next;
                                    }} />)}
                                    {messageLoading && <div className="flex justify-start max-w-5xl mx-auto w-full px-4"><div className="flex items-start gap-4"><div className={`w-10 h-10 rounded-full flex items-center justify-center border ${assistantAvatarTone}`}><Icons.Bot /></div><LoadingDots /></div></div>}
                                    <div ref={messagesEndRef} className="h-4" />
                                </div>
                            )}

                            {shouldShowComposer && (
                                <div className={`${shouldCenterComposer ? 'absolute inset-0 flex items-center justify-center px-6 py-6 pt-40' : 'absolute bottom-0 left-0 right-0 px-6 pb-6 pt-6'} bg-transparent z-30 pointer-events-none`}>
                                    <div className={`w-full ${shouldCenterComposer ? 'max-w-3xl' : 'max-w-4xl mx-auto'} space-y-4 bg-transparent pointer-events-auto`}>
                                        <div className={`bg-white rounded-2xl shadow-xl border p-2 flex flex-col group transition-all ${!currentChatId ? 'opacity-50 border-gray-100 grayscale cursor-not-allowed' : 'border-gray-100 focus-within:border-blue-400 focus-within:ring-4 focus-within:ring-blue-500/10'}`}>
                                            {currentChatId && !!contextTagText && <div className="px-4 pt-3 flex items-center gap-2 text-xs"><span className={`inline-flex items-center gap-2 px-3 py-1 rounded-full border font-bold ${contextTagClass}`}>{contextIconNode}{contextTagText}</span></div>}
                                            <textarea value={input} onChange={e => setInput(e.target.value)} onKeyUp={e => e.key === 'Enter' && !e.shiftKey && sendMessage()} disabled={messageLoading} placeholder={shouldCenterComposer ? centeredComposerPlaceholder : composerPlaceholder} className="flex-1 bg-transparent border-none focus:ring-0 outline-none text-gray-700 px-4 py-3 max-h-32 min-h-[56px] resize-none text-sm" rows="1" />
                                            <div className="flex justify-between items-center px-4 pb-2">
                                                <div className="flex items-center gap-2">
                                                    <div className="relative" data-context-menu-root>
                                                        <button onClick={() => setContextMenuOpen(prev => !prev)} className="flex items-center gap-1.5 px-3 py-1 rounded-lg text-[11px] font-bold transition-all border bg-slate-50 border-slate-200 text-slate-600 shadow-sm"><Icons.Plus className="w-3 h-3" />{chatContext.type === 'team' ? (currentTeamName || '选择数据源') : (currentDatasourceName || '选择数据源')}</button>
                                                        {contextMenuOpen && currentChatId && (
                                                            <div className="absolute bottom-full left-0 mb-2 w-72 bg-white rounded-xl border border-gray-200 shadow-xl z-50 overflow-hidden">
                                                                <div className="px-3 py-2 bg-gray-50 border-b border-gray-100 text-[11px] font-bold text-gray-600">选择数据源</div>
                                                                <div className="max-h-72 overflow-y-auto p-2 space-y-1">
                                                                    <button onClick={clearCurrentContext} className="w-full text-left px-3 py-2 rounded-lg hover:bg-gray-50 text-sm text-gray-700">清除数据源选择</button>
                                                                    {datasources.map(ds => <button key={ds.name} onClick={() => openContextWithDatasource(ds.name)} className="w-full text-left px-3 py-2 rounded-lg hover:bg-blue-50 text-sm text-gray-700 flex items-center justify-between"><span>{ds.display_name || ds.name}</span><span className="text-[10px] text-gray-400">{ds.type === 'excel' ? 'Excel' : 'BI'}</span></button>)}
                                                                    {availableTeams.map(team => <button key={team.id} onClick={() => openContextWithTeam(team.id, team.name)} className="w-full text-left px-3 py-2 rounded-lg hover:bg-cyan-50 text-sm text-gray-700 flex items-center justify-between"><span>{team.name}</span><span className="text-[10px] text-gray-400">Team</span></button>)}
                                                                </div>
                                                            </div>
                                                        )}
                                                    </div>
                                                    <button onClick={() => currentChatId && setMemoryEnabled(!memoryEnabled)} disabled={!currentChatId} className={`flex items-center gap-1.5 px-3 py-1 rounded-lg text-[11px] font-bold transition-all border ${memoryEnabled && currentChatId ? 'bg-blue-50 border-blue-200 text-blue-600 shadow-sm' : 'bg-gray-50 border-gray-100 text-gray-400'}`}><Icons.RefreshCw className={`w-3 h-3 ${memoryEnabled && currentChatId ? 'text-blue-500 animate-spin-slow' : 'text-gray-300'}`} />上下文记忆</button>
                                                    {shouldShowAnalysisToggle && <button onClick={() => currentChatId && setAnalysisEnabled(!analysisEnabled)} disabled={!currentChatId} className={`flex items-center gap-1.5 px-3 py-1 rounded-lg text-[11px] font-bold transition-all border ${analysisEnabled && currentChatId ? 'bg-amber-50 border-amber-200 text-amber-700 shadow-sm' : 'bg-gray-50 border-gray-100 text-gray-400'}`}><Icons.Bot className={`w-3 h-3 ${analysisEnabled && currentChatId ? 'text-amber-600' : 'text-gray-300'}`} />分析解读</button>}
                                                    {currentChatId && <SkillSelector selectedIds={selectedSkillIds} onChange={setSelectedSkillIds} showAlert={showAlert} />}
                                                </div>
                                                <button onClick={sendMessage} disabled={messageLoading || !input.trim()} className={`p-2 rounded-xl transition-all ${messageLoading || !input.trim() ? 'bg-gray-100 text-gray-400' : `${sendButtonClass} shadow-lg active:scale-95`}`}><Icons.Send className="w-4 h-4" /></button>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            )}
                        </div>
                    </>
                )}
            </div>

            {showSchemaViewer && <SchemaViewer onClose={() => setShowSchemaViewer(false)} datasourceName={currentDatasourceName} showAlert={showAlert} />}
            {showKnowledgeEditor && <KnowledgeEditor onClose={() => setShowKnowledgeEditor(false)} datasourceName={currentDatasourceName} isGlobal={false} type="knowledge" showAlert={showAlert} />}
            {uploadLoading && <div className="fixed inset-0 bg-black/40 backdrop-blur-sm z-[9999] flex items-center justify-center animate-fade-in"><div className="bg-white p-8 rounded-3xl shadow-2xl flex flex-col items-center gap-4 animate-slide-up"><div className="relative"><div className="w-16 h-16 border-4 border-blue-100 border-t-blue-600 rounded-full animate-spin"></div><div className="absolute inset-0 flex items-center justify-center"><Icons.RefreshCw className="w-6 h-6 text-blue-600 animate-pulse" /></div></div><div className="text-center"><h3 className="text-lg font-black text-gray-800">正在准备分析环境</h3><p className="text-sm text-gray-500 mt-1">正在更新会话上下文并准备执行环境，请稍候...</p></div></div></div>}
            <Modal isOpen={modalState.isOpen} onClose={closeModal} title={modalState.title} message={modalState.message} type={modalState.type} onConfirm={modalState.onConfirm} onCancel={modalState.onCancel} />
        </div>
    );
};

export default App;
