import axios from 'axios';
const http = axios.create({
    baseURL: '/api',
    timeout: 30000,
});
export const hardwareApi = {
    /** 获取所有硬件列表（含最新统计），按分类分组 */
    list() {
        return http.get('/hardware').then(r => r.data);
    },
    /** 获取单个硬件详情 + 最新统计 */
    detail(id) {
        return http.get(`/hardware/${id}`).then(r => r.data);
    },
    /** 获取价格走势 */
    trend(id, days = 30) {
        return http.get(`/hardware/${id}/trend`, { params: { days } }).then(r => r.data);
    },
};
export const crawlerApi = {
    /** 获取爬虫状态 */
    status() {
        return http.get('/crawler/status').then(r => r.data);
    },
    /** 手动触发爬取 */
    run() {
        return http.post('/crawler/run').then();
    },
};
