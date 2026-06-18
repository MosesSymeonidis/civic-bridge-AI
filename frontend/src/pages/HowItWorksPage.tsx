const pipelineLayers = [
  {
    tone: 'blue',
    title: 'Role + age + country',
    description:
      'Teacher or student, age band, Cyprus or another country context.',
  },
  {
    tone: 'red',
    title: 'Safety and privacy screen',
    description:
      'Triage if a child appears personally targeted; no names, profiles, or school identifiers.',
  },
  {
    tone: 'amber',
    title: 'Two-axis analysis',
    description:
      'Severity tier plus semantic barriers that explain how dialogue is blocked.',
  },
  {
    tone: 'green',
    title: 'Teaching and response path',
    description:
      'Understand it, teach with it, or report and escalate with country-specific contacts.',
  },
  {
    tone: 'violet',
    title: 'Evidence layer',
    description:
      'Council of Europe standards, ECHR cases, source citations, and local registries.',
  },
]

const methodCards = [
  {
    tag: 'Grounded standards',
    title: 'Council of Europe risk signals',
    description:
      'Civic Bridge AI uses a four-tier severity model grounded in Council of Europe Recommendation CM/Rec(2022)16. It distinguishes protected offensive expression from denigration, dehumanisation, and incitement risk.',
  },
  {
    tag: 'Semantic barriers',
    title: 'What the message does to dialogue',
    description:
      'The system looks for seven codebook mechanisms: rigid opposition, transfer of meaning, prohibited thoughts, stigma, undermining the motive, distrust, and bracketing. This shifts the focus from labels to repairable dialogue failures.',
  },
  {
    tag: 'Practical guidance',
    title: 'From risk signal to next step',
    description:
      'The assistant offers a controlled path: understand the incident, teach with it, or report it. Legal determination stays with human authorities while educators focus on safe, proportionate action.',
  },
]

const ageGroups = [
  ['6-9', 'Simplified language, with no harsh repetition.'],
  ['10-13', 'Gentle examples and severe-span redaction.'],
  ['14-17', 'More explicit reasoning and realistic counter-speech.'],
  ['18+', 'Fuller explanation and professional framing.'],
]

const teachingSteps = [
  {
    title: 'Notice the target and frame.',
    description:
      'Who is being spoken about, and as what kind of person or group?',
  },
  {
    title: 'Name the semantic barrier.',
    description:
      'Identify the mechanism: rigid opposition, transfer of meaning, stigma, distrust, prohibited thoughts, undermining the motive, or bracketing.',
  },
  {
    title: 'Connect to RFCDC competences.',
    description:
      'Use democratic culture competences such as empathy, critical thinking, respect, and tolerance of ambiguity.',
  },
  {
    title: 'Choose a safe response path.',
    description:
      'Classroom activity, supportive conversation, counter-speech, documentation, or country-specific reporting.',
  },
]

const barriers = [
  {
    title: 'Rigid opposition',
    description:
      'Binary us-versus-them framing that leaves no middle ground: "they will never change".',
  },
  {
    title: 'Transfer of meaning',
    description:
      'Linking a group to an already loaded category such as invasion, disease, or foreign agents, so hostility transfers automatically.',
  },
  {
    title: 'Prohibited thoughts',
    description:
      'Marking the alternative view as dangerous even to consider: "it would be the end of us".',
  },
  {
    title: 'Stigma',
    description:
      'Branding people who engage with the other side as traitors or naive, enforcing conformity.',
  },
  {
    title: 'Undermining the motive',
    description:
      'Dismissing a speaker by attacking who pays or drives them instead of what they say.',
  },
  {
    title: 'Distrust',
    description:
      'Categorical, history-laden distrust of an entire group as a source: "you cannot trust a single one".',
  },
  {
    title: 'Bracketing',
    description:
      'Holding the other view at a distance through hedging or refusal: "their version of history" or "nothing to discuss".',
  },
]

const evidenceSources = [
  {
    title: 'CM/Rec(2022)16',
    description:
      'Graduated hate-speech standards and explanatory guidance.',
  },
  {
    title: 'ECHR Article 10',
    description:
      'Freedom of expression context and case-law framing.',
  },
  {
    title: 'ECRI and CoE reports',
    description:
      'Policy evidence and democratic-resilience context.',
  },
  {
    title: 'Country registries',
    description:
      'Cyprus support, hotlines, equality body, and reporting contacts.',
  },
]

