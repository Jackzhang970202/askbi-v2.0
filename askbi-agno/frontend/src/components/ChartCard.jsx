import React, { useMemo, useState } from 'react';
import { createPortal } from 'react-dom';
import { Icons } from './Icons';
import VegaChart from './VegaChart';

const THEME_OPTIONS = [
    { key: 'ocean', label: '海洋', colors: ['#2680D9', '#28A4BD', '#4D62CB'] },
    { key: 'warm', label: '暖色', colors: ['#E76E50', '#2A9D90', '#274754'] },
    { key: 'forest', label: '森林', colors: ['#339955', '#73A63F', '#367D65'] },
    { key: 'sunset', label: '日落', colors: ['#E89C30', '#E25336', '#D7425B'] },
    { key: 'mono', label: '单色', colors: ['#47566B', '#6C7C93', '#9DA4AF'] },
];

const CHART_TYPES = [
    { key: 'bar', label: '柱状图' },
    { key: 'line', label: '折线图' },
    { key: 'area', label: '面积图' },
    { key: 'point', label: '散点图' },
    { key: 'arc', label: '饼图' },
];

const AGGREGATIONS = [
    { key: 'none', label: '原值' },
    { key: 'sum', label: '求和' },
    { key: 'average', label: '平均值' },
    { key: 'count', label: '计数' },
    { key: 'max', label: '最大值' },
    { key: 'min', label: '最小值' },
];

const normalizeText = (value, fallback = '') => {
    if (typeof value === 'string') return value;
    if (typeof value === 'number') return String(value);
    if (value && typeof value === 'object') {
        if (typeof value.text === 'string') return value.text;
        if (typeof value.subtitle === 'string') return value.subtitle;
        if (typeof value.anchor === 'string') return value.anchor;
    }
    return fallback;
};

const normalizeRows = (values) => Array.isArray(values)
    ? values.filter((item) => item && typeof item === 'object' && !Array.isArray(item))
    : [];

const detectFieldType = (value) => {
    if (value == null) return 'nominal';
    if (typeof value === 'number') return 'quantitative';
    if (typeof value === 'string' && /^\d{4}[-/]\d{1,2}([-/]\d{1,2})?$/.test(value)) return 'temporal';
    return 'nominal';
};

const inferOriginalMark = (spec) => {
    if (!spec) return 'line';
    if (typeof spec.mark === 'string') return spec.mark;
    if (spec.mark?.type) return spec.mark.type;
    if (Array.isArray(spec.layer) && spec.layer[0]?.mark) {
        return typeof spec.layer[0].mark === 'string' ? spec.layer[0].mark : spec.layer[0].mark.type || 'line';
    }
    return 'line';
};

const collectFields = (rows) => {
    const first = rows[0] || {};
    return Object.keys(first)
        .filter((key) => typeof first[key] !== 'object' || first[key] === null)
        .map((key) => ({ key, type: detectFieldType(first[key]) }));
};

const pickInitialFields = (rows, spec) => {
    const fields = collectFields(rows);
    const encoding = spec?.encoding || spec?.layer?.[0]?.encoding || {};
    const xField = encoding?.x?.field || fields.find((item) => item.type !== 'quantitative')?.key || fields[0]?.key || '';
    const yField = encoding?.y?.field || encoding?.theta?.field || fields.find((item) => item.type === 'quantitative')?.key || fields[1]?.key || '';
    const colorField = encoding?.color?.field || '';
    const aggregation = encoding?.y?.aggregate || 'none';
    return { fields, xField, yField, colorField, aggregation };
};

const findFieldType = (fields, key) => fields.find((item) => item.key === key)?.type || 'nominal';

const buildColorEncoding = (field, type, theme, showLegend, orient = 'top') => ({
    field,
    type,
    scale: { range: theme.colors },
    legend: showLegend ? { orient, direction: orient === 'right' ? 'vertical' : 'horizontal', labelColor: '#475569', titleColor: '#475569' } : null,
});

