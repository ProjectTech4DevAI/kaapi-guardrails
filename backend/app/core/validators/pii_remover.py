from __future__ import annotations
import os
from typing import Callable, List, Optional

from guardrails import OnFailAction
from guardrails.validators import (
    FailResult,
    PassResult,
    register_validator,
    ValidationResult,
    Validator,
)
from presidio_analyzer import AnalyzerEngine, RecognizerResult
from presidio_analyzer.entity_recognizer import EntityRecognizer
from presidio_analyzer.nlp_engine import NlpEngineProvider
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

CONFIGURATION = {
    "nlp_engine_name": "spacy",
    "models": [{"lang_code": "en", "model_name": "en_core_web_lg"}],
}

# Labels returned by dslim/bert-base-NER → Presidio entity types
_TRANSFORMER_LABEL_MAP = {
    "PER": "PERSON",
    "LOC": "LOCATION",
}

_GLOBAL_NLP_ENGINE = None
_ANALYZER_CACHE = {}
_TRANSFORMER_RECOGNIZER: Optional["TransformerNERRecognizer"] = None


INDIA_RECOGNIZERS = {
    "IN_AADHAAR": InAadhaarRecognizer,
    "IN_PAN": InPanRecognizer,
    "IN_PASSPORT": InPassportRecognizer,
    "IN_VEHICLE_REGISTRATION": InVehicleRegistrationRecognizer,
    "IN_VOTER": InVoterRecognizer,
}


class TransformerNERRecognizer(EntityRecognizer):
    """
    NER recognizer backed by dslim/bert-base-NER (BERT fine-tuned on CoNLL-2003).
    Returns real confidence scores (0–1) instead of spaCy's fixed 0.85, which
    allows the score threshold to meaningfully filter low-confidence detections.
    Handles Hinglish text correctly because out-of-distribution Hindi tokens
    score near zero and are suppressed by the threshold.
    """

    SUPPORTED_ENTITIES = ["PERSON", "LOCATION"]
    MODEL_NAME = "dslim/bert-base-NER"

    def __init__(self) -> None:
        super().__init__(
            supported_entities=self.SUPPORTED_ENTITIES,
            name="TransformerNERRecognizer",
        )
        self._pipeline = None

    def load(self) -> None:
        pass  # lazy-loaded on first analyze() call

    def _ensure_loaded(self) -> None:
        if self._pipeline is None:
            from transformers import pipeline

            self._pipeline = pipeline(
                "token-classification",
                model=self.MODEL_NAME,
                aggregation_strategy="simple",
            )

    def analyze(
        self, text: str, entities: List[str], nlp_artifacts=None
    ) -> List[RecognizerResult]:
        self._ensure_loaded()
        predictions = self._pipeline(text)
        results = []
        for pred in predictions:
            entity_type = _TRANSFORMER_LABEL_MAP.get(pred["entity_group"])
            if entity_type and entity_type in entities:
                results.append(
                    RecognizerResult(
                        entity_type=entity_type,
                        start=pred["start"],
                        end=pred["end"],
                        score=round(float(pred["score"]), 4),
                    )
                )
        return results


def _get_transformer_recognizer() -> TransformerNERRecognizer:
    global _TRANSFORMER_RECOGNIZER
    if _TRANSFORMER_RECOGNIZER is None:
        _TRANSFORMER_RECOGNIZER = TransformerNERRecognizer()
    return _TRANSFORMER_RECOGNIZER


def _build_analyzer(entity_types: list[str]) -> AnalyzerEngine:
    global _GLOBAL_NLP_ENGINE
    if _GLOBAL_NLP_ENGINE is None:
        provider = NlpEngineProvider(nlp_configuration=CONFIGURATION)
        _GLOBAL_NLP_ENGINE = provider.create_engine()

    analyzer = AnalyzerEngine(nlp_engine=_GLOBAL_NLP_ENGINE)

    # Replace the default SpacyRecognizer with a transformer-based NER recognizer.
    # SpacyRecognizer assigns a fixed 0.85 score to every entity regardless of
    # confidence, and the English model classifies Hinglish words as PERSON/LOCATION.
    # The transformer recognizer returns real probabilities, so the score threshold
    # suppresses low-confidence (out-of-distribution) Hindi token detections.
    analyzer.registry.recognizers = [
        r
        for r in analyzer.registry.recognizers
        if r.__class__.__name__ != "SpacyRecognizer"
    ]
    analyzer.registry.add_recognizer(_get_transformer_recognizer())

    for entity_type, recognizer_cls in INDIA_RECOGNIZERS.items():
        if entity_type in entity_types:
            analyzer.registry.add_recognizer(recognizer_cls())

    return analyzer


def _get_cached_analyzer(entity_types: list[str]) -> AnalyzerEngine:
    recognizer_key = tuple(sorted(t for t in entity_types if t in INDIA_RECOGNIZERS))
    if recognizer_key not in _ANALYZER_CACHE:
        _ANALYZER_CACHE[recognizer_key] = _build_analyzer(entity_types)
    return _ANALYZER_CACHE[recognizer_key]


@register_validator(name="pii-remover", data_type="string")
class PIIRemover(Validator):
    """
    Anonymize sensitive data in the text using a transformer-based NER model
    and predefined regex patterns. Supports Hinglish (Hindi + English) text.

    Detected entities are replaced with placeholders like <PERSON>. The
    score_threshold (default 0.5) filters low-confidence detections; raise it
    to reduce sensitivity or lower it to increase recall.
    """

    def __init__(
        self,
        entity_types=None,
        threshold=0.5,
        on_fail: Optional[Callable] = OnFailAction.FIX,
    ):
        super().__init__(on_fail=on_fail)

        self.entity_types = entity_types or ALL_ENTITY_TYPES
        self.threshold = threshold
        self.on_fail = on_fail
        self.analyzer = _get_cached_analyzer(self.entity_types)
        self.anonymizer = AnonymizerEngine()

    def _validate(self, value: str, metadata: dict | None = None) -> ValidationResult:
        text = value
        results = self.analyzer.analyze(
            text=text,
            entities=self.entity_types,
            language="en",
            score_threshold=self.threshold,
        )
        anonymized = self.anonymizer.anonymize(text=text, analyzer_results=results)
        anonymized_text = anonymized.text

        if anonymized_text != text:
            return FailResult(
                error_message="PII detected in the text.", fix_value=anonymized_text
            )
        return PassResult(value=text)