const evidenceNumbers = [
  ['439', 'indexed passages from 7 Council of Europe documents'],
  ['58', 'European Court of Human Rights cases, theme-tagged'],
  ['15', 'curated legal passages with citable IDs'],
  ['46', 'member states in the support registry, Cyprus verified'],
]

const hiddenLayers = [
  {
    title: 'Analysis card',
    description:
      'The tier card is generated separately from the conversational reply. It shows risk signals for human review while the assistant keeps the conversation focused on next steps.',
  },
  {
    title: 'Retrieval with citations',
    description:
      'Open questions trigger retrieval from the legal corpus. The interface keeps sources compact, but every reference can be opened.',
  },
  {
    title: 'Reporting support',
    description:
      'Reporting contacts appear when escalation is chosen, including country-specific options such as Cyprus cybercrime, helplines, and equality-body information.',
  },
]

const safeguards = [
  {
    title: 'No legal determinations.',
    description:
      'The system describes risk signals; authorities and courts decide legality.',
  },
  {
    title: 'Human review by design.',
    description:
      'The output supports educators and reviewers, not automated enforcement.',
  },
  {
    title: 'Privacy-first prompts.',
    description:
      'It avoids usernames, school names, profile links, exact locations, and names of minors.',
  },
  {
    title: 'Safety triage for students.',
    description:
      'If a student may be personally targeted, support and help-seeking take priority.',
  },
]

