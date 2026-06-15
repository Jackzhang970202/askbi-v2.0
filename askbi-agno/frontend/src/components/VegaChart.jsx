import React, { useEffect, useRef, useState } from 'react';

const VegaChart = ({ spec, compact = false }) => {

    const baseMinHeight = compact ? 240 : 300;

    const containerClassName = compact
        ? 'w-full h-full rounded-lg'
        : 'w-full';

    const containerStyle = compact
        ? { minHeight: baseMinHeight, height: '100%' }
        : { minHeight: baseMinHeight };

    const mergedSpec = spec ? {
        ...spec,
        width: spec.width || 'container',
        autosize: spec.autosize || { type: 'fit', contains: 'padding', resize: true },
    } : spec;
    const containerRef = useRef(null);
    const embedResultRef = useRef(null);
    const [error, setError] = useState(null);

    useEffect(() => {
        let cancelled = false;

        const render = async () => {
            const vegaEmbed = window.vegaEmbed;
            if (!vegaEmbed) {
                setError('Vega-Embed CDN 未加载，请检查网络连接后刷新页面');
                return;
            }
            if (!spec || !containerRef.current) return;

            // 如果上一轮已渲染，先销毁
            if (embedResultRef.current) {
                try { embedResultRef.current.finalize(); } catch (_) {}
                embedResultRef.current = null;
            }

            // 清空容器
            containerRef.current.innerHTML = '';

            // 合并默认配置
            const mergedRenderSpec = {
                ...mergedSpec,
                background: 'transparent',
                config: {
                    ...(mergedSpec?.config || {}),
                    view: { stroke: 'transparent', ...(mergedSpec?.config?.view || {}) },
                    axis: { labelColor: '#475569', titleColor: '#475569', ...(mergedSpec?.config?.axis || {}) },
                    legend: { labelColor: '#475569', titleColor: '#475569', ...(mergedSpec?.config?.legend || {}) },
                },
            };

            try {
                const tooltipInstance = window.vegaTooltip?.Handler ? new window.vegaTooltip.Handler() : null;
                const tooltipHandler = tooltipInstance ? tooltipInstance.call.bind(tooltipInstance) : true;
                const result = await vegaEmbed(containerRef.current, mergedRenderSpec, {
                    actions: false,
                    renderer: 'svg',
                    tooltip: tooltipHandler,
                });

                if (result?.view) {
                    result.view.tooltip(tooltipHandler);
                    result.view.runAsync();
                }
                if (!window.vegaTooltip?.Handler) {
                    console.warn('[VegaChart] vega-tooltip 未加载，回退默认 tooltip');
                }
                if (!cancelled) {
                    embedResultRef.current = result;
                    setError(null);
                } else {
                    result.finalize();
                }
            } catch (e) {
                console.error("[VegaChart] 渲染失败:", e);
                if (!cancelled) setError(`图表渲染失败: ${e.message}`);
            }
        };

        render();

        return () => {
            cancelled = true;
            if (embedResultRef.current) {
                try { embedResultRef.current.finalize(); } catch (_) {}
                embedResultRef.current = null;
            }
        };
    }, [spec]);

    if (error) {
        return (
            <div className="w-full min-h-[300px] flex items-center justify-center border-2 border-red-200 bg-red-50 rounded-xl">
                <div className="text-center p-6">
                    <div className="text-red-500 text-lg mb-2">图表错误</div>
                    <div className="text-red-600 text-sm font-medium">{error}</div>
                </div>
            </div>
        );
    }

    return <div ref={containerRef} className={containerClassName} style={containerStyle} />;
};

export default VegaChart;
