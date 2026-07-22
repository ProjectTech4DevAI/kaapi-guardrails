from __future__ import annotations
import os
from collections.abc import Callable
from typing import Optional

from guardrails import OnFailAction
from guardrails.validators import (
    FailResult,
    PassResult,
    register_validator,
    ValidationResult,
    Validator,
)
from presidio_analyzer import AnalyzerEngine, EntityRecognizer, RecognizerResult
from presidio_analyzer.nlp_engine import NlpEngineProvider, SpacyNlpEngine
from presidio_anonymizer import AnonymizerEngine
from presidio_analyzer.predefined_recognizers.country_specific.india.in_aadhaar_recognizer import (
    InAadhaarRecognizer,
)
from presidio_analyzer.predefined_recognizers.country_specific.india.in_pan_recognizer import (
    InPanRecognizer,
)
from presidio_analyzer.predefined_recognizers.country_specific.india.in_passport_recognizer import (
    InPassportRecognizer,
)
from presidio_analyzer.predefined_recognizers.country_specific.india.in_vehicle_registration_recognizer import (
    InVehicleRegistrationRecognizer,
)
from presidio_analyzer.predefined_recognizers.country_specific.india.in_voter_recognizer import (
    InVoterRecognizer,
)

os.environ["TOKENIZERS_PARALLELISM"] = "false"

ALL_ENTITY_TYPES = [
    "CREDIT_CARD",
    "EMAIL_ADDRESS",
    "IBAN_CODE",
    "IP_ADDRESS",
    "LOCATION",
    "MEDICAL_LICENSE",
    "NRP",
    "PERSON",
    "PHONE_NUMBER",
    "URL",
    "IN_AADHAAR",
    "IN_PAN",
    "IN_PASSPORT",
    "IN_VEHICLE_REGISTRATION",
    "IN_VOTER",
]

SPACY_CONFIGURATION = {
    "nlp_engine_name": "spacy",
    "models": [{"lang_code": "en", "model_name": "en_core_web_lg"}],
}

# Lightweight spaCy model used only for tokenization when the transformers engine handles NER
SPACY_TOKENIZER_CONFIGURATION = {
    "nlp_engine_name": "spacy",
    "models": [{"lang_code": "en", "model_name": "en_core_web_sm"}],
}

# Shared label mapping for models using CoNLL-style PER/ORG/LOC/MISC labels
# (e.g. dslim/bert-base-NER, Davlan/xlm-roberta-base-ner-hrl)
CONLL_NER_LABEL_MAPPING = {
    "PER": "PERSON",
    "ORG": "ORGANIZATION",
    "LOC": "LOCATION",
    "MISC": "MISC",
}

DEFAULT_TRANSFORMERS_MODEL = "Davlan/bert-base-multilingual-cased-ner-hrl"
DEFAULT_TRANSFORMERS_THRESHOLD = 0.7

_NLP_ENGINE_CACHE: dict = {}
_ANALYZER_CACHE: dict = {}


INDIA_RECOGNIZERS = {
    "IN_AADHAAR": InAadhaarRecognizer,
    "IN_PAN": InPanRecognizer,
    "IN_PASSPORT": InPassportRecognizer,
    "IN_VEHICLE_REGISTRATION": InVehicleRegistrationRecognizer,
    "IN_VOTER": InVoterRecognizer,
}


class HuggingFaceNERRecognizer(EntityRecognizer):
    """Presidio EntityRecognizer backed by a HuggingFace token-classification pipeline."""

    def __init__(self, model_name: str, label_mapping: dict[str, str], threshold: float = 0.5):
        supported_entities = list(set(label_mapping.values()))
        super().__init__(supported_entities=supported_entities, name="HuggingFaceNERRecognizer")
        from transformers import pipeline as hf_pipeline

        self.ner_pipeline = hf_pipeline(
            "token-classification",
            model=model_name,
            aggregation_strategy="simple",
        )
        self.label_mapping = label_mapping
        self.threshold = threshold

    def load(self) -> None:
        pass

    def analyze(self, text: str, entities: list[str], nlp_artifacts=None) -> list[RecognizerResult]:
        results: list[RecognizerResult] = []
        for ent in self.ner_pipeline(text):
            presidio_label = self.label_mapping.get(ent["entity_group"])
            if presidio_label is None or presidio_label not in entities:
                continue
            if ent["score"] < self.threshold:
                continue
            results.append(
                RecognizerResult(
                    entity_type=presidio_label,
                    start=ent["start"],
                    end=ent["end"],
                    score=float(ent["score"]),
                )
            )
        return results


