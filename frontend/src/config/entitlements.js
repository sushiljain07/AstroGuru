// frontend/src/config/entitlements.js
//
// Stub entitlement system for the Rajyogas / Career Report paywall.
//
// There is currently no real payment or account backend — see the Master
// Execution Plan's Phase 3 (Postgres) and Phase 4 (Razorpay). This module
// exists so the locked-tab UI can be built and shipped now, with exactly
// one function body to swap out later: hasPremiumAccess(). Every component
// that gates on it stays unchanged when real payments land.
//
// Single paid tier for now — one purchase ("Full Report") unlocks both the
// Rajyogas tab and the Career Report tab together, matching the one price
// point that already exists in the product (₹499/₹999 CTA in the free
// Reading tab). Split into per-feature entitlements later only if you
// actually start selling them separately.

const DEV_UNLOCK_KEY = 'starjyotish_dev_unlock'

// Master switch. Set VITE_PAYWALL_ENABLED=false in .env to go back to
// today's fully-open behaviour everywhere, with no component changes.
const PAYWALL_ENABLED = import.meta.env.VITE_PAYWALL_ENABLED !== 'false'

// Owner/developer convenience: visiting the app once with ?unlock=1 sets a
// localStorage flag that persists on this device/browser, so you can see
// real content behind the lock while everyone else still sees it locked.
// ?unlock=0 clears it again.
//
// This is NOT security — there's no backend check behind it yet, so it
// only hides/shows content client-side. Don't rely on it once a real paid
// tier exists; at that point this whole file's hasPremiumAccess() body
// should be replaced with a real entitlement check against the backend.
if (typeof window !== 'undefined') {
  const params = new URLSearchParams(window.location.search)
  if (params.get('unlock') === '1') {
    localStorage.setItem(DEV_UNLOCK_KEY, 'on')
  } else if (params.get('unlock') === '0') {
    localStorage.removeItem(DEV_UNLOCK_KEY)
  }
}

// Intentionally unused for now — see the comment in hasPremiumAccess()
// below: kept in place so re-enabling the paywall later is a one-line
// change instead of rebuilding this.
// eslint-disable-next-line no-unused-vars
function isDevUnlocked() {
  if (typeof window === 'undefined') return false
  return localStorage.getItem(DEV_UNLOCK_KEY) === 'on'
}

export function isPaywallEnabled() {
  return PAYWALL_ENABLED
}

// The one function every gated component calls. Swap the body for a real
// check (e.g. an API call backed by Phase 3/4) when that infra exists.
export function hasPremiumAccess() {
  // Locking disabled for now — until real accounts/subscriptions exist
  // (Master Plan Phase 3/4/7), showing a lock nobody can actually unlock
  // doesn't make sense. The dev-unlock mechanism above is left in place,
  // unused, so re-enabling this later is a one-line change, not a rebuild.
  return true

  // Original gated logic — restore this when real payments/accounts exist:
  // if (!PAYWALL_ENABLED) return true
  // if (isDevUnlocked()) return true
  // return false
}

// Placeholder for a future finer-grained gate — e.g. once the Career Report
// grows sections worth splitting into free vs. premium tiers. Everything is
// free for now, so this always returns true; no component calls this yet.
// eslint-disable-next-line no-unused-vars
export function hasSectionAccess(sectionKey) {
  // Same "always true until real payments exist" story as hasPremiumAccess().
  return true

  // Future per-section logic — restore/extend when real entitlements exist:
  // if (!PAYWALL_ENABLED) return true
  // if (isDevUnlocked()) return true
  // return FREE_SECTIONS.has(sectionKey)
}
