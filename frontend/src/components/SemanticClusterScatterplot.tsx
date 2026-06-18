import { useState } from 'react'

export type SemanticClusterPoint = {
  x: number
  y: number
  topic_id: number
  parent_category: string | null
  category: string | null
  confidence: number | null
  is_outlier: boolean
  keywords: string[]
  participant_type: 'student' | 'educator' | 'social-media'
}

export type SemanticClusterCategory = {
  topic_id: number
  parent_category: string | null
  category: string | null
  count: number
  keywords: string[]
}

export type SemanticClusterPlot = {
  projection_version: string | null
  total_points: number
  displayed_points: number
  categories: SemanticClusterCategory[]
  points: SemanticClusterPoint[]
}

type SemanticClusterScatterplotProps = {
  plot: SemanticClusterPlot | undefined
  minimumGroupSize: number
}

type SemanticClusterGroup = {
  key: string
  label: string
  count: number
  topicIds: number[]
  categories: string[]
  keywords: string[]
}

const colors = [
  '#184f3e',
  '#e96d4e',
  '#b28b2d',
  '#735d9a',
  '#34849a',
  '#9b4f68',
  '#567246',
  '#a55b33',
]

function axisTicks(minimum: number, maximum: number): number[] {
  return Array.from(
    { length: 5 },
    (_, index) => minimum + ((maximum - minimum) * index) / 4,
  )
}

function categoryGroupKey(category: SemanticClusterCategory): string {
  return category.parent_category
    ? `parent:${category.parent_category}`
    : `topic:${category.topic_id}`
}

function groupCategories(
  categories: SemanticClusterCategory[],
): SemanticClusterGroup[] {
  const groups = new Map<string, SemanticClusterGroup>()

  for (const category of categories) {
    const key = categoryGroupKey(category)
    const existing = groups.get(key)
    const categoryLabel =
      category.category ?? `Topic ${category.topic_id}`

    if (existing) {
      existing.count += category.count
      existing.topicIds.push(category.topic_id)
      if (!existing.categories.includes(categoryLabel)) {
        existing.categories.push(categoryLabel)
      }
      for (const keyword of category.keywords) {
        if (!existing.keywords.includes(keyword)) {
          existing.keywords.push(keyword)
        }
      }
      continue
    }

    groups.set(key, {
      key,
      label: category.parent_category ?? categoryLabel,
      count: category.count,
      topicIds: [category.topic_id],
      categories: [categoryLabel],
      keywords: [...category.keywords],
    })
  }

  return [...groups.values()].sort(
    (left, right) =>
      right.count - left.count || left.label.localeCompare(right.label),
  )
}

