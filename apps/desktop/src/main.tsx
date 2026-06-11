import React from "react";
import { createRoot } from "react-dom/client";
import {
  Activity,
  Bell,
  ChevronLeft,
  ChevronRight,
  CheckCircle2,
  Clock3,
  Download,
  ExternalLink,
  FileText,
  HeartPulse,
  Hospital,
  KeyRound,
  Lock,
  LogOut,
  Menu,
  RefreshCcw,
  Save,
  Search,
  ServerCog,
  Trash2,
  UnlockKeyhole,
  UserPlus,
  UserRound,
  Users,
  UploadCloud
} from "lucide-react";
import awkLogoUrl from "../../../packages/P02/templates/html/assets/images/logo-awK.png";
import "./styles.css";

type Health = {
  app: string;
  status: string;
  api_port: number;
  frontend_port: number;
  forbidden_ports: string[];
};

type PackageInfo = {
  package_code: string;
  package_name: string;
  status: string;
  version: string;
  page_count: number;
};

type Job = {
  job_id: string;
  job_type: string;
  status: string;
  progress: number;
  total: number;
  succeeded: number;
  failed: number;
  message: string;
  created_at: string;
  updated_at: string;
  completed_at?: string | null;
};

type OcrParseLog = {
  log_id: string;
  job_id: string;
  package_code: string;
  source_file: string;
  strategy_version: string;
  provider: string;
  status: string;
  confidence: number;
  extracted_field_count: number;
  result_json: Record<string, unknown>;
  notes: string;
  created_at: string;
};

type OcrLogPagination = {
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
};

type PaginatedOcrLogs = OcrLogPagination & {
  items: OcrParseLog[];
};

type FieldMapping = {
  key: string;
  label: string;
  pages: string[];
  source: string;
  fill_type: string;
  status: string;
};

type TemplateField = {
  field_key: string;
  page: string;
  tag: string;
  sample_text: string;
};

type PackageConfig = {
  manifest: PackageInfo & {
    template_version?: string;
    rule_version?: string;
    prompt_version?: string;
    default_ai_model?: string;
    pages?: Array<{ page: string; title: string; enabled: boolean }>;
  };
  fields: {
    config_version?: string;
    required_fields?: string[];
    optional_fields?: string[];
    field_mapping?: FieldMapping[];
  };
  rules: {
    version?: string;
    rules?: Array<Record<string, unknown>>;
  };
  ocr_strategy: {
    strategy_version?: string;
    current_provider?: string;
    fallback_provider?: string;
  };
  template_fields: TemplateField[];
};

type RenderFromOcrResponse = {
  log_id: string;
  source_file: string;
  package_code: string;
  report_data: Record<string, unknown>;
  render_result?: {
    report_id: string;
    html_path: string;
    html_url: string;
    created_at: string;
  };
};

type AiConfig = {
  provider: string;
  default_base_url: string;
  default_model: string;
  has_credential: boolean;
  credential_label: string;
};

type CredentialSummary = {
  credential_id: string;
  provider: string;
  label: string;
  created_at: string;
  updated_at: string;
};

type AuthUser = {
  user_id: string;
  username: string;
  display_name: string;
  role: RoleKey;
  role_label: string;
  is_active: boolean;
  last_login_at: string;
  created_at: string;
  updated_at: string;
};

type LoginResponse = {
  access_token: string;
  token_type: string;
  expires_at: string;
  user: AuthUser;
};

type AccountUser = AuthUser;

type AiActionResult = {
  status: string;
  message?: string;
  provider?: string;
  model?: string;
  source_file?: string;
  cleared_documents?: number;
  raw_content?: string;
  usage?: Record<string, unknown>;
  render_result?: {
    report_id: string;
    html_path: string;
    html_url: string;
    created_at: string;
  };
};

type ReviewReport = {
  report_id: string;
  case_id: string;
  package_code: string;
  status: string;
  template_version: string;
  rule_version: string;
  prompt_version: string;
  ai_model: string;
  patient_name: string;
  report_no: string;
  source_file: string;
  ai_status: string;
  html_url: string;
  export_url: string;
  page_count: number;
  created_at: string;
  updated_at: string;
};

type ReviewPage = {
  page_name: string;
  title: string;
  page_no: number;
  page_url: string;
};

type ReviewReportDetail = ReviewReport & {
  pages: ReviewPage[];
};

type ReportPageContent = {
  report_id: string;
  page_name: string;
  html_content: string;
  base_url: string;
  page_url: string;
};

type ReportExportResult = {
  status: string;
  report_id: string;
  pdf_path: string;
  pdf_url: string;
  page_count: number;
  asset_dpi: number;
  asset_summary?: Record<string, unknown>;
};

type ImportedDocument = {
  document_id: string;
  import_job_id: string;
  package_code: string;
  original_name: string;
  stored_path: string;
  size: number;
  status: string;
  created_at: string;
  updated_at: string;
};

type ImportDocumentsResponse = {
  job: Job;
  documents: ImportedDocument[];
};

type ViewKey = "dashboard" | "batch" | "review" | "packages" | "accounts" | "admin";
type RoleKey = "admin" | "customer_service" | "inspector";

const browserHost = typeof window !== "undefined" ? window.location.hostname : "127.0.0.1";
const defaultApiBase = `http://${browserHost}:8111`;
const apiBase = import.meta.env.VITE_API_BASE_URL || defaultApiBase;
const tokenStorageKey = "awk-auth-token";
const ocrLogPageSize = 10;
const defaultOcrLogPagination: OcrLogPagination = {
  page: 1,
  page_size: ocrLogPageSize,
  total: 0,
  total_pages: 1
};

const roleOptions: Array<{ key: RoleKey; label: string }> = [
  { key: "customer_service", label: "客服" },
  { key: "inspector", label: "检测" },
  { key: "admin", label: "管理员" }
];

const roleHome: Record<RoleKey, ViewKey> = {
  admin: "dashboard",
  customer_service: "batch",
  inspector: "review"
};

const roleViewAccess: Record<RoleKey, ViewKey[]> = {
  admin: ["dashboard", "batch", "review", "packages", "accounts", "admin"],
  customer_service: ["batch"],
  inspector: ["review"]
};

let activeApiToken = "";

function isRoleKey(value: string | null): value is RoleKey {
  return value === "admin" || value === "customer_service" || value === "inspector";
}

function getInitialToken() {
  try {
    return window.localStorage.getItem(tokenStorageKey) || "";
  } catch {
    return "";
  }
}

function setActiveApiToken(token: string) {
  activeApiToken = token;
}

function apiHeaders(extra: Record<string, string> = {}) {
  return activeApiToken ? { ...extra, Authorization: `Bearer ${activeApiToken}` } : extra;
}

function canAccessView(role: RoleKey, view: ViewKey) {
  return roleViewAccess[role].includes(view);
}

function hasBatchAccess(role: RoleKey) {
  return role === "admin" || role === "customer_service";
}

function hasReviewAccess(role: RoleKey) {
  return role === "admin" || role === "inspector";
}

function hasAdminAccess(role: RoleKey) {
  return role === "admin";
}

const navItems: Array<{ key: ViewKey; label: string; icon: React.ReactNode }> = [
  { key: "dashboard", label: "工作台", icon: <Activity size={18} /> },
  { key: "batch", label: "批量任务", icon: <UploadCloud size={18} /> },
  { key: "review", label: "报告审查", icon: <FileText size={18} /> },
  { key: "packages", label: "套餐配置", icon: <ServerCog size={18} /> },
  { key: "accounts", label: "账号管理", icon: <Users size={18} /> },
  { key: "admin", label: "后台管理", icon: <KeyRound size={18} /> }
];

const viewCopy: Record<ViewKey, { title: string; subtitle: string }> = {
  dashboard: {
    title: "工作台",
    subtitle: "欢迎回来，今天聚焦报告管理总览。"
  },
  batch: {
    title: "批量任务",
    subtitle: "批量导入 PDF、OCR 解析、AI 输出和报告合成。"
  },
  review: {
    title: "报告审查",
    subtitle: "查看待审报告、退回修改或审核通过后导出正式报告。"
  },
  packages: {
    title: "套餐配置",
    subtitle: "管理套餐字段、规则、提示词和模版版本。"
  },
  accounts: {
    title: "账号管理",
    subtitle: "新建平台账号，配置角色权限、启停账号和重置密码。"
  },
  admin: {
    title: "后台管理",
    subtitle: "管理 OCR/DeepSeek 凭据、用户权限、备份恢复和机构信息。"
  }
};

const jobTypeLabels: Record<string, string> = {
  import_documents: "导入PDF任务",
  ocr_documents: "OCR解析任务",
  extract_fields: "字段抽取任务",
  generate_ai_report: "AI输出任务",
  render_html: "报告合成任务",
  export_pdf: "报告导出任务"
};

async function buildApiError(response: Response) {
  try {
    const payload = (await response.json()) as { detail?: unknown };
    const detail = typeof payload.detail === "string" ? payload.detail : "";
    return new Error(detail ? `${response.status} ${detail}` : `${response.status} ${response.statusText}`);
  } catch {
    return new Error(`${response.status} ${response.statusText}`);
  }
}

async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(`${apiBase}${path}`, {
    headers: apiHeaders()
  });
  if (!response.ok) throw await buildApiError(response);
  return response.json();
}

async function postJson<T>(path: string, body: unknown = {}): Promise<T> {
  const response = await fetch(`${apiBase}${path}`, {
    method: "POST",
    headers: apiHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify(body)
  });
  if (!response.ok) throw await buildApiError(response);
  return response.json();
}

async function patchJson<T>(path: string, body: unknown = {}): Promise<T> {
  const response = await fetch(`${apiBase}${path}`, {
    method: "PATCH",
    headers: apiHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify(body)
  });
  if (!response.ok) throw await buildApiError(response);
  return response.json();
}

async function deleteJson<T>(path: string): Promise<T> {
  const response = await fetch(`${apiBase}${path}`, {
    method: "DELETE",
    headers: apiHeaders()
  });
  if (!response.ok) throw await buildApiError(response);
  return response.json();
}

