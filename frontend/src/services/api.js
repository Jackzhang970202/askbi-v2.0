/**
 * API Service Layer
 * Encapsulates all backend communication.
 */

export const APP_BASE = '/askbi';
const BASE_URL = APP_BASE;
export const withBase = (path = '') => `${APP_BASE}${path.startsWith('/') ? path : `/${path}`}`;
// Proxy handles routing

const getAuthHeaders = (isMultipart = false) => {
    const token = localStorage.getItem('askbi_token');
    const headers = {};
    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }
    if (!isMultipart) {
        headers['Content-Type'] = 'application/json';
    }
    return headers;
};

export const api = {
    // BI Routes
    async createBiChat(knowledgeId, datasourceName = null) {
        const body = { knowledge_id: knowledgeId };
        if (datasourceName) {
            body.datasource_name = datasourceName;
            body.context_type = 'bi';
            body.context_ref_name = datasourceName;
        }
        const res = await fetch(`${BASE_URL}/create_chat`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify(body)
        });
        if (!res.ok) throw new Error(`Create chat failed: ${res.status}`);
        return await res.json();
    },

    async createGeneralChat() {
        const res = await fetch(`${BASE_URL}/create_chat`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify({ context_type: 'general' })
        });
        if (!res.ok) throw new Error(`Create chat failed: ${res.status}`);
        return await res.json();
    },

    async askGeneral(chatId, question, skillIds = null) {
        const body = { chatid: chatId, question };
        if (skillIds !== null) body.skill_ids = skillIds;
        const res = await fetch(`${BASE_URL}/chat/ask`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify(body)
        });
        if (!res.ok) throw new Error(`Request failed: ${res.status}`);
        return await res.json();
    },

    async updateChatContext(chatId, contextType, options = {}) {
        const body = {
            chatid: chatId,
            context_type: contextType,
            context_ref_id: options.contextRefId ?? null,
            context_ref_name: options.contextRefName ?? null,
            datasource_name: options.datasourceName ?? null,
        };
        const res = await fetch(`${BASE_URL}/chat/context`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify(body)
        });
        if (!res.ok) throw new Error(`Update context failed: ${res.status}`);
        return await res.json();
    },

    async clearChatContext(chatId) {
        const res = await fetch(`${BASE_URL}/chat/context/clear`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify({ chatid: chatId })
        });
        if (!res.ok) throw new Error(`Clear context failed: ${res.status}`);
        return await res.json();
    },

    async getChatContext(chatId) {
        const res = await fetch(`${BASE_URL}/chat/context?chatid=${encodeURIComponent(chatId)}`, {
            headers: getAuthHeaders()
        });
        if (!res.ok) throw new Error(`Get context failed: ${res.status}`);
        return await res.json();
    },

    async listChatSessions() {
        const res = await fetch(`${BASE_URL}/chat/sessions`, {
            headers: getAuthHeaders()
        });
        if (!res.ok) throw new Error(`Failed to list sessions: ${res.status}`);
        return await res.json();
    },

    async getChatSession(chatId) {
        const res = await fetch(`${BASE_URL}/chat/sessions/${encodeURIComponent(chatId)}`, {
            headers: getAuthHeaders()
        });
        if (!res.ok) throw new Error(`Failed to get session: ${res.status}`);
        return await res.json();
    },

    async getGeneralMessages(chatId) {
        const res = await fetch(`${BASE_URL}/chat/messages/${encodeURIComponent(chatId)}`, {
            headers: getAuthHeaders()
        });
        if (!res.ok) throw new Error(`Failed to get messages: ${res.status}`);
        return await res.json();
    },

    async deleteChatSession(chatId) {
        const res = await fetch(`${BASE_URL}/chat/sessions/${encodeURIComponent(chatId)}`, {
            method: 'DELETE',
            headers: getAuthHeaders()
        });
        if (!res.ok) throw new Error(`Delete failed: ${res.status}`);
        return await res.json();
    },

    async getGeneralProgress(chatId, offset = 0) {
        const res = await fetch(`${BASE_URL}/chat/progress?chatid=${encodeURIComponent(chatId)}&offset=${offset}`, {
            headers: getAuthHeaders()
        });
        if (!res.ok) throw new Error(`Progress failed: ${res.status}`);
        return await res.json();
    },

    async createTeamChat(teamId, teamName, datasourceName = null) {
        const body = {
            context_type: 'team',
            context_ref_id: String(teamId),
            context_ref_name: teamName,
        };
        if (datasourceName) body.datasource_name = datasourceName;
        const res = await fetch(`${BASE_URL}/create_chat`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify(body)
        });
        if (!res.ok) throw new Error(`Create team chat failed: ${res.status}`);
        return await res.json();
    },

    async createExcelChat(datasourceName = null) {
        const body = { context_type: 'excel' };
        if (datasourceName) {
            body.datasource_name = datasourceName;
            body.context_ref_name = datasourceName;
        }
        const res = await fetch(`${BASE_URL}/create_chat`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify(body)
        });
        if (!res.ok) throw new Error(`Create excel chat failed: ${res.status}`);
        return await res.json();
    },

    async getProgressByContext(chatId, contextType, opts = {}) {
        if (contextType === 'excel') return this.getExcelProgress(chatId);
        if (contextType === 'team') return this.getGeneralProgress(chatId, 0);
        return this.getGeneralProgress(chatId, 0);
    },

    async getMessagesByContext(chatId, contextType) {
        if (contextType === 'excel') return this.getExcelMessages(chatId);
        if (contextType === 'general') return this.getGeneralMessages(chatId);
        return this.getBiMessages(chatId);
    },

    async deleteSessionByContext(chatId, contextType) {
        if (contextType === 'excel') return this.deleteExcelChat(chatId);
        if (contextType === 'general') return this.deleteChatSession(chatId);
        return this.deleteBiSession(chatId);
    },

    async createChatForContext(contextType, options = {}) {
        if (contextType === 'bi') return this.createBiChat(options.knowledgeId || '0', options.datasourceName || null);
        if (contextType === 'excel') return this.createExcelChat(options.datasourceName || null);
        if (contextType === 'team') return this.createTeamChat(options.teamId, options.teamName, options.datasourceName || null);
        return this.createGeneralChat();
    },

    async sendMessageByContext(contextType, payload) {
        if (contextType === 'bi') {
            return this.biAsk(payload.chatId, payload.question, payload.knowledgeId, payload.datasourceName, payload.memoryCount, payload.enableAnalysis, payload.skillIds);
        }
        if (contextType === 'excel') {
            return this.excelAsk(payload.chatId, payload.question, payload.memoryCount, payload.datasourceName, payload.enableAnalysis, payload.skillIds);
        }
        if (contextType === 'team') {
            return this.runTeam(payload.teamId, payload.chatId, payload.question, payload.datasourceName, payload.skillIds);
        }
        return this.askGeneral(payload.chatId, payload.question, payload.skillIds);
    },

    async updateContextBySelection(chatId, selection) {
        if (!selection) return this.clearChatContext(chatId);
        if (selection.type === 'team') {
            return this.updateChatContext(chatId, 'team', {
                contextRefId: selection.teamId,
                contextRefName: selection.teamName,
                datasourceName: selection.datasourceName || null,
            });
        }
        if (selection.type === 'excel') {
            return this.updateChatContext(chatId, 'excel', {
                contextRefName: selection.datasourceName,
                datasourceName: selection.datasourceName,
            });
        }
        if (selection.type === 'bi') {
            return this.updateChatContext(chatId, 'bi', {
                contextRefName: selection.datasourceName,
                datasourceName: selection.datasourceName,
            });
        }
        return this.clearChatContext(chatId);
    },

    async hydrateChatSession(chatId) {
        const [sessionRes, msgRes] = await Promise.all([
            this.getChatSession(chatId),
            this.getGeneralMessages(chatId).catch(() => this.getBiMessages(chatId))
        ]);
        return { session: sessionRes.session, context: sessionRes.context, messages: msgRes.messages || [] };
    },

    async listUnifiedSessions() {
        return this.listChatSessions();
    },

    async createEmptyChat() {
        return this.createGeneralChat();
    },

    async detachChatContext(chatId) {
        return this.clearChatContext(chatId);
    },

    async attachDatasourceContext(chatId, datasourceName, isExcel = false) {
        return this.updateChatContext(chatId, isExcel ? 'excel' : 'bi', {
            contextRefName: datasourceName,
            datasourceName,
        });
    },

    async attachTeamContext(chatId, teamId, teamName, datasourceName = null) {
        return this.updateChatContext(chatId, 'team', {
            contextRefId: teamId,
            contextRefName: teamName,
            datasourceName,
        });
    },

    async getSessionMessages(chatId) {
        return this.getGeneralMessages(chatId);
    },

    async getSessionDetail(chatId) {
        return this.getChatSession(chatId);
    },

    async removeSession(chatId) {
        return this.deleteChatSession(chatId);
    },

    async routeByContext(context, payload) {
        const contextType = context?.type || 'general';
        return this.sendMessageByContext(contextType, payload);
    },

    async getChatStreamPath(chatId, context, opts = {}) {
        if (context?.type === 'excel') return withBase(`/excel/stream?chatid=${encodeURIComponent(chatId)}&token=${encodeURIComponent(localStorage.getItem('askbi_token') || '')}`);
        if (context?.type === 'team' && opts.teamId) return withBase(`/teams/${opts.teamId}/stream?chatid=${encodeURIComponent(chatId)}&token=${encodeURIComponent(localStorage.getItem('askbi_token') || '')}`);
        if (context?.type === 'general') return withBase(`/chat/stream?chatid=${encodeURIComponent(chatId)}&token=${encodeURIComponent(localStorage.getItem('askbi_token') || '')}`);
        return withBase(`/stream?chatid=${encodeURIComponent(chatId)}&token=${encodeURIComponent(localStorage.getItem('askbi_token') || '')}`);
    },

    async getUnifiedMessages(chatId, contextType) {
        return this.getMessagesByContext(chatId, contextType || 'general');
    },

    async deleteUnifiedSession(chatId, contextType) {
        return this.deleteSessionByContext(chatId, contextType || 'general');
    },

    async createChat() {
        return this.createGeneralChat();
    },

    async bindContext(chatId, contextType, data = {}) {
        return this.updateChatContext(chatId, contextType, data);
    },

    async unbindContext(chatId) {
        return this.clearChatContext(chatId);
    },

    async askChat(chatId, question, context, options = {}) {
        return this.sendMessageByContext(context?.type || 'general', {
            chatId,
            question,
            knowledgeId: options.knowledgeId || '0',
            datasourceName: context?.datasource_name || context?.ref_name || options.datasourceName || null,
            teamId: context?.ref_id || options.teamId || null,
            memoryCount: options.memoryCount || 0,
            enableAnalysis: options.enableAnalysis || false,
            skillIds: options.skillIds ?? null,
        });
    },

    async fetchChatMessages(chatId, contextType) {
        return this.getMessagesByContext(chatId, contextType || 'general');
    },

    async fetchChatContext(chatId) {
        return this.getChatContext(chatId);
    },

    async fetchChatSessions() {
        return this.listChatSessions();
    },

    async listUserMemories(keyword = '', memoryKind = null, status = 'active', userId = null) {
        const params = new URLSearchParams();
        if (keyword) params.set('keyword', keyword);
        if (memoryKind) params.set('memory_kind', memoryKind);
        if (status) params.set('status', status);
        if (userId !== null && userId !== undefined) params.set('user_id', String(userId));
        const res = await fetch(`${BASE_URL}/memory/user?${params.toString()}`, { headers: getAuthHeaders() });
        const contentType = res.headers.get('content-type') || '';
        if (!contentType.includes('application/json')) throw new Error(`memory 接口返回了非 JSON 内容 (status=${res.status}, content-type=${contentType || 'unknown'})`);
        if (!res.ok) throw new Error(`Failed to list memories: ${res.status}`);
        return await res.json();
    },

    async listSessionMemories(chatId = null, status = 'active') {
        const url = chatId
            ? `${BASE_URL}/memory/session/${encodeURIComponent(chatId)}?status=${encodeURIComponent(status)}`
            : `${BASE_URL}/memory/session/_all?status=${encodeURIComponent(status)}`;
        const res = await fetch(url, { headers: getAuthHeaders() });
        if (!res.ok) throw new Error(`Failed to list session memories: ${res.status}`);
        return await res.json();
    },

    async listMemoryEvents(chatId = null, limit = 100) {
        const params = new URLSearchParams();
        if (chatId) params.set('chatid', chatId);
        params.set('limit', String(limit));
        const res = await fetch(`${BASE_URL}/memory/events?${params.toString()}`, { headers: getAuthHeaders() });
        if (!res.ok) throw new Error(`Failed to list memory events: ${res.status}`);
        return await res.json();
    },

    async updateMemory(scope, id, payload) {
        const res = await fetch(`${BASE_URL}/memory/${encodeURIComponent(scope)}/${encodeURIComponent(id)}`, {
            method: 'PUT',
            headers: getAuthHeaders(),
            body: JSON.stringify(payload),
        });
        if (!res.ok) throw new Error(`Failed to update memory: ${res.status}`);
        return await res.json();
    },

    async archiveMemory(scope, id) {
        const res = await fetch(`${BASE_URL}/memory/${encodeURIComponent(scope)}/${encodeURIComponent(id)}/archive`, {
            method: 'PATCH',
            headers: getAuthHeaders(),
        });
        if (!res.ok) throw new Error(`Failed to archive memory: ${res.status}`);
        return await res.json();
    },

    async deleteMemory(scope, id) {
        const res = await fetch(`${BASE_URL}/memory/${encodeURIComponent(scope)}/${encodeURIComponent(id)}`, {
            method: 'DELETE',
            headers: getAuthHeaders(),
        });
        if (!res.ok) throw new Error(`Failed to delete memory: ${res.status}`);
        return await res.json();
    },

    async summarizeSessionMemory(chatId) {
        const res = await fetch(`${BASE_URL}/memory/session/${encodeURIComponent(chatId)}/summarize`, {
            method: 'POST',
            headers: getAuthHeaders(),
        });
        if (!res.ok) throw new Error(`Failed to summarize session memory: ${res.status}`);
        return await res.json();
    },

    async biAsk(chatId, question, knowledgeId, datasourceName, memoryCount = 0, enableAnalysis = false, skillIds = null) {
        const body = {
            chatid: chatId,
            question,
            knowledge_id: knowledgeId || '0',
            datasource_name: datasourceName || null,
            memory_count: memoryCount,
            enable_analysis: enableAnalysis
        };
        if (skillIds !== null) body.skill_ids = skillIds;
        const res = await fetch(`${BASE_URL}/ask`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify(body)
        });
        if (!res.ok) throw new Error(`Request failed: ${res.status}`);
        return await res.json();
    },

    async getBiProgress(chatId, offset) {
        const res = await fetch(`${BASE_URL}/progress?chatid=${encodeURIComponent(chatId)}&offset=${offset}`, {
            headers: getAuthHeaders()
        });
        if (!res.ok) throw new Error(`Progress failed: ${res.status}`);
        return await res.json();
    },

    // Excel Routes
    async initExcelFromDatasource(datasourceName, chatId) {
        const formData = new FormData();
        formData.append('datasource_name', datasourceName);
        if (chatId) formData.append('chatid', chatId);
        
        const res = await fetch(`${BASE_URL}/excel/init_from_datasource`, {
            method: 'POST',
            headers: getAuthHeaders(true),
            body: formData
        });
        if (!res.ok) throw new Error(`Initialize from datasource failed: ${res.status}`);
        return await res.json();
    },

    async uploadExcelFiles(id, files, configs, isDatasource = true) {
        const formData = new FormData();
        if (isDatasource) {
            formData.append('datasource_name', id);
        } else {
            formData.append('chatid', id);
        }
        
        files.forEach((file, index) => {
            formData.append('file', file);
            const config = configs[index] || configs[file.name] || {};
            formData.append('table_header_rows', config.table_header_rows || '');
            formData.append('sub_name_rows', config.sub_name_rows || '');
        });

        const res = await fetch(`${BASE_URL}/excel/upload_file`, { 
            method: 'POST', 
            headers: getAuthHeaders(true),
            body: formData 
        });
        if (!res.ok) throw new Error(`Upload failed: ${res.status}`);
        return await res.json();
    },

    async excelAsk(chatId, question, memoryCount = 0, datasourceName = null, enableAnalysis = false, skillIds = null) {
        const body = {
            chatid: chatId,
            question,
            memory_count: memoryCount,
            datasource_name: datasourceName,
            enable_analysis: enableAnalysis
        };
        if (skillIds !== null) body.skill_ids = skillIds;
        const res = await fetch(`${BASE_URL}/excel/ask`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify(body)
        });
        if (!res.ok) throw new Error(`Request failed: ${res.status}`);
        return await res.json();
    },

    async getExcelProgress(chatId) {
        const res = await fetch(`${BASE_URL}/excel/progress?chatid=${encodeURIComponent(chatId)}`, {
            headers: getAuthHeaders()
        });
        if (!res.ok) throw new Error(`Progress failed: ${res.status}`);
        return await res.json();
    },

    async getExcelMessages(chatId) {
        const res = await fetch(`${BASE_URL}/excel/sessions/${encodeURIComponent(chatId)}/messages`, {
            headers: getAuthHeaders()
        });
        if (!res.ok) throw new Error(`Failed to get Excel messages: ${res.status}`);
        return await res.json();
    },

    async listExcelSessions() {
        const res = await fetch(`${BASE_URL}/excel/list_sessions`, {
            headers: getAuthHeaders()
        });
        if (!res.ok) throw new Error(`Failed to list sessions: ${res.status}`);
        return await res.json();
    },

    async getExcelFileData(chatId) {
        const res = await fetch(`${BASE_URL}/excel/get_file_data?chatid=${encodeURIComponent(chatId)}`, {
            headers: getAuthHeaders()
        });
        if (!res.ok) throw new Error(`Failed to get file data: ${res.status}`);
        return await res.json();
    },

    async deleteExcelChat(chatId) {
        const res = await fetch(`${BASE_URL}/excel/delete_chat?chatid=${encodeURIComponent(chatId)}`, {
            method: 'DELETE',
            headers: getAuthHeaders()
        });
        if (!res.ok) throw new Error(`Delete failed: ${res.status}`);
        return await res.json();
    },

    async downloadExcelFile(chatId, filename, isModified = false) {
        const token = localStorage.getItem('askbi_token');
        const url = `${BASE_URL}/excel/download_file?chatid=${encodeURIComponent(chatId)}&filename=${encodeURIComponent(filename)}&is_modified=${isModified}&token=${token}`;
        window.open(url, '_blank');
    },

    // 知识库 API
    async getGlobalKnowledge() {
        const res = await fetch(`${BASE_URL}/knowledge/global`, {
            headers: getAuthHeaders()
        });
        if (!res.ok) throw new Error('获取全局知识库失败');
        return await res.json();
    },

    async saveGlobalKnowledge(content) {
        const res = await fetch(`${BASE_URL}/knowledge/global`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify({ content })
        });
        if (!res.ok) throw new Error('保存全局知识库失败');
        return await res.json();
    },

    async getTempKnowledge(datasourceName) {
        const res = await fetch(`${BASE_URL}/knowledge/temp/${encodeURIComponent(datasourceName)}`, {
            headers: getAuthHeaders()
        });
        if (!res.ok) throw new Error('获取数据源知识失败');
        return await res.json();
    },

    async saveTempKnowledge(datasourceName, content, vocabulary, reference_sql) {
        const res = await fetch(`${BASE_URL}/knowledge/temp`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify({ datasource_name: datasourceName, content, vocabulary, reference_sql })
        });
        if (!res.ok) throw new Error('保存数据源知识失败');
        return await res.json();
    },

    async saveOriginalFile(chatId, filename, sheetName, data) {
        const formData = new FormData();
        formData.append('chatid', chatId);
        formData.append('filename', filename);
        formData.append('sheet_name', sheetName);
        formData.append('data', JSON.stringify(data));
        
        const res = await fetch(`${BASE_URL}/excel/save_original_file`, {
            method: 'POST',
            headers: getAuthHeaders(true),
            body: formData
        });
        if (!res.ok) throw new Error(`Save failed: ${res.status}`);
        return await res.json();
    },

    async saveModifiedFile(chatId, filename, sheetName, data) {
        const formData = new FormData();
        formData.append('chatid', chatId);
        formData.append('filename', filename);
        formData.append('sheet_name', sheetName);
        formData.append('data', JSON.stringify(data));
        
        const res = await fetch(`${BASE_URL}/excel/save_modified_file`, {
            method: 'POST',
            headers: getAuthHeaders(true),
            body: formData
        });
        if (!res.ok) throw new Error(`Save failed: ${res.status}`);
        return await res.json();
    },

    // 数据源管理 API
    async listDatasources() {
        const res = await fetch(`${BASE_URL}/datasources`, {
            headers: getAuthHeaders()
        });
        if (!res.ok) {
            const contentType = res.headers.get('content-type');
            if (contentType && contentType.includes('text/html')) {
                throw new Error(`服务器返回了 HTML 页面而不是 JSON。可能是后端 API 未运行或配置错误。状态码: ${res.status}`);
            }
            throw new Error(`Failed to list datasources: ${res.status}`);
        }
        return await res.json();
    },

    async addDatasource(name, type, config, knowledgeId = '0', files = [], fileConfigs = {}) {
        let res;
        if (type === 'excel' && files.length > 0) {
            const formData = new FormData();
            formData.append('name', name);
            formData.append('type', type);
            formData.append('knowledge_id', knowledgeId);
            files.forEach((file, index) => {
                formData.append('file', file);
                const cfg = fileConfigs[file.name] || fileConfigs[index] || {};
                formData.append('table_header_rows', cfg.table_header_rows || '');
                formData.append('sub_name_rows', cfg.sub_name_rows || '');
            });
            
            res = await fetch(`${BASE_URL}/datasources`, {
                method: 'POST',
                headers: getAuthHeaders(true),
                body: formData
            });
        } else {
            res = await fetch(`${BASE_URL}/datasources`, {
                method: 'POST',
                headers: getAuthHeaders(),
                body: JSON.stringify({ name, type, config, knowledge_id: knowledgeId })
            });
        }
        
        if (!res.ok) throw new Error(`Failed to add datasource: ${res.status}`);
        return await res.json();
    },

    async deleteDatasource(name) {
        const url = name
            ? `${BASE_URL}/datasources/${encodeURIComponent(name)}`
            : `${BASE_URL}/datasources?name=`;

        const res = await fetch(url, {
            method: 'DELETE',
            headers: getAuthHeaders()
        });
        if (!res.ok) throw new Error(`Failed to delete datasource: ${res.status}`);
        return await res.json();
    },

    // 📅 2026.03.26 新增：批量删除数据源
    async batchDeleteDatasources(names) {
        const res = await fetch(`${BASE_URL}/datasources/batch_delete`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify({ names })
        });
        if (!res.ok) {
            const errorData = await res.json().catch(() => ({}));
            throw new Error(errorData.error || `HTTP ${res.status}`);
        }
        return await res.json();
    },

    async getDatasource(name) {
        const res = await fetch(`${BASE_URL}/datasources/${encodeURIComponent(name)}`, {
            headers: getAuthHeaders()
        });
        if (!res.ok) throw new Error(`Failed to get datasource: ${res.status}`);
        return await res.json();
    },

    async testDatasource(name) {
        const res = await fetch(`${BASE_URL}/datasources/${encodeURIComponent(name)}/test`, {
            method: 'POST',
            headers: getAuthHeaders()
        });
        if (!res.ok) throw new Error(`Failed to test datasource: ${res.status}`);
        return await res.json();
    },

    async generateMetadata(name) {
        const res = await fetch(`${BASE_URL}/datasources/${encodeURIComponent(name)}/generate_metadata`, {
            method: 'POST',
            headers: getAuthHeaders()
        });
        if (!res.ok) {
            const errorData = await res.json().catch(() => ({ error: `HTTP ${res.status}` }));
            throw new Error(errorData.error || errorData.message || `Generate metadata failed: ${res.status}`);
        }
        return await res.json();
    },

    async getDatasourceTables(name, schema) {
        const url = schema 
            ? `${BASE_URL}/datasources/${encodeURIComponent(name)}/tables?schema=${encodeURIComponent(schema)}`
            : `${BASE_URL}/datasources/${encodeURIComponent(name)}/tables`;
        const res = await fetch(url, {
            headers: getAuthHeaders()
        });
        if (!res.ok) throw new Error(`Failed to get tables: ${res.status}`);
        return await res.json();
    },

    async getTableColumns(name, schema, table) {
        const res = await fetch(`${BASE_URL}/datasources/${encodeURIComponent(name)}/tables/${encodeURIComponent(schema)}/${encodeURIComponent(table)}/columns`, {
            headers: getAuthHeaders()
        });
        if (!res.ok) throw new Error(`Failed to get columns: ${res.status}`);
        return await res.json();
    },

    async getReferSchema(datasourceName) {
        const url = `${BASE_URL}/refer/schema?datasource_name=${encodeURIComponent(datasourceName)}`;
        const res = await fetch(url, {
            headers: getAuthHeaders()
        });
        if (!res.ok) {
            const errorData = await res.json().catch(() => ({}));
            throw new Error(errorData.error || `加载表结构失败: HTTP ${res.status}`);
        }
        return await res.json();
    },

    // BI Session API
    async listBiSessions() {
        const res = await fetch(`${BASE_URL}/bi/sessions`, {
            headers: getAuthHeaders()
        });
        if (!res.ok) throw new Error(`Failed to list BI sessions: ${res.status}`);
        return await res.json();
    },

    async getBiMessages(chatId) {
        const res = await fetch(`${BASE_URL}/bi/sessions/${encodeURIComponent(chatId)}/messages`, {
            headers: getAuthHeaders()
        });
        if (!res.ok) throw new Error(`Failed to get messages: ${res.status}`);
        return await res.json();
    },

    async deleteBiSession(chatId) {
        const res = await fetch(`${BASE_URL}/bi/sessions/${encodeURIComponent(chatId)}`, {
            method: 'DELETE',
            headers: getAuthHeaders()
        });
        if (!res.ok) throw new Error(`Delete failed: ${res.status}`);
        return await res.json();
    },

    // 外接知识库管理 API
    async listKnowledgeBases() {
        const res = await fetch(`${BASE_URL}/knowledge_bases`, {
            headers: getAuthHeaders()
        });
        if (!res.ok) throw new Error('获取知识库列表失败');
        return await res.json();
    },

    async addKnowledgeBase(id, name, type, description, api_url, headers) {
        const res = await fetch(`${BASE_URL}/knowledge_bases`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify({ id, name, type, description, api_url, headers })
        });
        if (!res.ok) throw new Error('添加知识库失败');
        return await res.json();
    },

    async deleteKnowledgeBase(id) {
        const res = await fetch(`${BASE_URL}/knowledge_bases/${encodeURIComponent(id)}`, {
            method: 'DELETE',
            headers: getAuthHeaders()
        });
        if (!res.ok) throw new Error('删除知识库失败');
        return await res.json();
    },

    // 全局配置 API
    async listGlobalConfigs(category) {
        let url = `${BASE_URL}/global_configs`;
        if (category) url += `?category=${encodeURIComponent(category)}`;
        const res = await fetch(url, {
            headers: getAuthHeaders()
        });
        if (!res.ok) {
            const errorData = await res.json().catch(() => ({}));
            throw new Error(errorData.error || `HTTP ${res.status}`);
        }
        return await res.json();
    },

    async saveGlobalConfig(config) {
        const res = await fetch(`${BASE_URL}/global_configs`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify(config)
        });
        if (!res.ok) {
            const errorData = await res.json().catch(() => ({}));
            throw new Error(errorData.error || `HTTP ${res.status}`);
        }
        return await res.json();
    },

    async deleteGlobalConfig(id) {
        const res = await fetch(`${BASE_URL}/global_configs/${id}`, {
            method: 'DELETE',
            headers: getAuthHeaders()
        });
        if (!res.ok) {
            const errorData = await res.json().catch(() => ({}));
            throw new Error(errorData.error || `HTTP ${res.status}`);
        }
        return await res.json();
    },

    async toggleGlobalConfig(id, isEnabled) {
        const res = await fetch(`${BASE_URL}/global_configs/${id}/toggle`, {
            method: 'PATCH',
            headers: getAuthHeaders(),
            body: JSON.stringify({ is_enabled: isEnabled })
        });
        if (!res.ok) {
            const errorData = await res.json().catch(() => ({}));
            throw new Error(errorData.error || `HTTP ${res.status}`);
        }
        return await res.json();
    },

    // 📅 2026.03.04 新增：报表生成 API
    // 📝 变更说明：添加报表生成和下载相关方法

    async generateReport(chatId, reportName, rule) {
        const res = await fetch(`${BASE_URL}/reports/generate`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify({
                chat_id: chatId,
                report_name: reportName,
                rule: rule || ''  // 传递用户配置的规则，前后提示词由后端硬编码
            })
        });
        if (!res.ok) {
            const errorData = await res.json().catch(() => ({}));
            throw new Error(errorData.error || `HTTP ${res.status}`);
        }
        return await res.json();
    },

    async downloadReport(chatId, filename) {
        const token = localStorage.getItem('askbi_token');
        const url = `${BASE_URL}/reports/download/${encodeURIComponent(chatId)}/${encodeURIComponent(filename)}?token=${token}`;
        window.open(url, '_blank');
    },

    async listReports(chatId) {
        const res = await fetch(`${BASE_URL}/reports/list/${encodeURIComponent(chatId)}`, {
            headers: getAuthHeaders()
        });
        if (!res.ok) {
            const errorData = await res.json().catch(() => ({}));
            throw new Error(errorData.error || `HTTP ${res.status}`);
        }
        return await res.json();
    },

    // 📅 2026.03.19 新增：固定规则报表管理 API
    // 📝 变更说明：添加独立报表管理的 API 方法

    async generateReportFromFiles(formData) {
        const res = await fetch(`${BASE_URL}/report/generate`, {
            method: 'POST',
            headers: getAuthHeaders(true),
            body: formData
        });
        if (!res.ok) {
            const errorData = await res.json().catch(() => ({}));
            throw new Error(errorData.error || `HTTP ${res.status}`);
        }
        return await res.json();
    },

    async toggleReportDesensitize(reportId, enable, columnConfig = null) {
        const body = { report_id: reportId, enable };
        if (columnConfig) {
            body.column_config = columnConfig;
        }
        const res = await fetch(`${BASE_URL}/report/desensitize`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify(body)
        });
        if (!res.ok) {
            const errorData = await res.json().catch(() => ({}));
            throw new Error(errorData.error || `HTTP ${res.status}`);
        }
        return await res.json();
    },

    // 📅 2026.03.19 新增：获取可用的脱敏方法列表
    async getDesensitizeMethods() {
        const res = await fetch(`${BASE_URL}/report/desensitize/methods`, {
            headers: getAuthHeaders()
        });
        if (!res.ok) {
            const errorData = await res.json().catch(() => ({}));
            throw new Error(errorData.error || `HTTP ${res.status}`);
        }
        return await res.json();
    },

    // 📅 2026.03.19 新增：获取报表列的脱敏预览配置
    async getDesensitizePreview(reportId) {
        const res = await fetch(`${BASE_URL}/report/desensitize/preview?report_id=${encodeURIComponent(reportId)}`, {
            headers: getAuthHeaders()
        });
        if (!res.ok) {
            const errorData = await res.json().catch(() => ({}));
            throw new Error(errorData.error || `HTTP ${res.status}`);
        }
        return await res.json();
    },

    async createReportAskSession(reportId, useDesensitized) {
        const res = await fetch(`${BASE_URL}/report/ask`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify({ report_id: reportId, use_desensitized: useDesensitized })
        });
        if (!res.ok) {
            const errorData = await res.json().catch(() => ({}));
            throw new Error(errorData.error || `HTTP ${res.status}`);
        }
        return await res.json();
    },

    async listUserReports() {
        const res = await fetch(`${BASE_URL}/report/list`, {
            headers: getAuthHeaders()
        });
        if (!res.ok) {
            const errorData = await res.json().catch(() => ({}));
            throw new Error(errorData.error || `HTTP ${res.status}`);
        }
        return await res.json();
    },

    // 📅 2026.03.19 新增：删除报表
    async deleteReport(reportId) {
        const res = await fetch(`${BASE_URL}/report/${encodeURIComponent(reportId)}`, {
            method: 'DELETE',
            headers: getAuthHeaders()
        });
        if (!res.ok) {
            const errorData = await res.json().catch(() => ({}));
            throw new Error(errorData.error || `HTTP ${res.status}`);
        }
        return await res.json();
    },

    // 📅 2026.04.02 新增：重命名报表
    async renameReport(reportId, newFileName) {
        const res = await fetch(`${BASE_URL}/report/${encodeURIComponent(reportId)}/rename`, {
            method: 'PUT',
            headers: getAuthHeaders(),
            body: JSON.stringify({ display_file_name: newFileName })
        });
        if (!res.ok) {
            const errorData = await res.json().catch(() => ({}));
            throw new Error(errorData.error || `HTTP ${res.status}`);
        }
        return await res.json();
    },

    // 📅 2026.03.19 新增：获取报表预览数据
    async getReportPreview(reportId) {
        const res = await fetch(`${BASE_URL}/report/preview/${encodeURIComponent(reportId)}`, {
            headers: getAuthHeaders()
        });
        if (!res.ok) {
            const errorData = await res.json().catch(() => ({}));
            throw new Error(errorData.error || `HTTP ${res.status}`);
        }
        return await res.json();
    },

    // 📅 2026.03.20 更新：下载固定规则报表（使用后端返回的文件名）
    downloadFixedReport(reportId, desensitized = false) {
        const token = localStorage.getItem('askbi_token');
        const url = `${BASE_URL}/report/download/${encodeURIComponent(reportId)}?desensitized=${desensitized}&token=${token}`;
        window.open(url, '_blank');
    },

    // 📅 2026.03.20 新增：获取报表下载文件名
    async getReportDownloadInfo(reportId) {
        const res = await fetch(`${BASE_URL}/report/download-info/${encodeURIComponent(reportId)}`, {
            headers: getAuthHeaders()
        });
        if (!res.ok) {
            const errorData = await res.json().catch(() => ({}));
            throw new Error(errorData.error || `HTTP ${res.status}`);
        }
        return await res.json();
    },

    // 📅 2026.03.20 新增：报表问数
    async askReportQuestion(reportId, question, memoryCount = 0) {
        const res = await fetch(`${BASE_URL}/report/ask-question`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify({
                report_id: reportId,
                question: question,
                memory_count: memoryCount
            })
        });
        if (!res.ok) {
            const errorData = await res.json().catch(() => ({}));
            throw new Error(errorData.error || `HTTP ${res.status}`);
        }
        return await res.json();
    },

    // 📅 2026.03.19 新增：获取报表完整数据（用于编辑）
    async getReportFullData(reportId) {
        const res = await fetch(`${BASE_URL}/report/full-data/${encodeURIComponent(reportId)}`, {
            headers: getAuthHeaders()
        });
        if (!res.ok) {
            const errorData = await res.json().catch(() => ({}));
            throw new Error(errorData.error || `HTTP ${res.status}`);
        }
        return await res.json();
    },

    // 📅 2026.03.19 新增：更新报表数据
    async updateReportData(reportId, data, columns) {
        const res = await fetch(`${BASE_URL}/report/update/${encodeURIComponent(reportId)}`, {
            method: 'PUT',
            headers: getAuthHeaders(),
            body: JSON.stringify({ data, columns })
        });
        if (!res.ok) {
            const errorData = await res.json().catch(() => ({}));
            throw new Error(errorData.error || `HTTP ${res.status}`);
        }
        return await res.json();
    },

    // 📅 2026.03.19 新增：AI智能改表
    async aiEditReport(reportId, sampleData, columns, userRequest) {
        const res = await fetch(`${BASE_URL}/report/ai-edit`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify({
                report_id: reportId,
                sample_data: sampleData,
                columns: columns,
                user_request: userRequest
            })
        });
        if (!res.ok) {
            const errorData = await res.json().catch(() => ({}));
            throw new Error(errorData.error || `HTTP ${res.status}`);
        }
        return await res.json();
    },

    // 📅 2026.03.24 新增：大屏管理 API
    async generateDashboard(formData) {
        const res = await fetch(`${BASE_URL}/dashboard/generate`, {
            method: 'POST',
            headers: getAuthHeaders(true),
            body: formData
        });
        if (!res.ok) {
            const errorData = await res.json().catch(() => ({}));
            throw new Error(errorData.error || `HTTP ${res.status}`);
        }
        return await res.json();
    },

    async deleteDashboard(dashboardId) {
        const res = await fetch(`${BASE_URL}/dashboard/${encodeURIComponent(dashboardId)}`, {
            method: 'DELETE',
            headers: getAuthHeaders()
        });
        if (!res.ok) {
            const errorData = await res.json().catch(() => ({}));
            throw new Error(errorData.error || `HTTP ${res.status}`);
        }
        return await res.json();
    },

    // ==================== Skills API ====================
    async listSkills() {
        const res = await fetch(`${BASE_URL}/skills`, { headers: getAuthHeaders() });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return await res.json();
    },

    async getSkill(id) {
        const res = await fetch(`${BASE_URL}/skills/${id}`, { headers: getAuthHeaders() });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return await res.json();
    },

    async createSkill(data) {
        const res = await fetch(`${BASE_URL}/skills`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify(data)
        });
        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            throw new Error(err.error || `HTTP ${res.status}`);
        }
        return await res.json();
    },

    async updateSkill(id, data) {
        const res = await fetch(`${BASE_URL}/skills/${id}`, {
            method: 'PUT',
            headers: getAuthHeaders(),
            body: JSON.stringify(data)
        });
        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            throw new Error(err.error || `HTTP ${res.status}`);
        }
        return await res.json();
    },

    async deleteSkill(id) {
        const res = await fetch(`${BASE_URL}/skills/${id}`, {
            method: 'DELETE',
            headers: getAuthHeaders()
        });
        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            throw new Error(err.error || `HTTP ${res.status}`);
        }
        return await res.json();
    },

    async toggleSkill(id) {
        const res = await fetch(`${BASE_URL}/skills/${id}/toggle`, {
            method: 'PATCH',
            headers: getAuthHeaders()
        });
        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            throw new Error(err.error || `HTTP ${res.status}`);
        }
        return await res.json();
    },

    // ==================== Agents API ====================
    async listAgents() {
        const res = await fetch(`${BASE_URL}/agents`, { headers: getAuthHeaders() });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return await res.json();
    },

    async getAgent(name) {
        const res = await fetch(`${BASE_URL}/agents/${encodeURIComponent(name)}`, { headers: getAuthHeaders() });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return await res.json();
    },

    async updateAgent(id, data) {
        const res = await fetch(`${BASE_URL}/agents/${id}`, {
            method: 'PUT',
            headers: getAuthHeaders(),
            body: JSON.stringify(data)
        });
        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            throw new Error(err.error || `HTTP ${res.status}`);
        }
        return await res.json();
    },

    async bindSkillsToAgent(agentId, skillIds) {
        const res = await fetch(`${BASE_URL}/agents/${agentId}/bind-skills`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify({ skill_ids: skillIds })
        });
        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            throw new Error(err.error || `HTTP ${res.status}`);
        }
        return await res.json();
    },

    async createCustomAgent(data) {
        const res = await fetch(`${BASE_URL}/teams/agents/custom`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify(data)
        });
        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            throw new Error(err.error || `HTTP ${res.status}`);
        }
        return await res.json();
    },

    // ==================== Teams API ====================
    async listTeams() {
        const res = await fetch(`${BASE_URL}/teams`, { headers: getAuthHeaders() });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return await res.json();
    },

    async getTeam(id) {
        const res = await fetch(`${BASE_URL}/teams/${id}`, { headers: getAuthHeaders() });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return await res.json();
    },

    async createTeam(data) {
        const res = await fetch(`${BASE_URL}/teams`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify(data)
        });
        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            throw new Error(err.error || `HTTP ${res.status}`);
        }
        return await res.json();
    },

    async updateTeam(id, data) {
        const res = await fetch(`${BASE_URL}/teams/${id}`, {
            method: 'PUT',
            headers: getAuthHeaders(),
            body: JSON.stringify(data)
        });
        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            throw new Error(err.error || `HTTP ${res.status}`);
        }
        return await res.json();
    },

    async deleteTeam(id) {
        const res = await fetch(`${BASE_URL}/teams/${id}`, {
            method: 'DELETE',
            headers: getAuthHeaders()
        });
        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            throw new Error(err.error || `HTTP ${res.status}`);
        }
        return await res.json();
    },

    async testTeam(id, message, datasourceName = null, skillIds = null) {
        const body = { message };
        if (datasourceName) body.datasource_name = datasourceName;
        if (skillIds) body.skill_ids = skillIds;
        const res = await fetch(`${BASE_URL}/teams/${id}/test`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify(body)
        });
        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            throw new Error(err.error || `HTTP ${res.status}`);
        }
        return await res.json();
    },

    async runTeam(teamId, chatId, question, datasourceName = null, skillIds = null) {
        const body = { chatid: chatId, question };
        if (datasourceName) body.datasource_name = datasourceName;
        if (skillIds !== null) body.skill_ids = skillIds;
        const res = await fetch(`${BASE_URL}/teams/${teamId}/run`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify(body)
        });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return await res.json();
    }
};
