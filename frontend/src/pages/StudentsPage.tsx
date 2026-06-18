import {
  type FormEvent,
  type KeyboardEvent,
  useEffect,
  useRef,
  useState,
} from 'react'

import ChatAnalysisCard from '../components/ChatAnalysisCard'
import ChatImageAttachmentInput from '../components/ChatImageAttachmentInput'
import ChatMarkdown from '../components/ChatMarkdown'
import ChatReferences from '../components/ChatReferences'
import { availableLanguages, euCountries } from '../data/euCountries'
import {
  analyzeIncident,
  type ChatAnalysis,
} from '../services/chatAnalysis'
import {
  type ChatReference,
  type RagCitation,
  referencesFromRagResponse,
} from '../services/chatReferences'
import {
  anonymizeChatMessage,
  clearAnonymizationSession,
  preloadAnonymizer,
} from '../services/anonymizer'
import { storeIncidentAnalysis } from '../services/incidentAnalytics'
import {
  chatImageOnlyPrompt,
  type ChatImageAttachment,
  messageWithImageAttachment,
  prepareChatImage,
  truncateForAnalytics,
} from '../services/imageAttachments'
import { classifyAndStoreSemanticCluster } from '../services/semanticClustering'
import { createUuid } from '../services/uuid'

type AgeBand = '6-9' | '10-13' | '14-17' | '18+'

type StudentContext = {
  country: string
  region_area: string
  language: string
  age_band: AgeBand
}

type StudentSessionResponse = {
  session_id: string
  context: StudentContext
  welcome_message: string
}

type RagChatResponse = {
  reply: string
  analysis?: ChatAnalysis | null
  references?: ChatReference[]
  citations?: RagCitation[]
  triage?: boolean
}

type ChatMessage = {
  id: string
  role: 'student' | 'assistant'
  content: string
  analysis?: ChatAnalysis
  analysisUnavailable?: boolean
  analyticsStorageFailed?: boolean
  references?: ChatReference[]
}

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? '/api/v1'
const ragApiBaseUrl = import.meta.env.VITE_RAG_API_BASE_URL ?? '/rag-api'
const classifierApiBaseUrl =
  import.meta.env.VITE_CLASSIFIER_API_BASE_URL ?? '/classifier-api'

const ageBands: Array<{ value: AgeBand; label: string; note: string }> = [
  { value: '6-9', label: '6-9', note: 'Simple guidance' },
  { value: '10-13', label: '10-13', note: 'Step-by-step support' },
  { value: '14-17', label: '14-17', note: 'Context and options' },
  { value: '18+', label: '18+', note: 'Detailed guidance' },
]

const supportGoals = [
  {
    number: '01',
    title: 'Understand it',
    description:
      'Spot the difference between disagreement, bullying, and possible hate speech.',
  },
  {
    number: '02',
    title: 'Protect yourself',
    description:
      'Make a practical plan for evidence, support, blocking, and safety.',
  },
  {
    number: '03',
    title: 'Choose what to do',
    description:
      'Compare response and reporting options without being pushed into one.',
  },
]

const starterActions = [
  {
    label: 'Could this be hate speech?',
    prompt:
      'Help me understand whether something I saw could be hate speech. What signs should I look for?',
  },
  {
    label: 'Make a plan for me',
    prompt:
      'Someone posted something hurtful about me. Help me make a clear plan for what to do next.',
  },
  {
    label: 'Help me support a friend',
    prompt:
      'A friend was targeted by a hurtful post. How can I support them safely?',
  },
  {
    label: 'What should I save or report?',
    prompt:
      'What evidence should I save, and what reporting options could I consider?',
  },
]

const initialContext: StudentContext = {
  country: '',
  region_area: '',
  language: '',
  age_band: '14-17',
}

async function readApiError(response: Response): Promise<string> {
  try {
    const body = (await response.json()) as { detail?: string }
    if (typeof body.detail === 'string') {
      return body.detail
    }
  } catch {
    // Fall back to a generic message when the API did not return JSON.
  }

  return 'The service could not complete your request. Please try again.'
}

