// 📅 2026.03.20 重构：报表管理页面组件
// 📝 变更说明：改为左右分栏布局，左边编辑区，右边对话框，支持AI改表模式
// 📅 2026.03.20 更新：统一对话框、添加保存/撤销功能、单元格颜色标记
// 📅 2026.04.02 更新：移除问数功能，只保留报表和大屏生成功能
import React, { useState, useRef, useEffect, useCallback, useMemo } from 'react';
import { Icons } from './Icons';
import { api, withBase } from '../services/api';
import VegaChart from './VegaChart';
import ChatInput from './ChatInput';

// 解析Markdown内容
const parseMarkdown = (text) => {
    if (!text) return '';
    if (window.marked) {
        return window.marked.parse(text);
    }
    // 简单的Markdown处理（如果没有marked库）
    return text
        .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.+?)\*/g, '<em>$1</em>')
        .replace(/`(.+?)`/g, '<code class="bg-gray-100 px-1 rounded">$1</code>')
        .replace(/\n/g, '<br/>');
};

// 解析图表配置（Vega-Lite 格式）
const parseChartOptions = (chart) => {
    if (!chart) return null;
    try {
        let chartStr = typeof chart === 'string' ? chart : JSON.stringify(chart);
        chartStr = chartStr.replace(/```json/g, '').replace(/```/g, '');
        let parsed;
        try {
            parsed = JSON.parse(chartStr);
        } catch (e) {
            parsed = eval(`(${chartStr})`);
        }
        // 仅识别 Vega-Lite 格式（含 $schema 或 mark）
        if (parsed && (parsed.$schema || parsed.mark)) return parsed;
        if (parsed && parsed.chart_needed === false) return null;
        return null;
    } catch (e) {
        console.error("Chart parsing failed", e);
        return null;
    }
};

// 消息项组件 - 使用React.memo优化渲染
const MessageItem = React.memo(({ msg }) => {
    const content = msg.structuredData?.summary || msg.content;
    const chartOptions = useMemo(() => parseChartOptions(msg.structuredData?.chart), [msg.structuredData?.chart]);
    const htmlContent = useMemo(() => parseMarkdown(content), [content]);

    if (msg.role === 'user') {
        return (
            <div className="flex justify-end">
                <div className={`max-w-[85%] rounded-xl px-4 py-2 ${
                    msg.type === 'ai-edit' ? 'bg-purple-600 text-white' : 'bg-blue-600 text-white'
                }`}>
                    <p className="text-sm">{msg.content}</p>
                </div>
            </div>
        );
    }

    return (
        <div className="flex justify-start">
            <div className="max-w-[85%] rounded-xl bg-white border border-gray-200 p-4 shadow-sm">
                <div
                    className="markdown-body"
                    dangerouslySetInnerHTML={{ __html: htmlContent }}
                />
                {chartOptions && (
                    <div className="mt-4 pt-4 border-t border-gray-100">
                        <div className="flex items-center justify-center mb-2">
                            <span className="bg-gray-100 text-gray-500 text-xs px-2 py-0.5 rounded-full">图表</span>
                        </div>
                        <div className="bg-gray-50 rounded-lg p-2">
                            <VegaChart spec={chartOptions} />
                        </div>
                    </div>
                )}
                {msg.type === 'ai-edit' && msg.editResult && (
                    <div className="mt-2 pt-2 border-t border-gray-200 text-xs text-gray-500">
                        已修改 {msg.editResult.modifiedCount || msg.editResult.modifiedCells?.length || 0} 个单元格
                    </div>
                )}
            </div>
        </div>
    );
});

const REPORT_TYPES = [
    { id: 'hr_attendance', name: '人事考勤报表', description: '根据考勤明细和汇总表生成人事考勤报表' },
    { id: 'dept_attendance', name: '部门维度考勤报表', description: '根据个人维度明细和汇总表生成部门维度考勤报表' },
    { id: 'multi_month_hr', name: '多月个人维度报表', description: '根据多月考勤明细和汇总表生成合并的个人维度报表' },
    { id: 'multi_month_dept', name: '多月部门维度报表', description: '根据多月考勤明细和汇总表生成合并的部门维度报表' }
];

