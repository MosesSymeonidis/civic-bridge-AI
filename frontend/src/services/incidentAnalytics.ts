import type { ChatAnalysis } from './chatAnalysis'

export const analyticsChannelName = 'civic-bridge-analytics'

type StoreIncidentAnalysisInput = {
  apiBaseUrl: string
  participant: 'students' | 'educators'
  sessionId: string
  eventId: string
  messageCount: number
  incidentText: string
  analysis: ChatAnalysis
}

function notifyDashboard(): void {
  if (typeof BroadcastChannel === 'undefined') {
    return
  }

  const channel = new BroadcastChannel(analyticsChannelName)
  channel.postMessage({ type: 'incident-analysis-stored' })
  channel.close()
}

export async function storeIncidentAnalysis({
  apiBaseUrl,
  participant,
  sessionId,
  eventId,
  messageCount,
  incidentText,
  analysis,
}: StoreIncidentAnalysisInput): Promise<void> {
  const response = await fetch(
    `${apiBaseUrl}/${participant}/sessions/${sessionId}/analyses`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        analysis_event_id: eventId,
        message_count: messageCount,
        analysis_version: 'rag-incident-v1',
        incident_text: incidentText,
        analysis,
      }),
    },
  )

  if (!response.ok) {
    throw new Error(
      `Analytics API returned status ${response.status}.`,
    )
  }

  notifyDashboard()
}
