import { useState, useEffect, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import { useAuth } from '../contexts/AuthContext'
import { API_BASE } from '../api/config'
import { hasPremiumAccess } from '../config/entitlements'
import PaywallCard from './PaywallCard'
import SectionJumpNav from './SectionJumpNav'
import AskChart from './AskChart'

// icon/style metadata per section key — content ordering now comes from
// SECTION_GROUPS below, grouped into the report's information architecture.
const SECTION_META = {
  career_destiny_brief: { icon: '✨', style: 'gold'     },
  natural_strengths:    { icon: '💪', style: 'gradient' },
  best_career_path:         { icon: '🎯', style: 'verdict'  },
  job_vs_business_verdict:  { icon: '⚖️',  style: 'verdict'  },
  peak_career_window:   { icon: '⏳', style: 'plain'    },
  current_phase:        { icon: '🚀', style: 'plain'    },
  career_growth:        { icon: '📈', style: 'gradient' },
  career_money:         { icon: '💰', style: 'tinted'   },
  career_challenges:    { icon: '🧭', style: 'plain'    },
  academic_path:        { icon: '🎓', style: 'tinted'   },
  gemstone_recommendation:  { icon: '💎', style: 'gem'  },
  rudraksha_recommendation: { icon: '🔴', style: 'tinted' },
  empowering_remedies:      { icon: '🙏', style: 'plain'  },
  closing_blessing:     { icon: '🌟', style: 'gradient' },
  // Legacy keys — only ever populated on older saved reports, not generated
  // by the current prompt; kept so nothing from a previously saved report
  // silently disappears.
  lagna_personality:    { icon: '🌟', style: 'gradient' },
  job_vs_business:      { icon: '⚖️',  style: 'verdict'  },
  tenth_house_d1:       { icon: '🏛️',  style: 'plain'   },
  d10_analysis:         { icon: '📊',  style: 'plain'   },
  amatyakaraka:         { icon: '💫',  style: 'tinted'  },
  career_fields:        { icon: '💼',  style: 'plain'   },
  student_streams:      { icon: '🎓',  style: 'tinted'  },
  yogas_combinations:   { icon: '✨',  style: 'plain'   },
  dasha_predictions:    { icon: '⏳',  style: 'plain'   },
  transit_impact:       { icon: '🌍',  style: 'tinted'  },
  remedies:             { icon: '🙏',  style: 'plain'   },
  conclusion:           { icon: '🔮',  style: 'gradient'},
}

// Which section keys render inside each new-IA anchor, in order.
const SECTION_GROUPS = {
  currentCareer:    ['job_vs_business_verdict', 'current_phase'],
  careerDna:        ['natural_strengths'],
  careerDirections: ['best_career_path', 'academic_path'],
  growth:           ['career_growth'],
  money:            ['career_money'],
  challenges:       ['career_challenges'],
  timing:           ['peak_career_window', 'gemstone_recommendation', 'rudraksha_recommendation', 'empowering_remedies', 'closing_blessing'],
  // Not part of the current prompt's output — only ever populated on an
  // older saved report. No dedicated jump-nav stop; shown at the end.
  legacy: ['lagna_personality', 'job_vs_business', 'tenth_house_d1', 'd10_analysis', 'amatyakaraka', 'career_fields', 'student_streams', 'yogas_combinations', 'dasha_predictions', 'transit_impact', 'remedies', 'conclusion'],
}

const JUMP_SECTIONS = [
  { id: 'career-overview',    label: 'Overview' },
  { id: 'career-current',     label: 'Current Career' },
  { id: 'career-dna',         label: 'Career DNA' },
  { id: 'career-directions',  label: 'Directions' },
  { id: 'career-growth',      label: 'Growth' },
  { id: 'career-money',       label: 'Money' },
  { id: 'career-challenges',  label: 'Challenges' },
  { id: 'career-timing',      label: 'Timing' },
  { id: 'career-roadmap',     label: 'Roadmap' },
  { id: 'career-evidence',    label: 'Evidence' },
  { id: 'career-ask-ai',      label: 'Ask AI' },
]

// Which anchors to front-load, per stated concern (from CAREER_CONCERNS
// below) — dynamic module ordering. Overview always stays first regardless.
const CONCERN_PRIORITY = {
  'Am I in the right career?':                        ['career-dna', 'career-directions', 'career-current'],
  'How far can I progress?':                           ['career-growth', 'career-current', 'career-timing'],
  'When will my career improve?':                      ['career-timing', 'career-roadmap'],
  'Why do I feel stuck?':                               ['career-current', 'career-challenges', 'career-timing'],
  'Will I get promoted?':                               ['career-growth', 'career-current', 'career-timing'],
  'Should I change my job?':                            ['career-current', 'career-directions', 'career-challenges'],
  'Should I change my profession?':                     ['career-directions', 'career-dna', 'career-current'],
  'Should I move into management or leadership?':       ['career-growth', 'career-dna'],
  'Should I start a business?':                         ['career-current', 'career-money', 'career-timing'],
  'Will I have strong financial growth?':               ['career-money', 'career-timing'],
  'Are foreign opportunities or relocation favorable?': ['career-directions', 'career-timing'],
  'What is the next major turning point in my career?': ['career-timing', 'career-roadmap'],
}

function reorderSections(careerContext) {
  const concern  = careerContext?.career_concerns?.[0]
  const priority = CONCERN_PRIORITY[concern] || []
  const [overview, ...rest] = JUMP_SECTIONS
  const prioritized = priority.map(id => rest.find(s => s.id === id)).filter(Boolean)
  const remaining   = rest.filter(s => !priority.includes(s.id))
  return [overview, ...prioritized, ...remaining]
}

const EFFORT_COLOR = {
  low:    'text-emerald-600 bg-emerald-50',
  medium: 'text-primary-dark bg-primary-light',
  high:   'text-vermillion bg-vermillion-light',
}

const CAREER_CONTEXT_KEY = 'starjyotish_career_context'

const CAREER_STAGES = [
  { value: 'student',     label: 'Student / Pre-career' },
  { value: '0_3_years',   label: '0–3 years experience' },
  { value: 'experienced', label: 'Experienced professional' },
  { value: 'senior',      label: 'Senior / Executive' },
  { value: 'entrepreneur',label: 'Entrepreneur / Business owner' },
  { value: 'transition',  label: 'Career transition' },
  { value: 'job_seeker',  label: 'Job seeker / Career break' },
]

const CAREER_CONCERNS = [
  'Am I in the right career?',
  'How far can I progress?',
  'When will my career improve?',
  'Why do I feel stuck?',
  'Will I get promoted?',
  'Should I change my job?',
  'Should I change my profession?',
  'Should I move into management or leadership?',
  'Should I start a business?',
  'Will I have strong financial growth?',
  'Are foreign opportunities or relocation favorable?',
  'What is the next major turning point in my career?',
]

const MAX_CONCERNS = 3

function loadCareerContext() {
  try {
    const raw = localStorage.getItem(CAREER_CONTEXT_KEY)
    return raw ? JSON.parse(raw) : null
  } catch {
    return null
  }
}

function saveCareerContext(ctx) {
  try {
    localStorage.setItem(CAREER_CONTEXT_KEY, JSON.stringify(ctx))
  } catch {
    // Best-effort only — localStorage can throw in private browsing or when full.
  }
}

function CareerContextForm({ initial, onDone }) {
  const [careerStage, setCareerStage] = useState(initial?.career_stage || '')
  const [profession, setProfession]   = useState(initial?.current_profession || '')
  const [concerns, setConcerns]       = useState(initial?.career_concerns || [])

  function toggleConcern(c) {
    setConcerns(prev => {
      if (prev.includes(c)) return prev.filter(x => x !== c)
      if (prev.length >= MAX_CONCERNS) return prev
      return [...prev, c]
    })
  }

  function submit() {
    onDone({
      career_stage: careerStage || undefined,
      current_profession: profession.trim() || undefined,
      career_concerns: concerns.length ? concerns : undefined,
    })
  }

  return (
    <div className="max-w-2xl mx-auto py-6 px-2 space-y-6">
      <div className="text-center">
        <div className="text-4xl mb-3">💼</div>
        <h2 className="text-xl font-bold text-ink mb-1">Tell us a little about your career</h2>
        <p className="text-ink-muted text-sm">
          Optional — this helps the report speak to your actual situation instead of a generic one.
        </p>
      </div>

      <div>
        <p className="text-sm font-semibold text-ink mb-2">Where are you in your career?</p>
        <div className="flex flex-wrap gap-2">
          {CAREER_STAGES.map(s => (
            <button key={s.value} type="button" onClick={() => setCareerStage(s.value)}
              className={`px-3 py-1.5 rounded-full text-sm border transition ${
                careerStage === s.value
                  ? 'bg-primary text-night border-primary font-semibold'
                  : 'bg-parchment-card text-ink-muted border-line hover:border-primary/50'
              }`}>
              {s.label}
            </button>
          ))}
        </div>
      </div>

      <div>
        <p className="text-sm font-semibold text-ink mb-2">What's your current profession?</p>
        <input
          type="text"
          value={profession}
          onChange={e => setProfession(e.target.value)}
          placeholder="e.g. Software Engineer, Teacher, Business Owner"
          className="w-full border border-line rounded-lg px-3 py-2 bg-parchment text-ink text-sm focus:outline-none focus:ring-2 focus:ring-primary"
        />
      </div>

      <div>
        <p className="text-sm font-semibold text-ink mb-2">
          What do you want to know? <span className="text-ink-faint font-normal">(pick up to {MAX_CONCERNS})</span>
        </p>
        <div className="flex flex-wrap gap-2">
          {CAREER_CONCERNS.map(c => (
            <button key={c} type="button" onClick={() => toggleConcern(c)}
              disabled={!concerns.includes(c) && concerns.length >= MAX_CONCERNS}
              className={`px-3 py-1.5 rounded-full text-sm border transition disabled:opacity-40 ${
                concerns.includes(c)
                  ? 'bg-primary text-night border-primary font-semibold'
                  : 'bg-parchment-card text-ink-muted border-line hover:border-primary/50'
              }`}>
              {c}
            </button>
          ))}
        </div>
      </div>

      <div className="flex items-center justify-between pt-2">
        <button type="button" onClick={() => onDone(null)}
          className="text-sm text-ink-muted hover:text-ink transition">
          Skip for now
        </button>
        <button type="button" onClick={submit}
          className="px-6 py-2.5 bg-primary hover:bg-primary-dark text-night font-semibold rounded-full transition shadow-md">
          Continue
        </button>
      </div>
    </div>
  )
}

function SectionContent({ content, light = false }) {
  if (!content) return <span className="text-ink-faint italic">—</span>
  const bullets = content
    .split('\n')
    .map(l => l.replace(/^[-•]\s*/, '').trim())
    .filter(Boolean)
  const cls = light ? 'text-primary-light' : 'text-ink'
  if (bullets.length <= 1)
    return <p className={`text-sm leading-relaxed ${cls}`}>{content}</p>
  return (
    <ul className="space-y-2">
      {bullets.map((b, i) => (
        <li key={i} className={`flex gap-2 text-sm leading-relaxed ${cls}`}>
          <span className="mt-1.5 shrink-0 w-1.5 h-1.5 rounded-full bg-current opacity-50" />
          <span>{b}</span>
        </li>
      ))}
    </ul>
  )
}

function SectionCard({ icon, section, style }) {
  if (!section?.content) return null

  if (style === 'gold') return (
    <div className="bg-parchment-card rounded-2xl shadow-md overflow-hidden border border-primary/30">
      <div className="bg-gradient-to-r from-primary to-primary-dark px-5 py-3.5 flex items-center gap-2">
        <span className="text-2xl">{icon}</span>
        <h3 className="font-extrabold text-night text-lg leading-tight">{section.title}</h3>
      </div>
      <div className="px-5 py-4">
        <SectionContent content={section.content} />
      </div>
    </div>
  )

  if (style === 'gem') return (
    <div className="bg-parchment-card rounded-2xl shadow-md overflow-hidden border border-mauve/30">
      <div className="bg-gradient-to-r from-sage to-mauve px-5 py-3.5 flex items-center gap-2">
        <span className="text-2xl">{icon}</span>
        <h3 className="font-extrabold text-white text-lg leading-tight">{section.title}</h3>
      </div>
      <div className="px-5 py-4">
        <SectionContent content={section.content} />
      </div>
    </div>
  )

  if (style === 'gradient') return (
    <div className="bg-parchment-card rounded-xl shadow-sm overflow-hidden border border-primary/30">
      <div className="bg-night px-5 py-3 flex items-center gap-2">
        <span className="text-xl">{icon}</span>
        <h3 className="font-bold text-primary-light text-base">{section.title}</h3>
      </div>
      <div className="px-5 py-4">
        <SectionContent content={section.content} />
      </div>
    </div>
  )

  if (style === 'verdict') return (
    <div className="bg-parchment-card rounded-xl p-5 shadow-sm border-l-4 border-vermillion border border-vermillion/20">
      <div className="flex items-center gap-2 mb-3">
        <span className="text-xl">{icon}</span>
        <h3 className="font-bold text-vermillion text-base">{section.title}</h3>
      </div>
      <SectionContent content={section.content} />
    </div>
  )

  if (style === 'tinted') return (
    <div className="bg-primary-light rounded-xl p-5 shadow-sm border border-primary/30">
      <div className="flex items-center gap-2 mb-3">
        <span className="text-xl">{icon}</span>
        <h3 className="font-bold text-primary-dark text-base">{section.title}</h3>
      </div>
      <SectionContent content={section.content} />
    </div>
  )

  return (
    <div className="bg-parchment-card rounded-xl p-5 shadow-sm border border-line">
      <div className="flex items-center gap-2 mb-3">
        <span className="text-xl">{icon}</span>
        <h3 className="font-bold text-primary text-base">{section.title}</h3>
      </div>
      <SectionContent content={section.content} />
    </div>
  )
}

function CareerOptionCard({ opt }) {
  const [open, setOpen] = useState(false)
  const effortCls = EFFORT_COLOR[opt.effort_required] ?? EFFORT_COLOR.medium
  return (
    <div className="bg-parchment-card rounded-xl border border-line shadow-sm overflow-hidden">
      <button
        onClick={() => setOpen(o => !o)}
        className="w-full text-left p-4 flex items-start gap-3"
      >
        <div className={`shrink-0 w-8 h-8 rounded-full text-night text-sm font-extrabold flex items-center justify-center ${opt.rank === 1 ? 'bg-primary-dark' : 'bg-primary'}`}>
          {opt.rank === 1 ? '★' : opt.rank}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-bold text-ink text-sm">{opt.title}</span>
            <span className="text-xs text-ink-muted bg-night/10 px-2 py-0.5 rounded-full">{opt.field}</span>
            <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${effortCls}`}>
              {opt.effort_required} effort
            </span>
          </div>
          {opt.timeline && (
            <p className="text-xs text-ink-faint mt-0.5">{opt.timeline}</p>
          )}
        </div>
        <span className={`text-ink-faint text-xs mt-1 shrink-0 transition-transform ${open ? 'rotate-180' : ''}`}>▼</span>
      </button>

      {open && (
        <div className="px-4 pb-4 pt-0 border-t border-line space-y-3">
          {opt.reason && (
            <div>
              <p className="text-xs font-semibold text-primary-dark uppercase tracking-wide mb-1">Why this career?</p>
              <p className="text-xs text-ink-muted leading-relaxed">{opt.reason}</p>
            </div>
          )}
          <div className="flex flex-wrap gap-4">
            {opt.key_planets?.length > 0 && (
              <div>
                <p className="text-xs font-semibold text-ink-muted mb-1">Key Planets</p>
                <div className="flex gap-1 flex-wrap">
                  {opt.key_planets.map(p => (
                    <span key={p} className="text-xs bg-primary-light text-primary-dark px-2 py-0.5 rounded-full">{p}</span>
                  ))}
                </div>
              </div>
            )}
            {opt.favorable_dasha && (
              <div>
                <p className="text-xs font-semibold text-ink-muted mb-1">Best Dasha</p>
                <span className="text-xs bg-primary-light text-primary-dark px-2 py-0.5 rounded-full">{opt.favorable_dasha}</span>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

function AstrologicalEvidenceCard({ evidence }) {
  const [showAllPlanets, setShowAllPlanets] = useState(false)
  if (!evidence) return null
  const rows = [
    ['Lagna (Ascendant)', evidence.lagna],
    ['Moon Sign', evidence.moon_sign],
    ['Sun Sign', evidence.sun_sign],
    ['Amatyakaraka (career soul planet)', `${evidence.amatyakaraka} — ${evidence.amatyakaraka_placement}`],
    ['10th Lord', `${evidence.tenth_lord} — ${evidence.tenth_lord_placement}`],
    ['D10 Lagna (Dasamsa)', evidence.d10_lagna],
    ['D10 Job Score', evidence.d10_job_score],
    ['D10 Business Score', evidence.d10_business_score],
    ['Current Mahadasha', `${evidence.current_mahadasha} (until ${evidence.current_mahadasha_end})`],
    ['Current Antardasha', evidence.current_antardasha],
  ]
  return (
    <div className="bg-parchment-card rounded-xl p-5 shadow-sm border border-line">
      <div className="flex items-center gap-2 mb-3">
        <span className="text-xl">🔬</span>
        <h3 className="font-bold text-primary text-base">The Astrology Behind This Report</h3>
      </div>
      <div className="divide-y divide-line">
        {rows.map(([label, value]) => (
          <div key={label} className="flex justify-between items-center gap-4 py-2 text-sm">
            <span className="text-ink-muted">{label}</span>
            <span className="text-ink font-medium text-right">{value}</span>
          </div>
        ))}
      </div>
      {evidence.all_planets?.length > 0 && (
        <div className="mt-3 pt-3 border-t border-line">
          <button onClick={() => setShowAllPlanets(o => !o)}
            className="text-xs font-semibold text-primary-dark hover:underline">
            {showAllPlanets ? 'Hide' : 'See'} all planets {showAllPlanets ? '▲' : '▼'}
          </button>
          {showAllPlanets && (
            <div className="divide-y divide-line mt-2">
              {evidence.all_planets.map(p => (
                <div key={p.name} className="flex justify-between items-center gap-4 py-1.5 text-xs">
                  <span className="text-ink-muted">{p.name}{p.retrograde ? ' (R)' : ''}</span>
                  <span className="text-ink font-medium text-right">{p.sign} · H{p.house} · {p.dignity}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function CareerAlignmentBadge({ alignment }) {
  if (!alignment) return null
  const COLOR = {
    'Strong Alignment':        'bg-emerald-50 text-emerald-700 border-emerald-200',
    'Partial Alignment':       'bg-primary-light text-primary-dark border-primary/30',
    'Underutilized Potential': 'bg-mauve/10 text-mauve border-mauve/30',
  }
  const cls = COLOR[alignment.label] || COLOR['Partial Alignment']
  return (
    <div className={`rounded-xl p-4 border ${cls}`}>
      <div className="flex items-center gap-2 mb-1">
        <span className="text-lg">🧭</span>
        <span className="font-bold text-sm">{alignment.label}</span>
      </div>
      <p className="text-sm leading-relaxed opacity-90">{alignment.explanation}</p>
    </div>
  )
}

function CareerRoadmapCard({ roadmap, onAskQuestion }) {
  if (!roadmap) return null
  const horizons = [
    ['Now', roadmap.now],
    ['Next 12 Months', roadmap.next_12_months],
    ['1–3 Years', roadmap.years_1_to_3],
    ['3–5 Years', roadmap.years_3_to_5],
  ].filter(([, text]) => text)

  return (
    <div className="space-y-4">
      {horizons.length > 0 && (
        <div className="bg-parchment-card rounded-xl border border-line shadow-sm overflow-hidden">
          <div className="bg-night px-5 py-3">
            <h3 className="font-bold text-primary-light text-base">🗺️ Your Career Roadmap</h3>
          </div>
          <div className="divide-y divide-line">
            {horizons.map(([label, text]) => (
              <div key={label} className="px-5 py-3">
                <p className="text-xs font-semibold text-primary uppercase tracking-wide mb-1">{label}</p>
                <p className="text-sm text-ink leading-relaxed">{text}</p>
              </div>
            ))}
          </div>
        </div>
      )}
      {(roadmap.top_actions?.length > 0 || roadmap.top_avoid?.length > 0) && (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {roadmap.top_actions?.length > 0 && (
            <div className="bg-emerald-50 rounded-xl p-4 border border-emerald-200">
              <p className="text-xs font-semibold text-emerald-700 uppercase tracking-wide mb-2">Top Actions</p>
              <ul className="space-y-1.5">
                {roadmap.top_actions.map((a, i) => (
                  <li key={i} className="text-sm text-ink flex gap-2">
                    <span className="text-emerald-600 shrink-0">✓</span><span>{a}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
          {roadmap.top_avoid?.length > 0 && (
            <div className="bg-primary-light rounded-xl p-4 border border-primary/30">
              <p className="text-xs font-semibold text-primary-dark uppercase tracking-wide mb-2">Keep In Mind</p>
              <ul className="space-y-1.5">
                {roadmap.top_avoid.map((a, i) => (
                  <li key={i} className="text-sm text-ink flex gap-2">
                    <span className="text-primary-dark shrink-0">•</span><span>{a}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
      {roadmap.next_question && (
        <button onClick={() => onAskQuestion(roadmap.next_question)}
          className="w-full text-left bg-parchment-card rounded-xl p-4 border border-line hover:border-primary/50 transition">
          <p className="text-xs text-ink-faint mb-1">Suggested next question</p>
          <p className="text-sm font-medium text-primary-dark">"{roadmap.next_question}" →</p>
        </button>
      )}
    </div>
  )
}

function ScenarioAnalysisBox({ onSubmit }) {
  const [text, setText] = useState('')
  function submit() {
    if (!text.trim()) return
    onSubmit(text.trim())
    setText('')
  }
  return (
    <div className="bg-parchment-card rounded-xl p-4 border border-mauve/30 space-y-3">
      <div>
        <p className="font-bold text-ink text-sm mb-1">🔍 Compare a Decision</p>
        <p className="text-xs text-ink-muted">
          Describe a real decision you're weighing — two job offers, a relocation, switching industries.
          Submitting starts a fresh, focused conversation below.
        </p>
      </div>
      <textarea
        value={text}
        onChange={e => setText(e.target.value)}
        placeholder="e.g. I have two offers: a startup in Bangalore vs. a stable corporate role in Delhi..."
        rows={3}
        className="w-full border border-line rounded-lg px-3 py-2 bg-parchment text-ink text-sm focus:outline-none focus:ring-2 focus:ring-primary resize-none"
      />
      <button onClick={submit} disabled={!text.trim()}
        className="px-5 py-2 bg-primary hover:bg-primary-dark disabled:bg-night/10 disabled:text-ink-faint text-night font-semibold rounded-full text-sm transition">
        Compare →
      </button>
    </div>
  )
}

function buildAskSeedQuestion(careerContext) {
  const concern = careerContext?.career_concerns?.[0]
  return concern || 'What should I focus on in my career right now?'
}

export default function CareerReportTab({ input, onOpenRajyogas }) {
  const { t, i18n } = useTranslation()
  const { isAuthenticated } = useAuth()
  const [status, setStatus] = useState('idle')
  const [report, setReport] = useState(null)
  const [errorMsg, setErrorMsg] = useState('')

  // Career context (stage/profession/concerns) — captured lazily, once, and
  // skippable; see CareerContextForm above. null until a choice (fill or
  // skip) has been made, which also gates the auto-reveal effect below so
  // signed-in users see this step before the report starts generating.
  const [careerContext, setCareerContext] = useState(loadCareerContext)
  const [showContextForm, setShowContextForm] = useState(() => loadCareerContext() === null)
  // Anonymous visitors only see the context form after opting in via the
  // "Generate Career Report" CTA — signed-in users are already past that
  // opt-in moment just by opening the tab, matching the existing pattern.
  const [wantsReport, setWantsReport] = useState(isAuthenticated)

  // Depth tier — 'full' is the blueprint's own stated default; Quick View
  // and Deep Analysis are alternate toggles, not the initial state.
  const [depth, setDepth] = useState('full')
  // Ask Career AI seeding: null uses the default career-concern seed.
  // Set by the roadmap's "ask this" affordance and by Scenario Analysis —
  // askNonce forces AskChart to remount (via its key prop) so a new seed
  // actually gets sent, since AskChart only auto-sends on mount.
  const [askSeed, setAskSeed] = useState(null)
  const [askNonce, setAskNonce] = useState(0)

  function askQuestion(question) {
    setAskSeed(question)
    setAskNonce(n => n + 1)
    setTimeout(() => document.getElementById('career-ask-ai')?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 50)
  }

  function handleScenarioSubmit(scenarioText) {
    askQuestion(
      `I'm weighing a career decision: ${scenarioText}. Based on my chart, timing, and career profile, ` +
      `compare the options and give me astrological guidance (not a guaranteed prediction) — what does my ` +
      `chart favor and why, and what timing considerations matter?`
    )
  }

  // Auto-reveal for signed-in visitors — see the matching effect and its
  // comment in ChartReading.jsx for the reasoning. Declared before the
  // hasPremiumAccess() early return below: hooks can't follow a
  // conditional return, so this fires on every render regardless, but the
  // effect body itself still only ever calls generate() once someone's
  // actually entitled to see this report (status starts/stays 'idle'
  // for anyone who never gets past the paywall, since generate() is
  // never reachable for them either way) and once the career-context step
  // has been resolved (filled or skipped).
  const autoRevealedRef = useRef(false)
  useEffect(() => {
    if (isAuthenticated && hasPremiumAccess() && !showContextForm && status === 'idle' && !autoRevealedRef.current) {
      autoRevealedRef.current = true
      generate()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isAuthenticated, showContextForm])

  // Resolving the context step (initial fill/skip, or a later edit) always
  // (re)generates directly — setting the ref first stops the effect above
  // from also firing when its showContextForm dependency changes.
  function handleContextDone(ctx) {
    const resolved = ctx || {}
    saveCareerContext(resolved)
    setCareerContext(resolved)
    setShowContextForm(false)
    autoRevealedRef.current = true
    generate(resolved)
  }

  if (!hasPremiumAccess()) {
    return (
      <PaywallCard
        icon="💼"
        title="Your Full Career Report"
        body="Your exact career field, whether your chart favors a job or business, your peak career window, and the precise activation protocol for every Raj Yoga in your chart — gemstone, mantra, timing, and ritual, calibrated to you."
        bullets={[
          'Your best career options, ranked for your specific chart',
          'Activation protocol for every Raj Yoga you carry',
          'Delivered as a report you can keep and revisit',
        ]}
      />
    )
  }

  if (showContextForm && wantsReport) {
    return <CareerContextForm initial={careerContext} onDone={handleContextDone} />
  }

  // ctxOverride avoids a stale-closure read of the `careerContext` state
  // when called right after handleContextDone resolves it in the same tick.
  async function generate(ctxOverride) {
    const ctx = ctxOverride !== undefined ? ctxOverride : careerContext
    setStatus('loading')
    setReport(null)
    setErrorMsg('')
    const language = i18n.language?.startsWith('hi') ? 'hi' : 'en'
    try {
      const resp = await fetch(`${API_BASE}/api/career-report`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          date: input.date, time: input.time, place: input.place, language,
          career_stage: ctx?.career_stage,
          current_profession: ctx?.current_profession,
          career_concerns: ctx?.career_concerns,
        }),
      })
      if (!resp.ok) {
        const err = await resp.json().catch(() => ({}))
        throw new Error(err.detail ?? 'Career analysis failed. Please try again.')
      }
      setReport(await resp.json())
      setStatus('done')
    } catch (e) {
      setErrorMsg(e.message || 'Something went wrong. Please try again.')
      setStatus('error')
    }
  }

  if (status === 'idle' && !isAuthenticated) return (
    <div className="flex flex-col items-center justify-center py-16 px-4 text-center">
      <div className="text-5xl mb-4">💼</div>
      <h2 className="text-xl font-bold text-ink mb-2">Vedic Career Report</h2>
      <p className="text-ink-muted text-sm mb-6 max-w-sm">
        Personalized career destiny reading using D1 + D10 charts, Amatyakaraka, career yogas,
        future dasha timing, and your top career paths — powered by your Vedic astrology skill files.
      </p>
      <button
        onClick={() => (showContextForm ? setWantsReport(true) : generate())}
        className="px-8 py-3 bg-primary hover:bg-primary-dark text-night font-semibold rounded-full transition shadow-md"
      >
        Generate Career Report
      </button>
      <p className="text-xs text-ink-faint mt-3">{t('reading_powered_by_generic')} · takes ~20 seconds</p>
    </div>
  )

  // Also covers the one render where an authenticated visitor is still
  // technically 'idle' before the auto-reveal effect above fires.
  if (status === 'loading' || (status === 'idle' && isAuthenticated)) return (
    <div className="flex flex-col items-center justify-center py-16 px-4 text-center">
      <div className="text-4xl mb-4 animate-spin">⏳</div>
      <p className="text-primary-dark font-semibold">Reading your career destiny…</p>
      <p className="text-xs text-ink-faint mt-1">D1 + D10 · Amatyakaraka · Yogas · Future Dashas · Career Paths</p>
      <div className="mt-5 w-52 h-1.5 bg-night/10 rounded-full overflow-hidden">
        <div className="h-full bg-primary rounded-full animate-pulse w-3/4" />
      </div>
    </div>
  )

  if (status === 'error') return (
    <div className="flex flex-col items-center justify-center py-16 px-4 text-center">
      <div className="text-4xl mb-4">⚠️</div>
      <p className="text-vermillion font-medium mb-4">{errorMsg}</p>
      <button
        onClick={() => setStatus('idle')}
        className="px-6 py-2 bg-primary hover:bg-primary-dark text-night rounded-full text-sm transition"
      >
        Try Again
      </button>
    </div>
  )

  const hasOptions = report?.career_options?.length > 0
  const hasLegacy  = SECTION_GROUPS.legacy.some(key => report[key]?.content)

  function renderKeys(keys) {
    return keys.map(key => {
      const section = report[key]
      if (!section?.content) return null
      const meta = SECTION_META[key] || { icon: '✨', style: 'plain' }
      return <SectionCard key={key} icon={meta.icon} section={section} style={meta.style} />
    })
  }

  const depthToggle = (
    <div className="flex gap-1 bg-night/5 rounded-full p-1">
      {[['quick', 'Quick', 'Quick View'], ['full', 'Full', 'Full Report'], ['deep', 'Deep', 'Deep Analysis']].map(([key, short, full]) => (
        <button key={key} onClick={() => setDepth(key)}
          className={`flex-1 px-2 sm:px-3 py-1.5 rounded-full text-xs font-medium transition whitespace-nowrap ${
            depth === key ? 'bg-primary text-night' : 'text-ink-muted hover:text-ink'
          }`}>
          <span className="sm:hidden">{short}</span>
          <span className="hidden sm:inline">{full}</span>
        </button>
      ))}
    </div>
  )

  const footer = (
    <>
      <div className="text-center mt-6 pb-2 space-x-4">
        <button
          onClick={() => setStatus('idle')}
          className="text-sm text-primary hover:text-primary-dark transition font-medium"
        >
          ↺ Regenerate Report
        </button>
        <button
          onClick={() => setShowContextForm(true)}
          className="text-sm text-ink-muted hover:text-ink transition"
        >
          Edit your career context
        </button>
      </div>

      {/* ── DISCLAIMER ───────────────────────────────────────────────────── */}
      {report?.llm_provider && (
        <p className="text-center text-[11px] text-ink-faint pb-1">
          {t('reading_powered_by', { provider: report.llm_provider })}
        </p>
      )}
      <p className="text-center text-[11px] text-ink-faint leading-relaxed px-4 pb-4">
        {t('disclaimer')}
      </p>
    </>
  )

  // ── QUICK VIEW ─────────────────────────────────────────────────────────────
  // Scannable in 3-5 minutes, per the blueprint: snapshot + current phase +
  // peak window + a way to jump into the full report. No jump-nav here.
  if (depth === 'quick') return (
    <div className="max-w-2xl mx-auto py-2 space-y-4">
      {depthToggle}
      {renderKeys(['career_destiny_brief'])}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {report.current_phase?.content && (
          <div className="bg-parchment-card rounded-xl p-4 border border-line">
            <p className="text-xs font-semibold text-primary uppercase tracking-wide mb-1">Current Phase</p>
            <p className="text-sm text-ink line-clamp-4">{report.current_phase.content}</p>
          </div>
        )}
        {report.peak_career_window?.content && (
          <div className="bg-parchment-card rounded-xl p-4 border border-line">
            <p className="text-xs font-semibold text-primary uppercase tracking-wide mb-1">Peak Window</p>
            <p className="text-sm text-ink line-clamp-4">{report.peak_career_window.content}</p>
          </div>
        )}
      </div>
      <button onClick={() => setDepth('full')}
        className="w-full py-3 bg-primary hover:bg-primary-dark text-night font-semibold rounded-full transition shadow-md">
        See Full Report →
      </button>
      {footer}
    </div>
  )

  // ── FULL REPORT / DEEP ANALYSIS ──────────────────────────────────────────
  const rajYogaTeaser = report?.active_yogas?.length > 0 && (
    <div className="bg-parchment-card rounded-xl p-5 shadow-sm border border-primary/30">
      <div className="flex items-center gap-2 mb-2">
        <span className="text-xl">👑</span>
        <h3 className="font-bold text-primary text-base">
          You have {report.active_yogas.length} active Raj Yoga{report.active_yogas.length > 1 ? 's' : ''}
        </h3>
      </div>
      <p className="text-ink text-sm leading-relaxed mb-3">
        Including {report.active_yogas.slice(0, 2).map(y => y.name).join(' and ')}
        {report.active_yogas.length > 2 ? ', and more' : ''} — see the full breakdown of what each one means for you.
      </p>
      <button onClick={onOpenRajyogas}
        className="text-sm font-semibold text-primary-dark hover:underline">
        See my Raj Yogas →
      </button>
    </div>
  )

  const careerOptionsBlock = hasOptions && (
    <div className="bg-parchment-card rounded-xl border border-line shadow-sm p-5">
      <div className="flex items-center gap-2 mb-4">
        <span className="text-xl">🎯</span>
        <h3 className="font-bold text-ink text-base">Your Best Career Options</h3>
        <span className="text-xs text-ink-faint ml-1">· tap to expand</span>
      </div>
      <div className="space-y-2">
        {report.career_options.map(opt => (
          <CareerOptionCard key={opt.rank} opt={opt} />
        ))}
      </div>
    </div>
  )

  const SECTION_RENDERERS = {
    'career-overview':   () => renderKeys(['career_destiny_brief']),
    'career-current':    () => <>{renderKeys(SECTION_GROUPS.currentCareer)}<CareerAlignmentBadge alignment={report.career_alignment} /></>,
    'career-dna':        () => <>{renderKeys(SECTION_GROUPS.careerDna)}{rajYogaTeaser}</>,
    'career-directions': () => <>{careerOptionsBlock}{renderKeys(SECTION_GROUPS.careerDirections)}</>,
    'career-growth':     () => renderKeys(SECTION_GROUPS.growth),
    'career-money':      () => renderKeys(SECTION_GROUPS.money),
    'career-challenges': () => renderKeys(SECTION_GROUPS.challenges),
    'career-timing':     () => <>{renderKeys(SECTION_GROUPS.timing)}{hasLegacy && renderKeys(SECTION_GROUPS.legacy)}</>,
    'career-roadmap':    () => <CareerRoadmapCard roadmap={report.career_roadmap} onAskQuestion={askQuestion} />,
    'career-evidence':   () => <AstrologicalEvidenceCard evidence={report?.astrological_evidence} />,
    'career-ask-ai':     () => (
      <>
        {depth === 'deep' && <ScenarioAnalysisBox onSubmit={handleScenarioSubmit} />}
        <AskChart key={askNonce} input={input} initialQuestion={askSeed || buildAskSeedQuestion(careerContext)} />
      </>
    ),
  }

  const orderedSections = reorderSections(careerContext)

  return (
    <div className="max-w-2xl mx-auto py-2 space-y-4">

      <div className="sticky top-[100px] z-20 -mx-2 px-2 py-2 bg-parchment/95 backdrop-blur-sm space-y-2">
        {depthToggle}
        <SectionJumpNav sections={orderedSections} />
      </div>

      {orderedSections.map(({ id }) => (
        <section key={id} id={id} className="space-y-4 scroll-mt-40">
          {SECTION_RENDERERS[id]()}
        </section>
      ))}

      {footer}
    </div>
  )
}
