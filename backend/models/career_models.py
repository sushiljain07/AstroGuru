from typing import List, Optional
from pydantic import BaseModel


class CareerSection(BaseModel):
    title: str
    content: str


class AstrologicalEvidence(BaseModel):
    lagna: str = "?"
    moon_sign: str = "?"
    sun_sign: str = "?"
    amatyakaraka: str = "N/A"
    amatyakaraka_placement: str = "N/A"
    tenth_lord: str = "?"
    tenth_lord_placement: str = "N/A"
    d10_lagna: str = "?"
    d10_job_score: int = 0
    d10_business_score: int = 0
    current_mahadasha: str = "?"
    current_mahadasha_end: str = "?"
    current_antardasha: str = "N/A"
    # Full planet-by-planet table — Deep Analysis tier's expanded drill-down.
    all_planets: List[dict] = []


class CareerOption(BaseModel):
    rank: int
    title: str
    field: str
    reason: str
    key_planets: List[str] = []
    favorable_dasha: str = ""
    effort_required: str = "medium"
    timeline: str = ""


class CareerRoadmap(BaseModel):
    now: str = ""
    next_12_months: str = ""
    years_1_to_3: str = ""
    years_3_to_5: str = ""
    top_actions: List[str] = []
    top_avoid: List[str] = []
    next_question: str = ""


class CareerAlignment(BaseModel):
    label: str
    amk_planet: str = "?"
    matched_keywords: List[str] = []
    explanation: str = ""


class CareerReport(BaseModel):
    llm_provider: str = ""
    # ── New v2 sections (primary report flow) ─────────────────────────────────
    career_destiny_brief: Optional[CareerSection] = None
    natural_strengths: Optional[CareerSection] = None
    best_career_path: Optional[CareerSection] = None
    job_vs_business_verdict: Optional[CareerSection] = None
    peak_career_window: Optional[CareerSection] = None
    current_phase: Optional[CareerSection] = None
    career_growth: Optional[CareerSection] = None
    career_money: Optional[CareerSection] = None
    career_challenges: Optional[CareerSection] = None
    academic_path: Optional[CareerSection] = None
    gemstone_recommendation: Optional[CareerSection] = None
    rudraksha_recommendation: Optional[CareerSection] = None
    empowering_remedies: Optional[CareerSection] = None
    closing_blessing: Optional[CareerSection] = None

    # ── Legacy sections (Optional for backward compatibility) ──────────────────
    # career_rajyogas: retired — full Raj Yoga detail lives only in the
    # dedicated Rajyogas tab now (see active_yogas below for the teaser).
    career_rajyogas: Optional[CareerSection] = None
    lagna_personality: Optional[CareerSection] = None
    job_vs_business: Optional[CareerSection] = None
    tenth_house_d1: Optional[CareerSection] = None
    d10_analysis: Optional[CareerSection] = None
    amatyakaraka: Optional[CareerSection] = None
    career_fields: Optional[CareerSection] = None
    student_streams: Optional[CareerSection] = None
    yogas_combinations: Optional[CareerSection] = None
    dasha_predictions: Optional[CareerSection] = None
    remedies: Optional[CareerSection] = None
    conclusion: Optional[CareerSection] = None

    # ── Structured data ────────────────────────────────────────────────────────
    career_options: Optional[List[CareerOption]] = None
    single_best_career: Optional[CareerSection] = None
    transit_impact: Optional[CareerSection] = None
    # Deterministic (check_all_yogas()), same shape as ReadingResponse.active_yogas
    # in models/chart_data.py — used to render a teaser linking to the Rajyogas tab.
    active_yogas: List[dict] = []
    # Deterministic technical drill-down — no LLM involvement, see career_analysis.py.
    astrological_evidence: Optional[AstrologicalEvidence] = None
    career_roadmap: Optional[CareerRoadmap] = None
    # Deterministic (compute_career_alignment()) — no LLM involvement.
    career_alignment: Optional[CareerAlignment] = None
