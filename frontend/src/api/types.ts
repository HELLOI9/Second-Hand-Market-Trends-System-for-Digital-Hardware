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
  search_keywords: string[]
  is_active: boolean
  latest_stats: DailyStats | null
}

export interface HardwareCreatePayload {
  name: string
  category: string
  search_keywords: string[]
  cold_start: boolean
}

export interface HardwareUpdatePayload {
  name?: string
  category?: string
  search_keywords?: string[]
  is_active?: boolean
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

export interface HardwareSample {
  id: number
  price: number
  title: string
  item_url: string | null
  area: string | null
  seller: string | null
  image_url: string | null
  publish_time: string | null
  snapshot_date: string
}

export interface CrawlerStatus {
  last_run_date: string | null
  last_run_success: number
  last_run_failed: number
}

export interface CrawlerRunResponse {
  status: 'started' | 'running' | 'paused' | 'idle' | string
  summary: {
    message?: string
    force?: boolean
    active_run_id?: number
    active_status?: string
    [key: string]: unknown
  }
}

export interface DealItem {
  hardware_id: number
  hardware_name: string
  category: string
  price: number
  baseline_median: number
  discount_rate: number
  title: string
  item_url: string | null
  area: string | null
  seller: string | null
  image_url: string | null
  snapshot_date: string
}

export type AlertScopeType = 'hardware' | 'all'
export type AlertRuleType = 'below_price' | 'below_median_pct' | 'level_low'
export type AlertChannel = 'webhook' | 'telegram'

export interface PriceAlert {
  id: number
  scope_type: AlertScopeType
  scope_value: string | null
  rule_type: AlertRuleType
  threshold: number | null
  channel: AlertChannel
  channel_target: string
  is_active: boolean
  last_fired_at: string | null
  cooldown_hours: number
  created_at: string
}

export interface AlertPayload {
  scope_type: AlertScopeType
  scope_value: string | null
  rule_type: AlertRuleType
  threshold: number | null
  channel: AlertChannel
  channel_target: string
  cooldown_hours: number
  is_active: boolean
}

export interface CrawlRunDetail {
  hardware_id?: number
  hardware?: string
  status?: string
  message?: string
  count?: number
  raw?: number
  saved?: number
  validated?: number
  valid?: number
  invalid?: number
  validation_failed?: number
  median_price?: number | null
}

export interface CrawlerHealth {
  status: 'ok' | 'warning'
  cookie_exists: boolean
  cookie_age_days: number | null
  active_hardware: number
  run_count: number
  latest_run: {
    id: number
    status: string
    started_at: string
    ended_at: string | null
    success: number
    failed: number
    skipped: number
    details: CrawlRunDetail[]
    progress: {
      phase: string
      percent: number
      processed: number
      total: number
      current_hardware: string | null
      validation_total?: number
      validation_processed?: number
      validation_pending?: number
    } | null
  } | null
  alerts: Array<{
    level: 'warning' | 'error'
    hardware?: string
    hardware_id?: number
    message: string
  }>
}
