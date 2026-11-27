"""Deterministic rule-based clinical information extractor.

Extracts structured clinical facts strictly from consultation transcripts using
sentence segmentation, speaker attribution, negation/uncertainty handling,
historical context detection, and regex/keyword rules. Never invents clinical facts.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from app.schemas.extraction import ClinicalExtractionPayload

Speaker = Literal["doctor", "patient", "unknown"]

_SPEAKER_LINE_RE = re.compile(
    r"^\s*(?P<label>doctor|dr\.?|clinician|physician|patient|pt\.?)\s*:\s*(?P<body>.*)$",
    re.IGNORECASE,
)

# Split sentences on . ! ? followed by whitespace, without splitting on decimals (99.8)
# or common abbreviations (Dr., Mr., Mrs., Ms., e.g., i.e., vs.).
_ABBREV_RE = re.compile(
    r"\b(?:Dr|Mr|Mrs|Ms|Prof|Sr|Jr|St|vs|etc|e\.g|i\.e)\.",
    re.IGNORECASE,
)
_SENTENCE_SPLIT_RE = re.compile(r"(?<!\d)(?<=[.!?])\s+(?=[A-Z0-9\"'(])|(?<=[.!?])\s*\n+")

_NEGATION_PREFIX_RE = re.compile(
    r"(?:\b(?:no|not|denies|denied|without|negative\s+for|absent|absence\s+of|"
    r"ruled\s+out|rules\s+out|never|neither|nor|no\s+history\s+of|no\s+known)\b)",
    re.IGNORECASE,
)

_UNCERTAINTY_RE = re.compile(
    r"\b(?:maybe|possibly|possible|probable|probably|likely|suspected|suspect|"
    r"unsure|not\s+sure|uncertain|might\s+be|could\s+be|may\s+be|rule\s+out|r/o|"
    r"differential|questionable|unclear|appears\s+to\s+be)\b|\?",
    re.IGNORECASE,
)

_HISTORICAL_RE = re.compile(
    r"\b(?:history\s+of|h/o|past\s+history|past\s+medical\s+history|pmh|"
    r"previously|in\s+the\s+past|years?\s+ago|months?\s+ago|childhood|"
    r"known\s+case\s+of|k/c/o|diagnosed\s+with|surgical\s+history|had\s+.+\s+before)\b",
    re.IGNORECASE,
)

_SYMPTOM_CATALOG: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\bdry\s+cough\b", re.IGNORECASE), "Dry cough"),
    (re.compile(r"\bproductive\s+cough\b|\bwet\s+cough\b", re.IGNORECASE), "Productive cough"),
    (re.compile(r"\bcough\b", re.IGNORECASE), "Cough"),
    (re.compile(r"\bmild\s+fever\b|\blow[- ]grade\s+fever\b", re.IGNORECASE), "Mild fever"),
    (re.compile(r"\bhigh\s+fever\b|\bhigh[- ]grade\s+fever\b", re.IGNORECASE), "High fever"),
    (re.compile(r"\bfever\b|\bpyrexia\b", re.IGNORECASE), "Fever"),
    (re.compile(r"\bsore\s+throat\b|\bthroat\s+pain\b", re.IGNORECASE), "Sore throat"),
    (re.compile(r"\bheadache\b|\bhead\s+ache\b", re.IGNORECASE), "Headache"),
    (re.compile(r"\bchest\s+pain\b|\bchest\s+tightness\b", re.IGNORECASE), "Chest pain"),
    (
        re.compile(
            r"\bshortness\s+of\s+breath\b|\bbreathing\s+trouble\b|\bdifficulty\s+breathing\b|\bdyspnea\b|\bbreathlessness\b",
            re.IGNORECASE,
        ),
        "Shortness of breath",
    ),
    (re.compile(r"\bwheezing\b", re.IGNORECASE), "Wheezing"),
    (re.compile(r"\bfatigue\b|\btiredness\b|\bexhaustion\b", re.IGNORECASE), "Fatigue"),
    (re.compile(r"\bweakness\b|\bmalaise\b", re.IGNORECASE), "Weakness"),
    (re.compile(r"\bdizziness\b|\blightheaded(?:ness)?\b|\bvertigo\b", re.IGNORECASE), "Dizziness"),
    (re.compile(r"\bnausea\b", re.IGNORECASE), "Nausea"),
    (re.compile(r"\bvomiting\b|\bemesis\b", re.IGNORECASE), "Vomiting"),
    (re.compile(r"\bdiarrhea\b|\bloose\s+(?:stools|motions)\b", re.IGNORECASE), "Diarrhea"),
    (re.compile(r"\babdominal\s+pain\b|\bstomach\s+(?:pain|ache)\b", re.IGNORECASE), "Abdominal pain"),
    (re.compile(r"\bback\s+pain\b", re.IGNORECASE), "Back pain"),
    (re.compile(r"\bjoint\s+pain\b|\barthralgia\b", re.IGNORECASE), "Joint pain"),
    (re.compile(r"\bbody\s+ache\b|\bbody\s+aches\b|\bmyalgia\b", re.IGNORECASE), "Body aches"),
    (re.compile(r"\brunny\s+nose\b|\brhinorrhea\b", re.IGNORECASE), "Runny nose"),
    (re.compile(r"\bnasal\s+congestion\b|\bstuffy\s+nose\b|\bblocked\s+nose\b", re.IGNORECASE), "Nasal congestion"),
    (re.compile(r"\bchills\b|\brigors\b", re.IGNORECASE), "Chills"),
    (re.compile(r"\bnight\s+sweats\b", re.IGNORECASE), "Night sweats"),
    (re.compile(r"\bpalpitations\b", re.IGNORECASE), "Palpitations"),
    (re.compile(r"\bswelling\b|\bedema\b", re.IGNORECASE), "Swelling"),
    (re.compile(r"\brash\b|\bitching\b|\bpruritus\b", re.IGNORECASE), "Rash / itching"),
    (re.compile(r"\bear\s+pain\b|\botalgia\b", re.IGNORECASE), "Ear pain"),
    (re.compile(r"\bburning\s+(?:micturition|urination)\b|\bdysuria\b", re.IGNORECASE), "Burning urination"),
    (re.compile(r"\bloss\s+of\s+appetite\b|\banorexia\b", re.IGNORECASE), "Loss of appetite"),
    (re.compile(r"\binsomnia\b|\bdifficulty\s+sleeping\b", re.IGNORECASE), "Difficulty sleeping"),
]

_DURATION_RE = re.compile(
    r"(?:\b(?:for|since|over)\s+(?:the\s+)?(?:past|last)?\s*"
    r"(?:(?:\d+|one|two|three|four|five|six|seven|eight|nine|ten|a\s+few|several)\s+"
    r"(?:hours?|hrs?|days?|weeks?|months?|years?))|"
    r"\bsince\s+(?:yesterday|last\s+night|this\s+morning|monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b)",
    re.IGNORECASE,
)

_SEVERITY_RE = re.compile(
    r"\b(?:mild|moderate|severe|intense|worsening|worse\s+at\s+night|worse\s+in\s+the\s+morning|"
    r"intermittent|constant|persistent|progressive)\b|\b\d{1,2}\s*/\s*10\b",
    re.IGNORECASE,
)

_HISTORY_CONDITIONS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\bhypertension\b|\bhigh\s+blood\s+pressure\b|\bhtn\b", re.IGNORECASE), "Hypertension"),
    (re.compile(r"\bdiabetes(?:\s+mellitus)?\b|\bt2dm\b|\bt1dm\b|\bsugar\b", re.IGNORECASE), "Diabetes mellitus"),
    (re.compile(r"\basthma\b", re.IGNORECASE), "Asthma"),
    (re.compile(r"\bcopd\b", re.IGNORECASE), "COPD"),
    (re.compile(r"\bhypothyroid(?:ism)?\b|\bthyroid\b", re.IGNORECASE), "Thyroid disorder"),
    (re.compile(r"\bcoronary\s+artery\s+disease\b|\bcad\b|\bheart\s+disease\b", re.IGNORECASE), "Heart disease"),
    (re.compile(r"\bstroke\b|\bcva\b", re.IGNORECASE), "Stroke"),
    (re.compile(r"\bmigraine\b", re.IGNORECASE), "Migraine"),
    (re.compile(r"\btuberculosis\b|\btb\b", re.IGNORECASE), "Tuberculosis"),
    (re.compile(r"\bkidney\s+disease\b|\bckd\b", re.IGNORECASE), "Kidney disease"),
    (re.compile(r"\bgerd\b|\bacid\s+reflux\b|\bgastritis\b", re.IGNORECASE), "GERD / gastritis"),
]

_LIFESTYLE_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\bsmok(?:e|es|ing|er)\b", re.IGNORECASE), "Smoking status mentioned"),
    (re.compile(r"\balcohol\b|\bdrink(?:s|ing)?\b", re.IGNORECASE), "Alcohol use mentioned"),
    (re.compile(r"\bexercise\b|\bwalk(?:s|ing)?\b|\bsedentary\b", re.IGNORECASE), "Physical activity mentioned"),
    (re.compile(r"\bdiet\b|\bvegetarian\b|\bnon[- ]veg\b|\bsalt\b", re.IGNORECASE), "Dietary habits mentioned"),
]

_EXAM_CUE_RE = re.compile(
    r"\b(?:on\s+examination|o/e|physical\s+exam(?:ination)?|exam(?:ination)?\s+shows|"
    r"auscultation|palpation|percussion|throat\s+is|chest\s+is|lungs\s+(?:are|clear)|"
    r"heart\s+sounds|abdomen\s+is|tenderness|erythema|congested|rales|crackles|"
    r"wheeze|murmur|edema|no\s+pallor|no\s+icterus|no\s+cyanosis|no\s+lymphadenopathy)\b",
    re.IGNORECASE,
)

_ASSESSMENT_CUE_RE = re.compile(
    r"\b(?:assessment|impression|diagnosis|diagnoses|working\s+diagnosis|"
    r"consistent\s+with|viral\s+(?:upper\s+respiratory|fever|uri|urti|infection)|"
    r"bacterial\s+infection|acute\s+\w+|essential\s+hypertension|gastritis|"
    r"pharyngitis|bronchitis|pneumonia|migraine|urinary\s+tract\s+infection|uti)\b",
    re.IGNORECASE,
)

_DIFF_DX_RE = re.compile(
    r"\b(?:differential(?:\s+diagnos(?:is|es))?|ddx|rule\s+out|r/o|versus)\b",
    re.IGNORECASE,
)

_MED_INSTRUCTION_CUE_RE = re.compile(
    r"\b(?:\d+\s*(?:mg|mcg|g|ml|iu)\b|tablet|tab\.?|capsule|cap\.?|syrup|drops|inhaler|"
    r"once\s+daily|twice\s+daily|thrice\s+daily|\bod\b|\bbd\b|\btds\b|\bqid\b|\bsos\b|\bprn\b|\bhs\b|"
    r"prescribe|paracetamol|acetaminophen|ibuprofen|amoxicillin|azithromycin|cetirizine|"
    r"pantoprazole|omeprazole|metformin|amlodipine|atorvastatin|salbutamol|levocetirizine)\b",
    re.IGNORECASE,
)

_CURRENT_MED_CUE_RE = re.compile(
    r"\b(?:currently\s+taking|taking|on\s+regular|already\s+on|home\s+medications?|"
    r"been\s+taking|uses?\s+(?:inhaler|insulin|tablets?))\b",
    re.IGNORECASE,
)

_INVESTIGATION_CUE_RE = re.compile(
    r"\b(?:cbc|complete\s+blood\s+count|blood\s+test|x[- ]?ray|chest\s+x[- ]?ray|"
    r"ecg|ekg|ultrasound|usg|ct\s+scan|mri|urinalysis|urine\s+test|lipid\s+profile|"
    r"hba1c|lft|rft|kft|tsh|thyroid\s+profile|blood\s+sugar|fbs|rbs|ppbs|culture|swab)\b",
    re.IGNORECASE,
)

_PLAN_CUE_RE = re.compile(
    r"\b(?:plan\s*:|gargles?|hydration|plenty\s+of\s+fluids|oral\s+fluids|rest|"
    r"steam\s+inhalation|low[- ]salt\s+diet|dietary|avoid\s+|warm\s+compress|"
    r"monitor\s+(?:bp|blood\s+pressure|sugar|temperature)|home\s+bp)\b",
    re.IGNORECASE,
)

_FOLLOW_UP_CUE_RE = re.compile(
    r"\b(?:follow[- ]?up|review\s+in|return\s+in|come\s+back|revisit|"
    r"if\s+(?:fever|symptoms?)\s+(?:persists?|worsens?|does\s+not\s+improve))\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class Segment:
    text: str
    speaker: Speaker
    is_uncertain: bool
    is_historical: bool


def _append_unique(target: list[str], item: str) -> None:
    cleaned = item.strip()
    if not cleaned:
        return
    lowered = cleaned.lower()
    if not any(existing.lower() == lowered for existing in target):
        target.append(cleaned)


def _clip_evidence(text: str, max_len: int = 180) -> str:
    cleaned = re.sub(r"\s+", " ", text).strip()
    if len(cleaned) <= max_len:
        return cleaned
    return cleaned[: max_len - 3].rstrip() + "..."


def _record_evidence(evidence: dict[str, str], key: str, text: str) -> None:
    if key not in evidence and text.strip():
        evidence[key] = _clip_evidence(text)


def _split_sentences(body: str) -> list[str]:
    # Temporarily mask abbreviations so we don't split inside "Dr. Smith"
    placeholders: dict[str, str] = {}

    def _mask(match: re.Match[str]) -> str:
        token = f"__ABBR_{len(placeholders)}__"
        placeholders[token] = match.group(0)
        return token

    masked = _ABBREV_RE.sub(_mask, body.strip())
    parts = [p.strip() for p in _SENTENCE_SPLIT_RE.split(masked) if p.strip()]
    restored: list[str] = []
    for part in parts:
        for token, orig in placeholders.items():
            part = part.replace(token, orig)
        restored.append(part)
    return restored


def segment_transcript(transcript_text: str) -> tuple[list[Segment], bool]:
    """Segment transcript into speaker-attributed sentences.

    Returns (segments, has_explicit_speakers).
    """
    segments: list[Segment] = []
    has_explicit_speakers = False

    for raw_line in transcript_text.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        speaker: Speaker = "unknown"
        body = line
        match = _SPEAKER_LINE_RE.match(line)
        if match:
            has_explicit_speakers = True
            label = match.group("label").lower().rstrip(".")
            speaker = "doctor" if label in {"doctor", "dr", "clinician", "physician"} else "patient"
            body = match.group("body").strip()

        if not body:
            continue

        for sentence in _split_sentences(body):
            segments.append(
                Segment(
                    text=sentence,
                    speaker=speaker,
                    is_uncertain=bool(_UNCERTAINTY_RE.search(sentence)),
                    is_historical=bool(_HISTORICAL_RE.search(sentence)),
                )
            )

    return segments, has_explicit_speakers


def _is_term_negated(sentence: str, match_start: int) -> bool:
    """Determine whether a matched term at `match_start` is negated in its local clause."""
    prefix = sentence[:match_start]
    # Limit scope to the current clause; allow "or" / "," inside a negated list like "no chest pain or fever"
    clause_breaks = [
        prefix.rfind(";"),
        prefix.rfind(" but "),
        prefix.rfind(" however "),
        prefix.rfind(" except "),
    ]
    last_break = max(clause_breaks)
    if last_break != -1:
        prefix = prefix[last_break + 1 :]
    return bool(_NEGATION_PREFIX_RE.search(prefix))


def _extract_vitals(sentence: str, vitals: dict[str, str], evidence: dict[str, str]) -> None:
    temp_match = re.search(
        r"\b(?:temp(?:erature)?)\s*(?:is|of|:|=)?\s*(\d{2,3}(?:\.\d+)?)\s*(?:°?\s*([FC])|deg(?:rees?)?\s*([FC])|(fahrenheit|celsius))?\b",
        sentence,
        re.IGNORECASE,
    )
    if temp_match:
        val = temp_match.group(1)
        unit_raw = temp_match.group(2) or temp_match.group(3) or temp_match.group(4) or ""
        unit = "F" if unit_raw.lower().startswith("f") else ("C" if unit_raw.lower().startswith("c") else "")
        if not unit:
            unit = "F" if float(val) > 45 else "C"
        vitals["Temperature"] = f"{val} {unit}"
        _record_evidence(evidence, "vitals", sentence)

    bp_match = re.search(
        r"\b(?:bp|blood\s+pressure)\s*(?:is|of|:|=)?\s*(\d{2,3}\s*/\s*\d{2,3})(?:\s*(mmhg))?\b",
        sentence,
        re.IGNORECASE,
    )
    if bp_match:
        bp_val = re.sub(r"\s+", "", bp_match.group(1))
        vitals["BP"] = f"{bp_val} mmHg"
        _record_evidence(evidence, "vitals", sentence)

    hr_match = re.search(
        r"\b(?:hr|heart\s+rate|pulse)\s*(?:is|of|:|=)?\s*(\d{2,3})\s*(?:bpm|/min|beats\s+per\s+minute)?\b",
        sentence,
        re.IGNORECASE,
    )
    if hr_match:
        vitals["Heart Rate"] = f"{hr_match.group(1)} bpm"
        _record_evidence(evidence, "vitals", sentence)

    spo2_match = re.search(
        r"\b(?:spo2|o2\s*sat|oxygen\s+saturation|saturation)\s*(?:is|of|:|=)?\s*(\d{2,3})\s*(?:%|percent)(\s+on\s+room\s+air)?\b",
        sentence,
        re.IGNORECASE,
    )
    if spo2_match:
        room_air = " on room air" if spo2_match.group(2) else ""
        vitals["SpO2"] = f"{spo2_match.group(1)}%{room_air}"
        _record_evidence(evidence, "vitals", sentence)

    rr_match = re.search(
        r"\b(?:rr|respiratory\s+rate)\s*(?:is|of|:|=)?\s*(\d{1,2})\s*(?:/min|breaths/min)?\b",
        sentence,
        re.IGNORECASE,
    )
    if rr_match:
        vitals["Respiratory Rate"] = f"{rr_match.group(1)} /min"
        _record_evidence(evidence, "vitals", sentence)

    wt_match = re.search(
        r"\b(?:weight|wt)\s*(?:is|of|:|=)?\s*(\d{2,3}(?:\.\d+)?)\s*(kg|lbs)\b",
        sentence,
        re.IGNORECASE,
    )
    if wt_match:
        vitals["Weight"] = f"{wt_match.group(1)} {wt_match.group(2).lower()}"
        _record_evidence(evidence, "vitals", sentence)


def _extract_allergies(sentence: str, allergies: list[str], evidence: dict[str, str], speaker: Speaker) -> None:
    lower = sentence.lower()
    if "allerg" not in lower and "nkda" not in lower:
        return
    # Skip pure doctor questions like "Any known drug allergies?"
    if sentence.strip().endswith("?") and speaker == "doctor":
        return

    if re.search(r"\b(?:no\s+known(?:\s+drug)?\s+allergies|no\s+drug\s+allergies|no\s+allergies|nkda|denies\s+allergies)\b", lower):
        suffix = " (patient stated)" if speaker == "patient" else ""
        _append_unique(allergies, f"No known allergies{suffix}")
        _record_evidence(evidence, "allergies", sentence)
        return

    match = re.search(r"\ballergic\s+to\s+([^.;,]+)", sentence, re.IGNORECASE)
    if match:
        allergen = match.group(1).strip()
        _append_unique(allergies, f"Allergic to {allergen}")
        _record_evidence(evidence, "allergies", sentence)
        return

    match = re.search(r"\ballerg(?:y|ies)\s*(?::|to|include)?\s*([^.;]+)", sentence, re.IGNORECASE)
    if match and not sentence.strip().endswith("?"):
        detail = match.group(1).strip()
        if detail and len(detail) > 2:
            _append_unique(allergies, detail)
            _record_evidence(evidence, "allergies", sentence)


def _extract_symptoms_and_negatives(
    seg: Segment,
    symptoms: list[str],
    other_observations: list[str],
    evidence: dict[str, str],
) -> None:
    text = seg.text
    # Skip doctor's screening questions, plan/medication instructions, and assessment lines
    if seg.speaker == "doctor" and (
        text.strip().endswith("?")
        or _PLAN_CUE_RE.search(text)
        or _MED_INSTRUCTION_CUE_RE.search(text)
        or _ASSESSMENT_CUE_RE.search(text)
    ):
        return

    matched_spans: list[tuple[int, int]] = []
    for pattern, label in _SYMPTOM_CATALOG:
        for m in pattern.finditer(text):
            # Avoid double-counting "cough" inside "dry cough" or "fever" inside "mild fever"
            if any(m.start() >= s and m.end() <= e for s, e in matched_spans):
                continue
            matched_spans.append((m.start(), m.end()))

            if _is_term_negated(text, m.start()):
                _append_unique(other_observations, f"Pertinent negative: No {label.lower()}")
                _record_evidence(evidence, "pertinent_negatives", text)
            elif seg.is_historical:
                # Historical symptoms belong in medical history, not active symptoms
                continue
            else:
                formatted = f"Possible {label.lower()} (uncertain)" if seg.is_uncertain else label
                _append_unique(symptoms, formatted)
                _record_evidence(evidence, "symptoms", text)


def _extract_history(
    seg: Segment,
    medical_history: list[str],
    lifestyle_info: list[str],
    evidence: dict[str, str],
) -> None:
    text = seg.text
    if text.strip().endswith("?") and seg.speaker == "doctor":
        return

    if seg.is_historical or seg.speaker in {"patient", "unknown"}:
        for pattern, label in _HISTORY_CONDITIONS:
            m = pattern.search(text)
            if m and not _is_term_negated(text, m.start()):
                if seg.is_historical or "known case" in text.lower() or "diagnosed" in text.lower():
                    _append_unique(medical_history, label)
                    _record_evidence(evidence, "medical_history", text)

    for pattern, _label in _LIFESTYLE_PATTERNS:
        m = pattern.search(text)
        if m and not text.strip().endswith("?"):
            _append_unique(lifestyle_info, _clip_evidence(text, 120))
            _record_evidence(evidence, "lifestyle_info", text)
            break


def _extract_clinical_sections(
    seg: Segment,
    medications: list[str],
    examination_findings: list[str],
    assessment: list[str],
    differential_diagnoses: list[str],
    plan: list[str],
    medication_instructions: list[str],
    investigations: list[str],
    follow_up_parts: list[str],
    evidence: dict[str, str],
) -> None:
    text = seg.text
    lower = text.lower()

    # Examination findings (doctor-stated or explicit exam cues)
    if _EXAM_CUE_RE.search(text) and seg.speaker != "patient":
        cleaned = re.sub(r"^(?:on\s+examination|o/e|physical\s+exam(?:ination)?)\s*[:,]?\s*", "", text, flags=re.IGNORECASE).strip()
        if cleaned:
            _append_unique(examination_findings, cleaned)
            _record_evidence(evidence, "examination_findings", text)

    # Differential diagnoses
    if _DIFF_DX_RE.search(text) and seg.speaker != "patient":
        cleaned = re.sub(r"^(?:differential\s+diagnos(?:is|es)|ddx)\s*[:,]?\s*", "", text, flags=re.IGNORECASE).strip()
        if cleaned:
            _append_unique(differential_diagnoses, cleaned)
            _record_evidence(evidence, "differential_diagnoses", text)

    # Assessment
    elif _ASSESSMENT_CUE_RE.search(text) and seg.speaker != "patient" and not _DIFF_DX_RE.search(text):
        # Split if "Assessment: ... Plan: ..." are in the same sentence
        assess_segment = re.split(r"\bplan\s*:", text, maxsplit=1, flags=re.IGNORECASE)[0]
        cleaned = re.sub(
            r"^(?:assessment|impression|working\s+diagnosis|diagnosis)\s*(?:is|:)?\s*",
            "",
            assess_segment,
            flags=re.IGNORECASE,
        ).strip(" .")
        if cleaned:
            tag = " (doctor stated)" if seg.speaker == "doctor" else ""
            _append_unique(assessment, f"{cleaned}{tag}")
            _record_evidence(evidence, "assessment", assess_segment)

    # Current/past medications vs newly prescribed medication instructions
    if _MED_INSTRUCTION_CUE_RE.search(text):
        if _CURRENT_MED_CUE_RE.search(text) or seg.speaker == "patient":
            if not _is_term_negated(text, _MED_INSTRUCTION_CUE_RE.search(text).start()):  # type: ignore[union-attr]
                _append_unique(medications, _clip_evidence(text, 140))
                _record_evidence(evidence, "medications", text)
        else:
            # Extract from "Plan: ..." if prefixed
            med_segment = re.sub(r"^(?:plan|medications?|rx)\s*:\s*", "", text, flags=re.IGNORECASE).strip()
            if med_segment:
                _append_unique(medication_instructions, med_segment)
                _record_evidence(evidence, "medication_instructions", text)

    # Investigations
    if _INVESTIGATION_CUE_RE.search(text) and seg.speaker != "patient":
        _append_unique(investigations, _clip_evidence(text, 140))
        _record_evidence(evidence, "investigations", text)

    # Plan (non-medication care instructions)
    if _PLAN_CUE_RE.search(text) and seg.speaker != "patient":
        plan_segment = re.sub(r"^plan\s*:\s*", "", text, flags=re.IGNORECASE).strip()
        # If this sentence also contains medication instructions, keep care advice without duplicating pure med line
        if plan_segment and not (
            _MED_INSTRUCTION_CUE_RE.search(plan_segment)
            and not any(kw in lower for kw in ("gargle", "fluid", "hydration", "rest", "diet", "steam", "monitor", "avoid"))
        ):
            _append_unique(plan, plan_segment)
            _record_evidence(evidence, "plan", text)

    # Follow-up
    if _FOLLOW_UP_CUE_RE.search(text) and seg.speaker != "patient":
        fu_segment = re.sub(r"^(?:follow[- ]?up)\s*:\s*", "", text, flags=re.IGNORECASE).strip()
        if fu_segment:
            _append_unique(follow_up_parts, fu_segment)
            _record_evidence(evidence, "follow_up", text)


def _compute_missing_and_ambiguities(
    payload: ClinicalExtractionPayload,
    has_explicit_speakers: bool,
    uncertain_segments: list[Segment],
) -> list[str]:
    missing: list[str] = []
    checks = [
        (not payload.chief_complaint and not payload.symptoms, "Chief complaint or symptoms not documented"),
        (not payload.vitals, "Vitals not documented"),
        (not payload.examination_findings, "Physical examination findings not documented"),
        (not payload.allergies, "Allergies not mentioned or asked"),
        (not payload.assessment, "Clinical assessment not explicitly documented"),
        (not payload.plan and not payload.medication_instructions, "Treatment plan not explicitly documented"),
        (not payload.follow_up, "Follow-up instructions not stated"),
    ]
    for condition, label in checks:
        if condition:
            _append_unique(missing, label)

    if not has_explicit_speakers and (payload.symptoms or payload.assessment or payload.plan):
        _append_unique(
            missing,
            "Speaker attribution not explicitly labeled in transcript; verify patient vs. doctor statements",
        )

    for seg in uncertain_segments:
        if _DURATION_RE.search(seg.text) or "duration" in seg.text.lower():
            _append_unique(missing, "Symptom duration noted as uncertain; verify with patient")
            break

    return missing


def extract_with_rules(transcript_text: str) -> ClinicalExtractionPayload:
    """Extract structured clinical information deterministically from a transcript."""
    cleaned_transcript = (transcript_text or "").strip()
    if not cleaned_transcript:
        return ClinicalExtractionPayload(
            missing_information=["Transcript is empty; no clinical facts could be extracted."]
        )

    segments, has_explicit_speakers = segment_transcript(cleaned_transcript)

    symptoms: list[str] = []
    durations: list[str] = []
    severities: list[str] = []
    medical_history: list[str] = []
    medications: list[str] = []
    allergies: list[str] = []
    lifestyle_info: list[str] = []
    vitals: dict[str, str] = {}
    examination_findings: list[str] = []
    other_observations: list[str] = []
    assessment: list[str] = []
    differential_diagnoses: list[str] = []
    plan: list[str] = []
    medication_instructions: list[str] = []
    investigations: list[str] = []
    follow_up_parts: list[str] = []
    evidence_quotes: dict[str, str] = {}
    uncertain_segments: list[Segment] = []

    for seg in segments:
        if seg.is_uncertain:
            uncertain_segments.append(seg)

        _extract_vitals(seg.text, vitals, evidence_quotes)
        _extract_allergies(seg.text, allergies, evidence_quotes, seg.speaker)
        _extract_symptoms_and_negatives(seg, symptoms, other_observations, evidence_quotes)
        _extract_history(seg, medical_history, lifestyle_info, evidence_quotes)

        # Duration & severity from patient-reported or unlabelled symptom statements
        if seg.speaker != "doctor" or not has_explicit_speakers:
            for dm in _DURATION_RE.finditer(seg.text):
                dur_val = dm.group(0).strip()
                if seg.is_uncertain:
                    dur_val = f"{dur_val} (uncertain)"
                _append_unique(durations, dur_val)
                _record_evidence(evidence_quotes, "symptom_duration", seg.text)

            for sm in _SEVERITY_RE.finditer(seg.text):
                _append_unique(severities, sm.group(0).strip().capitalize())
                _record_evidence(evidence_quotes, "symptom_severity", seg.text)

        _extract_clinical_sections(
            seg=seg,
            medications=medications,
            examination_findings=examination_findings,
            assessment=assessment,
            differential_diagnoses=differential_diagnoses,
            plan=plan,
            medication_instructions=medication_instructions,
            investigations=investigations,
            follow_up_parts=follow_up_parts,
            evidence=evidence_quotes,
        )

    chief_complaint: str | None = None
    if symptoms:
        chief_complaint = ", ".join(symptoms[:2])
        if "symptoms" in evidence_quotes:
            evidence_quotes.setdefault("chief_complaint", evidence_quotes["symptoms"])

    payload = ClinicalExtractionPayload(
        chief_complaint=chief_complaint,
        symptoms=symptoms,
        symptom_duration="; ".join(durations) if durations else None,
        symptom_severity="; ".join(severities) if severities else None,
        medical_history=medical_history,
        medications=medications,
        allergies=allergies,
        lifestyle_info=lifestyle_info,
        vitals=vitals,
        examination_findings=examination_findings,
        other_observations=other_observations,
        assessment=assessment,
        differential_diagnoses=differential_diagnoses,
        plan=plan,
        medication_instructions=medication_instructions,
        investigations=investigations,
        follow_up="; ".join(follow_up_parts) if follow_up_parts else None,
        evidence_quotes=evidence_quotes,
    )
    payload.missing_information = _compute_missing_and_ambiguities(
        payload, has_explicit_speakers=has_explicit_speakers, uncertain_segments=uncertain_segments
    )
    return payload