function TwoAxisAnalysisPlot() {
  return (
    <figure className="hiw-plot">
      <div className="hiw-plot__canvas">
        <svg
          viewBox="0 0 880 380"
          role="img"
          aria-labelledby="two-axis-plot-title two-axis-plot-description"
        >
          <title id="two-axis-plot-title">
            Two independent analysis axes lead to different response paths
          </title>
          <desc id="two-axis-plot-description">
            A post receives one grounded analysis. Its severity tier informs
            response and reporting, while its semantic barriers inform
            education and dialogue repair.
          </desc>
          <defs>
            <marker
              id="hiw-analysis-arrow"
              viewBox="0 0 10 10"
              refX="9"
              refY="5"
              markerWidth="7"
              markerHeight="7"
              orient="auto-start-reverse"
            >
              <path d="M0 0L10 5L0 10z" fill="#738078" />
            </marker>
          </defs>

          <text x="20" y="34" fontSize="15" fontWeight="700" fill="#17211c">
            Two independent axes, two different paths
          </text>

          <rect
            x="20"
            y="150"
            width="160"
            height="104"
            rx="4"
            fill="#fff"
            stroke="#d7d8d0"
          />
          <text
            x="100"
            y="178"
            textAnchor="middle"
            fontSize="14"
            fontWeight="700"
            fill="#17211c"
          >
            A post
          </text>
          <line
            x1="40"
            y1="196"
            x2="160"
            y2="196"
            stroke="#cfd3ce"
            strokeWidth="6"
            strokeLinecap="round"
          />
          <line
            x1="40"
            y1="214"
            x2="140"
            y2="214"
            stroke="#cfd3ce"
            strokeWidth="6"
            strokeLinecap="round"
          />
          <line
            x1="40"
            y1="232"
            x2="152"
            y2="232"
            stroke="#cfd3ce"
            strokeWidth="6"
            strokeLinecap="round"
          />

          <line
            x1="182"
            y1="202"
            x2="240"
            y2="202"
            stroke="#738078"
            strokeWidth="2"
            markerEnd="url(#hiw-analysis-arrow)"
          />

          <rect
            x="244"
            y="142"
            width="196"
            height="120"
            rx="4"
            fill="#184f3e"
          />
          <text
            x="342"
            y="186"
            textAnchor="middle"
            fontSize="15"
            fontWeight="700"
            fill="#fff"
          >
            One grounded
          </text>
          <text
            x="342"
            y="206"
            textAnchor="middle"
            fontSize="15"
            fontWeight="700"
            fill="#fff"
          >
            analysis
          </text>
          <text
            x="342"
            y="234"
            textAnchor="middle"
            fontSize="11"
            fill="#bad9c7"
          >
            CoE standards + codebook
          </text>

          <path
            d="M442 176 C496 176 496 98 540 98"
            fill="none"
            stroke="#738078"
            strokeWidth="2"
            markerEnd="url(#hiw-analysis-arrow)"
          />
          <path
            d="M442 228 C496 228 496 306 540 306"
            fill="none"
            stroke="#738078"
            strokeWidth="2"
            markerEnd="url(#hiw-analysis-arrow)"
          />

          <text
            x="544"
            y="64"
            fontSize="11"
            fontWeight="750"
            fill="#a9671e"
            letterSpacing="1"
          >
            AXIS 1
          </text>
          <rect
            x="544"
            y="72"
            width="150"
            height="64"
            rx="4"
            fill="#fff"
            stroke="#a9671e"
            strokeWidth="1.6"
          />
          <text
            x="619"
            y="98"
            textAnchor="middle"
            fontSize="13.5"
            fontWeight="700"
            fill="#17211c"
          >
            Severity tier 1-4
          </text>
          <text
            x="619"
            y="118"
            textAnchor="middle"
            fontSize="11.5"
            fill="#59665f"
          >
            how harmful is this?
          </text>
          <line
            x1="696"
            y1="104"
            x2="724"
            y2="104"
            stroke="#738078"
            strokeWidth="2"
            markerEnd="url(#hiw-analysis-arrow)"
          />
          <rect
            x="728"
            y="72"
            width="132"
            height="64"
            rx="4"
            fill="#a74b43"
          />
          <text
            x="794"
            y="98"
            textAnchor="middle"
            fontSize="13.5"
            fontWeight="700"
            fill="#fff"
          >
            Respond + report
          </text>
          <text
            x="794"
            y="118"
            textAnchor="middle"
            fontSize="11"
            fill="#f3d9d6"
          >
            authorities, report draft
          </text>

          <text
            x="544"
            y="272"
            fontSize="11"
            fontWeight="750"
            fill="#2b6f94"
            letterSpacing="1"
          >
            AXIS 2
          </text>
          <rect
            x="544"
            y="280"
            width="150"
            height="64"
            rx="4"
            fill="#fff"
            stroke="#2b6f94"
            strokeWidth="1.6"
          />
          <text
            x="619"
            y="306"
            textAnchor="middle"
            fontSize="13.5"
            fontWeight="700"
            fill="#17211c"
          >
            Semantic barriers
          </text>
          <text
            x="619"
            y="326"
            textAnchor="middle"
            fontSize="11.5"
            fill="#59665f"
          >
            what blocks dialogue?
          </text>
          <line
            x1="696"
            y1="312"
            x2="724"
            y2="312"
            stroke="#738078"
            strokeWidth="2"
            markerEnd="url(#hiw-analysis-arrow)"
          />
          <rect
            x="728"
            y="280"
            width="132"
            height="64"
            rx="4"
            fill="#184f3e"
          />
          <text
            x="794"
            y="306"
            textAnchor="middle"
            fontSize="13.5"
            fontWeight="700"
            fill="#fff"
          >
            Educate
          </text>
          <text
            x="794"
            y="326"
            textAnchor="middle"
            fontSize="11"
            fill="#d5e7dc"
          >
            counter-strategies, activities
          </text>
        </svg>
      </div>
      <figcaption>
        A post can be lawful yet loaded with barriers. That is the content
        conventional moderation ignores and education can address.
      </figcaption>
    </figure>
  )
}

