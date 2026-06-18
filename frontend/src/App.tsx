import { useEffect, useState } from 'react'

import EducatorsPage from './pages/EducatorsPage'
import HowItWorksPage from './pages/HowItWorksPage'
import PublicInstitutionsPage from './pages/PublicInstitutionsPage'
import StudentsPage from './pages/StudentsPage'

type HealthResponse = {
  status: string
  service: string
  environment: string
}

type ApiState =
  | { kind: 'loading' }
  | { kind: 'ready'; health: HealthResponse }
  | { kind: 'error' }

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? '/api/v1'

const workflow = [
  {
    number: '01',
    title: 'Detect',
    description:
      'Place public or anonymised text on a graduated severity scale, not a binary label.',
  },
  {
    number: '02',
    title: 'Interpret',
    description:
      'Identify narrative frames and the semantic barriers that close down dialogue.',
  },
  {
    number: '03',
    title: 'Contextualise',
    description:
      'Read the content through its country, language, historical, and social context.',
  },
  {
    number: '04',
    title: 'Educate',
    description:
      'Turn the analysis into age-appropriate prompts, activities, and democratic competences.',
  },
  {
    number: '05',
    title: 'Respond',
    description:
      'Draft bridge formulations and counter-narratives for a trained human to adapt.',
  },
]

const personas = [
  {
    label: 'Students / Young People',
    route: '/students',
    description:
      'Experienced an incident? Start a constructive dialogue with our chat assistant.',
    available: true,
  },
  {
    label: 'Educators',
    route: '/educators',
    description:
      'Faced a hate-speech incident? Chat with our assistant to support age-appropriate learning, constructive classroom dialogue, and appropriate next steps.',
    available: true,
  },
  {
    label: 'Public Institutions',
    route: '/public-institutions',
    description:
      'Review discourse patterns across your institution or region with accountable safeguards.',
    available: true,
  },
]

const safeguards = [
  'No legal determinations',
  'No automated removal or reporting',
  'No action against users',
  'No identity profiling',
  'Human review for consequential decisions',
]

function App() {
  const pathname = window.location.pathname.replace(/\/+$/, '') || '/'

  if (pathname === '/students') {
    return <StudentsPage />
  }

  if (pathname === '/educators') {
    return <EducatorsPage />
  }

  if (pathname === '/public-institutions') {
    return <PublicInstitutionsPage />
  }

  if (pathname === '/how-it-works') {
    return <HowItWorksPage />
  }

  return <LandingPage />
}

