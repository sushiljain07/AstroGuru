import { useState, useEffect, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import { useAuth } from '../contexts/AuthContext'
import { API_BASE } from '../api/config'
import { Button } from './ui'

// Faint kundli wheel SVG watermark
function KundliWheelBg() {
  const spokes = Array.from({ length: 12 }, (_, i) => {
    const a = (i * 30 * Math.PI) / 180
    return {
      x1: 150 + 45 * Math.cos(a), y1: 150 + 45 * Math.sin(a),
      x2: 150 + 140 * Math.cos(a), y2: 150 + 140 * Math.sin(a),
    }
  })
  return (
    <svg width="320" height="320" viewBox="0 0 300 300"
         className="absolute inset-0 m-auto pointer-events-none select-none"
         style={{ opacity: 0.05, color: '#D4AF37' }}>
      <circle cx="150" cy="150" r="140" stroke="currentColor" fill="none" strokeWidth="1" />
      <circle cx="150" cy="150" r="90"  stroke="currentColor" fill="none" strokeWidth="0.8" />
      <circle cx="150" cy="150" r="45"  stroke="currentColor" fill="none" strokeWidth="0.8" />
      {spokes.map((s, i) => (
        <line key={i} x1={s.x1} y1={s.y1} x2={s.x2} y2={s.y2}
              stroke="currentColor" strokeWidth="0.5" />
      ))}
    </svg>
  )
}

// Section display config — ordered as they appear in the prediction
const SECTION_CONFIG = [
  { key: 'identity',       title: 'Your Cosmic Identity',          icon: '🌟' },
  { key: 'strengths',      title: 'Your Career Domain & Strengths',icon: '💪' },
  { key: 'currentperiod',  title: 'Your Current Life Period',       icon: '⏳' },
  { key: 'prediction',     title: 'Your Next 2–3 Years',           icon: '🔮' },
  { key: 'health',         title: 'Your Health & Vitality',        icon: '💚' },
  { key: 'relationships',  title: 'Your Love & Relationships',      icon: '💫' },
]

export default function ChartReading({ input, topic, onOpenRajyogas }) {
  const { t, i18n } = useTranslation()
  const { isAuthenticated } = useAuth()

  const [status, setStatus]           = useState('idle')
  const [predSections, setPredSections] = useState({})
  const [activeYogas, setActiveYogas] = useState([])
  const [errorMsg, setErrorMsg]       = useState('')
  const [provider, setProvider]       = useState(null)

  // Staggered visibility per section
  const [visible, setVisible]         = useState([])
  const [showWa, setShowWa]           = useState(false)

  // WhatsApp
  const [waNumber, setWaNumber]       = useState('')
  const [waSubmitted, setWaSubmitted] = useState(false)

  async function generate() {
    setStatus('loading')
    setPredSections({})
    setVisible([])
    setShowWa(false)
    setErrorMsg('')

    try {
      const lang = i18n.language.startsWith('hi') ? 'hi' : 'en'
      const res = await fetch(`${API_BASE}/api/kundli/reading`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...input, language: lang }),
      })
      if (!res.ok) {
        const err = await res.json().catch(() => ({}))
        throw new Error(err.detail || 'Error generating prediction')
      }
      const data = await res.json()

      const secs = data.prediction_sections || {}
      setPredSections(secs)
      setActiveYogas(data.active_yogas || [])
      setProvider(data.llm_provider || null)
      setStatus('done')

      // Stagger each section's fade-in, 380ms apart
      const count = SECTION_CONFIG.filter(c => secs[c.key]).length
      SECTION_CONFIG.forEach((c, i) => {
        if (secs[c.key]) {
          setTimeout(() => setVisible(prev => [...prev, c.key]), i * 380)
        }
      })
      const base = count * 380 + 300
      setTimeout(() => setShowWa(true), base + 400)
    } catch (e) {
      setErrorMsg(e.message || 'Error generating prediction')
      setStatus('error')
    }
  }

  // Auto-reveal for signed-in visitors — the "Reveal My Prediction" click
  // gate exists for the anonymous funnel (it's a deliberate curiosity/
  // conversion moment for someone who just typed in a birth chart with no
  // account), but a signed-in person coming from their own home page
  // already made that decision by opening the tab. Making them click
  // again to see their own reading is friction with no purpose. Guarded
  // by a ref (not just `status === 'idle'`) so this fires exactly once
  // per mount, not every time status happens to cycle back through idle.
  const autoRevealedRef = useRef(false)
  useEffect(() => {
    if (isAuthenticated && status === 'idle' && !autoRevealedRef.current) {
      autoRevealedRef.current = true
      generate()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isAuthenticated])

  function handleWaSubmit() {
    if (waNumber.trim()) {
      try {
        localStorage.setItem('starjyotish_wa', JSON.stringify({
          number: waNumber.trim(), savedAt: new Date().toISOString(),
        }))
      } catch {
        // Best-effort only — localStorage can throw in private browsing
        // or when full; the WhatsApp number itself isn't critical to save.
      }
      setWaSubmitted(true)
    }
  }

  // ── IDLE ──────────────────────────────────────────────────────────────────
  if (status === 'idle' && !isAuthenticated) return (
    <div className="flex flex-col items-center justify-center py-16 px-4 text-center">
      <div className="text-5xl mb-4">🔮</div>
      <h2 className="text-xl font-bold text-ink mb-2">{t('reading_idle_heading')}</h2>
      <p className="text-ink-muted text-sm mb-6 max-w-sm">
        {t('reading_idle_body')}
      </p>
      <Button size="lg" onClick={generate}>
        Reveal My Prediction
      </Button>
      <p className="text-xs text-ink-faint mt-3">{t('reading_powered_by_generic')}</p>
    </div>
  )

  // ── LOADING ───────────────────────────────────────────────────────────────
  // Also covers the one render where an authenticated visitor is still
  // technically 'idle' before the auto-reveal effect above fires — without
  // this, that single frame would flash the "Reveal My Prediction" button
  // pointlessly before immediately replacing it with this same screen.
  if (status === 'loading' || (status === 'idle' && isAuthenticated)) return (
    <div className="flex flex-col items-center justify-center py-16 px-4 text-center">
      <div className="text-4xl mb-4 animate-spin">⏳</div>
      <p className="font-medium text-primary-dark">Reading your birth chart…</p>
      <div className="mt-4 w-48 h-1.5 bg-night/10 rounded-full overflow-hidden">
        <div className="h-full rounded-full animate-pulse"
             style={{ width: '75%', background: 'linear-gradient(90deg,#2D1B69,#D4AF37)' }} />
      </div>
      <p className="text-xs text-ink-faint mt-3">Identifying Raj Yogas in your chart…</p>
    </div>
  )

  // ── ERROR ─────────────────────────────────────────────────────────────────
  if (status === 'error') return (
    <div className="flex flex-col items-center justify-center py-16 px-4 text-center">
      <div className="text-4xl mb-4">⚠️</div>
      <p className="text-vermillion font-medium mb-4">{errorMsg}</p>
      <Button onClick={() => setStatus('idle')}>
        Try Again
      </Button>
    </div>
  )

  // ── DONE ──────────────────────────────────────────────────────────────────
  return (
    <div className="max-w-2xl mx-auto py-4 px-2 space-y-4">

      {/* ── PREDICTION SECTIONS ─────────────────────────────────────────────── */}
      {SECTION_CONFIG.map(({ key, title, icon }) => {
        const content = predSections[key]
        if (!content) return null
        const isVisible = visible.includes(key)
        const isHealth        = key === 'health'
        const isRelationships = key === 'relationships'

        if (isHealth) return (
          <div key={key}
               className={`rounded-xl overflow-hidden shadow-sm border border-green-200
                          transition-all duration-700
                          ${isVisible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-3'}`}>
            <div className="bg-gradient-to-r from-green-500 to-emerald-400 px-5 py-3 flex items-center gap-2">
              <span className="text-xl">{icon}</span>
              <h3 className="font-bold text-white text-base">{title}</h3>
            </div>
            <div className="bg-parchment-card px-5 py-4">
              <p className="text-ink text-sm leading-relaxed" style={{ whiteSpace: 'pre-wrap' }}>{content}</p>
            </div>
          </div>
        )

        if (isRelationships) return (
          <div key={key}
               className={`rounded-xl overflow-hidden shadow-sm border border-rose-200
                          transition-all duration-700
                          ${isVisible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-3'}`}>
            <div className="bg-gradient-to-r from-rose-500 to-pink-400 px-5 py-3 flex items-center gap-2">
              <span className="text-xl">{icon}</span>
              <h3 className="font-bold text-white text-base">{title}</h3>
            </div>
            <div className="bg-parchment-card px-5 py-4">
              <p className="text-ink text-sm leading-relaxed" style={{ whiteSpace: 'pre-wrap' }}>{content}</p>
            </div>
          </div>
        )

        // Default section style
        return (
          <div key={key}
               className={`rounded-xl p-5 bg-parchment-card border border-primary/30 shadow-sm
                          transition-all duration-700
                          ${isVisible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-3'}`}>
            <div className="flex items-center gap-2 mb-2">
              <span className="text-xl">{icon}</span>
              <h3 className="font-bold text-primary text-base">{title}</h3>
            </div>
            <p className="text-ink text-sm leading-relaxed"
               style={{ whiteSpace: 'pre-wrap' }}>{content}</p>
          </div>
        )
      })}

      {/* ── RAJ YOGA TEASER — deterministic, links to the Rajyogas tab which is
          the single source of truth for the full breakdown (career topic only,
          since only career has a Rajyogas tab to send people to). ──────────── */}
      {topic === 'career' && activeYogas.length > 0 && (
        <div className="relative overflow-hidden rounded-2xl p-6"
             style={{
               background: '#1A0A3B',
               border: '2px solid #D4AF37',
               boxShadow: '0 0 28px rgba(212,175,55,0.18)',
             }}>
          <KundliWheelBg />
          <div className="relative z-10">
            <div className="flex items-center gap-2 mb-2">
              <span className="text-2xl">👑</span>
              <h3 className="font-extrabold text-lg" style={{ color: '#D4AF37' }}>
                You have {activeYogas.length} active Raj Yoga{activeYogas.length > 1 ? 's' : ''}
              </h3>
            </div>
            <p className="text-white text-sm leading-relaxed font-medium mb-4">
              Including {activeYogas.slice(0, 2).map(y => y.name).join(' and ')}
              {activeYogas.length > 2 ? ', and more' : ''} — see the full breakdown of what each one means for you.
            </p>
            <button onClick={onOpenRajyogas}
              className="px-4 py-2 rounded-lg font-semibold text-sm"
              style={{ background: '#D4AF37', color: '#1A0A3B' }}>
              See my Raj Yogas →
            </button>
          </div>
        </div>
      )}

      {/* ── WHATSAPP LEAD CAPTURE ─────────────────────────────────────────── */}
      <div className={`transition-all duration-700
                      ${showWa ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4'}`}>
        {showWa && !waSubmitted && (
          <div className="rounded-xl p-4"
               style={{ border: '1px solid rgba(147,51,234,0.45)', background: 'rgba(45,27,105,0.35)' }}>
            <p className="text-white text-sm mb-3">
              📲 Want a reminder when your peak career window opens? Enter your WhatsApp number for a free timing alert.
            </p>
            <div className="flex flex-col sm:flex-row gap-2">
              <input
                type="tel"
                value={waNumber}
                onChange={e => setWaNumber(e.target.value)}
                placeholder="WhatsApp number"
                className="flex-1 px-3 py-2 rounded-lg text-white text-sm placeholder-gray-500 focus:outline-none"
                style={{ background: 'rgba(30,10,60,0.8)', border: '1px solid rgba(147,51,234,0.6)' }}
              />
              <button
                onClick={handleWaSubmit}
                className="px-4 py-2 rounded-lg font-semibold text-sm shrink-0 w-full sm:w-auto"
                style={{ background: '#D4AF37', color: '#1A0A3B' }}>
                Notify Me →
              </button>
            </div>
            <p className="text-gray-500 text-xs mt-2">No spam. Only your personal career timing updates.</p>
          </div>
        )}
        {waSubmitted && (
          <div className="rounded-xl p-4 text-center"
               style={{ background: 'rgba(4,120,87,0.15)', border: '1px solid rgba(16,185,129,0.4)' }}>
            <p className="text-emerald-400 text-sm">
              ✓ We'll notify you on WhatsApp when your peak career window opens.
            </p>
          </div>
        )}
      </div>

      <div className="text-center pb-4">
        <button onClick={() => setStatus('idle')}
          className="text-sm text-primary hover:text-primary-dark transition">
          ↺ Regenerate Prediction
        </button>
      </div>

      {/* ── DISCLAIMER ───────────────────────────────────────────────────── */}
      {provider && (
        <p className="text-center text-[11px] text-ink-faint pb-1">
          {t('reading_powered_by', { provider })}
        </p>
      )}
      <p className="text-center text-[11px] text-ink-faint leading-relaxed px-4 pb-2">
        {t('disclaimer')}
      </p>
    </div>
  )
}
