from enum import Enum


class SlurSeverity(Enum):
    Low = "low"
    Medium = "medium"
    High = "high"
    All = "all"


class BiasCategories(Enum):
    Generic = "generic"
    Healthcare = "healthcare"
    Education = "education"
    All = "all"


class GuardrailOnFail(Enum):
    Exception = "exception"
    Fix = "fix"
    Rephrase = "rephrase"


class Stage(Enum):
    Input = "input"
    Output = "output"


class ValidatorType(Enum):
    LexicalSlur = "uli_slur_match"
    PIIRemover = "pii_remover"
    GenderAssumptionBias = "gender_assumption_bias"
    BanList = "ban_list"