def _build_spacy_engine(configuration: dict) -> SpacyNlpEngine:
    provider = NlpEngineProvider(nlp_configuration=configuration)
    return provider.create_engine()  # type: ignore[return-value]


def _build_analyzer(
    entity_types: list[str], nlp_engine_type: str, model_name: str, threshold: float
) -> AnalyzerEngine:
    if nlp_engine_type == "transformers":
        # Use en_core_web_sm only for tokenization; BERT handles NER
        if "spacy_tokenizer_engine" not in _NLP_ENGINE_CACHE:
            _NLP_ENGINE_CACHE["spacy_tokenizer_engine"] = _build_spacy_engine(SPACY_TOKENIZER_CONFIGURATION)
        nlp_engine = _NLP_ENGINE_CACHE["spacy_tokenizer_engine"]
    else:
        if "spacy_engine" not in _NLP_ENGINE_CACHE:
            _NLP_ENGINE_CACHE["spacy_engine"] = _build_spacy_engine(SPACY_CONFIGURATION)
        nlp_engine = _NLP_ENGINE_CACHE["spacy_engine"]

    analyzer = AnalyzerEngine(nlp_engine=nlp_engine)

    if nlp_engine_type == "transformers":
        # Remove SpacyRecognizer so spaCy NER doesn't run alongside BERT
        analyzer.registry.remove_recognizer("SpacyRecognizer")

        hf_recognizer_key = ("hf_recognizer", model_name)
        if hf_recognizer_key not in _NLP_ENGINE_CACHE:
            _NLP_ENGINE_CACHE[hf_recognizer_key] = HuggingFaceNERRecognizer(
                model_name=model_name,
                label_mapping=CONLL_NER_LABEL_MAPPING,
                threshold=threshold,
            )
        analyzer.registry.add_recognizer(_NLP_ENGINE_CACHE[hf_recognizer_key])

    for entity_type, recognizer_cls in INDIA_RECOGNIZERS.items():
        if entity_type in entity_types:
            analyzer.registry.add_recognizer(recognizer_cls())

    return analyzer


def _get_cached_analyzer(
    entity_types: list[str], nlp_engine_type: str, model_name: str, threshold: float
) -> AnalyzerEngine:
    recognizer_key = (
        nlp_engine_type,
        model_name,
        threshold,
        tuple(sorted(t for t in entity_types if t in INDIA_RECOGNIZERS)),
    )
    if recognizer_key not in _ANALYZER_CACHE:
        _ANALYZER_CACHE[recognizer_key] = _build_analyzer(
            entity_types, nlp_engine_type, model_name, threshold
        )
    return _ANALYZER_CACHE[recognizer_key]


@register_validator(name="pii-remover", data_type="string")
class PIIRemover(Validator):
    """
    Anonymize sensitive data in the text using NLP (English only) and predefined regex patterns.
    Anonymizes detected entities with placeholders like [REDACTED_PERSON_1] and stores the real values in a Vault.
    Deanonymizer can be used to replace the placeholders back to their original values.
    """

    def __init__(
        self,
        entity_types=None,
        threshold: float | None = None,
        nlp_engine_type: str = "spacy",
        model_name: str | None = None,
        on_fail: Optional[Callable] = OnFailAction.FIX,
    ):
        super().__init__(on_fail=on_fail)

        self.entity_types = entity_types or ALL_ENTITY_TYPES
        self.nlp_engine_type = nlp_engine_type
        if nlp_engine_type == "transformers":
            self.model_name = model_name or DEFAULT_TRANSFORMERS_MODEL
            self.threshold = threshold if threshold is not None else DEFAULT_TRANSFORMERS_THRESHOLD
        else:
            self.model_name = model_name or "en_core_web_lg"
            self.threshold = threshold if threshold is not None else 0.5
        self.on_fail = on_fail
        self.analyzer = _get_cached_analyzer(
            self.entity_types, self.nlp_engine_type, self.model_name, self.threshold
        )
        self.anonymizer = AnonymizerEngine()

    def _validate(self, value: str, metadata: dict | None = None) -> ValidationResult:
        text = value
        results = self.analyzer.analyze(
            text=text, entities=self.entity_types, language="en"
        )
        anonymized = self.anonymizer.anonymize(text=text, analyzer_results=results)
        anonymized_text = anonymized.text

        if anonymized_text != text:
            return FailResult(
                error_message="PII detected in the text.", fix_value=anonymized_text
            )
        return PassResult(value=text)

