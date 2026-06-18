export type ChatReference = {
  id?: string
  title: string
  url?: string
  file?: string
  locator?: string
  detail?: string
  excerpt?: string
}

export type RagCitation = {
  source: string
  page?: string | number
  url?: string
  file?: string
  text?: string
}

export function referencesFromRagResponse(
  references: ChatReference[] | undefined,
  citations: RagCitation[] | undefined,
): ChatReference[] {
  if (references) {
    return references
  }

  return (citations ?? []).map((citation, index) => ({
    id: `S${index + 1}`,
    title: citation.source,
    url: citation.url,
    file: citation.file,
    locator:
      citation.page === undefined || citation.page === ''
        ? undefined
        : `p.${citation.page}`,
    excerpt: citation.text,
  }))
}
