import React, { useState, useEffect } from 'react';
import { Icons } from './Icons';
import { api } from '../services/api';

const KnowledgeEditor = ({ onClose, chatId, datasourceName, isGlobal = false, type = 'knowledge', showAlert }) => {
    const [content, setContent] = useState('');
    const [vocabulary, setVocabulary] = useState([{ word: '', explanation: '' }]);
    const [referenceSql, setReferenceSql] = useState([{ name: '', sql: '' }]);
    const [loading, setLoading] = useState(false);
    const [saving, setSaving] = useState(false);

    useEffect(() => {
        loadData();
    }, [chatId, datasourceName, isGlobal, type]);

    const loadData = async () => {
        try {
            setLoading(true);
            let result;
            if (isGlobal) {
                result = await api.getGlobalKnowledge();
                if (result.success) {
                    setContent(result.content || '');
                }
            } else {
                const targetName = datasourceName || chatId;
                result = await api.getTempKnowledge(targetName);
                if (result.success) {
                    setContent(result.content || '');
                    setVocabulary(result.vocabulary?.length > 0 ? result.vocabulary : [{ word: '', explanation: '' }]);
                    setReferenceSql(result.reference_sql?.length > 0 ? result.reference_sql : [{ name: '', sql: '' }]);
                }
            }
        } catch (e) {
            console.error('加载失败:', e);
        } finally {
            setLoading(false);
        }
    };

    const handleSave = async () => {
        try {
            setSaving(true);
            let result;
            if (isGlobal) {
                result = await api.saveGlobalKnowledge(content);
            } else {
                const targetName = datasourceName || chatId;
                const filteredVocab = vocabulary.filter(v => v.word.trim() || v.explanation.trim());
                const filteredSql = referenceSql.filter(s => s.name.trim() || s.sql.trim());
                
                // 获取当前数据源的完整知识，以便增量更新
                const currentData = await api.getTempKnowledge(targetName);
                
                result = await api.saveTempKnowledge(
                    targetName, 
                    type === 'knowledge' ? content : currentData.content, 
                    type === 'vocabulary' ? filteredVocab : currentData.vocabulary,
                    type === 'sql' ? filteredSql : currentData.reference_sql
                );
            }
            if (result.success) {
                if (showAlert) showAlert('保存成功！', '成功', 'success');
                else alert('保存成功！');
                onClose();
            }
        } catch (e) {
            if (showAlert) showAlert('保存失败: ' + e.message, '错误', 'error');
            else alert('保存失败: ' + e.message);
        } finally {
            setSaving(false);
        }
    };

    const addVocabRow = () => setVocabulary([...vocabulary, { word: '', explanation: '' }]);
    const removeVocabRow = (index) => {
        if (vocabulary.length > 1) {
            setVocabulary(vocabulary.filter((_, i) => i !== index));
        } else {
            setVocabulary([{ word: '', explanation: '' }]);
        }
    };
    const updateVocab = (index, field, value) => {
        const next = [...vocabulary];
        next[index][field] = value;
        setVocabulary(next);
    };

    const addSqlRow = () => setReferenceSql([...referenceSql, { name: '', sql: '' }]);
    const removeSqlRow = (index) => {
        if (referenceSql.length > 1) {
            setReferenceSql(referenceSql.filter((_, i) => i !== index));
        } else {
            setReferenceSql([{ name: '', sql: '' }]);
        }
    };
    const updateSql = (index, field, value) => {
        const next = [...referenceSql];
        next[index][field] = value;
        setReferenceSql(next);
    };

    return (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
            <div className="bg-white rounded-2xl w-full max-w-4xl max-h-[90vh] flex flex-col shadow-2xl overflow-hidden animate-fade-in">
                <div className="p-6 border-b border-gray-100 flex justify-between items-center bg-gray-50/50">
                    <div className="flex items-center gap-3">
                        <div className={`p-2 rounded-lg ${isGlobal ? 'bg-blue-50 text-blue-600' : (type === 'knowledge' ? 'bg-emerald-50 text-emerald-600' : (type === 'vocabulary' ? 'bg-purple-50 text-purple-600' : 'bg-indigo-50 text-indigo-600'))}`}>
                            {type === 'knowledge' ? <Icons.Terminal /> : (type === 'vocabulary' ? <Icons.Database className="w-5 h-5" /> : <Icons.Settings className="w-5 h-5" />)}
                        </div>
                        <div>
                            <h2 className="text-xl font-bold text-gray-800">
                                {isGlobal ? '全局业务规则' : (type === 'knowledge' ? '业务背景与知识' : (type === 'vocabulary' ? '业务词汇映射' : '参考 SQL 示例'))}
                            </h2>
                            <p className="text-sm text-gray-500 mt-0.5">
                                {isGlobal ? '影响所有对话的业务规则、口径和元数据映射' : (type === 'knowledge' ? '该数据源专属的业务背景、统计口径或特殊要求' : (type === 'vocabulary' ? '定义该数据源专有的术语解释，如 GMV -> 交易总额' : '提供参考的 SQL 语句或查询逻辑，帮助 AI 生成更准确的代码'))}
                            </p>
                        </div>
                    </div>
                    <button onClick={onClose} className="p-2 hover:bg-white rounded-xl transition-all">
                        <Icons.X className="w-5 h-5 text-gray-400" />
                    </button>
                </div>

                <div className="flex-1 p-6 flex flex-col min-h-0 overflow-y-auto">
                    {loading ? (
                        <div className="flex items-center justify-center flex-1">
                            <div className="animate-spin text-blue-500 text-2xl">↻</div>
                        </div>
                    ) : (
                        <div className="flex-1 flex flex-col gap-4 min-h-0">
                            {type === 'knowledge' ? (
                                <div className="flex-1">
                                    <textarea
                                        value={content}
                                        onChange={(e) => setContent(e.target.value)}
                                        placeholder={isGlobal ? "例如：\n- 员工、职员 → 指 employee_core 表\n- 本月 → 指 1号至今..." : "请输入该对话相关的特殊背景或临时业务规则..."}
                                        className="w-full h-[60vh] p-6 border border-gray-200 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none text-sm font-mono text-gray-700 bg-gray-50/50 resize-none leading-relaxed shadow-inner"
                                    />
                                </div>
                            ) : type === 'vocabulary' ? (
                                <div className="flex-1 space-y-3">
                                    <div className="grid grid-cols-12 gap-4 px-4 py-2 bg-gray-50 rounded-lg text-xs font-bold text-gray-500 uppercase tracking-wider">
                                        <div className="col-span-4">业务词汇</div>
                                        <div className="col-span-7">对应解释</div>
                                        <div className="col-span-1 text-center">操作</div>
                                    </div>
                                    <div className="space-y-2 pr-2">
                                        {vocabulary.map((v, i) => (
                                            <div key={i} className="grid grid-cols-12 gap-4 group">
                                                <div className="col-span-4">
                                                    <input
                                                        type="text"
                                                        value={v.word}
                                                        onChange={(e) => updateVocab(i, 'word', e.target.value)}
                                                        placeholder="例如: GMV"
                                                        className="w-full px-4 py-2 border border-gray-200 rounded-xl text-sm focus:ring-2 focus:ring-purple-500 outline-none transition-all"
                                                    />
                                                </div>
                                                <div className="col-span-7">
                                                    <input
                                                        type="text"
                                                        value={v.explanation}
                                                        onChange={(e) => updateVocab(i, 'explanation', e.target.value)}
                                                        placeholder="例如: 商品交易总额，包含未付款订单"
                                                        className="w-full px-4 py-2 border border-gray-200 rounded-xl text-sm focus:ring-2 focus:ring-purple-500 outline-none transition-all"
                                                    />
                                                </div>
                                                <div className="col-span-1 flex items-center justify-center">
                                                    <button
                                                        onClick={() => removeVocabRow(i)}
                                                        className="p-2 text-gray-300 hover:text-red-500 hover:bg-red-50 rounded-lg transition-all"
                                                    >
                                                        <Icons.Trash className="w-4 h-4" />
                                                    </button>
                                                </div>
                                            </div>
                                        ))}
                                        <button
                                            onClick={addVocabRow}
                                            className="w-full py-3 border-2 border-dashed border-gray-100 rounded-xl text-gray-400 hover:border-purple-200 hover:text-purple-500 hover:bg-purple-50/30 transition-all flex items-center justify-center gap-2 text-sm font-bold mt-4"
                                        >
                                            <Icons.Plus className="w-4 h-4" />
                                            新增词汇映射
                                        </button>
                                    </div>
                                </div>
                            ) : (
                                <div className="flex-1 space-y-3">
                                    <div className="grid grid-cols-12 gap-4 px-4 py-2 bg-gray-50 rounded-lg text-xs font-bold text-gray-500 uppercase tracking-wider">
                                        <div className="col-span-4">参考名称/描述</div>
                                        <div className="col-span-7">参考 SQL 或逻辑</div>
                                        <div className="col-span-1 text-center">操作</div>
                                    </div>
                                    <div className="space-y-2 pr-2">
                                        {referenceSql.map((s, i) => (
                                            <div key={i} className="grid grid-cols-12 gap-4 group">
                                                <div className="col-span-4">
                                                    <input
                                                        type="text"
                                                        value={s.name}
                                                        onChange={(e) => updateSql(i, 'name', e.target.value)}
                                                        placeholder="例如: 查询去年销售额"
                                                        className="w-full px-4 py-2 border border-gray-200 rounded-xl text-sm focus:ring-2 focus:ring-indigo-500 outline-none transition-all"
                                                    />
                                                </div>
                                                <div className="col-span-7">
                                                    <textarea
                                                        value={s.sql}
                                                        onChange={(e) => updateSql(i, 'sql', e.target.value)}
                                                        placeholder="例如: SELECT SUM(amount) FROM sales WHERE year = 2023"
                                                        className="w-full px-4 py-2 border border-gray-200 rounded-xl text-sm focus:ring-2 focus:ring-indigo-500 outline-none transition-all font-mono min-h-[80px] resize-y"
                                                    />
                                                </div>
                                                <div className="col-span-1 flex items-start justify-center pt-2">
                                                    <button
                                                        onClick={() => removeSqlRow(i)}
                                                        className="p-2 text-gray-300 hover:text-red-500 hover:bg-red-50 rounded-lg transition-all"
                                                    >
                                                        <Icons.Trash className="w-4 h-4" />
                                                    </button>
                                                </div>
                                            </div>
                                        ))}
                                        <button
                                            onClick={addSqlRow}
                                            className="w-full py-3 border-2 border-dashed border-gray-100 rounded-xl text-gray-400 hover:border-indigo-200 hover:text-indigo-500 hover:bg-indigo-50/30 transition-all flex items-center justify-center gap-2 text-sm font-bold mt-4"
                                        >
                                            <Icons.Plus className="w-4 h-4" />
                                            新增参考 SQL
                                        </button>
                                    </div>
                                </div>
                            )}
                            <div className={`${type === 'knowledge' ? 'bg-blue-50/50 border-blue-100' : (type === 'vocabulary' ? 'bg-purple-50/50 border-purple-100' : 'bg-indigo-50/50 border-indigo-100')} p-4 rounded-xl border flex-shrink-0 mt-auto`}>
                                <p className={`text-xs ${type === 'knowledge' ? 'text-blue-700' : (type === 'vocabulary' ? 'text-purple-700' : 'text-indigo-700')} leading-relaxed`}>
                                    <strong>💡 提示：</strong> {type === 'knowledge' ? '您可以使用自然语言描述业务规则。' : (type === 'vocabulary' ? '定义的业务词汇将被 AI 用于理解您的提问，确保口径一致。' : '参考 SQL 将为 AI 生成查询提供范例，您可以提供正确的复杂查询逻辑供其参考。')} 保存后将立即生效。
                                </p>
                            </div>
                        </div>
                    )}
                </div>

                <div className="p-6 border-t border-gray-100 flex justify-end gap-3 bg-gray-50/50">
                    <button
                        onClick={onClose}
                        className="px-6 py-2.5 text-gray-600 hover:bg-white rounded-xl text-sm font-bold transition-all border border-transparent hover:border-gray-200"
                    >
                        取消
                    </button>
                    <button
                        onClick={handleSave}
                        disabled={saving}
                        className={`px-8 py-2.5 rounded-xl text-sm font-bold text-white transition-all shadow-lg flex items-center gap-2 ${
                            isGlobal ? 'bg-blue-600 hover:bg-blue-700 shadow-blue-900/10' : (type === 'knowledge' ? 'bg-emerald-600 hover:bg-emerald-700 shadow-emerald-900/10' : (type === 'vocabulary' ? 'bg-purple-600 hover:bg-purple-700 shadow-purple-900/10' : 'bg-indigo-600 hover:bg-indigo-700 shadow-indigo-900/10'))
                        } ${saving ? 'opacity-50 cursor-not-allowed' : 'active:scale-95'}`}
                    >
                        {saving ? '正在保存...' : '保存配置'}
                    </button>
                </div>
            </div>
        </div>
    );
};

export default KnowledgeEditor;