function renderStatusLabel(status: string) {
  const labelMap: Record<string, string> = {
    mapped: "已匹配",
    ai_pending: "AI待接入",
    ai_connected: "AI已接入",
    missing_credential: "缺少凭据",
    dry_run: "试运行",
    generated: "已生成",
    failed: "失败",
    succeeded: "成功",
    pending_review: "待审",
    edited: "已编辑",
    reviewed: "已审",
    exported: "已导出",
    pending: "待配置",
    ocr: "OCR",
    ai: "AI",
    derived: "规则生成",
    static: "固定值"
  };
  return labelMap[status] || status;
}

function packageOptionLabel(item: PackageInfo) {
  return item.package_name.startsWith(`${item.package_code}-`)
    ? item.package_name
    : `${item.package_code} - ${item.package_name}`;
}

function getStructuredReport(log?: OcrParseLog) {
  return log?.result_json?.structured_report as
    | {
        report_id?: string;
        patient_info?: Record<string, unknown>;
        tests?: Array<Record<string, unknown>>;
        additional_info?: Record<string, unknown>;
      }
    | undefined;
}

function StatusPill({ status }: { status: string }) {
  const labelMap: Record<string, string> = {
    queued: "排队中",
    running: "执行中",
    succeeded: "已完成",
    failed: "失败",
    cancelled: "已取消",
    pending_review: "待审",
    edited: "已编辑",
    reviewed: "已审",
    exported: "已导出",
    healthy: "正常"
  };
  return <span className={`status-pill status-${status}`}>{labelMap[status] || status}</span>;
}

function isLockedReportStatus(status?: string) {
  return status === "reviewed" || status === "exported";
}

function JobProgressPanel({ jobs }: { jobs: Job[] }) {
  return (
    <section className="panel wide-panel">
      <div className="panel-heading">
        <h3>任务进度</h3>
        <span className="muted">最近 {jobs.length} 条任务</span>
      </div>
      <div className="job-table">
        <div className="job-header">
          <span>类型</span>
          <span>状态</span>
          <span>进度</span>
          <span>结果</span>
          <span>完成时间</span>
        </div>
        {jobs.length === 0 && <div className="empty-row">暂无任务，可以先创建导入、OCR、AI 或报告合成任务。</div>}
        {jobs.map((job) => (
          <div className="job-row" key={job.job_id}>
            <span>{jobTypeLabels[job.job_type] || job.job_type}</span>
            <StatusPill status={job.status} />
            <div className="progress-track" aria-label={`进度 ${job.progress}%`}>
              <i style={{ width: `${job.progress}%` }} />
            </div>
            <span>{job.succeeded}/{job.total} 成功，{job.failed} 失败</span>
            <span>{job.completed_at ? formatDateTime(job.completed_at) : "—"}</span>
          </div>
        ))}
      </div>
    </section>
  );
}

function OcrLogPanel({
  logs,
  pagination,
  onPageChange
}: {
  logs: OcrParseLog[];
  pagination: OcrLogPagination;
  onPageChange: (page: number) => void;
}) {
  const currentPage = Math.max(pagination.page, 1);
  const totalPages = Math.max(pagination.total_pages, 1);
  return (
    <section className="panel wide-panel">
      <div className="panel-heading">
        <h3>OCR解析日志</h3>
        <span className="muted">共 {pagination.total} 条，每页最多 {pagination.page_size} 条</span>
      </div>
      <div className="ocr-log-table">
        <div className="ocr-log-header">
          <span>PDF文件</span>
          <span>策略版本</span>
          <span>供应商</span>
          <span>置信度</span>
          <span>字段数</span>
          <span>状态</span>
        </div>
        {logs.length === 0 && <div className="empty-row">暂无 OCR 解析日志。点击“OCR解析任务”后会生成标准 JSON 日志。</div>}
        {logs.map((log) => (
          <details className="ocr-log-row" key={log.log_id}>
            <summary>
              <span>{log.source_file}</span>
              <span>{log.strategy_version}</span>
              <span>{log.provider}</span>
              <span>{Math.round(log.confidence * 100)}%</span>
              <span>{log.extracted_field_count}</span>
              <StatusPill status={log.status} />
            </summary>
            <div className="json-preview">
              <div className="json-preview-meta">
                <b>解析结果 JSON</b>
                <span>任务：{log.job_id}</span>
              </div>
              <pre>{JSON.stringify(log.result_json, null, 2)}</pre>
            </div>
          </details>
        ))}
      </div>
      <div className="log-pagination">
        <button
          className="icon-button"
          type="button"
          title="上一页"
          disabled={currentPage <= 1}
          onClick={() => onPageChange(currentPage - 1)}
        >
          <ChevronLeft size={16} />
        </button>
        <span>
          第 {currentPage} / {totalPages} 页
        </span>
        <button
          className="icon-button"
          type="button"
          title="下一页"
          disabled={currentPage >= totalPages}
          onClick={() => onPageChange(currentPage + 1)}
        >
          <ChevronRight size={16} />
        </button>
      </div>
    </section>
  );
}

function getDateFromValue(value: string) {
  if (!value) return null;
  const direct = new Date(value);
  if (!Number.isNaN(direct.getTime())) return direct;
  const hasTimezone = /(?:Z|[+-]\d{2}:\d{2})$/i.test(value);
  if (hasTimezone) return null;
  const fallback = new Date(`${value}Z`);
  return Number.isNaN(fallback.getTime()) ? null : fallback;
}

function getLocalDayKey(value: string) {
  const date = getDateFromValue(value);
  if (!date) return "";
  return `${date.getFullYear()}-${date.getMonth() + 1}-${date.getDate()}`;
}

function formatShortDate(value: string) {
  const date = getDateFromValue(value);
  if (!date) return "—";
  return date.toLocaleDateString("zh-CN", { month: "2-digit", day: "2-digit" });
}

function formatMetricValue(value: number) {
  return value.toLocaleString("zh-CN");
}

function getRecentMonthBuckets() {
  const now = new Date();
  return Array.from({ length: 6 }, (_, index) => {
    const date = new Date(now.getFullYear(), now.getMonth() - 5 + index, 1);
    return {
      key: `${date.getFullYear()}-${date.getMonth()}`,
      label: `${date.getMonth() + 1}月`,
      reports: 0,
      reviewed: 0,
      tasks: 0
    };
  });
}

