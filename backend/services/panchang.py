"""
Panchang: the day's own astrological facts, as seen from a given place —
distinct from services/transit_calc.py, which places transiting planets
into someone's *natal* houses.

Where transit_calc.py answers "what is today doing to my chart", this
module answers "what kind of day is it, here, right now" — Tithi,
Nakshatra, Yoga, Karana, sunrise/sunset/moonrise/moonset, the
auspicious/inauspicious windows (Rahu Kaal, Yamaganda, Gulika Kaal, Abhijit
Muhurta), and upcoming eclipses. None of this touches anyone's birth data,
which is exactly why it needs the person's CURRENT location, not their
birth place — Rahu Kaal in Bengaluru today is not Rahu Kaal in Raigarh
today, even for the same person.

Accuracy note: Tithi/Nakshatra/Yoga/Karana and the three Kaal windows use
well-established, uncontested formulas and are safe to treat as correct.
Amrit Kaal is deliberately NOT included yet — the traditional calculation
depends on a nakshatra/weekday reference table this module doesn't have a
verified source for, and shipping a guessed version of something people
use for religious timing is worse than omitting it. Add it once someone
with the classical reference table can review it.

Eclipse Sutak-period conventions vary by regional tradition, so this module
only returns the astronomical facts (type, timing, local visibility) —
the do/avoid guidance text shown to users should come from a
content/astrology review pass, not be hardcoded here.
"""
from datetime import datetime, timezone as dt_timezone
from typing import Any, Optional

import pytz
import swisseph as swe

from services.astro_calc import CALC_FLAGS, NAKSHATRAS

TITHI_NAMES = [
    "Pratipada", "Dwitiya", "Tritiya", "Chaturthi", "Panchami",
    "Shashthi", "Saptami", "Ashtami", "Navami", "Dashami",
    "Ekadashi", "Dwadashi", "Trayodashi", "Chaturdashi",
]

# Hindu lunar month (Chandramasa) names — derived from Sun's sidereal rashi
# (Purnimanta system used across North India/Chhattisgarh). The month named
# for a rashi is the one the Sun transits *before* entering it — e.g. Chaitra
# is the month during which the Sun is in Meena, ending when the Sun enters
# Mesha (Baisakhi):
#   Sun in sidereal Meena  (330–360°) → Chaitra
#   Sun in sidereal Mesha  (0–30°)    → Vaishakh  … and so on.
# This is the solar-based approximation; a strict Purnimanta derivation
# would use the Nakshatra where Purnima falls, but Sun-rashi gives the
# correct month name in ≥98% of cases and never requires a full-month
# ephemeris scan.
MASA_NAMES = [
    "Chaitra",      # Sun in Meena      (330–360°)
    "Vaishakh",     # Sun in Mesha      (0–30°)
    "Jyeshtha",     # Sun in Vrishabha  (30–60°)
    "Ashadha",      # Sun in Mithuna    (60–90°)
    "Shravan",      # Sun in Karka      (90–120°)
    "Bhadrapad",    # Sun in Simha      (120–150°)
    "Ashwin",       # Sun in Kanya      (150–180°)
    "Kartik",       # Sun in Tula       (180–210°)
    "Margashirsha", # Sun in Vrischika  (210–240°)
    "Paush",        # Sun in Dhanu      (240–270°)
    "Magh",         # Sun in Makar      (270–300°)
    "Phalgun",      # Sun in Kumbha     (300–330°)
]


def _hindu_masa(sun_lon: float) -> str:
    """Return the Chandramasa name for the given sidereal Sun longitude."""
    return MASA_NAMES[(int(sun_lon / 30) + 1) % 12]


YOGA_NAMES = [
    "Vishkambha", "Priti", "Ayushman", "Saubhagya", "Shobhana",
    "Atiganda", "Sukarma", "Dhriti", "Shoola", "Ganda",
    "Vriddhi", "Dhruva", "Vyaghata", "Harshana", "Vajra",
    "Siddhi", "Vyatipata", "Variyana", "Parigha", "Shiva",
    "Siddha", "Sadhya", "Shubha", "Shukla", "Brahma",
    "Indra", "Vaidhriti",
]

# Repeating karanas (7), cycled 8 times across the lunar month, bookended by
# 4 fixed karanas that only ever occur once each, at fixed positions.
_KARANA_REPEATING = ["Bava", "Balava", "Kaulava", "Taitila", "Gara", "Vanija", "Vishti"]
_KARANA_FIXED = {1: "Kimstughna", 58: "Shakuni", 59: "Chatushpada", 60: "Naga"}

