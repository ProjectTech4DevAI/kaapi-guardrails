import pytest
from unittest.mock import Mock, patch

from app.core.guardrail_controller import build_guard


def test_build_guard_with_validators():
    # mock validator instances returned by .build()
    v1 = Mock(name="validator1")
    v2 = Mock(name="validator2")

    # mock validator config objects
    cfg1 = Mock()
    cfg1.build.return_value = v1

    cfg2 = Mock()
    cfg2.build.return_value = v2

    mock_guard = Mock()

    with patch(
        "app.core.guardrail_controller.Guard",
        return_value=mock_guard,
    ) as GuardMock:
        result = build_guard([cfg1, cfg2])

    # .build() called on each config
    cfg1.build.assert_called_once()
    cfg2.build.assert_called_once()

    # Guard instantiated
    GuardMock.assert_called_once()

    # use_many called with correct validators
    mock_guard.use_many.assert_called_once_with(v1, v2)

    # return value is whatever Guard().use_many returns
    assert result == mock_guard.use_many.return_value


def test_build_guard_with_no_validators():
    mock_guard = Mock()

    with patch(
        "app.core.guardrail_controller.Guard",
        return_value=mock_guard,
    ):
        result = build_guard([])

    mock_guard.use_many.assert_called_once_with()
    assert result == mock_guard.use_many.return_value


def test_build_guard_build_failure_propagates():
    cfg = Mock()
    cfg.build.side_effect = RuntimeError("invalid config")

    with patch("app.core.guardrail_controller.Guard"):
        with pytest.raises(RuntimeError, match="invalid config"):
            build_guard([cfg])


def test_build_guard_use_many_failure():
    cfg = Mock()
    cfg.build.return_value = Mock()

    mock_guard = Mock()
    mock_guard.use_many.side_effect = RuntimeError("guard failure")

    with patch(
        "app.core.guardrail_controller.Guard",
        return_value=mock_guard,
    ):
        with pytest.raises(RuntimeError, match="guard failure"):
            build_guard([cfg])