function LandingPage() {
  const [apiState, setApiState] = useState<ApiState>({ kind: 'loading' })

  useEffect(() => {
    const controller = new AbortController()

    async function loadHealth() {
      try {
        const response = await fetch(`${apiBaseUrl}/health`, {
          signal: controller.signal,
        })

        if (!response.ok) {
          throw new Error(`Health check failed with status ${response.status}`)
        }

        const health = (await response.json()) as HealthResponse
        setApiState({ kind: 'ready', health })
      } catch (error) {
        if (error instanceof DOMException && error.name === 'AbortError') {
          return
        }
        setApiState({ kind: 'error' })
      }
    }

    void loadHealth()
    return () => controller.abort()
  }, [])

  const statusLabel =
    apiState.kind === 'ready'
      ? 'System online'
      : apiState.kind === 'error'
        ? 'System unavailable'
        : 'Checking system'

  return (
    <div className="site-shell">
      <header className="topbar">
        <a className="brand" href="#top" aria-label="Civic Bridge AI home">
          <span className="brand__mark" aria-hidden="true">
            <span />
            <span />
            <span />
          </span>
          <span>Civic Bridge AI</span>
        </a>

        <nav aria-label="Primary navigation">
          <a href="/how-it-works">How it works</a>
          <a href="#method">Method</a>
          <a href="#education">Education</a>
          <a href="#safeguards">Safeguards</a>
        </nav>

        <div
          className={`system-status system-status--${apiState.kind}`}
          aria-live="polite"
          title={
            apiState.kind === 'ready'
              ? `${apiState.health.service}: ${apiState.health.environment}`
              : statusLabel
          }
        >
          <span aria-hidden="true" />
          {statusLabel}
        </div>
      </header>

      <main id="top">
        <section className="hero" aria-labelledby="hero-title">
          <div className="hero__content">
            <p className="eyebrow">
              Human-led AI for democratic dialogue
            </p>
            <h1 id="hero-title">
              Detect harm.
              <span> Reopen dialogue.</span>
            </h1>
            <p className="hero__summary">
              Civic Bridge AI turns hate-speech detection into an explained,
              privacy-conscious pathway for interpretation, education, and
              constructive response.
            </p>

            <div className="persona-entry" aria-labelledby="persona-title">
              <div className="persona-entry__heading">
                <p id="persona-title">Choose your workspace</p>
              </div>

              <div className="persona-buttons">
                {personas.map((persona, index) => {
                  const content = (
                    <>
                      <span className="persona-button__number">
                        {String(index + 1).padStart(2, '0')}
                      </span>
                      <span className="persona-button__content">
                        <strong>{persona.label}</strong>
                        <small>{persona.description}</small>
                      </span>
                      <span className="persona-button__status">
                        {persona.available ? 'Open workspace' : 'Coming soon'}
                      </span>
                    </>
                  )

                  return persona.available ? (
                    <a
                      className="persona-button persona-button--available"
                      href={persona.route}
                      key={persona.route}
                    >
                      {content}
                    </a>
                  ) : (
                    <button
                      className="persona-button"
                      disabled
                      key={persona.route}
                      type="button"
                    >
                      {content}
                    </button>
                  )
                })}
              </div>
            </div>

            <div className="hero__actions">
              <a className="button button--primary" href="#method">
                Explore the five-step method
                <span aria-hidden="true">&rarr;</span>
              </a>
              <a className="button button--secondary" href="#safeguards">
                Review our safeguards
              </a>
            </div>

            <ul className="trust-list" aria-label="Core principles">
              <li>Privacy-conscious</li>
              <li>Human in the loop</li>
              <li>Multilingual by design</li>
            </ul>
          </div>
        </section>

        <section className="positioning" aria-label="Project purpose">
          <p>Beyond traditional moderation</p>
          <blockquote>
            Not only &ldquo;Is this hate speech?&rdquo; but &ldquo;How can this
            harmful narrative be understood, challenged, and
            transformed?&rdquo;
          </blockquote>
          <span>Designed around Council of Europe CM/Rec(2022)16</span>
        </section>

        <section className="method section" id="method">
          <div className="section-heading">
            <div>
              <p className="eyebrow">One accountable process</p>
              <h2>Five steps from detection to democratic learning.</h2>
            </div>
            <p>
              A large-language-model-orchestrated pipeline supports each
              stage. Human judgement remains responsible for every decision
              that carries consequences.
            </p>
          </div>

          <div className="workflow">
            {workflow.map((step) => (
              <article className="workflow-card" key={step.number}>
                <span>{step.number}</span>
                <h3>{step.title}</h3>
                <p>{step.description}</p>
              </article>
            ))}
          </div>
        </section>

        <section
          className="analysis-showcase section"
          aria-labelledby="analysis-title"
        >
          <div className="analysis-showcase__intro">
            <p className="eyebrow">Illustrative analysis</p>
            <h2 id="analysis-title">From signal to understanding.</h2>
            <p>
              The analysis combines a graduated risk signal with the
              discursive mechanisms that close dialogue and the strategies
              that can reopen it.
            </p>
          </div>

          <div className="analysis-card" aria-label="Illustrative analysis">
            <div className="analysis-card__top">
              <div>
                <p className="card-kicker">Illustrative analysis</p>
                <h2>Human-reviewed risk support</h2>
              </div>
              <span className="review-badge">Human review</span>
            </div>

            <div className="sample-text">
              <span>Public / anonymised text</span>
              <p>
                A statement frames an entire social group as a threat and
                rejects alternative perspectives.
              </p>
            </div>

            <div className="severity">
              <div className="severity__heading">
                <span>Graduated severity</span>
                <strong>Review recommended</strong>
              </div>
              <div className="severity__scale" aria-hidden="true">
                <span />
                <span />
                <span className="is-active" />
                <span />
              </div>
              <div className="severity__labels" aria-hidden="true">
                <span>Expression</span>
                <span>Harmful</span>
                <span>Review</span>
                <span>High risk</span>
              </div>
            </div>

            <div className="analysis-grid">
              <div>
                <span className="analysis-label">Semantic barriers</span>
                <strong>Rigid opposition / Collective blame</strong>
              </div>
              <div>
                <span className="analysis-label">Bridge promoters</span>
                <strong>Context / Corroboration / Empathy</strong>
              </div>
            </div>

            <p className="analysis-note">
              The system narrows attention and explains its reasoning. A
              trained human decides.
            </p>
          </div>
        </section>

        <section className="education section" id="education">
          <div className="education__content">
            <p className="eyebrow">Education, not automation</p>
            <h2>Guidance that meets people where they are.</h2>
            <p>
              Educators, pupils, students, and families receive
              developmentally appropriate prompts to examine harmful
              statements, recognise propaganda mechanisms, and create
              counter-narratives.
            </p>

            <div className="age-bands" aria-label="Supported age bands">
              <span>Ages 6-9</span>
              <span>Ages 10-13</span>
              <span>Ages 14-17</span>
              <span>Ages 18+</span>
            </div>
          </div>

          <div className="context-card">
            <p className="card-kicker">First country context</p>
            <div className="context-card__title">
              <h3>Cyprus</h3>
              <span>Case study 01</span>
            </div>
            <p>
              Greek, Turkish, and English modules connect analysis with local
              history, intercommunal narratives, anti-migrant discourse, and
              human-rights guidance.
            </p>
            <div className="language-list">
              <span>EL</span>
              <span>TR</span>
              <span>EN</span>
              <strong>46 CoE member states on the roadmap</strong>
            </div>
          </div>
        </section>

        <section className="safeguards section" id="safeguards">
          <div className="safeguards__intro">
            <p className="eyebrow">Boundaries by design</p>
            <h2>Analyse discourse. Never identity.</h2>
            <p>
              The platform is designed for public or anonymised text without
              usernames, profile links, exact locations, or private messages.
              It supports judgement; it does not automate it.
            </p>
          </div>

          <ul>
            {safeguards.map((safeguard) => (
              <li key={safeguard}>
                <span aria-hidden="true">&#10003;</span>
                {safeguard}
              </li>
            ))}
          </ul>
        </section>
      </main>

      <footer>
        <div className="brand brand--footer">
          <span className="brand__mark" aria-hidden="true">
            <span />
            <span />
            <span />
          </span>
          <span>Civic Bridge AI</span>
        </div>
        <p>
          Technology for dignity, democratic education, and dialogue in
          divided societies.
        </p>
      </footer>
    </div>
  )
}

export default App
