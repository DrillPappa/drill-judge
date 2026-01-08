from pydantic import BaseModel, Field
from typing import List, Literal

# Orsaker till avdrag (kontrollerade värden)
DeductionReason = Literal[
    "tapp",
    "stort_missat_moment",
    "osynk_tajming",
    "stegfel",
    "annan"
]

class Deduction(BaseModel):
    reason: DeductionReason
    points: int = Field(description="Negativt heltal, t.ex. -2")
    time: str = Field(description="Tidsstämpel, t.ex. 01:24")

class CategoryScores(BaseModel):
    teknik: int = Field(ge=0, le=10)
    utforande: int = Field(ge=0, le=10)
    koreografi_svarighet: int = Field(ge=0, le=10)
    musikalitet_tajming: int = Field(ge=0, le=5)
    scennarvaro_helhet: int = Field(ge=0, le=5)

class JudgeResult(BaseModel):
    total: int
    categories: CategoryScores
    deductions: List[Deduction]
    key_observations: List[str] = Field(
        description="Korta, konkreta observationer"
    )
    training_focus_next_2_weeks: List[str] = Field(
        description="3–6 träningspunkter"
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Hur säker bedömningen är baserat på videokvalitet"
    )