function DashboardView({
  reports,
  jobs,
  users,
  currentUser,
  selectedPackage,
  selectedPackageCode,
  health,
  aiConfig,
  onOpenReview,
  onOpenBatch
}: {
  reports: ReviewReport[];
  jobs: Job[];
  users: AccountUser[];
  currentUser: AuthUser;
  selectedPackage: PackageInfo | undefined;
  selectedPackageCode: string;
  health: Health | null;
  aiConfig: AiConfig | null;
  onOpenReview: () => void;
  onOpenBatch: () => void;
}) {
  const todayKey = getLocalDayKey(new Date().toISOString());
  const todayReports = reports.filter((report) => getLocalDayKey(report.created_at) === todayKey).length;
  const pendingReports = reports.filter((report) => report.status === "pending_review").length;
  const reviewedReports = reports.filter((report) => report.status === "reviewed" || report.status === "exported").length;
  const exportedReports = reports.filter((report) => report.status === "exported").length;
  const runningJobs = jobs.filter((job) => job.status === "queued" || job.status === "running").length;
  const activeUsers = users.length > 0 ? users.filter((user) => user.is_active).length : currentUser.is_active ? 1 : 0;
  const latestReports = [...reports]
    .sort((left, right) => {
      const leftDate = getDateFromValue(left.updated_at)?.getTime() || 0;
      const rightDate = getDateFromValue(right.updated_at)?.getTime() || 0;
      return rightDate - leftDate;
    })
    .slice(0, 5);

  const monthBuckets = getRecentMonthBuckets();
  const monthMap = new Map(monthBuckets.map((item) => [item.key, item]));
  reports.forEach((report) => {
    const date = getDateFromValue(report.created_at);
    if (!date) return;
    const bucket = monthMap.get(`${date.getFullYear()}-${date.getMonth()}`);
    if (!bucket) return;
    bucket.reports += 1;
    if (report.status === "reviewed" || report.status === "exported") {
      bucket.reviewed += 1;
    }
  });
  jobs.forEach((job) => {
    const date = getDateFromValue(job.created_at);
    if (!date) return;
    const bucket = monthMap.get(`${date.getFullYear()}-${date.getMonth()}`);
    if (bucket) bucket.tasks += 1;
  });

  const chartWidth = 720;
  const chartHeight = 220;
  const chartLeft = 44;
  const chartRight = 696;
  const chartTop = 26;
  const chartBottom = 184;
  const maxLineValue = Math.max(1, ...monthBuckets.map((item) => Math.max(item.reports, item.reviewed)));
  const chartPoint = (value: number, index: number) => {
    const x = chartLeft + ((chartRight - chartLeft) / Math.max(1, monthBuckets.length - 1)) * index;
    const y = chartBottom - (value / maxLineValue) * (chartBottom - chartTop);
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  };
  const reportLine = monthBuckets.map((item, index) => chartPoint(item.reports, index)).join(" ");
  const reviewedLine = monthBuckets.map((item, index) => chartPoint(item.reviewed, index)).join(" ");
  const reportArea = `${chartLeft},${chartBottom} ${reportLine} ${chartRight},${chartBottom}`;
  const maxTaskValue = Math.max(1, ...monthBuckets.map((item) => item.tasks));

  const overviewItems = [
    { icon: <Clock3 size={15} />, label: "等待审查", value: `${pendingReports}份`, tone: "orange" },
    { icon: <CheckCircle2 size={15} />, label: "已完成审查", value: `${reviewedReports}份`, tone: "green" },
    { icon: <FileText size={15} />, label: "已导出报告", value: `${exportedReports}份`, tone: "blue" },
    { icon: <Activity size={15} />, label: "进行中任务", value: `${runningJobs}个`, tone: "teal" }
  ];
  const notices = [
    {
      title: "后端服务",
      time: health ? `运行中，端口 ${health.api_port}` : "未连接",
      tone: health ? "green" : "orange"
    },
    {
      title: "当前套餐",
      time: `${selectedPackageCode} ${selectedPackage?.version || ""}`.trim(),
      tone: "blue"
    },
    {
      title: "DeepSeek凭据",
      time: aiConfig?.has_credential ? "已配置" : "待配置",
      tone: aiConfig?.has_credential ? "green" : "orange"
    }
  ];

  return (
    <section className="dashboard-overview">
      <section className="dashboard-stat-grid">
        <article className="dashboard-stat-card">
          <div>
            <span>今日报告</span>
            <strong>{formatMetricValue(todayReports)}</strong>
            <p>共 {formatMetricValue(reports.length)} 份报告</p>
          </div>
          <i className="dashboard-stat-icon dashboard-stat-blue"><FileText size={18} /></i>
        </article>
        <article className="dashboard-stat-card">
          <div>
            <span>待审查</span>
            <strong>{formatMetricValue(pendingReports)}</strong>
            <p>{formatMetricValue(reviewedReports)} 份已完成审查</p>
          </div>
          <i className="dashboard-stat-icon dashboard-stat-green"><Activity size={18} /></i>
        </article>
        <article className="dashboard-stat-card">
          <div>
            <span>批量任务</span>
            <strong>{formatMetricValue(jobs.length)}</strong>
            <p>{formatMetricValue(runningJobs)} 个任务进行中</p>
          </div>
          <i className="dashboard-stat-icon dashboard-stat-blue"><ServerCog size={18} /></i>
        </article>
        <article className="dashboard-stat-card">
          <div>
            <span>活跃用户</span>
            <strong>{formatMetricValue(activeUsers)}</strong>
            <p>{users.length > 0 ? `${formatMetricValue(users.length)} 个平台账号` : currentUser.role_label}</p>
          </div>
          <i className="dashboard-stat-icon dashboard-stat-purple"><Users size={18} /></i>
        </article>
      </section>

      <section className="dashboard-chart-row">
        <article className="dashboard-card dashboard-trend-card">
          <div className="dashboard-card-heading">
            <div>
              <h3>报告生成趋势</h3>
              <p>近6个月报告与审查数据</p>
            </div>
            <span className="dashboard-soft-badge">报告管理</span>
          </div>
          <svg className="dashboard-line-chart" viewBox={`0 0 ${chartWidth} ${chartHeight}`} role="img" aria-label="报告生成趋势">
            <defs>
              <linearGradient id="dashboardReportArea" x1="0" x2="0" y1="0" y2="1">
                <stop offset="0%" stopColor="rgba(22,100,255,0.26)" />
                <stop offset="100%" stopColor="rgba(22,100,255,0.02)" />
              </linearGradient>
            </defs>
            {[0, 1, 2, 3].map((index) => {
              const y = chartTop + ((chartBottom - chartTop) / 3) * index;
              return <line className="dashboard-grid-line" key={index} x1={chartLeft} x2={chartRight} y1={y} y2={y} />;
            })}
            {monthBuckets.map((item, index) => {
              const x = chartLeft + ((chartRight - chartLeft) / Math.max(1, monthBuckets.length - 1)) * index;
              return (
                <g key={item.key}>
                  <line className="dashboard-grid-line dashboard-grid-vertical" x1={x} x2={x} y1={chartTop} y2={chartBottom} />
                  <text className="dashboard-chart-label" x={x} y={210} textAnchor="middle">{item.label}</text>
                </g>
              );
            })}
            <polygon className="dashboard-chart-area" points={reportArea} />
            <polyline className="dashboard-line dashboard-line-report" points={reportLine} />
            <polyline className="dashboard-line dashboard-line-reviewed" points={reviewedLine} />
          </svg>
        </article>

        <article className="dashboard-card dashboard-task-card">
          <div className="dashboard-card-heading">
            <div>
              <h3>任务完成情况</h3>
              <p>近6个月批量任务</p>
            </div>
          </div>
          <div className="dashboard-bar-chart">
            {monthBuckets.map((item) => (
              <div className="dashboard-bar-item" key={item.key}>
                <div className="dashboard-bar-track">
                  <i style={{ height: item.tasks > 0 ? `${Math.max(8, (item.tasks / maxTaskValue) * 100)}%` : "0%" }} />
                </div>
                <span>{item.label}</span>
              </div>
            ))}
          </div>
        </article>
      </section>

      <section className="dashboard-bottom-grid">
        <article className="dashboard-card dashboard-latest-card">
          <div className="dashboard-card-heading">
            <div>
              <h3>最新报告</h3>
              <p>最近更新的报告记录</p>
            </div>
            <button className="dashboard-link-button" type="button" onClick={onOpenReview}>
              查看全部 <ExternalLink size={13} />
            </button>
          </div>
          <div className="dashboard-report-list">
            {latestReports.length === 0 && <div className="empty-row">暂无报告。完成 AI 输出后，报告会进入报告审查列表。</div>}
            {latestReports.map((report) => (
              <button className="dashboard-report-row" key={report.report_id} type="button" onClick={onOpenReview}>
                <span className="dashboard-report-avatar">{(report.patient_name || report.report_no || "报").slice(0, 1)}</span>
                <span className="dashboard-report-main">
                  <b>{report.patient_name || "未命名报告"}</b>
                  <small>{report.report_no || report.source_file || report.package_code}</small>
                </span>
                <span className="dashboard-report-date">{formatShortDate(report.updated_at)}</span>
                <StatusPill status={report.status} />
              </button>
            ))}
          </div>
        </article>

        <aside className="dashboard-side-stack">
          <article className="dashboard-card">
            <div className="dashboard-card-heading">
              <div>
                <h3>今日概览</h3>
                <p>报告审查与任务状态</p>
              </div>
            </div>
            <div className="dashboard-overview-list">
              {overviewItems.map((item) => (
                <div className="dashboard-overview-item" key={item.label}>
                  <i className={`dashboard-mini-icon dashboard-mini-${item.tone}`}>{item.icon}</i>
                  <span>{item.label}</span>
                  <b>{item.value}</b>
                </div>
              ))}
            </div>
          </article>
          <article className="dashboard-card">
            <div className="dashboard-card-heading">
              <div>
                <h3>系统公告</h3>
                <p>运行与配置状态</p>
              </div>
            </div>
            <div className="dashboard-notice-list">
              {notices.map((notice) => (
                <div className="dashboard-notice-item" key={notice.title}>
                  <i className={`notice-dot notice-${notice.tone}`} />
                  <div>
                    <b>{notice.title}</b>
                    <span>{notice.time}</span>
                  </div>
                </div>
              ))}
            </div>
            <button className="dashboard-link-button dashboard-link-block" type="button" onClick={onOpenBatch}>
              查看批量任务 <ExternalLink size={13} />
            </button>
          </article>
        </aside>
      </section>
    </section>
  );
}

function BatchActions({
  selectedPackageCode,
  documents,
  importMessage,
  canRunExport,
  onImportPdfs,
  onCreateJob
}: {
  selectedPackageCode: string;
  documents: ImportedDocument[];
  importMessage: string;
  canRunExport: boolean;
  onImportPdfs: (files: FileList) => Promise<void>;
  onCreateJob: (type: string) => Promise<void>;
}) {
  const inputRef = React.useRef<HTMLInputElement | null>(null);
  const latestDocuments = documents.slice(0, 4);

  return (
    <section className="panel wide-panel">
      <div className="panel-heading">
        <h3>批量流程</h3>
        <span className="muted">{selectedPackageCode} 已导入 {documents.length} 个PDF</span>
      </div>
      <input
        ref={inputRef}
        type="file"
        accept="application/pdf,.pdf"
        multiple
        className="hidden-file-input"
        onChange={(event) => {
          const files = event.currentTarget.files;
          if (files && files.length > 0) {
            void onImportPdfs(files);
          }
          event.currentTarget.value = "";
        }}
      />
      <div className={`action-grid ${canRunExport ? "action-grid-wide" : "action-grid-three"}`}>
        <button onClick={() => inputRef.current?.click()}><UploadCloud size={18} /> 导入PDF任务</button>
        <button onClick={() => void onCreateJob("ocr")}><Activity size={18} /> OCR解析任务</button>
        <button onClick={() => void onCreateJob("interpret")}><ServerCog size={18} /> AI输出任务</button>
        {canRunExport && <button onClick={() => void onCreateJob("export")}><FileText size={18} /> 报告合成任务</button>}
      </div>
      {importMessage && <p className="import-message">{importMessage}</p>}
      {documents.length > 0 && (
        <div className="document-chip-list">
          {latestDocuments.map((document) => (
            <span key={document.document_id}>{document.original_name}</span>
          ))}
          {documents.length > latestDocuments.length && <span>另有 {documents.length - latestDocuments.length} 个PDF</span>}
        </div>
      )}
      <p className="panel-note">导入和OCR任务使用已选择PDF的真实数量；AI输出会读取最新OCR日志生成报告。</p>
    </section>
  );
}