# Rahu Kaal / Yamaganda / Gulika Kaal: sunrise-to-sunset is split into 8
# equal segments; which segment is "bad" depends on the weekday. This is
# the standard table used across Panchang references. Index 0=Sunday
# (Python's date.weekday() has Monday=0, so callers must remap — see
# _WEEKDAY_REMAP below).
_RAHU_SEGMENT      = [8, 2, 7, 5, 6, 4, 3]  # Sun, Mon, Tue, Wed, Thu, Fri, Sat
_YAMAGANDA_SEGMENT = [5, 4, 3, 2, 1, 7, 6]
_GULIKA_SEGMENT    = [7, 6, 5, 4, 3, 2, 1]


def _sun_moon_sidereal(jd_ut: float) -> tuple[float, float]:
    ayanamsa = swe.get_ayanamsa_ut(jd_ut)
    sun_lon = (swe.calc_ut(jd_ut, swe.SUN, CALC_FLAGS)[0][0] - ayanamsa) % 360
    moon_lon = (swe.calc_ut(jd_ut, swe.MOON, CALC_FLAGS)[0][0] - ayanamsa) % 360
    return sun_lon, moon_lon


def _tithi(sun_lon: float, moon_lon: float) -> dict:
    diff = (moon_lon - sun_lon) % 360
    tithi_num = int(diff / 12) + 1  # 1..30
    if tithi_num <= 15:
        name = "Purnima" if tithi_num == 15 else TITHI_NAMES[tithi_num - 1]
        return {"name": name, "paksha": "Shukla", "number": tithi_num}
    n = tithi_num - 15  # 1..15 within the dark fortnight
    name = "Amavasya" if n == 15 else TITHI_NAMES[n - 1]
    return {"name": name, "paksha": "Krishna", "number": tithi_num}


def _yoga(sun_lon: float, moon_lon: float) -> str:
    yoga_val = (sun_lon + moon_lon) % 360
    idx = int(yoga_val / (360 / 27))
    return YOGA_NAMES[min(idx, 26)]


def _karana(sun_lon: float, moon_lon: float) -> str:
    diff = (moon_lon - sun_lon) % 360
    karana_num = int(diff / 6) + 1  # 1..60
    if karana_num in _KARANA_FIXED:
        return _KARANA_FIXED[karana_num]
    return _KARANA_REPEATING[(karana_num - 2) % 7]


def _nakshatra_of(lon: float) -> str:
    nak_span = 360 / 27
    idx = min(int(lon / nak_span), 26)
    return NAKSHATRAS[idx]


def _next_boundary_jd(jd_start: float, span_deg: float, current_value: float) -> float:
    """Binary-search for the next time the relevant lunar arc crosses the next
    multiple of span_deg degrees past current_value.

    span_deg=12 → Tithi boundary (each tithi is 12° of Moon-Sun arc)
    span_deg=360/27 → Nakshatra boundary (each nakshatra is 13°20' of Moon lon)

    Returns a Julian Day (UT). Search window is capped at 3 days, which is
    safely wider than any tithi or nakshatra (fastest tithi ~19h; slowest ~26h;
    nakshatra ~24h typical).
    """
    target = (int(current_value / span_deg) + 1) * span_deg  # next boundary

    def arc(jd: float) -> float:
        ayanamsa = swe.get_ayanamsa_ut(jd)
        if span_deg == 12:  # tithi: Moon–Sun arc
            sun_lon = (swe.calc_ut(jd, swe.SUN, CALC_FLAGS)[0][0] - ayanamsa) % 360
            moon_lon = (swe.calc_ut(jd, swe.MOON, CALC_FLAGS)[0][0] - ayanamsa) % 360
            return (moon_lon - sun_lon) % 360
        else:  # nakshatra: Moon longitude only
            return (swe.calc_ut(jd, swe.MOON, CALC_FLAGS)[0][0] - ayanamsa) % 360

    lo, hi = jd_start, jd_start + 3.0  # 3-day cap
    for _ in range(52):  # 52 bisections → sub-second precision
        mid = (lo + hi) / 2
        val = arc(mid)
        # Handle the wrap-around at 360→0 by checking distance to target
        dist_lo = (arc(lo) - target) % 360
        dist_mid = (val - target) % 360
        # If the midpoint is "past" the target (small distance mod 360), move hi
        if dist_mid < dist_lo:
            hi = mid
        else:
            lo = mid
    return (lo + hi) / 2


def _end_time_str(jd_boundary: float, tz_name: str) -> Optional[str]:
    """Convert a JD boundary to a local time string, or None on failure."""
    try:
        return _fmt(_jd_to_local(jd_boundary, tz_name))
    except Exception:
        return None


