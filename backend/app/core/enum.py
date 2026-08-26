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


class ValidatorFamily(str, Enum):
    Lexical = "lexical"
    Classifier = "classifier"
    Semantic = "semantic"


# Family of each validator type: lexical = word/pattern matching,
# classifier = local ML model, semantic = makes a real LLM call.
VALIDATOR_FAMILY: dict[str, ValidatorFamily] = {
    ValidatorType.LexicalSlur.value: ValidatorFamily.Lexical,
    ValidatorType.BanList.value: ValidatorFamily.Lexical,
    ValidatorType.ProfanityFree.value: ValidatorFamily.Lexical,
    ValidatorType.PIIRemover.value: ValidatorFamily.Classifier,
    ValidatorType.GenderAssumptionBias.value: ValidatorFamily.Classifier,
    ValidatorType.LlamaGuard7B.value: ValidatorFamily.Classifier,
    ValidatorType.NSFWText.value: ValidatorFamily.Classifier,
    ValidatorType.TopicRelevance.value: ValidatorFamily.Semantic,
    ValidatorType.TopicRelevanceLLM.value: ValidatorFamily.Semantic,
    ValidatorType.LLMCritic.value: ValidatorFamily.Semantic,
    ValidatorType.AnswerRelevanceCustomLLM.value: ValidatorFamily.Semantic,
}