const buildTooltip = (xField, xType, yField, colorField, colorType, aggregation) => {
    const tooltip = [];
    if (xField) tooltip.push({ field: xField, type: xType, title: xField });
    if (yField) tooltip.push({ field: yField, type: 'quantitative', title: yField, aggregate: aggregation !== 'none' ? aggregation : undefined });
    if (colorField) tooltip.push({ field: colorField, type: colorType, title: colorField });
    return tooltip;
};

const supportsChartType = (chartType, xType, yType) => {
    if (chartType === 'arc') return yType === 'quantitative';
    if (chartType === 'point') return yType === 'quantitative';
    if (chartType === 'line' || chartType === 'area') return yType === 'quantitative' && (xType === 'temporal' || xType === 'nominal');
    return yType === 'quantitative';
};

const getEffectiveConfig = ({ rows, chartType, xField, yField, colorField, aggregation, stackMode }) => {
    const xDistinct = new Set(rows.map((row) => row?.[xField]).filter((value) => value != null)).size;
    const next = {
        chartType,
        colorField,
        aggregation,
        stackMode,
    };

    if ((chartType === 'line' || chartType === 'area') && xDistinct < 2) {
        next.chartType = 'bar';
    }

    if (next.chartType === 'line' || next.chartType === 'area') {
        next.aggregation = 'none';
    }

    if (next.chartType === 'line') {
        next.stackMode = 'group';
    }

    if (next.chartType === 'area') {
        next.stackMode = stackMode === 'percent' ? 'percent' : 'stack';
    }

    if (colorField) {
        const groups = new Map();
        rows.forEach((row) => {
            const colorValue = row?.[colorField];
            const xValue = row?.[xField];
            if (colorValue == null || xValue == null) return;
            if (!groups.has(colorValue)) groups.set(colorValue, new Set());
            groups.get(colorValue).add(xValue);
        });
        const maxPointsPerSeries = groups.size ? Math.max(...Array.from(groups.values()).map((set) => set.size)) : 0;
        if ((next.chartType === 'line' || next.chartType === 'area') && maxPointsPerSeries < 2) {
            next.colorField = '';
        }
    }

    return next;
};

const buildCommonBase = (title, chartType) => ({
    $schema: 'https://vega.github.io/schema/vega-lite/v5.json',
    title,
    width: 'container',
    height: 320,
    padding: chartType === 'arc'
        ? { top: 16, right: 140, bottom: 16, left: 16 }
        : { top: 16, right: 16, bottom: 16, left: 16 },
    autosize: { type: 'fit', contains: 'padding', resize: true },
    config: {
        view: { stroke: 'transparent' },
        axis: { gridColor: '#e2e8f0', domainColor: '#cbd5e1', tickColor: '#cbd5e1', labelColor: '#64748b', titleColor: '#475569' },
        legend: { labelColor: '#475569', titleColor: '#475569', symbolType: 'circle' },
    },
});

