// frontend/src/components/home/TodayWindow.jsx
//
// "Your window today" — turns the panchang's muhurta data into one
// practical read: a sunrise→sunset timeline with the Abhijit muhurta
// (favorable) and Rahu kaal (avoid beginnings) marked, a live "now"
// marker from the real clock, and a plain-English "best window" line.
//
// The timeline always spans sunrise→sunset (the Vedic day boundary) rather
// than an arbitrary 6am–9pm clock window. This is both more accurate
// (Rahu Kaal and Abhijit are fractions of daylight, so they only make
// sense on a daylight axis) and more honest (the "now" marker clamps to
// the bar edges when outside daylight hours instead of appearing stuck at 9pm).
//
// Falls back to 6:00am / 18:00 if panchang hasn't loaded yet.
//
// Fix: Rahu Kaal can overlap Abhijit Muhurta (this is a real astronomical
// situation — Rahu takes priority). The "best window" copy excludes any
// overlap with Rahu Kaal, so the recommended window is always clear.
import { useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { computeWindow, minutesToLabel } from '../../utils/muhurtaWindow'

// Position as % along the sunrise→sunset bar
function pctOf(mins, sunriseMin, sunsetMin) {
  const span = sunsetMin - sunriseMin
  if (span <= 0) return 0
  const p = (mins - sunriseMin) / span
  return Math.max(0, Math.min(100, p * 100))
}

function PanchangCell({ label, value }) {
  if (!value) return null
  return (
    <div className="min-w-0">
      <p className="text-3xs uppercase tracking-wider text-ink-faint">{label}</p>
      <p className="text-xs text-ink-onnight truncate">{value}</p>
    </div>
  )
}

export default function TodayWindow({ panchang }) {
  const { t } = useTranslation()
  const navigate = useNavigate()

  const { abhijitStart, abhijitEnd, rahuStart, rahuEnd, sunrise, sunset, bestStart, bestEnd, bestNote } = useMemo(
    () => computeWindow(panchang),
    [panchang?.sunrise, panchang?.sunset, panchang?.muhurtas],
  )

  // "now" marker only makes sense while we're actually inside today's
  // sunrise→sunset span — outside daylight hours (e.g. after sunset) the
  // marker is simply hidden rather than pinned at an edge, since a "now"
  // stuck at the sunset mark reads as if it's still that time.
  const { nowPct, showNow } = useMemo(() => {
    const now = new Date()
    const nowMin = now.getHours() * 60 + now.getMinutes()
    const p = (nowMin - sunrise) / (sunset - sunrise)
    return { nowPct: Math.max(2, Math.min(98, p * 100)), showNow: nowMin >= sunrise && nowMin <= sunset }
  }, [sunrise, sunset])

  const goodLeft  = pctOf(abhijitStart, sunrise, sunset)
  const goodWidth = Math.max(1, pctOf(abhijitEnd, sunrise, sunset) - goodLeft)
  const avoidLeft  = pctOf(rahuStart, sunrise, sunset)
  const avoidWidth = Math.max(1, pctOf(rahuEnd, sunrise, sunset) - avoidLeft)

  const tithiName = panchang?.tithi?.name
  const nakName = typeof panchang?.nakshatra === 'object' ? panchang?.nakshatra?.name : panchang?.nakshatra
  const horaName = typeof panchang?.hora === 'object' ? panchang?.hora?.name : panchang?.hora

  const hasSummary = Boolean(
    tithiName || nakName || panchang?.yoga || panchang?.karana || panchang?.sunrise || panchang?.sunset || horaName,
  )

  const sunriseLabel = panchang?.sunrise ?? minutesToLabel(sunrise)
  const sunsetLabel  = panchang?.sunset  ?? minutesToLabel(sunset)

  return (
    <button
      onClick={() => navigate('/panchang')}
      className="w-full text-left bg-white/[0.045] border border-white/[0.09] rounded-card p-5 hover:border-primary/30 transition"
    >
      {/* Timeline bar: spans sunrise → sunset */}
      <div className="relative h-3.5 rounded-full bg-white/[0.06] mx-1 mt-2 mb-2">
        {/* Abhijit Muhurta — favorable (golden) */}
        <div
          className="absolute top-0 h-full rounded-full"
          style={{
            left: `${goodLeft}%`,
            width: `${goodWidth}%`,
            background: 'linear-gradient(90deg, rgba(217,164,65,0.55), rgba(240,203,128,0.85))',
            boxShadow: '0 0 12px rgba(240,203,128,0.35)',
          }}
        />
        {/* Rahu Kaal — avoid (red) */}
        <div
          className="absolute top-0 h-full rounded-full bg-vermillion/40"
          style={{ left: `${avoidLeft}%`, width: `${avoidWidth}%` }}
        />
        {/* Now marker — only while today's daylight window is still current */}
        {showNow && (
          <div
            className="absolute -top-1.5 w-0.5 h-[26px] bg-white rounded-sm motion-reduce:transition-none"
            style={{ left: `${nowPct}%`, boxShadow: '0 0 8px rgba(255,255,255,0.8)' }}
          >
            <span className="absolute -top-4 left-1/2 -translate-x-1/2 text-[8px] tracking-widest uppercase text-white whitespace-nowrap">
              {t('home_window_now', 'now')}
            </span>
          </div>
        )}
      </div>

      {/* Axis labels: sunrise and sunset times */}
      <div className="flex justify-between text-3xs text-ink-faint px-1">
        <span>☀ {sunriseLabel}</span>
        <span>{sunsetLabel} ☀</span>
      </div>

      <div className="flex gap-5 mt-3 text-2xs text-ink-onnight/60 flex-wrap">
        <span className="flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full bg-primary-glow shrink-0" style={{ boxShadow: '0 0 6px rgba(240,203,128,0.6)' }} />
          {t('home_window_abhijit', 'Abhijit muhurta — favorable')}
        </span>
        <span className="flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full bg-vermillion shrink-0" />
          {t('home_window_rahu', 'Rahu kaal — avoid beginnings')}
        </span>
      </div>

      {bestStart != null ? (
        <p className="text-sm text-ink-onnight mt-3">
          {t('home_window_best', {
            defaultValue: 'Best window: {{start}} – {{end}}',
            start: minutesToLabel(bestStart),
            end: minutesToLabel(bestEnd),
          })}
          {' — '}
          {t('home_window_best_hint', 'sign, send, or start it here.')}
          {bestNote && (
            <span className="block text-2xs text-vermillion/70 mt-0.5">{bestNote}</span>
          )}
        </p>
      ) : (
        <p className="text-sm text-ink-onnight/60 mt-3">
          Abhijit Muhurta falls within Rahu Kaal today — consider waiting for tomorrow's window.
        </p>
      )}

      <p className="text-sm text-ink-onnight/60 mt-1.5">
        {t('home_window_avoid', {
          defaultValue: 'Avoid: {{start}} – {{end}}',
          start: minutesToLabel(rahuStart),
          end: minutesToLabel(rahuEnd),
        })}
        {' — '}
        {t('home_window_avoid_hint', "Rahu Kaal, skip new starts here.")}
      </p>

      {hasSummary && (
        <div className="grid grid-cols-3 gap-x-3 gap-y-2.5 mt-4 pt-4 border-t border-white/[0.08]">
          <PanchangCell label={t('panchang_tithi', 'Tithi')} value={tithiName} />
          <PanchangCell label={t('panchang_nakshatra', 'Nakshatra')} value={nakName} />
          <PanchangCell label={t('panchang_yoga', 'Yoga')} value={panchang?.yoga} />
          <PanchangCell label={t('panchang_karana', 'Karana')} value={panchang?.karana} />
          <PanchangCell label={t('home_window_sunrise', 'Sunrise')} value={panchang?.sunrise} />
          <PanchangCell label={t('home_window_sunset', 'Sunset')} value={panchang?.sunset} />
          <PanchangCell label={t('home_window_hora', 'Hora')} value={horaName} />
        </div>
      )}

      <p className="text-2xs font-bold text-primary mt-4">
        {t('home_window_full_panchang', 'Full panchang →')}
      </p>
    </button>
  )
}
