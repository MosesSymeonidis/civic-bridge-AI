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
import { buildIncidentProfileDashboardUrl } from '../services/dashboardProfileLinks'
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
import {
  buildIncidentActivityPrompt,
  clearEducatorActivityHandoff,
  loadEducatorActivityHandoff,
  type EducatorActivityHandoff,
} from '../services/educatorActivityHandoff'
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

type LearnerAgeBand = '6-9' | '10-13' | '14-17' | '18+' | 'mixed'
type EducatorRole =
  | 'classroom-teacher'
  | 'school-leader'
  | 'counselor-psychologist'
  | 'youth-worker'
  | 'teacher-educator'
  | 'other'
type EducationSetting =
  | 'primary-school'
  | 'secondary-school'
  | 'higher-education'
  | 'vocational-training'
  | 'non-formal-youth'
  | 'other'
type SupportGoal =
  | 'understand-incident'
  | 'support-learner'
  | 'classroom-activity'
  | 'counter-narrative'
  | 'reporting-next-steps'

type EducatorContext = {
  country: string
  region_area: string
  language: string
  educator_role: EducatorRole
  learner_age_band: LearnerAgeBand
  education_setting: EducationSetting
  support_goal: SupportGoal
}

type EducatorSessionResponse = {
  session_id: string
  context: EducatorContext
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
  role: 'educator' | 'assistant'
  content: string
  analysis?: ChatAnalysis
  analysisUnavailable?: boolean
  analyticsStorageFailed?: boolean
  references?: ChatReference[]
}

type InitialEducatorState = {
  contextForm: EducatorContext
  activityHandoff: EducatorActivityHandoff | null
}

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? '/api/v1'
const ragApiBaseUrl = import.meta.env.VITE_RAG_API_BASE_URL ?? '/rag-api'
const classifierApiBaseUrl =
  import.meta.env.VITE_CLASSIFIER_API_BASE_URL ?? '/classifier-api'

const educatorRoles: Array<{ value: EducatorRole; label: string }> = [
  { value: 'classroom-teacher', label: 'Classroom teacher' },
  { value: 'school-leader', label: 'School leader' },
  {
    value: 'counselor-psychologist',
    label: 'Counsellor / psychologist',
  },
  { value: 'youth-worker', label: 'Youth worker' },
  { value: 'teacher-educator', label: 'Teacher educator' },
  { value: 'other', label: 'Other education role' },
]

const educationSettings: Array<{
  value: EducationSetting
  label: string
}> = [
  { value: 'primary-school', label: 'Primary school' },
  { value: 'secondary-school', label: 'Secondary school' },
  { value: 'higher-education', label: 'Higher education' },
  { value: 'vocational-training', label: 'Vocational training' },
  { value: 'non-formal-youth', label: 'Non-formal / youth setting' },
  { value: 'other', label: 'Other setting' },
]

const learnerAgeBands: Array<{
  value: LearnerAgeBand
  label: string
  note: string
}> = [
  { value: '6-9', label: '6-9', note: 'Early primary' },
  { value: '10-13', label: '10-13', note: 'Upper primary' },
  { value: '14-17', label: '14-17', note: 'Secondary' },
  { value: '18+', label: '18+', note: 'Adult learners' },
  { value: 'mixed', label: 'Mixed', note: 'Multiple ages' },
]

const supportGoals: Array<{
  value: SupportGoal
  label: string
  description: string
}> = [
  {
    value: 'understand-incident',
    label: 'Understand an incident',
    description: 'Analyse the language, narrative, and context.',
  },
  {
    value: 'support-learner',
    label: 'Support an affected learner',
    description: 'Plan a safe, age-appropriate response.',
  },
  {
    value: 'classroom-activity',
    label: 'Create a learning activity',
    description: 'Turn the case into guided democratic learning.',
  },
  {
    value: 'counter-narrative',
    label: 'Develop a counter-narrative',
    description: 'Prepare a bridge formulation or response.',
  },
  {
    value: 'reporting-next-steps',
    label: 'Consider reporting steps',
    description: 'Review evidence and institutional next actions.',
  },
]

