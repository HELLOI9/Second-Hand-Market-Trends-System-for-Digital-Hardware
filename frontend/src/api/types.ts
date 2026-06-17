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
  validation_rule: string | null
  is_active: boolean
  latest_stats: DailyStats | null
  // 全站最近一轮采集日期（锚点）
  latest_run_date?: string | null
  // latest_stats 是否为旧数据（早于锚点日，本轮未采到）
  stats_is_stale?: boolean
}

export interface HardwareCreatePayload {
  name: string
  category: string
  search_keywords: string[]
  validation_rule?: string | null
  cold_start: boolean
}

export interface HardwareUpdatePayload {
  name?: string
  category?: string
  search_keywords?: string[]
  validation_rule?: string | null
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

export interface CookieStatus {
  exists: boolean
  age_days: number | null
  count: number
}

export interface ConfigData {
  llm_base_url: string
  llm_model: string
  llm_api_key: string
  llm_validation_enabled: boolean
  crawler_schedule: string
  crawler_schedule_times: string
  frontend_port: number
  cors_origins: string
  admin_token_hint: string
  postgres_user: string
  postgres_password: string
  postgres_db: string
  postgres_host: string
  postgres_port: number
  database_url_preview: string
}

export interface HwCrawlProgress {
  phase: string
  percent: number
  processed: number
  total: number
  current_hardware: string | null
  crawl_percent: number
  crawl_done: number
  crawl_total: number
  llm_percent: number
  llm_done: number
  llm_total: number
  llm_current_hardware: string | null
  llm_current_done: number | null
  llm_current_total: number | null
}

export interface HwCrawlProgressResponse {
  running: boolean
  run_id: number | null
  progress: HwCrawlProgress | null
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
      // crawl progress
      crawl_percent: number
      crawl_done: number
      crawl_total: number
      // LLM validation progress
      llm_percent: number
      llm_done: number
      llm_total: number
      llm_current_hardware: string | null
      llm_current_done: number | null
      llm_current_total: number | null
    } | null
  } | null
  active_hw_crawls: Array<{
    hardware_id: number
    hardware_name: string
    run_id: number
    progress: HwCrawlProgress | null
  }>
  alerts: Array<{
    level: 'warning' | 'error'
    hardware?: string
    hardware_id?: number
    message: string
  }>
}
