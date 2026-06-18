import type { ChatAnalysis } from '../services/chatAnalysis'

type ChatAnalysisCardProps = {
  analysis: ChatAnalysis
}

function humanize(value: string): string {
  return value
    .replace(/[_-]+/g, ' ')
    .replace(/\b\w/g, (character) => character.toUpperCase())
}

function displayTarget(target: string): string {
  const normalized = target.trim().toLowerCase()
  return !normalized || normalized === 'none' || normalized === 'unknown'
    ? 'Not identified'
    : target
}

function ChatAnalysisCard({ analysis }: ChatAnalysisCardProps) {
  const hasDetails =
    analysis.barriers.length > 0 ||
    analysis.rationale.length > 0 ||
    analysis.themes.length > 0

  return (
    <details
      className={`chat-analysis chat-analysis--tier-${analysis.tier}`}
    >
      <summary>
        <span>View incident analysis</span>
        <small>Type, severity and dialogue barriers</small>
      </summary>

      <div className="chat-analysis__content">
        <div className="chat-analysis__header">
          <div>
            <span>Incident type</span>
            <strong>{analysis.tier_label}</strong>
          </div>
          <b>Tier {analysis.tier}</b>
        </div>

        <dl className="chat-analysis__facts">
          <div>
            <dt>Target</dt>
            <dd>{displayTarget(analysis.target_group)}</dd>
          </div>
          <div>
            <dt>Confidence</dt>
            <dd>{humanize(analysis.confidence)}</dd>
          </div>
          <div>
            <dt>Dialogue barriers</dt>
            <dd>{analysis.barriers.length}</dd>
          </div>
        </dl>

        {hasDetails ? (
          <div className="chat-analysis__detail-body">
            {analysis.themes.length > 0 ? (
              <section>
                <h4>Themes</h4>
                <div className="chat-analysis__tags">
                  {analysis.themes.map((theme) => (
                    <span key={theme}>{theme}</span>
                  ))}
                </div>
              </section>
            ) : null}

            {analysis.barriers.length > 0 ? (
              <section>
                <h4>Semantic barriers</h4>
                <ul className="chat-analysis__barriers">
                  {analysis.barriers.map((barrier) => (
                    <li key={`${barrier.id}-${barrier.span}`}>
                      <strong>{humanize(barrier.id)}</strong>
                      {barrier.span ? <q>{barrier.span}</q> : null}
                      <span>{barrier.rationale}</span>
                      {barrier.promoters.length > 0 ? (
                        <small>
                          Dialogue promoters:{' '}
                          {barrier.promoters.map(humanize).join(', ')}
                        </small>
                      ) : null}
                    </li>
                  ))}
                </ul>
              </section>
            ) : null}

            {analysis.rationale.length > 0 ? (
              <section>
                <h4>Severity rationale</h4>
                <ul className="chat-analysis__rationale">
                  {analysis.rationale.map((item) => (
                    <li key={item.citation_id}>
                      <strong>[{item.citation_id}]</strong>
                      <span>{item.reason}</span>
                    </li>
                  ))}
                </ul>
              </section>
            ) : null}
          </div>
        ) : null}

        <small className="chat-analysis__notice">
          Risk-support signal for human review, not a legal determination.
        </small>
      </div>
    </details>
  )
}

export default ChatAnalysisCard
