export type EducatorActivityHandoffIncident = {
  id: string
  participantType: 'student' | 'educator' | 'social-media'
  country: string
  regionArea: string
  language: string
  learnerAgeBand: string
  severity: string
  tierLabel: string
  targetGroup: string
  themes: string[]
  confidence: string
  messageCount: number
  completedAt: string
  incidentText: string
  rationale: Array<{ citationId: string; reason: string }>
  barriers: Array<{
    id: string
    rationale: string
    promoters: string[]
  }>
}

export type EducatorActivityHandoff = {
  source: 'incident-review'
  createdAt: string
  incidents: EducatorActivityHandoffIncident[]
}

const educatorActivityHandoffStorageKey =
  'civic-bridge-educator-activity-handoff-v1'

function getSessionStorage(): Storage | null {
  if (typeof window === 'undefined') return null

  try {
    return window.sessionStorage
  } catch {
    return null
  }
}

function isEducatorActivityHandoff(
  value: unknown,
): value is EducatorActivityHandoff {
  if (!value || typeof value !== 'object') return false

  const candidate = value as {
    source?: unknown
    createdAt?: unknown
    incidents?: unknown
  }

  return (
    candidate.source === 'incident-review' &&
    typeof candidate.createdAt === 'string' &&
    Array.isArray(candidate.incidents) &&
    candidate.incidents.length > 0
  )
}

function humanize(value: string): string {
  return value
    .replace(/[_-]+/g, ' ')
    .replace(/\b\w/g, (character) => character.toUpperCase())
}

function truncate(value: string, maxLength: number): string {
  const normalized = value.trim()
  if (normalized.length <= maxLength) return normalized

  return `${normalized.slice(0, Math.max(0, maxLength - 3)).trimEnd()}...`
}

function formatIncidentForPrompt(
  incident: EducatorActivityHandoffIncident,
  index: number,
  textLimit: number,
): string {
  const details = [
    `Incident ${index + 1}: ${
      incident.tierLabel || humanize(incident.severity)
    }`,
    `Context: ${incident.regionArea}, ${incident.country}; ${
      incident.language
    }; learners ${incident.learnerAgeBand}; ${
      incident.participantType
    } source; ${incident.messageCount} messages analysed.`,
    `Target group: ${incident.targetGroup || 'Not identified'}.`,
  ]

  if (incident.themes.length > 0) {
    details.push(`Themes: ${incident.themes.join(', ')}.`)
  }

  if (incident.barriers.length > 0) {
    details.push(
      `Semantic barriers: ${incident.barriers
        .map((barrier) => humanize(barrier.id))
        .join(', ')}.`,
    )
  }

  details.push(
    `Anonymized incident text: ${
      truncate(incident.incidentText, textLimit) ||
      'The incident text was not recorded.'
    }`,
  )

  return details.join('\n')
}

export function saveEducatorActivityHandoff(
  handoff: EducatorActivityHandoff,
): boolean {
  const storage = getSessionStorage()
  if (!storage) return false

  try {
    storage.setItem(
      educatorActivityHandoffStorageKey,
      JSON.stringify(handoff),
    )
    return true
  } catch {
    return false
  }
}

export function loadEducatorActivityHandoff():
  | EducatorActivityHandoff
  | null {
  const storage = getSessionStorage()
  if (!storage) return null

  const rawHandoff = storage.getItem(educatorActivityHandoffStorageKey)
  if (!rawHandoff) return null

  try {
    const handoff = JSON.parse(rawHandoff) as unknown
    return isEducatorActivityHandoff(handoff) ? handoff : null
  } catch {
    return null
  }
}

export function clearEducatorActivityHandoff(): void {
  const storage = getSessionStorage()
  storage?.removeItem(educatorActivityHandoffStorageKey)
}

export function buildIncidentActivityPrompt(
  handoff: EducatorActivityHandoff,
): string {
  const textLimit = Math.max(
    180,
    Math.floor(1700 / Math.max(1, handoff.incidents.length)),
  )
  const incidentDescriptions = handoff.incidents
    .map((incident, index) =>
      formatIncidentForPrompt(incident, index, textLimit),
    )
    .join('\n\n')

  return truncate(
    [
      'Create an in-class learning activity based on the selected anonymized incidents below.',
      'Use the incidents as classroom cases without naming people or asking learners to reproduce harmful language unnecessarily.',
      'Design an age-appropriate activity with learning objectives, timing, materials, facilitation steps, discussion questions, safeguards, and a short reflection or assessment task.',
      '',
      'Selected incidents:',
      incidentDescriptions,
    ].join('\n'),
    3900,
  )
}
