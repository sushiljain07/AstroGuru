// frontend/src/components/SectionJumpNav.jsx
//
// Sticky in-page "jump to section" nav for long single-scroll reports.
// Drives `active` from scroll position via IntersectionObserver instead of
// switching rendered content — every section stays mounted, this only
// changes which item is highlighted and what a tap scrolls to.
//
// Two renderings, not one shrunk to fit the other:
//   - sm and up: AnimatedTabRow's pill row (same visual language as
//     Result.jsx's SubTabBar) — there's room for it.
//   - below sm: a horizontal strip of 11 pills isn't a native mobile
//     pattern, and the app's real bottom nav bar (BottomNav.jsx) already
//     owns the fixed bottom edge for global nav, so this doesn't get one
//     too. Instead: a compact "Current Section ▾" trigger that opens a
//     bottom-sheet-style overlay listing every section as a tall tap
//     target, closer to how native apps present a "jump to" menu.
import { useEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import AnimatedTabRow from './AnimatedTabRow'

export default function SectionJumpNav({ sections, className = '' }) {
  const [active, setActive] = useState(sections[0]?.id)
  const [sheetOpen, setSheetOpen] = useState(false)
  const observerRef = useRef(null)

  useEffect(() => {
    const elements = sections.map(s => document.getElementById(s.id)).filter(Boolean)
    if (elements.length === 0) return

    // Detection band near the top of the viewport — a section becomes
    // "active" once it crosses into the upper portion of the screen.
    observerRef.current = new IntersectionObserver(
      entries => {
        const visible = entries.filter(e => e.isIntersecting)
        if (visible.length === 0) return
        const topMost = visible.reduce((a, b) =>
          a.boundingClientRect.top < b.boundingClientRect.top ? a : b
        )
        setActive(topMost.target.id)
      },
      { rootMargin: '-120px 0px -70% 0px', threshold: 0 }
    )
    elements.forEach(el => observerRef.current.observe(el))
    return () => observerRef.current?.disconnect()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sections.length])

  function scrollToSection(id) {
    document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }

  function handleMobileSelect(id) {
    scrollToSection(id)
    setSheetOpen(false)
  }

  const activeLabel = sections.find(s => s.id === active)?.label ?? sections[0]?.label

  return (
    <>
      {/* sm and up: horizontal pill row */}
      <div className={`hidden sm:block ${className}`}>
        <AnimatedTabRow
          tabs={sections}
          active={active}
          onChange={scrollToSection}
          variant="pill"
          accent="mauve"
        />
      </div>

      {/* below sm: compact trigger + bottom-sheet overlay */}
      <div className={`sm:hidden ${className}`}>
        <button
          type="button"
          onClick={() => setSheetOpen(true)}
          aria-haspopup="true"
          aria-expanded={sheetOpen}
          className="w-full flex items-center justify-between gap-2 px-4 py-2 rounded-full bg-mauve text-white text-sm font-medium shadow-sm"
        >
          <span className="truncate">{activeLabel}</span>
          <span className="shrink-0 opacity-80">▾</span>
        </button>

        {sheetOpen && createPortal(
          // Portalled to document.body: the sticky header this trigger
          // lives in uses backdrop-blur (backdrop-filter), which — like
          // `filter` and `transform` — establishes a new containing block
          // for `position: fixed` descendants. Left in place, "fixed
          // inset-0" here would resolve against that small sticky box
          // instead of the viewport, squashing the sheet instead of
          // anchoring it to the real screen bottom.
          <div className="fixed inset-0 z-50 flex items-end" role="dialog" aria-modal="true">
            <div
              className="absolute inset-0 bg-night/40"
              onClick={() => setSheetOpen(false)}
            />
            <div className="relative w-full bg-parchment-card rounded-t-2xl max-h-[70vh] overflow-y-auto pb-safe shadow-2xl animate-fade-in-fast">
              <div className="sticky top-0 bg-parchment-card border-b border-line px-4 py-3 flex items-center justify-between">
                <span className="font-bold text-ink text-sm">Jump to section</span>
                <button
                  type="button"
                  onClick={() => setSheetOpen(false)}
                  aria-label="Close"
                  className="text-ink-faint text-xl leading-none px-2"
                >
                  ×
                </button>
              </div>
              <div className="p-2">
                {sections.map(s => (
                  <button
                    key={s.id}
                    type="button"
                    onClick={() => handleMobileSelect(s.id)}
                    className={`w-full text-left px-4 py-3 rounded-lg text-sm transition ${
                      active === s.id ? 'bg-mauve text-white font-semibold' : 'text-ink hover:bg-night/5'
                    }`}
                  >
                    {s.label}
                  </button>
                ))}
              </div>
            </div>
          </div>,
          document.body
        )}
      </div>
    </>
  )
}