function SafetyPipelinePlot() {
  return (
    <figure className="hiw-plot hiw-plot--dark">
      <div className="hiw-plot__canvas">
        <svg
          viewBox="0 0 880 310"
          role="img"
          aria-labelledby="safety-plot-title safety-plot-description"
        >
          <title id="safety-plot-title">
            Safety checks run before and after AI analysis
          </title>
          <desc id="safety-plot-description">
            A student message first passes through deterministic triage. A
            personal safety concern branches directly to human help. Other
            messages receive grounded AI analysis followed by deterministic
            output guards.
          </desc>
          <defs>
            <marker
              id="hiw-safety-arrow"
              viewBox="0 0 10 10"
              refX="9"
              refY="5"
              markerWidth="7"
              markerHeight="7"
              orient="auto-start-reverse"
            >
              <path d="M0 0L10 5L0 10z" fill="#738078" />
            </marker>
          </defs>

          <text x="20" y="34" fontSize="15" fontWeight="700" fill="#17211c">
            Safety is enforced in code, before and after the AI
          </text>

          <rect
            x="20"
            y="92"
            width="120"
            height="56"
            rx="4"
            fill="#fff"
            stroke="#d7d8d0"
          />
          <text
            x="80"
            y="116"
            textAnchor="middle"
            fontSize="13"
            fontWeight="700"
            fill="#17211c"
          >
            Message
          </text>
          <text
            x="80"
            y="134"
            textAnchor="middle"
            fontSize="11"
            fill="#59665f"
          >
            from a student
          </text>
          <line
            x1="142"
            y1="120"
            x2="176"
            y2="120"
            stroke="#738078"
            strokeWidth="2"
            markerEnd="url(#hiw-safety-arrow)"
          />

          <rect
            x="180"
            y="84"
            width="168"
            height="72"
            rx="4"
            fill="#fbf1df"
            stroke="#a9671e"
            strokeWidth="1.6"
          />
          <text
            x="264"
            y="110"
            textAnchor="middle"
            fontSize="13"
            fontWeight="700"
            fill="#17211c"
          >
            Triage screen
          </text>
          <text
            x="264"
            y="128"
            textAnchor="middle"
            fontSize="11"
            fill="#59665f"
          >
            rule-based, runs first,
          </text>
          <text
            x="264"
            y="143"
            textAnchor="middle"
            fontSize="11"
            fill="#59665f"
          >
            no AI involved
          </text>

          <path
            d="M264 158 L264 202"
            fill="none"
            stroke="#a9671e"
            strokeWidth="2"
            markerEnd="url(#hiw-safety-arrow)"
          />
          <rect
            x="116"
            y="206"
            width="296"
            height="62"
            rx="4"
            fill="#a9671e"
          />
          <text
            x="264"
            y="232"
            textAnchor="middle"
            fontSize="12.5"
            fontWeight="700"
            fill="#fff"
          >
            &ldquo;This is about me&rdquo; leads to help first
          </text>
          <text
            x="264"
            y="250"
            textAnchor="middle"
            fontSize="11"
            fill="#f7e4ca"
          >
            trusted adults, child helpline, evidence preservation
          </text>

          <line
            x1="350"
            y1="120"
            x2="384"
            y2="120"
            stroke="#738078"
            strokeWidth="2"
            markerEnd="url(#hiw-safety-arrow)"
          />
          <rect
            x="388"
            y="84"
            width="150"
            height="72"
            rx="4"
            fill="#184f3e"
          />
          <text
            x="463"
            y="116"
            textAnchor="middle"
            fontSize="13.5"
            fontWeight="700"
            fill="#fff"
          >
            AI analysis + reply
          </text>
          <text
            x="463"
            y="136"
            textAnchor="middle"
            fontSize="11"
            fill="#bad9c7"
          >
            grounded, citable
          </text>
          <line
            x1="540"
            y1="120"
            x2="574"
            y2="120"
            stroke="#738078"
            strokeWidth="2"
            markerEnd="url(#hiw-safety-arrow)"
          />

          <rect
            x="578"
            y="84"
            width="168"
            height="72"
            rx="4"
            fill="#edf2ec"
            stroke="#4f8664"
            strokeWidth="1.6"
          />
          <text
            x="662"
            y="106"
            textAnchor="middle"
            fontSize="13"
            fontWeight="700"
            fill="#17211c"
          >
            Output guards
          </text>
          <text
            x="662"
            y="124"
            textAnchor="middle"
            fontSize="11"
            fill="#59665f"
          >
            no legal determinations,
          </text>
          <text
            x="662"
            y="139"
            textAnchor="middle"
            fontSize="11"
            fill="#59665f"
          >
            under-13 redaction
          </text>
          <line
            x1="748"
            y1="120"
            x2="782"
            y2="120"
            stroke="#738078"
            strokeWidth="2"
            markerEnd="url(#hiw-safety-arrow)"
          />

          <rect
            x="786"
            y="92"
            width="76"
            height="56"
            rx="4"
            fill="#fff"
            stroke="#d7d8d0"
          />
          <text
            x="824"
            y="125"
            textAnchor="middle"
            fontSize="13"
            fontWeight="700"
            fill="#17211c"
          >
            Reply
          </text>

          <text x="436" y="252" fontSize="11.5" fill="#59665f">
            No prompt failure can switch off the amber or green paths.
          </text>
          <text x="436" y="274" fontSize="11.5" fill="#59665f">
            Both are deterministic code.
          </text>
        </svg>
      </div>
      <figcaption>
        Personal safety signals bypass discourse analysis and route directly to
        human support.
      </figcaption>
    </figure>
  )
}

