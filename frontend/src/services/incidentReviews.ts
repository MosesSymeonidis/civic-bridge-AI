import { analyticsChannelName } from './incidentAnalytics'

export type ReviewOutcome =
  | 'bridge-response-adapted'
  | 'educational-activity-created'
  | 'safeguarding-guidance-prioritised'
  | 'expert-review-requested'

export type IncidentReviewItem = {
  id: string
  participant_type: 'student' | 'educator' | 'social-media'
  country: string
  region_area: string
  language: string
  student_age_band: string
  severity: string
  semantic_barriers: string[]
  bridge_promoters: string[]
  message_count: number
  completed_at: string
  tier_label: string
  target_group: string
  themes: string[]
  confidence: string
  incident_text: string
  rationale: Array<{ citation_id: string; reason: string }>
  barriers: Array<{
    id: string
    rationale: string
    promoters: string[]
  }>
  reviewed_at: string | null
  reviewer_reference: string | null
  reviewer_notes: string | null
  reviewer_outcome: ReviewOutcome | null
  constructive_response: boolean
}

export type IncidentReviewQueue = {
  total: number
  items: IncidentReviewItem[]
}

type ReviewFilters = {
  timeRange: '30d' | '90d' | '12m'
  country: string
  language: string
  participantType: 'student' | 'educator' | 'social-media' | ''
  reviewed: boolean
}

type SubmitReviewInput = {
  reviewerReference: string
  notes: string
}

export async function loadIncidentReviews(
  apiBaseUrl: string,
  filters: ReviewFilters,
  signal: AbortSignal,
): Promise<IncidentReviewQueue> {
  const params = new URLSearchParams({
    time_range: filters.timeRange,
    reviewed: String(filters.reviewed),
    limit: '50',
  })
  if (filters.country) params.set('country', filters.country)
  if (filters.language) params.set('language', filters.language)
  if (filters.participantType) {
    params.set('participant_type', filters.participantType)
  }

  const response = await fetch(
    `${apiBaseUrl}/dashboard/reviews?${params.toString()}`,
    { cache: 'no-store', signal },
  )
  if (!response.ok) {
    throw new Error(`Review queue API returned ${response.status}.`)
  }
  return (await response.json()) as IncidentReviewQueue
}

export async function submitIncidentReview(
  apiBaseUrl: string,
  incidentId: string,
  input: SubmitReviewInput,
): Promise<IncidentReviewItem> {
  const response = await fetch(
    `${apiBaseUrl}/dashboard/reviews/${incidentId}`,
    {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        reviewer_reference: input.reviewerReference,
        notes: input.notes,
      }),
    },
  )
  if (!response.ok) {
    throw new Error(`Review API returned ${response.status}.`)
  }

  if (typeof BroadcastChannel !== 'undefined') {
    const channel = new BroadcastChannel(analyticsChannelName)
    channel.postMessage({ type: 'incident-reviewed' })
    channel.close()
  }
  return (await response.json()) as IncidentReviewItem
}