function PackageConfigView({
  config,
  logs,
  preview,
  aiResult,
  onRenderPreview,
  onAiInterpret
}: {
  config: PackageConfig | null;
  logs: OcrParseLog[];
  preview: RenderFromOcrResponse | null;
  aiResult: AiActionResult | null;
  onRenderPreview: () => Promise<void>;
  onAiInterpret: () => Promise<void>;
}) {
  const latestLog = logs[0];
  const structured = getStructuredReport(latestLog);
  const patientInfo = structured?.patient_info || {};
  const mappings = config?.fields.field_mapping || [];
  const aiConnectedCount = mappings.filter((item) => item.status === "ai_connected").length;
  const mappedCount = mappings.filter((item) => item.status === "mapped").length;
  const previewUrl = preview?.render_result?.html_url ? `${apiBase}${preview.render_result.html_url}` : "";

  return (
    <>
      <section className="metric-grid metric-grid-four">
        <article className="metric-card">
          <span><ServerCog size={20} /> 配置版本</span>
          <strong>{config?.fields.config_version || "未加载"}</strong>
          <p>{config?.manifest.package_name || "当前套餐配置"}</p>
        </article>
        <article className="metric-card">
          <span><FileText size={20} /> 模板字段</span>
          <strong>{config?.template_fields.length || 0}</strong>
          <p>从 HTML data-field 自动扫描</p>
        </article>
        <article className="metric-card">
          <span><Activity size={20} /> 已匹配</span>
          <strong>{mappedCount}</strong>
          <p>可由 OCR、固定值或规则生成填充</p>
        </article>
        <article className="metric-card">
          <span><CheckCircle2 size={20} /> AI已接入</span>
          <strong>{aiConnectedCount}</strong>
          <p>由 DeepSeek 生成解读后进入人工审查</p>
        </article>
      </section>

      <section className="panel wide-panel">
        <div className="panel-heading">
          <div>
            <h3>{config?.manifest.package_code || "当前套餐"} OCR模板预览</h3>
            <span className="muted">使用最新 OCR 日志生成 report_data 并填充 HTML 模板</span>
          </div>
          <button className="primary-action" onClick={() => void onRenderPreview()}>
            <ExternalLink size={18} /> 生成预览
          </button>
          <button className="secondary-action" onClick={() => void onAiInterpret()}>
            <Activity size={18} /> AI解读测试
          </button>
        </div>
        <div className="preview-grid">
          <div>
            <b>最新OCR文件</b>
            <p>{latestLog?.source_file || "暂无OCR日志，请先执行OCR解析任务"}</p>
          </div>
          <div>
            <b>患者信息</b>
            <p>{String(patientInfo.name || "—")} / {String(patientInfo.gender || "—")} / {String(patientInfo.age || "—")}岁</p>
          </div>
          <div>
            <b>报告编号</b>
            <p>{structured?.report_id || "—"}</p>
          </div>
          <div>
            <b>检验项目</b>
            <p>{structured?.tests?.length || 0} 项</p>
          </div>
        </div>
        {preview && (
          <div className="preview-result">
            <span>已生成：{preview.source_file}</span>
            {previewUrl && (
              <a href={previewUrl} target="_blank" rel="noreferrer">
                打开HTML预览 <ExternalLink size={15} />
              </a>
            )}
          </div>
        )}
        {aiResult && (
          <div className={`preview-result ${aiResult.status === "succeeded" ? "" : "preview-warning"}`}>
            <span>
              AI状态：{renderStatusLabel(aiResult.status)}
              {aiResult.message ? `，${aiResult.message}` : ""}
            </span>
            {aiResult.render_result?.html_url && (
              <a href={`${apiBase}${aiResult.render_result.html_url}`} target="_blank" rel="noreferrer">
                打开AI报告预览 <ExternalLink size={15} />
              </a>
            )}
          </div>
        )}
      </section>

      <section className="panel wide-panel">
        <div className="panel-heading">
          <h3>字段映射配置</h3>
          <span className="muted">{mappings.length} 个字段</span>
        </div>
        <div className="config-table">
          <div className="config-header">
            <span>字段Key</span>
            <span>显示名称</span>
            <span>页面</span>
            <span>来源</span>
            <span>状态</span>
          </div>
          {mappings.map((item) => (
            <div className="config-row" key={item.key}>
              <code>{item.key}</code>
              <span>{item.label}</span>
              <span>{item.pages.join("、")}</span>
              <span>{item.source}</span>
              <span className={`config-status status-${item.status}`}>{renderStatusLabel(item.status)}</span>
            </div>
          ))}
        </div>
      </section>

      <section className="panel wide-panel">
        <div className="panel-heading">
          <h3>模板元素扫描</h3>
          <span className="muted">来自 {config?.manifest.package_code || "当前套餐"} HTML 模板</span>
        </div>
        <div className="template-field-list">
          {(config?.template_fields || []).map((item, index) => (
            <div className="template-field-row" key={`${item.page}-${item.field_key}-${index}`}>
              <code>{item.field_key}</code>
              <span>{item.page}</span>
              <span>{item.sample_text || "—"}</span>
            </div>
          ))}
        </div>
      </section>
    </>
  );
}

function AdminView({
  aiConfig,
  credentials,
  apiKey,
  credentialLabel,
  aiModel,
  aiBaseUrl,
  aiTestResult,
  onApiKeyChange,
  onCredentialLabelChange,
  onAiModelChange,
  onAiBaseUrlChange,
  onSaveCredential,
  onTestConnection
}: {
  aiConfig: AiConfig | null;
  credentials: CredentialSummary[];
  apiKey: string;
  credentialLabel: string;
  aiModel: string;
  aiBaseUrl: string;
  aiTestResult: AiActionResult | null;
  onApiKeyChange: (value: string) => void;
  onCredentialLabelChange: (value: string) => void;
  onAiModelChange: (value: string) => void;
  onAiBaseUrlChange: (value: string) => void;
  onSaveCredential: () => Promise<void>;
  onTestConnection: () => Promise<void>;
}) {
  return (
    <>
      <section className="metric-grid metric-grid-three">
        <article className="metric-card">
          <span><KeyRound size={20} /> DeepSeek凭据</span>
          <strong>{aiConfig?.has_credential ? "已配置" : "未配置"}</strong>
          <p>{aiConfig?.credential_label || "请先保存API Key"}</p>
        </article>
        <article className="metric-card">
          <span><ServerCog size={20} /> 默认模型</span>
          <strong>{aiConfig?.default_model || "deepseek-v4-flash"}</strong>
          <p>可在测试时临时切换</p>
        </article>
        <article className="metric-card">
          <span><Activity size={20} /> 凭据数量</span>
          <strong>{credentials.length}</strong>
          <p>只展示标签，不显示密钥明文</p>
        </article>
      </section>

      <section className="panel wide-panel">
        <div className="panel-heading">
          <div>
            <h3>DeepSeek调用测试</h3>
            <span className="muted">API Key加密写入SQLite，前端不会读取密钥明文</span>
          </div>
          <button className="secondary-action" onClick={() => void onTestConnection()}>
            <Activity size={18} /> 测试连接
          </button>
        </div>
        <div className="admin-form-grid">
          <label>
            <span>凭据标签</span>
            <input value={credentialLabel} onChange={(event) => onCredentialLabelChange(event.target.value)} />
          </label>
          <label>
            <span>DeepSeek API Key</span>
            <input
              type="password"
              value={apiKey}
              onChange={(event) => onApiKeyChange(event.target.value)}
              placeholder="sk-..."
            />
          </label>
          <label>
            <span>模型</span>
            <input value={aiModel} onChange={(event) => onAiModelChange(event.target.value)} />
          </label>
          <label>
            <span>Base URL</span>
            <input value={aiBaseUrl} onChange={(event) => onAiBaseUrlChange(event.target.value)} />
          </label>
        </div>
        <div className="admin-action-row">
          <button className="primary-action" onClick={() => void onSaveCredential()}>
            <KeyRound size={18} /> 保存Key
          </button>
          {aiTestResult && (
            <span className={`admin-result result-${aiTestResult.status}`}>
              连接状态：{renderStatusLabel(aiTestResult.status)}
              {aiTestResult.message ? `，${aiTestResult.message}` : ""}
            </span>
          )}
        </div>
      </section>

      <section className="panel wide-panel">
        <div className="panel-heading">
          <h3>凭据记录</h3>
          <span className="muted">按创建时间倒序</span>
        </div>
        <div className="credential-list">
          {credentials.length === 0 && <div className="empty-row">暂无DeepSeek或OCR凭据。</div>}
          {credentials.map((item) => (
            <div className="credential-row" key={item.credential_id}>
              <b>{item.provider}</b>
              <span>{item.label}</span>
              <code>{item.credential_id}</code>
            </div>
          ))}
        </div>
      </section>
    </>
  );
}

function LoginView({
  onLogin,
  loginError
}: {
  onLogin: (username: string, password: string) => Promise<void>;
  loginError: string;
}) {
  const [username, setUsername] = React.useState("admin");
  const [password, setPassword] = React.useState("");
  const [isSubmitting, setIsSubmitting] = React.useState(false);

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    setIsSubmitting(true);
    try {
      await onLogin(username, password);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <main className="login-shell">
      <div className="login-bg-art" aria-hidden="true">
        <svg className="login-ecg" viewBox="0 0 740 180" role="presentation">
          <path d="M0 92H132L162 92L185 44L224 142L258 92H364L394 92L420 58L455 124L492 92H740" />
        </svg>
        <svg className="login-ecg-secondary" viewBox="0 0 740 180" role="presentation">
          <path d="M0 102H112L144 102L168 70L203 128L238 102H328L356 102L382 42L426 154L462 102H740" />
        </svg>
        <svg className="login-dna" viewBox="0 0 260 360" role="presentation">
          <path d="M72 12C182 64 184 130 74 178C-8 214 8 294 132 348" />
          <path d="M188 12C78 64 76 130 186 178C268 214 252 294 128 348" />
          <path d="M86 56H174M69 105H191M73 158H187M63 215H197M77 269H183M98 320H160" />
        </svg>
        <svg className="login-dna-left" viewBox="0 0 260 360" role="presentation">
          <path d="M72 12C182 64 184 130 74 178C-8 214 8 294 132 348" />
          <path d="M188 12C78 64 76 130 186 178C268 214 252 294 128 348" />
          <path d="M86 56H174M69 105H191M73 158H187M63 215H197M77 269H183M98 320H160" />
        </svg>
        <svg className="login-molecule" viewBox="0 0 320 240" role="presentation">
          <path d="M94 96L158 54L232 92M158 54L162 150M94 96L62 164M162 150L232 92M162 150L246 184" />
          <circle cx="94" cy="96" r="20" />
          <circle cx="158" cy="54" r="18" />
          <circle cx="232" cy="92" r="22" />
          <circle cx="62" cy="164" r="18" />
          <circle cx="162" cy="150" r="24" />
          <circle cx="246" cy="184" r="18" />
        </svg>
        <svg className="login-molecule-left" viewBox="0 0 320 240" role="presentation">
          <path d="M94 96L158 54L232 92M158 54L162 150M94 96L62 164M162 150L232 92M162 150L246 184" />
          <circle cx="94" cy="96" r="20" />
          <circle cx="158" cy="54" r="18" />
          <circle cx="232" cy="92" r="22" />
          <circle cx="62" cy="164" r="18" />
          <circle cx="162" cy="150" r="24" />
          <circle cx="246" cy="184" r="18" />
        </svg>
        <svg className="login-vial" viewBox="0 0 260 320" role="presentation">
          <path d="M94 30H166M112 30V82L64 166C34 218 72 286 130 286C188 286 226 218 196 166L148 82V30" />
          <path d="M86 188H174M78 236H182M108 126H152" />
        </svg>
        <svg className="login-shield" viewBox="0 0 260 300" role="presentation">
          <path d="M130 24L220 62V126C220 202 174 250 130 274C86 250 40 202 40 126V62L130 24Z" />
          <path d="M130 82V184M82 133H178" />
        </svg>
        <span className="login-cross login-cross-one" />
        <span className="login-cross login-cross-two" />
        <span className="login-cross login-cross-three" />
        <span className="login-cross login-cross-four" />
        <span className="login-cross login-cross-five" />
      </div>
      <section className="login-panel" aria-label="平台登录">
        <img className="login-corner-logo" src={awkLogoUrl} alt="安为康" />
        <div className="login-logo-tile">
          <Hospital size={42} strokeWidth={1.8} />
          <HeartPulse className="login-logo-heart" size={24} strokeWidth={2.2} />
        </div>
        <div className="login-heading">
          <h1>功能医学报告管理平台</h1>
          <p>请登录您的平台账号</p>
        </div>
        <form className="login-form" onSubmit={submit}>
          <label className="login-field">
            <span>账号</span>
            <div className="login-input-wrap">
              <UserRound size={20} />
              <input
                value={username}
                autoComplete="username"
                placeholder="请输入账号"
                onChange={(event) => setUsername(event.target.value)}
              />
            </div>
          </label>
          <label className="login-field">
            <span>密码</span>
            <div className="login-input-wrap">
              <Lock size={20} />
              <input
                value={password}
                type="password"
                autoComplete="current-password"
                placeholder="请输入密码"
                onChange={(event) => setPassword(event.target.value)}
              />
            </div>
          </label>
          {loginError && <div className="login-error">{loginError}</div>}
          <button className="login-button" disabled={isSubmitting} type="submit">
            <KeyRound size={18} />
            <span>{isSubmitting ? "登录中" : "登录平台"}</span>
          </button>
        </form>
        <p className="login-help">账号由管理员在后台统一开通和维护</p>
      </section>
      <p className="login-copyright">2025 合肥安为康医学实验室.版权所有</p>
    </main>
  );
}

