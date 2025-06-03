"""Unit tests for the TextInput class."""
from unittest.mock import MagicMock, patch

import pytest
from pynput import keyboard

from nixwhisper.input import TextInput, TextInputError


class MockKey:
    """Mock class for pynput.keyboard.Key"""
    def __init__(self, name):
        self.name = name

    def __eq__(self, other):
        return self.name == other.name


class MockKeyCode:
    """Mock class for pynput.keyboard.KeyCode"""
    def __init__(self, char=None, vk=None):
        self.char = char
        self.vk = vk

    def __eq__(self, other):
        return self.char == other.char and self.vk == other.vk


@pytest.fixture
def controller():
    """Fixture to mock the pynput.keyboard.Controller."""
    with patch('pynput.keyboard.Controller') as mock_controller_cls:
        mock_controller = MagicMock()
        mock_controller_cls.return_value = mock_controller
        yield mock_controller


def test_text_input_initialization():
    """Test TextInput initialization."""
    text_input = TextInput()
    assert text_input.controller is not None


def test_type_text_success(controller):
    """Test typing text successfully."""
    text_input = TextInput()
    test_text = "Hello, world!"
    result = text_input.type_text(test_text)
    assert result is True
    controller.type.assert_called_once_with(test_text)


def test_type_text_empty_string():
    """Test typing an empty string."""
    text_input = TextInput()
    result = text_input.type_text("")
    assert result is True


def test_type_text_with_special_characters(controller):
    """Test typing text with special characters."""
    text_input = TextInput()
    test_text = "Hello, 世界! 😊"
    result = text_input.type_text(test_text)
    assert result is True
    controller.type.assert_called_once_with(test_text)


def test_type_text_with_control_characters(controller):
    """Test typing text with control characters."""
    text_input = TextInput()
    test_text = "Line 1\nLine 2\tTabbed"
    result = text_input.type_text(test_text)
    assert result is True
    controller.type.assert_called_once_with(test_text)


def test_type_text_error_handling(controller):
    """Test error handling when typing text fails."""
    text_input = TextInput()
    test_text = "Hello"
    controller.type.side_effect = Exception("Simulated error")
    with pytest.raises(TextInputError, match="Failed to type text"):
        text_input.type_text(test_text)


def test_press_key_combo_single_key(controller):
    """Test pressing a single key combination."""
    text_input = TextInput()
    key = keyboard.Key.ctrl
    with text_input.press_key_combo(key):
        pass
    controller.press.assert_called_once_with(key)
    controller.release.assert_called_once_with(key)


def test_press_key_combo_multiple_keys(controller):
    """Test pressing a combination of multiple keys."""
    text_input = TextInput()
    keys = [keyboard.Key.ctrl, keyboard.Key.shift, 'a']
    with text_input.press_key_combo(*keys):
        pass
    # Should press all keys in order
    press_calls = [call[0][0] for call in controller.press.call_args_list]
    assert len(press_calls) == 3
    assert all(k1 == k2 for k1, k2 in zip(press_calls, keys))
    # Should release all keys in reverse order
    release_calls = [call[0][0] for call in controller.release.call_args_list]
    assert len(release_calls) == 3
    assert all(k1 == k2 for k1, k2 in zip(release_calls, reversed(keys)))


def test_press_key_combo_with_exception(controller):
    """Test that keys are released even if an exception occurs."""
    text_input = TextInput()
    key = keyboard.Key.ctrl
    with pytest.raises(ValueError):
        with text_input.press_key_combo(key):
            raise ValueError("Test exception")
    # Key should still be released even with exception
    controller.release.assert_called_once_with(key)


def test_parse_hotkey():
    """Test parsing hotkey strings.

    Note: This test accesses protected member _parse_hotkey directly
    as it is testing the internal implementation details of hotkey parsing.
    """
    text_input = TextInput()
    # Test with modifier keys
    keys = text_input._parse_hotkey("<ctrl>+<alt>+a")
    assert len(keys) == 3
    assert keys[0] == keyboard.Key.ctrl
    assert keys[1] == keyboard.Key.alt
    assert keys[2] == 'a'
    # Test with shift modifier (should preserve case)
    keys = text_input._parse_hotkey("<shift>+A")
    assert len(keys) == 2
    assert keys[0] == keyboard.Key.shift
    assert keys[1] == 'A'  # Should preserve case
    # Test with key names
    keys = text_input._parse_hotkey("<space>")
    assert len(keys) == 1
    assert keys[0] == keyboard.Key.space
    # Test with key code
    keys = text_input._parse_hotkey("<97>")
    assert len(keys) == 1
    assert keys[0].vk == 97


def test_parse_hotkey_invalid():
    """Test parsing invalid hotkey strings.

    Note: This test accesses protected member _parse_hotkey directly
    as it is testing the internal implementation details of hotkey parsing.
    """
    text_input = TextInput()
    # Empty string
    with pytest.raises(ValueError, match="Empty hotkey"):
        text_input._parse_hotkey("")
    # Invalid key
    with pytest.raises(ValueError, match="Unknown key"):
        text_input._parse_hotkey("<invalid>")
    # Invalid format
    with pytest.raises(ValueError, match="Invalid hotkey format"):
        text_input._parse_hotkey("ctrl+alt+x")  # Missing <>
    # Invalid key code
    with pytest.raises(ValueError, match="Unknown key: abc"):
        text_input._parse_hotkey("<abc>")  # Not a valid key
