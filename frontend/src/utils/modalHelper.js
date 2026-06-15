/**
 * Modal 辅助函数 - 用于在组件中优雅地使用自定义弹窗
 * 如果传入了 showAlert/showConfirm，使用自定义弹窗；否则回退到浏览器原生弹窗
 */

export const safeAlert = (showAlert, message, title = '提示', type = 'alert') => {
    if (showAlert) {
        showAlert(message, title, type);
    } else {
        alert(message);
    }
};

export const safeConfirm = async (showConfirm, message, onConfirm, title = '确认') => {
    if (showConfirm) {
        return new Promise((resolve) => {
            showConfirm(message, () => {
                if (onConfirm) onConfirm();
                resolve(true);
            }, title);
        });
    } else {
        const result = window.confirm(message);
        if (result && onConfirm) onConfirm();
        return result;
    }
};