function AccountManagementView({
  users,
  currentUser,
  accountMessage,
  onCreateUser,
  onUpdateUser,
  onDeleteUser
}: {
  users: AccountUser[];
  currentUser: AuthUser | null;
  accountMessage: string;
  onCreateUser: (payload: {
    username: string;
    display_name: string;
    password: string;
    role: RoleKey;
    is_active: boolean;
  }) => Promise<void>;
  onUpdateUser: (
    userId: string,
    payload: { display_name?: string; password?: string; role?: RoleKey; is_active?: boolean }
  ) => Promise<void>;
  onDeleteUser: (userId: string) => Promise<void>;
}) {
  const [username, setUsername] = React.useState("");
  const [displayName, setDisplayName] = React.useState("");
  const [password, setPassword] = React.useState("");
  const [confirmPassword, setConfirmPassword] = React.useState("");
  const [role, setRole] = React.useState<RoleKey>("customer_service");
  const [isCreating, setIsCreating] = React.useState(false);
  const [formMessage, setFormMessage] = React.useState("");

  const create = async () => {
    const normalizedPassword = password.trim();
    const normalizedConfirmPassword = confirmPassword.trim();
    if (!username.trim()) {
      setFormMessage("请先填写账号。");
      return;
    }
    if (normalizedPassword.length < 8) {
      setFormMessage("初始密码至少需要 8 位。");
      return;
    }
    if (normalizedPassword !== normalizedConfirmPassword) {
      setFormMessage("两次输入的初始密码不一致。");
      return;
    }
    setFormMessage("");
    setIsCreating(true);
    try {
      await onCreateUser({
        username: username.trim(),
        display_name: displayName,
        password: normalizedPassword,
        role,
        is_active: true
      });
      setUsername("");
      setDisplayName("");
      setPassword("");
      setConfirmPassword("");
      setRole("customer_service");
    } finally {
      setIsCreating(false);
    }
  };

  return (
    <>
      <section className="panel wide-panel">
        <div className="panel-heading">
          <div>
            <h3>新建账号</h3>
            <span className="muted">账号创建后即可按角色权限登录平台</span>
          </div>
          <button className="primary-action" disabled={isCreating} onClick={() => void create()}>
            <UserPlus size={18} /> {isCreating ? "创建中" : "创建账号"}
          </button>
        </div>
        <div className="admin-form-grid account-create-grid">
          <label>
            <span>账号</span>
            <input value={username} onChange={(event) => setUsername(event.target.value)} />
          </label>
          <label>
            <span>姓名/显示名</span>
            <input value={displayName} onChange={(event) => setDisplayName(event.target.value)} />
          </label>
          <label>
            <span>初始密码</span>
            <input value={password} type="password" onChange={(event) => setPassword(event.target.value)} />
          </label>
          <label>
            <span>确认密码</span>
            <input value={confirmPassword} type="password" onChange={(event) => setConfirmPassword(event.target.value)} />
          </label>
          <label>
            <span>角色权限</span>
            <select value={role} onChange={(event) => setRole(event.target.value as RoleKey)}>
              {roleOptions.map((item) => (
                <option key={item.key} value={item.key}>{item.label}</option>
              ))}
            </select>
          </label>
        </div>
        {(formMessage || accountMessage) && <div className="review-message account-message">{formMessage || accountMessage}</div>}
      </section>

      <section className="panel wide-panel">
        <div className="panel-heading">
          <h3>账号列表</h3>
          <span className="muted">{users.length} 个账号</span>
        </div>
        <div className="account-table">
          <div className="account-header">
            <span>账号</span>
            <span>显示名</span>
            <span>角色</span>
            <span>状态</span>
            <span>重置密码</span>
            <span>操作</span>
          </div>
          {users.length === 0 && <div className="empty-row">暂无账号。</div>}
          {users.map((user) => (
            <AccountRow
              key={user.user_id}
              user={user}
              isCurrentUser={currentUser?.user_id === user.user_id}
              onUpdateUser={onUpdateUser}
              onDeleteUser={onDeleteUser}
            />
          ))}
        </div>
      </section>
    </>
  );
}

function AccountRow({
  user,
  isCurrentUser,
  onUpdateUser,
  onDeleteUser
}: {
  user: AccountUser;
  isCurrentUser: boolean;
  onUpdateUser: (
    userId: string,
    payload: { display_name?: string; password?: string; role?: RoleKey; is_active?: boolean }
  ) => Promise<void>;
  onDeleteUser: (userId: string) => Promise<void>;
}) {
  const [displayName, setDisplayName] = React.useState(user.display_name);
  const [role, setRole] = React.useState<RoleKey>(user.role);
  const [isActive, setIsActive] = React.useState(user.is_active);
  const [isSaving, setIsSaving] = React.useState(false);
  const [isResetting, setIsResetting] = React.useState(false);
  const [isDeleting, setIsDeleting] = React.useState(false);

  React.useEffect(() => {
    setDisplayName(user.display_name);
    setRole(user.role);
    setIsActive(user.is_active);
  }, [user]);

  const save = async () => {
    setIsSaving(true);
    try {
      await onUpdateUser(user.user_id, {
        display_name: displayName,
        role,
        is_active: isActive
      });
    } finally {
      setIsSaving(false);
    }
  };

  const resetPassword = async () => {
    if (isCurrentUser) return;
    setIsResetting(true);
    try {
      await onUpdateUser(user.user_id, { password: "Abc12345" });
    } finally {
      setIsResetting(false);
    }
  };

  const deleteAccount = async () => {
    if (isCurrentUser) return;
    const confirmed = window.confirm(`确认删除账号 ${user.username}？删除后该账号不能继续登录。`);
    if (!confirmed) return;
    setIsDeleting(true);
    try {
      await onDeleteUser(user.user_id);
    } finally {
      setIsDeleting(false);
    }
  };

  return (
    <div className="account-row">
      <div>
        <b>{user.username}</b>
        {isCurrentUser && <span className="account-self">当前登录</span>}
      </div>
      <input value={displayName} onChange={(event) => setDisplayName(event.target.value)} />
      <select value={role} onChange={(event) => setRole(event.target.value as RoleKey)}>
        {roleOptions.map((item) => (
          <option key={item.key} value={item.key}>{item.label}</option>
        ))}
      </select>
      <label className="account-active-toggle">
        <input
          type="checkbox"
          checked={isActive}
          disabled={isCurrentUser}
          onChange={(event) => setIsActive(event.target.checked)}
        />
        启用
      </label>
      <button className="secondary-action" disabled={isCurrentUser || isResetting} onClick={() => void resetPassword()}>
        <KeyRound size={18} /> {isResetting ? "重置中" : "重置"}
      </button>
      <div className="account-row-actions">
        <button className="secondary-action" disabled={isSaving} onClick={() => void save()}>
          <Save size={18} /> {isSaving ? "保存中" : "保存"}
        </button>
        <button className="danger-action" disabled={isCurrentUser || isDeleting} onClick={() => void deleteAccount()}>
          {isDeleting ? "删除中" : "删除"}
        </button>
      </div>
    </div>
  );
}

function formatDateTime(value: string) {
  if (!value) return "—";
  const date = getDateFromValue(value);
  if (!date) return value;
  return date.toLocaleString("zh-CN", { hour12: false });
}

function buildReviewSrcDoc(page: ReportPageContent | null, readonly = false) {
  if (!page) return "";
  const base = `<base data-review-helper="true" href="${page.base_url}" />`;
  const reviewStyle = `
    <style id="awk-review-editor-style" data-review-helper="true">
      html { background: #eef3f7; }
      body { min-height: 100vh; }
      .editable { cursor: text; }
      .editable:hover { box-shadow: 0 0 0 2px rgba(17, 107, 216, 0.12); }
      ${
        readonly
          ? `
      .editable,
      [contenteditable="true"] {
        cursor: default !important;
        pointer-events: none !important;
      }
      .editable:hover,
      [contenteditable="true"]:hover {
        box-shadow: none !important;
      }`
          : ""
      }
    </style>
  `;
  const readonlyScript = readonly
    ? `
    <script data-review-helper="true">
      document.addEventListener("DOMContentLoaded", () => {
        document.querySelectorAll(".editable, [contenteditable='true']").forEach((node) => {
          node.setAttribute("contenteditable", "false");
          node.setAttribute("aria-readonly", "true");
        });
      });
    </script>
  `
    : "";
  if (page.html_content.includes("<head>")) {
    return page.html_content.replace("<head>", `<head>${base}${reviewStyle}${readonlyScript}`);
  }
  return `${base}${reviewStyle}${readonlyScript}${page.html_content}`;
}

