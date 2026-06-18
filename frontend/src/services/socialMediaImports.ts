import type { ChatAnalysis } from './chatAnalysis'
import { analyticsChannelName } from './incidentAnalytics'
import type { SemanticClusterPrediction } from './semanticClustering'

export type SocialMediaCsvRow = {
  post_id: string
  post_text: string
  country: string
  language: string
  region_area?: string
  platform?: string
  published_at?: string
  source_reference?: string
}

type StoreSocialMediaImportOptions = {
  notifyDashboard?: boolean
}

const preflightBatchSize = 500

export async function findExistingSocialMediaPosts(
  apiBaseUrl: string,
  postIds: string[],
): Promise<Set<string>> {
  const existingPostIds = new Set<string>()

  for (let offset = 0; offset < postIds.length; offset += preflightBatchSize) {
    const batch = postIds.slice(offset, offset + preflightBatchSize)
    const response = await fetch(`${apiBaseUrl}/imports/social-media/check`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ post_ids: batch }),
    })
    if (!response.ok) {
      throw new Error(`Import preflight returned ${response.status}.`)
    }
    const body = (await response.json()) as { existing_post_ids: string[] }
    body.existing_post_ids.forEach((postId) => existingPostIds.add(postId))
  }

  return existingPostIds
}

export async function storeSocialMediaImport(
  apiBaseUrl: string,
  row: SocialMediaCsvRow,
  incidentText: string,
  analysis: ChatAnalysis,
  prediction: SemanticClusterPrediction,
  options: StoreSocialMediaImportOptions = {},
): Promise<'imported' | 'duplicate'> {
  const response = await fetch(`${apiBaseUrl}/imports/social-media/events`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      post_id: row.post_id,
      country: row.country,
      region_area: row.region_area || 'Unspecified',
      language: row.language,
      platform: row.platform || null,
      published_at: row.published_at
        ? new Date(row.published_at).toISOString()
        : null,
      source_reference: row.source_reference || null,
      incident_text: incidentText,
      analysis,
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
  })
  if (!response.ok) {
    throw new Error(`Import storage returned ${response.status}.`)
  }

  const body = (await response.json()) as {
    status: 'imported' | 'duplicate'
  }
  if (
    body.status === 'imported' &&
    options.notifyDashboard !== false &&
    typeof BroadcastChannel !== 'undefined'
  ) {
    const channel = new BroadcastChannel(analyticsChannelName)
    channel.postMessage({ type: 'social-media-imported' })
    channel.close()
  }
  return body.status
}
