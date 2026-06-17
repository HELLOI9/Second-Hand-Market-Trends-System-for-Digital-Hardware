<template>
  <OpsLayout active-nav="config">
    <template #header>
      <header class="ops-header">
        <div class="ops-header-copy">
          <h1 class="ops-header-title"><el-icon><Tools /></el-icon>系统配置</h1>
          <p class="ops-header-subtitle">管理 LLM、调度、访问等运行时配置项。修改后点击右上角「保存」生效。</p>
        </div>
        <el-button type="primary" :loading="saving" @click="save">保存配置</el-button>
      </header>
    </template>

    <div v-if="loadError" class="cfg-error">
      <el-alert type="error" :title="loadError" show-icon :closable="false" />
    </div>

    <el-form v-else v-loading="loading" class="cfg-body" label-position="left" label-width="auto">

      <!-- LLM 配置 -->
      <section class="cfg-panel">
        <div class="cfg-panel-head">
          <div class="cfg-panel-head-row">
            <div>
              <h2>LLM 配置</h2>
              <p>用于价格校验的大语言模型接入配置，支持 OpenAI 官方及任何兼容接口。</p>
            </div>
            <div class="cfg-test-area">
              <span v-if="llmTest.status !== 'idle'" class="cfg-test-msg" :class="llmTest.status">
                {{ llmTest.message }}
              </span>
              <el-button size="small" :loading="llmTest.status === 'testing'" @click="runLlmTest">测试连接</el-button>
            </div>
          </div>
        </div>
        <div class="cfg-grid">
          <el-form-item label="API 基础地址">
            <el-input v-model="form.llm_base_url" placeholder="https://api.openai.com/v1" clearable />
            <div class="cfg-hint">环境变量：<code>LLM_BASE_URL</code></div>
          </el-form-item>
          <el-form-item label="模型名称">
            <el-input v-model="form.llm_model" placeholder="gpt-4o-mini" clearable />
            <div class="cfg-hint">环境变量：<code>LLM_MODEL</code></div>
          </el-form-item>
          <el-form-item label="API 密钥" class="cfg-span-full">
            <el-input
              v-model="form.llm_api_key"
              :type="showApiKey ? 'text' : 'password'"
              placeholder="sk-... （本地模型可留空）"
              clearable
            >
              <template #suffix>
                <el-icon class="key-toggle" @click="showApiKey = !showApiKey">
                  <component :is="showApiKey ? Hide : View" />
                </el-icon>
              </template>
            </el-input>
            <div class="cfg-hint">环境变量：<code>LLM_API_KEY</code></div>
          </el-form-item>
          <el-form-item label="LLM 价格校验" class="cfg-span-full">
            <div class="cfg-switch-row">
              <el-switch v-model="form.llm_validation_enabled" />
              <span class="cfg-switch-label">{{ form.llm_validation_enabled ? '已启用' : '已禁用' }}</span>
              <span class="cfg-switch-desc">禁用后跳过 LLM 校验步骤，加快采集速度但降低数据准确性。</span>
            </div>
          </el-form-item>
        </div>
      </section>

      <!-- 数据库配置 -->
      <section class="cfg-panel">
        <div class="cfg-panel-head">
          <div class="cfg-panel-head-row">
            <div>
              <h2>数据库配置</h2>
              <p>PostgreSQL 连接信息。<strong>修改后需重启容器才能生效，当前运行中的连接不受影响。</strong></p>
            </div>
            <div class="cfg-test-area">
              <span v-if="dbTest.status !== 'idle'" class="cfg-test-msg" :class="dbTest.status">
                {{ dbTest.message }}
              </span>
              <el-button size="small" :loading="dbTest.status === 'testing'" @click="runDbTest">测试连接</el-button>
            </div>
          </div>
        </div>
        <el-alert
          type="warning"
          title="数据库配置修改后需重启后端服务（docker compose restart backend）才能生效。"
          :closable="false"
          show-icon
          class="cfg-db-warning"
        />
        <div class="cfg-grid">
          <el-form-item label="主机地址">
            <el-input v-model="form.postgres_host" placeholder="localhost" clearable />
            <div class="cfg-hint">环境变量：<code>POSTGRES_HOST</code></div>
          </el-form-item>
          <el-form-item label="端口">
            <el-input-number v-model="form.postgres_port" :min="1" :max="65535" style="width:100%" />
            <div class="cfg-hint">环境变量：<code>POSTGRES_PORT</code></div>
          </el-form-item>
          <el-form-item label="数据库名">
            <el-input v-model="form.postgres_db" placeholder="market" clearable />
            <div class="cfg-hint">环境变量：<code>POSTGRES_DB</code></div>
          </el-form-item>
          <el-form-item label="用户名">
            <el-input v-model="form.postgres_user" placeholder="market" clearable />
            <div class="cfg-hint">环境变量：<code>POSTGRES_USER</code></div>
          </el-form-item>
          <el-form-item label="密码" class="cfg-span-full">
            <el-input
              v-model="form.postgres_password"
              :type="showDbPassword ? 'text' : 'password'"
              placeholder="数据库密码"
              clearable
            >
              <template #suffix>
                <el-icon class="key-toggle" @click="showDbPassword = !showDbPassword">
                  <component :is="showDbPassword ? Hide : View" />
                </el-icon>
              </template>
            </el-input>
            <div class="cfg-hint">环境变量：<code>POSTGRES_PASSWORD</code></div>
          </el-form-item>
          <el-form-item label="连接串预览（只读）" class="cfg-span-full">
            <el-input :value="form.database_url_preview" disabled />
            <div class="cfg-hint">保存后自动更新 <code>DATABASE_URL</code></div>
          </el-form-item>
        </div>
      </section>

      <!-- 调度配置 -->
      <section class="cfg-panel">
        <div class="cfg-panel-head">
          <h2>调度配置</h2>
          <p>设置每天自动采集的时间点，可添加多个，每天各执行一次。</p>
        </div>
        <div class="cfg-grid">
          <el-form-item label="采集时间点" class="cfg-span-full">
            <div class="cfg-schedule-editor">
              <div class="cfg-schedule-tags">
                <el-tag
                  v-for="t in scheduleTimes"
                  :key="t"
                  closable
                  class="cfg-schedule-tag"
                  @close="removeScheduleTime(t)"
                >
                  {{ t }}
                </el-tag>
                <span v-if="scheduleTimes.length === 0" class="cfg-schedule-empty">暂无时间点，请添加</span>
              </div>
              <div class="cfg-schedule-add">
                <el-time-picker
                  v-model="newTimeValue"
                  format="HH:mm"
                  placeholder="选择时间"
                  :clearable="false"
                  style="width: 140px"
                  @change="addScheduleTime"
                />
                <el-button @click="addScheduleTime">添加</el-button>
              </div>
            </div>
          </el-form-item>
        </div>
      </section>

      <!-- 访问配置 -->
      <section class="cfg-panel">
        <div class="cfg-panel-head">
          <h2>访问配置</h2>
          <p>前端端口和跨域来源白名单，留空时自动根据端口生成。</p>
        </div>
        <div class="cfg-grid">
          <el-form-item label="前端端口">
            <el-input-number v-model="form.frontend_port" :min="1" :max="65535" style="width:100%" />
            <div class="cfg-hint">环境变量：<code>FRONTEND_PORT</code></div>
          </el-form-item>
          <el-form-item label="CORS 允许来源">
            <el-input v-model="form.cors_origins" placeholder="留空自动根据端口生成" clearable />
            <div class="cfg-hint">环境变量：<code>CORS_ORIGINS</code> · 多个来源用逗号分隔</div>
          </el-form-item>
        </div>
      </section>

      <!-- 闲鱼 Cookies -->
      <section class="cfg-panel">
        <div class="cfg-panel-head">
          <div class="cfg-panel-head-row">
            <div>
              <h2>闲鱼 Cookies</h2>
              <p>爬虫使用 <code>cookies.json</code> 进行登录认证。将从浏览器导出的 Cookie JSON 数组粘贴到下方，保存后立即生效。</p>
            </div>
            <div class="cfg-cookie-status" :class="cookieStatus?.exists ? 'status-ok' : 'status-missing'">
              <span v-if="cookieStatus === null" class="cfg-cookie-badge">加载中…</span>
              <template v-else-if="cookieStatus.exists">
                <span class="cfg-cookie-badge ok">已配置</span>
                <span class="cfg-cookie-meta">{{ cookieStatus.count }} 条 · {{ cookieStatus.age_days === 0 ? '今日更新' : `${cookieStatus.age_days} 天前` }}</span>
              </template>
              <span v-else class="cfg-cookie-badge missing">未配置</span>
            </div>
          </div>
        </div>
        <div class="cfg-grid">
          <el-form-item label="Cookie JSON" class="cfg-span-full">
            <el-input
              v-model="cookieInput"
              type="textarea"
              :rows="8"
              placeholder='粘贴 JSON 数组，例如 [{"name":"cookie1","value":"...","domain":".goofish.com",...}]'
              class="cfg-cookie-textarea"
            />
            <div class="cfg-hint">支持浏览器插件（Cookie-Editor、EditThisCookie 等）导出的 JSON 格式。<strong>不要</strong>粘贴 Netscape 文本格式。</div>
          </el-form-item>
          <div class="cfg-cookie-actions cfg-span-full">
            <el-button type="primary" :loading="cookieSaving" :disabled="!cookieInput.trim()" @click="saveCookies">保存 Cookies</el-button>
            <el-button type="danger" plain :loading="cookieDeleting" :disabled="!cookieStatus?.exists" @click="deleteCookies">清除 Cookies</el-button>
          </div>
        </div>
      </section>

      <!-- 只读信息 -->
      <section class="cfg-panel">
        <div class="cfg-panel-head">
          <h2>只读信息</h2>
          <p>这些字段无法通过界面修改，请直接编辑 <code>.env</code> 文件后重启生效。</p>
        </div>
        <div class="cfg-grid">
          <el-form-item label="管理令牌">
            <el-input :value="form.admin_token_hint" disabled />
            <div class="cfg-hint">环境变量：<code>ADMIN_TOKEN</code> · 修改令牌后需同步更新前端 ADMIN_TOKEN 常量。</div>
          </el-form-item>
        </div>
      </section>

    </el-form>
  </OpsLayout>
