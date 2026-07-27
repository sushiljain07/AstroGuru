// frontend/src/components/landing/CareerReportPreview.jsx
//
// Static, non-interactive preview of the Career Intelligence Report for the
// landing page — illustrates the depth of the real feature (an 11-section
// navigable report, a structured roadmap, a personal AI to ask) using the
// same visual language as the real CareerReportTab.jsx (gold/night cards,
// pill nav) rather than a raster screenshot, so this won't go stale again
// the next time that UI changes, and stays visually consistent with the
// rest of this page (which otherwise has zero images).
const PREVIEW_SECTIONS = ['Overview', 'Growth', 'Money', 'Timing', 'Roadmap', 'Ask AI']
const ROADMAP_HORIZONS = ['Now', 'Next 12 Months', '1–3 Years', '3–5 Years']

export default function CareerReportPreview() {
  return (
    <div className="max-w-lg mx-auto bg-parchment-card rounded-2xl border border-line shadow-md overflow-hidden" aria-hidden="true">
      {/* Mini pill nav — mirrors SectionJumpNav's real pill row */}
      <div className="px-4 pt-4 pb-2 flex gap-1.5 overflow-x-auto [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
        {PREVIEW_SECTIONS.map((label, i) => (
          <span
            key={label}
            className={`shrink-0 whitespace-nowrap text-xs px-3 py-1.5 rounded-lg font-medium ${
              i === 0 ? 'bg-mauve text-white' : 'text-ink-muted border border-line'
            }`}
          >
            {label}
          </span>
        ))}
      </div>

      <div className="p-4 space-y-3">
        {/* Gold "Overview" sample card */}
        <div className="rounded-xl overflow-hidden border border-primary/30">
          <div className="bg-gradient-to-r from-primary to-primary-dark px-4 py-2.5 flex items-center gap-2">
            <span className="text-lg">✨</span>
            <span className="font-extrabold text-night text-sm">Your Career Destiny in Brief</span>
          </div>
          <div className="px-4 py-3 bg-parchment-card">
            <p className="text-xs text-ink-muted leading-relaxed">
              A personalized read of your chart's career strengths, current phase, and what's ahead — grounded in real planetary positions, not generic horoscope text.
            </p>
          </div>
        </div>

        {/* Roadmap sample card */}
        <div className="rounded-xl border border-line overflow-hidden">
          <div className="bg-night px-4 py-2.5">
            <span className="font-bold text-primary-light text-sm">🗺️ Your Career Roadmap</span>
          </div>
          <div className="px-4 py-3 grid grid-cols-2 gap-2">
            {ROADMAP_HORIZONS.map(label => (
              <p key={label} className="text-2xs font-semibold text-primary uppercase tracking-wide">
                {label}
              </p>
            ))}
          </div>
        </div>

        {/* Ask Career AI teaser */}
        <div className="rounded-xl border border-mauve/30 bg-mauve/5 px-4 py-3 flex items-center gap-2">
          <span className="text-lg">💬</span>
          <div>
            <p className="font-semibold text-ink text-xs">Ask Career AI</p>
            <p className="text-2xs text-ink-muted">"Should I ask for a promotion this year?"</p>
          </div>
        </div>
      </div>
    </div>
  )
}
