import axios from 'axios'
import type {
  AlertPayload,
  CrawlerHealth,
  CrawlerRunResponse,
  HardwareDetail,
  HardwareSample,
  DealItem,
  HardwareCreatePayload,
  HardwareUpdatePayload,
  PriceAlert,
  TrendResponse,
  CrawlerStatus,
} from './types'

const http = axios.create({
  baseURL: '/api',
  timeout: 30_000,
})

function adminHeaders(token: string) {
  return {
    headers: {
      'X-Admin-Token': token,
    },
  }
}

export const hardwareApi = {
  /** 获取所有订阅对象列表（含最新统计） */
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

  samples(id: number, limit = 8): Promise<HardwareSample[]> {
    return http.get<HardwareSample[]>(`/hardware/${id}/samples`, { params: { limit } }).then(r => r.data)
  },

  adminList(token: string): Promise<HardwareDetail[]> {
    return http.get<HardwareDetail[]>('/hardware/admin', adminHeaders(token)).then(r => r.data)
  },

  create(token: string, payload: HardwareCreatePayload): Promise<HardwareDetail> {
    return http.post<HardwareDetail>('/hardware', payload, adminHeaders(token)).then(r => r.data)
  },

  update(token: string, id: number, payload: HardwareUpdatePayload): Promise<HardwareDetail> {
    return http.patch<HardwareDetail>(`/hardware/${id}`, payload, adminHeaders(token)).then(r => r.data)
  },

  remove(token: string, id: number): Promise<void> {
    return http.delete(`/hardware/${id}`, adminHeaders(token)).then()
  },

  restore(token: string, id: number): Promise<void> {
    return http.post(`/hardware/${id}/restore`, null, adminHeaders(token)).then()
  },

  crawl(token: string, id: number): Promise<void> {
    return http.post(`/hardware/${id}/crawl`, null, adminHeaders(token)).then()
  },
}

export const crawlerApi = {
  /** 获取爬虫状态 */
  status(): Promise<CrawlerStatus> {
    return http.get<CrawlerStatus>('/crawler/status').then(r => r.data)
  },

  /** 手动触发爬取 */
  run(force = false): Promise<CrawlerRunResponse> {
    return http.post<CrawlerRunResponse>('/crawler/run', null, { params: { force } }).then(r => r.data)
  },

  /** 暂停当前爬取 */
  pause(): Promise<CrawlerRunResponse> {
    return http.post<CrawlerRunResponse>('/crawler/pause').then(r => r.data)
  },
}

export const dealsApi = {
  today(limit = 20): Promise<DealItem[]> {
    return http.get<DealItem[]>('/deals/today', { params: { limit } }).then(r => r.data)
  },
}

export const alertsApi = {
  list(channelTarget?: string): Promise<PriceAlert[]> {
    return http.get<PriceAlert[]>('/alerts', {
      params: channelTarget ? { channel_target: channelTarget } : undefined,
    }).then(r => r.data)
  },

  create(payload: AlertPayload): Promise<PriceAlert> {
    return http.post<PriceAlert>('/alerts', payload).then(r => r.data)
  },

  update(id: number, payload: Partial<AlertPayload>): Promise<PriceAlert> {
    return http.patch<PriceAlert>(`/alerts/${id}`, payload).then(r => r.data)
  },

  remove(id: number): Promise<void> {
    return http.delete(`/alerts/${id}`).then()
  },

  test(id: number): Promise<{ status: 'sent' | 'failed' }> {
    return http.post<{ status: 'sent' | 'failed' }>(`/alerts/${id}/test`).then(r => r.data)
  },
}

export const healthApi = {
  crawler(): Promise<CrawlerHealth> {
    return http.get<CrawlerHealth>('/health/crawler').then(r => r.data)
  },
}