function Brand() {
  return (
    <a className="brand" href="/" aria-label="Civic Bridge AI home">
      <span className="brand__mark" aria-hidden="true">
        <span />
        <span />
        <span />
      </span>
      <span>Civic Bridge AI</span>
    </a>
  )
}

function HowItWorksPage() {
  return (
    <div className="hiw-page">
      <header className="hiw-topbar">
        <Brand />
        <nav className="hiw-nav" aria-label="How it works sections">
          <a href="#method">Method</a>
          <a href="#roles">Roles</a>
          <a href="#example">Example</a>
          <a href="#teaching">Teaching</a>
          <a href="#evidence">Evidence</a>
          <a href="#safeguards">Safeguards</a>
        </nav>
        <a className="hiw-back-link" href="/">
          Back to overview
        </a>
      </header>

      <main>
        <section className="hiw-hero">
          <div className="hiw-hero__copy">
            <p className="eyebrow">Behind the chatbot</p>
            <h1>How Civic Bridge AI works.</h1>
            <p className="hiw-lead">
              Civic Bridge AI turns a complex hate-speech incident into
              teachable, evidence-grounded guidance: what happened, why it
              blocks dialogue, how to teach through it, and when to connect
              people with human support.
            </p>
            <div className="hiw-actions">
              <a className="button button--primary" href="#method">
                See the method <span aria-hidden="true">&darr;</span>
              </a>
              <a className="button button--secondary" href="/students">
                Open the student chat
              </a>
            </div>
          </div>

          <div className="hiw-pipeline" aria-label="System flow diagram">
            <div className="hiw-pipeline__heading">
              <strong>One conversation, five grounded layers</strong>
              <span>Live pipeline</span>
            </div>
            {pipelineLayers.map((layer, index) => (
              <div className="hiw-pipeline__item" key={layer.title}>
                {index > 0 ? (
                  <span className="hiw-flow-arrow" aria-hidden="true">
                    &darr;
                  </span>
                ) : null}
                <div className={`hiw-node hiw-node--${layer.tone}`}>
                  <strong>{layer.title}</strong>
                  <span>{layer.description}</span>
                </div>
              </div>
            ))}
          </div>
        </section>

        <section className="hiw-section" id="method">
          <div className="hiw-section-heading">
            <p className="eyebrow">Guided reasoning</p>
            <h2>It is not a keyword filter.</h2>
            <p>
              Legal and policy standards ground the answer, semantic-barrier
              theory explains the communicative harm, and pedagogy turns the
              analysis into classroom action.
            </p>
          </div>

          <div className="hiw-card-grid">
            {methodCards.map((card) => (
              <article className="hiw-card" key={card.title}>
                <span className="hiw-tag">{card.tag}</span>
                <h3>{card.title}</h3>
                <p>{card.description}</p>
              </article>
            ))}
          </div>

          <TwoAxisAnalysisPlot />
        </section>

        <section className="hiw-section hiw-section--band" id="roles">
          <div className="hiw-section-heading">
            <p className="eyebrow">Context-aware guidance</p>
            <h2>Roles and age groups shape the conversation.</h2>
            <p>
              A teacher needs practical classroom moves. A student needs a
              thinking partner. A younger learner needs safer wording. The same
              incident is handled differently depending on who is asking.
            </p>
          </div>

          <div className="hiw-role-grid">
            <article className="hiw-role-card">
              <span aria-hidden="true">T</span>
              <div>
                <h3>Teacher guidance</h3>
                <p>
                  Teachers receive direct explanations, classroom options,
                  RFCDC links, and structured choices: understand, teach, or
                  report. The assistant avoids overloading the teacher with a
                  full lesson plan until they ask for depth.
                </p>
              </div>
            </article>
            <article className="hiw-role-card">
              <span aria-hidden="true">S</span>
              <div>
                <h3>Student guidance</h3>
                <p>
                  Students get Socratic support: who is targeted, whose voice
                  is missing, and what the message asks people to feel. If the
                  student appears personally targeted, safety and help-seeking
                  come first.
                </p>
              </div>
            </article>
          </div>

          <div className="hiw-age-grid" aria-label="Age group adaptations">
            {ageGroups.map(([age, description]) => (
              <div key={age}>
                <strong>{age}</strong>
                <span>{description}</span>
              </div>
            ))}
          </div>
        </section>

        <section className="hiw-section" id="example">
          <div className="hiw-section-heading">
            <p className="eyebrow">One incident, two paths</p>
            <h2>The same message creates two different conversations.</h2>
            <p>
              Both users share the comment: &ldquo;They will never change, it
              is in their nature. Anyone who talks to them is a
              traitor.&rdquo; The teacher gets a professional reading and a
              choice of paths. The student gets a thinking partner who asks
              before telling.
            </p>
          </div>

          <div className="hiw-conversation-grid">
            <article className="hiw-conversation">
              <header>
                <strong>Teacher, class age 14-17</strong>
                <span>Didactic flow</span>
              </header>
              <div>
                <p className="hiw-bubble hiw-bubble--user">
                  <span>Teacher</span>
                  A student showed me this comment under a news article:
                  &ldquo;They will never change, it is in their nature. Anyone
                  who talks to them is a traitor.&rdquo; What am I looking at?
                </p>
                <div className="hiw-analysis-note">
                  <strong>Tier 3</strong>
                  <p>
                    Potential hate speech for human review. Rigid opposition
                    and stigma detected. Counter-strategies: superordinate
                    identity and outgroup empathy. Related case: Feret v
                    Belgium.
                  </p>
                </div>
                <p className="hiw-bubble hiw-bubble--assistant">
                  <span>Civic Bridge</span>
                  The comment essentialises a group as unchangeable and shames
                  anyone who engages with them. Would you like to understand
                  it further, teach with it, or report it?
                </p>
                <p className="hiw-bubble hiw-bubble--user">
                  <span>Teacher</span>
                  Teach with it.
                </p>
                <p className="hiw-bubble hiw-bubble--assistant">
                  <span>Civic Bridge</span>
                  Ask students to rewrite the concern without the either-or
                  frame, then compare what changed. Follow with a short
                  role-play about being called a traitor for talking. Both
                  build RFCDC empathy and critical thinking.
                </p>
              </div>
            </article>

            <article className="hiw-conversation">
              <header>
                <strong>Student, age 14-17</strong>
                <span>Socratic flow</span>
              </header>
              <div>
                <p className="hiw-bubble hiw-bubble--user">
                  <span>Student</span>
                  I saw this under a video: &ldquo;They will never change, it
                  is in their nature. Anyone who talks to them is a
                  traitor.&rdquo; Is this hate speech?
                </p>
                <p className="hiw-bubble hiw-bubble--assistant">
                  <span>Civic Bridge</span>
                  Before I give you labels, who is being talked about, and what
                  is the post asking readers to feel about them?
                </p>
                <p className="hiw-bubble hiw-bubble--user">
                  <span>Student</span>
                  It does not even say who. It wants you to feel they are
                  dangerous and that being friendly with them is betrayal.
                </p>
                <p className="hiw-bubble hiw-bubble--assistant">
                  <span>Civic Bridge</span>
                  You found both moves: it treats a whole group as one
                  unchangeable thing, and it punishes anyone who builds a
                  bridge. Those dialogue-blockers are called rigid opposition
                  and stigma. What would you ask the person who wrote it?
                </p>
              </div>
            </article>
          </div>

          <aside className="hiw-triage-note">
            <strong>What if the student is the target?</strong>
            <p>
              If a student says they are being targeted and are scared, the
              analysis does not run. A rule-based screen answers with
              help-seeking first: talk to a trusted adult, use the country
              child helpline, preserve evidence, and return gently if the
              system misread the situation. A scared child does not receive a
              lecture on discourse analysis.
            </p>
          </aside>
        </section>

        <section className="hiw-section hiw-teaching" id="teaching">
          <div className="hiw-section-heading">
            <p className="eyebrow">Dialogue restoration</p>
            <h2>The teaching theory goes beyond classification.</h2>
            <p>
              The goal is to help teachers and students understand how speech
              closes democratic conversation, then practise ways to reopen it.
            </p>
          </div>
          <ol className="hiw-teaching-steps">
            {teachingSteps.map((step) => (
              <li key={step.title}>
                <strong>{step.title}</strong>
                <span>{step.description}</span>
              </li>
            ))}
          </ol>
        </section>

        <section className="hiw-section hiw-section--band">
          <div className="hiw-section-heading">
            <p className="eyebrow">The codebook</p>
            <h2>Seven semantic barriers explain why dialogue breaks.</h2>
            <p>
              Hate speech is not only a set of bad words. It works through
              recognisable mechanisms that shut down dialogue. The codebook is
              grounded in peer-reviewed social psychology and matches each
              mechanism with linguistic markers, examples, and
              counter-strategies.
            </p>
          </div>
          <div className="hiw-barrier-list">
            {barriers.map((barrier, index) => (
              <article key={barrier.title}>
                <span>{String(index + 1).padStart(2, '0')}</span>
                <strong>{barrier.title}</strong>
                <p>{barrier.description}</p>
              </article>
            ))}
          </div>
        </section>

        <section className="hiw-section" id="evidence">
          <div className="hiw-section-heading">
            <p className="eyebrow">Auditable evidence</p>
            <h2>External sources ground every answer.</h2>
            <p>
              Civic Bridge AI retrieves and cites external sources rather than
              asking users to trust a black-box answer. The evidence layer
              combines retrieval-augmented generation, curated norms, ECHR
              cases, and country registries.
            </p>
          </div>
          <div className="hiw-source-grid">
            {evidenceSources.map((source) => (
              <article key={source.title}>
                <strong>{source.title}</strong>
                <p>{source.description}</p>
              </article>
            ))}
          </div>
          <div className="hiw-number-grid" aria-label="System evidence figures">
            {evidenceNumbers.map(([value, description]) => (
              <div key={value}>
                <strong>{value}</strong>
                <span>{description}</span>
              </div>
            ))}
          </div>
        </section>

        <section className="hiw-section hiw-aggregate">
          <div>
            <p className="eyebrow">Privacy-preserving signals</p>
            <h2>From single incidents to the aggregate picture.</h2>
          </div>
          <div>
            <p>
              Every analysis contributes categorical signals such as tier,
              mechanisms, and themes to an aggregate view. Never the text,
              never an identity.
            </p>
            <p>
              Public institutions see where education is the right tool, where
              reporting channels need strengthening, and which
              dialogue-blocking mechanisms dominate local discourse. They read
              the aggregate picture, never individuals.
            </p>
            <a className="button button--primary" href="/public-institutions">
              Open the institution dashboard
            </a>
          </div>
        </section>

        <section className="hiw-section">
          <div className="hiw-section-heading">
            <p className="eyebrow">Behind the interface</p>
            <h2>What the chat window does not show.</h2>
            <p>
              The visible chatbot is the last step. Behind it is a set of
              constraints that keep the answer grounded, age-aware,
              educational, and safe.
            </p>
          </div>
          <div className="hiw-card-grid">
            {hiddenLayers.map((layer) => (
              <article className="hiw-card" key={layer.title}>
                <h3>{layer.title}</h3>
                <p>{layer.description}</p>
              </article>
            ))}
          </div>
        </section>

        <section
          className="hiw-section hiw-section--dark"
          id="safeguards"
        >
          <div className="hiw-section-heading">
            <p className="eyebrow">Enforced boundaries</p>
            <h2>Safeguards are part of the product, not fine print.</h2>
            <p>
              The system is deliberately constrained because the domain
              involves children, schools, discrimination, and possible legal
              escalation.
            </p>
          </div>

          <SafetyPipelinePlot />

          <div className="hiw-safeguard-grid">
            {safeguards.map((safeguard) => (
              <article key={safeguard.title}>
                <strong>{safeguard.title}</strong>
                <p>{safeguard.description}</p>
              </article>
            ))}
          </div>
        </section>

        <section className="hiw-cta">
          <p className="eyebrow">Standards, classrooms, action</p>
          <h2>A bridge from analysis to democratic learning.</h2>
          <p>
            Civic Bridge AI makes the reasoning behind hate-speech guidance
            visible: standards for legitimacy, semantic barriers for
            understanding, pedagogy for repair, and country contacts for
            real-world response.
          </p>
          <div className="hiw-actions">
            <a className="button button--primary" href="/students">
              Try the student chat
            </a>
            <a className="button button--secondary" href="/educators">
              Open the educator workspace
            </a>
          </div>
        </section>
      </main>

      <footer className="hiw-footer">
        <Brand />
        <p>
          Civic Bridge AI is a human-review aid for education and civic
          response. It does not provide legal advice or make legal
          determinations.
        </p>
      </footer>
    </div>
  )
}

export default HowItWorksPage