const classroomActivitySupportGoal =
  supportGoals.find((goal) => goal.value === 'classroom-activity') ??
  supportGoals[0]

const supportGoalSamplePrompts: Record<SupportGoal, string> = {
  'understand-incident':
    'A learner shared an online post that uses harmful stereotypes about a protected group. Help me analyse the language, narrative, context, and possible impact without making a legal determination.',
  'support-learner':
    'A learner was targeted by repeated harmful comments about their identity and is distressed. Help me plan an age-appropriate, supportive response and identify any immediate safeguarding steps.',
  'classroom-activity':
    'A harmful statement about a protected group caused disagreement in class. Create a 45-minute, age-appropriate activity that helps learners examine the claim, compare perspectives, and practise constructive dialogue.',
  'counter-narrative':
    'A harmful message claims that all members of a protected group are dangerous. Help me develop a concise counter-narrative that corrects the generalisation without repeating or amplifying the harm.',
  'reporting-next-steps':
    'An anonymized harmful post targeting a protected group is still available online. Help me identify what evidence to preserve and which institutional reporting and safeguarding steps to consider.',
}

const initialContext: EducatorContext = {
  country: '',
  region_area: '',
  language: '',
  educator_role: 'classroom-teacher',
  learner_age_band: '14-17',
  education_setting: 'secondary-school',
  support_goal: 'understand-incident',
}

function uniqueNonEmpty(values: string[]): string[] {
  return Array.from(
    new Set(values.map((value) => value.trim()).filter(Boolean)),
  )
}

function sharedValue(values: string[]): string {
  const uniqueValues = uniqueNonEmpty(values)
  return uniqueValues.length === 1 ? uniqueValues[0] : ''
}

function isLearnerAgeBand(value: string): value is LearnerAgeBand {
  return learnerAgeBands.some((ageBand) => ageBand.value === value)
}

function contextDefaultsFromActivityHandoff(
  handoff: EducatorActivityHandoff,
): Partial<EducatorContext> {
  const country = sharedValue(
    handoff.incidents.map((incident) => incident.country),
  )
  const availableCountry = euCountries.find((item) => item.name === country)
  const language = sharedValue(
    handoff.incidents.map((incident) => incident.language),
  )
  const regionArea =
    sharedValue(handoff.incidents.map((incident) => incident.regionArea)) ||
    'Multiple regions'
  const learnerAgeBand = sharedValue(
    handoff.incidents.map((incident) => incident.learnerAgeBand),
  )
  const languageForCountry =
    availableCountry && availableLanguages.includes(language)
      ? language
      : availableCountry?.defaultLanguage ?? ''

  return {
    country: availableCountry?.name ?? '',
    region_area: regionArea,
    language: languageForCountry,
    learner_age_band: isLearnerAgeBand(learnerAgeBand)
      ? learnerAgeBand
      : 'mixed',
    support_goal: 'classroom-activity',
  }
}

function createInitialEducatorState(): InitialEducatorState {
  const activityHandoff = loadEducatorActivityHandoff()

  return {
    activityHandoff,
    contextForm: {
      ...initialContext,
      ...(activityHandoff
        ? contextDefaultsFromActivityHandoff(activityHandoff)
        : {}),
    },
  }
}

