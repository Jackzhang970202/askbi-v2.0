/**
 * 蓝绿商务简约风 - 月度考勤分析报告
 * 数据源：PERSONAL_DATA（个人维度）+ DEPT_DATA（部门维度）
 * 规则：所有百分比/率保留两位小数
 *
 * 📅 2026.03.25 更新：
 * - 图表1: 堆叠柱状图（平日贡献+休息日贡献）
 * - 图表2: 环形图+指示线（贡献时长分布）
 * - 图表3: 纵向柱状图（职能部门公休日打卡率）
 * - 图表4: 折线图（下班后打卡率）
 * - 图表5: 纵向柱状图（销售部门出差率）
 * - 支持过滤"总经理室"和"销售/营销"部门
 */
(function() {
    'use strict';

    const COLORS = {
        primary: '#0d9488',
        light: '#14b8a6',
        accent: '#f59e0b',
        danger: '#dc2626',
        cyan: '#06b6d4',
        blue: '#3b82f6',
        purple: '#8b5cf6',
        palette: ['#0d9488', '#14b8a6', '#06b6d4', '#0ea5e9', '#3b82f6', '#8b5cf6', '#a855f7', '#d946ef', '#ec4899', '#f43f5e']
    };

    // 职能部门列表（用于公休打卡率）
    const FUNCTION_DEPTS = [
        '市场业务部',
        '运营与采购管理部',
        '科技创新部',
        '法务合规与投资部',
        '财务部',
        '人力资源部',
        '综合办公室(安全管理部)',
        '纪检部'
    ];

    // 原有的8个事业部（用于公休打卡率和出差率）
    const TARGET_DEPTS = [
        '宏观经济数据事业部',
        '模数工坊事业部',
        '浪潮(青岛)数据要素有限公司',
        '天元大数据信用管理有限公司',
        '政务数据服务事业本部',
        '山东浪潮智慧医疗科技有限公司',
        '浪潮卓数（北京）大数据技术有限公司',
        '北方健康医疗大数据科技有限公司'
    ];

    // 部门简称映射（用于图表显示）
    const DEPT_SHORT_NAME = {
        '浪潮(青岛)数据要素有限公司': '青岛数据要素公司',
        '天元大数据信用管理有限公司': '天元征信公司',
        '山东浪潮智慧医疗科技有限公司': '智慧医疗公司',
        '浪潮卓数（北京）大数据技术有限公司': '卓数北京公司',
        '北方健康医疗大数据科技有限公司': '北方健康公司'
    };

    // 不参与图表显示的公司（但KPI仍包含）
    const EXCLUDE_FROM_CHARTS = [
        '浪潮（山东）信息技术咨询服务有限公司'
    ];

    // 获取部门显示名称（用简称）
    function getDeptDisplayName(deptName) {
        return DEPT_SHORT_NAME[deptName] || deptName;
    }

    // 销售部门列表（用于出差率）
    const SALES_DEPTS = [
        '营销南区',
        '营销北区',
        '医疗健康营销部',
        '总部中心'
    ];

    // 过滤状态
    const filterState = {
        excludeZJL: true,       // 排除总经理室（默认启用）
        excludeSales: false     // 排除销售部门（仅特定图表使用）
    };

    // 销售部门列表（用于特定图表排除）
    const SALES_DEPTS_FILTER = [
        '营销南区',
        '营销北区',
        '总部中心',
        '医疗健康营销部'
    ];

    // 判断是否是销售部门（用于特定图表过滤）
    function isSalesDept(deptName) {
        if (!deptName) return false;
        return SALES_DEPTS_FILTER.some(sales => deptName.includes(sales) || sales.includes(deptName));
    }

    const personalData = typeof PERSONAL_DATA !== 'undefined' ? PERSONAL_DATA : [];
    const deptData = typeof DEPT_DATA !== 'undefined' ? DEPT_DATA : [];

    // 过滤部门数据：排除"合计"行
    const deptRows = deptData.filter(d => d.dept2 && d.dept2 !== '合计' && d.dept2 !== '');
    // 一级部门合计行
    const dept1Totals = deptData.filter(d => d.dept2 === '合计');

    const avg = arr => arr.length ? arr.reduce((s, v) => s + v, 0) / arr.length : 0;
    const sum = arr => arr.reduce((s, v) => s + v, 0);
    const groupBy = (data, key) => {
        const map = {};
        data.forEach(d => { if (d[key]) { if (!map[d[key]]) map[d[key]] = []; map[d[key]].push(d); } });
        return map;
    };

    const fmtPct = (val) => val.toFixed(2);

    // X轴标签自动换行：每5个字符换一行
    const wrapLabel = (text, maxLen) => {
        maxLen = maxLen || 5;
        if (!text || text.length <= maxLen) return text;
        return text.match(new RegExp('.{1,' + maxLen + '}', 'g')).join('\n');
    };

    // Y轴最大值计算：留出20%余量给顶部标签
    const yMaxWithPadding = (value) => Math.ceil(value.max * 1.2) || 1;

    // 判断部门是否应该被过滤
    function shouldFilterDept(deptName) {
        if (!deptName) return false;
        // 检查是否是总经理室
        if (filterState.excludeZJL && deptName.includes('总经理室')) {
            return true;
        }
        // 检查是否是销售/营销部门（同时匹配"销售"和"营销"）
        if (filterState.excludeSales && (deptName.includes('销售') || deptName.includes('营销'))) {
            return true;
        }
        return false;
    }

    // 判断是否应该从图表中排除（不影响KPI）
    function shouldExcludeFromChart(deptName) {
        if (!deptName) return false;
        return EXCLUDE_FROM_CHARTS.some(excluded => deptName.includes(excluded) || excluded.includes(deptName));
    }

    // 判断是否是三期人员（需要排除）
    function isSanqiPerson(person) {
        const sanqiType = person.sanqiType || '';
        // 三期人员标识：值为"三期"或包含"三期"（如"三期/病假"）
        return sanqiType.includes('三期');
    }

    // 获取过滤后的一级部门合计数据
    function getFilteredDept1Totals() {
        return dept1Totals.filter(d => !shouldFilterDept(d.dept1));
    }

    // 获取过滤后的二级部门数据
    function getFilteredDeptRows() {
        return deptRows.filter(d => !shouldFilterDept(d.dept1));
    }

    // 获取过滤后的个人数据（排除三期人员）
    function getFilteredPersonalData() {
        return personalData.filter(d => !shouldFilterDept(d.dept1) && !isSanqiPerson(d));
    }

    // 获取计入部门的个人数据（用于下班一小时后打卡率，排除三期人员）
    function getIncludedPersonalData() {
        return personalData.filter(d => !shouldFilterDept(d.dept1) && d.countInDept === '是' && !isSanqiPerson(d));
    }

    // 获取过滤后的个人数据（额外排除销售部门，用于chart1、chart2、chart4）
    function getFilteredPersonalDataExcludeSales() {
        return personalData.filter(d => !shouldFilterDept(d.dept1) && !isSalesDept(d.dept1) && !isSanqiPerson(d));
    }

    // 获取计入部门的个人数据（额外排除销售部门，用于chart4）
    function getIncludedPersonalDataExcludeSales() {
        return personalData.filter(d => !shouldFilterDept(d.dept1) && !isSalesDept(d.dept1) && d.countInDept === '是' && !isSanqiPerson(d));
    }

    // 获取过滤后的部门数据（额外排除销售部门）
    function getFilteredDept1TotalsExcludeSales() {
        return dept1Totals.filter(d => !shouldFilterDept(d.dept1) && !isSalesDept(d.dept1) && !shouldExcludeFromChart(d.dept1));
    }

    function getFilteredDeptRowsExcludeSales() {
        return deptRows.filter(d => !shouldFilterDept(d.dept1) && !isSalesDept(d.dept1) && !shouldExcludeFromChart(d.dept1));
    }

    const charts = {};

    // 暴露给外部（截图用）
    window.getCharts = function() { return Object.values(charts); };

    function init() {
        initTime();
        initKPIs();
        initCharts();
        window.addEventListener('resize', resizeCharts);
    }

    // 刷新所有图表
    function refreshAllCharts() {
        initKPIs();
        chart1();
        chart2();
        chart3();
        chart4();
        chart5();
    }

    function initTime() {
        const tick = () => {
            const now = new Date();
            const pad = n => String(n).padStart(2, '0');
            document.getElementById('liveTime').textContent = `${pad(now.getHours())}:${pad(now.getMinutes())}:${pad(now.getSeconds())}`;
            const week = ['日', '一', '二', '三', '四', '五', '六'];
            document.getElementById('liveDate').textContent = `${now.getFullYear()}年${now.getMonth()+1}月${now.getDate()}日 周${week[now.getDay()]}`;
        };
        tick();
        setInterval(tick, 1000);
    }

    function animateNum(id, target, dec, hasUnit) {
        const el = document.getElementById(id);
        if (!el) return;
        const dur = 1200, start = performance.now();
        const step = now => {
            const p = Math.min((now - start) / dur, 1);
            const ease = 1 - Math.pow(1 - p, 3);
            const val = (target * ease).toFixed(dec);
            if (hasUnit) {
                el.innerHTML = val + '<span class="unit">' + hasUnit + '</span>';
            } else {
                el.textContent = val;
            }
            if (p < 1) requestAnimationFrame(step);
        };
        requestAnimationFrame(step);
    }

    function initKPIs() {
        // 使用过滤后的数据（排除总经理室、销售部门、三期人员）
        const filteredPersonal = getFilteredPersonalDataExcludeSales();
        const includedPersonal = getIncludedPersonalDataExcludeSales();  // 计入部门的人员

        // 总人数（个人维度）
        const total = filteredPersonal.length;
        // 人均贡献时长（个人维度）
        const avgContrib = avg(filteredPersonal.map(d => d.totalContrib || 0));
        // 平均出差率（个人维度）
        const avgBizTrip = avg(filteredPersonal.map(d => d.bizTripRate || 0));
        // 下班一小时后打卡率（只计算计入部门的人员，上限100%）
        const avgAfterWork = Math.min(avg(includedPersonal.map(d => d.afterWorkRate || 0)), 100);
        // 公休日打卡率（上限100%）
        const avgWeekend = Math.min(avg(filteredPersonal.map(d => d.weekendRate || 0)), 100);

        animateNum('kpiTotal', total, 0);
        animateNum('kpiContrib', avgContrib, 2, 'h');
        animateNum('kpiBizTrip', avgBizTrip, 2, '%');
        animateNum('kpiAfterWork', avgAfterWork, 2, '%');
        animateNum('kpiWeekend', avgWeekend, 2, '%');
    }

    function initCharts() {
        chart1();
        chart2();
        chart3();
        chart4();
        chart5();
    }

    function resizeCharts() {
        Object.values(charts).forEach(c => c && c.resize());
    }

    function createChart(id) {
        const el = document.getElementById(id);
        if (!el) return null;
        if (charts[id]) charts[id].dispose();
        charts[id] = echarts.init(el);
        return charts[id];
    }

    // 图表1：部门贡献时长对比 - 堆叠柱状图（人均平日贡献+人均休息日贡献）
    function chart1() {
        // 使用过滤后的个人数据（排除总经理室、销售部门、三期人员）
        const filteredPersonal = getFilteredPersonalDataExcludeSales();

        // 按一级部门统计人均平日贡献和人均休息日贡献
        // 排除总经理室和销售部门，保留其他所有一级部门
        const groups = groupBy(filteredPersonal, 'dept1');
        const stats = Object.entries(groups)
            .filter(([dept]) => dept && !dept.includes('总经理室') && !isSalesDept(dept) && !shouldExcludeFromChart(dept) && groups[dept].length > 0)
            .map(([dept, arr]) => {
                const normalContrib = avg(arr.map(d => d.normalContrib || 0));
                const weekendContrib = avg(arr.map(d => d.weekendContrib || 0));
                const holidayContrib = avg(arr.map(d => d.holidayContrib || 0));
                return {
                    name: getDeptDisplayName(dept),
                    fullName: dept,
                    normalContrib: normalContrib,
                    weekendContrib: weekendContrib,
                    holidayContrib: holidayContrib,
                    totalContrib: normalContrib + weekendContrib + holidayContrib,
                    count: arr.length
                };
            })
            .sort((a, b) => b.totalContrib - a.totalContrib);

        const chart = createChart('chart1');
        chart.setOption({
            tooltip: {
                trigger: 'axis',
                axisPointer: { type: 'shadow' },
                formatter: params => {
                    const d = stats[params[0].dataIndex];
                    return `<b>${d.fullName}</b><br/>人数: ${d.count}人<br/>人均平日贡献: ${d.normalContrib.toFixed(1)}h<br/>人均休息日贡献: ${d.weekendContrib.toFixed(1)}h<br/>人均总贡献: ${d.totalContrib.toFixed(1)}h`;
                }
            },
            legend: {
                data: ['人均平日贡献', '人均休息日贡献', '人均总贡献'],
                top: 5,
                textStyle: { fontSize: 10, color: '#64748b' }
            },
            grid: { left: 55, right: 25, top: 35, bottom: 70 },
            xAxis: {
                type: 'category',
                data: stats.map(s => s.name),
                axisLabel: {
                    interval: 0,
                    fontSize: 10,
                    color: '#64748b',
                    formatter: function(val) { return wrapLabel(val, 6); },
                    lineHeight: 14
                },
                axisLine: { lineStyle: { color: '#e2e8f0' } }
            },
            yAxis: {
                type: 'value',
                name: '贡献时长(h)',
                nameTextStyle: { fontSize: 10, color: '#94a3b8' },
                axisLabel: { fontSize: 10, color: '#94a3b8' },
                splitLine: { lineStyle: { color: '#f1f5f9' } }
            },
            series: [
                {
                    name: '人均平日贡献',
                    type: 'bar',
                    stack: 'total',
                    data: stats.map(s => +s.normalContrib.toFixed(1)),
                    itemStyle: {
                        color: COLORS.primary,
                        borderRadius: [0, 0, 0, 0]
                    },
                    barMaxWidth: 35,
                    label: {
                        show: true,
                        position: 'inside',
                        fontSize: 9,
                        color: '#fff',
                        formatter: p => p.value > 10 ? p.value : ''
                    },
                    animationDelay: (idx) => idx * 50
                },
                {
                    name: '人均休息日贡献',
                    type: 'bar',
                    stack: 'total',
                    data: stats.map(s => {
                        const val = +s.weekendContrib.toFixed(1);
                        const isSmall = val > 0 && val < 3;
                        return {
                            value: val,
                            label: {
                                show: val > 0,
                                position: isSmall ? 'top' : 'inside',
                                fontSize: isSmall ? 8 : 9,
                                color: isSmall ? COLORS.accent : '#fff',
                                fontWeight: isSmall ? 'bold' : 'normal',
                                distance: isSmall ? 2 : 0,
                                formatter: p => p.value > 0 ? p.value : ''
                            }
                        };
                    }),
                    itemStyle: {
                        color: COLORS.accent,
                        borderRadius: [4, 4, 0, 0]
                    },
                    animationDelay: (idx) => idx * 50 + 25
                },
                {
                    name: '人均总贡献',
                    type: 'line',
                    symbol: 'circle',
                    symbolSize: 8,
                    lineStyle: { color: COLORS.purple, width: 2, type: 'dashed' },
                    itemStyle: { color: COLORS.purple },
                    data: stats.map(s => {
                        const val = +s.totalContrib.toFixed(1);
                        const weekendVal = +s.weekendContrib.toFixed(1);
                        const hasSmall = weekendVal > 0 && weekendVal < 3;
                        return {
                            value: val,
                            label: {
                                show: true,
                                position: 'top',
                                distance: hasSmall ? 18 : 5,
                                fontSize: 11,
                                fontWeight: 'bold',
                                color: COLORS.purple,
                                formatter: p => p.value + 'h'
                            }
                        };
                    }),
                    animationDelay: (idx) => idx * 50 + 100
                }
            ],
            animationEasing: 'elasticOut'
        });
    }

    // 图表2：贡献时长分布 - 环形图带指示线
    function chart2() {
        // 使用过滤后的个人数据（排除总经理室、销售部门、三期人员）
        const filteredPersonal = getFilteredPersonalDataExcludeSales();

        const bins = [[0, 20], [20, 40], [40, 60], [60, 80], [80, 100], [100, Infinity]];
        const labels = ['0-20h', '20-40h', '40-60h', '60-80h', '80-100h', '100h+'];
        const counts = bins.map(([min, max]) =>
            filteredPersonal.filter(d => (d.totalContrib || 0) >= min && (d.totalContrib || 0) < max).length
        );

        const total = filteredPersonal.length;
        const maxIdx = counts.indexOf(Math.max(...counts));

        const chart = createChart('chart2');
        chart.setOption({
            tooltip: {
                trigger: 'item',
                formatter: params => `${params.name}<br/>人数: ${params.value}人<br/>占比: ${params.percent.toFixed(1)}%`
            },
            legend: {
                orient: 'vertical',
                right: 5,
                top: 'center',
                textStyle: { fontSize: 9, color: '#64748b' },
                itemWidth: 10,
                itemHeight: 10,
                formatter: name => {
                    const idx = labels.indexOf(name);
                    return `${name}: ${counts[idx]}人`;
                }
            },
            series: [{
                type: 'pie',
                radius: ['40%', '65%'],
                center: ['38%', '50%'],
                avoidLabelOverlap: true,
                itemStyle: {
                    borderRadius: 4,
                    borderColor: '#fff',
                    borderWidth: 2
                },
                label: {
                    show: true,
                    position: 'outside',
                    fontSize: 9,
                    color: '#64748b',
                    formatter: params => `${params.name}\n${params.value}人(${params.percent.toFixed(1)}%)`,
                    lineHeight: 12
                },
                labelLine: {
                    show: true,
                    length: 10,
                    length2: 8
                },
                emphasis: {
                    label: {
                        show: true,
                        fontSize: 11,
                        fontWeight: 'bold'
                    }
                },
                data: labels.map((label, i) => ({
                    value: counts[i],
                    name: label,
                    itemStyle: {
                        color: i === maxIdx ? COLORS.accent : COLORS.palette[i]
                    }
                })),
                animationType: 'scale',
                animationEasing: 'elasticOut'
            }],
            // 中心文字 - 圆环中心在 center: ['38%', '50%']
            graphic: [{
                type: 'group',
                left: '38%',
                top: '50%',
                bounding: 'raw',  // 以group中心点定位
                children: [{
                    type: 'text',
                    top: -14,  // 数字在中心上方
                    style: {
                        text: String(total),
                        fontSize: 22,
                        fontWeight: 'bold',
                        fill: COLORS.primary,
                        textAlign: 'center',
                        textBaseline: 'bottom'
                    }
                }, {
                    type: 'text',
                    top: 8,  // "总人数"在数字下方
                    style: {
                        text: '总人数',
                        fontSize: 10,
                        fill: '#94a3b8',
                        textAlign: 'center',
                        textBaseline: 'top'
                    }
                }]
            }]
        });
    }

    // 图表3：公休日打卡率 - 纵向柱状图（原8个事业部 + 8个职能部门）
    function chart3() {
        // 使用过滤后的一级部门合计数据
        const filteredDept1Totals = getFilteredDept1Totals();
        const filteredDeptRows = getFilteredDeptRows();

        let targetStats = [];  // 事业部数据
        let functionStats = [];  // 职能部门数据

        if (filteredDept1Totals.length > 0) {
            TARGET_DEPTS.filter(dept => !shouldFilterDept(dept) && !shouldExcludeFromChart(dept)).forEach(dept => {
                const d = filteredDept1Totals.find(item => item.dept1 === dept);
                if (d && d.headcount > 0) {
                    targetStats.push({
                        name: getDeptDisplayName(dept),
                        fullName: dept,
                        weekendRate: d.weekendRate || 0,
                        headcount: d.headcount || 0,
                        isTarget: true
                    });
                }
            });
            FUNCTION_DEPTS.filter(dept => !shouldFilterDept(dept)).forEach(dept => {
                const d = filteredDept1Totals.find(item => item.dept1 === dept);
                if (d && d.headcount > 0) {
                    functionStats.push({
                        name: dept,
                        fullName: dept,
                        weekendRate: d.weekendRate || 0,
                        headcount: d.headcount || 0,
                        isTarget: false
                    });
                }
            });
        } else {
            const groups = groupBy(filteredDeptRows, 'dept1');
            TARGET_DEPTS.filter(dept => !shouldFilterDept(dept) && !shouldExcludeFromChart(dept) && groups[dept]).forEach(dept => {
                const arr = groups[dept] || [];
                if (arr.length > 0) {
                    targetStats.push({
                        name: getDeptDisplayName(dept),
                        fullName: dept,
                        weekendRate: avg(arr.map(d => d.weekendRate || 0)),
                        headcount: sum(arr.map(d => d.headcount || 0)),
                        isTarget: true
                    });
                }
            });
            FUNCTION_DEPTS.filter(dept => !shouldFilterDept(dept) && groups[dept]).forEach(dept => {
                const arr = groups[dept] || [];
                if (arr.length > 0) {
                    functionStats.push({
                        name: dept,
                        fullName: dept,
                        weekendRate: avg(arr.map(d => d.weekendRate || 0)),
                        headcount: sum(arr.map(d => d.headcount || 0)),
                        isTarget: false
                    });
                }
            });
        }

        // 各自按从高到低排序
        targetStats.sort((a, b) => b.weekendRate - a.weekendRate);
        functionStats.sort((a, b) => b.weekendRate - a.weekendRate);

        // 合并数据：先事业部，再职能部门
        const stats = [...targetStats, ...functionStats];

        const chart = createChart('chart3');
        chart.setOption({
            tooltip: {
                trigger: 'axis',
                axisPointer: { type: 'shadow' },
                formatter: params => {
                    const d = stats[params[0].dataIndex];
                    return `<b>${d.fullName}</b><br/>公休日打卡率: ${fmtPct(d.weekendRate)}%<br/>部门人数: ${d.headcount}人`;
                }
            },
            legend: {
                data: [
                    { name: '事业部', itemStyle: { color: COLORS.blue } },
                    { name: '职能部门', itemStyle: { color: COLORS.cyan } }
                ],
                top: 5,
                textStyle: { fontSize: 10, color: '#64748b' }
            },
            grid: { left: 50, right: 20, top: 35, bottom: 100 },
            xAxis: {
                type: 'category',
                data: stats.map(s => s.name),
                axisLabel: {
                    interval: 0,
                    fontSize: 9,
                    color: '#64748b',
                    formatter: function(val) { return wrapLabel(val, 6); },
                    lineHeight: 13
                },
                axisLine: { lineStyle: { color: '#e2e8f0' } }
            },
            yAxis: {
                type: 'value',
                name: '%',
                nameTextStyle: { fontSize: 10, color: '#94a3b8' },
                axisLabel: { fontSize: 10, color: '#94a3b8' },
                splitLine: { lineStyle: { color: '#f1f5f9' } }
            },
            series: [
                {
                    name: '事业部',
                    type: 'bar',
                    data: stats.map(s => s.isTarget ? +s.weekendRate.toFixed(2) : '-'),
                    barMaxWidth: 24,
                    barCategoryGap: '40%',
                    itemStyle: { color: COLORS.blue, borderRadius: [4, 4, 0, 0] },
                    label: {
                        show: true,
                        position: 'top',
                        formatter: p => p.value !== '-' ? `${p.value}%` : '',
                        fontSize: 9,
                        color: '#64748b'
                    },
                    animationDelay: (idx) => idx * 40
                },
                {
                    name: '职能部门',
                    type: 'bar',
                    data: stats.map(s => !s.isTarget ? +s.weekendRate.toFixed(2) : '-'),
                    barMaxWidth: 24,
                    barGap: '-100%',
                    itemStyle: { color: COLORS.cyan, borderRadius: [4, 4, 0, 0] },
                    label: {
                        show: true,
                        position: 'top',
                        formatter: p => p.value !== '-' ? `${p.value}%` : '',
                        fontSize: 9,
                        color: '#64748b'
                    },
                    animationDelay: (idx) => idx * 40
                }
            ],
            animationEasing: 'elasticOut'
        });
    }

    // 图表4：下班一小时后打卡率 - 折线图（一级部门维度，排除销售部门）
    function chart4() {
        // 使用过滤后的一级部门合计数据（排除总经理室、销售部门）
        const filteredDept1Totals = getFilteredDept1TotalsExcludeSales();
        const filteredDeptRows = getFilteredDeptRowsExcludeSales();
        let stats;
        if (filteredDept1Totals.length > 0) {
            stats = filteredDept1Totals
                .filter(d => d.dept1 && !shouldFilterDept(d.dept1) && !isSalesDept(d.dept1) && !shouldExcludeFromChart(d.dept1))
                .map(d => ({
                    name: getDeptDisplayName(d.dept1),
                    afterWorkRate: Math.min(d.afterWorkRate || 0, 100),
                    headcount: d.headcount || 0
                }))
                .sort((a, b) => b.afterWorkRate - a.afterWorkRate)
                .slice(0, 12);
        } else {
            // fallback: 按一级部门分组计算
            const groups = groupBy(filteredDeptRows, 'dept1');
            stats = Object.entries(groups)
                .filter(([dept]) => !shouldFilterDept(dept) && !isSalesDept(dept) && !shouldExcludeFromChart(dept))
                .map(([dept, arr]) => ({
                    name: getDeptDisplayName(dept),
                    afterWorkRate: Math.min(avg(arr.map(d => d.afterWorkRate || 0)), 100),
                    headcount: sum(arr.map(d => d.headcount || 0))
                }))
                .sort((a, b) => b.afterWorkRate - a.afterWorkRate)
                .slice(0, 12);
        }

        const chart = createChart('chart4');
        chart.setOption({
            tooltip: {
                trigger: 'axis',
                formatter: params => {
                    const d = stats[params[0].dataIndex];
                    return `<b>${d.name}</b><br/>下班1h后打卡率: ${fmtPct(d.afterWorkRate)}%<br/>部门人数: ${d.headcount}人`;
                }
            },
            grid: { left: 50, right: 40, top: 25, bottom: 70 },
            xAxis: {
                type: 'category',
                data: stats.map(s => s.name),
                axisLabel: {
                    interval: 0,
                    fontSize: 9,
                    color: '#64748b',
                    formatter: function(val) { return wrapLabel(val, 6); },
                    lineHeight: 13
                },
                axisLine: { lineStyle: { color: '#e2e8f0' } },
                boundaryGap: false
            },
            yAxis: {
                type: 'value',
                name: '打卡率(%)',
                max: 100,
                nameTextStyle: { fontSize: 10, color: '#94a3b8' },
                axisLabel: { fontSize: 10, color: '#94a3b8' },
                splitLine: { lineStyle: { color: '#f1f5f9' } }
            },
            series: [{
                type: 'line',
                data: stats.map(s => +s.afterWorkRate.toFixed(2)),
                symbol: 'circle',
                symbolSize: 8,
                lineStyle: {
                    color: COLORS.primary,
                    width: 3
                },
                itemStyle: {
                    color: params => {
                        const val = params.value;
                        return val > 50 ? COLORS.accent : val > 30 ? COLORS.cyan : COLORS.primary;
                    },
                    borderWidth: 2,
                    borderColor: '#fff'
                },
                areaStyle: {
                    color: {
                        type: 'linear',
                        x: 0, y: 0, x2: 0, y2: 1,
                        colorStops: [
                            { offset: 0, color: 'rgba(13, 148, 136, 0.3)' },
                            { offset: 1, color: 'rgba(13, 148, 136, 0.05)' }
                        ]
                    }
                },
                label: {
                    show: true,
                    position: 'top',
                    formatter: p => `${p.value}%`,
                    fontSize: 9,
                    color: '#64748b'
                },
                animationDelay: (idx) => idx * 50
            }],
            animationEasing: 'elasticOut'
        });
    }

    // 图表5：出差率 - 纵向柱状图（原8个事业部 + 4个销售部门）
    function chart5() {
        // 使用过滤后的一级部门数据
        const filteredDept1Totals = getFilteredDept1Totals();
        const filteredDeptRows = getFilteredDeptRows();

        let targetStats = [];  // 事业部数据
        let salesStats = [];  // 销售部门数据

        if (filteredDept1Totals.length > 0) {
            TARGET_DEPTS.filter(dept => !shouldFilterDept(dept) && !shouldExcludeFromChart(dept)).forEach(dept => {
                const d = filteredDept1Totals.find(item => item.dept1 === dept);
                if (d && d.headcount > 0) {
                    targetStats.push({
                        name: getDeptDisplayName(dept),
                        fullName: dept,
                        bizTripRate: d.bizTripRate || 0,
                        headcount: d.headcount || 0,
                        isTarget: true
                    });
                }
            });
            SALES_DEPTS.filter(dept => !shouldFilterDept(dept)).forEach(dept => {
                const d = filteredDept1Totals.find(item => item.dept1 === dept);
                if (d && d.headcount > 0) {
                    salesStats.push({
                        name: dept,
                        fullName: dept,
                        bizTripRate: d.bizTripRate || 0,
                        headcount: d.headcount || 0,
                        isTarget: false
                    });
                }
            });
        } else {
            const groups = groupBy(filteredDeptRows, 'dept1');
            TARGET_DEPTS.filter(dept => !shouldFilterDept(dept) && !shouldExcludeFromChart(dept) && groups[dept]).forEach(dept => {
                const arr = groups[dept] || [];
                if (arr.length > 0) {
                    targetStats.push({
                        name: getDeptDisplayName(dept),
                        fullName: dept,
                        bizTripRate: avg(arr.map(d => d.bizTripRate || 0)),
                        headcount: sum(arr.map(d => d.headcount || 0)),
                        isTarget: true
                    });
                }
            });
            SALES_DEPTS.filter(dept => !shouldFilterDept(dept) && groups[dept]).forEach(dept => {
                const arr = groups[dept] || [];
                if (arr.length > 0) {
                    salesStats.push({
                        name: dept,
                        fullName: dept,
                        bizTripRate: avg(arr.map(d => d.bizTripRate || 0)),
                        headcount: sum(arr.map(d => d.headcount || 0)),
                        isTarget: false
                    });
                }
            });
        }

        // 各自按从高到低排序
        targetStats.sort((a, b) => b.bizTripRate - a.bizTripRate);
        salesStats.sort((a, b) => b.bizTripRate - a.bizTripRate);

        // 合并数据：先事业部，再销售部门
        const stats = [...targetStats, ...salesStats];

        const chart = createChart('chart5');
        chart.setOption({
            tooltip: {
                trigger: 'axis',
                axisPointer: { type: 'shadow' },
                formatter: params => {
                    const d = stats[params[0].dataIndex];
                    return `<b>${d.fullName}</b><br/>出差率: ${fmtPct(d.bizTripRate)}%<br/>人数: ${d.headcount}人`;
                }
            },
            legend: {
                data: [
                    { name: '事业部', itemStyle: { color: COLORS.accent } },
                    { name: '销售部门', itemStyle: { color: COLORS.purple } }
                ],
                top: 5,
                textStyle: { fontSize: 10, color: '#64748b' }
            },
            grid: { left: 50, right: 20, top: 35, bottom: 100 },
            xAxis: {
                type: 'category',
                data: stats.map(s => s.name),
                axisLabel: {
                    interval: 0,
                    fontSize: 9,
                    color: '#64748b',
                    formatter: function(val) { return wrapLabel(val, 6); },
                    lineHeight: 13
                },
                axisLine: { lineStyle: { color: '#e2e8f0' } }
            },
            yAxis: {
                type: 'value',
                name: '%',
                nameTextStyle: { fontSize: 10, color: '#94a3b8' },
                axisLabel: { fontSize: 10, color: '#94a3b8' },
                splitLine: { lineStyle: { color: '#f1f5f9' } }
            },
            series: [
                {
                    name: '事业部',
                    type: 'bar',
                    data: stats.map(s => s.isTarget ? +s.bizTripRate.toFixed(2) : '-'),
                    barMaxWidth: 24,
                    barCategoryGap: '40%',
                    itemStyle: { color: COLORS.accent, borderRadius: [4, 4, 0, 0] },
                    label: {
                        show: true,
                        position: 'top',
                        formatter: p => p.value !== '-' ? `${p.value}%` : '',
                        fontSize: 9,
                        fontWeight: 'bold',
                        color: '#64748b'
                    },
                    animationDelay: (idx) => idx * 50
                },
                {
                    name: '销售部门',
                    type: 'bar',
                    data: stats.map(s => !s.isTarget ? +s.bizTripRate.toFixed(2) : '-'),
                    barMaxWidth: 24,
                    barGap: '-100%',
                    itemStyle: { color: COLORS.purple, borderRadius: [4, 4, 0, 0] },
                    label: {
                        show: true,
                        position: 'top',
                        formatter: p => p.value !== '-' ? `${p.value}%` : '',
                        fontSize: 9,
                        fontWeight: 'bold',
                        color: '#64748b'
                    },
                    animationDelay: (idx) => idx * 50
                }
            ],
            animationEasing: 'elasticOut'
        });
    }

    // 图表6：迟到请假情况 - 堆叠柱状图
    function chart6() {
        const groups = groupBy(personalData, 'location');
        const stats = Object.entries(groups)
            .map(([loc, arr]) => ({
                name: loc,
                count: arr.length,
                late: sum(arr.map(d => d.lateTimes || 0)),
                leave: sum(arr.map(d => d.leaveDays || 0))
            }))
            .sort((a, b) => (b.late + b.leave) - (a.late + a.leave))
            .slice(0, 8);

        const chart = createChart('chart6');
        chart.setOption({
            tooltip: {
                trigger: 'axis',
                axisPointer: { type: 'shadow' },
                formatter: params => {
                    const d = stats[params[0].dataIndex];
                    return `<b>${d.name}</b><br/>迟到总次数: ${d.late}次<br/>请假总天数: ${d.leave}天<br/>合计: ${d.late + d.leave}`;
                }
            },
            legend: {
                data: ['迟到次数', '请假天数'],
                top: 5,
                textStyle: { fontSize: 10, color: '#64748b' }
            },
            grid: { left: 50, right: 15, top: 35, bottom: 45 },
            xAxis: {
                type: 'category',
                data: stats.map(s => s.name.length > 4 ? s.name.slice(0, 4) + '..' : s.name),
                axisLabel: { rotate: 25, fontSize: 9, color: '#64748b' },
                axisLine: { lineStyle: { color: '#e2e8f0' } }
            },
            yAxis: {
                type: 'value',
                name: '次数/天数',
                max: yMaxWithPadding,
                nameTextStyle: { fontSize: 9, color: '#94a3b8' },
                axisLabel: { fontSize: 9, color: '#94a3b8' },
                splitLine: { lineStyle: { color: '#f1f5f9' } }
            },
            series: [
                {
                    name: '迟到次数',
                    type: 'bar',
                    stack: 'total',
                    data: stats.map((s, i) => ({
                        value: s.late,
                        itemStyle: {
                            color: COLORS.accent,
                            borderRadius: stats[i].leave === 0 ? [4, 4, 0, 0] : [0, 0, 0, 0]
                        }
                    })),
                    barMaxWidth: 30,
                    label: {
                        show: true,
                        position: 'inside',
                        fontSize: 8,
                        color: '#fff',
                        formatter: p => p.value > 0 ? p.value : ''
                    },
                    animationDelay: (idx) => idx * 50
                },
                {
                    name: '请假天数',
                    type: 'bar',
                    stack: 'total',
                    data: stats.map((s, i) => ({
                        value: s.leave,
                        itemStyle: {
                            color: COLORS.cyan,
                            borderRadius: [4, 4, 0, 0]
                        }
                    })),
                    label: {
                        show: true,
                        position: 'insideTop',
                        fontSize: 8,
                        color: '#fff',
                        formatter: p => p.value > 0 ? p.value : ''
                    },
                    animationDelay: (idx) => idx * 50 + 25
                }
            ],
            animationEasing: 'elasticOut'
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    // 监听来自父窗口的过滤消息
    window.addEventListener('message', function(event) {
        if (event.data && event.data.type === 'DASHBOARD_FILTER') {
            const { excludeZJL, excludeSales } = event.data;
            console.log('收到过滤消息:', { excludeZJL, excludeSales });
            filterState.excludeZJL = excludeZJL;
            filterState.excludeSales = excludeSales;
            console.log('当前过滤状态:', filterState);
            refreshAllCharts();
        }
        if (event.data && event.data.type === 'updateTitle') {
            const title = event.data.title;
            if (title) {
                const h1 = document.querySelector('.header-title h1');
                if (h1) h1.textContent = title;
                document.title = title;
            }
        }
    });

    // 页面加载完成后，通知父窗口
    window.addEventListener('load', function() {
        if (window.parent !== window) {
            window.parent.postMessage({ type: 'DASHBOARD_READY' }, '*');
        }
    });
})();