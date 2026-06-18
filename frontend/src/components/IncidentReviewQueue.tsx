import { useEffect, useState } from 'react'

import {
  type ChatReference,
  type RagCitation,
  referencesFromRagResponse,
} from '../services/chatReferences'
import {
  type IncidentReviewItem,
  type IncidentReviewQueue as IncidentReviewQueueData,
  loadIncidentReviews,
} from '../services/incidentReviews'
import { saveEducatorActivityHandoff } from '../services/educatorActivityHandoff'
import type {
  DashboardParticipantType,
  DashboardSeverity,
} from '../services/dashboardProfileLinks'
import { createUuid } from '../services/uuid'

type IncidentReviewQueueProps = {
  apiBaseUrl: string
  ragApiBaseUrl: string
  socialPostPageUrl: string
  timeRange: '30d' | '90d' | '12m'
  country: string
  regionArea: string
  language: string
  participantType: DashboardParticipantType | ''
  severity: DashboardSeverity | ''
  refreshToken: number
}

type RagChatResponse = {
  reply: string
  references?: ChatReference[]
  citations?: RagCitation[]
}

function humanize(value: string): string {
  return value
    .replace(/[_-]+/g, ' ')
    .replace(/\b\w/g, (character) => character.toUpperCase())
}

function formatDate(value: string): string {
  return new Intl.DateTimeFormat(undefined, {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(value))
}

function newestIncidentFirst(
  left: IncidentReviewItem,
  right: IncidentReviewItem,
): number {
  const leftTime = Date.parse(left.completed_at)
  const rightTime = Date.parse(right.completed_at)
  const leftValue = Number.isFinite(leftTime) ? leftTime : 0
  const rightValue = Number.isFinite(rightTime) ? rightTime : 0

  return rightValue - leftValue || right.id.localeCompare(left.id)
}

async function readApiError(response: Response): Promise<string> {
  try {
    const body = (await response.json()) as { detail?: string }
    if (typeof body.detail === 'string') return body.detail
  } catch {
    // Fall back to a generic message when the API did not return JSON.
  }

  return `RAG service returned ${response.status}.`
}

function truncate(value: string, maxLength: number): string {
  const normalized = value.trim()
  if (normalized.length <= maxLength) return normalized

  return `${normalized.slice(0, Math.max(0, maxLength - 3)).trimEnd()}...`
}

function normalizeAgeBand(
  value: string,
): '6-9' | '10-13' | '14-17' | '18+' | 'mixed' {
  return value === '6-9' ||
    value === '10-13' ||
    value === '14-17' ||
    value === '18+'
    ? value
    : 'mixed'
}

function extractUrls(value: string): string[] {
  return (
    value
      .match(/https?:\/\/[^\s)\],;]+/gi)
      ?.map((url) => url.replace(/[.,]+$/, '')) ?? []
  )
}

function splitTrailingSourceSection(
  postText: string,
): { body: string; sourceSection: string } {
  const lines = postText.trim().split(/\r?\n/)
  const sourceLinePattern =
    /^\s*(?:source(?:\s+links?)?|sources?|references?)\s*:/i
  const sourceHeadingPattern =
    /^\s*(?:source(?:\s+links?)?|sources?|references?)\s*:?\s*$/i

  for (let index = lines.length - 1; index >= 0; index -= 1) {
    const line = lines[index].trim()
    if (!line) continue

    if (sourceLinePattern.test(line) || sourceHeadingPattern.test(line)) {
      return {
        body: lines.slice(0, index).join('\n').trim(),
        sourceSection: lines.slice(index).join('\n').trim(),
      }
    }

    if (extractUrls(line).length > 0) continue
    break
  }

  return { body: postText.trim(), sourceSection: '' }
}

function mergeReferenceUrls(
  postText: string,
  references: ChatReference[],
): string {
  const referenceUrls = references
    .map((reference) => reference.url?.trim())
    .filter((url): url is string => Boolean(url))
  const { body, sourceSection } = splitTrailingSourceSection(postText)
  const sourceSectionUrls = extractUrls(sourceSection)
  const uniqueReferenceUrls = Array.from(
    new Set([...referenceUrls, ...sourceSectionUrls]),
  )
  if (uniqueReferenceUrls.length === 0) return postText

  return [
    body,
    '',
    'Source links:',
    ...uniqueReferenceUrls.map((url) => url),
  ]
    .filter(Boolean)
    .join('\n')
}

