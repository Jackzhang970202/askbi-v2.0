import React from 'react';

/**
 * 兜底错误边界：避免前端运行时异常直接白屏。
 * 会把错误信息渲染出来，方便远端调试。
 */
export default class ErrorBoundary extends React.Component {
    constructor(props) {
        super(props);
        this.state = { hasError: false, error: null, errorInfo: null };
    }

    static getDerivedStateFromError(error) {
        return { hasError: true, error };
    }

    componentDidCatch(error, errorInfo) {
        // eslint-disable-next-line no-console
        console.error('[ErrorBoundary] Uncaught error:', error, errorInfo);
        this.setState({ error, errorInfo });
    }

    render() {
        if (this.state.hasError) {
            const msg = this.state.error?.message || String(this.state.error || 'Unknown error');
            const stack = this.state.error?.stack || '';
            const compStack = this.state.errorInfo?.componentStack || '';

            return (
                <div className="min-h-screen bg-gray-50 p-6">
                    <div className="max-w-4xl mx-auto bg-white border border-red-200 rounded-2xl shadow-sm p-6">
                        <div className="text-lg font-black text-red-600 mb-2">页面发生错误（已拦截，未白屏）</div>
                        <div className="text-sm text-gray-700 mb-4">请把下面信息发我，我可以继续修复。</div>
                        <div className="text-xs font-mono whitespace-pre-wrap bg-gray-50 border border-gray-200 rounded-xl p-4">
                            {msg}
                            {stack ? `\n\n${stack}` : ''}
                            {compStack ? `\n\nComponentStack:\n${compStack}` : ''}
                        </div>
                        <div className="mt-4 flex gap-2">
                            <button
                                onClick={() => window.location.reload()}
                                className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-bold"
                            >
                                刷新页面
                            </button>
                        </div>
                    </div>
                </div>
            );
        }

        return this.props.children;
    }
}


