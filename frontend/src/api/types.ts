export type PriceLevel = 'low' | 'normal' | 'high'

export interface HardwareListItem {
  id: number
  name: string
  category: string
}

export interface DailyStats {
  stat_date: string
  median_price: number
  avg_price: number
  min_price: number
  max_price: number
  sample_count: number
  price_level: PriceLevel
}

export interface HardwareDetail {
  id: number
  name: string
  category: string
  latest_stats: DailyStats | null
}

export interface TrendPoint {
  date: string
  median_price: number
  avg_price: number
  min_price: number
  max_price: number
  sample_count: number
  price_level: PriceLevel
}

export interface TrendResponse {
  hardware_id: number
  hardware_name: string
  days: number
  trend: TrendPoint[]
}

export interface CrawlerStatus {
  last_run_date: string | null
  last_run_success: number
  last_run_failed: number
}
