// frontend/src/pages/PersonalHome.jsx  v5 — "Home, reimagined"
//
// A restructure of v4's dark "sky masthead + thread of beats" page onto
// the approved home-v5 mock: one page-level Starfield behind everything,
// a slimmer masthead (tithi line, edition chip, streak pill, a real
// celestial-clock disc instead of the old sun-arc), a practical "your
// window today" muhurta beat, a constellation in place of the week chip
// row, life-area signal folded into the reports beat instead of living
// separately, and a "the sky remembers" memory+journal beat closing out
// before one last idea and a quiet closing chapter. Every beat still reads
// from the same real hooks v4 used (useDailyEditor, usePanchang,
// useChartExtras, useUserJourney) — this is a new skin and structure on
// real data, not new fake content.
//
// Beat order:
//  1. HomeMasthead — profile chips, streak pill, greeting, tithi line,
//     edition chip, celestial clock (Sun by day / phase-accurate Moon by
//     night)
//  2. ContinuityStrip — "the app remembers you" whisper
//  3. Beat: Your day — DailyPatrikaHero (tap-through patrika deck +
//     reactions + day-score ring) + Do/Avoid + the moon/dasha "why"
//  4. Beat: Your window today — TodayWindow (muhurta timeline + panchang
//     brief)
//  5. Beat: This week — WeekStrip, now a constellation → /week-ahead
//  6. Beat: Your charts — ChartsStrip → /kundli divisional tab
//  7. Beat: Your reports — ReportsStrip, now carrying the life-area trend
//     signal that used to be LifeAreaGrid's own beat
//  8. Beat: Coming up — ComingUpStrip, reduced to the 2 nearest events
//  9. Beat: The sky remembers — a slim Ask-Jyoti entry point + SkyRemembers
//     (yesterday's-reaction memory line + free-text journal)
//  10. Beat: One idea before you go — KnowledgeCapsule
//  11. ClosingBeat — the page's quiet full stop + share
//  12. DisclaimerBlock
//  13. AskPersonaPanel FAB
//
// LifeAreaGrid.jsx, ReflectionLoop.jsx and JournalPrompt.jsx are no longer
// wired in here (their roles are folded into ReportsStrip and
// SkyRemembers respectively) but remain on disk, unmodified and still
// importable elsewhere — nothing was deleted.
//
// Header/footer/BottomNav/background are the app shell's job — see
// components/layout/WorkspaceLayout.jsx. This page renders content only.

import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useAuth } from '../contexts/AuthContext'
import Seo from '../components/Seo'
import Reveal from '../components/Reveal'
import { Button, Card, StateBlock } from '../components/ui'
import { useCurrentLocation } from '../hooks/useCurrentLocation'
import { usePanchang } from '../hooks/usePanchang'
import { useDailyEditor } from '../hooks/useDailyEditor'
import { useUserJourney } from '../hooks/useUserJourney'
import { useChartExtras } from '../hooks/useChartExtras'

import Starfield from '../components/home/Starfield'
import HomeMasthead from '../components/home/HomeMasthead'
import ContinuityStrip from '../components/home/ContinuityStrip'
import DailyPatrikaHero from '../components/home/DailyPatrikaHero'
import DoAvoidCards from '../components/home/DoAvoidCards'
import ChartSpotlight from '../components/home/ChartSpotlight'
import TodayWindow from '../components/home/TodayWindow'
import ComingUpStrip from '../components/home/ComingUpStrip'
import ReportsStrip from '../components/home/ReportsStrip'
import DisclaimerBlock from '../components/home/DisclaimerBlock'
import AskPersonaPanel from '../components/home/AskPersonaPanel'
import KnowledgeCapsule from '../components/home/KnowledgeCapsule'
import WeekStrip from '../components/home/WeekStrip'
import ChartsStrip from '../components/home/ChartsStrip'
import SkyRemembers from '../components/home/SkyRemembers'
import ClosingBeat from '../components/home/ClosingBeat'

import { getPrimaryProfile, listProfiles, loadProfiles } from '../services/astrologyProfiles'
import { withHindiPlanet } from '../config/hindiNames'
import {
  computeDayScore, computeDoAvoid, computeLifeAreas, computeSpotlight,
  buildComingUpEvents, computeOneAction,
} from '../utils/dailyInsights'
import { formatDate } from '../utils/format'

