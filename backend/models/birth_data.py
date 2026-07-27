from typing import List, Optional
from pydantic import BaseModel, Field, field_validator
from datetime import date, time


class BirthInput(BaseModel):
    date: str   # "YYYY-MM-DD"
    time: str   # "HH:MM"
    # max_length=200: generous headroom above any real place name — even a
    # fully-detailed Nominatim display_name for a small Indian village
    # (village, taluk, district, state, postal code, country) typically
    # runs well under 150 chars — while still blocking pathological input
    # from reaching the geocoding call or an LLM prompt unbounded.
    place: str = Field(max_length=200)  # e.g. "New Delhi, India"
    language: str = "en"
    # max_length=500: a genuinely detailed, multi-clause question still
    # comfortably fits (the realistic preset questions in the landing page's
    # Ask spotlight run 35-42 chars); this just stops unbounded text from
    # being concatenated into the AI prompt.
    question: Optional[str] = Field(default=None, max_length=500)
    topic: Optional[str] = None  # 'career' | 'relationship' | 'health' | 'finance' — set when the
                                  # user arrived via a landing-page topic card; see services/ai.py's
                                  # build_prediction_prompt() for how it's used.
    # 'unmarried' | 'married' | 'divorced_widowed' — used only by
    # /api/relationship-report (services/relationship_analysis.py). Without
    # this, the report has no way to know whether to predict a future
    # marriage or discuss an existing one, which produces confidently wrong
    # content for anyone not single. Defaults to 'unmarried' for backward
    # compatibility with the relationship-report patch shipped before this
    # field existed.
    marital_status: Optional[str] = "unmarried"
    # Optional career-report context, captured lazily in CareerReportTab
    # (skippable — omitted entirely for anyone who skips the capture step
    # or for any non-career report). Used only by
    # services/career_analysis.py's generate_career_report() to bias which
    # of the report's existing sections get emphasized; it must never be
    # treated as astrological evidence on its own (see that module's
    # "context, not evidence" prompt guardrail).
    # e.g. 'student' | '0_3_years' | 'experienced' | 'senior' |
    # 'entrepreneur' | 'career_break' | 'job_seeker' | 'transition'
    career_stage: Optional[str] = None
    current_profession: Optional[str] = Field(default=None, max_length=200)
    # Up to 3 free-form concern strings, e.g. "Am I in the right career?"
    career_concerns: Optional[List[str]] = None
    # Opt-in persistence: when set, the report-generating routes (career,
    # rajyogas, relationship, wealth) best-effort save a BirthProfile +
    # Report row for this phone number via services/persistence.py. Omit
    # it (the default) and nothing is written — behavior is identical to
    # before this field existed. Not validated as a real phone number
    # here; the persistence layer treats it as an opaque identity key the
    # same way the WhatsApp/Razorpay funnel design already does.
    save_for_phone: Optional[str] = Field(default=None, max_length=20)

    @field_validator("date")
    @classmethod
    def validate_date(cls, v: str) -> str:
        date.fromisoformat(v)
        return v

    @field_validator("time")
    @classmethod
    def validate_time(cls, v: str) -> str:
        time.fromisoformat(v)
        return v
