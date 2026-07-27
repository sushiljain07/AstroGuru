// frontend/src/pages/Insights.jsx
// Standalone page for AI readings, Rajyogas, and topic reports.
// Promoted from the old "Insights" tab inside /kundli to its own URL.
import { useState, lazy, Suspense } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useAuth } from '../contexts/AuthContext'
import AnimatedTabRow from '../components/AnimatedTabRow'
import Seo from '../components/Seo'
import { getTopic } from '../config/topics'

const ChartReading    = lazy(() => import('../components/ChartReading'))
const RajyogasTab     = lazy(() => import('../components/RajyogasTab'))
const CareerReportTab = lazy(() => import('../components/CareerReportTab'))
const TopicReportTab  = lazy(() => import('../components/TopicReportTab'))

function TabLoader() {
  return (
    <div className="flex flex-col items-center justify-center py-20 px-4 text-center">
      <div className="text-3xl mb-3 animate-spin">🪐</div>
      <div className="w-40 h-1.5 bg-night/10 rounded-full overflow-hidden">
        <div className="h-full rounded-full animate-pulse bg-primary w-3/4" />
      </div>
    </div>
  )
}

function buildSubtabs(t, topicId) {
  const reading = { id: 'reading', label: t('nav_reading', 'Reading') }
  if (topicId === 'career') {
    return [reading, { id: 'rajyogas', label: t('nav_rajyogas', 'Rajyogas') }, { id: 'career', label: 'Career' }]
  }
  if (topicId === 'health' || topicId === 'relationship' || topicId === 'finance') {
    return [reading, { id: topicId, label: topicId.charAt(0).toUpperCase() + topicId.slice(1) }]
  }
  return [reading]
}

export default function Insights() {
  const { t } = useTranslation()
  const { state }   = useLocation()
  const navigate    = useNavigate()
  const { isAuthenticated } = useAuth()

  // All hooks before any early return
  const [activeSub, setActiveSub] = useState('reading')

  const homeDestination = isAuthenticated ? '/home' : '/'

  if (!state?.input) { navigate(homeDestination); return null }

  const { input } = state
  const topic   = getTopic(input?.topic)
  const topicId = topic?.id ?? null
  const SUBTABS = buildSubtabs(t, topicId)

  return (
    <div className="flex-1 flex flex-col">
      <Seo title="Chart Insights" description="AI-powered reading of your Vedic birth chart." path="/insights" noindex />

      <div className="bg-parchment-card border-b border-line sticky top-[60px] z-30">
        <div className="max-w-5xl mx-auto px-4">
          <div className="pt-2 pb-1">
            <p className="text-[10px] font-semibold uppercase tracking-widest" style={{ color: '#D9A441' }}>
              Insights
            </p>
          </div>

          {SUBTABS.length > 1 && (
            <div className="border-t border-line/40 py-2">
              <AnimatedTabRow tabs={SUBTABS} active={activeSub} onChange={setActiveSub} variant="pill" accent="mauve" />
            </div>
          )}
        </div>
      </div>

      <div className="flex-1 max-w-5xl mx-auto w-full px-4 pt-6 pb-8 sm:pb-4">
        <Suspense fallback={<TabLoader />}>
          <div className={activeSub === 'reading' ? 'tab-fade' : 'hidden'}>
            <ChartReading input={input} />
          </div>
          <div className={activeSub === 'rajyogas' ? 'tab-fade' : 'hidden'}>
            <RajyogasTab input={input} />
          </div>
          <div className={activeSub === 'career' ? 'tab-fade' : 'hidden'}>
            <CareerReportTab input={input} />
          </div>
          {(topicId === 'relationship' || topicId === 'finance' || topicId === 'health') && (
            <div className={activeSub === topicId ? 'tab-fade' : 'hidden'}>
              <TopicReportTab topic={topicId} input={input} />
            </div>
          )}
        </Suspense>
      </div>
    </div>
  )
}
