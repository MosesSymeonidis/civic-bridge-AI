import type { ChatReference } from '../services/chatReferences'

type ChatReferencesProps = {
  references: ChatReference[]
}

function safeExternalUrl(url?: string): string | null {
  if (!url) {
    return null
  }

  try {
    const parsed = new URL(url)
    return parsed.protocol === 'http:' || parsed.protocol === 'https:'
      ? parsed.toString()
      : null
  } catch {
    return null
  }
}

function truncate(value: string, maxLength = 180): string {
  if (value.length <= maxLength) {
    return value
  }
  return `${value.slice(0, maxLength).trimEnd()}...`
}

function ChatReferences({ references }: ChatReferencesProps) {
  if (references.length === 0) {
    return (
      <p className="chat-references-empty">
        No external references were attached to this response.
      </p>
    )
  }

  return (
    <details className="chat-references">
      <summary>
        <span>References</span>
        <small>
          {references.length} {references.length === 1 ? 'source' : 'sources'}
        </small>
      </summary>
      <ol>
        {references.map((reference, index) => {
          const href = safeExternalUrl(reference.url)
          const detail = reference.excerpt || reference.detail

          return (
            <li
              key={`${reference.id ?? 'reference'}-${reference.url ?? reference.file ?? index}`}
            >
              <div className="chat-reference__heading">
                {reference.id ? <span>[{reference.id}]</span> : null}
                {href ? (
                  <a href={href} target="_blank" rel="noreferrer">
                    {reference.title}
                  </a>
                ) : (
                  <strong>{reference.title}</strong>
                )}
                {reference.locator ? <small>{reference.locator}</small> : null}
              </div>
              {detail ? <p>{truncate(detail)}</p> : null}
              {reference.file ? (
                <code title={reference.file}>{reference.file}</code>
              ) : null}
            </li>
          )
        })}
      </ol>
    </details>
  )
}

export default ChatReferences
