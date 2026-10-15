from enum import Enum


class LLMValidatorName(str, Enum):
    TopicRelevance = "topic_relevance"
    AnswerRelevanceCustomLLM = "answer_relevance_custom_llm"


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


class PIIEntityType(str, Enum):
    CreditCard = "CREDIT_CARD"
    EmailAddress = "EMAIL_ADDRESS"
    IbanCode = "IBAN_CODE"
    IpAddress = "IP_ADDRESS"
    Location = "LOCATION"
    MedicalLicense = "MEDICAL_LICENSE"
    Nrp = "NRP"
    Person = "PERSON"
    PhoneNumber = "PHONE_NUMBER"
    Url = "URL"
    InAadhaar = "IN_AADHAAR"
    InPan = "IN_PAN"
    InPassport = "IN_PASSPORT"
    InVehicleRegistration = "IN_VEHICLE_REGISTRATION"
    InVoter = "IN_VOTER"


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
    TopicRelevance = "topic_relevance"
    TopicRelevanceLLM = "topic_relevance_llm"
    LLMCritic = "llm_critic"
    LlamaGuard7B = "llamaguard_7b"
    ProfanityFree = "profanity_free"
    NSFWText = "nsfw_text"
    AnswerRelevanceCustomLLM = "answer_relevance_custom_llm"
    ContentSafety = "content_safety"
