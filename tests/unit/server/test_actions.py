from cactus_test_definitions.server import actions


def test_action_admin_setup():
    """Ensures Action.admin_setup() method works."""
    result = actions.Action.admin_setup()
    assert isinstance(result, actions.Action)

    # Ensure type is a reserved name
    assert result.type in actions.Action.RESERVED_NAMES


def test_action_admin_teardown():
    """Ensures Action.admin_teardown() method works."""
    result = actions.Action.admin_teardown()
    assert isinstance(result, actions.Action)

    # Ensure type is a reserved name
    assert result.type in actions.Action.RESERVED_NAMES


def test_valid_action_names_factory_reserved(monkeypatch):
    """Ensures that reserved names can't be used."""
    # Patch the parameter schema keys temporarily for this test
    new_schema = {k: dict() for k in actions.Action.RESERVED_NAMES}
    monkeypatch.setattr(actions, "ACTION_PARAMETER_SCHEMA", new_schema)

    # Act + Assert
    try:
        # Act
        _ = actions.valid_action_names_factory()

    except Exception as exc:
        # Assert
        assert isinstance(
            exc, ValueError
        ), f"Invalid exception thrown. Expected 'ValueError'; got '{exc.__class__.__name__}'"
        exc_str = str(exc)
        missing_vals = [k for k in new_schema if k not in exc_str]
        assert missing_vals == []
        return

    raise AssertionError("No exception thrown. Expected ValueError")
