import React from 'react';

/**
 * 自定义弹窗组件 - 替代浏览器原生的 alert 和 confirm
 */
const Modal = ({ isOpen, onClose, title, message, type = 'alert', onConfirm, onCancel }) => {
    if (!isOpen) return null;

    const handleConfirm = () => {
        if (onConfirm) onConfirm();
        onClose();
    };

    const handleCancel = () => {
        if (onCancel) onCancel();
        onClose();
    };

    // 根据类型选择图标和颜色
    const getIcon = () => {
        switch (type) {
            case 'success':
                return (
                    <svg className="w-12 h-12 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                    </svg>
                );
            case 'error':
                return (
                    <svg className="w-12 h-12 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                );
            case 'warning':
            case 'confirm':
                return (
                    <svg className="w-12 h-12 text-yellow-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                    </svg>
                );
            default:
                return (
                    <svg className="w-12 h-12 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                );
        }
    };

    return (
        <div className="fixed inset-0 z-[9999] flex items-center justify-center">
            {/* 遮罩层 */}
            <div 
                className="absolute inset-0 bg-black bg-opacity-50 transition-opacity"
                onClick={type !== 'confirm' ? handleCancel : undefined}
            />
            
            {/* 弹窗内容 */}
            <div className="relative bg-white rounded-2xl shadow-2xl max-w-md w-full mx-4 transform transition-all animate-scale-in">
                {/* 关闭按钮 */}
                {type !== 'confirm' && (
                    <button
                        onClick={handleCancel}
                        className="absolute top-4 right-4 text-gray-400 hover:text-gray-600 transition-colors"
                    >
                        <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                        </svg>
                    </button>
                )}

                {/* 内容区域 */}
                <div className="p-6 text-center">
                    {/* 图标 */}
                    <div className="flex justify-center mb-4">
                        {getIcon()}
                    </div>

                    {/* 标题 */}
                    {title && (
                        <h3 className="text-xl font-semibold text-gray-900 mb-2">
                            {title}
                        </h3>
                    )}

                    {/* 消息内容 */}
                    <div className="text-gray-600 mb-6 whitespace-pre-wrap">
                        {message}
                    </div>

                    {/* 按钮区域 */}
                    <div className="flex gap-3 justify-center">
                        {type === 'confirm' ? (
                            <>
                                <button
                                    onClick={handleCancel}
                                    className="px-6 py-2.5 bg-gray-200 text-gray-700 rounded-lg font-medium hover:bg-gray-300 transition-colors min-w-[100px]"
                                >
                                    取消
                                </button>
                                <button
                                    onClick={handleConfirm}
                                    className="px-6 py-2.5 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 transition-colors min-w-[100px]"
                                >
                                    确定
                                </button>
                            </>
                        ) : (
                            <button
                                onClick={handleCancel}
                                className="px-8 py-2.5 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 transition-colors min-w-[120px]"
                            >
                                确定
                            </button>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
};

// 添加动画样式
const style = document.createElement('style');
style.textContent = `
    @keyframes scale-in {
        from {
            opacity: 0;
            transform: scale(0.9);
        }
        to {
            opacity: 1;
            transform: scale(1);
        }
    }
    .animate-scale-in {
        animation: scale-in 0.2s ease-out;
    }
`;
document.head.appendChild(style);

export default Modal;