// One "beat" on the home thread: gold dot on the hairline, serif gold
// heading, optional sub + view-full CTA. Pure design tokens
// (primary-glow / primary / night-deep) — no hardcoded hex.
function Beat({ id, title, subtitle, cta, onCta, delay = 0, children }) {
  return (
    <div id={id} className="relative pl-5 mb-8">
      <div
        className="absolute -left-px top-[7px] w-2 h-2 rounded-full bg-primary ring-4 ring-night-deep"
        aria-hidden="true"
      />
      <div className="flex items-start justify-between gap-3 mb-3.5">
        <div>
          <h2 className="font-serif font-medium text-base sm:text-[19px] leading-snug text-primary-glow">
            {title}
          </h2>
          {subtitle && <p className="text-xs text-primary-light/55 mt-1">{subtitle}</p>}
        </div>
        {cta && (
          <Button variant="outline" surface="night" size="sm" onClick={onCta} className="shrink-0">
            {cta}
          </Button>
        )}
      </div>
      <Reveal delay={delay}>{children}</Reveal>
    </div>
  )
}

export default function PersonalHome() {
  const { t, i18n } = useTranslation()
  const navigate = useNavigate()
  const { user, accessToken } = useAuth()

  const [profilesLoaded, setProfilesLoaded] = useState(false)
  useEffect(() => {
    loadProfiles(user, accessToken).then(() => setProfilesLoaded(true))
  }, [user?.id]) // eslint-disable-line

  const [activeProfile] = useState(null)
  const profile = activeProfile ?? getPrimaryProfile(user)
  const allProfiles = listProfiles(user)

  const { location } = useCurrentLocation()
  const panchang = usePanchang(location)
  const { transit, outlook } = useChartExtras(profile)
  const editorLang = i18n.language?.startsWith('hi') ? 'hi' : 'en'
  const { edition, requestRefresh } = useDailyEditor(profile, panchang.data, editorLang)
  const { summary: journeySummary, recordReaction, cardReactions } = useUserJourney(accessToken)

  function openChart(activeSubtab = 'birth_chart', activeTabId = 'kundli') {
    if (!profile) return
    navigate('/kundli', {
      state: {
        data: profile.chart,
        input: { name: profile.label, date: profile.birth_date, time: profile.birth_time, place: profile.place },
        activeTab: activeTabId, activeSubtab,
      },
    })
  }

  function openReport(topicId) {
    if (!profile) return
    // Career, finance, relationship, health → /insights with topic set,
    // which builds the Reading/Rajyogas/Report subtabs (buildSubtabs in Insights.jsx).
    navigate('/insights', {
      state: {
        data: profile.chart,
        input: {
          name: profile.label,
          date: profile.birth_date,
          time: profile.birth_time,
          place: profile.place,
          topic: topicId,
        },
      },
    })
  }

  const loading = !profilesLoaded && !profile

  if (loading) {
    return (
      <div className="max-w-2xl mx-auto w-full px-4 pt-10">
        <StateBlock loading lines={6} surface="night" />
      </div>
    )
  }

  if (!profile) {
    return (
      <div className="max-w-3xl mx-auto w-full px-4 pt-16 pb-16">
        <Seo title={t('home_seo_title')} description={t('home_seo_description')} path="/home" noindex />
        <StateBlock
          surface="night"
          title={t('home_empty_title')}
          body={t('home_empty_body')}
          action={
            <Button to="/onboarding" size="lg" className="mt-6">
              {t('home_set_up_chart')}
            </Button>
          }
        />
      </div>
    )
  }

  const { chart } = profile

  const transitPlanets = transit?.transit_planets ?? null
  const dayScore    = transitPlanets ? computeDayScore(chart, transitPlanets, t) : null
  const oneAction   = transitPlanets ? computeOneAction(chart, transitPlanets, dayScore, panchang.data, t) : null
  const doAvoid     = transitPlanets ? computeDoAvoid(chart, transitPlanets, panchang.data, t) : null
  const lifeAreas   = transitPlanets ? computeLifeAreas(chart, transitPlanets, t) : null
  const spotlight   = transitPlanets ? computeSpotlight(chart, transitPlanets, t) : null
  const comingUpEvents = outlook ? buildComingUpEvents(chart, outlook, formatDate, t) : []

  const patrikaHeadline = edition?.headline ?? edition?.cards?.[0]?.text ?? null

  return (
    <div className="relative">
      <Seo title={t('home_seo_title')} description={t('home_seo_description')} path="/home" noindex />

      {/* One page-level sky behind everything — see Starfield.jsx. */}
      <Starfield />

      <div className="relative z-10">
        <HomeMasthead
            profile={profile}
            profiles={allProfiles}
            location={location}
            panchang={panchang.data}
            dashaTags={spotlight?.dashaSpotlight}
        />

        <div className="max-w-2xl mx-auto px-4 sm:px-6 pb-28 md:pb-12">
          <div className="pt-1"><ContinuityStrip summary={journeySummary} /></div>

          {/* The thread: a fading gold hairline the beats hang off. */}
          <div className="relative mt-5 before:content-[''] before:absolute before:left-[3px] before:top-1 before:bottom-6 before:w-px before:bg-gradient-to-b before:from-primary before:to-primary/10 before:opacity-40">
            <Beat id="sj-your-day" title={t('home_right_now_label')} delay={0}>
              <DailyPatrikaHero
                firstName={profile.label?.split(' ')[0]}
                edition={edition}
                dayScore={dayScore}
                panchang={panchang.data}
                chapterLabelFn={withHindiPlanet}
                oneAction={oneAction}
                onRefresh={requestRefresh}
                onReaction={(cardType, reaction, event) =>
                  recordReaction(cardType, reaction, {
                    planet: event?.planet, house: event?.house, variation: edition?.variation,
                  })
                }
                cardReactions={cardReactions}
              />
              {doAvoid && <div className="mt-4"><DoAvoidCards doItems={doAvoid.doItems} avoidItems={doAvoid.avoidItems} /></div>}
              {spotlight && (
                <div className="mt-4">
                  <ChartSpotlight moonSpotlight={spotlight.moonSpotlight} dashaSpotlight={spotlight.dashaSpotlight} />
                </div>
              )}
            </Beat>

            <Beat id="sj-window" title={t('home_window_label', 'Your window today')}>
              <TodayWindow panchang={panchang.data} />
            </Beat>

            <Beat id="sj-week" title={t('home_week_strip_label')} cta={t('home_week_strip_cta')} onCta={() => navigate('/week-ahead')}>
              <WeekStrip location={location} />
            </Beat>

            <Beat id="sj-charts" title={t('home_charts_strip_label')} cta={t('home_charts_strip_cta')} onCta={() => openChart('divisional', 'kundli')}>
              <ChartsStrip profile={profile} />
            </Beat>

            <Beat
              title={t('home_your_reports_label')}
              cta={t('home_generate_for_others_cta', 'For someone else')}
              onCta={() => navigate('/generate')}
            >
              <ReportsStrip onOpenReport={openReport} featuredId={lifeAreas?.[0]?.topicId ?? 'career'} lifeAreas={lifeAreas} />
            </Beat>

            <Beat title={t('home_coming_up_label')}>
              {comingUpEvents.length > 0
                ? <ComingUpStrip events={comingUpEvents} />
                : <p className="text-sm text-ink-onnight/55">{t('home_coming_up_loading')}</p>
              }
            </Beat>

            <Beat title={t('home_sky_remembers_label', 'The sky remembers')}>
              <Card
                as="button"
                surface="night"
                padding="none"
                interactive
                onClick={() => window.dispatchEvent(new Event('sj:open-jyoti'))}
                className="w-full text-left px-5 py-4 mb-4 hover:bg-white/[0.07] flex items-center justify-between gap-3"
              >
                <div>
                  <p className="text-2xs uppercase tracking-wider text-primary font-semibold mb-1">{t('home_ask_jyoti_label')}</p>
                  <p className="text-sm text-ink-onnight/75">{t('home_ask_jyoti_body')}</p>
                </div>
                <span className="text-primary-light text-lg shrink-0">↗</span>
              </Card>
              <SkyRemembers profile={profile} lang={editorLang} journeySummary={journeySummary} />
            </Beat>

            <Beat title={t('home_one_idea_label', 'One idea before you go')}>
              <KnowledgeCapsule edition={edition} />
            </Beat>
          </div>

          <ClosingBeat headline={patrikaHeadline} comingUpEvents={comingUpEvents} />
          <DisclaimerBlock />
        </div>
      </div>

      <AskPersonaPanel
        userId={user?.id}
        input={{ date: profile.birth_date, time: profile.birth_time, place: profile.place }}
      />
    </div>
  )
}