function buildSocialMediaPostPrompt(
  incidents: IncidentReviewItem[],
  pageUrl: string,
): string {
  const textLimit = Math.max(160, Math.floor(1500 / incidents.length))
  const incidentDescriptions = incidents
    .map((incident, index) =>
      [
        `Incident ${index + 1}: ${
          incident.tier_label || humanize(incident.severity)
        }`,
        `Context: ${incident.region_area}, ${incident.country}; ${
          incident.language
        }; learners ${incident.student_age_band}; ${
          humanize(incident.participant_type)
        } source; ${incident.message_count} messages analysed.`,
        `Target group: ${incident.target_group || 'Not identified'}.`,
        incident.themes.length > 0
          ? `Themes: ${incident.themes.join(', ')}.`
          : '',
        incident.barriers.length > 0
          ? `Semantic barriers: ${incident.barriers
              .map((barrier) => humanize(barrier.id))
              .join(', ')}.`
          : '',
        `Anonymized incident text: ${
          truncate(incident.incident_text, textLimit) ||
          'The incident text was not recorded.'
        }`,
      ]
        .filter(Boolean)
        .join('\n'),
    )
    .join('\n\n')

  return truncate(
    [
      'Create one public-facing social media post based on the selected anonymized incidents.',
      'The post must be attractive, social-media ready, and suitable for an official education or public institution account.',
      'Use a warm, clear hook; one practical takeaway; a constructive call to action; and 1-3 relevant hashtags if they fit naturally. Keep it concise enough for LinkedIn, Facebook, or Instagram captions.',
      'Ground any legal or educational claims in European or EU-relevant standards supported by the available RAG sources, such as Council of Europe Recommendation CM/Rec(2022)16, ECHR Article 10, education/media-literacy duties, or other retrieved EU/European regulatory sources. Do not add a separate source, sources, or references section; source links are appended automatically. Do not invent article numbers, URLs, or legal claims.',
      'Do not repeat slurs or inflammatory wording. Paraphrase harm neutrally, validate affected communities, invite constructive dialogue, and point readers toward learning, reporting, or support when appropriate.',
      `Include this page link in the post as the final call to action: ${pageUrl}`,
      'Return only the finished post text, suitable for an official social media caption. Include no markdown heading.',
      '',
      'Selected incidents:',
      incidentDescriptions,
    ].join('\n'),
    3900,
  )
}

function IncidentEvidence({ incident }: { incident: IncidentReviewItem }) {
  return (
    <div className="incident-review-evidence">
      <div className="incident-review-text">
        <strong>Anonymized incident text</strong>
        <blockquote>
          {incident.incident_text ||
            'The incident text was not recorded for this older item.'}
        </blockquote>
      </div>

      <dl>
        <div>
          <dt>Target group</dt>
          <dd>{incident.target_group || 'Not identified'}</dd>
        </div>
        <div>
          <dt>Confidence</dt>
          <dd>{incident.confidence ? humanize(incident.confidence) : 'Unknown'}</dd>
        </div>
        <div>
          <dt>Messages analysed</dt>
          <dd>{incident.message_count}</dd>
        </div>
      </dl>

      {incident.themes.length > 0 && (
        <div className="incident-review-tags">
          {incident.themes.map((theme) => (
            <span key={theme}>{theme}</span>
          ))}
        </div>
      )}

      {incident.rationale.length > 0 && (
        <details>
          <summary>Analysis rationale</summary>
          <ul>
            {incident.rationale.map((item, index) => (
              <li key={`${incident.id}-${item.citation_id}-${index}`}>
                <strong>[{item.citation_id}]</strong> {item.reason}
              </li>
            ))}
          </ul>
        </details>
      )}

      {incident.barriers.length > 0 && (
        <details>
          <summary>Semantic barriers</summary>
          <ul>
            {incident.barriers.map((barrier, index) => (
              <li key={`${incident.id}-${barrier.id}-${index}`}>
                <strong>{humanize(barrier.id)}</strong> {barrier.rationale}
                {barrier.promoters.length > 0 && (
                  <small>
                    Proposed promoters:{' '}
                    {barrier.promoters.map(humanize).join(', ')}
                  </small>
                )}
              </li>
            ))}
          </ul>
        </details>
      )}
    </div>
  )
}