function StudentsPage() {
  const [contextForm, setContextForm] =
    useState<StudentContext>(initialContext)
  const [session, setSession] = useState<StudentSessionResponse | null>(null)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [draft, setDraft] = useState('')
  const [pendingImage, setPendingImage] =
    useState<ChatImageAttachment | null>(null)
  const [isStarting, setIsStarting] = useState(false)
  const [isSending, setIsSending] = useState(false)
  const [isAnonymizing, setIsAnonymizing] = useState(false)
  const [isProcessingImage, setIsProcessingImage] = useState(false)
  const [error, setError] = useState('')
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const composerRef = useRef<HTMLTextAreaElement>(null)
  const selectedCountry = euCountries.find(
    (country) => country.name === contextForm.country,
  )
  const otherLanguages = availableLanguages.filter(
    (language) => !selectedCountry?.officialLanguages.includes(language),
  )

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isSending])

  useEffect(() => {
    void preloadAnonymizer().catch(() => undefined)
  }, [])

  async function handleContextSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError('')
    setIsStarting(true)

    try {
      const response = await fetch(`${apiBaseUrl}/students/sessions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(contextForm),
      })

      if (!response.ok) {
        throw new Error(await readApiError(response))
      }

      const createdSession = (await response.json()) as StudentSessionResponse
      setSession(createdSession)
      setContextForm(createdSession.context)
      setMessages([
        {
          id: createUuid(),
          role: 'assistant',
          content: createdSession.welcome_message,
        },
      ])
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : 'The student workspace could not be started.',
      )
    } finally {
      setIsStarting(false)
    }
  }

  async function sendMessage() {
    const message = draft.trim()
    const imageAttachment = pendingImage
    if (
      !session ||
      isSending ||
      isProcessingImage ||
      (!message && !imageAttachment)
    ) {
      return
    }
    const outboundMessage = message || chatImageOnlyPrompt
    const displayedMessage = messageWithImageAttachment(
      outboundMessage,
      imageAttachment,
    )

    setError('')
    setDraft('')
    setMessages((current) => [
      ...current,
      { id: createUuid(), role: 'student', content: displayedMessage },
    ])
    setIsSending(true)
    setIsAnonymizing(true)
    let requestStage: 'anonymizing' | 'sending' = 'anonymizing'

    try {
      const safeMessage = await anonymizeChatMessage(
        outboundMessage,
        session.session_id,
      )
      if (!safeMessage.trim()) {
        throw new Error('Anonymization produced an empty message.')
      }
      const analysisText = safeMessage

      requestStage = 'sending'
      setIsAnonymizing(false)
      const response = await fetch(`${ragApiBaseUrl}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: session.session_id,
          role: 'student',
          age_band: session.context.age_band,
          country: session.context.country,
          message: safeMessage,
          image: imageAttachment
            ? {
                image: imageAttachment.image,
                filename: imageAttachment.fileName,
                mime_type: imageAttachment.mediaType,
              }
            : undefined,
        }),
      })

      if (!response.ok) {
        throw new Error(await readApiError(response))
      }

      const reply = (await response.json()) as RagChatResponse
      const analyticsEventId = createUuid()
      const classificationStorage = imageAttachment
        ? Promise.resolve(true)
        : classifyAndStoreSemanticCluster(
            classifierApiBaseUrl,
            apiBaseUrl,
            'students',
            session.session_id,
            analyticsEventId,
            analysisText,
          )
            .then(() => true)
            .catch(() => false)
      let analysis = reply.analysis ?? undefined
      let analysisUnavailable = false
      if (!analysis && !reply.triage) {
        try {
          analysis = await analyzeIncident({
            apiBaseUrl: ragApiBaseUrl,
            text: analysisText,
            country: session.context.country,
            ageBand: session.context.age_band,
            role: 'student',
          })
        } catch {
          analysisUnavailable = true
        }
      }
      const assistantMessageId = createUuid()
      let analyticsStorageFailed = false
      if (analysis) {
        try {
          await storeIncidentAnalysis({
            apiBaseUrl,
            participant: 'students',
            sessionId: session.session_id,
            eventId: analyticsEventId,
            messageCount:
              messages.filter((item) => item.role === 'student').length + 1,
            incidentText: imageAttachment
              ? ''
              : truncateForAnalytics(analysisText),
            analysis,
          })
        } catch {
          analyticsStorageFailed = true
        }
      }
      if (!(await classificationStorage)) {
        analyticsStorageFailed = true
      }
      setMessages((current) => [
        ...current,
        {
          id: assistantMessageId,
          role: 'assistant',
          content: reply.reply,
          analysis,
          analysisUnavailable,
          analyticsStorageFailed,
          references: referencesFromRagResponse(
            reply.references,
            reply.citations,
          ),
        },
      ])
      setPendingImage(null)
    } catch (requestError) {
      setDraft(message)
      setError(
        requestStage === 'anonymizing'
          ? 'For privacy, your message was not sent because local anonymization could not be completed. Please try again.'
          : requestError instanceof Error
          ? requestError.message
          : 'Your message could not be sent.',
      )
    } finally {
      setIsSending(false)
      setIsAnonymizing(false)
    }
  }

  function handleMessageSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    void sendMessage()
  }

  function handleComposerKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault()
      void sendMessage()
    }
  }

  function resetSession() {
    if (session) {
      clearAnonymizationSession(session.session_id)
    }
    setSession(null)
    setMessages([])
    setDraft('')
    setPendingImage(null)
    setError('')
  }

  function handleCountryChange(countryName: string) {
    const country = euCountries.find((item) => item.name === countryName)
    setContextForm((current) => ({
      ...current,
      country: countryName,
      language: country?.defaultLanguage ?? '',
    }))
  }

  function chooseStarter(prompt: string) {
    setDraft(prompt)
    composerRef.current?.focus()
  }

  async function handleImageSelected(file: File) {
    setError('')
    setIsProcessingImage(true)
    try {
      setPendingImage(await prepareChatImage(file))
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : 'The image could not be processed.',
      )
    } finally {
      setIsProcessingImage(false)
    }
  }

  const hasStudentMessage = messages.some(
    (message) => message.role === 'student',
  )

  return (
    <div className="student-page">
      <header className="student-topbar">
        <a className="brand" href="/" aria-label="Return to Civic Bridge AI">
          <span className="brand__mark" aria-hidden="true">
            <span />
            <span />
            <span />
          </span>
          <span>Civic Bridge AI</span>
        </a>
        <span className="student-topbar__label">Student workspace</span>
        <a className="student-back-link" href="/">
          Back to overview
        </a>
      </header>

      {!session ? (
        <main className="student-onboarding">
          <section className="student-onboarding__intro">
            <p className="eyebrow">Your space to ask what happens next</p>
            <h1>Something happened. Let&apos;s work out what to do.</h1>
            <p>
              Describe it in your own words. Civic Bridge can help you
              understand the harm, protect yourself or a friend, and compare
              your next options.
            </p>

            <div
              className="student-support-goals"
              aria-label="How Civic Bridge can help"
            >
              {supportGoals.map((goal) => (
                <article key={goal.number}>
                  <span>{goal.number}</span>
                  <div>
                    <strong>{goal.title}</strong>
                    <p>{goal.description}</p>
                  </div>
                </article>
              ))}
            </div>

            <div className="student-privacy-note">
              <span aria-hidden="true">i</span>
              <p>
                <strong>Keep it anonymous.</strong> Do not enter names, your
                school, usernames, profile links, addresses, or other details
                that identify someone.
              </p>
            </div>
          </section>

          <section className="student-form-card" aria-labelledby="context-title">
            <div className="student-form-card__heading">
              <span>60-second setup</span>
              <h2 id="context-title">Make the guidance fit you</h2>
              <p>
                We use these details for age-appropriate, locally relevant
                support. We do not need your identity.
              </p>
            </div>

            <ol className="student-journey" aria-label="Support journey">
              <li className="student-journey__active">
                <span>1</span>
                Set context
              </li>
              <li>
                <span>2</span>
                Tell your story
              </li>
              <li>
                <span>3</span>
                Choose a next step
              </li>
            </ol>

            <form onSubmit={handleContextSubmit}>
              <div className="student-form-grid">
                <label>
                  <span>Country</span>
                  <select
                    autoComplete="country-name"
                    name="country"
                    onChange={(event) => handleCountryChange(event.target.value)}
                    required
                    value={contextForm.country}
                  >
                    <option value="">Select an EU country</option>
                    {euCountries.map((country) => (
                      <option key={country.name} value={country.name}>
                        {country.name}
                      </option>
                    ))}
                  </select>
                </label>

                <label>
                  <span>Region / Area</span>
                  <input
                    autoComplete="address-level1"
                    maxLength={120}
                    minLength={2}
                    name="region_area"
                    onChange={(event) =>
                      setContextForm((current) => ({
                        ...current,
                        region_area: event.target.value,
                      }))
                    }
                    placeholder="e.g. Nicosia"
                    required
                    value={contextForm.region_area}
                  />
                </label>

                <label className="student-form-grid__wide">
                  <span>Preferred language</span>
                  <select
                    autoComplete="language"
                    disabled={!selectedCountry}
                    name="language"
                    onChange={(event) =>
                      setContextForm((current) => ({
                        ...current,
                        language: event.target.value,
                      }))
                    }
                    required
                    value={contextForm.language}
                  >
                    {!selectedCountry && (
                      <option value="">Select a country first</option>
                    )}
                    {selectedCountry && (
                      <optgroup label={`Official in ${selectedCountry.name}`}>
                        {selectedCountry.officialLanguages.map((language) => (
                          <option key={language} value={language}>
                            {language}
                          </option>
                        ))}
                      </optgroup>
                    )}
                    {selectedCountry && otherLanguages.length > 0 && (
                      <optgroup label="Other available languages">
                        {otherLanguages.map((language) => (
                          <option key={language} value={language}>
                            {language}
                          </option>
                        ))}
                      </optgroup>
                    )}
                  </select>
                  <small className="student-field-note">
                    The country&apos;s default official language is selected
                    automatically. You can choose another language.
                  </small>
                </label>
              </div>

              <fieldset className="age-band-fieldset">
                <legend>Age band</legend>
                <div className="age-band-options">
                  {ageBands.map((ageBand) => (
                    <label key={ageBand.value}>
                      <input
                        checked={contextForm.age_band === ageBand.value}
                        name="age_band"
                        onChange={() =>
                          setContextForm((current) => ({
                            ...current,
                            age_band: ageBand.value,
                          }))
                        }
                        type="radio"
                        value={ageBand.value}
                      />
                      <span>
                        <strong>{ageBand.label}</strong>
                        <small>{ageBand.note}</small>
                      </span>
                    </label>
                  ))}
                </div>
              </fieldset>

              {error && (
                <p className="student-error" role="alert">
                  {error}
                </p>
              )}

              <button
                className="student-submit-button"
                disabled={isStarting}
                type="submit"
              >
                {isStarting ? 'Starting conversation...' : 'Continue to chat'}
                <span aria-hidden="true">&rarr;</span>
              </button>
            </form>
          </section>
        </main>
      ) : (
        <main className="student-chat">
          <aside className="student-context-panel">
            <div>
              <p className="eyebrow">Your support path</p>
              <h1>You set the pace.</h1>
              <p>
                Get a simple explanation, a practical plan, or both. You can
                stop or change direction at any time.
              </p>
            </div>

            <ol
              className="student-chat-journey"
              aria-label="Conversation progress"
            >
              <li className="student-chat-journey__done">
                <span>1</span>
                Context ready
              </li>
              <li
                className={
                  !hasStudentMessage
                    ? 'student-chat-journey__active'
                    : 'student-chat-journey__done'
                }
              >
                <span>2</span>
                Describe what happened
              </li>
              <li
                className={
                  hasStudentMessage
                    ? 'student-chat-journey__active'
                    : undefined
                }
              >
                <span>3</span>
                Explore your options
              </li>
            </ol>

            <dl>
              <div>
                <dt>Country</dt>
                <dd>{session.context.country}</dd>
              </div>
              <div>
                <dt>Region / Area</dt>
                <dd>{session.context.region_area}</dd>
              </div>
              <div>
                <dt>Language</dt>
                <dd>{session.context.language}</dd>
              </div>
              <div>
                <dt>Age band</dt>
                <dd>{session.context.age_band}</dd>
              </div>
            </dl>

            <button className="student-reset-button" onClick={resetSession}>
              Change context
            </button>

            <div className="student-safety-card">
              <strong>Immediate danger?</strong>
              <p>
                Contact local emergency services or a trusted adult nearby.
                This chat is not an emergency service.
              </p>
            </div>

            <p className="student-boundary-note">
              Civic Bridge can explain risk signals and options. It cannot
              decide whether a crime happened or whether someone should be
              punished or expelled.
            </p>
          </aside>

          <section className="chat-panel" aria-labelledby="chat-title">
            <header className="chat-panel__header">
              <div>
                <span className="chat-status">
                  <span aria-hidden="true" />
                  Ready when you are
                </span>
                <h2 id="chat-title">Start wherever feels easiest</h2>
              </div>
              <span className="chat-panel__privacy">No identifying details</span>
            </header>

            <div className="chat-messages" aria-live="polite">
              {!hasStudentMessage && (
                <section
                  className="student-starters"
                  aria-labelledby="starter-title"
                >
                  <div>
                    <span>Not sure what to type?</span>
                    <h3 id="starter-title">Choose a starting point</h3>
                  </div>
                  <div className="student-starters__actions">
                    {starterActions.map((action) => (
                      <button
                        key={action.label}
                        onClick={() => chooseStarter(action.prompt)}
                        type="button"
                      >
                        {action.label}
                        <span aria-hidden="true">&rarr;</span>
                      </button>
                    ))}
                  </div>
                </section>
              )}

              {messages.map((message) => (
                <article
                  className={`chat-message chat-message--${message.role}`}
                  key={message.id}
                >
                  <span className="chat-message__author">
                    {message.role === 'assistant' ? 'Civic Bridge' : 'You'}
                  </span>
                  {message.role === 'assistant' &&
                  message.analysisUnavailable ? (
                    <p className="chat-analysis-unavailable" role="status">
                      Incident analysis is temporarily unavailable. The chat
                      response is still shown below.
                    </p>
                  ) : null}
                  {message.role === 'assistant' ? (
                    <ChatMarkdown content={message.content} />
                  ) : (
                    <p className="chat-message__body">{message.content}</p>
                  )}
                  {message.role === 'assistant' && message.analysis ? (
                    <ChatAnalysisCard analysis={message.analysis} />
                  ) : null}
                  {message.role === 'assistant' &&
                  message.analyticsStorageFailed ? (
                    <p className="chat-analysis-unavailable" role="status">
                      One or more structured analytics results could not be
                      added to the dashboard.
                    </p>
                  ) : null}
                  {message.role === 'assistant' && message.references ? (
                    <ChatReferences references={message.references} />
                  ) : null}
                </article>
              ))}

              {isSending && (
                <article className="chat-message chat-message--assistant">
                  <span className="chat-message__author">Civic Bridge</span>
                  <p className="chat-message__body chat-thinking">
                    {isAnonymizing
                      ? 'Removing identifying details locally...'
                      : 'Analyzing the incident and preparing guidance...'}
                  </p>
                </article>
              )}
              <div ref={messagesEndRef} />
            </div>

            <form className="chat-composer" onSubmit={handleMessageSubmit}>
              {error && (
                <p className="student-error" role="alert">
                  {error}
                </p>
              )}
              <label htmlFor="incident-message">
                Ask a question or describe what happened
              </label>
              <div className="chat-composer__input">
                <div className="chat-composer__textarea-shell">
                  <textarea
                    id="incident-message"
                    maxLength={4000}
                    onChange={(event) => setDraft(event.target.value)}
                    onKeyDown={handleComposerKeyDown}
                    placeholder="Use simple words. You can say what happened, how it affected you, and what help you want."
                    ref={composerRef}
                    rows={3}
                    value={draft}
                  />
                  <ChatImageAttachmentInput
                    attachment={pendingImage}
                    disabled={isSending}
                    inputId="student-image-attachment"
                    isProcessing={isProcessingImage}
                    onRemoveImage={() => setPendingImage(null)}
                    onSelectImage={handleImageSelected}
                  />
                </div>
                <button
                  className="chat-composer__send-button"
                  disabled={
                    (!draft.trim() && !pendingImage) ||
                    isSending ||
                    isProcessingImage
                  }
                  type="submit"
                >
                  Send
                  <span aria-hidden="true">&uarr;</span>
                </button>
              </div>
              <p>
                Typed text is anonymized before sending. Attached images are
                processed with your prompt by the RAG service. Press Enter to
                send; use Shift + Enter for a new line.
              </p>
            </form>
          </section>
        </main>
      )}
    </div>
  )
}

export default StudentsPage
