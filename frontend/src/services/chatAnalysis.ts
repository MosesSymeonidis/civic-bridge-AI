export type AnalysisRationale = {
  citation_id: string
  reason: string
}

export type AnalysisBarrier = {
  id: string
  span: string
  rationale: string
  promoters: string[]
}

export type RelatedCase = {
  name?: string
  appno?: string
  conclusion?: string
  url?: string
}

export type ChatAnalysis = {
  tier: 1 | 2 | 3 | 4
  tier_label: string
  rationale: AnalysisRationale[]
  barriers: AnalysisBarrier[]
  target_group: string
  themes: string[]
  confidence: string
  related_cases?: RelatedCase[]
}

type AnalyzeIncidentInput = {
  apiBaseUrl: string
  text: string
  country: string
  ageBand: string
  role: 'student' | 'teacher'
}

export async function analyzeIncident({
  apiBaseUrl,
  text,
  country,
  ageBand,
  role,
}: AnalyzeIncidentInput): Promise<ChatAnalysis> {
  const response = await fetch(`${apiBaseUrl}/analyze`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      text,
      country,
      age_band: ageBand,
      role,
    }),
  })

  if (!response.ok) {
    throw new Error(`Incident analysis failed with status ${response.status}`)
  }

  return (await response.json()) as ChatAnalysis
}

export async function analyzeSocialMediaPost(
  apiBaseUrl: string,
  text: string,
  country: string,
): Promise<ChatAnalysis> {
  const response = await fetch(`${apiBaseUrl}/analyze`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text, country }),
  })

  if (!response.ok) {
    throw new Error(`Incident analysis failed with status ${response.status}`)
  }

  return (await response.json()) as ChatAnalysis
}