const ReportManager = ({ showAlert = () => {}, showConfirm = () => Promise.resolve(true), initialCreateMode, onCreateModeConsumed, pendingLoadReport, onPendingLoadConsumed, onReportCreated }) => {
    // ==================== 基础状态 ====================
    const [hasReport, setHasReport] = useState(false);
    const [selectedType, setSelectedType] = useState('');
    const [detailFile, setDetailFile] = useState(null);
    const [summaryFile, setSummaryFile] = useState(null);

    // 创建模式选择
    const [createMode, setCreateMode] = useState(null); // null | 'report' | 'dashboard'
    const [dashboardPersonalFile, setDashboardPersonalFile] = useState(null);
    const [dashboardDeptFile, setDashboardDeptFile] = useState(null);
    const [isDashboard, setIsDashboard] = useState(false);
    const [dashboardId, setDashboardId] = useState(null);

    // 生成状态
    const [isGenerating, setIsGenerating] = useState(false);
    const [generationProgress, setGenerationProgress] = useState(0);

    // 报表数据
    const [reportData, setReportData] = useState(null);
    const [reportId, setReportId] = useState(null);
    const [downloadFileName, setDownloadFileName] = useState('');
    const [previewData, setPreviewData] = useState([]);
    const [previewColumns, setPreviewColumns] = useState([]);

    // ==================== 右侧对话框状态 ====================
    const [messages, setMessages] = useState([]); // 统一消息列表
    const [isLoading, setIsLoading] = useState(false);

    // ==================== 编辑状态 ====================
    // 单元格修改记录 { human: {}, ai: {} }
    const [cellModifications, setCellModifications] = useState({ human: {}, ai: {} });
    // 撤销栈
    const [undoStack, setUndoStack] = useState([]);

    // 脱敏状态
    const [isDesensitized, setIsDesensitized] = useState(false);
    const [isDesensitizing, setIsDesensitizing] = useState(false);
    const [showDesensitizeModal, setShowDesensitizeModal] = useState(false);
    const [desensitizeMethods, setDesensitizeMethods] = useState([]);
    const [desensitizeColumnConfig, setDesensitizeColumnConfig] = useState({});
    const [loadingDesensitizeConfig, setLoadingDesensitizeConfig] = useState(false);

    // 历史记录状态
    const [reportHistory, setReportHistory] = useState([]);
    const [showHistoryDropdown, setShowHistoryDropdown] = useState(false);
    const [loadingHistory, setLoadingHistory] = useState(false);

    // 大屏过滤状态
    const [excludeZJL, setExcludeZJL] = useState(true); // 排除总经理室（默认启用）
    const [excludeSales, setExcludeSales] = useState(false); // 排除销售部门
    const [dashboardIframeReady, setDashboardIframeReady] = useState(false); // iframe 是否加载完成

    const detailInputRef = useRef(null);
    const summaryInputRef = useRef(null);
    const dashboardPersonalInputRef = useRef(null);
    const dashboardDeptInputRef = useRef(null);
    const messagesEndRef = useRef(null);
    const tableScrollRef = useRef(null);
    const scrollbarRef = useRef(null);
    const historyDropdownRef = useRef(null);

    // 自动滚动到底部
    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);

    // 发送过滤消息到大屏 iframe
    const sendFilterToDashboard = useCallback((excludeZJL, excludeSales) => {
        const iframe = document.getElementById('dashboard-iframe');
        if (iframe && iframe.contentWindow) {
            console.log('发送过滤消息到 iframe:', { excludeZJL, excludeSales });
            iframe.contentWindow.postMessage({
                type: 'DASHBOARD_FILTER',
                excludeZJL,
                excludeSales
            }, '*');
        }
    }, []);

    // 监听来自 iframe 的消息
    useEffect(() => {
        const handleMessage = (event) => {
            if (event.data && event.data.type === 'DASHBOARD_READY') {
                console.log('收到 iframe 就绪消息');
                setDashboardIframeReady(true);
            }
        };
        window.addEventListener('message', handleMessage);
        return () => window.removeEventListener('message', handleMessage);
    }, []);

    // 当过滤状态变化或 iframe 准备好时，发送消息到大屏
    useEffect(() => {
        if (isDashboard && dashboardId && dashboardIframeReady) {
            sendFilterToDashboard(excludeZJL, excludeSales);
        }
    }, [excludeZJL, excludeSales, isDashboard, dashboardId, dashboardIframeReady, sendFilterToDashboard]);

    // 重置所有报表状态到初始状态
    const resetAllStates = useCallback(() => {
        // 重置报表数据
        setHasReport(false);
        setSelectedType('');
        setDetailFile(null);
        setSummaryFile(null);
        setDashboardPersonalFile(null);
        setDashboardDeptFile(null);
        setIsDashboard(false);
        setDashboardId(null);
        setReportData(null);
        setReportId(null);
        setDownloadFileName('');
        setPreviewData([]);
        setPreviewColumns([]);
        setIsDesensitized(false);
        setIsDesensitizing(false);
        setDesensitizeColumnConfig({});
        setCellModifications({ human: {}, ai: {} });
        setUndoStack([]);
        setMessages([]);
        setIsLoading(false);
        setIsGenerating(false);
        setGenerationProgress(0);
        // 重置大屏过滤状态
        setExcludeZJL(true);  // 默认排除总经理室
        setExcludeSales(false);
        setDashboardIframeReady(false);
    }, []);

    // 响应外部传入的创建模式（来自侧边栏点击）
    useEffect(() => {
        if (initialCreateMode) {
            // 先重置所有状态，然后设置新的创建模式
            resetAllStates();
            setCreateMode(initialCreateMode);
            onCreateModeConsumed && onCreateModeConsumed();
        }
    }, [initialCreateMode, onCreateModeConsumed, resetAllStates]);

    // 响应侧边栏点击历史记录加载报表
    useEffect(() => {
        if (pendingLoadReport) {
            handleLoadReport(pendingLoadReport);
            onPendingLoadConsumed && onPendingLoadConsumed();
        }
    }, [pendingLoadReport, onPendingLoadConsumed]);

    // 点击外部关闭历史记录下拉
    useEffect(() => {
        const handleClickOutside = (e) => {
            if (historyDropdownRef.current && !historyDropdownRef.current.contains(e.target)) {
                setShowHistoryDropdown(false);
            }
        };
        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, []);

    // 同步横向滚动
    const handleTableScroll = useCallback((e) => {
        if (scrollbarRef.current && e.target === tableScrollRef.current) {
            scrollbarRef.current.scrollLeft = e.target.scrollLeft;
        }
    }, []);

    const handleScrollbarScroll = useCallback((e) => {
        if (tableScrollRef.current && e.target === scrollbarRef.current) {
            tableScrollRef.current.scrollLeft = e.target.scrollLeft;
        }
    }, []);

    // ==================== 历史记录功能 ====================
    // 加载历史报表列表
    const loadReportHistory = useCallback(async () => {
        setLoadingHistory(true);
        try {
            const response = await api.listUserReports();
            if (response.success) {
                setReportHistory(response.reports || []);
            }
        } catch (error) {
            console.error('加载历史报表失败:', error);
        } finally {
            setLoadingHistory(false);
        }
    }, []);

    // 初始加载历史记录
    useEffect(() => {
        loadReportHistory();
    }, [loadReportHistory]);

    // 加载历史报表
    const handleLoadReport = useCallback(async (report) => {
        setShowHistoryDropdown(false);
        setIsLoading(true);

        try {
            // 判断是否是大屏类型
            if (report.report_type === 'dashboard') {
                setDashboardId(report.report_id);
                setIsDashboard(true);
                setHasReport(false);
                setReportData({
                    display_file_name: report.display_file_name || '人力资源效能分析大屏',
                    row_count: report.row_count
                });
                setCreateMode('dashboard');
                setCellModifications({ human: {}, ai: {} });
                setUndoStack([]);
                setMessages([]);
                showAlert('大屏加载成功！', '成功', 'success');
                setIsLoading(false);
                return;
            }

            // 加载普通报表 - 需要重置大屏状态
            setIsDashboard(false);
            setDashboardId(null);
            setCreateMode('report');

            // 获取报表完整数据
            const fullDataResponse = await api.getReportFullData(report.report_id);
            if (fullDataResponse.success) {
                setReportId(report.report_id);
                setReportData({
                    report_name: report.report_type,
                    file_path: report.file_path,
                    row_count: report.row_count,
                    column_count: fullDataResponse.columns?.length || 0,
                    display_file_name: report.display_file_name || '报表'
                });
                setPreviewData(fullDataResponse.data || []);
                setPreviewColumns(fullDataResponse.columns || []);
                setIsDesensitized(report.is_desensitized || false);
                setHasReport(true);

                // 重置编辑状态
                setCellModifications({ human: {}, ai: {} });
                setUndoStack([]);
                setMessages([]);

                showAlert('报表加载成功！', '成功', 'success');
            } else {
                showAlert('加载报表失败', '错误', 'error');
            }
        } catch (error) {
            console.error('加载报表失败:', error);
            showAlert('加载报表失败: ' + (error.message || '未知错误'), '错误', 'error');
        } finally {
            setIsLoading(false);
        }
    }, [showAlert]);

    // 打开历史记录下拉
    const handleOpenHistory = useCallback(() => {
        if (!showHistoryDropdown) {
            loadReportHistory();
        }
        setShowHistoryDropdown(!showHistoryDropdown);
    }, [showHistoryDropdown, loadReportHistory]);

    // 删除历史报表
    const handleDeleteReport = useCallback(async (e, report) => {
        e.stopPropagation();
        const confirmed = window.confirm(`确定要删除报表"${report.display_file_name || report.report_id}"吗？`);
        if (!confirmed) return;

        try {
            const response = await api.deleteReport(report.report_id);
            if (response.success) {
                setReportHistory(prev => prev.filter(r => r.report_id !== report.report_id));
                if (reportId === report.report_id) {
                    handleReset();
                }
                showAlert('报表已删除', '成功', 'success');
            } else {
                showAlert(response.error || '删除失败', '错误', 'error');
            }
        } catch (error) {
            console.error('删除报表失败:', error);
            showAlert('删除失败: ' + (error.message || '未知错误'), '错误', 'error');
        }
    }, [reportId, showAlert]);

    // ==================== 文件上传处理 ====================
    const handleDetailFileChange = (e) => {
        const file = e.target.files[0];
        if (file) {
            const validTypes = ['.xlsx', '.xls'];
            const ext = file.name.substring(file.name.lastIndexOf('.')).toLowerCase();
            if (!validTypes.includes(ext)) {
                showAlert('请上传 .xlsx 或 .xls 格式的文件', '文件格式错误', 'error');
                return;
            }
            setDetailFile(file);
        }
    };

    const handleSummaryFileChange = (e) => {
        const file = e.target.files[0];
        if (file) {
            const validTypes = ['.xlsx', '.xls'];
            const ext = file.name.substring(file.name.lastIndexOf('.')).toLowerCase();
            if (!validTypes.includes(ext)) {
                showAlert('请上传 .xlsx 或 .xls 格式的文件', '文件格式错误', 'error');
                return;
            }
            setSummaryFile(file);
        }
    };

    // ==================== 大屏文件上传 ====================
    const handleDashboardFileChange = (type, e) => {
        const file = e.target.files[0];
        if (file) {
            const validTypes = ['.xlsx', '.xls'];
            const ext = file.name.substring(file.name.lastIndexOf('.')).toLowerCase();
            if (!validTypes.includes(ext)) {
                showAlert('请上传 .xlsx 或 .xls 格式的文件', '文件格式错误', 'error');
                return;
            }
            if (type === 'personal') {
                setDashboardPersonalFile(file);
            } else {
                setDashboardDeptFile(file);
            }
        }
    };

    // ==================== 生成大屏 ====================
    const handleGenerateDashboard = async () => {
        if (!dashboardPersonalFile || !dashboardDeptFile) {
            showAlert('请上传个人维度和部门维度两个Excel文件', '提示', 'warning');
            return;
        }

        setIsGenerating(true);
        setGenerationProgress(0);

        const progressInterval = setInterval(() => {
            setGenerationProgress(prev => {
                if (prev >= 90) return prev;
                return prev + Math.random() * 25;
            });
        }, 800);

        try {
            const formData = new FormData();
            formData.append('personal_file', dashboardPersonalFile);
            formData.append('dept_file', dashboardDeptFile);

            const response = await api.generateDashboard(formData);

            clearInterval(progressInterval);
            setGenerationProgress(100);

            if (response.success) {
                setDashboardId(response.dashboard_id);
                setIsDashboard(true);
                setReportData({
                    display_file_name: response.display_file_name || '人力资源效能分析大屏',
                    row_count: response.row_count
                });
                showAlert('大屏生成成功！', '成功', 'success');
                loadReportHistory();
                onReportCreated && onReportCreated(); // 通知 App.jsx 刷新侧边栏历史记录
            } else {
                showAlert(response.error || '大屏生成失败', '错误', 'error');
            }
        } catch (error) {
            console.error('大屏生成失败:', error);
            showAlert(error.message || '大屏生成失败，请稍后重试', '错误', 'error');
        } finally {
            clearInterval(progressInterval);
            setIsGenerating(false);
        }
    };

    // ==================== 生成报表 ====================
    const handleGenerateReport = async () => {
        if (!selectedType) {
            showAlert('请选择报表类型', '提示', 'warning');
            return;
        }
        if (!detailFile || !summaryFile) {
            showAlert('请上传明细表和汇总表', '提示', 'warning');
            return;
        }

        setIsGenerating(true);
        setGenerationProgress(0);

        const progressInterval = setInterval(() => {
            setGenerationProgress(prev => {
                if (prev >= 90) return prev;
                return prev + Math.random() * 20;
            });
        }, 1000);

        try {
            const formData = new FormData();
            formData.append('report_type', selectedType);
            formData.append('detail_file', detailFile);
            formData.append('summary_file', summaryFile);

            const response = await api.generateReportFromFiles(formData);

            clearInterval(progressInterval);
            setGenerationProgress(100);

            if (response.success) {
                setReportId(response.report_id);
                setDownloadFileName(response.display_file_name || '人力考勤报表.xlsx');
                setReportData({
                    report_name: response.report_type,
                    file_path: response.file_path,
                    row_count: response.row_count,
                    column_count: response.column_count,
                    display_file_name: response.display_file_name || '人力考勤报表.xlsx',
                    yellow_cells_count: response.yellow_cells_count || 0,
                    problem_count: response.problem_count || 0
                });

                // 获取完整数据用于编辑
                const fullDataResponse = await api.getReportFullData(response.report_id);
                if (fullDataResponse.success) {
                    setPreviewData(fullDataResponse.data || []);
                    setPreviewColumns(fullDataResponse.columns || []);
                }

                setHasReport(true);
                // 重置编辑状态
                setCellModifications({ human: {}, ai: {} });
                setUndoStack([]);
                setIsDesensitized(false); // 重置脱敏状态
                showAlert('报表生成成功！', '成功', 'success');
                loadReportHistory();
                onReportCreated && onReportCreated(); // 通知 App.jsx 刷新侧边栏历史记录
            } else {
                showAlert(response.error || '报表生成失败', '错误', 'error');
            }
        } catch (error) {
            console.error('报表生成失败:', error);
            showAlert(error.message || '报表生成失败，请稍后重试', '错误', 'error');
        } finally {
            clearInterval(progressInterval);
            setIsGenerating(false);
        }
    };

    // ==================== 下载报表 ====================
    const handleDownload = () => {
        if (!reportId) return;
        api.downloadFixedReport(reportId, isDesensitized);
    };

    // ==================== 脱敏功能 ====================
    // 打开脱敏设置弹窗
    const handleOpenDesensitizeModal = useCallback(async () => {
        if (!reportId) return;

        setShowDesensitizeModal(true);
        setLoadingDesensitizeConfig(true);

        try {
            // 并行获取脱敏方法和列配置
            const [methodsRes, previewRes] = await Promise.all([
                api.getDesensitizeMethods(),
                api.getDesensitizePreview(reportId)
            ]);

            if (methodsRes.success) {
                setDesensitizeMethods(methodsRes.methods || []);
            }

            if (previewRes.success) {
                // 使用已保存的配置或推荐的配置
                const config = previewRes.saved_config || previewRes.suggested_config || {};
                setDesensitizeColumnConfig(config);
                setIsDesensitized(previewRes.is_desensitized || false);
            }
        } catch (error) {
            console.error('获取脱敏配置失败:', error);
            showAlert('获取脱敏配置失败', '错误', 'error');
        } finally {
            setLoadingDesensitizeConfig(false);
        }
    }, [reportId, showAlert]);

    // 应用脱敏设置
    const handleApplyDesensitize = useCallback(async () => {
        if (!reportId) return;

        setIsDesensitizing(true);
        try {
            const response = await api.toggleReportDesensitize(reportId, true, desensitizeColumnConfig);
            if (response.success) {
                setIsDesensitized(true);
                setShowDesensitizeModal(false);
                showAlert('脱敏设置已应用', '成功', 'success');
                // 重新加载完整数据（后端返回的只是预览数据）
                const fullDataResponse = await api.getReportFullData(reportId);
                if (fullDataResponse.success) {
                    setPreviewData(fullDataResponse.data || []);
                    setPreviewColumns(fullDataResponse.columns || []);
                }
            } else {
                showAlert(response.error || '脱敏操作失败', '错误', 'error');
            }
        } catch (error) {
            console.error('脱敏操作失败:', error);
            showAlert('脱敏操作失败: ' + (error.message || '未知错误'), '错误', 'error');
        } finally {
            setIsDesensitizing(false);
        }
    }, [reportId, desensitizeColumnConfig, showAlert]);

    // 关闭脱敏
    const handleDisableDesensitize = useCallback(async () => {
        if (!reportId) return;

        setIsDesensitizing(true);
        try {
            const response = await api.toggleReportDesensitize(reportId, false);
            if (response.success) {
                setIsDesensitized(false);
                setShowDesensitizeModal(false);
                showAlert('已关闭脱敏', '成功', 'success');
                // 重新加载完整数据
                const fullDataResponse = await api.getReportFullData(reportId);
                if (fullDataResponse.success) {
                    setPreviewData(fullDataResponse.data || []);
                    setPreviewColumns(fullDataResponse.columns || []);
                }
            } else {
                showAlert(response.error || '关闭脱敏失败', '错误', 'error');
            }
        } catch (error) {
            console.error('关闭脱敏失败:', error);
            showAlert('关闭脱敏失败: ' + (error.message || '未知错误'), '错误', 'error');
        } finally {
            setIsDesensitizing(false);
        }
    }, [reportId, showAlert]);

    // 更新列脱敏方法
    const handleColumnMethodChange = useCallback((column, methodId) => {
        setDesensitizeColumnConfig(prev => ({
            ...prev,
            [column]: methodId
        }));
    }, []);

    // ==================== 保存功能 ====================
    const handleSave = useCallback(async () => {
        if (!reportId || !previewData.length) return;

        setIsLoading(true);
        try {
            const response = await api.updateReportData(reportId, previewData, previewColumns);
            if (response.success) {
                // 保存成功后清除颜色标记和撤销栈
                setCellModifications({ human: {}, ai: {} });
                setUndoStack([]);
                showAlert('保存成功！', '成功', 'success');
            } else {
                showAlert(response.error || '保存失败', '错误', 'error');
            }
        } catch (error) {
            console.error('保存失败:', error);
            showAlert('保存失败: ' + (error.message || '未知错误'), '错误', 'error');
        } finally {
            setIsLoading(false);
        }
    }, [reportId, previewData, previewColumns, showAlert]);

    // ==================== 撤销功能 ====================
    const handleUndo = useCallback(() => {
        if (undoStack.length === 0) return;

        const lastAction = undoStack[undoStack.length - 1];
        const newData = [...previewData];

        // 恢复数据
        lastAction.changes.forEach(change => {
            if (newData[change.row]) {
                newData[change.row] = { ...newData[change.row], [change.column]: change.oldValue };
            }
        });

        setPreviewData(newData);

        // 更新撤销栈
        setUndoStack(prev => prev.slice(0, -1));

        // 更新单元格修改记录
        setCellModifications(prev => {
            const newMods = { ...prev };
            lastAction.changes.forEach(change => {
                const key = `${change.row}_${change.column}`;
                if (change.source === 'human') {
                    delete newMods.human[key];
                    // 如果之前有AI修改，恢复AI标记
                    if (change.previousAiMod) {
                        newMods.ai[key] = change.previousAiMod;
                    }
                } else if (change.source === 'ai') {
                    delete newMods.ai[key];
                    // 如果之前有人工修改，恢复人工标记
                    if (change.previousHumanMod) {
                        newMods.human[key] = change.previousHumanMod;
                    }
                }
            });
            return newMods;
        });

        showAlert('已撤销上一次修改', '提示', 'success');
    }, [undoStack, previewData, showAlert]);

    // ==================== AI改表功能 ====================
    const handleAiEdit = useCallback(async (request) => {
        if (!request || !request.trim() || isLoading) return;
        if (!hasReport) {
            showAlert('请先生成报表', '提示', 'warning');
            return;
        }

        setIsLoading(true);

        // 添加用户消息
        const userMsg = {
            id: Date.now().toString(),
            role: 'user',
            content: request,
            type: 'ai-edit',
            timestamp: Date.now()
        };
        setMessages(prev => [...prev, userMsg]);

        try {
            const sampleData = previewData.slice(0, 100);
            const response = await api.aiEditReport(reportId, sampleData, previewColumns, request);

            if (response.success && response.data) {
                // 后端直接返回修改后的数据和modified_cells
                const newData = response.data;
                const modifiedCells = response.modified_cells || [];

                // 记录修改到撤销栈
                const undoAction = {
                    type: 'ai-edit',
                    changes: modifiedCells.map(cell => ({
                        row: cell.row,
                        column: cell.column,
                        oldValue: cell.old_value !== undefined ? cell.old_value : cell.oldValue,
                        newValue: cell.new_value !== undefined ? cell.new_value : cell.newValue,
                        source: 'ai',
                        previousHumanMod: cellModifications.human[`${cell.row}_${cell.column}`],
                        previousAiMod: cellModifications.ai[`${cell.row}_${cell.column}`]
                    }))
                };

                // 更新状态
                setPreviewData(newData);
                if (response.columns) {
                    setPreviewColumns(response.columns);
                }
                setUndoStack(prev => [...prev, undoAction]);

                // 更新单元格修改记录
                const newAiMods = {};
                modifiedCells.forEach(cell => {
                    const key = `${cell.row}_${cell.column}`;
                    newAiMods[key] = {
                        oldValue: cell.old_value !== undefined ? cell.old_value : cell.oldValue,
                        newValue: cell.new_value !== undefined ? cell.new_value : cell.newValue,
                        timestamp: Date.now()
                    };
                });
                setCellModifications(prev => ({
                    human: prev.human,
                    ai: { ...prev.ai, ...newAiMods }
                }));

                // 添加AI反馈消息
                const summary = response.description || `已完成修改，共修改了 ${modifiedCells.length} 个单元格。`;
                const aiMsg = {
                    id: (Date.now() + 1).toString(),
                    role: 'assistant',
                    content: summary,
                    type: 'ai-edit',
                    timestamp: Date.now(),
                    editResult: {
                        modifiedCount: modifiedCells.length
                    }
                };
                setMessages(prev => [...prev, aiMsg]);
            } else {
                // 添加错误消息
                const errorMsg = {
                    id: (Date.now() + 1).toString(),
                    role: 'assistant',
                    content: 'AI改表失败: ' + (response.error || '未知错误'),
                    type: 'ai-edit',
                    timestamp: Date.now()
                };
                setMessages(prev => [...prev, errorMsg]);
            }
        } catch (error) {
            console.error('AI改表失败:', error);
            const errorMsg = {
                id: (Date.now() + 1).toString(),
                role: 'assistant',
                content: 'AI改表失败: ' + (error.message || '未知错误'),
                type: 'ai-edit',
                timestamp: Date.now()
            };
            setMessages(prev => [...prev, errorMsg]);
        } finally {
            setIsLoading(false);
        }
    }, [isLoading, hasReport, reportId, previewData, previewColumns, cellModifications, showAlert]);

    // ==================== 表格单元格编辑 ====================
    const handleCellEdit = useCallback((rowIndex, column, newValue) => {
        if (!previewData[rowIndex]) return;
        const oldValue = previewData[rowIndex][column];
        if (oldValue === newValue) return;

        const key = `${rowIndex}_${column}`;

        // 更新数据
        const newData = [...previewData];
        newData[rowIndex] = { ...newData[rowIndex], [column]: newValue };
        setPreviewData(newData);

        // 记录到撤销栈
        const undoAction = {
            type: 'human-edit',
            changes: [{
                row: rowIndex,
                column: column,
                oldValue: oldValue,
                newValue: newValue,
                source: 'human',
                previousHumanMod: cellModifications.human[key],
                previousAiMod: cellModifications.ai[key]
            }]
        };
        setUndoStack(prev => [...prev, undoAction]);

        // 更新单元格修改记录
        setCellModifications(prev => ({
            ...prev,
            human: {
                ...prev.human,
                [key]: {
                    oldValue: oldValue,
                    newValue: newValue,
                    timestamp: Date.now()
                }
            }
        }));
    }, [previewData, cellModifications]);

    // ==================== 发送消息 ====================
    const handleSend = useCallback((text, mode) => {
        // 只保留AI改表功能
        handleAiEdit(text);
    }, [handleAiEdit]);

    // ==================== 重置表单 ====================
    const handleReset = () => {
        setHasReport(false);
        setSelectedType('');
        setDetailFile(null);
        setSummaryFile(null);
        setReportData(null);
        setPreviewData([]);
        setPreviewColumns([]);
        setReportId(null);
        setDownloadFileName('');
        setCellModifications({ human: {}, ai: {} });
        setUndoStack([]);
        setMessages([]);
        setCreateMode(null);
        setDashboardPersonalFile(null);
        setDashboardDeptFile(null);
        setIsDashboard(false);
        setDashboardId(null);
        if (detailInputRef.current) detailInputRef.current.value = '';
        if (summaryInputRef.current) summaryInputRef.current.value = '';
        if (dashboardPersonalInputRef.current) dashboardPersonalInputRef.current.value = '';
        if (dashboardDeptInputRef.current) dashboardDeptInputRef.current.value = '';
    };

    // ==================== 获取单元格样式 ====================
    const getCellStyle = useCallback((rowIndex, column) => {
        const key = `${rowIndex}_${column}`;
        // 人工修改优先显示（覆盖AI修改）
        if (cellModifications.human[key]) {
            return 'bg-amber-50'; // 淡黄色
        }
        if (cellModifications.ai[key]) {
            return 'bg-purple-100'; // 淡紫色
        }
        return '';
    }, [cellModifications]);

    // ==================== 渲染左面板内容 ====================
    const renderLeftPanel = () => {
        // 大屏展示模式
        if (isDashboard && dashboardId) {
            return (
                <div className="flex flex-col h-full">
                    <div className="p-4 bg-white border-b border-gray-200 flex items-center justify-between">
                        <div className="flex items-center gap-4">
                            <span className="text-sm text-gray-500">
                                共 {reportData?.row_count || 0} 条数据
                            </span>
                        </div>
                        <div className="flex items-center gap-3">
                            <button
                                onClick={() => {
                                    const iframe = document.getElementById('dashboard-iframe');
                                    if (iframe && iframe.requestFullscreen) {
                                        iframe.requestFullscreen();
                                    } else if (iframe && iframe.webkitRequestFullscreen) {
                                        iframe.webkitRequestFullscreen();
                                    }
                                }}
                                className="px-4 py-2 bg-blue-600 text-white rounded-xl font-bold hover:bg-blue-700 transition-all flex items-center gap-2"
                            >
                                <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                    <polyline points="15 3 21 3 21 9"></polyline>
                                    <polyline points="9 21 3 21 3 15"></polyline>
                                    <line x1="21" y1="3" x2="14" y2="10"></line>
                                    <line x1="3" y1="21" x2="10" y2="14"></line>
                                </svg>
                                全屏
                            </button>
                            <button
                                onClick={async () => {
                                    try {
                                        const iframe = document.getElementById('dashboard-iframe');
                                        let htmlContent = null;

                                        // 尝试从iframe获取当前HTML（包含修改后的标题）
                                        if (iframe && iframe.contentWindow && iframe.contentDocument) {
                                            try {
                                                htmlContent = iframe.contentDocument.documentElement.outerHTML;
                                            } catch (err) {
                                                console.log('无法获取iframe内容，使用默认下载');
                                            }
                                        }

                                        let blob;
                                        if (htmlContent) {
                                            blob = new Blob([htmlContent], { type: 'text/html' });
                                        } else {
                                            const response = await fetch(withBase(`/dashboard/static/${dashboardId}/${dashboardId}.html`));
                                            blob = await response.blob();
                                        }
                                        const url = URL.createObjectURL(blob);
                                        const a = document.createElement('a');
                                        a.href = url;
                                        a.download = `${dashboardId}.html`;
                                        document.body.appendChild(a);
                                        a.click();
                                        document.body.removeChild(a);
                                        URL.revokeObjectURL(url);
                                    } catch (e) {
                                        console.error('下载HTML失败:', e);
                                    }
                                }}
                                className="px-4 py-2 bg-teal-600 text-white rounded-xl font-bold hover:bg-teal-700 transition-all flex items-center gap-2"
                            >
                                <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                                    <polyline points="7 10 12 15 17 10"></polyline>
                                    <line x1="12" y1="15" x2="12" y2="3"></line>
                                </svg>
                                下载HTML
                            </button>
                            <button
                                onClick={async (e) => {
                                    try {
                                        // 从iframe获取当前标题
                                        const iframe = document.getElementById('dashboard-iframe');
                                        let title = reportData?.display_file_name || '人力资源效能分析大屏';
                                        if (iframe && iframe.contentWindow) {
                                            const h1 = iframe.contentWindow.document.querySelector('.header-title h1');
                                            if (h1) title = h1.textContent;
                                        }

                                        const btn = e.target.closest('button');
                                        if (btn) {
                                        btn.disabled = true;
                                        btn.innerHTML = '⏳ 生成中...';
                                    }

                                        const response = await fetch(withBase(`/dashboard/static/${dashboardId}/screenshot?title=${encodeURIComponent(title)}`));
                                        if (!response.ok) {
                                            const err = await response.json().catch(() => ({error: '未知错误'}));
                                            alert('截图失败: ' + err.error);
                                            return;
                                        }
                                        const blob = await response.blob();
                                        const url = URL.createObjectURL(blob);
                                        const a = document.createElement('a');
                                        a.href = url;
                                        a.download = `${dashboardId}.png`;
                                        document.body.appendChild(a);
                                        a.click();
                                        document.body.removeChild(a);
                                        URL.revokeObjectURL(url);

                                        if (btn) { btn.disabled = false; btn.textContent = '下载PNG'; }
                                    } catch (e) {
                                        console.error('下载PNG失败:', e);
                                        alert('下载PNG失败: ' + e.message);
                                    }
                                }}
                                className="px-4 py-2 bg-indigo-600 text-white rounded-xl font-bold hover:bg-indigo-700 transition-all"
                            >
                                下载PNG
                            </button>
                            <button
                                onClick={handleReset}
                                className="px-4 py-2 bg-gray-200 text-gray-700 rounded-xl font-bold hover:bg-gray-300 transition-all"
                            >
                                重新生成
                            </button>
                        </div>
                    </div>
                    <div className="flex-1 overflow-hidden">
                        <iframe
                            id="dashboard-iframe"
                            src={withBase(`/dashboard/static/${dashboardId}/${dashboardId}.html`)}
                            className="w-full h-full border-none"
                            title="人力资源效能分析大屏"
                            onLoad={() => {
                                console.log('iframe 加载完成');
                                setDashboardIframeReady(true);
                                // 发送标题到 iframe
                                const iframe = document.getElementById('dashboard-iframe');
                                if (iframe && iframe.contentWindow) {
                                    const title = reportData?.display_file_name || '人力资源效能分析大屏';
                                    iframe.contentWindow.postMessage({ type: 'updateTitle', title }, '*');
                                }
                            }}
                        />
                    </div>
                </div>
            );
        }

        if (!hasReport) {
            // 未选择创建模式时，显示空白
            if (createMode === null) {
                return (
                    <div className="flex flex-col h-full">
                        <div className="flex-1 flex items-center justify-center">
                            <div className="text-center text-gray-300">
                                <Icons.Table className="w-16 h-16 mx-auto mb-4 opacity-20" />
                                <p className="text-sm">请从左侧菜单选择新建报表或新建大屏</p>
                            </div>
                        </div>
                    </div>
                );
            }

            // 大屏上传表单
            if (createMode === 'dashboard') {
                return (
                    <div className="flex flex-col h-full">
                        <div className="p-4 bg-white border-b border-gray-200 flex items-center justify-between">
                            <button
                                onClick={() => { setCreateMode(null); setDashboardPersonalFile(null); setDashboardDeptFile(null); }}
                                className="text-sm text-gray-500 hover:text-gray-700 flex items-center gap-1"
                            >
                                <Icons.ChevronLeft className="w-4 h-4" />
                                返回
                            </button>
                        </div>
                        <div className="flex-1 overflow-auto p-8">
                            <div className="max-w-xl mx-auto bg-white rounded-2xl shadow-lg border border-gray-200 p-8">
                                <div className="flex items-center gap-3 mb-6">
                                    <div className="w-10 h-10 rounded-xl bg-teal-100 text-teal-600 flex items-center justify-center">
                                        <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                            <rect x="2" y="3" width="20" height="14" rx="2" ry="2"></rect>
                                            <line x1="8" y1="21" x2="16" y2="21"></line>
                                            <line x1="12" y1="17" x2="12" y2="21"></line>
                                        </svg>
                                    </div>
                                    <h3 className="text-lg font-bold text-gray-800">生成大屏</h3>
                                </div>

                                {/* 个人维度文件上传 */}
                                <div className="mb-4">
                                    <label className="text-sm font-bold text-gray-600 mb-2 block">
                                        个人维度明细表 <span className="text-red-500">*</span>
                                    </label>
                                    <div
                                        onClick={() => dashboardPersonalInputRef.current?.click()}
                                        className="border-2 border-dashed border-gray-200 rounded-xl p-5 text-center cursor-pointer hover:border-teal-400 hover:bg-teal-50/50 transition-all"
                                    >
                                        <input
                                            ref={dashboardPersonalInputRef}
                                            type="file"
                                            accept=".xlsx,.xls"
                                            onChange={(e) => handleDashboardFileChange('personal', e)}
                                            className="hidden"
                                        />
                                        {dashboardPersonalFile ? (
                                            <div className="flex items-center justify-center gap-2 text-teal-600">
                                                <Icons.Table className="w-5 h-5" />
                                                <span className="font-bold">{dashboardPersonalFile.name}</span>
                                                <span className="text-teal-500">&#10003;</span>
                                            </div>
                                        ) : (
                                            <div className="text-gray-400">
                                                <Icons.Upload className="w-6 h-6 mx-auto mb-1" />
                                                <p className="text-sm">点击上传个人维度Excel文件</p>
                                                <p className="text-xs mt-1 text-gray-300">包含员工工号、姓名、考勤地、贡献时长等字段</p>
                                            </div>
                                        )}
                                    </div>
                                </div>

                                {/* 部门维度文件上传 */}
                                <div className="mb-6">
                                    <label className="text-sm font-bold text-gray-600 mb-2 block">
                                        部门维度明细表 <span className="text-red-500">*</span>
                                    </label>
                                    <div
                                        onClick={() => dashboardDeptInputRef.current?.click()}
                                        className="border-2 border-dashed border-gray-200 rounded-xl p-5 text-center cursor-pointer hover:border-cyan-400 hover:bg-cyan-50/50 transition-all"
                                    >
                                        <input
                                            ref={dashboardDeptInputRef}
                                            type="file"
                                            accept=".xlsx,.xls"
                                            onChange={(e) => handleDashboardFileChange('dept', e)}
                                            className="hidden"
                                        />
                                        {dashboardDeptFile ? (
                                            <div className="flex items-center justify-center gap-2 text-cyan-600">
                                                <Icons.Table className="w-5 h-5" />
                                                <span className="font-bold">{dashboardDeptFile.name}</span>
                                                <span className="text-cyan-500">&#10003;</span>
                                            </div>
                                        ) : (
                                            <div className="text-gray-400">
                                                <Icons.Upload className="w-6 h-6 mx-auto mb-1" />
                                                <p className="text-sm">点击上传部门维度Excel文件</p>
                                                <p className="text-xs mt-1 text-gray-300">包含一级部门、二级部门、部门人数、周末出勤率等字段</p>
                                            </div>
                                        )}
                                    </div>
                                </div>

                                <div className="mb-6 p-4 bg-teal-50 rounded-xl border border-teal-100">
                                    <h4 className="text-sm font-bold text-teal-700 mb-2">数据要求说明</h4>
                                    <ul className="text-xs text-teal-600 space-y-1">
                                        <li>&#8226; <b>个人维度表</b>：包含每位员工的考勤、出差、贡献时长等明细数据</li>
                                        <li>&#8226; <b>部门维度表</b>：包含各一级/二级部门的汇总数据（公休日打卡率、出差率等）</li>
                                        <li>&#8226; 系统会自动匹配列名，支持多种常见命名方式</li>
                                    </ul>
                                </div>

                                <div className="flex justify-end gap-4">
                                    <button
                                        onClick={() => { setCreateMode(null); setDashboardPersonalFile(null); setDashboardDeptFile(null); }}
                                        className="px-6 py-3 rounded-xl text-gray-600 hover:bg-gray-100 font-bold transition-all"
                                    >
                                        取消
                                    </button>
                                    <button
                                        onClick={handleGenerateDashboard}
                                        disabled={!dashboardPersonalFile || !dashboardDeptFile || isGenerating}
                                        className={`px-6 py-3 rounded-xl font-bold transition-all flex items-center gap-2 ${
                                            !dashboardPersonalFile || !dashboardDeptFile || isGenerating
                                                ? 'bg-gray-200 text-gray-400 cursor-not-allowed'
                                                : 'bg-teal-600 text-white hover:bg-teal-700 shadow-lg shadow-teal-600/30'
                                        }`}
                                    >
                                        {isGenerating ? (
                                            <>
                                                <svg className="animate-spin h-5 w-5 text-white" viewBox="0 0 24 24">
                                                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none"></circle>
                                                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
                                                </svg>
                                                生成中...
                                            </>
                                        ) : (
                                            <>
                                                <Icons.Check className="w-5 h-5" />
                                                开始生成大屏
                                            </>
                                        )}
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>
                );
            }

            // 报表上传表单（原有逻辑）
            return (
                <div className="flex flex-col h-full">
                    <div className="p-4 bg-white border-b border-gray-200 flex items-center justify-between">
                        <button
                            onClick={() => { setCreateMode(null); setSelectedType(''); setDetailFile(null); setSummaryFile(null); }}
                            className="text-sm text-gray-500 hover:text-gray-700 flex items-center gap-1"
                        >
                            <Icons.ChevronLeft className="w-4 h-4" />
                            返回
                        </button>
                    </div>

                    <div className="flex-1 overflow-auto p-8">
                        <div className="max-w-xl mx-auto bg-white rounded-2xl shadow-lg border border-gray-200 p-8">
                            <h3 className="text-lg font-bold text-gray-800 mb-6 text-center">生成报表</h3>

                            <div className="mb-6">
                                <label className="text-sm font-bold text-gray-600 mb-2 block">报表类型</label>
                                <div className="relative">
                                    <select
                                        value={selectedType}
                                        onChange={(e) => setSelectedType(e.target.value)}
                                        className="w-full px-4 py-3 bg-gray-50 border-2 border-gray-100 rounded-xl focus:ring-0 focus:border-emerald-500 outline-none transition-all font-bold text-gray-700 appearance-none cursor-pointer"
                                    >
                                        <option value="">请选择报表类型</option>
                                        {REPORT_TYPES.map(type => (
                                            <option key={type.id} value={type.id}>{type.name}</option>
                                        ))}
                                    </select>
                                    <div className="absolute right-4 top-1/2 -translate-y-1/2 pointer-events-none text-gray-400">
                                        <Icons.ChevronDown className="w-5 h-5" />
                                    </div>
                                </div>
                            </div>

                            {selectedType && (
                                <div className="space-y-4 mb-6">
                                    <div>
                                        <label className="text-sm font-bold text-gray-600 mb-2 block">
                                            {selectedType === 'dept_attendance' ? '上传个人明细结果表' :
                                             selectedType.startsWith('multi_month') ? '上传多月明细表' : '上传明细表'} <span className="text-red-500">*</span>
                                        </label>
                                        <div
                                            onClick={() => detailInputRef.current?.click()}
                                            className="border-2 border-dashed border-gray-200 rounded-xl p-6 text-center cursor-pointer hover:border-emerald-400 hover:bg-emerald-50/50 transition-all"
                                        >
                                            <input
                                                ref={detailInputRef}
                                                type="file"
                                                accept=".xlsx,.xls"
                                                onChange={handleDetailFileChange}
                                                className="hidden"
                                            />
                                            {detailFile ? (
                                                <div className="flex items-center justify-center gap-2 text-emerald-600">
                                                    <Icons.Table className="w-5 h-5" />
                                                    <span className="font-bold">{detailFile.name}</span>
                                                    <span className="text-emerald-500">✓</span>
                                                </div>
                                            ) : (
                                                <div className="text-gray-400">
                                                    <Icons.Upload className="w-8 h-8 mx-auto mb-2" />
                                                    <p className="text-sm">{
                                                        selectedType === 'dept_attendance' ? '点击上传个人明细结果表（考勤分析-个人维度）' :
                                                        selectedType.startsWith('multi_month') ? '点击上传多月明细表（需包含月份列）' :
                                                        '点击上传明细表'
                                                    }</p>
                                                </div>
                                            )}
                                        </div>
                                    </div>

                                    <div>
                                        <label className="text-sm font-bold text-gray-600 mb-2 block">
                                            {selectedType.startsWith('multi_month') ? '上传多月汇总表' : '上传汇总表'} <span className="text-red-500">*</span>
                                        </label>
                                        <div
                                            onClick={() => summaryInputRef.current?.click()}
                                            className="border-2 border-dashed border-gray-200 rounded-xl p-6 text-center cursor-pointer hover:border-emerald-400 hover:bg-emerald-50/50 transition-all"
                                        >
                                            <input
                                                ref={summaryInputRef}
                                                type="file"
                                                accept=".xlsx,.xls"
                                                onChange={handleSummaryFileChange}
                                                className="hidden"
                                            />
                                            {summaryFile ? (
                                                <div className="flex items-center justify-center gap-2 text-emerald-600">
                                                    <Icons.Table className="w-5 h-5" />
                                                    <span className="font-bold">{summaryFile.name}</span>
                                                    <span className="text-emerald-500">✓</span>
                                                </div>
                                            ) : (
                                                <div className="text-gray-400">
                                                    <Icons.Upload className="w-8 h-8 mx-auto mb-2" />
                                                    <p className="text-sm">{
                                                        selectedType.startsWith('multi_month') ? '点击上传多月汇总表（需包含月份列）' : '点击上传汇总表'
                                                    }</p>
                                                </div>
                                            )}
                                        </div>
                                    </div>

                                    {selectedType.startsWith('multi_month') && (
                                        <div className="p-3 bg-blue-50 rounded-lg border border-blue-100 text-sm text-blue-600">
                                            <strong>多月报表说明：</strong>数据中需包含"月份"列用于区分不同月份数据
                                        </div>
                                    )}
                                </div>
                            )}

                            {selectedType && (
                                <div className="flex justify-end gap-4">
                                    <button
                                        onClick={handleReset}
                                        className="px-6 py-3 rounded-xl text-gray-600 hover:bg-gray-100 font-bold transition-all"
                                    >
                                        取消
                                    </button>
                                    <button
                                        onClick={handleGenerateReport}
                                        disabled={!detailFile || !summaryFile || isGenerating}
                                        className={`px-6 py-3 rounded-xl font-bold transition-all flex items-center gap-2 ${
                                            !detailFile || !summaryFile || isGenerating
                                                ? 'bg-gray-200 text-gray-400 cursor-not-allowed'
                                                : 'bg-emerald-600 text-white hover:bg-emerald-700 shadow-lg shadow-emerald-600/30'
                                        }`}
                                    >
                                        {isGenerating ? (
                                            <>
                                                <svg className="animate-spin h-5 w-5 text-white" viewBox="0 0 24 24">
                                                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none"></circle>
                                                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
                                                </svg>
                                                生成中...
                                            </>
                                        ) : (
                                            <>
                                                <Icons.Check className="w-5 h-5" />
                                                开始生成报表
                                            </>
                                        )}
                                    </button>
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            );
        }

        // 已生成报表时显示可编辑表格
        const hasModifications = Object.keys(cellModifications.human).length > 0 || Object.keys(cellModifications.ai).length > 0;
        const modificationCount = Object.keys(cellModifications.human).length + Object.keys(cellModifications.ai).length;

        return (
            <div className="flex flex-col h-full">
                {/* 工具栏 */}
                <div className="p-4 bg-white border-b border-gray-200 flex items-center justify-between">
                    <div className="flex items-center gap-4">
                        {/* 脱敏按钮 */}
                        <button
                            onClick={handleOpenDesensitizeModal}
                            disabled={isDesensitizing}
                            className={`px-3 py-2 rounded-xl font-bold transition-all flex items-center gap-2 ${
                                isDesensitized
                                    ? 'bg-amber-100 text-amber-700 border border-amber-300'
                                    : 'bg-gray-100 text-gray-600 border border-gray-200 hover:bg-gray-200'
                            }`}
                            title="点击设置脱敏"
                        >
                            {isDesensitizing ? (
                                <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none"></circle>
                                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
                                </svg>
                            ) : (
                                <span>{isDesensitized ? '🔒' : '🔓'}</span>
                            )}
                            {isDesensitized ? '已脱敏' : '脱敏设置'}
                        </button>
                        <div className="w-px h-6 bg-gray-200"></div>
                        {hasModifications && (
                            <span className="text-sm text-orange-600 font-medium">
                                已修改 {modificationCount} 个单元格
                            </span>
                        )}
                        <span className="text-sm text-gray-500">
                            共 {reportData?.row_count || 0} 行 × {previewColumns.length} 列
                        </span>
                    </div>
                    <div className="flex items-center gap-3">
                        {/* 撤销按钮 */}
                        <button
                            onClick={handleUndo}
                            disabled={undoStack.length === 0}
                            className={`px-3 py-2 rounded-xl font-bold transition-all flex items-center gap-1 ${
                                undoStack.length === 0
                                    ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
                                    : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                            }`}
                            title="撤销上一次修改"
                        >
                            <Icons.Undo className="w-4 h-4" />
                            撤销
                        </button>
                        {/* 保存按钮 */}
                        <button
                            onClick={handleSave}
                            disabled={!hasModifications}
                            className={`px-4 py-2 rounded-xl font-bold transition-all flex items-center gap-2 ${
                                !hasModifications
                                    ? 'bg-gray-200 text-gray-400 cursor-not-allowed'
                                    : 'bg-emerald-600 text-white hover:bg-emerald-700 shadow-lg shadow-emerald-600/30'
                            }`}
                        >
                            <Icons.Save className="w-4 h-4" />
                            保存
                        </button>
                        {/* 下载报表 */}
                        <button
                            onClick={handleDownload}
                            className="px-4 py-2 bg-blue-600 text-white rounded-xl font-bold hover:bg-blue-700 transition-all flex items-center gap-2"
                        >
                            <Icons.Download className="w-4 h-4" />
                            下载
                        </button>
                        {/* 重新生成 */}
                        <button
                            onClick={handleReset}
                            className="px-4 py-2 bg-gray-200 text-gray-700 rounded-xl font-bold hover:bg-gray-300 transition-all"
                        >
                            重新生成
                        </button>
                    </div>
                </div>

                {/* 颜色图例 */}
                {hasModifications && (
                    <div className="px-4 py-2 bg-gray-50 border-b border-gray-200 flex items-center gap-6 text-xs text-gray-500">
                        <div className="flex items-center gap-2">
                            <div className="w-4 h-4 rounded bg-purple-100 border border-purple-200"></div>
                            <span>AI修改</span>
                        </div>
                        <div className="flex items-center gap-2">
                            <div className="w-4 h-4 rounded bg-amber-50 border border-amber-200"></div>
                            <span>人工修改</span>
                        </div>
                    </div>
                )}

                {/* 可编辑表格 - 横向滚动条固定在可见区域底部 */}
                <div className="flex-1 overflow-hidden flex flex-col p-4 pb-2">
                    <div className="flex-1 overflow-y-auto">
                        <div className="bg-white rounded-xl shadow border border-gray-200 overflow-hidden">
                            <div
                                ref={tableScrollRef}
                                className="overflow-x-auto"
                                onScroll={handleTableScroll}
                            >
                                <table className="min-w-max text-sm w-full" style={{ minWidth: `${previewColumns.length * 100}px` }}>
                                    <thead className="bg-gray-50 sticky top-0 z-10">
                                        <tr>
                                            <th className="px-3 py-2 text-left font-bold text-gray-500 border-b border-gray-200 w-12">#</th>
                                            {previewColumns && previewColumns.map((col, idx) => (
                                                <th
                                                    key={idx}
                                                    className="px-4 py-2 text-left font-bold text-gray-700 border-b border-gray-200 whitespace-nowrap min-w-[100px]"
                                                >
                                                    {col}
                                                </th>
                                            ))}
                                        </tr>
                                    </thead>
                                    <tbody className="divide-y divide-gray-100">
                                        {previewData && previewData.slice(0, 200).map((row, rowIdx) => (
                                            <tr key={rowIdx} className="hover:bg-gray-50">
                                                <td className="px-3 py-2 text-gray-400 border-b border-gray-100 font-mono text-xs">{rowIdx + 1}</td>
                                                {previewColumns && previewColumns.map((col, colIdx) => (
                                                    <td
                                                        key={colIdx}
                                                        className={`px-4 py-2 text-gray-600 border-b border-gray-100 min-w-[100px] ${getCellStyle(rowIdx, col)}`}
                                                    >
                                                        <input
                                                            type="text"
                                                            value={row && row[col] !== undefined ? row[col] : ''}
                                                            onChange={(e) => handleCellEdit(rowIdx, col, e.target.value)}
                                                            className="w-full bg-transparent border-none focus:ring-0 p-0 text-sm"
                                                        />
                                                    </td>
                                                ))}
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                            {previewData && previewData.length > 200 && (
                                <div className="px-4 py-2 bg-gray-50 border-t border-gray-200 text-sm text-gray-500 text-center">
                                    显示前 200 行，共 {previewData.length} 行
                                </div>
                            )}
                        </div>
                    </div>
                    {/* 固定的横向滚动条 */}
                    <div
                        className="mt-2 overflow-x-auto bg-gray-100 rounded-lg"
                        ref={scrollbarRef}
                        onScroll={handleScrollbarScroll}
                    >
                        <div style={{ width: `${previewColumns.length * 100}px`, height: '12px' }}></div>
                    </div>
                </div>
            </div>
        );
    };

    // ==================== 渲染右面板内容 ====================
    const renderRightPanel = () => {
        return (
            <div className="flex flex-col h-full">
                {/* 消息列表 */}
                <div className="flex-1 overflow-y-auto p-4 space-y-3">
                    {messages.length === 0 ? (
                        <div className="text-center text-gray-400 mt-8">
                            <span className="text-4xl">✨</span>
                            <p className="mt-2 font-medium">AI智能改表</p>
                            <p className="text-sm mt-2">
                                例如："将所有空值替换为0"
                            </p>
                            {!hasReport && (
                                <p className="text-sm mt-4 text-amber-600">
                                    ⚠️ 请先上传文件生成报表
                                </p>
                            )}
                        </div>
                    ) : (
                        messages.map((msg) => (
                            <MessageItem key={msg.id} msg={msg} />
                        ))
                    )}
                    {isLoading && (
                        <div className="flex justify-start">
                            <div className="bg-gray-100 rounded-xl p-3 flex items-center gap-2">
                                <svg className="animate-spin h-4 w-4 text-gray-600" viewBox="0 0 24 24">
                                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none"></circle>
                                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
                                </svg>
                                <span className="text-sm text-gray-600">AI分析中...</span>
                            </div>
                        </div>
                    )}
                    <div ref={messagesEndRef} />
                </div>

                {/* 底部输入区域 */}
                <ChatInput
                    hasReport={hasReport}
                    isLoading={isLoading}
                    onSend={handleSend}
                />
            </div>
        );
    };

    // ==================== 渲染生成中遮罩 ====================
    const renderGeneratingOverlay = () => {
        if (!isGenerating) return null;

        return (
            <div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center">
                <div className="bg-white rounded-2xl shadow-2xl p-8 max-w-md w-full mx-4">
                    <div className="text-center">
                        <div className="mb-4">
                            <svg className="animate-spin h-12 w-12 mx-auto text-emerald-600" viewBox="0 0 24 24">
                                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none"></circle>
                                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
                            </svg>
                        </div>
                        <h3 className="text-lg font-bold text-gray-800 mb-2">
                            {createMode === 'dashboard' ? '⏳ 正在生成大屏' : '⏳ 正在生成报表'}
                        </h3>
                        <p className="text-gray-500 mb-4">请稍候，系统正在处理您的数据...</p>
                        <div className="w-full bg-gray-200 rounded-full h-2 mb-2">
                            <div
                                className="bg-emerald-600 h-2 rounded-full transition-all duration-300"
                                style={{ width: `${Math.min(generationProgress, 100)}%` }}
                            ></div>
                        </div>
                        <p className="text-sm text-gray-400">{Math.min(Math.round(generationProgress), 100)}%</p>
                    </div>
                </div>
            </div>
        );
    };

    // ==================== 渲染脱敏设置弹窗 ====================
    const renderDesensitizeModal = () => {
        if (!showDesensitizeModal) return null;

        return (
            <div className="fixed inset-0 z-50 flex items-center justify-center">
                <div className="absolute inset-0 bg-black/50" onClick={() => setShowDesensitizeModal(false)} />
                <div className="relative bg-white rounded-2xl shadow-2xl w-full max-w-2xl mx-4 max-h-[80vh] flex flex-col overflow-hidden">
                    {/* 头部 */}
                    <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 bg-gradient-to-r from-amber-500 to-orange-500">
                        <div className="flex items-center gap-2 text-white">
                            <span className="text-xl">🔒</span>
                            <span className="font-bold text-lg">脱敏设置</span>
                        </div>
                        <button
                            onClick={() => setShowDesensitizeModal(false)}
                            className="text-white/80 hover:text-white"
                        >
                            <Icons.X className="w-5 h-5" />
                        </button>
                    </div>

                    {/* 内容 */}
                    <div className="flex-1 overflow-y-auto p-6">
                        {loadingDesensitizeConfig ? (
                            <div className="flex items-center justify-center py-12">
                                <svg className="animate-spin h-8 w-8 text-amber-500" viewBox="0 0 24 24">
                                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none"></circle>
                                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
                                </svg>
                            </div>
                        ) : (
                            <>
                                {/* 当前状态提示 */}
                                {isDesensitized && (
                                    <div className="mb-4 p-3 bg-amber-50 border border-amber-200 rounded-lg text-amber-700 text-sm">
                                        🔒 当前报表已启用脱敏，修改设置后会重新生成脱敏数据
                                    </div>
                                )}

                                {/* 说明 */}
                                <div className="mb-4 text-sm text-gray-500">
                                    选择每列的脱敏方式。不脱敏的列将保持原数据不变。
                                </div>

                                {/* 列配置列表 */}
                                <div className="space-y-2">
                                    {previewColumns.map((column, idx) => (
                                        <div key={idx} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                                            <span className="font-medium text-gray-700">{column}</span>
                                            <select
                                                value={desensitizeColumnConfig[column] || 'none'}
                                                onChange={(e) => handleColumnMethodChange(column, e.target.value)}
                                                className="px-3 py-1.5 bg-white border border-gray-200 rounded-lg text-sm focus:ring-0 focus:border-amber-500 outline-none"
                                            >
                                                {desensitizeMethods.map(method => (
                                                    <option key={method.id} value={method.id}>
                                                        {method.name}
                                                    </option>
                                                ))}
                                            </select>
                                        </div>
                                    ))}
                                </div>

                                {/* 脱敏方法说明 */}
                                <div className="mt-6 p-4 bg-gray-50 rounded-lg">
                                    <h4 className="font-bold text-gray-700 mb-2">脱敏方法说明</h4>
                                    <div className="grid grid-cols-2 gap-2 text-xs text-gray-500">
                                        {desensitizeMethods.filter(m => m.id !== 'none').map(method => (
                                            <div key={method.id} className="flex items-start gap-1">
                                                <span className="font-medium text-gray-600">{method.name}:</span>
                                                <span>{method.description}</span>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            </>
                        )}
                    </div>

                    {/* 底部按钮 */}
                    <div className="flex items-center justify-between px-6 py-4 border-t border-gray-200 bg-gray-50">
                        <div>
                            {isDesensitized && (
                                <button
                                    onClick={handleDisableDesensitize}
                                    disabled={isDesensitizing}
                                    className="px-4 py-2 text-red-600 hover:bg-red-50 rounded-lg font-medium transition-all"
                                >
                                    关闭脱敏
                                </button>
                            )}
                        </div>
                        <div className="flex gap-3">
                            <button
                                onClick={() => setShowDesensitizeModal(false)}
                                className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg font-medium hover:bg-gray-300 transition-all"
                            >
                                取消
                            </button>
                            <button
                                onClick={handleApplyDesensitize}
                                disabled={isDesensitizing || loadingDesensitizeConfig}
                                className="px-6 py-2 bg-amber-500 text-white rounded-lg font-bold hover:bg-amber-600 transition-all flex items-center gap-2 disabled:opacity-50"
                            >
                                {isDesensitizing ? (
                                    <>
                                        <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                                            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none"></circle>
                                            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
                                        </svg>
                                        处理中...
                                    </>
                                ) : (
                                    <>应用设置</>
                                )}
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        );
    };

    return (
        <div className="flex-1 flex flex-col bg-[#f8fafc] overflow-hidden relative">
            {/* 页面标题 */}
            <div className="h-16 bg-white/80 backdrop-blur border-b border-gray-200/60 flex items-center justify-between px-8 shadow-sm">
                <div className="flex items-center">
                    <div className={`p-1.5 rounded-lg ${isDashboard ? 'bg-teal-100 text-teal-600' : 'bg-emerald-100 text-emerald-600'}`}>
                        {isDashboard ? (
                            <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                <rect x="2" y="3" width="20" height="14" rx="2" ry="2"></rect>
                                <line x1="8" y1="21" x2="16" y2="21"></line>
                                <line x1="12" y1="17" x2="12" y2="21"></line>
                            </svg>
                        ) : (
                            <Icons.Table className="w-5 h-5" />
                        )}
                    </div>
                    <h2 className="ml-4 font-bold text-gray-800">
                        {isDashboard
                            ? `大屏管理 - ${reportData?.display_file_name || '人力资源效能分析大屏'}`
                            : hasReport
                                ? `报表管理 - ${reportData?.display_file_name || '人力考勤报表'}`
                                : '报表管理'}
                    </h2>
                </div>

                {/* 右侧按钮组 */}
                <div className="flex items-center gap-3">
                    {/* 保留空占位或后续可添加其他功能 */}
                </div>
            </div>

            {/* 主内容区域 - 全屏显示 */}
            <div className="flex-1 overflow-hidden">
                <div className="flex h-full">
                    {/* 左面板：报表编辑区/上传区/大屏展示 - 全宽 */}
                    <div className="w-full flex flex-col overflow-hidden">
                        {renderLeftPanel()}
                    </div>
                </div>
            </div>

            {/* 生成中遮罩 */}
            {renderGeneratingOverlay()}

            {/* 脱敏设置弹窗 */}
            {renderDesensitizeModal()}
        </div>
    );
};

export default ReportManager;