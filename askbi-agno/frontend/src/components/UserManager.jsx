import React, { useState, useEffect } from 'react';
import { Icons } from './Icons';
import { withBase } from '../services/api';

const UserManager = ({ token, showAlert, showConfirm }) => {
    const [users, setUsers] = useState([]);
    const [loading, setLoading] = useState(false);
    const [showModal, setShowModal] = useState(false);
    const [formData, setFormData] = useState({ username: '', password: '', role: 'user' });
    const [error, setError] = useState('');

    const fetchUsers = async () => {
        setLoading(true);
        try {
            const res = await fetch(withBase('/auth/users'), {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            const data = await res.json();
            if (data.success) {
                setUsers(data.users || []);
            } else {
                setError(data.error || '获取用户列表失败');
            }
        } catch (err) {
            setError('网络错误');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchUsers();
    }, [token]);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');
        
        if (!formData.username.trim() || !formData.password) {
            setError('用户名和密码不能为空');
            return;
        }
        
        try {
            const res = await fetch(withBase('/auth/users'), {
                method: 'POST',
                headers: { 
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify(formData)
            });
            const data = await res.json();
            if (data.success) {
                setShowModal(false);
                setFormData({ username: '', password: '', role: 'user' });
                fetchUsers();
            } else {
                setError(data.error || '创建失败');
            }
        } catch (err) {
            setError('网络错误');
        }
    };

    const handleDelete = async (userId, username) => {
        // 使用浏览器原生确认框
        if (!window.confirm(`确定要删除用户 "${username}" 吗？`)) return;

        try {
            const res = await fetch(withBase(`/auth/users/${userId}`), {
                method: 'DELETE',
                headers: { 'Authorization': `Bearer ${token}` }
            });
            const data = await res.json();
            if (data.success) {
                fetchUsers();
            } else {
                console.error(data.error || '删除失败');
            }
        } catch (err) {
            console.error('网络错误');
        }
    };

    return (
        <div className="flex-1 flex flex-col bg-white overflow-hidden h-full">
            {/* Header */}
            <div className="h-16 bg-white border-b border-gray-200/60 flex items-center justify-between px-8 shrink-0">
                <div className="flex items-center gap-4">
                    <div className="p-1.5 bg-amber-100 text-amber-600 rounded-lg">
                        <Icons.User className="w-5 h-5" />
                    </div>
                    <div>
                        <h2 className="font-bold text-gray-800 text-sm">用户管理</h2>
                        <div className="text-[10px] text-gray-400 font-medium">管理系统用户账号</div>
                    </div>
                </div>
                <button
                    onClick={() => {
                        setFormData({ username: '', password: '', role: 'user' });
                        setError('');
                        setShowModal(true);
                    }}
                    className="px-6 py-2.5 bg-amber-500 hover:bg-amber-600 text-white rounded-xl text-xs font-black shadow-lg shadow-amber-500/30 transition-all flex items-center gap-2"
                >
                    <Icons.Plus className="w-4 h-4" />
                    新建用户
                </button>
            </div>

            {/* Content */}
            <div className="flex-1 p-8 overflow-auto">
                {loading ? (
                    <div className="flex flex-col items-center justify-center py-20 gap-3">
                        <div className="w-8 h-8 border-4 border-amber-500 border-t-transparent rounded-full animate-spin"></div>
                        <p className="text-[10px] font-black text-gray-400 uppercase">加载中...</p>
                    </div>
                ) : users.length === 0 ? (
                    <div className="text-center py-20 bg-gray-50/50 rounded-3xl border-2 border-dashed border-gray-200">
                        <Icons.User className="w-12 h-12 mx-auto mb-4 text-gray-200" />
                        <p className="text-sm font-bold text-gray-400">暂无用户</p>
                    </div>
                ) : (
                    <div className="bg-white border border-gray-100 rounded-2xl overflow-hidden shadow-sm">
                        <table className="w-full text-left border-collapse">
                            <thead className="bg-gray-50/80">
                                <tr>
                                    <th className="px-6 py-4 text-sm font-medium text-gray-500 border-b border-gray-100">ID</th>
                                    <th className="px-6 py-4 text-sm font-medium text-gray-500 border-b border-gray-100">用户名</th>
                                    <th className="px-6 py-4 text-sm font-medium text-gray-500 border-b border-gray-100">角色</th>
                                    <th className="px-6 py-4 text-sm font-medium text-gray-500 border-b border-gray-100">创建时间</th>
                                    <th className="px-6 py-4 text-sm font-medium text-gray-500 border-b border-gray-100 text-right">操作</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-gray-50">
                                {users.map(user => (
                                    <tr key={user.id} className="hover:bg-gray-50/30 transition-colors">
                                        <td className="px-6 py-5 text-sm text-gray-500">{user.id}</td>
                                        <td className="px-6 py-5">
                                            <span className="text-sm font-medium text-gray-900">{user.username}</span>
                                        </td>
                                        <td className="px-6 py-5">
                                            <span className={`px-2 py-1 rounded-lg text-xs font-bold ${
                                                user.role === 'admin' 
                                                ? 'bg-red-100 text-red-700' 
                                                : user.role === 'manager'
                                                ? 'bg-amber-100 text-amber-700'
                                                : 'bg-gray-100 text-gray-600'
                                            }`}>
                                                {user.role === 'admin' ? '超级管理员' : user.role === 'manager' ? '管理员' : '普通用户'}
                                            </span>
                                        </td>
                                        <td className="px-6 py-5 text-sm text-gray-500">{user.create_time}</td>
                                        <td className="px-6 py-5 text-right">
                                            {user.username !== 'admin' && (
                                                <button
                                                    onClick={() => handleDelete(user.id, user.username)}
                                                    className="text-gray-400 hover:text-red-500 transition-colors"
                                                    title="删除"
                                                >
                                                    <Icons.Trash className="w-5 h-5" />
                                                </button>
                                            )}
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>

            {/* Create User Modal */}
            {showModal && (
                <div className="fixed inset-0 bg-black/60 backdrop-blur-md z-[100] flex items-center justify-center p-4">
                    <div className="bg-white rounded-3xl w-full max-w-md shadow-2xl overflow-hidden animate-slide-up">
                        <div className="p-6 border-b border-gray-100 flex justify-between items-center bg-gray-50/50">
                            <div>
                                <h2 className="text-xl font-black text-gray-800">新建用户</h2>
                                <p className="text-sm text-gray-500 font-medium">创建新的系统账号</p>
                            </div>
                            <button onClick={() => setShowModal(false)} className="p-2 hover:bg-white rounded-xl transition-all">
                                <Icons.X className="w-5 h-5 text-gray-400" />
                            </button>
                        </div>
                        
                        <form onSubmit={handleSubmit} className="p-6 space-y-5">
                            {error && (
                                <div className="bg-red-50 border border-red-100 text-red-600 px-4 py-3 rounded-xl text-sm font-medium">
                                    {error}
                                </div>
                            )}
                            
                            <div className="space-y-2">
                                <label className="text-xs font-black text-gray-400 uppercase tracking-widest">用户名</label>
                                <input
                                    type="text"
                                    value={formData.username}
                                    onChange={e => setFormData({ ...formData, username: e.target.value })}
                                    placeholder="请输入用户名"
                                    className="w-full px-4 py-3 bg-gray-50 border border-gray-200 rounded-xl focus:ring-2 focus:ring-amber-500/20 focus:border-amber-500 outline-none transition-all font-medium"
                                    required
                                />
                            </div>
                            
                            <div className="space-y-2">
                                <label className="text-xs font-black text-gray-400 uppercase tracking-widest">密码</label>
                                <input
                                    type="password"
                                    value={formData.password}
                                    onChange={e => setFormData({ ...formData, password: e.target.value })}
                                    placeholder="请输入密码"
                                    className="w-full px-4 py-3 bg-gray-50 border border-gray-200 rounded-xl focus:ring-2 focus:ring-amber-500/20 focus:border-amber-500 outline-none transition-all font-medium"
                                    required
                                />
                            </div>
                            
                            <div className="space-y-2">
                                <label className="text-xs font-black text-gray-400 uppercase tracking-widest">角色</label>
                                <select
                                    value={formData.role}
                                    onChange={e => setFormData({ ...formData, role: e.target.value })}
                                    className="w-full px-4 py-3 bg-gray-50 border border-gray-200 rounded-xl focus:ring-2 focus:ring-amber-500/20 focus:border-amber-500 outline-none transition-all font-medium"
                                >
                                    <option value="user">普通用户</option>
                                    <option value="manager">管理员（可查看所有数据）</option>
                                    <option value="admin">超级管理员（可用户管理）</option>
                                </select>
                            </div>
                            
                            <div className="flex gap-3 pt-4">
                                <button
                                    type="button"
                                    onClick={() => setShowModal(false)}
                                    className="flex-1 py-3 text-gray-500 font-bold hover:bg-gray-100 rounded-xl transition-all"
                                >
                                    取消
                                </button>
                                <button
                                    type="submit"
                                    className="flex-1 py-3 bg-amber-500 text-white rounded-xl font-black shadow-lg shadow-amber-500/20 hover:bg-amber-600 transition-all"
                                >
                                    创建
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
        </div>
    );
};

export default UserManager;

