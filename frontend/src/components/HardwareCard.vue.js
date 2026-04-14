import { computed } from 'vue';
const props = defineProps();
const emit = defineEmits();
const CATEGORY_LABELS = {
    cpu: 'CPU',
    gpu: '显卡',
    memory: '内存',
    ssd: '固态',
};
const latestStats = computed(() => props.item.latest_stats ?? null);
const levelClass = computed(() => {
    switch (latestStats.value?.price_level) {
        case 'low':
            return 'level-low';
        case 'high':
            return 'level-high';
        default:
            return 'level-normal';
    }
});
const categoryLabel = computed(() => CATEGORY_LABELS[props.item.category] ?? props.item.category);
const levelLabel = computed(() => {
    switch (latestStats.value?.price_level) {
        case 'low':
            return '低位';
        case 'high':
            return '偏高';
        default:
            return '正常';
    }
});
function formatPrice(price) {
    return price >= 10000 ? `${(price / 10000).toFixed(1)}万` : Math.round(price).toLocaleString();
}
debugger; /* PartiallyEnd: #3632/scriptSetup.vue */
const __VLS_ctx = {};
let __VLS_components;
let __VLS_directives;
/** @type {__VLS_StyleScopedClasses['hardware-card']} */ ;
/** @type {__VLS_StyleScopedClasses['hardware-card']} */ ;
/** @type {__VLS_StyleScopedClasses['category-pill']} */ ;
/** @type {__VLS_StyleScopedClasses['level-pill']} */ ;
/** @type {__VLS_StyleScopedClasses['meta-line']} */ ;
/** @type {__VLS_StyleScopedClasses['meta-line']} */ ;
/** @type {__VLS_StyleScopedClasses['level-pill']} */ ;
/** @type {__VLS_StyleScopedClasses['level-low']} */ ;
/** @type {__VLS_StyleScopedClasses['price']} */ ;
/** @type {__VLS_StyleScopedClasses['level-pill']} */ ;
/** @type {__VLS_StyleScopedClasses['level-high']} */ ;
/** @type {__VLS_StyleScopedClasses['price']} */ ;
/** @type {__VLS_StyleScopedClasses['hardware-card']} */ ;
/** @type {__VLS_StyleScopedClasses['name']} */ ;
/** @type {__VLS_StyleScopedClasses['price']} */ ;
// CSS variable injection 
// CSS variable injection end 
const __VLS_0 = {}.ElCard;
/** @type {[typeof __VLS_components.ElCard, typeof __VLS_components.elCard, typeof __VLS_components.ElCard, typeof __VLS_components.elCard, ]} */ ;
// @ts-ignore
const __VLS_1 = __VLS_asFunctionalComponent(__VLS_0, new __VLS_0({
    ...{ 'onClick': {} },
    ...{ class: "hardware-card" },
    ...{ class: (__VLS_ctx.levelClass) },
    shadow: "never",
}));
const __VLS_2 = __VLS_1({
    ...{ 'onClick': {} },
    ...{ class: "hardware-card" },
    ...{ class: (__VLS_ctx.levelClass) },
    shadow: "never",
}, ...__VLS_functionalComponentArgsRest(__VLS_1));
let __VLS_4;
let __VLS_5;
let __VLS_6;
const __VLS_7 = {
    onClick: (...[$event]) => {
        __VLS_ctx.emit('click');
    }
};
var __VLS_8 = {};
__VLS_3.slots.default;
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "card-header" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
    ...{ class: "category-pill" },
});
(__VLS_ctx.categoryLabel);
if (__VLS_ctx.latestStats) {
    __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
        ...{ class: "level-pill" },
    });
    (__VLS_ctx.levelLabel);
}
__VLS_asFunctionalElement(__VLS_intrinsicElements.h3, __VLS_intrinsicElements.h3)({
    ...{ class: "name" },
});
(__VLS_ctx.item.name);
if (__VLS_ctx.latestStats) {
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "price-row" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
        ...{ class: "price" },
    });
    (__VLS_ctx.formatPrice(__VLS_ctx.latestStats.median_price));
    __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
        ...{ class: "price-label" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "meta-line" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({});
    (__VLS_ctx.formatPrice(__VLS_ctx.latestStats.min_price));
    (__VLS_ctx.formatPrice(__VLS_ctx.latestStats.max_price));
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "meta-line" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({});
    (__VLS_ctx.latestStats.sample_count);
    __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({});
    (__VLS_ctx.latestStats.stat_date);
}
else {
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "no-data" },
    });
}
var __VLS_3;
/** @type {__VLS_StyleScopedClasses['hardware-card']} */ ;
/** @type {__VLS_StyleScopedClasses['card-header']} */ ;
/** @type {__VLS_StyleScopedClasses['category-pill']} */ ;
/** @type {__VLS_StyleScopedClasses['level-pill']} */ ;
/** @type {__VLS_StyleScopedClasses['name']} */ ;
/** @type {__VLS_StyleScopedClasses['price-row']} */ ;
/** @type {__VLS_StyleScopedClasses['price']} */ ;
/** @type {__VLS_StyleScopedClasses['price-label']} */ ;
/** @type {__VLS_StyleScopedClasses['meta-line']} */ ;
/** @type {__VLS_StyleScopedClasses['meta-line']} */ ;
/** @type {__VLS_StyleScopedClasses['no-data']} */ ;
var __VLS_dollars;
const __VLS_self = (await import('vue')).defineComponent({
    setup() {
        return {
            emit: emit,
            latestStats: latestStats,
            levelClass: levelClass,
            categoryLabel: categoryLabel,
            levelLabel: levelLabel,
            formatPrice: formatPrice,
        };
    },
    __typeEmits: {},
    __typeProps: {},
});
export default (await import('vue')).defineComponent({
    setup() {
        return {};
    },
    __typeEmits: {},
    __typeProps: {},
});
; /* PartiallyEnd: #4569/main.vue */
