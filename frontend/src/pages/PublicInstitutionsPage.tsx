import { useEffect, useState } from 'react'

import CountrySignalMap from '../components/CountrySignalMap'
import IncidentReviewQueue from '../components/IncidentReviewQueue'
import SemanticClusterScatterplot, {
  type SemanticClusterPlot,
} from '../components/SemanticClusterScatterplot'
import SocialMediaCsvImport from '../components/SocialMediaCsvImport'
import { availableLanguages, euCountries } from '../data/euCountries'
import {
  type DashboardParticipantType,
  type DashboardSeverity,
  dashboardSeverityOptions,
} from '../services/dashboardProfileLinks'
import { analyticsChannelName } from '../services/incidentAnalytics'

type TimeRange = '30d' | '90d' | '12m'
type ParticipantType = DashboardParticipantType
type SeverityFilter = DashboardSeverity

type InitialDashboardFilters = {
  timeRange: TimeRange
  country: string
  regionArea: string
  language: string
  participantType: ParticipantType | ''
  severity: SeverityFilter | ''
  openSelections: boolean
}

type DistributionItem = {
  key: string
  label: string
  count: number
  percentage: number
}

type TrendPoint = {
  period_start: string
  student: number
  educator: number
  social_media: number
  total: number
}

type DashboardSummary = {
  generated_at: string
  period: { start: string; end: string; bucket: string }
  filters: {
    time_range: TimeRange
    country: string | null
    region_area: string | null
    language: string | null
    participant_type: ParticipantType | null
    severity: SeverityFilter | null
    minimum_group_size: number
  }
  totals: {
    analysed_conversations: number
    incident_signals: number
    human_review_rate: number
    pending_reviews: number
    completed_reviews: number
    review_completion_rate: number
    constructive_response_rate: number
    previous_period_change: number | null
  }
  regions: DistributionItem[]
  trend: TrendPoint[]
  sources: DistributionItem[]
  severity: DistributionItem[]
  semantic_barriers: DistributionItem[]
  bridge_promoters: DistributionItem[]
  age_bands: DistributionItem[]
  languages: DistributionItem[]
  semantic_clusters: SemanticClusterPlot
}

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? '/api/v1'
const ragApiBaseUrl = import.meta.env.VITE_RAG_API_BASE_URL ?? '/rag-api'
const classifierApiBaseUrl =
  import.meta.env.VITE_CLASSIFIER_API_BASE_URL ?? '/classifier-api'
const configuredSocialPostPageUrl =
  import.meta.env.VITE_SOCIAL_POST_PAGE_URL ?? ''
const numberFormatter = new Intl.NumberFormat()

const severityTones: Record<string, string> = {
  'ordinary-political-expression': 'green',
  'offensive-or-harmful-expression': 'yellow',
  'potential-hate-speech': 'coral',
  'high-severity-incitement-risk': 'red',
}

const sourceColors: Record<string, string> = {
  student: '#184f3e',
  educator: '#e96d4e',
  'social-media': '#7868b5',
}

const languageColors = ['#184f3e', '#e96d4e', '#efc861', '#9caaa2']

function isTimeRange(value: string | null): value is TimeRange {
  return value === '30d' || value === '90d' || value === '12m'
}

function isParticipantType(value: string | null): value is ParticipantType {
  return (
    value === 'student' ||
    value === 'educator' ||
    value === 'social-media'
  )
}

function isSeverityFilter(value: string | null): value is SeverityFilter {
  return dashboardSeverityOptions.some((option) => option.value === value)
}

function initialDashboardFilters(): InitialDashboardFilters {
  const params = new URLSearchParams(window.location.search)
  const timeRange = params.get('time_range')
  const participantType = params.get('participant_type')
  const severity = params.get('severity')

  return {
    timeRange: isTimeRange(timeRange) ? timeRange : '30d',
    country: params.get('country') ?? 'Cyprus',
    regionArea: params.get('region_area') ?? '',
    language: params.get('language') ?? '',
    participantType: isParticipantType(participantType)
      ? participantType
      : '',
    severity: isSeverityFilter(severity) ? severity : '',
    openSelections:
      params.get('open_selections') === 'true' ||
      params.get('open_reviews') === 'true',
  }
}

