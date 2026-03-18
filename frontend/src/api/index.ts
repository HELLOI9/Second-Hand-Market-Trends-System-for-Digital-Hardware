import axios from 'axios'
import type {
  HardwareDetail,
  TrendResponse,
  CrawlerStatus,
} from './types'

const http = axios.create({
  baseURL: '/api',
  timeout: 30_000,
})

export const hardwareApi = {
  /** 获取所有硬件列表（含最新统计），按分类分组 */
  list(): Promise<Record<string, HardwareDetail[]>> {
    return http.get<Record<string, HardwareDetail[]>>('/hardware').then(r => r.data)
  },

  /** 获取单个硬件详情 + 最新统计 */
  detail(id: number): Promise<HardwareDetail> {
    return http.get<HardwareDetail>(`/hardware/${id}`).then(r => r.data)
  },

  /** 获取价格走势 */
  trend(id: number, days: 7 | 30 | 90 = 30): Promise<TrendResponse> {
    return http.get<TrendResponse>(`/hardware/${id}/trend`, { params: { days } }).then(r => r.data)
  },
}

export const crawlerApi = {
  /** 获取爬虫状态 */
  status(): Promise<CrawlerStatus> {
    return http.get<CrawlerStatus>('/crawler/status').then(r => r.data)
  },

  /** 手动触发爬取 */
  run(): Promise<void> {
    return http.post('/crawler/run').then()
  },
}
