import { analyticsChannelName } from './incidentAnalytics'

export type SemanticClusterKeyword = {
  term: string
  weight: number
}

export type SemanticClusterPrediction = {
  text: string
  topic_id: number
  parent_category: string | null
  category: string | null
  confidence: number | null
  is_outlier: boolean
  assignment_method: string
  keywords_role: string
  keywords: SemanticClusterKeyword[]
  keywords_topic_id: number
  coordinates: {
    x: number
    y: number
    projection_version: string
  }
  nearest_candidate: {
    topic_id: number
    parent_category: string | null
    category: string | null
  }
}

type StoreSemanticClusterInput = {
  apiBaseUrl: string
  participant: 'students' | 'educators'
  sessionId: string
  eventId: string
  prediction: SemanticClusterPrediction
}

function notifyDashboard(): void {
  if (typeof BroadcastChannel === 'undefined') {
    return
  }

  const channel = new BroadcastChannel(analyticsChannelName)
  channel.postMessage({ type: 'semantic-cluster-stored' })
  channel.close()
}

export async function classifySemanticCluster(
  apiBaseUrl: string,
  text: string,
): Promise<SemanticClusterPrediction> {
  const response = await fetch(`${apiBaseUrl}/predict`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text }),
  })

  if (!response.ok) {
    throw new Error(
      `Semantic classifier returned status ${response.status}.`,
    )
  }

  return (await response.json()) as SemanticClusterPrediction
}

export async function storeSemanticCluster({
  apiBaseUrl,
  participant,
  sessionId,
  eventId,
  prediction,
}: StoreSemanticClusterInput): Promise<void> {
  const response = await fetch(
    `${apiBaseUrl}/${participant}/sessions/${sessionId}/classifications`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        classification_event_id: eventId,
        classification_version: 'semantic-cluster-api-v1',
        classification: {
          topic_id: prediction.topic_id,
          parent_category: prediction.parent_category,
          category: prediction.category,
          confidence: prediction.confidence,
          is_outlier: prediction.is_outlier,
          assignment_method: prediction.assignment_method,
          keywords_role: prediction.keywords_role,
          keywords: prediction.keywords,
          keywords_topic_id: prediction.keywords_topic_id,
          coordinates: prediction.coordinates,
          nearest_candidate: prediction.nearest_candidate,
        },
      }),
    },
  )

  if (!response.ok) {
    throw new Error(
      `Semantic analytics API returned status ${response.status}.`,
    )
  }

  notifyDashboard()
}

export async function classifyAndStoreSemanticCluster(
  classifierApiBaseUrl: string,
  backendApiBaseUrl: string,
  participant: 'students' | 'educators',
  sessionId: string,
  eventId: string,
  text: string,
): Promise<void> {
  const prediction = await classifySemanticCluster(
    classifierApiBaseUrl,
    text,
  )
  await storeSemanticCluster({
    apiBaseUrl: backendApiBaseUrl,
    participant,
    sessionId,
    eventId,
    prediction,
  })
}
