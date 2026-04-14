/// <reference types="../../node_modules/.vue-global-types/vue_3.5_0_0_0.d.ts" />
import { computed } from 'vue';
import { use } from 'echarts/core';
import { CanvasRenderer } from 'echarts/renderers';
import { LineChart } from 'echarts/charts';
import { GridComponent, TooltipComponent, LegendComponent, } from 'echarts/components';
import VChart from 'vue-echarts';
use([CanvasRenderer, LineChart, GridComponent, TooltipComponent, LegendComponent]);
const props = defineProps();
const SERIES_COLORS = {
    median: '#1d4e89',
    avg: '#2f7ed8',
    min: '#2f9e44',
    max: '#7b5fc9',
};
function formatPriceTick(val) {
    return val >= 10000 ? `${(val / 10000).toFixed(1)}万` : Math.round(val).toLocaleString();
}
function toTimestamp(dateStr) {
    return new Date(`${dateStr}T00:00:00`).getTime();
}
const chartOption = computed(() => {
    const timestamps = props.trend.map((p) => toTimestamp(p.date));
    const medians = props.trend.map((p, idx) => [timestamps[idx], p.median_price]);
    const avgs = props.trend.map((p, idx) => [timestamps[idx], p.avg_price]);
    const mins = props.trend.map((p, idx) => [timestamps[idx], p.min_price]);
    const maxs = props.trend.map((p, idx) => [timestamps[idx], p.max_price]);
    const allPrices = props.trend.flatMap((point) => [point.min_price, point.max_price, point.median_price, point.avg_price]);
    const rawMin = allPrices.length ? Math.min(...allPrices) : 0;
    const rawMax = allPrices.length ? Math.max(...allPrices) : 0;
    const samePrice = rawMin === rawMax;
    const padding = samePrice ? Math.max(rawMin * 0.05, 1) : (rawMax - rawMin) * 0.12;
    const yMinBase = Math.max(0, rawMin - padding);
    const yMaxBase = rawMax + padding;
    const yMin = yMinBase >= 1000 ? Math.floor(yMinBase / 50) * 50 : Math.floor(yMinBase);
    const yMax = yMaxBase >= 1000 ? Math.ceil(yMaxBase / 50) * 50 : Math.ceil(yMaxBase);
    const onePoint = timestamps.length === 1;
    const xMin = onePoint ? timestamps[0] - 12 * 60 * 60 * 1000 : 'dataMin';
    const xMax = onePoint ? timestamps[0] + 12 * 60 * 60 * 1000 : 'dataMax';
    return {
        color: [SERIES_COLORS.median, SERIES_COLORS.avg, SERIES_COLORS.min, SERIES_COLORS.max],
        animationDuration: 380,
        tooltip: {
            trigger: 'axis',
            axisPointer: {
                type: 'cross',
                lineStyle: {
                    type: 'dashed',
                    color: '#7f8a99',
                },
            },
            backgroundColor: 'rgba(255, 255, 255, 0.98)',
            borderColor: '#c1c8d1',
            borderWidth: 1,
            textStyle: { color: '#1f2937' },
            formatter: (params) => {
                if (!params.length)
                    return '';
                const dataIndex = params[0].dataIndex;
                const point = props.trend[dataIndex];
                if (!point)
                    return '';
                const levelMap = { low: '低位', normal: '正常', high: '偏高' };
                return [
                    `<b>${point.date}</b>`,
                    `中位价：¥${Math.round(point.median_price).toLocaleString()}`,
                    `均价：¥${Math.round(point.avg_price).toLocaleString()}`,
                    `区间：¥${Math.round(point.min_price).toLocaleString()} ~ ¥${Math.round(point.max_price).toLocaleString()}`,
                    `样本：${point.sample_count} 件`,
                    `行情：${levelMap[point.price_level] ?? point.price_level}`,
                ].join('<br/>');
            },
        },
        legend: {
            data: ['中位价', '均价', '最低价', '最高价'],
            bottom: 0,
            itemWidth: 14,
            itemHeight: 8,
            textStyle: {
                color: '#536170',
                fontWeight: 600,
            },
        },
        grid: {
            top: 18,
            left: '7%',
            right: '3%',
            bottom: 42,
            containLabel: true,
        },
        xAxis: {
            type: 'time',
            min: xMin,
            max: xMax,
            axisLine: { lineStyle: { color: '#c1c8d1' } },
            axisTick: { show: false },
            splitLine: { show: false },
            axisLabel: {
                color: '#536170',
                fontSize: 11,
                hideOverlap: true,
                formatter: (value) => {
                    const d = new Date(value);
                    return `${d.getMonth() + 1}-${d.getDate()}`;
                },
            },
        },
        yAxis: {
            type: 'value',
            min: yMin,
            max: yMax,
            splitNumber: 5,
            axisLine: { show: false },
            axisTick: { show: false },
            splitLine: {
                lineStyle: {
                    color: 'rgba(127, 138, 153, 0.22)',
                    type: 'dashed',
                },
            },
            axisLabel: {
                formatter: formatPriceTick,
                color: '#536170',
                fontSize: 11,
            },
        },
        series: [
            {
                name: '中位价',
                type: 'line',
                data: medians,
                smooth: false,
                lineStyle: { width: 3.2 },
                areaStyle: { color: 'rgba(29, 78, 137, 0.1)' },
                showSymbol: false,
                emphasis: { focus: 'series' },
                z: 4,
            },
            {
                name: '均价',
                type: 'line',
                data: avgs,
                smooth: false,
                lineStyle: { width: 2.4, type: 'dashed' },
                showSymbol: false,
                emphasis: { focus: 'series' },
                z: 3,
            },
            {
                name: '最低价',
                type: 'line',
                data: mins,
                smooth: false,
                lineStyle: { width: 1.5, type: 'dotted' },
                showSymbol: false,
                emphasis: { focus: 'series' },
                z: 2,
            },
            {
                name: '最高价',
                type: 'line',
                data: maxs,
                smooth: false,
                lineStyle: { width: 1.7, type: 'dashdot' },
                showSymbol: false,
                emphasis: { focus: 'series' },
                z: 1,
            },
        ],
    };
});
debugger; /* PartiallyEnd: #3632/scriptSetup.vue */
const __VLS_ctx = {};
let __VLS_components;
let __VLS_directives;
const __VLS_0 = {}.VChart;
/** @type {[typeof __VLS_components.VChart, typeof __VLS_components.vChart, ]} */ ;
// @ts-ignore
const __VLS_1 = __VLS_asFunctionalComponent(__VLS_0, new __VLS_0({
    option: (__VLS_ctx.chartOption),
    ...{ style: {} },
    autoresize: true,
}));
const __VLS_2 = __VLS_1({
    option: (__VLS_ctx.chartOption),
    ...{ style: {} },
    autoresize: true,
}, ...__VLS_functionalComponentArgsRest(__VLS_1));
var __VLS_4 = {};
var __VLS_3;
var __VLS_dollars;
const __VLS_self = (await import('vue')).defineComponent({
    setup() {
        return {
            VChart: VChart,
            chartOption: chartOption,
        };
    },
    __typeProps: {},
});
export default (await import('vue')).defineComponent({
    setup() {
        return {};
    },
    __typeProps: {},
});
; /* PartiallyEnd: #4569/main.vue */
