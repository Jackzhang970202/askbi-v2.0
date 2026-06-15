import React, { useState } from 'react';
import { Icons } from './Icons';
import { withBase } from '../services/api';

const featureItems = [
    { title: '数据库自然语言问数', description: '面向业务问题快速生成查询与分析结论', icon: Icons.Database },
    { title: 'Excel 智能分析', description: '上传或挂载 Excel 后直接进行表格洞察与图表生成', icon: Icons.Table },
    { title: 'Skill 与记忆增强', description: '结合 Skill 与记忆模块提升连续性与专业性', icon: Icons.Lightbulb },
];

const LoginPage = ({ onLogin }) => {
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');

        if (!username.trim() || !password) {
            setError('请输入用户名和密码');
            return;
        }

        setLoading(true);
        try {
            const res = await fetch(withBase('/auth/login'), {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username: username.trim(), password })
            });

            const data = await res.json();

            if (data.success) {
                localStorage.setItem('askbi_token', data.token);
                localStorage.setItem('askbi_user', JSON.stringify(data.user));
                onLogin(data.user, data.token);
            } else {
                setError(data.error || '登录失败');
            }
        } catch {
            setError('网络错误，请稍后重试');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-blue-950 flex items-center justify-center p-6 lg:p-10 overflow-hidden">
            <div className="absolute inset-0 overflow-hidden pointer-events-none">
                <div className="absolute -top-28 left-1/2 h-72 w-72 -translate-x-1/2 rounded-full bg-blue-500/20 blur-3xl"></div>
                <div className="absolute top-1/3 -left-24 h-72 w-72 rounded-full bg-indigo-500/20 blur-3xl"></div>
                <div className="absolute bottom-0 right-0 h-80 w-80 rounded-full bg-cyan-500/10 blur-3xl"></div>
            </div>

            <div className="relative w-full max-w-6xl grid grid-cols-1 lg:grid-cols-[1.1fr_0.9fr] gap-8 items-stretch">
                <div className="hidden lg:flex flex-col justify-between rounded-[32px] border border-white/10 bg-white/6 backdrop-blur-xl p-10 shadow-2xl shadow-slate-950/30">
                    <div>
                        <div className="inline-flex items-center gap-3 rounded-2xl border border-white/10 bg-white/8 px-4 py-3 shadow-lg shadow-blue-950/20">
                            <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br from-blue-500 to-indigo-600 text-white shadow-lg shadow-blue-600/30">
                                <Icons.Bot className="w-6 h-6" />
                            </div>
                            <div>
                                <div className="text-2xl font-black text-white tracking-tight">AskBI</div>
                                <div className="text-sm text-blue-200/70 font-medium">统一会话驱动的智能分析平台</div>
                            </div>
                        </div>

                        <div className="mt-10 max-w-xl">
                            <h1 className="text-5xl font-black text-white leading-tight tracking-tight">
                                让数据问答、表格分析与业务洞察
                                <span className="block bg-gradient-to-r from-blue-300 via-cyan-300 to-indigo-300 bg-clip-text text-transparent">在同一会话里完成</span>
                            </h1>
                            <p className="mt-5 text-base leading-7 text-slate-300/90">
                                AskBI 面向真实业务场景，提供统一聊天入口、结构化分析结果、图表编辑能力与连续记忆增强，帮助团队更快完成从提问到结论交付的完整闭环。
                            </p>
                        </div>

                        <div className="mt-10 space-y-4">
                            {featureItems.map((item) => {
                                const Icon = item.icon;
                                return (
                                    <div key={item.title} className="rounded-2xl border border-white/10 bg-white/5 px-5 py-4 shadow-lg shadow-slate-950/10">
                                        <div className="flex items-start gap-4">
                                            <div className="mt-0.5 flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-gradient-to-br from-blue-500/25 to-indigo-500/25 text-blue-200 border border-blue-400/20">
                                                <Icon className="w-5 h-5" />
                                            </div>
                                            <div>
                                                <div className="text-base font-bold text-white">{item.title}</div>
                                                <div className="mt-1 text-sm leading-6 text-slate-300/80">{item.description}</div>
                                            </div>
                                        </div>
                                    </div>
                                );
                            })}
                        </div>
                    </div>

                    <div className="mt-10 flex items-center gap-3 text-xs text-slate-400/80">
                        <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1.5">统一会话</span>
                        <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1.5">Skill 增强</span>
                        <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1.5">图表分析</span>
                    </div>
                </div>

                <div className="flex items-center justify-center">
                    <div className="w-full max-w-md rounded-[32px] border border-white/10 bg-white/10 backdrop-blur-2xl p-8 shadow-2xl shadow-slate-950/30 lg:p-10">
                        <div className="lg:hidden text-center mb-8">
                            <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-3xl bg-gradient-to-br from-blue-500 to-indigo-600 text-white shadow-xl shadow-blue-600/30">
                                <Icons.Bot className="w-7 h-7" />
                            </div>
                            <h1 className="mt-5 text-3xl font-black text-white tracking-tight">AskBI</h1>
                            <p className="mt-2 text-sm text-blue-200/70">统一会话驱动的智能分析平台</p>
                        </div>

                        <div className="mb-8">
                            <h2 className="text-2xl font-black text-white tracking-tight">欢迎登录</h2>
                            <p className="mt-2 text-sm text-slate-300/80">进入 AskBI，开始数据问答与分析协作。</p>
                        </div>

                        <form onSubmit={handleSubmit} className="space-y-6">
                            {error && (
                                <div className="bg-red-500/10 border border-red-400/30 text-red-200 px-4 py-3 rounded-2xl text-sm font-medium flex items-center gap-2">
                                    <Icons.X className="w-4 h-4" />
                                    {error}
                                </div>
                            )}

                            <div className="space-y-2.5">
                                <label className="text-[10px] font-black text-blue-200/60 uppercase tracking-[0.2em] ml-1">用户名</label>
                                <div className="relative">
                                    <input
                                        type="text"
                                        value={username}
                                        onChange={(e) => setUsername(e.target.value)}
                                        placeholder="请输入用户名"
                                        className="w-full px-5 py-4 bg-white/6 border border-white/10 rounded-2xl text-white placeholder-white/25 focus:ring-2 focus:ring-blue-500/40 focus:border-blue-400/40 outline-none transition-all font-medium shadow-inner"
                                        autoComplete="username"
                                    />
                                    <Icons.User className="absolute right-4 top-1/2 -translate-y-1/2 w-5 h-5 text-white/20" />
                                </div>
                            </div>

                            <div className="space-y-2.5">
                                <label className="text-[10px] font-black text-blue-200/60 uppercase tracking-[0.2em] ml-1">密码</label>
                                <div className="relative">
                                    <input
                                        type="password"
                                        value={password}
                                        onChange={(e) => setPassword(e.target.value)}
                                        placeholder="请输入密码"
                                        className="w-full px-5 py-4 bg-white/6 border border-white/10 rounded-2xl text-white placeholder-white/25 focus:ring-2 focus:ring-blue-500/40 focus:border-blue-400/40 outline-none transition-all font-medium shadow-inner"
                                        autoComplete="current-password"
                                    />
                                    <Icons.Settings className="absolute right-4 top-1/2 -translate-y-1/2 w-5 h-5 text-white/20" />
                                </div>
                            </div>

                            <button
                                type="submit"
                                disabled={loading}
                                className={`w-full py-4 rounded-2xl font-black text-lg transition-all flex items-center justify-center gap-3 ${
                                    loading
                                        ? 'bg-blue-500/50 text-white/50 cursor-wait'
                                        : 'bg-gradient-to-r from-blue-600 to-indigo-600 text-white shadow-xl shadow-blue-600/30 hover:shadow-2xl hover:shadow-blue-600/40 hover:scale-[1.01] active:scale-95'
                                }`}
                            >
                                {loading ? (
                                    <>
                                        <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                                        登录中...
                                    </>
                                ) : (
                                    <>
                                        登录 AskBI
                                        <Icons.ArrowRight className="w-5 h-5" />
                                    </>
                                )}
                            </button>
                        </form>

                        <div className="mt-8 border-t border-white/10 pt-6 text-center text-xs text-blue-200/45 font-medium">
                            AskBI
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default LoginPage;