</template>

<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Hide, Tools, View } from '@element-plus/icons-vue'
import { configApi } from '@/api'
import type { ConfigData, CookieStatus } from '@/api/types'
import OpsLayout from '@/components/OpsLayout.vue'

const ADMIN_TOKEN = 'dev-admin-token'

const loading = ref(false)
const saving = ref(false)
const loadError = ref('')
const showApiKey = ref(false)
const showDbPassword = ref(false)
const original = ref<ConfigData | null>(null)

type TestStatus = 'idle' | 'testing' | 'ok' | 'error'
const llmTest = reactive<{ status: TestStatus; message: string }>({ status: 'idle', message: '' })
const dbTest = reactive<{ status: TestStatus; message: string }>({ status: 'idle', message: '' })

const cookieStatus = ref<CookieStatus | null>(null)
const cookieInput = ref('')
const cookieSaving = ref(false)
const cookieDeleting = ref(false)

// Schedule times — derived from form.crawler_schedule_times ("HH:MM,HH:MM,...")
const newTimeValue = ref<Date | null>(null)

const scheduleTimes = computed<string[]>(() => {
  const raw = form.crawler_schedule_times?.trim()
  if (!raw) return []
  return raw.split(',').map(t => t.trim()).filter(Boolean)
})

function _dateToHHMM(d: Date): string {
  const h = String(d.getHours()).padStart(2, '0')
  const m = String(d.getMinutes()).padStart(2, '0')
  return `${h}:${m}`
}