function ReviewView({
  reports,
  detail,
  selectedReportId,
  selectedPageName,
  pageContent,
  exportResult,
  reviewMessage,
  canReview,
  canUnlock,
  onSelectReport,
  onSelectPage,
  onSavePage,
  onExportPdf,
  onUnlockReport,
  onDeleteReport
}: {
  reports: ReviewReport[];
  detail: ReviewReportDetail | null;
  selectedReportId: string;
  selectedPageName: string;
  pageContent: ReportPageContent | null;
  exportResult: ReportExportResult | null;
  reviewMessage: string;
  canReview: boolean;
  canUnlock: boolean;
  onSelectReport: (reportId: string) => void;
  onSelectPage: (pageName: string) => void;
  onSavePage: (htmlContent: string) => Promise<void>;
  onExportPdf: () => Promise<void>;
  onUnlockReport: () => Promise<void>;
  onDeleteReport: () => Promise<void>;
}) {
  const iframeRef = React.useRef<HTMLIFrameElement | null>(null);
  const [isSaving, setIsSaving] = React.useState(false);
  const [isExporting, setIsExporting] = React.useState(false);
  const [isUnlocking, setIsUnlocking] = React.useState(false);
  const [isDeleting, setIsDeleting] = React.useState(false);
  const selectedReport = reports.find((item) => item.report_id === selectedReportId) || detail;
  const isLocked = isLockedReportStatus(selectedReport?.status);

  const saveCurrentPage = async () => {
    if (!canReview || isLocked) return;
    const documentElement = iframeRef.current?.contentDocument?.documentElement;
    if (!documentElement) return;
    const cleanDocument = documentElement.cloneNode(true) as HTMLElement;
    cleanDocument.querySelectorAll("[data-review-helper='true']").forEach((node) => node.remove());
    setIsSaving(true);
    try {
      await onSavePage(`<!doctype html>\n${cleanDocument.outerHTML}`);
    } finally {
      setIsSaving(false);
    }
  };

  const exportCurrentReport = async () => {
    if (!canReview || isLocked) return;
    setIsExporting(true);
    try {
      await onExportPdf();
    } finally {
      setIsExporting(false);
    }
  };

  const unlockCurrentReport = async () => {
    if (!canUnlock || !isLocked) return;
    setIsUnlocking(true);
    try {
      await onUnlockReport();
    } finally {
      setIsUnlocking(false);
    }
  };

  const deleteCurrentReport = async () => {
    if (!canReview || !selectedReport) return;
    const label = selectedReport.patient_name || selectedReport.report_no || selectedReport.report_id;
    const confirmed = window.confirm(`确认删除报告“${label}”？删除后会移除待审记录、HTML页面和已导出的PDF文件，不能恢复。`);
    if (!confirmed) return;
    setIsDeleting(true);
    try {
      await onDeleteReport();
    } finally {
      setIsDeleting(false);
    }
  };

  return (
    <section className="review-layout">
      <aside className="panel review-list-panel">
        <div className="panel-heading">
          <h3>报告列表</h3>
          <span className="muted">{reports.length} 份</span>
        </div>
        <div className="review-report-list">
          {reports.length === 0 && <div className="empty-row">暂无报告。完成 AI 输出后，最终版 HTML 会自动进入这里。</div>}
          {reports.map((report) => (
            <button
              type="button"
              className={[
                "review-report-card",
                report.report_id === selectedReportId ? "active" : "",
                isLockedReportStatus(report.status) ? "locked" : ""
              ].filter(Boolean).join(" ")}
              key={report.report_id}
              onClick={() => onSelectReport(report.report_id)}
            >
              <span className="report-card-title">{report.patient_name || "未命名报告"}</span>
              <span>{report.report_no}</span>
              <span>{report.source_file || report.package_code}</span>
              <StatusPill status={report.status} />
            </button>
          ))}
        </div>
      </aside>

      <section className="review-workspace">
        <section className="panel review-toolbar">
          <div className="review-toolbar-main">
            <h3>{selectedReport?.patient_name || "请选择报告"}</h3>
            <p>
              报告编号：{selectedReport?.report_no || "—"}　
              页数：{selectedReport?.page_count || 0}　
              更新时间：{selectedReport ? formatDateTime(selectedReport.updated_at) : "—"}
            </p>
          </div>
          <div className="review-actions">
            {selectedReport?.html_url && (
              <a className="secondary-link" href={`${apiBase}${selectedReport.html_url}`} target="_blank" rel="noreferrer">
                打开HTML <ExternalLink size={16} />
              </a>
            )}
            <button className="secondary-action" disabled={!pageContent || isSaving || isLocked || !canReview} onClick={() => void saveCurrentPage()}>
              <Save size={18} /> {isSaving ? "保存中" : "保存本页"}
            </button>
            <button className="primary-action" disabled={!detail || isExporting || isLocked || !canReview} onClick={() => void exportCurrentReport()}>
              <Download size={18} /> {isExporting ? "输出中" : "输出PDF"}
            </button>
            {isLocked && canUnlock && (
              <button className="secondary-action" disabled={isUnlocking} onClick={() => void unlockCurrentReport()}>
                <UnlockKeyhole size={18} /> {isUnlocking ? "解审核中" : "解审核"}
              </button>
            )}
            <button className="danger-action" disabled={!selectedReport || isDeleting || !canReview} onClick={() => void deleteCurrentReport()}>
              <Trash2 size={18} /> {isDeleting ? "删除中" : "删除报告"}
            </button>
          </div>
        </section>

        {selectedReport && (
          <section className="metric-grid metric-grid-four review-version-grid">
            <article className="metric-card compact-metric">
              <span>模板版本</span>
              <strong>{selectedReport.template_version || "—"}</strong>
            </article>
            <article className="metric-card compact-metric">
              <span>规则版本</span>
              <strong>{selectedReport.rule_version || "—"}</strong>
            </article>
            <article className="metric-card compact-metric">
              <span>提示词版本</span>
              <strong>{selectedReport.prompt_version || "—"}</strong>
            </article>
            <article className="metric-card compact-metric">
              <span>AI模型</span>
              <strong>{selectedReport.ai_model || "—"}</strong>
            </article>
          </section>
        )}

        {isLocked && <div className="review-lock-banner">该报告已审并锁定，不能继续编辑。需要修改时请使用管理员角色解审核。</div>}
        {reviewMessage && <div className="review-message">{reviewMessage}</div>}
        {exportResult && (
          <div className="preview-result">
            <span>PDF已输出：{exportResult.page_count} 页，图片资产按 {exportResult.asset_dpi}dpi 写入打印元数据</span>
            <a href={`${apiBase}${exportResult.pdf_url}`} target="_blank" rel="noreferrer">
              打开PDF <ExternalLink size={15} />
            </a>
          </div>
        )}

        <section className="panel review-editor-panel">
          <div className="review-page-tabs">
            {(detail?.pages || []).map((page) => (
              <button
                type="button"
                className={page.page_name === selectedPageName ? "active" : ""}
                key={page.page_name}
                onClick={() => onSelectPage(page.page_name)}
              >
                {String(page.page_no).padStart(2, "0")}
              </button>
            ))}
          </div>
          {pageContent ? (
            <iframe
              ref={iframeRef}
              className="review-frame"
              title={`报告审查 ${pageContent.page_name}`}
              srcDoc={buildReviewSrcDoc(pageContent, isLocked || !canReview)}
            />
          ) : (
            <div className="empty-row">请选择一份报告和页面。</div>
          )}
        </section>
      </section>
    </section>
  );
}