const buildSpec = ({ rows, title, chartType, xField, yField, colorField, theme, style, showLegend, showLabels, showAxes, showGrid, sortMode, aggregation, stackMode, fields }) => {
    const xType = findFieldType(fields, xField);
    const colorType = findFieldType(fields, colorField);
    const effective = getEffectiveConfig({ rows, chartType, xField, yField, colorField, aggregation, stackMode });
    const hasColorField = !!effective.colorField;
    const tooltip = buildTooltip(xField, xType, yField, effective.colorField, colorType, effective.aggregation);
    const base = buildCommonBase(title, effective.chartType);
    base.data = { values: rows };
    base.config.axis.grid = showGrid;

    if (effective.chartType === 'arc') {
        return {
            ...base,
            mark: { type: 'arc', innerRadius: style === 'rounded' ? 48 : 0, cornerRadius: style === 'rounded' ? 4 : 0 },
            encoding: {
                theta: { field: yField, type: 'quantitative' },
                color: hasColorField
                    ? buildColorEncoding(effective.colorField, colorType, theme, showLegend, 'right')
                    : buildColorEncoding(xField, xType, theme, showLegend, 'right'),
                tooltip,
            },
        };
    }

    const encoding = {
        x: {
            field: xField,
            type: xType,
            axis: showAxes ? { labelColor: '#64748b', titleColor: '#475569', labelFontSize: 11, titleFontSize: 12 } : null,
            sort: effective.chartType === 'line' || effective.chartType === 'area' || xType === 'temporal'
                ? undefined
                : sortMode === 'desc' ? '-y' : sortMode === 'asc' ? 'y' : undefined,
        },
        y: {
            field: yField,
            type: 'quantitative',
            aggregate: effective.aggregation !== 'none' ? effective.aggregation : undefined,
            axis: showAxes ? { labelColor: '#64748b', titleColor: '#475569', labelFontSize: 11, titleFontSize: 12 } : null,
        },
        tooltip,
    };

    if (hasColorField) {
        encoding.color = buildColorEncoding(effective.colorField, colorType, theme, showLegend, 'top');
    }

    if (effective.chartType === 'bar') {
        encoding.y.stack = effective.stackMode === 'stack' ? 'zero' : effective.stackMode === 'percent' ? 'normalize' : null;
    }

    if (effective.chartType === 'line') {
        if (hasColorField) encoding.detail = { field: effective.colorField, type: colorType };
        return {
            ...base,
            mark: { type: 'line', strokeWidth: 2, point: true, interpolate: style === 'rounded' ? 'monotone' : 'linear', color: hasColorField ? undefined : theme.colors[0] },
            encoding,
        };
    }

    if (effective.chartType === 'area') {
        if (hasColorField) encoding.detail = { field: effective.colorField, type: colorType };
        encoding.y.stack = hasColorField ? (effective.stackMode === 'percent' ? 'normalize' : 'zero') : null;
        return {
            ...base,
            mark: { type: 'area', interpolate: style === 'rounded' ? 'monotone' : 'linear', opacity: 0.68, color: hasColorField ? undefined : theme.colors[0] },
            encoding,
        };
    }

    if (effective.chartType === 'point') {
        if (hasColorField) encoding.detail = { field: effective.colorField, type: colorType };
        return {
            ...base,
            mark: { type: 'point', filled: true, size: 80, color: hasColorField ? undefined : theme.colors[0] },
            encoding,
        };
    }

    const barSpec = {
        ...base,
        mark: { type: 'bar', cornerRadiusTopLeft: style === 'rounded' ? 8 : 0, cornerRadiusTopRight: style === 'rounded' ? 8 : 0, color: hasColorField ? undefined : theme.colors[0] },
        encoding,
    };

    if (showLabels) {
        return {
            ...base,
            layer: [
                { mark: barSpec.mark, encoding: barSpec.encoding },
                {
                    mark: { type: 'text', dy: -10, color: '#475569', fontSize: 11 },
                    encoding: {
                        ...barSpec.encoding,
                        text: { field: yField, type: 'quantitative', aggregate: effective.aggregation !== 'none' ? effective.aggregation : undefined },
                    },
                },
            ],
        };
    }

    return barSpec;
};

const SmallToggle = ({ checked, onChange }) => (
    <button type="button" role="switch" aria-checked={checked} onClick={() => onChange(!checked)} className={`relative inline-flex h-6 w-10 items-center rounded-full transition-colors ${checked ? 'bg-blue-600' : 'bg-gray-200'}`}>
        <span className={`inline-block h-4 w-4 rounded-full bg-white transition-transform ${checked ? 'translate-x-5' : 'translate-x-1'}`} />
    </button>
);

