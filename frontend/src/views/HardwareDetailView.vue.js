/// <reference types="../../node_modules/.vue-global-types/vue_3.5_0_0_0.d.ts" />
import { ref, onMounted } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { ElMessage } from 'element-plus';
import { hardwareApi } from '@/api';
import PriceTrendChart from '@/components/PriceTrendChart.vue';
const props = defineProps();
const router = useRouter();
const route = useRoute();
const CATEGORY_LABELS = {
    cpu: 'CPU',
    gpu: '显卡',
    memory: '内存',
    ssd: '固态硬盘',
};
const VALID_CATEGORIES = new Set(Object.keys(CATEGORY_LABELS));
const LEVEL_LABELS = {
    low: '低位',
    normal: '正常',
    high: '偏高',
};
const loading = ref(true);
const trendLoading = ref(false);
const hardware = ref(null);
const trendData = ref(null);
const selectedDays = ref(30);
function queryString(value) {
    if (Array.isArray(value)) {
        return typeof value[0] === 'string' ? value[0] : null;
    }
    return typeof value === 'string' ? value : null;
}
function goBack() {
    const fromCategory = queryString(route.query.fromCategory);
    if (fromCategory && VALID_CATEGORIES.has(fromCategory)) {
        router.push({
            name: 'home',
            query: { category: fromCategory },
        });
        return;
    }
    router.push({ name: 'home' });
}
function levelTagType(level) {
    if (level === 'low')
        return 'success';
    if (level === 'high')
        return 'warning';
    return 'info';
}
function formatPrice(price) {
    return price >= 10000 ? `${(price / 10000).toFixed(1)}万` : Math.round(price).toLocaleString();
}
async function loadTrend() {
    trendLoading.value = true;
    try {
        trendData.value = await hardwareApi.trend(Number(props.id), selectedDays.value);
    }
    catch {
        ElMessage.error('加载走势数据失败');
    }
    finally {
        trendLoading.value = false;
    }
}
onMounted(async () => {
    try {
        const [detail] = await Promise.all([hardwareApi.detail(Number(props.id)), loadTrend()]);
        hardware.value = detail;
    }
    catch {
        ElMessage.error('加载硬件信息失败');
    }
    finally {
        loading.value = false;
    }
});
debugger; /* PartiallyEnd: #3632/scriptSetup.vue */
const __VLS_ctx = {};
let __VLS_components;
let __VLS_directives;
/** @type {__VLS_StyleScopedClasses['back-btn']} */ ;
/** @type {__VLS_StyleScopedClasses['stat-card']} */ ;
/** @type {__VLS_StyleScopedClasses['stat-value']} */ ;
/** @type {__VLS_StyleScopedClasses['chart-card']} */ ;
/** @type {__VLS_StyleScopedClasses['detail-page']} */ ;
/** @type {__VLS_StyleScopedClasses['header-inner']} */ ;
/** @type {__VLS_StyleScopedClasses['chart-header']} */ ;
// CSS variable injection 
// CSS variable injection end 
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "detail-page" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.header, __VLS_intrinsicElements.header)({
    ...{ class: "detail-header" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "header-inner" },
});
const __VLS_0 = {}.ElButton;
/** @type {[typeof __VLS_components.ElButton, typeof __VLS_components.elButton, typeof __VLS_components.ElButton, typeof __VLS_components.elButton, ]} */ ;
// @ts-ignore
const __VLS_1 = __VLS_asFunctionalComponent(__VLS_0, new __VLS_0({
    ...{ 'onClick': {} },
    ...{ class: "back-btn" },
    text: true,
}));
const __VLS_2 = __VLS_1({
    ...{ 'onClick': {} },
    ...{ class: "back-btn" },
    text: true,
}, ...__VLS_functionalComponentArgsRest(__VLS_1));
let __VLS_4;
let __VLS_5;
let __VLS_6;
const __VLS_7 = {
    onClick: (__VLS_ctx.goBack)
};
__VLS_3.slots.default;
const __VLS_8 = {}.ElIcon;
/** @type {[typeof __VLS_components.ElIcon, typeof __VLS_components.elIcon, typeof __VLS_components.ElIcon, typeof __VLS_components.elIcon, ]} */ ;
// @ts-ignore
const __VLS_9 = __VLS_asFunctionalComponent(__VLS_8, new __VLS_8({}));
const __VLS_10 = __VLS_9({}, ...__VLS_functionalComponentArgsRest(__VLS_9));
__VLS_11.slots.default;
const __VLS_12 = {}.ArrowLeft;
/** @type {[typeof __VLS_components.ArrowLeft, ]} */ ;
// @ts-ignore
const __VLS_13 = __VLS_asFunctionalComponent(__VLS_12, new __VLS_12({}));
const __VLS_14 = __VLS_13({}, ...__VLS_functionalComponentArgsRest(__VLS_13));
var __VLS_11;
var __VLS_3;
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "title-wrap" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.h2, __VLS_intrinsicElements.h2)({
    ...{ class: "title" },
});
(__VLS_ctx.hardware?.name ?? '加载中…');
if (__VLS_ctx.hardware?.latest_stats) {
    __VLS_asFunctionalElement(__VLS_intrinsicElements.p, __VLS_intrinsicElements.p)({
        ...{ class: "subtitle" },
    });
    (__VLS_ctx.hardware.latest_stats.stat_date);
    (__VLS_ctx.hardware.latest_stats.sample_count);
}
if (__VLS_ctx.hardware?.category) {
    const __VLS_16 = {}.ElTag;
    /** @type {[typeof __VLS_components.ElTag, typeof __VLS_components.elTag, typeof __VLS_components.ElTag, typeof __VLS_components.elTag, ]} */ ;
    // @ts-ignore
    const __VLS_17 = __VLS_asFunctionalComponent(__VLS_16, new __VLS_16({
        effect: "dark",
        round: true,
    }));
    const __VLS_18 = __VLS_17({
        effect: "dark",
        round: true,
    }, ...__VLS_functionalComponentArgsRest(__VLS_17));
    __VLS_19.slots.default;
    (__VLS_ctx.CATEGORY_LABELS[__VLS_ctx.hardware.category] ?? __VLS_ctx.hardware.category);
    var __VLS_19;
}
if (__VLS_ctx.hardware) {
    __VLS_asFunctionalElement(__VLS_intrinsicElements.main, __VLS_intrinsicElements.main)({
        ...{ class: "content" },
    });
    if (__VLS_ctx.hardware.latest_stats) {
        __VLS_asFunctionalElement(__VLS_intrinsicElements.section, __VLS_intrinsicElements.section)({
            ...{ class: "stats-row" },
        });
        const __VLS_20 = {}.ElCard;
        /** @type {[typeof __VLS_components.ElCard, typeof __VLS_components.elCard, typeof __VLS_components.ElCard, typeof __VLS_components.elCard, ]} */ ;
        // @ts-ignore
        const __VLS_21 = __VLS_asFunctionalComponent(__VLS_20, new __VLS_20({
            ...{ class: "stat-card" },
        }));
        const __VLS_22 = __VLS_21({
            ...{ class: "stat-card" },
        }, ...__VLS_functionalComponentArgsRest(__VLS_21));
        __VLS_23.slots.default;
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "stat-label" },
        });
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "stat-value emphasize" },
        });
        (__VLS_ctx.formatPrice(__VLS_ctx.hardware.latest_stats.median_price));
        var __VLS_23;
        const __VLS_24 = {}.ElCard;
        /** @type {[typeof __VLS_components.ElCard, typeof __VLS_components.elCard, typeof __VLS_components.ElCard, typeof __VLS_components.elCard, ]} */ ;
        // @ts-ignore
        const __VLS_25 = __VLS_asFunctionalComponent(__VLS_24, new __VLS_24({
            ...{ class: "stat-card" },
        }));
        const __VLS_26 = __VLS_25({
            ...{ class: "stat-card" },
        }, ...__VLS_functionalComponentArgsRest(__VLS_25));
        __VLS_27.slots.default;
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "stat-label" },
        });
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "stat-value" },
        });
        (__VLS_ctx.formatPrice(__VLS_ctx.hardware.latest_stats.min_price));
        __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
            ...{ class: "sep" },
        });
        (__VLS_ctx.formatPrice(__VLS_ctx.hardware.latest_stats.max_price));
        var __VLS_27;
        const __VLS_28 = {}.ElCard;
        /** @type {[typeof __VLS_components.ElCard, typeof __VLS_components.elCard, typeof __VLS_components.ElCard, typeof __VLS_components.elCard, ]} */ ;
        // @ts-ignore
        const __VLS_29 = __VLS_asFunctionalComponent(__VLS_28, new __VLS_28({
            ...{ class: "stat-card" },
        }));
        const __VLS_30 = __VLS_29({
            ...{ class: "stat-card" },
        }, ...__VLS_functionalComponentArgsRest(__VLS_29));
        __VLS_31.slots.default;
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "stat-label" },
        });
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "stat-value" },
        });
        (__VLS_ctx.hardware.latest_stats.sample_count);
        var __VLS_31;
        const __VLS_32 = {}.ElCard;
        /** @type {[typeof __VLS_components.ElCard, typeof __VLS_components.elCard, typeof __VLS_components.ElCard, typeof __VLS_components.elCard, ]} */ ;
        // @ts-ignore
        const __VLS_33 = __VLS_asFunctionalComponent(__VLS_32, new __VLS_32({
            ...{ class: "stat-card" },
        }));
        const __VLS_34 = __VLS_33({
            ...{ class: "stat-card" },
        }, ...__VLS_functionalComponentArgsRest(__VLS_33));
        __VLS_35.slots.default;
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "stat-label" },
        });
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "stat-value" },
        });
        const __VLS_36 = {}.ElTag;
        /** @type {[typeof __VLS_components.ElTag, typeof __VLS_components.elTag, typeof __VLS_components.ElTag, typeof __VLS_components.elTag, ]} */ ;
        // @ts-ignore
        const __VLS_37 = __VLS_asFunctionalComponent(__VLS_36, new __VLS_36({
            type: (__VLS_ctx.levelTagType(__VLS_ctx.hardware.latest_stats.price_level)),
            round: true,
        }));
        const __VLS_38 = __VLS_37({
            type: (__VLS_ctx.levelTagType(__VLS_ctx.hardware.latest_stats.price_level)),
            round: true,
        }, ...__VLS_functionalComponentArgsRest(__VLS_37));
        __VLS_39.slots.default;
        (__VLS_ctx.LEVEL_LABELS[__VLS_ctx.hardware.latest_stats.price_level]);
        var __VLS_39;
        var __VLS_35;
    }
    const __VLS_40 = {}.ElCard;
    /** @type {[typeof __VLS_components.ElCard, typeof __VLS_components.elCard, typeof __VLS_components.ElCard, typeof __VLS_components.elCard, ]} */ ;
    // @ts-ignore
    const __VLS_41 = __VLS_asFunctionalComponent(__VLS_40, new __VLS_40({
        ...{ class: "chart-card" },
    }));
    const __VLS_42 = __VLS_41({
        ...{ class: "chart-card" },
    }, ...__VLS_functionalComponentArgsRest(__VLS_41));
    __VLS_43.slots.default;
    {
        const { header: __VLS_thisSlot } = __VLS_43.slots;
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "chart-header" },
        });
        __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({});
        const __VLS_44 = {}.ElRadioGroup;
        /** @type {[typeof __VLS_components.ElRadioGroup, typeof __VLS_components.elRadioGroup, typeof __VLS_components.ElRadioGroup, typeof __VLS_components.elRadioGroup, ]} */ ;
        // @ts-ignore
        const __VLS_45 = __VLS_asFunctionalComponent(__VLS_44, new __VLS_44({
            ...{ 'onChange': {} },
            modelValue: (__VLS_ctx.selectedDays),
            size: "small",
        }));
        const __VLS_46 = __VLS_45({
            ...{ 'onChange': {} },
            modelValue: (__VLS_ctx.selectedDays),
            size: "small",
        }, ...__VLS_functionalComponentArgsRest(__VLS_45));
        let __VLS_48;
        let __VLS_49;
        let __VLS_50;
        const __VLS_51 = {
            onChange: (__VLS_ctx.loadTrend)
        };
        __VLS_47.slots.default;
        const __VLS_52 = {}.ElRadioButton;
        /** @type {[typeof __VLS_components.ElRadioButton, typeof __VLS_components.elRadioButton, typeof __VLS_components.ElRadioButton, typeof __VLS_components.elRadioButton, ]} */ ;
        // @ts-ignore
        const __VLS_53 = __VLS_asFunctionalComponent(__VLS_52, new __VLS_52({
            value: (7),
        }));
        const __VLS_54 = __VLS_53({
            value: (7),
        }, ...__VLS_functionalComponentArgsRest(__VLS_53));
        __VLS_55.slots.default;
        var __VLS_55;
        const __VLS_56 = {}.ElRadioButton;
        /** @type {[typeof __VLS_components.ElRadioButton, typeof __VLS_components.elRadioButton, typeof __VLS_components.ElRadioButton, typeof __VLS_components.elRadioButton, ]} */ ;
        // @ts-ignore
        const __VLS_57 = __VLS_asFunctionalComponent(__VLS_56, new __VLS_56({
            value: (30),
        }));
        const __VLS_58 = __VLS_57({
            value: (30),
        }, ...__VLS_functionalComponentArgsRest(__VLS_57));
        __VLS_59.slots.default;
        var __VLS_59;
        const __VLS_60 = {}.ElRadioButton;
        /** @type {[typeof __VLS_components.ElRadioButton, typeof __VLS_components.elRadioButton, typeof __VLS_components.ElRadioButton, typeof __VLS_components.elRadioButton, ]} */ ;
        // @ts-ignore
        const __VLS_61 = __VLS_asFunctionalComponent(__VLS_60, new __VLS_60({
            value: (90),
        }));
        const __VLS_62 = __VLS_61({
            value: (90),
        }, ...__VLS_functionalComponentArgsRest(__VLS_61));
        __VLS_63.slots.default;
        var __VLS_63;
        var __VLS_47;
    }
    if (__VLS_ctx.trendLoading) {
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "chart-loading" },
        });
        const __VLS_64 = {}.ElSkeleton;
        /** @type {[typeof __VLS_components.ElSkeleton, typeof __VLS_components.elSkeleton, ]} */ ;
        // @ts-ignore
        const __VLS_65 = __VLS_asFunctionalComponent(__VLS_64, new __VLS_64({
            rows: (6),
            animated: true,
        }));
        const __VLS_66 = __VLS_65({
            rows: (6),
            animated: true,
        }, ...__VLS_functionalComponentArgsRest(__VLS_65));
    }
    else if (!__VLS_ctx.trendData?.trend.length) {
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "chart-empty" },
        });
        const __VLS_68 = {}.ElEmpty;
        /** @type {[typeof __VLS_components.ElEmpty, typeof __VLS_components.elEmpty, ]} */ ;
        // @ts-ignore
        const __VLS_69 = __VLS_asFunctionalComponent(__VLS_68, new __VLS_68({
            description: "暂无历史走势数据",
        }));
        const __VLS_70 = __VLS_69({
            description: "暂无历史走势数据",
        }, ...__VLS_functionalComponentArgsRest(__VLS_69));
    }
    else {
        /** @type {[typeof PriceTrendChart, ]} */ ;
        // @ts-ignore
        const __VLS_72 = __VLS_asFunctionalComponent(PriceTrendChart, new PriceTrendChart({
            trend: (__VLS_ctx.trendData.trend),
        }));
        const __VLS_73 = __VLS_72({
            trend: (__VLS_ctx.trendData.trend),
        }, ...__VLS_functionalComponentArgsRest(__VLS_72));
    }
    var __VLS_43;
}
else if (!__VLS_ctx.loading) {
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "not-found" },
    });
    const __VLS_75 = {}.ElResult;
    /** @type {[typeof __VLS_components.ElResult, typeof __VLS_components.elResult, typeof __VLS_components.ElResult, typeof __VLS_components.elResult, ]} */ ;
    // @ts-ignore
    const __VLS_76 = __VLS_asFunctionalComponent(__VLS_75, new __VLS_75({
        icon: "warning",
        title: "硬件不存在",
        subTitle: "请返回首页重新选择",
    }));
    const __VLS_77 = __VLS_76({
        icon: "warning",
        title: "硬件不存在",
        subTitle: "请返回首页重新选择",
    }, ...__VLS_functionalComponentArgsRest(__VLS_76));
    __VLS_78.slots.default;
    {
        const { extra: __VLS_thisSlot } = __VLS_78.slots;
        const __VLS_79 = {}.ElButton;
        /** @type {[typeof __VLS_components.ElButton, typeof __VLS_components.elButton, typeof __VLS_components.ElButton, typeof __VLS_components.elButton, ]} */ ;
        // @ts-ignore
        const __VLS_80 = __VLS_asFunctionalComponent(__VLS_79, new __VLS_79({
            ...{ 'onClick': {} },
        }));
        const __VLS_81 = __VLS_80({
            ...{ 'onClick': {} },
        }, ...__VLS_functionalComponentArgsRest(__VLS_80));
        let __VLS_83;
        let __VLS_84;
        let __VLS_85;
        const __VLS_86 = {
            onClick: (__VLS_ctx.goBack)
        };
        __VLS_82.slots.default;
        var __VLS_82;
    }
    var __VLS_78;
}
/** @type {__VLS_StyleScopedClasses['detail-page']} */ ;
/** @type {__VLS_StyleScopedClasses['detail-header']} */ ;
/** @type {__VLS_StyleScopedClasses['header-inner']} */ ;
/** @type {__VLS_StyleScopedClasses['back-btn']} */ ;
/** @type {__VLS_StyleScopedClasses['title-wrap']} */ ;
/** @type {__VLS_StyleScopedClasses['title']} */ ;
/** @type {__VLS_StyleScopedClasses['subtitle']} */ ;
/** @type {__VLS_StyleScopedClasses['content']} */ ;
/** @type {__VLS_StyleScopedClasses['stats-row']} */ ;
/** @type {__VLS_StyleScopedClasses['stat-card']} */ ;
/** @type {__VLS_StyleScopedClasses['stat-label']} */ ;
/** @type {__VLS_StyleScopedClasses['stat-value']} */ ;
/** @type {__VLS_StyleScopedClasses['emphasize']} */ ;
/** @type {__VLS_StyleScopedClasses['stat-card']} */ ;
/** @type {__VLS_StyleScopedClasses['stat-label']} */ ;
/** @type {__VLS_StyleScopedClasses['stat-value']} */ ;
/** @type {__VLS_StyleScopedClasses['sep']} */ ;
/** @type {__VLS_StyleScopedClasses['stat-card']} */ ;
/** @type {__VLS_StyleScopedClasses['stat-label']} */ ;
/** @type {__VLS_StyleScopedClasses['stat-value']} */ ;
/** @type {__VLS_StyleScopedClasses['stat-card']} */ ;
/** @type {__VLS_StyleScopedClasses['stat-label']} */ ;
/** @type {__VLS_StyleScopedClasses['stat-value']} */ ;
/** @type {__VLS_StyleScopedClasses['chart-card']} */ ;
/** @type {__VLS_StyleScopedClasses['chart-header']} */ ;
/** @type {__VLS_StyleScopedClasses['chart-loading']} */ ;
/** @type {__VLS_StyleScopedClasses['chart-empty']} */ ;
/** @type {__VLS_StyleScopedClasses['not-found']} */ ;
var __VLS_dollars;
const __VLS_self = (await import('vue')).defineComponent({
    setup() {
        return {
            PriceTrendChart: PriceTrendChart,
            CATEGORY_LABELS: CATEGORY_LABELS,
            LEVEL_LABELS: LEVEL_LABELS,
            loading: loading,
            trendLoading: trendLoading,
            hardware: hardware,
            trendData: trendData,
            selectedDays: selectedDays,
            goBack: goBack,
            levelTagType: levelTagType,
            formatPrice: formatPrice,
            loadTrend: loadTrend,
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
