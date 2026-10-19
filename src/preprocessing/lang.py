"""Language detection with lingua (replaces the function-word heuristic from the EDA)."""
from lingua import Language, LanguageDetectorBuilder

ISO_TO_NAME = {
    'pl': 'POLISH', 'en': 'ENGLISH', 'de': 'GERMAN', 'ru': 'RUSSIAN', 'uk': 'UKRAINIAN',
    'cs': 'CZECH', 'sk': 'SLOVAK', 'fr': 'FRENCH', 'es': 'SPANISH', 'it': 'ITALIAN',
}


def build_detector(languages):
    """Detector restricted to the given ISO 639-1 codes (fewer candidates = faster and more accurate)."""
    langs = [getattr(Language, ISO_TO_NAME[code]) for code in languages]
    if Language.POLISH not in langs:
        langs.append(Language.POLISH)
    return LanguageDetectorBuilder.from_languages(*langs).with_preloaded_language_models().build()


def polish_confidence(detector, texts):
    """Confidence (0..1) that each text is Polish."""
    texts = list(texts)
    parallel = getattr(detector, 'compute_language_confidence_in_parallel', None)
    if parallel is not None:
        return list(parallel(texts, Language.POLISH))
    return [detector.compute_language_confidence(t, Language.POLISH) for t in texts]