function addScheduleTime() {
  if (!newTimeValue.value) return
  const t = _dateToHHMM(newTimeValue.value)
  const current = scheduleTimes.value
  if (current.includes(t)) { ElMessage.warning(`${t} 已存在`); return }
  form.crawler_schedule_times = [...current, t].join(',')
  newTimeValue.value = null
}

function removeScheduleTime(time: string) {
  form.crawler_schedule_times = scheduleTimes.value.filter(t => t !== time).join(',')
}

async function loadCookieStatus() {
  try {
    cookieStatus.value = await configApi.getCookies(ADMIN_TOKEN)
  } catch {
    // non-fatal
  }
}

async function saveCookies() {
  const raw = cookieInput.value.trim()
  if (!raw) { ElMessage.warning('请先粘贴 Cookie JSON'); return }
  cookieSaving.value = true
  try {
    cookieStatus.value = await configApi.uploadCookies(ADMIN_TOKEN, raw)
    cookieInput.value = ''
    ElMessage.success(`已保存 ${cookieStatus.value.count} 条 Cookie`)
  } catch (e: unknown) {
    const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? '保存失败'
    ElMessage.error(msg)
  } finally {
    cookieSaving.value = false
  }
}

async function deleteCookies() {
  try {
    await ElMessageBox.confirm('确认删除 cookies.json？爬虫将以未登录状态运行，可能无法获取完整数据。', '删除 Cookies', {
      confirmButtonText: '确认删除',
      cancelButtonText: '取消',
      type: 'warning',
    })
  } catch { return }
  cookieDeleting.value = true
  try {
    cookieStatus.value = await configApi.deleteCookies(ADMIN_TOKEN)
    ElMessage.success('Cookies 已删除')
  } catch {
    ElMessage.error('删除失败')
  } finally {
    cookieDeleting.value = false
  }
}