function labelFor<T extends string>(
  choices: Array<{ value: T; label: string }>,
  value: T,
): string {
  return choices.find((choice) => choice.value === value)?.label ?? value
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

function EducatorsPage() {
  const [initialState] = useState<InitialEducatorState>(
    createInitialEducatorState,
  )
  const [contextForm, setContextForm] = useState<EducatorContext>(
    initialState.contextForm,
  )
  const [activityHandoff] =
    useState<EducatorActivityHandoff | null>(
      initialState.activityHandoff,
    )
  const [session, setSession] = useState<EducatorSessionResponse | null>(null)
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
    if (activityHandoff) clearEducatorActivityHandoff()
  }, [activityHandoff])

  useEffect(() => {
    void preloadAnonymizer().catch(() => undefined)
  }, [])

  function handleCountryChange(countryName: string) {
    const country = euCountries.find((item) => item.name === countryName)
    setContextForm((current) => ({
      ...current,
      country: countryName,
      language: country?.defaultLanguage ?? '',
    }))
  }

  function handleSupportGoalChange(supportGoal: SupportGoal) {
    if (activityHandoff) return

    setContextForm((current) => ({
      ...current,
      support_goal: supportGoal,
    }))
    setDraft(supportGoalSamplePrompts[supportGoal])
  }

  async function handleContextSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError('')
    setIsStarting(true)

    try {
      const response = await fetch(`${apiBaseUrl}/educators/sessions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(contextForm),
      })

      if (!response.ok) {
        throw new Error(await readApiError(response))
      }

      const createdSession = (await response.json()) as EducatorSessionResponse
      setSession(createdSession)
      setContextForm(createdSession.context)
      setDraft(
        activityHandoff
          ? buildIncidentActivityPrompt(activityHandoff)
          : supportGoalSamplePrompts[createdSession.context.support_goal],
      )
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
          : 'The educator workspace could not be started.',
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
      { id: createUuid(), role: 'educator', content: displayedMessage },
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
          role: 'teacher',
          age_band: session.context.learner_age_band,
          country: session.context.country,
          message: safeMessage,
          image: imageAttachment
            ? {
                image: imageAttachment.image,
                filename: imageAttachment.fileName,
                mime_type: imageAttachment.mediaType,
              }
            : undefined,
          mode: session.context.support_goal,
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
            'educators',
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
            ageBand: session.context.learner_age_band,
            role: 'teacher',
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
            participant: 'educators',
            sessionId: session.session_id,
            eventId: analyticsEventId,
            messageCount:
              messages.filter((item) => item.role === 'educator').length + 1,
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

  return (
    <div className="student-page educator-page">
      <header className="student-topbar">
        <a className="brand" href="/" aria-label="Return to Civic Bridge AI">
          <span className="brand__mark" aria-hidden="true">
            <span />
            <span />
            <span />
          </span>
          <span>Civic Bridge AI</span>
        </a>
        <span className="student-topbar__label">Educator workspace</span>
        <a className="student-back-link" href="/">
          Back to overview
        </a>
      </header>

      {!session ? (
        <main className="student-onboarding educator-onboarding">
          <section className="student-onboarding__intro">
            <p className="eyebrow">Educators</p>
            <h1>Frame the learning need before the conversation.</h1>
            <p>
              Your professional context helps the assistant tailor its
              questions, developmental guidance, and suggested next steps.
            </p>

            <div className="student-privacy-note">
              <span aria-hidden="true">i</span>
              <p>
                Do not enter learner names, school names, account details, or
                other information that could identify a person.
              </p>
            </div>
          </section>

          <section
            className="student-form-card educator-form-card"
            aria-labelledby="educator-context-title"
          >
            <div className="student-form-card__heading">
              <span>Step 1 of 2</span>
              <h2 id="educator-context-title">
                Set your educator context
              </h2>
              <p>All seven fields guide the conversation.</p>
            </div>

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

                <label>
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
                </label>

                <label>
                  <span>Your role</span>
                  <select
                    name="educator_role"
                    onChange={(event) =>
                      setContextForm((current) => ({
                        ...current,
                        educator_role: event.target.value as EducatorRole,
                      }))
                    }
                    value={contextForm.educator_role}
                  >
                    {educatorRoles.map((role) => (
                      <option key={role.value} value={role.value}>
                        {role.label}
                      </option>
                    ))}
                  </select>
                </label>

                <label className="student-form-grid__wide">
                  <span>Education setting</span>
                  <select
                    name="education_setting"
                    onChange={(event) =>
                      setContextForm((current) => ({
                        ...current,
                        education_setting: event.target
                          .value as EducationSetting,
                      }))
                    }
                    value={contextForm.education_setting}
                  >
                    {educationSettings.map((setting) => (
                      <option key={setting.value} value={setting.value}>
                        {setting.label}
                      </option>
                    ))}
                  </select>
                </label>
              </div>

              <fieldset className="age-band-fieldset">
                <legend>Learner age band</legend>
                <div className="age-band-options educator-age-options">
                  {learnerAgeBands.map((ageBand) => (
                    <label key={ageBand.value}>
                      <input
                        checked={
                          contextForm.learner_age_band === ageBand.value
                        }
                        name="learner_age_band"
                        onChange={() =>
                          setContextForm((current) => ({
                            ...current,
                            learner_age_band: ageBand.value,
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

              <fieldset className="educator-support-fieldset">
                <legend>What support do you need?</legend>
                {activityHandoff ? (
                  <div className="educator-support-options educator-support-options--single">
                    <div className="educator-support-locked">
                      <strong>{classroomActivitySupportGoal.label}</strong>
                      <small>
                        {classroomActivitySupportGoal.description}
                      </small>
                    </div>
                  </div>
                ) : (
                  <div className="educator-support-options">
                    {supportGoals.map((goal) => (
                      <label key={goal.value}>
                        <input
                          checked={contextForm.support_goal === goal.value}
                          name="support_goal"
                          onChange={() => handleSupportGoalChange(goal.value)}
                          type="radio"
                          value={goal.value}
                        />
                        <span>
                          <strong>{goal.label}</strong>
                          <small>{goal.description}</small>
                        </span>
                      </label>
                    ))}
                  </div>
                )}
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
        <main className="student-chat educator-chat">
          <aside className="student-context-panel educator-context-panel">
            <div>
              <p className="eyebrow">Your educator context</p>
              <h1>Teaching support chat</h1>
              <p>
                The assistant uses these parameters when responding to your
                professional questions.
              </p>
            </div>

            <dl>
              <div>
                <dt>Location</dt>
                <dd>
                  {session.context.region_area}, {session.context.country}
                </dd>
              </div>
              <div>
                <dt>Language</dt>
                <dd>{session.context.language}</dd>
              </div>
              <div>
                <dt>Role</dt>
                <dd>
                  {labelFor(educatorRoles, session.context.educator_role)}
                </dd>
              </div>
              <div>
                <dt>Setting</dt>
                <dd>
                  {labelFor(
                    educationSettings,
                    session.context.education_setting,
                  )}
                </dd>
              </div>
              <div>
                <dt>Learners</dt>
                <dd>{session.context.learner_age_band}</dd>
              </div>
              <div>
                <dt>Support goal</dt>
                <dd>
                  {labelFor(supportGoals, session.context.support_goal)}
                </dd>
              </div>
            </dl>

            <button className="student-reset-button" onClick={resetSession}>
              Change context
            </button>

            <div className="student-safety-card educator-duty-card">
              <strong>Safeguarding responsibility</strong>
              <p>
                Follow your institution&apos;s safeguarding and emergency
                procedures whenever a learner may be at risk.
              </p>
            </div>
          </aside>

          <section className="chat-panel" aria-labelledby="educator-chat-title">
            <header className="chat-panel__header">
              <div>
                <span className="chat-status">
                  <span aria-hidden="true" />
                  Educator context active
                </span>
                <h2 id="educator-chat-title">
                  Describe the incident or learning need
                </h2>
              </div>
              <span className="chat-panel__privacy">
                No learner identifiers
              </span>
            </header>

            <div className="chat-messages" aria-live="polite">
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
                    <ChatMarkdown
                      content={message.content}
                      dashboardUrl={
                        message.analysis && session
                          ? buildIncidentProfileDashboardUrl(
                              {
                                country: session.context.country,
                                regionArea: session.context.region_area,
                                language: session.context.language,
                              },
                            )
                          : undefined
                      }
                    />
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
              <label htmlFor="educator-message">
                Incident or educational challenge
              </label>
              <div className="chat-composer__input">
                <div className="chat-composer__textarea-shell">
                  <textarea
                    id="educator-message"
                    maxLength={4000}
                    onChange={(event) => setDraft(event.target.value)}
                    onKeyDown={handleComposerKeyDown}
                    placeholder="Describe the situation without learner names, school names, usernames, or other identifying details."
                    rows={3}
                    value={draft}
                  />
                  <ChatImageAttachmentInput
                    attachment={pendingImage}
                    disabled={isSending}
                    inputId="educator-image-attachment"
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

export default EducatorsPage
