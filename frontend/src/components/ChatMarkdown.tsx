import { useMemo, useState } from 'react'
import ReactMarkdown, { defaultUrlTransform } from 'react-markdown'
import remarkGfm from 'remark-gfm'

type ChatMarkdownProps = {
  content: string
  dashboardUrl?: string
  summary?: string | null
  summaryMode?: boolean
}

function markdownToSummaryText(content: string): string {
  return content
    .replace(/```[\s\S]*?```/g, ' ')
    .replace(/`([^`]+)`/g, '$1')
    .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')
    .replace(/^#{1,6}\s+/gm, '')
    .replace(/^\s{0,3}[-*+]\s+/gm, '')
    .replace(/^\s{0,3}\d+\.\s+/gm, '')
    .replace(/[*_~>#]/g, '')
    .replace(/\s+/g, ' ')
    .trim()
}

function summarizeMarkdown(content: string): string {
  const plainText = markdownToSummaryText(content)
  const sentences =
    plainText.match(/[^.!?]+[.!?]+(?=\s|$)|[^.!?]+$/g) ?? []
  const summary = (sentences.slice(0, 2).join(' ') || plainText).trim()

  if (summary.length <= 320) {
    return summary
  }

  return `${summary.slice(0, 317).replace(/\s+\S*$/, '')}...`
}

function ChatMarkdown({
  content,
  dashboardUrl,
  summary: generatedSummary,
  summaryMode = false,
}: ChatMarkdownProps) {
  const [isFullReportOpen, setIsFullReportOpen] = useState(!summaryMode)
  const summary = useMemo(
    () => generatedSummary?.trim() || summarizeMarkdown(content),
    [content, generatedSummary],
  )

  const markdown = (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      skipHtml
      urlTransform={defaultUrlTransform}
      components={{
        a({ children, href }) {
          return (
            <a href={href} target="_blank" rel="noreferrer">
              {children}
            </a>
          )
        },
      }}
    >
      {content}
    </ReactMarkdown>
  )

  if (summaryMode) {
    return (
      <div className="chat-message__body chat-markdown">
        <div className="chat-markdown__summary">
          <span>Summary</span>
          <p>{summary}</p>
        </div>
        <div className="chat-markdown__actions">
          <button
            aria-expanded={isFullReportOpen}
            className="chat-markdown__report-button"
            onClick={() => setIsFullReportOpen((current) => !current)}
            type="button"
          >
            {isFullReportOpen ? 'Hide full report' : 'Read full report'}
          </button>
          {dashboardUrl ? (
            <a
              className="chat-markdown__dashboard-link"
              href={dashboardUrl}
              rel="noreferrer"
              target="_blank"
            >
              See more similar incidents within your area
            </a>
          ) : null}
        </div>
        {isFullReportOpen ? (
          <div className="chat-markdown__full-report">{markdown}</div>
        ) : null}
      </div>
    )
  }

  return (
    <div className="chat-message__body chat-markdown">
      {markdown}
      {dashboardUrl ? (
        <a
          className="chat-markdown__dashboard-link"
          href={dashboardUrl}
          rel="noreferrer"
          target="_blank"
        >
          See more similar incidents within your area
        </a>
      ) : null}
    </div>
  )
}

export default ChatMarkdown