function IncidentReviewQueue({
  apiBaseUrl,
  ragApiBaseUrl,
  socialPostPageUrl,
  timeRange,
  country,
  regionArea,
  language,
  participantType,
  severity,
  refreshToken,
}: IncidentReviewQueueProps) {
  const [queue, setQueue] = useState<IncidentReviewQueueData>({
    total: 0,
    items: [],
  })
  const [selectedIncidentIds, setSelectedIncidentIds] = useState<string[]>([])
  const [isCreatingSocialPost, setIsCreatingSocialPost] = useState(false)
  const [socialPostDraft, setSocialPostDraft] = useState('')
  const [isSocialPostModalOpen, setIsSocialPostModalOpen] = useState(false)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState('')
  const orderedItems = [...queue.items].sort(newestIncidentFirst)
  const visibleIncidentIds = new Set(orderedItems.map((item) => item.id))
  const selectedVisibleIncidentIds = selectedIncidentIds.filter(
    (incidentId) => visibleIncidentIds.has(incidentId),
  )

  useEffect(() => {
    const controller = new AbortController()

    async function loadQueue() {
      setIsLoading(true)
      setError('')
      try {
        setQueue(
          await loadIncidentReviews(
            apiBaseUrl,
            {
              timeRange,
              country,
              regionArea,
              language,
              participantType,
              severity,
              reviewed: false,
            },
            controller.signal,
          ),
        )
      } catch (requestError) {
        if (!controller.signal.aborted) {
          setError(
            requestError instanceof Error
              ? requestError.message
              : 'The incident selections could not be loaded.',
          )
        }
      } finally {
        if (!controller.signal.aborted) setIsLoading(false)
      }
    }

    void loadQueue()
    return () => controller.abort()
  }, [
    apiBaseUrl,
    country,
    language,
    participantType,
    regionArea,
    refreshToken,
    severity,
    timeRange,
  ])

  function toggleIncidentSelection(incidentId: string, checked: boolean) {
    setSelectedIncidentIds((current) => {
      if (checked) {
        return current.includes(incidentId)
          ? current
          : [...current, incidentId]
      }

      return current.filter((selectedId) => selectedId !== incidentId)
    })
  }

  function handleCreateActivity() {
    const selectedIncidents = getSelectedIncidents()
    if (selectedIncidents.length === 0) return

    const wasSaved = saveEducatorActivityHandoff({
      source: 'incident-review',
      createdAt: new Date().toISOString(),
      incidents: selectedIncidents.map((incident) => ({
        id: incident.id,
        participantType: incident.participant_type,
        country: incident.country,
        regionArea: incident.region_area,
        language: incident.language,
        learnerAgeBand: incident.student_age_band,
        severity: incident.severity,
        tierLabel: incident.tier_label,
        targetGroup: incident.target_group,
        themes: incident.themes,
        confidence: incident.confidence,
        messageCount: incident.message_count,
        completedAt: incident.completed_at,
        incidentText: incident.incident_text,
        rationale: incident.rationale.map((item) => ({
          citationId: item.citation_id,
          reason: item.reason,
        })),
        barriers: incident.barriers,
      })),
    })

    if (!wasSaved) {
      setError(
        'The selected incidents could not be prepared for the educator workspace.',
      )
      return
    }

    window.location.assign('/educators?source=incident-review')
  }

  function getSelectedIncidents() {
    return orderedItems.filter((incident) =>
      selectedVisibleIncidentIds.includes(incident.id),
    )
  }

  async function handleCreateSocialMediaPost() {
    const selectedIncidents = getSelectedIncidents()
    if (selectedIncidents.length === 0 || isCreatingSocialPost) return

    setError('')
    setIsCreatingSocialPost(true)
    try {
      const response = await fetch(`${ragApiBaseUrl}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: createUuid(),
          role: 'teacher',
          age_band: normalizeAgeBand(
            selectedIncidents[0]?.student_age_band ?? 'mixed',
          ),
          country: selectedIncidents[0]?.country ?? 'Cyprus',
          message: buildSocialMediaPostPrompt(
            selectedIncidents,
            socialPostPageUrl,
          ),
          mode: 'counter-narrative',
        }),
      })

      if (!response.ok) {
        throw new Error(await readApiError(response))
      }

      const result = (await response.json()) as RagChatResponse
      setSocialPostDraft(
        mergeReferenceUrls(
          result.reply,
          referencesFromRagResponse(result.references, result.citations),
        ),
      )
      setIsSocialPostModalOpen(true)
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : 'The social media post could not be created.',
      )
    } finally {
      setIsCreatingSocialPost(false)
    }
  }

  return (
    <section className="incident-review-section" id="incident-selections">
      <div className="incident-review-heading">
        <div>
          <p className="eyebrow">Incident selection</p>
          <h2>Select incidents for content generation.</h2>
        </div>
        <div className="incident-review-heading__actions">
          <p>
            Choose one or more anonymized incidents and turn them into a
            guided educational activity or public-facing post.
          </p>
        </div>
      </div>

      <div className="incident-review-toolbar">
        <div className="incident-review-toolbar__summary">
          <strong>{queue.total} incidents</strong>
          <button
            className="incident-review-activity-button"
            disabled={selectedVisibleIncidentIds.length === 0}
            onClick={handleCreateActivity}
            type="button"
          >
            Create educational content
            <span>{selectedVisibleIncidentIds.length}</span>
          </button>
          <button
            className="incident-review-social-button"
            disabled={
              selectedVisibleIncidentIds.length === 0 ||
              isCreatingSocialPost
            }
            onClick={handleCreateSocialMediaPost}
            type="button"
          >
            {isCreatingSocialPost
              ? 'Creating post...'
              : 'Create a social media post'}
            <span>{selectedVisibleIncidentIds.length}</span>
          </button>
        </div>
      </div>

      {error && <p className="incident-review-error" role="alert">{error}</p>}
      {isLoading ? (
        <p className="dashboard-empty-state">Loading incident selections...</p>
      ) : queue.items.length === 0 ? (
        <div className="incident-review-empty">
          <strong>No incidents are available for selection.</strong>
          <p>The queue follows the dashboard filters and selected time range.</p>
        </div>
      ) : (
        <div className="incident-review-list">
          {orderedItems.map((incident) => {
            const isSelected = selectedIncidentIds.includes(incident.id)

            return (
              <article
                className={`incident-review-card${
                  isSelected ? ' is-selected' : ''
                }`}
                key={incident.id}
              >
                <header>
                  <div>
                    <span
                      className={`incident-review-severity incident-review-severity--${incident.severity}`}
                    >
                      {incident.tier_label || humanize(incident.severity)}
                    </span>
                    <h3>
                      {humanize(incident.participant_type)} incident in{' '}
                      {incident.region_area}
                    </h3>
                    <p>
                      {incident.country} · {incident.language} · Age{' '}
                      {incident.student_age_band} ·{' '}
                      {formatDate(incident.completed_at)}
                    </p>
                  </div>
                  <div className="incident-review-card__meta">
                    <span className="incident-review-id">
                      {incident.id.slice(0, 8)}
                    </span>
                    <label className="incident-review-select">
                      <input
                        checked={isSelected}
                        onChange={(event) =>
                          toggleIncidentSelection(
                            incident.id,
                            event.target.checked,
                          )
                        }
                        type="checkbox"
                      />
                      <span>{isSelected ? 'Selected' : 'Select'}</span>
                    </label>
                  </div>
                </header>

                <IncidentEvidence incident={incident} />
              </article>
            )
          })}
        </div>
      )}

      {isSocialPostModalOpen && (
        <div
          aria-labelledby="social-post-modal-title"
          aria-modal="true"
          className="incident-review-modal"
          role="dialog"
        >
          <div className="incident-review-modal__panel">
            <header>
              <div>
                <p className="eyebrow">Generated draft</p>
                <h3 id="social-post-modal-title">
                  Edit the social media post
                </h3>
              </div>
              <button
                aria-label="Close social media post editor"
                onClick={() => setIsSocialPostModalOpen(false)}
                type="button"
              >
                Close
              </button>
            </header>
            <textarea
              aria-label="Generated social media post"
              onChange={(event) => setSocialPostDraft(event.target.value)}
              rows={10}
              value={socialPostDraft}
            />
          </div>
        </div>
      )}
    </section>
  )
}

export default IncidentReviewQueue