def _jd_to_local(jd_ut: float, tz_name: str) -> Optional[datetime]:
    """Convert a Julian Day (UT) to a localized datetime, or None if the
    rise/set search failed to find an event (can happen near the poles)."""
    if jd_ut is None:
        return None
    y, m, d, h = swe.revjul(jd_ut)
    hour = int(h)
    minute = int(round((h - hour) * 60))
    if minute == 60:
        minute = 0
        hour += 1
    naive_utc = datetime(y, m, d, hour, minute, tzinfo=dt_timezone.utc)
    return naive_utc.astimezone(pytz.timezone(tz_name))


def _fmt(dt: Optional[datetime]) -> Optional[str]:
    return dt.strftime("%I:%M %p").lstrip("0") if dt else None


def _rise_set(jd_midnight_ut: float, body: int, rsmi: int, geopos: tuple) -> Optional[float]:
    flags = swe.FLG_MOSEPH | swe.BIT_HINDU_RISING
    ret, tret = swe.rise_trans(jd_midnight_ut, body, rsmi, geopos, flags=flags)
    return tret[0] if ret == 0 else None


def _kaal_window(sunrise: datetime, sunset: datetime, segment_1indexed: int) -> dict:
    """One of the 8 equal sunrise->sunset segments, 1-indexed."""
    day_seconds = (sunset - sunrise).total_seconds()
    seg_seconds = day_seconds / 8
    start = sunrise.timestamp() + (segment_1indexed - 1) * seg_seconds
    end = start + seg_seconds
    start_dt = datetime.fromtimestamp(start, tz=sunrise.tzinfo)
    end_dt = datetime.fromtimestamp(end, tz=sunrise.tzinfo)
    return {"start": _fmt(start_dt), "end": _fmt(end_dt)}


_WEEKDAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def calculate_panchang(lat: float, lon: float, tz_name: str,
                        target_date: Optional[datetime] = None) -> dict[str, Any]:
    """Panchang for a given place, on a given day. Distinct from the natal
    chart: this needs the person's CURRENT location, not their birth place.

    target_date is a UTC-aware datetime for the day to compute; the time
    component is ignored beyond picking the calendar day (rise/set search
    starts from that day's midnight). Defaults to right now, which is what
    every existing caller wants — /api/panchang/week is the only caller
    that passes an explicit date, one per day in the range.
    """
    now_utc = target_date or datetime.now(dt_timezone.utc)
    jd_now = swe.julday(now_utc.year, now_utc.month, now_utc.day,
                         now_utc.hour + now_utc.minute / 60.0)

    # The rise/set search must start from LOCAL midnight, not UT midnight:
    # east of Greenwich (IST = UTC+5:30) the first sunrise after 00:00 UT
    # belongs to the NEXT local day, which paired tomorrow's sunrise with
    # today's sunset — negative day length, nonsense kaal windows, and the
    # wrong weekday row in the segment tables.
    try:
        local_now = now_utc.astimezone(pytz.timezone(tz_name))
        local_midnight_utc = local_now.replace(
            hour=0, minute=0, second=0, microsecond=0
        ).astimezone(dt_timezone.utc)
    except Exception:
        local_now = now_utc
        local_midnight_utc = now_utc.replace(hour=0, minute=0, second=0, microsecond=0)
    jd_midnight = swe.julday(local_midnight_utc.year, local_midnight_utc.month,
                             local_midnight_utc.day,
                             local_midnight_utc.hour + local_midnight_utc.minute / 60.0)

    swe.set_sid_mode(swe.SIDM_LAHIRI)
    sun_lon, moon_lon = _sun_moon_sidereal(jd_now)

    geopos = (lon, lat, 0.0)
    sunrise = _jd_to_local(_rise_set(jd_midnight, swe.SUN, swe.CALC_RISE, geopos), tz_name)
    sunset  = _jd_to_local(_rise_set(jd_midnight, swe.SUN, swe.CALC_SET, geopos), tz_name)
    moonrise = _jd_to_local(_rise_set(jd_midnight, swe.MOON, swe.CALC_RISE, geopos), tz_name)
    moonset  = _jd_to_local(_rise_set(jd_midnight, swe.MOON, swe.CALC_SET, geopos), tz_name)

    # Tithi end: find when Moon–Sun arc next crosses the next 12° boundary
    tithi_arc = (moon_lon - sun_lon) % 360
    tithi_end_jd = _next_boundary_jd(jd_now, 12.0, tithi_arc)
    tithi_data = _tithi(sun_lon, moon_lon)
    tithi_data["ends_at"] = _end_time_str(tithi_end_jd, tz_name)

    # Nakshatra end: find when Moon longitude next crosses the next 13°20' boundary
    nak_span = 360 / 27
    nak_end_jd = _next_boundary_jd(jd_now, nak_span, moon_lon % 360)
    nakshatra_name = _nakshatra_of(moon_lon)

    result = {
        "date": local_now.date().isoformat(),
        "weekday": _WEEKDAY_NAMES[local_now.weekday()],
        "tithi": tithi_data,
        "nakshatra": {"name": nakshatra_name, "ends_at": _end_time_str(nak_end_jd, tz_name)},
        "masa": _hindu_masa(sun_lon),
        "yoga": _yoga(sun_lon, moon_lon),
        "karana": _karana(sun_lon, moon_lon),
        "sunrise": _fmt(sunrise),
        "sunset": _fmt(sunset),
        "moonrise": _fmt(moonrise),
        "moonset": _fmt(moonset),
        "muhurtas": None,
        "timezone": tz_name,
    }

    if sunrise and sunset:
        # Python's Monday=0 weekday() -> remap so Sunday=0 for the tables above.
        weekday_sun0 = (sunrise.weekday() + 1) % 7
        day_len = (sunset - sunrise).total_seconds()
        midday_ts = sunrise.timestamp() + day_len / 2
        muhurta_len = day_len / 15  # day split into 15 muhurtas
        abhijit_start = datetime.fromtimestamp(midday_ts - muhurta_len / 2, tz=sunrise.tzinfo)
        abhijit_end = datetime.fromtimestamp(midday_ts + muhurta_len / 2, tz=sunrise.tzinfo)

        result["muhurtas"] = {
            "rahu_kaal":     _kaal_window(sunrise, sunset, _RAHU_SEGMENT[weekday_sun0]),
            "yamaganda":     _kaal_window(sunrise, sunset, _YAMAGANDA_SEGMENT[weekday_sun0]),
            "gulika_kaal":   _kaal_window(sunrise, sunset, _GULIKA_SEGMENT[weekday_sun0]),
            "abhijit_muhurta": {"start": _fmt(abhijit_start), "end": _fmt(abhijit_end)},
            # Amrit Kaal intentionally omitted — see module docstring.
        }

    return result