const LLM_FIELDS: (keyof ConfigData)[] = ['llm_base_url', 'llm_model', 'llm_api_key', 'llm_validation_enabled']
const DB_FIELDS: (keyof ConfigData)[] = ['postgres_host', 'postgres_port', 'postgres_user', 'postgres_password', 'postgres_db']

async function runLlmTest() {
  llmTest.status = 'testing'
  llmTest.message = ''
  try {
    const res = await configApi.testLlm(ADMIN_TOKEN)
    llmTest.status = res.ok ? 'ok' : 'error'
    llmTest.message = res.message
  } catch {
    llmTest.status = 'error'
    llmTest.message = '请求失败，请检查后端连接'
  }
}

async function runDbTest() {
  dbTest.status = 'testing'
  dbTest.message = ''
  try {
    const res = await configApi.testDb(ADMIN_TOKEN)
    dbTest.status = res.ok ? 'ok' : 'error'
    dbTest.message = res.message
  } catch {
    dbTest.status = 'error'
    dbTest.message = '请求失败，请检查后端连接'
  }
}

const form = reactive<ConfigData>({
  llm_base_url: '',
  llm_model: '',
  llm_api_key: '',
  llm_validation_enabled: true,
  crawler_schedule: '0 2 * * *',
  crawler_schedule_times: '02:00',
  frontend_port: 5173,
  cors_origins: '',
  admin_token_hint: '',
  postgres_user: 'market',
  postgres_password: '',
  postgres_db: 'market',
  postgres_host: 'localhost',
  postgres_port: 5432,
  database_url_preview: '',
})

async function load() {
  loading.value = true
  loadError.value = ''
  try {
    const [data] = await Promise.all([configApi.get(ADMIN_TOKEN), loadCookieStatus()])
    Object.assign(form, data)
    original.value = { ...data }
  } catch {
    loadError.value = '加载配置失败，请检查后端连接状态。'
  } finally {
    loading.value = false
  }
}

async function save() {
  if (!original.value) return
  const patch: Partial<ConfigData> = {}
  const readonlyKeys: (keyof ConfigData)[] = ['admin_token_hint', 'database_url_preview']
  const keys = (Object.keys(form) as (keyof ConfigData)[]).filter(k => !readonlyKeys.includes(k))
  for (const key of keys) {
    if ((form[key] as unknown) !== (original.value[key] as unknown)) {
      ;(patch as Record<string, unknown>)[key] = form[key]
    }
  }
  if (Object.keys(patch).length === 0) {
    ElMessage.info('没有检测到变更')
    return
  }
  const touchedLlm = LLM_FIELDS.some(k => k in patch)
  const touchedDb = DB_FIELDS.some(k => k in patch)
  saving.value = true
  try {
    const updated = await configApi.update(ADMIN_TOKEN, patch)
    Object.assign(form, updated)
    original.value = { ...updated }
    ElMessage.success('配置已保存')
    if (touchedLlm) runLlmTest()
    if (touchedDb) runDbTest()
  } catch {
    ElMessage.error('保存失败，请检查网络或令牌。')
  } finally {
    saving.value = false
  }
}

void load()
</script>

<style scoped>
.cfg-error {
  margin-bottom: 20px;
}