const SegmentButton = ({ active, onClick, children }) => (
    <button type="button" onClick={onClick} className={`rounded-md border px-3 py-1.5 text-xs font-medium transition-colors ${active ? 'border-blue-500 bg-blue-50 text-blue-700' : 'border-gray-200 text-gray-600 hover:border-blue-300 hover:text-blue-700'}`}>
        {children}
    </button>
);

const ChartCard = ({ spec, title }) => {
    const rows = useMemo(() => normalizeRows(spec?.data?.values), [spec]);
    const themeDefault = THEME_OPTIONS[0];
    const originalMark = useMemo(() => inferOriginalMark(spec), [spec]);
    const inferred = useMemo(() => pickInitialFields(rows, spec), [rows, spec]);

    const [drawerOpen, setDrawerOpen] = useState(false);
    const [viewMode, setViewMode] = useState('chart');
    const [editorState, setEditorState] = useState({
        title: normalizeText(title, normalizeText(spec?.title, '数据图表')),
        chartType: originalMark,
        xField: inferred.xField,
        yField: inferred.yField,
        colorField: inferred.colorField,
        themeKey: themeDefault.key,
        style: 'rounded',
        showLegend: true,
        showLabels: false,
        showAxes: true,
        showGrid: true,
        sortMode: 'none',
        aggregation: inferred.aggregation || 'none',
        stackMode: originalMark === 'area' ? 'stack' : 'group',
    });

    const fieldMeta = inferred.fields;
    const xType = findFieldType(fieldMeta, editorState.xField);
    const yType = findFieldType(fieldMeta, editorState.yField);
    const availableChartTypes = useMemo(() => CHART_TYPES.filter((item) => supportsChartType(item.key, xType, yType)), [xType, yType]);
    const activeTheme = useMemo(() => THEME_OPTIONS.find((item) => item.key === editorState.themeKey) || themeDefault, [editorState.themeKey]);
    const previewSpec = useMemo(() => buildSpec({
        rows,
        title: editorState.title,
        chartType: editorState.chartType,
        xField: editorState.xField,
        yField: editorState.yField,
        colorField: editorState.colorField,
        theme: activeTheme,
        style: editorState.style,
        showLegend: editorState.showLegend,
        showLabels: editorState.showLabels,
        showAxes: editorState.showAxes,
        showGrid: editorState.showGrid,
        sortMode: editorState.sortMode,
        aggregation: editorState.aggregation,
        stackMode: editorState.stackMode,
        fields: fieldMeta,
    }), [rows, editorState, activeTheme, fieldMeta]);

    const compactPreviewSpec = useMemo(() => {
        const next = {
            ...previewSpec,
            title: '',
            height: 260,
            padding: { top: 12, right: 12, bottom: 12, left: 12 },
        };
        if (editorState.chartType === 'arc' && next.encoding?.color) {
            next.encoding = {
                ...next.encoding,
                color: {
                    ...next.encoding.color,
                    legend: editorState.showLegend ? { orient: 'top', direction: 'horizontal', labelColor: '#475569', titleColor: '#475569' } : null,
                },
            };
        }
        return next;
    }, [previewSpec, editorState.chartType, editorState.showLegend]);

    const tableKeys = useMemo(() => Object.keys(rows[0] || {}).filter((key) => typeof rows[0]?.[key] !== 'object' || rows[0]?.[key] === null), [rows]);

    const updateField = (key, value) => setEditorState((prev) => ({ ...prev, [key]: value }));
    const openDrawerWithView = (nextView) => {
        setViewMode(nextView);
        setDrawerOpen(true);
    };

    return (
        <>
            <div className="flex flex-col gap-3 lg:flex-row">
                <div className={`flex-1 overflow-hidden rounded-2xl border bg-white shadow-sm ${drawerOpen ? 'ring-2 ring-blue-500/70' : 'border-gray-200'}`}>
                    <div className="h-[320px] w-full bg-gradient-to-b from-slate-50/70 to-white p-3">
                        <div className="h-full w-full overflow-hidden rounded-xl border border-gray-100 bg-white">
                            <VegaChart spec={compactPreviewSpec} compact />
                        </div>
                    </div>
                    <div className="flex items-center gap-2 border-t border-gray-100 px-4 py-3">
                        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-blue-50 text-blue-600">
                            <Icons.Table className="w-4 h-4" />
                        </div>
                        <p className="min-w-0 flex-1 truncate text-sm font-semibold text-gray-800">{editorState.title || '数据图表'}</p>
                        <button type="button" onClick={() => openDrawerWithView('table')} className="shrink-0 rounded-md p-1.5 text-gray-400 hover:bg-gray-100 hover:text-gray-700">
                            <Icons.Table className="w-4 h-4" />
                        </button>
                        <button type="button" onClick={() => openDrawerWithView('chart')} className="shrink-0 rounded-md p-1.5 text-gray-400 hover:bg-gray-100 hover:text-gray-700">
                            <Icons.Settings className="w-4 h-4" />
                        </button>
                    </div>
                </div>
            </div>

            {drawerOpen && typeof document !== 'undefined' && createPortal(
                <div className="fixed inset-0 z-[12000]">
                    <div className="absolute inset-0 bg-black/45" onClick={() => setDrawerOpen(false)} />
                    <div className="absolute inset-y-0 right-0 flex w-full max-w-[1200px] justify-end">
                        <div className="flex h-full w-full max-w-[1120px] bg-white shadow-2xl">
                            <div className="min-w-0 flex-1 border-r border-gray-200 bg-gray-50/60">
                                <div className="flex h-full flex-col">
                                    <div className="flex items-center justify-between border-b border-gray-200 bg-white px-5 py-3">
                                        <p className="min-w-0 flex-1 truncate text-sm font-semibold text-gray-800">{editorState.title || '数据图表'}</p>
                                        <button type="button" onClick={() => setDrawerOpen(false)} className="rounded-md p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-700">
                                            <Icons.X />
                                        </button>
                                    </div>
                                    <div className="flex shrink-0 border-b border-gray-200 bg-white">
                                        <button type="button" onClick={() => setViewMode('table')} className={`flex items-center gap-1.5 px-4 py-2 text-xs font-medium transition-colors ${viewMode === 'table' ? 'border-b-2 border-blue-600 text-blue-600' : 'text-gray-500 hover:text-gray-800'}`}>
                                            <Icons.Table className="w-3.5 h-3.5" />表格
                                        </button>
                                        <button type="button" onClick={() => setViewMode('chart')} className={`flex items-center gap-1.5 px-4 py-2 text-xs font-medium transition-colors ${viewMode === 'chart' ? 'border-b-2 border-blue-600 text-blue-600' : 'text-gray-500 hover:text-gray-800'}`}>
                                            <Icons.Database className="w-3.5 h-3.5" />图表
                                        </button>
                                    </div>
                                    <div className="min-h-0 flex-1 overflow-auto p-5">
                                        {viewMode === 'chart' ? (
                                            <div className="rounded-2xl border border-gray-200 bg-white p-4 shadow-sm">
                                                <div className="h-[520px] w-full rounded-xl bg-white">
                                                    <VegaChart spec={{ ...previewSpec, title: '' }} />
                                                </div>
                                            </div>
                                        ) : (
                                            <div className="overflow-hidden rounded-2xl border border-gray-200 bg-white shadow-sm">
                                                <div className="overflow-x-auto">
                                                    <table className="min-w-full divide-y divide-gray-200 text-sm">
                                                        <thead className="bg-slate-50">
                                                            <tr>
                                                                {tableKeys.map((key) => (
                                                                    <th key={key} className="whitespace-nowrap px-4 py-3 text-left text-xs font-semibold text-gray-500">{key}</th>
                                                                ))}
                                                            </tr>
                                                        </thead>
                                                        <tbody className="divide-y divide-gray-100 bg-white">
                                                            {rows.slice(0, 30).map((row, rowIndex) => (
                                                                <tr key={rowIndex}>
                                                                    {tableKeys.map((key) => (
                                                                        <td key={key} className="whitespace-nowrap px-4 py-2.5 text-sm text-gray-700">{normalizeText(row[key], String(row[key] ?? ''))}</td>
                                                                    ))}
                                                                </tr>
                                                            ))}
                                                        </tbody>
                                                    </table>
                                                </div>
                                            </div>
                                        )}
                                    </div>
                                </div>
                            </div>

                            <div className="h-full w-[380px] overflow-y-auto bg-white p-5">
                                <div className="space-y-6">
                                    <div className="space-y-2">
                                        <label className="text-sm font-medium text-gray-800">标题</label>
                                        <input value={editorState.title} onChange={(e) => updateField('title', e.target.value)} className="h-10 w-full rounded-lg border border-gray-200 px-3 text-sm outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-100" placeholder="图表标题" />
                                    </div>

                                    <div className="space-y-2">
                                        <label className="text-sm font-medium text-gray-800">图表类型</label>
                                        <div className="grid grid-cols-3 gap-2">
                                            {CHART_TYPES.map((item) => {
                                                const enabled = availableChartTypes.some((type) => type.key === item.key);
                                                return (
                                                    <button
                                                        key={item.key}
                                                        type="button"
                                                        disabled={!enabled}
                                                        onClick={() => enabled && updateField('chartType', item.key)}
                                                        className={`rounded-lg border p-2 text-xs font-medium transition-colors ${editorState.chartType === item.key ? 'border-blue-500 bg-blue-50 text-blue-700' : enabled ? 'border-gray-200 text-gray-600 hover:border-blue-300 hover:text-blue-700' : 'cursor-not-allowed border-gray-100 text-gray-300'}`}
                                                    >
                                                        {item.label}
                                                    </button>
                                                );
                                            })}
                                        </div>
                                    </div>

                                    <div className="space-y-2">
                                        <label className="text-sm font-medium text-gray-800">视觉风格</label>
                                        <div className="flex gap-2">
                                            <SegmentButton active={editorState.style === 'rounded'} onClick={() => updateField('style', 'rounded')}>圆润</SegmentButton>
                                            <SegmentButton active={editorState.style === 'sharp'} onClick={() => updateField('style', 'sharp')}>锐利</SegmentButton>
                                        </div>
                                    </div>

                                    <div className="space-y-2">
                                        <label className="text-sm font-medium text-gray-800">主题色</label>
                                        <div className="flex flex-wrap gap-2">
                                            {THEME_OPTIONS.map((item) => (
                                                <button key={item.key} type="button" onClick={() => updateField('themeKey', item.key)} className={`flex gap-0.5 rounded-lg border p-1.5 ${editorState.themeKey === item.key ? 'border-blue-500 ring-1 ring-blue-500' : 'border-gray-200 hover:border-blue-300'}`} title={item.label}>
                                                    {item.colors.map((color) => <span key={color} className="h-4 w-4 rounded-sm" style={{ backgroundColor: color }} />)}
                                                </button>
                                            ))}
                                        </div>
                                    </div>

                                    <div className="grid grid-cols-2 gap-3">
                                        <div className="space-y-1.5">
                                            <label className="text-sm font-medium text-gray-800">横轴（类别）</label>
                                            <select value={editorState.xField} onChange={(e) => updateField('xField', e.target.value)} className="h-10 w-full rounded-lg border border-gray-200 bg-white px-3 text-sm outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-100">
                                                {fieldMeta.map((field) => <option key={field.key} value={field.key}>{field.key}（{field.type === 'quantitative' ? '数值' : field.type === 'temporal' ? '时间' : '分类'}）</option>)}
                                            </select>
                                        </div>
                                        <div className="space-y-1.5">
                                            <label className="text-sm font-medium text-gray-800">纵轴（数值）</label>
                                            <select value={editorState.yField} onChange={(e) => updateField('yField', e.target.value)} className="h-10 w-full rounded-lg border border-gray-200 bg-white px-3 text-sm outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-100">
                                                {fieldMeta.filter((field) => field.type === 'quantitative').map((field) => <option key={field.key} value={field.key}>{field.key}</option>)}
                                            </select>
                                        </div>
                                    </div>

                                    <div className="grid grid-cols-2 gap-3">
                                        <div className="space-y-1.5">
                                            <label className="text-sm font-medium text-gray-800">颜色（分组）</label>
                                            <select value={editorState.colorField} onChange={(e) => updateField('colorField', e.target.value)} className="h-10 w-full rounded-lg border border-gray-200 bg-white px-3 text-sm outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-100">
                                                <option value="">（无）</option>
                                                {fieldMeta.filter((field) => field.key !== editorState.yField).map((field) => <option key={field.key} value={field.key}>{field.key}</option>)}
                                            </select>
                                        </div>
                                        <div className="space-y-1.5">
                                            <label className="text-sm font-medium text-gray-800">聚合方式</label>
                                            <select value={editorState.aggregation} onChange={(e) => updateField('aggregation', e.target.value)} className="h-10 w-full rounded-lg border border-gray-200 bg-white px-3 text-sm outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-100">
                                                {AGGREGATIONS.map((item) => <option key={item.key} value={item.key}>{item.label}</option>)}
                                            </select>
                                        </div>
                                    </div>

                                    <div className="grid grid-cols-2 gap-3">
                                        <div className="space-y-1.5">
                                            <label className="text-sm font-medium text-gray-800">排序</label>
                                            <div className="flex gap-2">
                                                <SegmentButton active={editorState.sortMode === 'none'} onClick={() => updateField('sortMode', 'none')}>默认</SegmentButton>
                                                <SegmentButton active={editorState.sortMode === 'asc'} onClick={() => updateField('sortMode', 'asc')}>升序</SegmentButton>
                                                <SegmentButton active={editorState.sortMode === 'desc'} onClick={() => updateField('sortMode', 'desc')}>降序</SegmentButton>
                                            </div>
                                        </div>
                                        <div className="space-y-1.5">
                                            <label className="text-sm font-medium text-gray-800">堆叠方式</label>
                                            <div className="flex gap-2">
                                                <SegmentButton active={editorState.stackMode === 'group'} onClick={() => updateField('stackMode', 'group')}>并列</SegmentButton>
                                                <SegmentButton active={editorState.stackMode === 'stack'} onClick={() => updateField('stackMode', 'stack')}>堆叠</SegmentButton>
                                                <SegmentButton active={editorState.stackMode === 'percent'} onClick={() => updateField('stackMode', 'percent')}>百分比</SegmentButton>
                                            </div>
                                        </div>
                                    </div>

                                    <div className="space-y-3 rounded-xl border border-gray-200 p-4">
                                        <div className="flex items-center justify-between"><span className="text-sm font-medium text-gray-800">图例</span><SmallToggle checked={editorState.showLegend} onChange={(value) => updateField('showLegend', value)} /></div>
                                        <div className="flex items-center justify-between"><span className="text-sm font-medium text-gray-800">数据标签</span><SmallToggle checked={editorState.showLabels} onChange={(value) => updateField('showLabels', value)} /></div>
                                        <div className="flex items-center justify-between"><span className="text-sm font-medium text-gray-800">坐标轴</span><SmallToggle checked={editorState.showAxes} onChange={(value) => updateField('showAxes', value)} /></div>
                                        <div className="flex items-center justify-between"><span className="text-sm font-medium text-gray-800">网格线</span><SmallToggle checked={editorState.showGrid} onChange={(value) => updateField('showGrid', value)} /></div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>,
                document.body
            )}
        </>
    );
};

export default ChartCard;