function linePoints(data: number[], max: number): string {
  const width = 560
  const height = 160

  if (data.length === 0) return ''
  if (data.length === 1) {
    return `0,${height - (data[0] / max) * height}`
  }

  return data
    .map((value, index) => {
      const x = (index / (data.length - 1)) * width
      const y = height - (value / max) * height
      return `${x},${y}`
    })
    .join(' ')
}

function formatPercentage(value: number): string {
  return `${value.toFixed(value % 1 === 0 ? 0 : 1)}%`
}

function formatGeneratedAt(value: string): string {
  return new Intl.DateTimeFormat(undefined, {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(value))
}

function formatTrendLabel(value: string, bucket: string): string {
  return new Intl.DateTimeFormat(undefined, {
    day: bucket === 'week' ? 'numeric' : undefined,
    month: 'short',
  }).format(new Date(`${value}T00:00:00`))
}

function donutBackground(items: DistributionItem[]): string {
  if (items.length === 0) {
    return 'radial-gradient(circle at center, white 0 43%, transparent 44%), #edf0ec'
  }

  let cursor = 0
  const segments = items.map((item, index) => {
    const start = cursor
    cursor += item.percentage
    return `${languageColors[index % languageColors.length]} ${start}% ${cursor}%`
  })

  return [
    'radial-gradient(circle at center, white 0 43%, transparent 44%)',
    `conic-gradient(${segments.join(', ')})`,
  ].join(', ')
}

function PublicInstitutionsPage() {
  const initialFilters = initialDashboardFilters()
  const socialPostPageUrl =
    configuredSocialPostPageUrl ||
    `${window.location.origin}/how-it-works`
  const [timeRange, setTimeRange] = useState<TimeRange>(
    initialFilters.timeRange,
  )
  const [country, setCountry] = useState(initialFilters.country)
  const [regionArea, setRegionArea] = useState(initialFilters.regionArea)
  const [language, setLanguage] = useState(initialFilters.language)
  const [participantType, setParticipantType] = useState<
    ParticipantType | ''
  >(initialFilters.participantType)
  const [severity, setSeverity] = useState<SeverityFilter | ''>(
    initialFilters.severity,
  )
  const [dashboard, setDashboard] = useState<DashboardSummary | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState('')
  const [reloadToken, setReloadToken] = useState(0)
  const [isSelectionWorkspaceOpen, setIsSelectionWorkspaceOpen] = useState(
    initialFilters.openSelections,
  )
  const [isCsvImportOpen, setIsCsvImportOpen] = useState(false)

  useEffect(() => {
    const refresh = () => setReloadToken((value) => value + 1)
    const intervalId = window.setInterval(refresh, 30_000)
    const channel =
      typeof BroadcastChannel === 'undefined'
        ? null
        : new BroadcastChannel(analyticsChannelName)

    if (channel) {
      channel.onmessage = refresh
    }
    window.addEventListener('focus', refresh)

    return () => {
      window.clearInterval(intervalId)
      window.removeEventListener('focus', refresh)
      channel?.close()
    }
  }, [])

  useEffect(() => {
    const controller = new AbortController()
    const params = new URLSearchParams({
      time_range: timeRange,
      minimum_group_size: '1',
    })
    if (country) params.set('country', country)
    if (regionArea) params.set('region_area', regionArea)
    if (language) params.set('language', language)
    if (participantType) params.set('participant_type', participantType)
    if (severity) params.set('severity', severity)

    async function loadDashboard() {
      setIsLoading(true)
      setError('')

      try {
        const response = await fetch(
          `${apiBaseUrl}/dashboard/summary?${params.toString()}`,
          { cache: 'no-store', signal: controller.signal },
        )
        if (!response.ok) {
          throw new Error(`Dashboard API returned ${response.status}.`)
        }
        setDashboard((await response.json()) as DashboardSummary)
      } catch (requestError) {
        if (!controller.signal.aborted) {
          setDashboard(null)
          setError(
            requestError instanceof Error
              ? requestError.message
              : 'Dashboard data could not be loaded.',
          )
        }
      } finally {
        if (!controller.signal.aborted) setIsLoading(false)
      }
    }

    void loadDashboard()
    return () => controller.abort()
  }, [
    country,
    language,
    participantType,
    regionArea,
    reloadToken,
    severity,
    timeRange,
  ])

  useEffect(() => {
    if (!isSelectionWorkspaceOpen) return

    const animationFrame = window.requestAnimationFrame(() => {
      document
        .getElementById('incident-selections')
        ?.scrollIntoView({ behavior: 'smooth', block: 'start' })
    })
    return () => window.cancelAnimationFrame(animationFrame)
  }, [isSelectionWorkspaceOpen])

  useEffect(() => {
    if (!isCsvImportOpen) return

    const animationFrame = window.requestAnimationFrame(() => {
      document
        .getElementById('social-media-import')
        ?.scrollIntoView({ behavior: 'smooth', block: 'start' })
    })
    return () => window.cancelAnimationFrame(animationFrame)
  }, [isCsvImportOpen])

  const totals = dashboard?.totals
  const studentTrend = dashboard?.trend.map((point) => point.student) ?? []
  const educatorTrend = dashboard?.trend.map((point) => point.educator) ?? []
  const socialMediaTrend =
    dashboard?.trend.map((point) => point.social_media) ?? []
  const trendMax =
    Math.max(1, ...studentTrend, ...educatorTrend, ...socialMediaTrend) + 2
  const regions = dashboard?.regions.slice(0, 5) ?? []
  const selectedCountry = euCountries.find((item) => item.name === country)
  const otherLanguages = availableLanguages.filter(
    (item) => !selectedCountry?.officialLanguages.includes(item),
  )
  const ageMax = Math.max(
    1,
    ...(dashboard?.age_bands.map((age) => age.percentage) ?? []),
  )
  const trendLabelIndexes = dashboard?.trend.length
    ? Array.from(
        new Set([
          0,
          Math.floor((dashboard.trend.length - 1) / 2),
          dashboard.trend.length - 1,
        ]),
      )
    : []
  const change = totals?.previous_period_change

  return (
    <div className="institution-page">
      <aside className="institution-sidebar">
        <a className="brand institution-brand" href="/">
          <span className="brand__mark" aria-hidden="true">
            <span />
            <span />
            <span />
          </span>
          <span>Civic Bridge AI</span>
        </a>

        <div className="institution-sidebar__identity">
          <span>Institution workspace</span>
          <strong>Democratic Dialogue Observatory</strong>
          <small>{country || 'EU'} pilot environment</small>
        </div>

        <nav className="institution-nav" aria-label="Dashboard sections">
          <a className="is-active" href="#overview"><span>01</span>Overview</a>
          <a href="#geography"><span>02</span>Geography</a>
          <a href="#analysis"><span>03</span>Narrative analysis</a>
          <a href="#demographics"><span>04</span>Education signals</a>
          <a href="#safeguards-dashboard"><span>05</span>Safeguards</a>
        </nav>

        <div className="institution-sidebar__notice">
          <span aria-hidden="true">i</span>
          <p>
            Records are aggregated by the backend. No individual conversation
            or exact location is exposed.
          </p>
        </div>

        <a className="institution-sidebar__back" href="/">
          &larr; Back to public overview
        </a>
      </aside>

      <main className="institution-main" aria-busy={isLoading}>
        <header className="institution-header" id="overview">
          <div>
            <p className="eyebrow">Aggregate democratic security signals</p>
            <h1>Platform intelligence dashboard</h1>
            <p>
              Privacy-preserving insights from student conversations, educator
              incident descriptions, and the platform&apos;s structured
              analysis pipeline.
            </p>
          </div>

          <div className="institution-header__meta">
            <span
              className={`institution-data-status${error ? ' is-error' : ''}`}
            >
              <span aria-hidden="true" />
              {error
                ? 'Data unavailable'
                : isLoading
                  ? 'Refreshing data'
                  : 'API data refreshed'}
            </span>
            <strong>
              {dashboard
                ? formatGeneratedAt(dashboard.generated_at)
                : 'Waiting for API'}
            </strong>
            <button
              className="social-import-open-button"
              onClick={() => setIsCsvImportOpen(true)}
              type="button"
            >
              Import social media CSV
            </button>
          </div>
        </header>

        <section className="institution-filters" aria-label="Dashboard filters">
          <label>
            <span>Country context</span>
            <select
              value={country}
              onChange={(event) => {
                setCountry(event.target.value)
                setRegionArea('')
                setLanguage('')
              }}
            >
              <option value="">All countries</option>
              {euCountries.map((item) => (
                <option key={item.name} value={item.name}>
                  {item.name}
                </option>
              ))}
            </select>
          </label>
          <label>
            <span>Regional area</span>
            <input
              onChange={(event) => setRegionArea(event.target.value)}
              placeholder="All regional areas"
              type="text"
              value={regionArea}
            />
          </label>
          <label>
            <span>Language</span>
            <select
              value={language}
              onChange={(event) => setLanguage(event.target.value)}
            >
              <option value="">All languages</option>
              {selectedCountry && (
                <optgroup label={`Official in ${selectedCountry.name}`}>
                  {selectedCountry.officialLanguages.map((item) => (
                    <option key={item} value={item}>
                      {item}
                    </option>
                  ))}
                </optgroup>
              )}
              {selectedCountry && otherLanguages.length > 0 && (
                <optgroup label="Other available languages">
                  {otherLanguages.map((item) => (
                    <option key={item} value={item}>
                      {item}
                    </option>
                  ))}
                </optgroup>
              )}
              {!selectedCountry &&
                availableLanguages.map((item) => (
                  <option key={item} value={item}>
                    {item}
                  </option>
                ))}
            </select>
          </label>
          <label>
            <span>Input source</span>
            <select
              value={participantType}
              onChange={(event) =>
                setParticipantType(event.target.value as ParticipantType | '')
              }
            >
              <option value="">All sources</option>
              <option value="student">Students / young people</option>
              <option value="educator">Educators</option>
              <option value="social-media">Social media posts</option>
            </select>
          </label>
          <label>
            <span>Incident type</span>
            <select
              value={severity}
              onChange={(event) =>
                setSeverity(event.target.value as SeverityFilter | '')
              }
            >
              <option value="">All incident types</option>
              {dashboardSeverityOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
          <div className="institution-range" aria-label="Time range">
            {(
              [
                ['30d', '30 days'],
                ['90d', '90 days'],
                ['12m', '12 months'],
              ] as Array<[TimeRange, string]>
            ).map(([value, label]) => (
              <button
                className={timeRange === value ? 'is-active' : ''}
                key={value}
                onClick={() => setTimeRange(value)}
                type="button"
              >
                {label}
              </button>
            ))}
          </div>
        </section>

        {isCsvImportOpen && (
          <SocialMediaCsvImport
            apiBaseUrl={apiBaseUrl}
            classifierApiBaseUrl={classifierApiBaseUrl}
            onClose={() => setIsCsvImportOpen(false)}
            onImported={() => setReloadToken((value) => value + 1)}
            ragApiBaseUrl={ragApiBaseUrl}
          />
        )}

        {error && (
          <div
            className="dashboard-api-message dashboard-api-message--error"
            role="alert"
          >
            <span>{error}</span>
            <button
              type="button"
              onClick={() => setReloadToken((value) => value + 1)}
            >
              Retry
            </button>
          </div>
        )}
        {isLoading && !dashboard && (
          <div className="dashboard-api-message">
            Loading aggregate dashboard data...
          </div>
        )}

        <section className="institution-kpis" aria-label="Key statistics">
          <article>
            <span>Analysis events</span>
            <strong>
              {numberFormatter.format(totals?.analysed_conversations ?? 0)}
            </strong>
            <small>
              {change == null
                ? 'No prior-period baseline'
                : `${change > 0 ? '+' : ''}${change}% from previous period`}
            </small>
          </article>
          <article>
            <span>Incident signals</span>
            <strong>
              {numberFormatter.format(totals?.incident_signals ?? 0)}
            </strong>
            <small>Aggregated across selected intake channels</small>
          </article>
          <article>
            <span>Selectable incidents</span>
            <strong>
              {numberFormatter.format(totals?.pending_reviews ?? 0)}
            </strong>
            <small>Available for educational or public content generation</small>
          </article>
        </section>

        <section className="institution-dashboard-grid" id="geography">
          <article className="dashboard-card dashboard-map-card">
            <header className="dashboard-card__header">
              <div>
                <span>Geographic distribution</span>
                <h2>{country || 'EU'} incident signals</h2>
              </div>
              <span className="dashboard-card__badge">Regional level only</span>
            </header>

            <div className="dashboard-map-layout">
              <div className="country-map-panel">
                <CountrySignalMap country={country} regions={regions} />
                <div className="country-map-legend">
                  <span>Lower volume</span>
                  <span className="map-legend-dot map-legend-dot--small" />
                  <span className="map-legend-dot map-legend-dot--large" />
                  <span>Higher volume</span>
                </div>
              </div>

              {regions.length > 0 ? (
                <ol className="region-ranking">
                  {regions.map((region, index) => (
                    <li key={region.key}>
                      <span>{String(index + 1).padStart(2, '0')}</span>
                      <div>
                        <strong>{region.label}</strong>
                        <small>
                          {numberFormatter.format(region.count)} signals
                        </small>
                      </div>
                      <b>{formatPercentage(region.percentage)}</b>
                    </li>
                  ))}
                </ol>
              ) : (
                <p className="dashboard-empty-state">
                  No incident signals match the selected filters.
                </p>
              )}
            </div>
          </article>

          <article className="dashboard-card dashboard-trend-card">
            <header className="dashboard-card__header">
              <div>
                <span>Signal trend</span>
                <h2>
                  {dashboard?.period.bucket === 'month' ? 'Monthly' : 'Weekly'}{' '}
                  incident volume
                </h2>
              </div>
              <strong className="dashboard-trend-total">
                {numberFormatter.format(totals?.incident_signals ?? 0)}
              </strong>
            </header>

            <div className="trend-legend">
              <span><i className="is-student" />Students</span>
              <span><i className="is-educator" />Educators</span>
              <span><i className="is-social-media" />Social media</span>
            </div>

            <svg
              className="trend-chart"
              aria-label="Incident trend for students and educators"
              role="img"
              viewBox="0 0 600 210"
            >
              {[0, 1, 2, 3, 4].map((line) => (
                <line
                  className="trend-chart__grid"
                  key={line}
                  x1="20"
                  x2="580"
                  y1={20 + line * 40}
                  y2={20 + line * 40}
                />
              ))}
              <g transform="translate(20 20)">
                <polyline
                  className="trend-chart__line trend-chart__line--student"
                  points={linePoints(studentTrend, trendMax)}
                />
                <polyline
                  className="trend-chart__line trend-chart__line--educator"
                  points={linePoints(educatorTrend, trendMax)}
                />
                <polyline
                  className="trend-chart__line trend-chart__line--social-media"
                  points={linePoints(socialMediaTrend, trendMax)}
                />
              </g>
              <g className="trend-chart__labels">
                {trendLabelIndexes.map((index) => {
                  const point = dashboard?.trend[index]
                  const totalPoints = dashboard?.trend.length ?? 1
                  const x =
                    20 + (index / Math.max(1, totalPoints - 1)) * 560
                  return point ? (
                    <text
                      key={point.period_start}
                      x={x}
                      y="205"
                      textAnchor={
                        index === 0
                          ? 'start'
                          : index === totalPoints - 1
                            ? 'end'
                            : 'middle'
                      }
                    >
                      {formatTrendLabel(
                        point.period_start,
                        dashboard?.period.bucket ?? 'week',
                      )}
                    </text>
                  ) : null
                })}
              </g>
            </svg>

            <div className="source-split">
              {dashboard?.sources.map((source) => (
                <div key={source.key}>
                  <span
                    style={{
                      background: sourceColors[source.key] ?? '#9caaa2',
                    }}
                  />
                  <strong>{formatPercentage(source.percentage)}</strong>
                  <small>{source.label}</small>
                </div>
              ))}
            </div>
          </article>
        </section>

        <section className="analysis-dashboard" id="analysis">
          <div className="analysis-dashboard__heading">
            <div>
              <p className="eyebrow">
                Structured analysis &middot; Aggregated
              </p>
              <h2>From individual signals to system-level understanding.</h2>
            </div>
            <p>
              Graduated severity, semantic-barrier, and bridge-promoter
              analysis is combined here without exposing individual messages.
            </p>
          </div>

          <div className="analysis-dashboard__grid">
            <article className="dashboard-card severity-dashboard-card">
              <header className="dashboard-card__header">
                <div>
                  <span>Detection</span>
                  <h2>Graduated severity distribution</h2>
                </div>
                <span className="dashboard-card__badge">
                  {numberFormatter.format(
                    totals?.analysed_conversations ?? 0,
                  )}{' '}
                  analysis events
                </span>
              </header>

              <div className="severity-stack" aria-hidden="true">
                {dashboard?.severity.map((tier) => (
                  <span
                    className={`severity-stack__${
                      severityTones[tier.key] ?? 'green'
                    }`}
                    key={tier.key}
                    style={{ width: `${tier.percentage}%` }}
                  />
                ))}
              </div>

              <div className="severity-dashboard-list">
                {dashboard?.severity.map((tier) => (
                  <div key={tier.key}>
                    <span
                      className={`severity-dot severity-dot--${
                        severityTones[tier.key] ?? 'green'
                      }`}
                    />
                    <p>{tier.label}</p>
                    <strong>{formatPercentage(tier.percentage)}</strong>
                    <small>{numberFormatter.format(tier.count)}</small>
                  </div>
                ))}
              </div>
            </article>

            <article className="dashboard-card narrative-card">
              <header className="dashboard-card__header">
                <div>
                  <span>Interpretation</span>
                  <h2>Semantic barriers detected</h2>
                </div>
              </header>
              <div className="horizontal-bars">
                {dashboard?.semantic_barriers.length ? (
                  dashboard.semantic_barriers.map((barrier) => (
                    <div key={barrier.key}>
                      <p>
                        <span>{barrier.label}</span>
                        <strong>{formatPercentage(barrier.percentage)}</strong>
                      </p>
                      <span className="horizontal-bars__track">
                        <span
                          className="horizontal-bars__fill horizontal-bars__fill--barrier"
                          style={{ width: `${barrier.percentage}%` }}
                        />
                      </span>
                    </div>
                  ))
                ) : (
                  <p className="dashboard-empty-state">
                    No semantic barriers recorded for these events.
                  </p>
                )}
              </div>
            </article>

            <article className="dashboard-card narrative-card">
              <header className="dashboard-card__header">
                <div>
                  <span>Response</span>
                  <h2>Bridge promoters proposed</h2>
                </div>
              </header>
              <div className="horizontal-bars">
                {dashboard?.bridge_promoters.length ? (
                  dashboard.bridge_promoters.map((promoter) => (
                    <div key={promoter.key}>
                      <p>
                        <span>{promoter.label}</span>
                        <strong>{formatPercentage(promoter.percentage)}</strong>
                      </p>
                      <span className="horizontal-bars__track">
                        <span
                          className="horizontal-bars__fill horizontal-bars__fill--promoter"
                          style={{ width: `${promoter.percentage}%` }}
                        />
                      </span>
                    </div>
                  ))
                ) : (
                  <p className="dashboard-empty-state">
                    No bridge promoters recorded for these events.
                  </p>
                )}
              </div>
            </article>
          </div>

          <SemanticClusterScatterplot
            minimumGroupSize={dashboard?.filters.minimum_group_size ?? 1}
            plot={dashboard?.semantic_clusters}
          />
        </section>

        <section className="demographic-dashboard" id="demographics">
          <article className="dashboard-card">
            <header className="dashboard-card__header">
              <div>
                <span>Education context</span>
                <h2>Signals by age band</h2>
              </div>
            </header>
            <div className="vertical-bars">
              {dashboard?.age_bands.map((age) => (
                <div key={age.key}>
                  <strong>{formatPercentage(age.percentage)}</strong>
                  <span>
                    <span
                      style={{
                        height: `${Math.max(
                          6,
                          (age.percentage / ageMax) * 125,
                        )}px`,
                      }}
                    />
                  </span>
                  <small>{age.label}</small>
                </div>
              ))}
            </div>
          </article>

          <article className="dashboard-card">
            <header className="dashboard-card__header">
              <div>
                <span>Country module</span>
                <h2>Language distribution</h2>
              </div>
            </header>
            <div className="language-dashboard">
              <div
                className="language-donut"
                aria-label="Language distribution"
                style={{
                  background: donutBackground(dashboard?.languages ?? []),
                }}
              >
                <span>
                  {numberFormatter.format(
                    totals?.analysed_conversations ?? 0,
                  )}
                  <small>records</small>
                </span>
              </div>
              <ul>
                {dashboard?.languages.map((item, index) => (
                  <li key={item.key}>
                    <span
                      className="language-color"
                      style={{
                        background:
                          languageColors[index % languageColors.length],
                      }}
                    />
                    <p>{item.label}</p>
                    <strong>{formatPercentage(item.percentage)}</strong>
                  </li>
                ))}
              </ul>
            </div>
          </article>

          <article className="dashboard-card content-workspace-card">
            <header className="dashboard-card__header">
              <div>
                <span>Content generation</span>
                <h2>Incident selections</h2>
              </div>
            </header>
            <p>
              Select anonymized incidents that match the current filters and
              turn them into educational content or a public-facing post.
            </p>
            <button
              aria-controls="incident-selections"
              aria-expanded={isSelectionWorkspaceOpen}
              className="content-workspace-button"
              onClick={() =>
                setIsSelectionWorkspaceOpen((isOpen) => !isOpen)
              }
              type="button"
            >
              Select incidents for content
              <span>{numberFormatter.format(totals?.pending_reviews ?? 0)}</span>
            </button>
          </article>

        </section>

        {isSelectionWorkspaceOpen && (
          <IncidentReviewQueue
            apiBaseUrl={apiBaseUrl}
            country={country}
            language={language}
            participantType={participantType}
            ragApiBaseUrl={ragApiBaseUrl}
            regionArea={regionArea}
            refreshToken={reloadToken}
            severity={severity}
            socialPostPageUrl={socialPostPageUrl}
            timeRange={timeRange}
          />
        )}

        <section className="dashboard-safeguards" id="safeguards-dashboard">
          <div>
            <p className="eyebrow">Privacy and proportionality</p>
            <h2>Aggregate patterns, never people.</h2>
          </div>
          <ul>
            <li>
              Dashboard updates from{' '}
              {dashboard?.filters.minimum_group_size ?? 1} stored record
            </li>
            <li>No usernames, profile links, or exact locations</li>
            <li>No automated enforcement or legal determination</li>
            <li>Generated materials remain advisory and editable</li>
          </ul>
        </section>
      </main>
    </div>
  )
}

export default PublicInstitutionsPage
