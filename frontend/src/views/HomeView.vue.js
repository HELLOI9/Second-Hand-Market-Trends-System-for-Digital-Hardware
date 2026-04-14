/// <reference types="../../node_modules/.vue-global-types/vue_3.5_0_0_0.d.ts" />
import { computed, onMounted, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { ElMessage } from 'element-plus';
import { hardwareApi, crawlerApi } from '@/api';
import HardwareCard from '@/components/HardwareCard.vue';
import MiniTrendSparkline from '@/components/MiniTrendSparkline.vue';
const CATEGORY_LABELS = [
    { value: 'cpu', label: 'CPU' },
    { value: 'gpu', label: '显卡' },
    { value: 'memory', label: '内存' },
    { value: 'ssd', label: '固态硬盘' },
];
const VALID_CATEGORIES = new Set(CATEGORY_LABELS.map((item) => item.value));
const HEAT_LEVEL_LABELS = {
    low: '低位',
    normal: '正常',
    high: '偏高',
    none: '无数据',
};
function pickQueryString(value) {
    if (Array.isArray(value)) {
        return typeof value[0] === 'string' ? value[0] : undefined;
    }
    return typeof value === 'string' ? value : undefined;
}
function normalizeCategory(value) {
    const maybe = pickQueryString(value);
    if (maybe && VALID_CATEGORIES.has(maybe)) {
        return maybe;
    }
    return 'cpu';
}
function normalizeView(value) {
    const maybe = pickQueryString(value);
    return maybe === 'cards' || maybe === 'table' ? maybe : 'heatmap';
}
const router = useRouter();
const route = useRoute();
const loading = ref(true);
const activeCategory = ref(normalizeCategory(route.query.category));
const displayMode = ref(normalizeView(route.query.view));
const groupedHardware = ref({});
const crawlerStatus = ref(null);
const trendCache = ref({});
const trendLoadingMap = ref({});
const trendInFlight = new Set();
const activeCategoryLabel = computed(() => {
    return CATEGORY_LABELS.find((item) => item.value === activeCategory.value)?.label ?? 'CPU';
});
const heatmapRows = computed(() => {
    return CATEGORY_LABELS.map((cat) => ({
        ...cat,
        items: groupedHardware.value[cat.value] ?? [],
    }));
});
const hardwareWithStats = computed(() => {
    return Object.values(groupedHardware.value)
        .flat()
        .filter((item) => item.latest_stats);
});
const maxSampleCount = computed(() => {
    const counts = hardwareWithStats.value.map((item) => item.latest_stats?.sample_count ?? 0);
    return counts.length ? Math.max(...counts) : 1;
});
const sampleRanking = computed(() => {
    return [...hardwareWithStats.value]
        .sort((a, b) => (b.latest_stats?.sample_count ?? 0) - (a.latest_stats?.sample_count ?? 0))
        .slice(0, 8);
});
const priceRanking = computed(() => {
    return [...hardwareWithStats.value]
        .sort((a, b) => (b.latest_stats?.median_price ?? 0) - (a.latest_stats?.median_price ?? 0))
        .slice(0, 8);
});
const opportunityRanking = computed(() => {
    return [...hardwareWithStats.value]
        .filter((item) => item.latest_stats?.price_level === 'low')
        .sort((a, b) => (b.latest_stats?.sample_count ?? 0) - (a.latest_stats?.sample_count ?? 0))
        .slice(0, 8);
});
watch([displayMode, activeCategory, groupedHardware], () => {
    if (displayMode.value === 'table') {
        void ensureTrendsForCategory(activeCategory.value);
    }
}, { immediate: true });
watch(() => route.query.category, (nextCategory) => {
    const normalized = normalizeCategory(nextCategory);
    if (normalized !== activeCategory.value) {
        activeCategory.value = normalized;
    }
});
watch(() => route.query.view, (nextView) => {
    const normalized = normalizeView(nextView);
    if (normalized !== displayMode.value) {
        displayMode.value = normalized;
    }
});
watch(activeCategory, (nextCategory) => {
    if (normalizeCategory(route.query.category) === nextCategory) {
        return;
    }
    router.replace({
        name: 'home',
        query: {
            ...route.query,
            category: nextCategory,
            view: displayMode.value,
        },
    });
});
watch(displayMode, (nextView) => {
    if (normalizeView(route.query.view) === nextView) {
        return;
    }
    router.replace({
        name: 'home',
        query: {
            ...route.query,
            category: activeCategory.value,
            view: nextView,
        },
    });
});
onMounted(async () => {
    try {
        const [hardware, status] = await Promise.all([hardwareApi.list(), crawlerApi.status()]);
        groupedHardware.value = hardware;
        crawlerStatus.value = status;
    }
    catch {
        ElMessage.error('加载数据失败，请检查后端服务');
    }
    finally {
        loading.value = false;
    }
});
function formatPrice(price) {
    return price >= 10000 ? `${(price / 10000).toFixed(1)}万` : Math.round(price).toLocaleString();
}
function heatLevel(item) {
    if (!item.latest_stats)
        return 'none';
    return item.latest_stats.price_level;
}
function isSpecialHeatLevel(item) {
    const level = heatLevel(item);
    return level === 'low' || level === 'high' || level === 'none';
}
function specialHeatLabel(item) {
    const level = heatLevel(item);
    return HEAT_LEVEL_LABELS[level];
}
async function loadTrendForHardware(hardwareId) {
    if (trendCache.value[hardwareId] !== undefined || trendInFlight.has(hardwareId)) {
        return;
    }
    trendInFlight.add(hardwareId);
    trendLoadingMap.value = { ...trendLoadingMap.value, [hardwareId]: true };
    try {
        const trend = await hardwareApi.trend(hardwareId, 30);
        trendCache.value = {
            ...trendCache.value,
            [hardwareId]: trend.trend.map((point) => point.median_price),
        };
    }
    catch {
        trendCache.value = {
            ...trendCache.value,
            [hardwareId]: [],
        };
    }
    finally {
        trendInFlight.delete(hardwareId);
        const { [hardwareId]: _removed, ...rest } = trendLoadingMap.value;
        trendLoadingMap.value = rest;
    }
}
async function ensureTrendsForCategory(category) {
    const idsToLoad = (groupedHardware.value[category] ?? [])
        .filter((item) => item.latest_stats)
        .map((item) => item.id)
        .filter((id) => trendCache.value[id] === undefined && !trendInFlight.has(id));
    if (!idsToLoad.length)
        return;
    const queue = [...idsToLoad];
    const concurrency = 4;
    const workers = Array.from({ length: Math.min(concurrency, queue.length) }, async () => {
        while (queue.length) {
            const id = queue.shift();
            if (id === undefined)
                return;
            await loadTrendForHardware(id);
        }
    });
    await Promise.all(workers);
}
function heatStyle(item) {
    if (!item.latest_stats) {
        return {
            backgroundColor: 'rgba(214, 217, 223, 0.35)',
            borderColor: 'rgba(193, 200, 209, 0.8)',
            color: '#536170',
        };
    }
    const ratio = Math.max(0, Math.min(1, item.latest_stats.sample_count / maxSampleCount.value));
    const alpha = 0.32 + ratio * 0.62;
    const colorMap = {
        low: {
            rgb: [72, 160, 120],
            textColor: '#eefaf4',
        },
        normal: {
            rgb: [61, 112, 184],
            textColor: '#f3f8ff',
        },
        high: {
            rgb: [108, 83, 170],
            textColor: '#f7f2ff',
        },
    };
    const level = heatLevel(item);
    const { rgb, textColor } = colorMap[level];
    const [r, g, b] = rgb;
    return {
        backgroundColor: `rgba(${r}, ${g}, ${b}, ${alpha.toFixed(3)})`,
        borderColor: `rgba(${r}, ${g}, ${b}, 0.96)`,
        color: textColor,
    };
}
function goToDetail(id, category) {
    const normalizedCategory = category && VALID_CATEGORIES.has(category)
        ? category
        : activeCategory.value;
    router.push({
        name: 'hardware-detail',
        params: { id },
        query: { fromCategory: normalizedCategory },
    });
}
debugger; /* PartiallyEnd: #3632/scriptSetup.vue */
const __VLS_ctx = {};
let __VLS_components;
let __VLS_directives;
/** @type {__VLS_StyleScopedClasses['hero']} */ ;
/** @type {__VLS_StyleScopedClasses['content']} */ ;
/** @type {__VLS_StyleScopedClasses['view-switch-wrap']} */ ;
/** @type {__VLS_StyleScopedClasses['insight-card']} */ ;
/** @type {__VLS_StyleScopedClasses['insight-card']} */ ;
/** @type {__VLS_StyleScopedClasses['rank-item']} */ ;
/** @type {__VLS_StyleScopedClasses['heatmap-head']} */ ;
/** @type {__VLS_StyleScopedClasses['legend-dot']} */ ;
/** @type {__VLS_StyleScopedClasses['legend-dot']} */ ;
/** @type {__VLS_StyleScopedClasses['legend-dot']} */ ;
/** @type {__VLS_StyleScopedClasses['legend-dot']} */ ;
/** @type {__VLS_StyleScopedClasses['heat-cell']} */ ;
/** @type {__VLS_StyleScopedClasses['cell-value']} */ ;
/** @type {__VLS_StyleScopedClasses['market-table']} */ ;
/** @type {__VLS_StyleScopedClasses['category-tabs']} */ ;
/** @type {__VLS_StyleScopedClasses['category-tabs']} */ ;
/** @type {__VLS_StyleScopedClasses['category-tabs']} */ ;
/** @type {__VLS_StyleScopedClasses['el-tabs__item']} */ ;
/** @type {__VLS_StyleScopedClasses['category-tabs']} */ ;
/** @type {__VLS_StyleScopedClasses['el-tabs__item']} */ ;
/** @type {__VLS_StyleScopedClasses['is-top']} */ ;
/** @type {__VLS_StyleScopedClasses['category-tabs']} */ ;
/** @type {__VLS_StyleScopedClasses['el-tabs__item']} */ ;
/** @type {__VLS_StyleScopedClasses['category-tabs']} */ ;
/** @type {__VLS_StyleScopedClasses['el-tabs__item']} */ ;
/** @type {__VLS_StyleScopedClasses['is-bottom']} */ ;
/** @type {__VLS_StyleScopedClasses['category-tabs']} */ ;
/** @type {__VLS_StyleScopedClasses['el-tabs__item']} */ ;
/** @type {__VLS_StyleScopedClasses['category-tabs']} */ ;
/** @type {__VLS_StyleScopedClasses['insights-grid']} */ ;
/** @type {__VLS_StyleScopedClasses['home']} */ ;
/** @type {__VLS_StyleScopedClasses['hero-inner']} */ ;
/** @type {__VLS_StyleScopedClasses['hero-status']} */ ;
/** @type {__VLS_StyleScopedClasses['view-switch-wrap']} */ ;
/** @type {__VLS_StyleScopedClasses['heatmap-row']} */ ;
/** @type {__VLS_StyleScopedClasses['row-label']} */ ;
/** @type {__VLS_StyleScopedClasses['row-cells']} */ ;
/** @type {__VLS_StyleScopedClasses['card-view']} */ ;
/** @type {__VLS_StyleScopedClasses['table-view']} */ ;
/** @type {__VLS_StyleScopedClasses['card-grid']} */ ;
// CSS variable injection 
// CSS variable injection end 
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "home" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "page-glow" },
    'aria-hidden': "true",
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.header, __VLS_intrinsicElements.header)({
    ...{ class: "hero" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "hero-inner" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "hero-title-wrap" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.p, __VLS_intrinsicElements.p)({
    ...{ class: "hero-eyebrow" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.h1, __VLS_intrinsicElements.h1)({
    ...{ class: "hero-title" },
});
const __VLS_0 = {}.ElIcon;
/** @type {[typeof __VLS_components.ElIcon, typeof __VLS_components.elIcon, typeof __VLS_components.ElIcon, typeof __VLS_components.elIcon, ]} */ ;
// @ts-ignore
const __VLS_1 = __VLS_asFunctionalComponent(__VLS_0, new __VLS_0({}));
const __VLS_2 = __VLS_1({}, ...__VLS_functionalComponentArgsRest(__VLS_1));
__VLS_3.slots.default;
const __VLS_4 = {}.Monitor;
/** @type {[typeof __VLS_components.Monitor, ]} */ ;
// @ts-ignore
const __VLS_5 = __VLS_asFunctionalComponent(__VLS_4, new __VLS_4({}));
const __VLS_6 = __VLS_5({}, ...__VLS_functionalComponentArgsRest(__VLS_5));
var __VLS_3;
__VLS_asFunctionalElement(__VLS_intrinsicElements.p, __VLS_intrinsicElements.p)({
    ...{ class: "hero-subtitle" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "hero-status" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
    ...{ class: "status-kicker" },
});
(__VLS_ctx.displayMode === 'heatmap' ? '总览视图' : '当前栏目');
if (__VLS_ctx.displayMode !== 'heatmap') {
    __VLS_asFunctionalElement(__VLS_intrinsicElements.strong, __VLS_intrinsicElements.strong)({
        ...{ class: "status-value" },
    });
    (__VLS_ctx.activeCategoryLabel);
}
if (__VLS_ctx.crawlerStatus?.last_run_date) {
    __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
        ...{ class: "status-update" },
    });
    (__VLS_ctx.crawlerStatus.last_run_date);
}
else {
    __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
        ...{ class: "status-update" },
    });
}
__VLS_asFunctionalElement(__VLS_intrinsicElements.main, __VLS_intrinsicElements.main)({
    ...{ class: "content" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.section, __VLS_intrinsicElements.section)({
    ...{ class: "view-switch-wrap" },
});
const __VLS_8 = {}.ElRadioGroup;
/** @type {[typeof __VLS_components.ElRadioGroup, typeof __VLS_components.elRadioGroup, typeof __VLS_components.ElRadioGroup, typeof __VLS_components.elRadioGroup, ]} */ ;
// @ts-ignore
const __VLS_9 = __VLS_asFunctionalComponent(__VLS_8, new __VLS_8({
    modelValue: (__VLS_ctx.displayMode),
    size: "small",
}));
const __VLS_10 = __VLS_9({
    modelValue: (__VLS_ctx.displayMode),
    size: "small",
}, ...__VLS_functionalComponentArgsRest(__VLS_9));
__VLS_11.slots.default;
const __VLS_12 = {}.ElRadioButton;
/** @type {[typeof __VLS_components.ElRadioButton, typeof __VLS_components.elRadioButton, typeof __VLS_components.ElRadioButton, typeof __VLS_components.elRadioButton, ]} */ ;
// @ts-ignore
const __VLS_13 = __VLS_asFunctionalComponent(__VLS_12, new __VLS_12({
    label: "heatmap",
    value: "heatmap",
}));
const __VLS_14 = __VLS_13({
    label: "heatmap",
    value: "heatmap",
}, ...__VLS_functionalComponentArgsRest(__VLS_13));
__VLS_15.slots.default;
var __VLS_15;
const __VLS_16 = {}.ElRadioButton;
/** @type {[typeof __VLS_components.ElRadioButton, typeof __VLS_components.elRadioButton, typeof __VLS_components.ElRadioButton, typeof __VLS_components.elRadioButton, ]} */ ;
// @ts-ignore
const __VLS_17 = __VLS_asFunctionalComponent(__VLS_16, new __VLS_16({
    label: "table",
    value: "table",
}));
const __VLS_18 = __VLS_17({
    label: "table",
    value: "table",
}, ...__VLS_functionalComponentArgsRest(__VLS_17));
__VLS_19.slots.default;
var __VLS_19;
const __VLS_20 = {}.ElRadioButton;
/** @type {[typeof __VLS_components.ElRadioButton, typeof __VLS_components.elRadioButton, typeof __VLS_components.ElRadioButton, typeof __VLS_components.elRadioButton, ]} */ ;
// @ts-ignore
const __VLS_21 = __VLS_asFunctionalComponent(__VLS_20, new __VLS_20({
    label: "cards",
    value: "cards",
}));
const __VLS_22 = __VLS_21({
    label: "cards",
    value: "cards",
}, ...__VLS_functionalComponentArgsRest(__VLS_21));
__VLS_23.slots.default;
var __VLS_23;
var __VLS_11;
if (__VLS_ctx.loading) {
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "loading-wrap" },
    });
    const __VLS_24 = {}.ElSkeleton;
    /** @type {[typeof __VLS_components.ElSkeleton, typeof __VLS_components.elSkeleton, ]} */ ;
    // @ts-ignore
    const __VLS_25 = __VLS_asFunctionalComponent(__VLS_24, new __VLS_24({
        rows: (8),
        animated: true,
    }));
    const __VLS_26 = __VLS_25({
        rows: (8),
        animated: true,
    }, ...__VLS_functionalComponentArgsRest(__VLS_25));
}
else if (__VLS_ctx.displayMode === 'heatmap') {
    __VLS_asFunctionalElement(__VLS_intrinsicElements.section, __VLS_intrinsicElements.section)({
        ...{ class: "insights-grid" },
    });
    const __VLS_28 = {}.ElCard;
    /** @type {[typeof __VLS_components.ElCard, typeof __VLS_components.elCard, typeof __VLS_components.ElCard, typeof __VLS_components.elCard, ]} */ ;
    // @ts-ignore
    const __VLS_29 = __VLS_asFunctionalComponent(__VLS_28, new __VLS_28({
        ...{ class: "insight-card" },
        shadow: "never",
    }));
    const __VLS_30 = __VLS_29({
        ...{ class: "insight-card" },
        shadow: "never",
    }, ...__VLS_functionalComponentArgsRest(__VLS_29));
    __VLS_31.slots.default;
    {
        const { header: __VLS_thisSlot } = __VLS_31.slots;
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "insight-title" },
        });
    }
    if (__VLS_ctx.sampleRanking.length) {
        __VLS_asFunctionalElement(__VLS_intrinsicElements.ol, __VLS_intrinsicElements.ol)({
            ...{ class: "rank-list" },
        });
        for (const [item] of __VLS_getVForSourceType((__VLS_ctx.sampleRanking))) {
            __VLS_asFunctionalElement(__VLS_intrinsicElements.li, __VLS_intrinsicElements.li)({
                ...{ onClick: (...[$event]) => {
                        if (!!(__VLS_ctx.loading))
                            return;
                        if (!(__VLS_ctx.displayMode === 'heatmap'))
                            return;
                        if (!(__VLS_ctx.sampleRanking.length))
                            return;
                        __VLS_ctx.goToDetail(item.id, item.category);
                    } },
                ...{ class: "rank-item" },
                key: (`sample-${item.id}`),
            });
            __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
                ...{ class: "rank-name" },
            });
            (item.name);
            __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
                ...{ class: "rank-value" },
            });
            (item.latest_stats?.sample_count ?? 0);
        }
    }
    else {
        const __VLS_32 = {}.ElEmpty;
        /** @type {[typeof __VLS_components.ElEmpty, typeof __VLS_components.elEmpty, ]} */ ;
        // @ts-ignore
        const __VLS_33 = __VLS_asFunctionalComponent(__VLS_32, new __VLS_32({
            description: "暂无数据",
        }));
        const __VLS_34 = __VLS_33({
            description: "暂无数据",
        }, ...__VLS_functionalComponentArgsRest(__VLS_33));
    }
    var __VLS_31;
    const __VLS_36 = {}.ElCard;
    /** @type {[typeof __VLS_components.ElCard, typeof __VLS_components.elCard, typeof __VLS_components.ElCard, typeof __VLS_components.elCard, ]} */ ;
    // @ts-ignore
    const __VLS_37 = __VLS_asFunctionalComponent(__VLS_36, new __VLS_36({
        ...{ class: "insight-card" },
        shadow: "never",
    }));
    const __VLS_38 = __VLS_37({
        ...{ class: "insight-card" },
        shadow: "never",
    }, ...__VLS_functionalComponentArgsRest(__VLS_37));
    __VLS_39.slots.default;
    {
        const { header: __VLS_thisSlot } = __VLS_39.slots;
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "insight-title" },
        });
    }
    if (__VLS_ctx.priceRanking.length) {
        __VLS_asFunctionalElement(__VLS_intrinsicElements.ol, __VLS_intrinsicElements.ol)({
            ...{ class: "rank-list" },
        });
        for (const [item] of __VLS_getVForSourceType((__VLS_ctx.priceRanking))) {
            __VLS_asFunctionalElement(__VLS_intrinsicElements.li, __VLS_intrinsicElements.li)({
                ...{ onClick: (...[$event]) => {
                        if (!!(__VLS_ctx.loading))
                            return;
                        if (!(__VLS_ctx.displayMode === 'heatmap'))
                            return;
                        if (!(__VLS_ctx.priceRanking.length))
                            return;
                        __VLS_ctx.goToDetail(item.id, item.category);
                    } },
                ...{ class: "rank-item" },
                key: (`price-${item.id}`),
            });
            __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
                ...{ class: "rank-name" },
            });
            (item.name);
            __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
                ...{ class: "rank-value" },
            });
            (__VLS_ctx.formatPrice(item.latest_stats?.median_price ?? 0));
        }
    }
    else {
        const __VLS_40 = {}.ElEmpty;
        /** @type {[typeof __VLS_components.ElEmpty, typeof __VLS_components.elEmpty, ]} */ ;
        // @ts-ignore
        const __VLS_41 = __VLS_asFunctionalComponent(__VLS_40, new __VLS_40({
            description: "暂无数据",
        }));
        const __VLS_42 = __VLS_41({
            description: "暂无数据",
        }, ...__VLS_functionalComponentArgsRest(__VLS_41));
    }
    var __VLS_39;
    const __VLS_44 = {}.ElCard;
    /** @type {[typeof __VLS_components.ElCard, typeof __VLS_components.elCard, typeof __VLS_components.ElCard, typeof __VLS_components.elCard, ]} */ ;
    // @ts-ignore
    const __VLS_45 = __VLS_asFunctionalComponent(__VLS_44, new __VLS_44({
        ...{ class: "insight-card" },
        shadow: "never",
    }));
    const __VLS_46 = __VLS_45({
        ...{ class: "insight-card" },
        shadow: "never",
    }, ...__VLS_functionalComponentArgsRest(__VLS_45));
    __VLS_47.slots.default;
    {
        const { header: __VLS_thisSlot } = __VLS_47.slots;
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "insight-title" },
        });
    }
    if (__VLS_ctx.opportunityRanking.length) {
        __VLS_asFunctionalElement(__VLS_intrinsicElements.ol, __VLS_intrinsicElements.ol)({
            ...{ class: "rank-list" },
        });
        for (const [item] of __VLS_getVForSourceType((__VLS_ctx.opportunityRanking))) {
            __VLS_asFunctionalElement(__VLS_intrinsicElements.li, __VLS_intrinsicElements.li)({
                ...{ onClick: (...[$event]) => {
                        if (!!(__VLS_ctx.loading))
                            return;
                        if (!(__VLS_ctx.displayMode === 'heatmap'))
                            return;
                        if (!(__VLS_ctx.opportunityRanking.length))
                            return;
                        __VLS_ctx.goToDetail(item.id, item.category);
                    } },
                ...{ class: "rank-item" },
                key: (`opp-${item.id}`),
            });
            __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
                ...{ class: "rank-name" },
            });
            (item.name);
            __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
                ...{ class: "rank-value" },
            });
            (item.latest_stats?.sample_count ?? 0);
        }
    }
    else {
        const __VLS_48 = {}.ElEmpty;
        /** @type {[typeof __VLS_components.ElEmpty, typeof __VLS_components.elEmpty, ]} */ ;
        // @ts-ignore
        const __VLS_49 = __VLS_asFunctionalComponent(__VLS_48, new __VLS_48({
            description: "暂无低位标记数据",
        }));
        const __VLS_50 = __VLS_49({
            description: "暂无低位标记数据",
        }, ...__VLS_functionalComponentArgsRest(__VLS_49));
    }
    var __VLS_47;
    __VLS_asFunctionalElement(__VLS_intrinsicElements.section, __VLS_intrinsicElements.section)({
        ...{ class: "heatmap-board" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "heatmap-head" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.h3, __VLS_intrinsicElements.h3)({});
    __VLS_asFunctionalElement(__VLS_intrinsicElements.p, __VLS_intrinsicElements.p)({});
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "heat-legend" },
        'aria-label': "热力图图例",
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
        ...{ class: "legend-item" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.i, __VLS_intrinsicElements.i)({
        ...{ class: "legend-dot low" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
        ...{ class: "legend-item" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.i, __VLS_intrinsicElements.i)({
        ...{ class: "legend-dot normal" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
        ...{ class: "legend-item" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.i, __VLS_intrinsicElements.i)({
        ...{ class: "legend-dot high" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
        ...{ class: "legend-item" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.i, __VLS_intrinsicElements.i)({
        ...{ class: "legend-dot none" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "heatmap-table" },
    });
    for (const [row] of __VLS_getVForSourceType((__VLS_ctx.heatmapRows))) {
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "heatmap-row" },
            key: (row.value),
        });
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "row-label" },
        });
        (row.label);
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "row-cells" },
        });
        for (const [item] of __VLS_getVForSourceType((row.items))) {
            __VLS_asFunctionalElement(__VLS_intrinsicElements.button, __VLS_intrinsicElements.button)({
                ...{ onClick: (...[$event]) => {
                        if (!!(__VLS_ctx.loading))
                            return;
                        if (!(__VLS_ctx.displayMode === 'heatmap'))
                            return;
                        __VLS_ctx.goToDetail(item.id, item.category);
                    } },
                key: (item.id),
                ...{ class: "heat-cell" },
                ...{ class: (`level-${__VLS_ctx.heatLevel(item)}`) },
                ...{ style: (__VLS_ctx.heatStyle(item)) },
            });
            __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
                ...{ class: "cell-top" },
            });
            __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
                ...{ class: "cell-name" },
            });
            (item.name);
            if (__VLS_ctx.isSpecialHeatLevel(item)) {
                __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
                    ...{ class: "cell-level" },
                    ...{ class: (`badge-${__VLS_ctx.heatLevel(item)}`) },
                });
                (__VLS_ctx.specialHeatLabel(item));
            }
            if (item.latest_stats) {
                __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
                    ...{ class: "cell-value" },
                });
                (__VLS_ctx.formatPrice(item.latest_stats.median_price));
            }
            else {
                __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
                    ...{ class: "cell-value muted" },
                });
            }
        }
    }
}
else if (__VLS_ctx.displayMode === 'table') {
    __VLS_asFunctionalElement(__VLS_intrinsicElements.section, __VLS_intrinsicElements.section)({
        ...{ class: "table-view" },
    });
    const __VLS_52 = {}.ElTabs;
    /** @type {[typeof __VLS_components.ElTabs, typeof __VLS_components.elTabs, typeof __VLS_components.ElTabs, typeof __VLS_components.elTabs, ]} */ ;
    // @ts-ignore
    const __VLS_53 = __VLS_asFunctionalComponent(__VLS_52, new __VLS_52({
        modelValue: (__VLS_ctx.activeCategory),
        ...{ class: "category-tabs table-tabs" },
    }));
    const __VLS_54 = __VLS_53({
        modelValue: (__VLS_ctx.activeCategory),
        ...{ class: "category-tabs table-tabs" },
    }, ...__VLS_functionalComponentArgsRest(__VLS_53));
    __VLS_55.slots.default;
    for (const [cat] of __VLS_getVForSourceType((__VLS_ctx.CATEGORY_LABELS))) {
        const __VLS_56 = {}.ElTabPane;
        /** @type {[typeof __VLS_components.ElTabPane, typeof __VLS_components.elTabPane, typeof __VLS_components.ElTabPane, typeof __VLS_components.elTabPane, ]} */ ;
        // @ts-ignore
        const __VLS_57 = __VLS_asFunctionalComponent(__VLS_56, new __VLS_56({
            key: (`table-${cat.value}`),
            label: (cat.label),
            name: (cat.value),
        }));
        const __VLS_58 = __VLS_57({
            key: (`table-${cat.value}`),
            label: (cat.label),
            name: (cat.value),
        }, ...__VLS_functionalComponentArgsRest(__VLS_57));
        __VLS_59.slots.default;
        const __VLS_60 = {}.ElTable;
        /** @type {[typeof __VLS_components.ElTable, typeof __VLS_components.elTable, typeof __VLS_components.ElTable, typeof __VLS_components.elTable, ]} */ ;
        // @ts-ignore
        const __VLS_61 = __VLS_asFunctionalComponent(__VLS_60, new __VLS_60({
            data: (__VLS_ctx.groupedHardware[cat.value] || []),
            ...{ class: "market-table" },
            stripe: true,
        }));
        const __VLS_62 = __VLS_61({
            data: (__VLS_ctx.groupedHardware[cat.value] || []),
            ...{ class: "market-table" },
            stripe: true,
        }, ...__VLS_functionalComponentArgsRest(__VLS_61));
        __VLS_63.slots.default;
        const __VLS_64 = {}.ElTableColumn;
        /** @type {[typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, ]} */ ;
        // @ts-ignore
        const __VLS_65 = __VLS_asFunctionalComponent(__VLS_64, new __VLS_64({
            prop: "name",
            label: "硬件",
            minWidth: "180",
        }));
        const __VLS_66 = __VLS_65({
            prop: "name",
            label: "硬件",
            minWidth: "180",
        }, ...__VLS_functionalComponentArgsRest(__VLS_65));
        const __VLS_68 = {}.ElTableColumn;
        /** @type {[typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, ]} */ ;
        // @ts-ignore
        const __VLS_69 = __VLS_asFunctionalComponent(__VLS_68, new __VLS_68({
            label: "中位价",
            width: "130",
        }));
        const __VLS_70 = __VLS_69({
            label: "中位价",
            width: "130",
        }, ...__VLS_functionalComponentArgsRest(__VLS_69));
        __VLS_71.slots.default;
        {
            const { default: __VLS_thisSlot } = __VLS_71.slots;
            const [{ row }] = __VLS_getSlotParams(__VLS_thisSlot);
            if (row.latest_stats) {
                __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({});
                (__VLS_ctx.formatPrice(row.latest_stats.median_price));
            }
            else {
                __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
                    ...{ class: "muted-cell" },
                });
            }
        }
        var __VLS_71;
        const __VLS_72 = {}.ElTableColumn;
        /** @type {[typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, ]} */ ;
        // @ts-ignore
        const __VLS_73 = __VLS_asFunctionalComponent(__VLS_72, new __VLS_72({
            label: "价格区间",
            minWidth: "180",
        }));
        const __VLS_74 = __VLS_73({
            label: "价格区间",
            minWidth: "180",
        }, ...__VLS_functionalComponentArgsRest(__VLS_73));
        __VLS_75.slots.default;
        {
            const { default: __VLS_thisSlot } = __VLS_75.slots;
            const [{ row }] = __VLS_getSlotParams(__VLS_thisSlot);
            if (row.latest_stats) {
                __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({});
                (__VLS_ctx.formatPrice(row.latest_stats.min_price));
                (__VLS_ctx.formatPrice(row.latest_stats.max_price));
            }
            else {
                __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
                    ...{ class: "muted-cell" },
                });
            }
        }
        var __VLS_75;
        const __VLS_76 = {}.ElTableColumn;
        /** @type {[typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, ]} */ ;
        // @ts-ignore
        const __VLS_77 = __VLS_asFunctionalComponent(__VLS_76, new __VLS_76({
            label: "样本数",
            width: "90",
        }));
        const __VLS_78 = __VLS_77({
            label: "样本数",
            width: "90",
        }, ...__VLS_functionalComponentArgsRest(__VLS_77));
        __VLS_79.slots.default;
        {
            const { default: __VLS_thisSlot } = __VLS_79.slots;
            const [{ row }] = __VLS_getSlotParams(__VLS_thisSlot);
            if (row.latest_stats) {
                __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({});
                (row.latest_stats.sample_count);
            }
            else {
                __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
                    ...{ class: "muted-cell" },
                });
            }
        }
        var __VLS_79;
        const __VLS_80 = {}.ElTableColumn;
        /** @type {[typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, ]} */ ;
        // @ts-ignore
        const __VLS_81 = __VLS_asFunctionalComponent(__VLS_80, new __VLS_80({
            label: "状态",
            width: "90",
        }));
        const __VLS_82 = __VLS_81({
            label: "状态",
            width: "90",
        }, ...__VLS_functionalComponentArgsRest(__VLS_81));
        __VLS_83.slots.default;
        {
            const { default: __VLS_thisSlot } = __VLS_83.slots;
            const [{ row }] = __VLS_getSlotParams(__VLS_thisSlot);
            __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
                ...{ class: "level-chip" },
                ...{ class: (`chip-${__VLS_ctx.heatLevel(row)}`) },
            });
            (__VLS_ctx.HEAT_LEVEL_LABELS[__VLS_ctx.heatLevel(row)]);
        }
        var __VLS_83;
        const __VLS_84 = {}.ElTableColumn;
        /** @type {[typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, ]} */ ;
        // @ts-ignore
        const __VLS_85 = __VLS_asFunctionalComponent(__VLS_84, new __VLS_84({
            label: "趋势(30天)",
            minWidth: "220",
        }));
        const __VLS_86 = __VLS_85({
            label: "趋势(30天)",
            minWidth: "220",
        }, ...__VLS_functionalComponentArgsRest(__VLS_85));
        __VLS_87.slots.default;
        {
            const { default: __VLS_thisSlot } = __VLS_87.slots;
            const [{ row }] = __VLS_getSlotParams(__VLS_thisSlot);
            /** @type {[typeof MiniTrendSparkline, ]} */ ;
            // @ts-ignore
            const __VLS_88 = __VLS_asFunctionalComponent(MiniTrendSparkline, new MiniTrendSparkline({
                points: (__VLS_ctx.trendCache[row.id] ?? []),
                loading: (Boolean(__VLS_ctx.trendLoadingMap[row.id])),
                level: (__VLS_ctx.heatLevel(row)),
            }));
            const __VLS_89 = __VLS_88({
                points: (__VLS_ctx.trendCache[row.id] ?? []),
                loading: (Boolean(__VLS_ctx.trendLoadingMap[row.id])),
                level: (__VLS_ctx.heatLevel(row)),
            }, ...__VLS_functionalComponentArgsRest(__VLS_88));
        }
        var __VLS_87;
        const __VLS_91 = {}.ElTableColumn;
        /** @type {[typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, ]} */ ;
        // @ts-ignore
        const __VLS_92 = __VLS_asFunctionalComponent(__VLS_91, new __VLS_91({
            label: "详情",
            width: "88",
            fixed: "right",
        }));
        const __VLS_93 = __VLS_92({
            label: "详情",
            width: "88",
            fixed: "right",
        }, ...__VLS_functionalComponentArgsRest(__VLS_92));
        __VLS_94.slots.default;
        {
            const { default: __VLS_thisSlot } = __VLS_94.slots;
            const [{ row }] = __VLS_getSlotParams(__VLS_thisSlot);
            const __VLS_95 = {}.ElButton;
            /** @type {[typeof __VLS_components.ElButton, typeof __VLS_components.elButton, typeof __VLS_components.ElButton, typeof __VLS_components.elButton, ]} */ ;
            // @ts-ignore
            const __VLS_96 = __VLS_asFunctionalComponent(__VLS_95, new __VLS_95({
                ...{ 'onClick': {} },
                link: true,
                type: "primary",
            }));
            const __VLS_97 = __VLS_96({
                ...{ 'onClick': {} },
                link: true,
                type: "primary",
            }, ...__VLS_functionalComponentArgsRest(__VLS_96));
            let __VLS_99;
            let __VLS_100;
            let __VLS_101;
            const __VLS_102 = {
                onClick: (...[$event]) => {
                    if (!!(__VLS_ctx.loading))
                        return;
                    if (!!(__VLS_ctx.displayMode === 'heatmap'))
                        return;
                    if (!(__VLS_ctx.displayMode === 'table'))
                        return;
                    __VLS_ctx.goToDetail(row.id, cat.value);
                }
            };
            __VLS_98.slots.default;
            var __VLS_98;
        }
        var __VLS_94;
        var __VLS_63;
        if (!(__VLS_ctx.groupedHardware[cat.value]?.length)) {
            const __VLS_103 = {}.ElEmpty;
            /** @type {[typeof __VLS_components.ElEmpty, typeof __VLS_components.elEmpty, ]} */ ;
            // @ts-ignore
            const __VLS_104 = __VLS_asFunctionalComponent(__VLS_103, new __VLS_103({
                description: "暂无数据",
            }));
            const __VLS_105 = __VLS_104({
                description: "暂无数据",
            }, ...__VLS_functionalComponentArgsRest(__VLS_104));
        }
        var __VLS_59;
    }
    var __VLS_55;
}
else {
    __VLS_asFunctionalElement(__VLS_intrinsicElements.section, __VLS_intrinsicElements.section)({
        ...{ class: "card-view" },
    });
    const __VLS_107 = {}.ElTabs;
    /** @type {[typeof __VLS_components.ElTabs, typeof __VLS_components.elTabs, typeof __VLS_components.ElTabs, typeof __VLS_components.elTabs, ]} */ ;
    // @ts-ignore
    const __VLS_108 = __VLS_asFunctionalComponent(__VLS_107, new __VLS_107({
        modelValue: (__VLS_ctx.activeCategory),
        ...{ class: "category-tabs" },
    }));
    const __VLS_109 = __VLS_108({
        modelValue: (__VLS_ctx.activeCategory),
        ...{ class: "category-tabs" },
    }, ...__VLS_functionalComponentArgsRest(__VLS_108));
    __VLS_110.slots.default;
    for (const [cat] of __VLS_getVForSourceType((__VLS_ctx.CATEGORY_LABELS))) {
        const __VLS_111 = {}.ElTabPane;
        /** @type {[typeof __VLS_components.ElTabPane, typeof __VLS_components.elTabPane, typeof __VLS_components.ElTabPane, typeof __VLS_components.elTabPane, ]} */ ;
        // @ts-ignore
        const __VLS_112 = __VLS_asFunctionalComponent(__VLS_111, new __VLS_111({
            key: (cat.value),
            label: (cat.label),
            name: (cat.value),
        }));
        const __VLS_113 = __VLS_112({
            key: (cat.value),
            label: (cat.label),
            name: (cat.value),
        }, ...__VLS_functionalComponentArgsRest(__VLS_112));
        __VLS_114.slots.default;
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "card-grid" },
        });
        for (const [item] of __VLS_getVForSourceType((__VLS_ctx.groupedHardware[cat.value] || []))) {
            /** @type {[typeof HardwareCard, ]} */ ;
            // @ts-ignore
            const __VLS_115 = __VLS_asFunctionalComponent(HardwareCard, new HardwareCard({
                ...{ 'onClick': {} },
                key: (item.id),
                item: (item),
            }));
            const __VLS_116 = __VLS_115({
                ...{ 'onClick': {} },
                key: (item.id),
                item: (item),
            }, ...__VLS_functionalComponentArgsRest(__VLS_115));
            let __VLS_118;
            let __VLS_119;
            let __VLS_120;
            const __VLS_121 = {
                onClick: (...[$event]) => {
                    if (!!(__VLS_ctx.loading))
                        return;
                    if (!!(__VLS_ctx.displayMode === 'heatmap'))
                        return;
                    if (!!(__VLS_ctx.displayMode === 'table'))
                        return;
                    __VLS_ctx.goToDetail(item.id, cat.value);
                }
            };
            var __VLS_117;
        }
        if (!(__VLS_ctx.groupedHardware[cat.value]?.length)) {
            const __VLS_122 = {}.ElEmpty;
            /** @type {[typeof __VLS_components.ElEmpty, typeof __VLS_components.elEmpty, ]} */ ;
            // @ts-ignore
            const __VLS_123 = __VLS_asFunctionalComponent(__VLS_122, new __VLS_122({
                description: "暂无数据",
            }));
            const __VLS_124 = __VLS_123({
                description: "暂无数据",
            }, ...__VLS_functionalComponentArgsRest(__VLS_123));
        }
        var __VLS_114;
    }
    var __VLS_110;
}
/** @type {__VLS_StyleScopedClasses['home']} */ ;
/** @type {__VLS_StyleScopedClasses['page-glow']} */ ;
/** @type {__VLS_StyleScopedClasses['hero']} */ ;
/** @type {__VLS_StyleScopedClasses['hero-inner']} */ ;
/** @type {__VLS_StyleScopedClasses['hero-title-wrap']} */ ;
/** @type {__VLS_StyleScopedClasses['hero-eyebrow']} */ ;
/** @type {__VLS_StyleScopedClasses['hero-title']} */ ;
/** @type {__VLS_StyleScopedClasses['hero-subtitle']} */ ;
/** @type {__VLS_StyleScopedClasses['hero-status']} */ ;
/** @type {__VLS_StyleScopedClasses['status-kicker']} */ ;
/** @type {__VLS_StyleScopedClasses['status-value']} */ ;
/** @type {__VLS_StyleScopedClasses['status-update']} */ ;
/** @type {__VLS_StyleScopedClasses['status-update']} */ ;
/** @type {__VLS_StyleScopedClasses['content']} */ ;
/** @type {__VLS_StyleScopedClasses['view-switch-wrap']} */ ;
/** @type {__VLS_StyleScopedClasses['loading-wrap']} */ ;
/** @type {__VLS_StyleScopedClasses['insights-grid']} */ ;
/** @type {__VLS_StyleScopedClasses['insight-card']} */ ;
/** @type {__VLS_StyleScopedClasses['insight-title']} */ ;
/** @type {__VLS_StyleScopedClasses['rank-list']} */ ;
/** @type {__VLS_StyleScopedClasses['rank-item']} */ ;
/** @type {__VLS_StyleScopedClasses['rank-name']} */ ;
/** @type {__VLS_StyleScopedClasses['rank-value']} */ ;
/** @type {__VLS_StyleScopedClasses['insight-card']} */ ;
/** @type {__VLS_StyleScopedClasses['insight-title']} */ ;
/** @type {__VLS_StyleScopedClasses['rank-list']} */ ;
/** @type {__VLS_StyleScopedClasses['rank-item']} */ ;
/** @type {__VLS_StyleScopedClasses['rank-name']} */ ;
/** @type {__VLS_StyleScopedClasses['rank-value']} */ ;
/** @type {__VLS_StyleScopedClasses['insight-card']} */ ;
/** @type {__VLS_StyleScopedClasses['insight-title']} */ ;
/** @type {__VLS_StyleScopedClasses['rank-list']} */ ;
/** @type {__VLS_StyleScopedClasses['rank-item']} */ ;
/** @type {__VLS_StyleScopedClasses['rank-name']} */ ;
/** @type {__VLS_StyleScopedClasses['rank-value']} */ ;
/** @type {__VLS_StyleScopedClasses['heatmap-board']} */ ;
/** @type {__VLS_StyleScopedClasses['heatmap-head']} */ ;
/** @type {__VLS_StyleScopedClasses['heat-legend']} */ ;
/** @type {__VLS_StyleScopedClasses['legend-item']} */ ;
/** @type {__VLS_StyleScopedClasses['legend-dot']} */ ;
/** @type {__VLS_StyleScopedClasses['low']} */ ;
/** @type {__VLS_StyleScopedClasses['legend-item']} */ ;
/** @type {__VLS_StyleScopedClasses['legend-dot']} */ ;
/** @type {__VLS_StyleScopedClasses['normal']} */ ;
/** @type {__VLS_StyleScopedClasses['legend-item']} */ ;
/** @type {__VLS_StyleScopedClasses['legend-dot']} */ ;
/** @type {__VLS_StyleScopedClasses['high']} */ ;
/** @type {__VLS_StyleScopedClasses['legend-item']} */ ;
/** @type {__VLS_StyleScopedClasses['legend-dot']} */ ;
/** @type {__VLS_StyleScopedClasses['none']} */ ;
/** @type {__VLS_StyleScopedClasses['heatmap-table']} */ ;
/** @type {__VLS_StyleScopedClasses['heatmap-row']} */ ;
/** @type {__VLS_StyleScopedClasses['row-label']} */ ;
/** @type {__VLS_StyleScopedClasses['row-cells']} */ ;
/** @type {__VLS_StyleScopedClasses['heat-cell']} */ ;
/** @type {__VLS_StyleScopedClasses['cell-top']} */ ;
/** @type {__VLS_StyleScopedClasses['cell-name']} */ ;
/** @type {__VLS_StyleScopedClasses['cell-level']} */ ;
/** @type {__VLS_StyleScopedClasses['cell-value']} */ ;
/** @type {__VLS_StyleScopedClasses['cell-value']} */ ;
/** @type {__VLS_StyleScopedClasses['muted']} */ ;
/** @type {__VLS_StyleScopedClasses['table-view']} */ ;
/** @type {__VLS_StyleScopedClasses['category-tabs']} */ ;
/** @type {__VLS_StyleScopedClasses['table-tabs']} */ ;
/** @type {__VLS_StyleScopedClasses['market-table']} */ ;
/** @type {__VLS_StyleScopedClasses['muted-cell']} */ ;
/** @type {__VLS_StyleScopedClasses['muted-cell']} */ ;
/** @type {__VLS_StyleScopedClasses['muted-cell']} */ ;
/** @type {__VLS_StyleScopedClasses['level-chip']} */ ;
/** @type {__VLS_StyleScopedClasses['card-view']} */ ;
/** @type {__VLS_StyleScopedClasses['category-tabs']} */ ;
/** @type {__VLS_StyleScopedClasses['card-grid']} */ ;
var __VLS_dollars;
const __VLS_self = (await import('vue')).defineComponent({
    setup() {
        return {
            HardwareCard: HardwareCard,
            MiniTrendSparkline: MiniTrendSparkline,
            CATEGORY_LABELS: CATEGORY_LABELS,
            HEAT_LEVEL_LABELS: HEAT_LEVEL_LABELS,
            loading: loading,
            activeCategory: activeCategory,
            displayMode: displayMode,
            groupedHardware: groupedHardware,
            crawlerStatus: crawlerStatus,
            trendCache: trendCache,
            trendLoadingMap: trendLoadingMap,
            activeCategoryLabel: activeCategoryLabel,
            heatmapRows: heatmapRows,
            sampleRanking: sampleRanking,
            priceRanking: priceRanking,
            opportunityRanking: opportunityRanking,
            formatPrice: formatPrice,
            heatLevel: heatLevel,
            isSpecialHeatLevel: isSpecialHeatLevel,
            specialHeatLabel: specialHeatLabel,
            heatStyle: heatStyle,
            goToDetail: goToDetail,
        };
    },
});
export default (await import('vue')).defineComponent({
    setup() {
        return {};
    },
});
; /* PartiallyEnd: #4569/main.vue */
