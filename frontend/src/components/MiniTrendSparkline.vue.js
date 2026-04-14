/// <reference types="../../node_modules/.vue-global-types/vue_3.5_0_0_0.d.ts" />
import { computed } from 'vue';
const props = withDefaults(defineProps(), {
    loading: false,
    level: 'normal',
    width: 180,
    height: 42,
});
const PADDING = 4;
const baselineY = props.height - PADDING;
const palette = computed(() => {
    switch (props.level) {
        case 'low':
            return {
                stroke: '#2d9b55',
            };
        case 'high':
            return {
                stroke: '#7255c7',
            };
        case 'none':
            return {
                stroke: '#94a3b8',
            };
        default:
            return {
                stroke: '#2f6fb2',
            };
    }
});
const normalized = computed(() => {
    if (!props.points.length)
        return [];
    const min = Math.min(...props.points);
    const max = Math.max(...props.points);
    const span = max - min || 1;
    const innerWidth = props.width - PADDING * 2;
    const innerHeight = props.height - PADDING * 2;
    const denominator = Math.max(props.points.length - 1, 1);
    if (props.points.length === 1) {
        return [{ x: props.width / 2, y: props.height / 2 }];
    }
    return props.points.map((value, idx) => {
        const x = PADDING + (innerWidth * idx) / denominator;
        const y = PADDING + innerHeight - ((value - min) / span) * innerHeight;
        return { x, y };
    });
});
const linePath = computed(() => {
    if (!normalized.value.length)
        return '';
    if (normalized.value.length === 1) {
        const { x, y } = normalized.value[0];
        return `M ${(x - 10).toFixed(2)} ${y.toFixed(2)} L ${(x + 10).toFixed(2)} ${y.toFixed(2)}`;
    }
    const points = normalized.value;
    let d = `M ${points[0].x.toFixed(2)} ${points[0].y.toFixed(2)}`;
    for (let i = 1; i < points.length; i += 1) {
        const prev = points[i - 1];
        const curr = points[i];
        const midX = ((prev.x + curr.x) / 2).toFixed(2);
        d += ` C ${midX} ${prev.y.toFixed(2)}, ${midX} ${curr.y.toFixed(2)}, ${curr.x.toFixed(2)} ${curr.y.toFixed(2)}`;
    }
    return d;
});
debugger; /* PartiallyEnd: #3632/scriptSetup.vue */
const __VLS_withDefaultsArg = (function (t) { return t; })({
    loading: false,
    level: 'normal',
    width: 180,
    height: 42,
});
const __VLS_ctx = {};
let __VLS_components;
let __VLS_directives;
// CSS variable injection 
// CSS variable injection end 
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "sparkline-wrap" },
});
if (__VLS_ctx.loading) {
    __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
        ...{ class: "placeholder" },
    });
}
else if (!__VLS_ctx.points.length) {
    __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
        ...{ class: "placeholder" },
    });
}
else {
    __VLS_asFunctionalElement(__VLS_intrinsicElements.svg, __VLS_intrinsicElements.svg)({
        viewBox: (`0 0 ${__VLS_ctx.width} ${__VLS_ctx.height}`),
        preserveAspectRatio: "none",
        ...{ class: "sparkline-svg" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.line)({
        ...{ class: "baseline" },
        x1: (__VLS_ctx.PADDING),
        x2: (__VLS_ctx.width - __VLS_ctx.PADDING),
        y1: (__VLS_ctx.baselineY),
        y2: (__VLS_ctx.baselineY),
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.path)({
        ...{ class: "line" },
        d: (__VLS_ctx.linePath),
        stroke: (__VLS_ctx.palette.stroke),
        fill: "none",
        'stroke-width': "1.35",
        'stroke-linecap': "round",
        'stroke-linejoin': "round",
    });
}
/** @type {__VLS_StyleScopedClasses['sparkline-wrap']} */ ;
/** @type {__VLS_StyleScopedClasses['placeholder']} */ ;
/** @type {__VLS_StyleScopedClasses['placeholder']} */ ;
/** @type {__VLS_StyleScopedClasses['sparkline-svg']} */ ;
/** @type {__VLS_StyleScopedClasses['baseline']} */ ;
/** @type {__VLS_StyleScopedClasses['line']} */ ;
var __VLS_dollars;
const __VLS_self = (await import('vue')).defineComponent({
    setup() {
        return {
            PADDING: PADDING,
            baselineY: baselineY,
            palette: palette,
            linePath: linePath,
        };
    },
    __typeProps: {},
    props: {},
});
export default (await import('vue')).defineComponent({
    setup() {
        return {};
    },
    __typeProps: {},
    props: {},
});
; /* PartiallyEnd: #4569/main.vue */