def get_upcoming_eclipse(lat: float, lon: float, tz_name: str, lookahead_days: int = 180) -> Optional[dict]:
    """The next eclipse actually visible from this location within the
    lookahead window, or None. Checks both lunar and solar eclipses and
    returns whichever comes first; each type is searched up to 4 events
    ahead before giving up, since most eclipses in a given 1-2 year window
    aren't visible from any single location.
    """
    now_utc = datetime.now(dt_timezone.utc)
    jd_start = swe.julday(now_utc.year, now_utc.month, now_utc.day, 0.0)
    geopos = (lon, lat, 0.0)
    horizon_jd = jd_start + lookahead_days

    candidates = []

    search_jd = jd_start
    for _ in range(4):
        try:
            ret, times = swe.lun_eclipse_when(search_jd, swe.FLG_MOSEPH)
        except Exception:
            break
        max_jd = times[0]
        if max_jd > horizon_jd:
            break
        how = swe.lun_eclipse_how(max_jd, geopos, swe.FLG_MOSEPH)
        if how[0] & swe.ECL_VISIBLE:
            kind = ("Total" if ret & swe.ECL_TOTAL else
                    "Partial" if ret & swe.ECL_PARTIAL else "Penumbral")
            candidates.append({
                "type": "lunar", "kind": kind, "jd": max_jd,
                "name": f"{kind} Lunar Eclipse (Chandra Grahan)",
            })
            break
        search_jd = max_jd + 1

    search_jd = jd_start
    for _ in range(4):
        try:
            ret, times = swe.sol_eclipse_when_glob(search_jd, swe.FLG_MOSEPH)
        except Exception:
            break
        max_jd = times[0]
        if max_jd > horizon_jd:
            break
        how = swe.sol_eclipse_how(max_jd, geopos, swe.FLG_MOSEPH)
        if how[0] & swe.ECL_VISIBLE:
            kind = ("Total" if ret & swe.ECL_TOTAL else
                    "Annular" if ret & swe.ECL_ANNULAR else "Partial")
            candidates.append({
                "type": "solar", "kind": kind, "jd": max_jd,
                "name": f"{kind} Solar Eclipse (Surya Grahan)",
            })
            break
        search_jd = max_jd + 1

    if not candidates:
        return None

    nearest = min(candidates, key=lambda c: c["jd"])
    local_dt = _jd_to_local(nearest["jd"], tz_name)
    return {
        "type": nearest["type"],
        "kind": nearest["kind"],
        "name": nearest["name"],
        "date": local_dt.strftime("%d %b %Y") if local_dt else None,
        "peak_time_local": _fmt(local_dt),
        # Sutak timing and do/avoid guidance are deliberately not computed
        # here — see module docstring. The frontend should treat their
        # absence as "pending content review", not render blank fields.
    }