.cfg-body {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.cfg-panel {
  border: 1px solid var(--paper-border);
  border-radius: var(--radius-card);
  background: var(--surface-floating);
  box-shadow: var(--paper-shadow);
  overflow: hidden;
}

.cfg-panel-head {
  padding: 20px 24px 16px;
  border-bottom: 1px solid var(--paper-border);
  background: var(--paper-surface-soft);
}

.cfg-panel-head-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.cfg-test-area {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
  padding-top: 2px;
}

.cfg-test-msg {
  font-size: 12px;
  font-weight: 800;
}

.cfg-test-msg.ok {
  color: var(--el-color-success);
}

.cfg-test-msg.error {
  color: var(--el-color-danger);
}

.cfg-test-msg.testing {
  color: var(--paper-muted);
}

.cfg-panel-head h2 {
  font-size: 16px;
  font-weight: 900;
  color: var(--text-strong);
  margin: 0 0 4px;
}

.cfg-panel-head p {
  font-size: 13px;
  color: var(--paper-muted);
  margin: 0;
  line-height: 1.5;
}

.cfg-panel-head code {
  padding: 1px 5px;
  border-radius: 3px;
  background: var(--paper-border);
  font-family: monospace;
  font-size: 12px;
}

.cfg-db-warning {
  margin: 16px 24px 0;
  border-radius: var(--radius-control);
}

.cfg-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0;
  padding: 20px 24px;
  column-gap: 24px;
  row-gap: 20px;
}

.cfg-span-full {
  grid-column: 1 / -1;
}

.cfg-grid :deep(.el-form-item) {
  margin-bottom: 0;
}

.cfg-grid :deep(.el-form-item__label) {
  font-size: 13px;
  font-weight: 800;
  color: var(--paper-text);
  line-height: 32px;
  padding-bottom: 0;
  text-align: right;
  padding-right: 12px;
}

.cfg-hint {
  margin-top: 6px;
  color: var(--paper-muted);
  font-size: 12px;
  line-height: 1.5;
}

.cfg-hint code {
  padding: 1px 5px;
  border-radius: 3px;
  background: var(--paper-surface-soft);
  border: 1px solid var(--paper-border);
  font-family: monospace;
  font-size: 11px;
  color: var(--paper-text);
}

.cfg-switch-row {
  display: flex;
  align-items: center;
  gap: 12px;
  min-height: 32px;
}

.cfg-switch-label {
  font-size: 13px;
  font-weight: 800;
  color: var(--paper-text);
}

.cfg-switch-desc {
  font-size: 12px;
  color: var(--paper-muted);
}

.key-toggle {
  cursor: pointer;
  color: var(--paper-muted);
  transition: color 0.15s;
}

.key-toggle:hover {
  color: var(--text-strong);
}

@media (max-width: 720px) {
  .cfg-grid {
    grid-template-columns: 1fr;
    padding: 16px;
  }

  .cfg-span-full {
    grid-column: 1;
  }

  .cfg-panel-head {
    padding: 16px;
  }

  .cfg-db-warning {
    margin: 12px 16px 0;
  }

  .cfg-switch-row {
    flex-wrap: wrap;
  }

  .cfg-switch-desc {
    flex-basis: 100%;
  }
}

.cfg-cookie-status {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
  padding-top: 2px;
}

.cfg-cookie-badge {
  display: inline-flex;
  align-items: center;
  padding: 2px 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 800;
  background: var(--paper-surface-soft);
  color: var(--paper-muted);
}

.cfg-cookie-badge.ok {
  background: rgba(16, 185, 129, 0.1);
  color: #059669;
}

.cfg-cookie-badge.missing {
  background: rgba(239, 68, 68, 0.1);
  color: #dc2626;
}

.cfg-cookie-meta {
  font-size: 12px;
  color: var(--paper-muted);
  font-weight: 700;
}

.cfg-cookie-textarea :deep(textarea) {
  font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace;
  font-size: 12px;
  line-height: 1.6;
}

.cfg-cookie-actions {
  display: flex;
  gap: 10px;
}

.cfg-schedule-editor {
  display: flex;
  flex-direction: column;
  gap: 10px;
  width: 100%;
}

.cfg-schedule-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
  min-height: 32px;
}

.cfg-schedule-tag {
  font-size: 13px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}

.cfg-schedule-empty {
  font-size: 13px;
  color: var(--paper-muted);
}

.cfg-schedule-add {
  display: flex;
  align-items: center;
  gap: 8px;
}
</style>