function App() {
  const [authToken, setAuthToken] = React.useState(() => getInitialToken());
  const [authChecked, setAuthChecked] = React.useState(false);
  const [currentUser, setCurrentUser] = React.useState<AuthUser | null>(null);
  const [loginError, setLoginError] = React.useState("");
  const [activeView, setActiveView] = React.useState<ViewKey>("batch");
  const [health, setHealth] = React.useState<Health | null>(null);
  const [packages, setPackages] = React.useState<PackageInfo[]>([]);
  const [selectedPackageCode, setSelectedPackageCode] = React.useState("P02");
  const [jobs, setJobs] = React.useState<Job[]>([]);
  const [ocrLogs, setOcrLogs] = React.useState<OcrParseLog[]>([]);
  const [ocrLogPage, setOcrLogPage] = React.useState(1);
  const [ocrLogPagination, setOcrLogPagination] = React.useState<OcrLogPagination>(defaultOcrLogPagination);
  const [packageConfig, setPackageConfig] = React.useState<PackageConfig | null>(null);
  const [renderPreview, setRenderPreview] = React.useState<RenderFromOcrResponse | null>(null);
  const [aiConfig, setAiConfig] = React.useState<AiConfig | null>(null);
  const [credentials, setCredentials] = React.useState<CredentialSummary[]>([]);
  const [accountUsers, setAccountUsers] = React.useState<AccountUser[]>([]);
  const [accountMessage, setAccountMessage] = React.useState("");
  const [apiKey, setApiKey] = React.useState("");
  const [credentialLabel, setCredentialLabel] = React.useState("DeepSeek V4");
  const [aiModel, setAiModel] = React.useState("deepseek-v4-flash");
  const [aiBaseUrl, setAiBaseUrl] = React.useState("https://api.deepseek.com");
  const [aiTestResult, setAiTestResult] = React.useState<AiActionResult | null>(null);
  const [aiInterpretResult, setAiInterpretResult] = React.useState<AiActionResult | null>(null);
  const [reviewReports, setReviewReports] = React.useState<ReviewReport[]>([]);
  const [selectedReviewReportId, setSelectedReviewReportId] = React.useState("");
  const [reviewDetail, setReviewDetail] = React.useState<ReviewReportDetail | null>(null);
  const [selectedReviewPageName, setSelectedReviewPageName] = React.useState("");
  const [reviewPageContent, setReviewPageContent] = React.useState<ReportPageContent | null>(null);
  const [reviewExportResult, setReviewExportResult] = React.useState<ReportExportResult | null>(null);
  const [reviewMessage, setReviewMessage] = React.useState("");
  const [importedDocuments, setImportedDocuments] = React.useState<ImportedDocument[]>([]);
  const [importMessage, setImportMessage] = React.useState("");
  const [error, setError] = React.useState<string>("");

  setActiveApiToken(authToken);

  const currentRole = currentUser?.role || "customer_service";
  const isAuthenticated = Boolean(authToken && currentUser);
  const selectedPackage = packages.find((item) => item.package_code === selectedPackageCode);
  const canBatchRole = hasBatchAccess(currentRole);
  const canReviewRole = hasReviewAccess(currentRole);
  const canAdminRole = hasAdminAccess(currentRole);
  const visibleNavItems = navItems.filter((item) => canAccessView(currentRole, item.key));

  const clearAuth = React.useCallback(() => {
    setActiveApiToken("");
    setAuthToken("");
    setCurrentUser(null);
    setLoginError("");
    setError("");
    setPackages([]);
    setJobs([]);
    setOcrLogs([]);
    setOcrLogPage(1);
    setOcrLogPagination(defaultOcrLogPagination);
    setCredentials([]);
    setAccountUsers([]);
    setReviewReports([]);
    setImportedDocuments([]);
    try {
      window.localStorage.removeItem(tokenStorageKey);
    } catch {
      // 本地存储不可用时，仅清理当前会话。
    }
  }, []);

  React.useEffect(() => {
    let cancelled = false;
    setActiveApiToken(authToken);
    if (!authToken) {
      setCurrentUser(null);
      setAuthChecked(true);
      return;
    }
    const loadCurrentUser = async () => {
      try {
        const user = await getJson<AuthUser>("/auth/me");
        if (cancelled) return;
        setCurrentUser(user);
        setActiveView(roleHome[user.role]);
      } catch {
        if (!cancelled) clearAuth();
      } finally {
        if (!cancelled) setAuthChecked(true);
      }
    };
    void loadCurrentUser();
    return () => {
      cancelled = true;
    };
  }, [authToken, clearAuth]);

  React.useEffect(() => {
    setOcrLogPage(1);
  }, [selectedPackageCode]);

  const refresh = React.useCallback(async () => {
    if (!isAuthenticated) return;
    try {
      setError("");
      const [
        healthData,
        packagesData,
        jobsData,
        ocrLogData,
        packageConfigData,
        aiConfigData,
        credentialData,
        accountUserData,
        reviewReportData,
        importedDocumentData
      ] = await Promise.all([
        getJson<Health>("/health"),
        getJson<PackageInfo[]>("/packages"),
        getJson<Job[]>("/jobs"),
        getJson<PaginatedOcrLogs>(
          `/ocr/logs?package_code=${encodeURIComponent(selectedPackageCode)}&page=${ocrLogPage}&page_size=${ocrLogPageSize}`
        ),
        getJson<PackageConfig>(`/packages/${encodeURIComponent(selectedPackageCode)}/config`),
        getJson<AiConfig>("/ai/config"),
        canAdminRole ? getJson<CredentialSummary[]>("/admin/credentials") : Promise.resolve([]),
        canAdminRole ? getJson<AccountUser[]>("/admin/users") : Promise.resolve([]),
        canReviewRole
          ? getJson<ReviewReport[]>(`/reports?package_code=${encodeURIComponent(selectedPackageCode)}&status=all`)
          : Promise.resolve([]),
        canBatchRole
          ? getJson<ImportedDocument[]>(`/documents?package_code=${encodeURIComponent(selectedPackageCode)}&limit=20`)
          : Promise.resolve([])
      ]);
      setHealth(healthData);
      setPackages(packagesData);
      if (!packagesData.some((item) => item.package_code === selectedPackageCode)) {
        setSelectedPackageCode(packagesData[0]?.package_code || "P02");
      }
      setJobs(jobsData);
      setOcrLogs(ocrLogData.items);
      setOcrLogPagination({
        page: ocrLogData.page,
        page_size: ocrLogData.page_size,
        total: ocrLogData.total,
        total_pages: ocrLogData.total_pages
      });
      if (ocrLogData.page !== ocrLogPage) {
        setOcrLogPage(ocrLogData.page);
      }
      setPackageConfig(packageConfigData);
      setAiConfig(aiConfigData);
      setCredentials(canAdminRole ? credentialData : []);
      setAccountUsers(canAdminRole ? accountUserData : []);
      setReviewReports(canReviewRole ? reviewReportData : []);
      setImportedDocuments(canBatchRole ? importedDocumentData : []);
      if (canReviewRole) {
        const hasSelectedReport = reviewReportData.some((item) => item.report_id === selectedReviewReportId);
        const nextReportId = hasSelectedReport ? selectedReviewReportId : reviewReportData[0]?.report_id || "";
        if (nextReportId !== selectedReviewReportId) {
          setSelectedReviewReportId(nextReportId);
        }
      } else if (selectedReviewReportId) {
        setSelectedReviewReportId("");
      }
      if (aiConfigData.default_model && aiModel === "deepseek-v4-flash") {
        setAiModel(aiConfigData.default_model);
      }
      if (aiConfigData.default_base_url && aiBaseUrl === "https://api.deepseek.com") {
        setAiBaseUrl(aiConfigData.default_base_url);
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : "请求失败";
      setError(message);
      if (message.startsWith("401")) clearAuth();
    }
  }, [
    isAuthenticated,
    selectedPackageCode,
    ocrLogPage,
    selectedReviewReportId,
    aiBaseUrl,
    aiModel,
    canAdminRole,
    canReviewRole,
    canBatchRole,
    clearAuth
  ]);

  React.useEffect(() => {
    if (currentUser && !canAccessView(currentRole, activeView)) {
      setActiveView(roleHome[currentRole]);
    }
  }, [currentUser, currentRole, activeView]);

  React.useEffect(() => {
    if (!isAuthenticated) return;
    void refresh();
    const timer = window.setInterval(() => void refresh(), 1800);
    return () => window.clearInterval(timer);
  }, [refresh, isAuthenticated]);

  React.useEffect(() => {
    if (!isAuthenticated || !canReviewRole || !selectedReviewReportId) {
      setReviewDetail(null);
      setReviewPageContent(null);
      return;
    }
    let cancelled = false;
    const loadDetail = async () => {
      try {
        const detail = await getJson<ReviewReportDetail>(`/reports/${encodeURIComponent(selectedReviewReportId)}`);
        if (cancelled) return;
        setReviewDetail(detail);
        const firstPage = detail.pages[0]?.page_name || "";
        if (!selectedReviewPageName || !detail.pages.some((page) => page.page_name === selectedReviewPageName)) {
          setSelectedReviewPageName(firstPage);
        }
      } catch (err) {
        if (!cancelled) {
          setReviewDetail(null);
          setReviewPageContent(null);
          setReviewMessage(err instanceof Error ? err.message : "加载报告失败");
        }
      }
    };
    void loadDetail();
    return () => {
      cancelled = true;
    };
  }, [isAuthenticated, selectedReviewReportId, selectedReviewPageName, canReviewRole]);

  React.useEffect(() => {
    if (!isAuthenticated || !canReviewRole || !selectedReviewReportId || !selectedReviewPageName) {
      setReviewPageContent(null);
      return;
    }
    let cancelled = false;
    const loadPage = async () => {
      try {
        const page = await getJson<ReportPageContent>(
          `/reports/${encodeURIComponent(selectedReviewReportId)}/pages/${encodeURIComponent(selectedReviewPageName)}`
        );
        if (!cancelled) {
          setReviewPageContent(page);
          setReviewMessage("");
        }
      } catch (err) {
        if (!cancelled) {
          setReviewPageContent(null);
          setReviewMessage(err instanceof Error ? err.message : "加载页面失败");
        }
      }
    };
    void loadPage();
    return () => {
      cancelled = true;
    };
  }, [isAuthenticated, selectedReviewReportId, selectedReviewPageName, canReviewRole]);

  const loginToPlatform = async (username: string, password: string) => {
    setLoginError("");
    try {
      const result = await postJson<LoginResponse>("/auth/login", {
        username: username.trim(),
        password: password.trim()
      });
      setActiveApiToken(result.access_token);
      setAuthToken(result.access_token);
      setCurrentUser(result.user);
      setActiveView(roleHome[result.user.role]);
      setAuthChecked(true);
      try {
        window.localStorage.setItem(tokenStorageKey, result.access_token);
      } catch {
        // 本地存储不可用时仍可完成当前会话登录。
      }
    } catch (err) {
      setLoginError(err instanceof Error ? err.message : "登录失败");
    }
  };

  const logout = async () => {
    try {
      await postJson("/auth/logout");
    } finally {
      clearAuth();
    }
  };

  const importPdfs = async (files: FileList) => {
    if (!canBatchRole) {
      setImportMessage("当前账号无批量任务权限。");
      return;
    }
    const pdfFiles = Array.from(files).filter((file) => file.name.toLowerCase().endsWith(".pdf"));
    if (pdfFiles.length === 0) {
      setImportMessage("请选择PDF文件。");
      return;
    }

    const formData = new FormData();
    formData.append("package_code", selectedPackageCode);
    pdfFiles.forEach((file) => formData.append("files", file));
    setImportMessage(`正在导入 ${pdfFiles.length} 个PDF...`);
    const response = await fetch(`${apiBase}/documents/import`, {
      method: "POST",
      headers: apiHeaders(),
      body: formData
    });
    if (!response.ok) {
      throw await buildApiError(response);
    }
    const result = (await response.json()) as ImportDocumentsResponse;
    setJobs((current) => [result.job, ...current.filter((item) => item.job_id !== result.job.job_id)].slice(0, 15));
    setImportedDocuments(result.documents);
    setImportMessage(`已导入 ${result.documents.length} 个PDF，可继续执行OCR解析任务。`);
    await refresh();
  };

  const createBatchJob = async (type: string) => {
    if (!canBatchRole) {
      setImportMessage("当前账号无批量任务权限。");
      return;
    }
    if (type === "export" && !canAdminRole) {
      setImportMessage("报告合成任务仅管理员可执行。");
      return;
    }
    if (type === "ocr" && importedDocuments.length === 0) {
      setImportMessage("请先点击“导入PDF任务”选择PDF文件，再执行OCR解析任务。");
      return;
    }
    const job = await postJson<Job>(`/batch/${type}`, { package_code: selectedPackageCode });
    setJobs((current) => [job, ...current.filter((item) => item.job_id !== job.job_id)].slice(0, 15));
    if (type === "ocr") {
      setOcrLogPage(1);
    }
  };

  const renderFromLatestOcr = async () => {
    if (!canBatchRole) return;
    const preview = await postJson<RenderFromOcrResponse>("/reports/render-from-ocr", {
      package_code: selectedPackageCode,
      render_html: true
    });
    setRenderPreview(preview);
  };

  const saveDeepseekCredential = async () => {
    if (!canAdminRole) return;
    if (!apiKey.trim()) {
      setAiTestResult({ status: "failed", message: "请先输入DeepSeek API Key。" });
      return;
    }
    await postJson("/admin/credentials", {
      provider: "deepseek",
      label: credentialLabel.trim() || "DeepSeek V4",
      value: apiKey.trim()
    });
    setApiKey("");
    setAiTestResult({ status: "succeeded", message: "DeepSeek API Key已加密保存。" });
    await refresh();
  };

  const testAiConnection = async () => {
    if (!canAdminRole) return;
    const result = await postJson<AiActionResult>("/ai/test-connection", {
      model: aiModel,
      base_url: aiBaseUrl
    });
    setAiTestResult(result);
    await refresh();
  };

  const runAiInterpret = async () => {
    if (!canBatchRole) return;
    const result = await postJson<AiActionResult>("/ai/interpret", {
      package_code: selectedPackageCode,
      model: aiModel,
      base_url: aiBaseUrl,
      render_html: true
    });
    setAiInterpretResult(result);
    if (result.render_result?.report_id) {
      if (canReviewRole) {
        setSelectedReviewReportId(result.render_result.report_id);
        setActiveView("review");
      } else {
        setImportMessage("AI输出完成，最终版HTML已提交报告审查菜单，请由检测或管理员账号审查。");
      }
    }
    if (typeof result.cleared_documents === "number" && result.cleared_documents > 0) {
      setImportMessage(`AI输出完成，已自动清理 ${result.cleared_documents} 个导入PDF记录。`);
    }
    await refresh();
  };

  const createAccount = async (payload: {
    username: string;
    display_name: string;
    password: string;
    role: RoleKey;
    is_active: boolean;
  }) => {
    try {
      await postJson<AccountUser>("/admin/users", payload);
      setAccountMessage("账号已创建。");
      await refresh();
    } catch (err) {
      setAccountMessage(err instanceof Error ? err.message : "创建账号失败");
    }
  };

  const updateAccount = async (
    userId: string,
    payload: { display_name?: string; password?: string; role?: RoleKey; is_active?: boolean }
  ) => {
    try {
      const updated = await patchJson<AccountUser>(`/admin/users/${encodeURIComponent(userId)}`, payload);
      setAccountUsers((current) => current.map((item) => (item.user_id === updated.user_id ? updated : item)));
      if (currentUser?.user_id === updated.user_id) {
        setCurrentUser(updated);
      }
      setAccountMessage("账号已保存。");
      await refresh();
    } catch (err) {
      setAccountMessage(err instanceof Error ? err.message : "保存账号失败");
    }
  };

  const deleteAccount = async (userId: string) => {
    try {
      await deleteJson<{ status: string }>(`/admin/users/${encodeURIComponent(userId)}`);
      setAccountUsers((current) => current.filter((item) => item.user_id !== userId));
      setAccountMessage("账号已删除。");
      await refresh();
    } catch (err) {
      setAccountMessage(err instanceof Error ? err.message : "删除账号失败");
    }
  };

  const selectReviewReport = (reportId: string) => {
    setSelectedReviewReportId(reportId);
    setSelectedReviewPageName("");
    setReviewExportResult(null);
    setReviewMessage("");
  };

  const selectReviewPage = (pageName: string) => {
    setSelectedReviewPageName(pageName);
    setReviewMessage("");
  };

  const saveReviewPage = async (htmlContent: string) => {
    if (!canReviewRole || !selectedReviewReportId || !selectedReviewPageName) return;
    const detail = await postJson<ReviewReportDetail>(
      `/reports/${encodeURIComponent(selectedReviewReportId)}/pages/${encodeURIComponent(selectedReviewPageName)}`,
      { html_content: htmlContent }
    );
    setReviewDetail(detail);
    setReviewMessage(`${selectedReviewPageName} 已保存，PDF 输出会使用审查后的内容。`);
    await refresh();
  };

  const exportReviewPdf = async () => {
    if (!canReviewRole || !selectedReviewReportId) return;
    const result = await postJson<ReportExportResult>(`/reports/${encodeURIComponent(selectedReviewReportId)}/export`);
    setReviewExportResult(result);
    setReviewMessage("PDF 输出完成，报告已标记为已审并锁定。");
    await refresh();
  };

  const unlockReviewReport = async () => {
    if (!canAdminRole || !selectedReviewReportId) return;
    const detail = await postJson<ReviewReportDetail>(`/reports/${encodeURIComponent(selectedReviewReportId)}/unlock`);
    setReviewDetail(detail);
    setReviewExportResult(null);
    setReviewMessage("已解审核，报告恢复为可编辑状态。");
    await refresh();
  };

  const deleteReviewReport = async () => {
    if (!canReviewRole || !selectedReviewReportId) return;
    await deleteJson<{ status: string; report_id: string }>(`/reports/${encodeURIComponent(selectedReviewReportId)}`);
    setSelectedReviewReportId("");
    setSelectedReviewPageName("");
    setReviewDetail(null);
    setReviewPageContent(null);
    setReviewExportResult(null);
    setReviewMessage("报告已删除。");
    await refresh();
  };

  if (!authChecked) {
    return <div className="loading-screen">正在检查登录状态...</div>;
  }

  if (!currentUser) {
    return <LoginView loginError={loginError} onLogin={loginToPlatform} />;
  }

  const copy = viewCopy[activeView];

  return (
    <main className="app-shell">
      <aside className="sidebar">
        <div className="brand-block">
          <div className="brand-mark brand-logo-mark">
            <img src={awkLogoUrl} alt="安为康" />
          </div>
          <div>
            <h1>功能医学报告管理平台</h1>
            <p>多套餐研发版</p>
          </div>
        </div>
        <nav className="nav-list" aria-label="模块导航">
          {visibleNavItems.map((item) => (
            <button
              className={item.key === activeView ? "active" : ""}
              key={item.key}
              type="button"
              onClick={() => setActiveView(item.key)}
            >
              {item.icon}
              {item.label}
            </button>
          ))}
        </nav>
        <div className="sidebar-footer">
          <div className="sidebar-user-card">
            <div className="sidebar-user-avatar">{(currentUser.display_name || currentUser.username).slice(0, 1)}</div>
            <div>
              <b>{currentUser.display_name || currentUser.username}</b>
              <span>{currentUser.role_label}</span>
            </div>
            <button className="sidebar-logout-button" onClick={() => void logout()} title="退出登录" type="button">
              <LogOut size={17} />
            </button>
          </div>
        </div>
      </aside>

      <section className="content">
        <header className="topbar">
          <div className="topbar-title-group">
            <button className="topbar-menu-button" type="button" title="导航菜单">
              <Menu size={20} />
            </button>
            <div>
              <h2>{copy.title}</h2>
              <p>{copy.subtitle}</p>
            </div>
          </div>
          <div className="topbar-actions">
            <label className="topbar-search">
              <Search size={16} />
              <input placeholder="搜索报告、患者、任务..." />
            </label>
            <label className="select-control">
              <span>当前套餐</span>
              <select value={selectedPackageCode} onChange={(event) => setSelectedPackageCode(event.target.value)}>
                {packages.map((item) => (
                  <option key={item.package_code} value={item.package_code}>
                    {packageOptionLabel(item)}
                  </option>
                ))}
              </select>
            </label>
            <button className="icon-button" onClick={() => void refresh()} title="刷新">
              <RefreshCcw size={18} />
            </button>
            <button className="icon-button" title="系统消息" type="button">
              <Bell size={18} />
            </button>
          </div>
        </header>

        {error && <div className="error-banner">后端连接失败：{error}</div>}

        {activeView === "dashboard" && (
          <DashboardView
            reports={reviewReports}
            jobs={jobs}
            users={accountUsers}
            currentUser={currentUser}
            selectedPackage={selectedPackage}
            selectedPackageCode={selectedPackageCode}
            health={health}
            aiConfig={aiConfig}
            onOpenReview={() => setActiveView("review")}
            onOpenBatch={() => setActiveView("batch")}
          />
        )}

        {activeView === "batch" && (
          <>
            <BatchActions
              selectedPackageCode={selectedPackageCode}
              documents={importedDocuments}
              importMessage={importMessage}
              canRunExport={canAdminRole}
              onImportPdfs={importPdfs}
              onCreateJob={createBatchJob}
            />
            <JobProgressPanel jobs={jobs} />
            <OcrLogPanel
              logs={ocrLogs}
              pagination={ocrLogPagination}
              onPageChange={(page) => setOcrLogPage(page)}
            />
          </>
        )}

        {activeView === "packages" && (
          <PackageConfigView
            config={packageConfig}
            logs={ocrLogs}
            preview={renderPreview}
            aiResult={aiInterpretResult}
            onRenderPreview={renderFromLatestOcr}
            onAiInterpret={runAiInterpret}
          />
        )}

        {activeView === "review" && (
          <ReviewView
            reports={reviewReports}
            detail={reviewDetail}
            selectedReportId={selectedReviewReportId}
            selectedPageName={selectedReviewPageName}
            pageContent={reviewPageContent}
            exportResult={reviewExportResult}
            reviewMessage={reviewMessage}
            canReview={canReviewRole}
            canUnlock={canAdminRole}
            onSelectReport={selectReviewReport}
            onSelectPage={selectReviewPage}
            onSavePage={saveReviewPage}
            onExportPdf={exportReviewPdf}
            onUnlockReport={unlockReviewReport}
            onDeleteReport={deleteReviewReport}
          />
        )}

        {activeView === "accounts" && (
          <AccountManagementView
            users={accountUsers}
            currentUser={currentUser}
            accountMessage={accountMessage}
            onCreateUser={createAccount}
            onUpdateUser={updateAccount}
            onDeleteUser={deleteAccount}
          />
        )}

        {activeView === "admin" && (
          <AdminView
            aiConfig={aiConfig}
            credentials={credentials}
            apiKey={apiKey}
            credentialLabel={credentialLabel}
            aiModel={aiModel}
            aiBaseUrl={aiBaseUrl}
            aiTestResult={aiTestResult}
            onApiKeyChange={setApiKey}
            onCredentialLabelChange={setCredentialLabel}
            onAiModelChange={setAiModel}
            onAiBaseUrlChange={setAiBaseUrl}
            onSaveCredential={saveDeepseekCredential}
            onTestConnection={testAiConnection}
          />
        )}

      </section>
    </main>
  );
}

createRoot(document.getElementById("root")!).render(<App />);
