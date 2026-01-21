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