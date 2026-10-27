from app.core.validators.ban_list import BanList


def test_passes_when_no_banned_word():
    result = BanList(banned_words=["sonography"]).validate("Is ultrasound safe?", {})
    assert result.outcome == "pass"


def test_fix_value_removes_whole_banned_word():
    result = BanList(banned_words=["sonography"]).validate(
        "Can I get a sonography to know", {}
    )
    assert result.outcome == "fail"
    assert result.fix_value == "Can I get a  to know"


def test_banned_word_at_start_of_text():
    result = BanList(banned_words=["sonography"]).validate("sonography kab karayein", {})
    assert result.fix_value == " kab karayein"


def test_multi_word_banned_phrase_spans_original_spaces():
    result = BanList(banned_words=["gender check"]).validate(
        "Where is gender check done?", {}
    )
    assert result.fix_value == "Where is  done?"
    span = result.error_spans[0]
    assert (span.start, span.end) == (9, 21)


def test_error_span_points_at_banned_word():
    text = "Can I get a sonography to know"
    result = BanList(banned_words=["sonography"]).validate(text, {})
    span = result.error_spans[0]
    assert text[span.start : span.end] == "sonography"
