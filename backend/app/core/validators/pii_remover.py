from __future__ import annotations
import os
from typing import Callable, Optional

from guardrails import OnFailAction
from guardrails.validators import (
    FailResult,
    PassResult,
    register_validator,
    ValidationResult,
    Validator,
)
from presidio_analyzer import AnalyzerEngine
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

_GLOBAL_NLP_ENGINE = None
_ANALYZER_CACHE = {}


INDIA_RECOGNIZERS = {
    "IN_AADHAAR": InAadhaarRecognizer,
    "IN_PAN": InPanRecognizer,
    "IN_PASSPORT": InPassportRecognizer,
    "IN_VEHICLE_REGISTRATION": InVehicleRegistrationRecognizer,
    "IN_VOTER": InVoterRecognizer,
}


def _build_analyzer(entity_types: list[str]) -> AnalyzerEngine:
    global _GLOBAL_NLP_ENGINE
    if _GLOBAL_NLP_ENGINE is None:
        provider = NlpEngineProvider(nlp_configuration=CONFIGURATION)
        _GLOBAL_NLP_ENGINE = provider.create_engine()
    analyzer = AnalyzerEngine(nlp_engine=_GLOBAL_NLP_ENGINE)

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
    Anonymize sensitive data in the text using NLP (English only) and predefined regex patterns.
    Anonymizes detected entities with placeholders like [REDACTED_PERSON_1] and stores the real values in a Vault.
    Deanonymizer can be used to replace the placeholders back to their original values.
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

    def _validate(self, value: str, metadata: dict = None) -> ValidationResult:
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