function SemanticClusterScatterplot({
  plot,
  minimumGroupSize,
}: SemanticClusterScatterplotProps) {
  const [selectedGroup, setSelectedGroup] = useState<string | null>(null)
  const categories = plot?.categories ?? []
  const points = plot?.points ?? []
  const groups = groupCategories(categories)
  const activeGroupKey =
    selectedGroup !== null &&
    groups.some((group) => group.key === selectedGroup)
      ? selectedGroup
      : null
  const activeGroup = groups.find(
    (group) => group.key === activeGroupKey,
  )
  const colorByGroup = new Map(
    groups.map((group, index) => [
      group.key,
      colors[index % colors.length],
    ]),
  )
  const groupByTopic = new Map(
    groups.flatMap((group) =>
      group.topicIds.map((topicId) => [topicId, group.key] as const),
    ),
  )

  const rawX = points.map((point) => point.x)
  const rawY = points.map((point) => point.y)
  const rawMinX = rawX.reduce(
    (minimum, value) => Math.min(minimum, value),
    Number.POSITIVE_INFINITY,
  )
  const rawMaxX = rawX.reduce(
    (maximum, value) => Math.max(maximum, value),
    Number.NEGATIVE_INFINITY,
  )
  const rawMinY = rawY.reduce(
    (minimum, value) => Math.min(minimum, value),
    Number.POSITIVE_INFINITY,
  )
  const rawMaxY = rawY.reduce(
    (maximum, value) => Math.max(maximum, value),
    Number.NEGATIVE_INFINITY,
  )
  const xPadding = Math.max(0.2, (rawMaxX - rawMinX) * 0.08)
  const yPadding = Math.max(0.2, (rawMaxY - rawMinY) * 0.08)
  const minX = Number.isFinite(rawMinX) ? rawMinX - xPadding : 0
  const maxX = Number.isFinite(rawMaxX) ? rawMaxX + xPadding : 1
  const minY = Number.isFinite(rawMinY) ? rawMinY - yPadding : 0
  const maxY = Number.isFinite(rawMaxY) ? rawMaxY + yPadding : 1

  const width = 900
  const height = 430
  const left = 58
  const right = 24
  const top = 22
  const bottom = 52
  const chartWidth = width - left - right
  const chartHeight = height - top - bottom
  const scaleX = (value: number) =>
    left + ((value - minX) / Math.max(maxX - minX, 1)) * chartWidth
  const scaleY = (value: number) =>
    top +
    chartHeight -
    ((value - minY) / Math.max(maxY - minY, 1)) * chartHeight
  const xTicks = axisTicks(minX, maxX)
  const yTicks = axisTicks(minY, maxY)

  return (
    <article className="dashboard-card semantic-cluster-card">
      <header className="dashboard-card__header">
        <div>
          <span>Semantic clustering</span>
          <h2>Two-dimensional narrative map</h2>
        </div>
        <span className="dashboard-card__badge">
          {plot?.displayed_points ?? 0} of {plot?.total_points ?? 0} points shown
        </span>
      </header>

      <p className="semantic-cluster-card__intro">
        Each anonymous point is a classifier output positioned in the saved
        embedding projection. Topic tags combine related classifier topics by
        parent category and are shown from {minimumGroupSize} stored record
        onward.
      </p>

      {points.length > 0 ? (
        <div className="semantic-cluster-layout">
          <div className="semantic-cluster-plot">
            <svg
              aria-label="Two-dimensional semantic cluster scatterplot"
              role="img"
              viewBox={`0 0 ${width} ${height}`}
            >
              <title>
                Anonymous message classifications grouped by semantic topic
              </title>
              {xTicks.map((tick) => (
                <g key={`x-${tick}`}>
                  <line
                    className="semantic-cluster-grid"
                    x1={scaleX(tick)}
                    x2={scaleX(tick)}
                    y1={top}
                    y2={top + chartHeight}
                  />
                  <text
                    className="semantic-cluster-axis-label"
                    x={scaleX(tick)}
                    y={height - 24}
                    textAnchor="middle"
                  >
                    {tick.toFixed(1)}
                  </text>
                </g>
              ))}
              {yTicks.map((tick) => (
                <g key={`y-${tick}`}>
                  <line
                    className="semantic-cluster-grid"
                    x1={left}
                    x2={left + chartWidth}
                    y1={scaleY(tick)}
                    y2={scaleY(tick)}
                  />
                  <text
                    className="semantic-cluster-axis-label"
                    x={left - 12}
                    y={scaleY(tick) + 4}
                    textAnchor="end"
                  >
                    {tick.toFixed(1)}
                  </text>
                </g>
              ))}
              <text
                className="semantic-cluster-axis-title"
                x={left + chartWidth / 2}
                y={height - 4}
                textAnchor="middle"
              >
                Projection X
              </text>
              <text
                className="semantic-cluster-axis-title"
                textAnchor="middle"
                transform={`translate(14 ${top + chartHeight / 2}) rotate(-90)`}
              >
                Projection Y
              </text>
              {points.map((point, index) => {
                const groupKey = groupByTopic.get(point.topic_id)
                const color =
                  (groupKey && colorByGroup.get(groupKey)) ?? '#7c8982'
                const isActive =
                  activeGroupKey === null || groupKey === activeGroupKey
                const title = [
                  point.category ?? `Topic ${point.topic_id}`,
                  point.parent_category,
                  point.keywords.join(', '),
                  point.confidence === null
                    ? null
                    : `Confidence ${(point.confidence * 100).toFixed(0)}%`,
                ]
                  .filter(Boolean)
                  .join(' | ')

                return (
                  <circle
                    className="semantic-cluster-point"
                    cx={scaleX(point.x)}
                    cy={scaleY(point.y)}
                    fill={color}
                    key={`${point.topic_id}-${index}`}
                    onClick={() => setSelectedGroup(groupKey ?? null)}
                    opacity={isActive ? 0.82 : 0.16}
                    r={isActive ? 5 : 3.5}
                  >
                    <title>{title}</title>
                  </circle>
                )
              })}
            </svg>
            <div className="semantic-cluster-plot__footer">
              <span>
                Projection: {plot?.projection_version ?? 'unavailable'}
              </span>
              <span>Circle = anonymized classification event</span>
            </div>
          </div>

          <div className="semantic-cluster-tags">
            <span className="semantic-cluster-tags__label">
              Grouped topic tags
            </span>
            <button
              aria-pressed={activeGroupKey === null}
              className={activeGroupKey === null ? 'is-active' : ''}
              onClick={() => setSelectedGroup(null)}
              type="button"
            >
              <i style={{ background: '#7c8982' }} />
              <span>
                <strong>All</strong>
                <small>All grouped topics</small>
              </span>
              <b>{points.length}</b>
            </button>
            {groups.map((group) => (
              <button
                aria-pressed={activeGroupKey === group.key}
                className={
                  activeGroupKey === group.key ? 'is-active' : ''
                }
                key={group.key}
                onClick={() => setSelectedGroup(group.key)}
                type="button"
              >
                <i
                  style={{
                    background: colorByGroup.get(group.key) ?? '#7c8982',
                  }}
                />
                <span>
                  <strong>{group.label}</strong>
                  <small>
                    {group.topicIds.length}{' '}
                    {group.topicIds.length === 1 ? 'topic' : 'topics'}
                  </small>
                </span>
                <b>{group.count}</b>
              </button>
            ))}

            {activeGroup ? (
              <div className="semantic-cluster-detail">
                <span>Selected topic group</span>
                <strong>{activeGroup.label}</strong>
                <p>
                  {activeGroup.count} records across{' '}
                  {activeGroup.topicIds.length}{' '}
                  {activeGroup.topicIds.length === 1 ? 'topic' : 'topics'}
                </p>
                <div>
                  {activeGroup.categories.map((category) => (
                    <small key={category}>{category}</small>
                  ))}
                </div>
                {activeGroup.keywords.length > 0 && (
                  <p className="semantic-cluster-detail__keywords">
                    Keywords: {activeGroup.keywords.slice(0, 8).join(', ')}
                  </p>
                )}
              </div>
            ) : null}
          </div>
        </div>
      ) : (
        <p className="dashboard-empty-state semantic-cluster-empty">
          No semantic classifications match the selected filters.
        </p>
      )}
    </article>
  )
}

export default SemanticClusterScatterplot
