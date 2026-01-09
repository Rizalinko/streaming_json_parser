"""
Unit tests for the StreamingJsonParser module.

Tests cover the main parser functionality, edge cases, and internal methods.
"""
import pytest

from json_parser import StreamingJsonParser


def test_parser_returns_empy_json_for_empty_or_invalid_json():
    """Test that parser returns empty dict for empty or invalid JSON input."""
    parser = StreamingJsonParser()
    parser.consume('')
    assert not parser.get()
    parser.consume('{}')
    assert not parser.get()
    parser.consume('{')
    assert not parser.get()
    parser.consume('just a string')
    assert not parser.get()


def test_parser_returns_entire_json_from_one_input():
    """Test parsing complete JSON from a single input chunk."""
    parser = StreamingJsonParser()
    parser.consume('{"foo": "bar", "bar": "foobar"}')
    assert parser.get() == {"foo": "bar", "bar": "foobar"}

def test_parser_returns_entire_json_from_two_inputs():
    """Test parsing complete JSON split across two input chunks."""
    parser = StreamingJsonParser()
    parser.consume('{"foo": "bar", ')
    parser.consume('"bar": "foobar"')
    assert parser.get() == {"foo": "bar", "bar": "foobar"}

def test_chunked_streaming_json_parser():
    """Test parsing JSON with value split across chunks."""
    parser = StreamingJsonParser()
    parser.consume('{"foo":')
    parser.consume('"bar"')
    assert parser.get() == {"foo": "bar"}

def test_parser_returns_nested_json_correctly():
    """Test parsing JSON with nested objects."""
    parser = StreamingJsonParser()
    parser.consume('{"foo": {"bar": "foobar"}}')
    assert parser.get() == {"foo": {"bar": "foobar"}}


def test_parser_returns_deeply_nested_json_correctly():
    """Test parsing JSON with deeply nested objects."""
    parser = StreamingJsonParser()
    parser.consume('{"a": {"b": "c", "d": {"e": "f"}}}')
    # Example structure:
    # {"a": {
    #     "b": "c",
    #     "d": {"e": "f"}
    #     }
    # }
    assert parser.get() == {"a": {"b": "c", "d": {"e": "f"}}}

def test_parser_returns_partial_json_correctly():
    """Test that parser returns completed key-value pairs from partial JSON."""
    parser = StreamingJsonParser()
    parser.consume('{"test": "hello", "worl')
    assert parser.get() == {"test": "hello"}


def test_incomplete_outer_object():
    """Test parsing incomplete outer object with complete nested object."""
    parser = StreamingJsonParser()
    parser.consume('{"foo": {"bar": "baz"')
    assert parser.get() == {"foo": {"bar": "baz"}}

def test_parser_ignores_trailing_comma():
    """Test that parser handles trailing commas correctly."""
    parser = StreamingJsonParser()
    parser.consume('{"foo": "bar",}')
    assert parser.get() == {"foo": "bar"}


def test_parser_no_op_after_completion():
    """Test that parser maintains state after completion with extra input."""
    parser = StreamingJsonParser()
    parser.consume('{"foo": "bar"}')
    assert parser.get() == {"foo": "bar"}
    parser.consume('}')  # Extra closing brace should be ignored
    assert parser.get() == {"foo": "bar"}

def test_parser_handles_split_strings():
    """Test parsing when string values are split across chunks."""
    parser = StreamingJsonParser()
    parser.consume('{"key fcxfgsdf": "hello')
    parser.consume(' world"}')
    assert parser.get() == {"key fcxfgsdf": "hello world"}


def test_parser_ignores_invalid_content():
    """Test that parser ignores content after valid JSON."""
    parser = StreamingJsonParser()
    parser.consume('{"foo": "bar"}bad_json')
    assert parser.get() == {"foo": "bar"}

def test_parser_updates_json_correctly():
    """Test that parser correctly updates result as more chunks arrive."""
    parser = StreamingJsonParser()
    parser.consume('{"test": "hello", "country": "Switzerl')
    assert parser.get() == {"test": "hello", "country": "Switzerl"}
    parser.consume('and"')
    assert parser.get() == {"test": "hello", "country": "Switzerland"}
    parser.consume('}')
    assert parser.get() == {"test": "hello", "country": "Switzerland"}


def test_parser_handles_invalid_value_types_correctly():
    """Test that parser correctly skips invalid value types (arrays, booleans)."""
    parser = StreamingJsonParser()
    json_str = ('{"key1": "value1", "key2": ["arrayValue1", "array 2"], '
                '"key3": true, "key4": {"nestedKey": "nestedValue"}}')
    parser.consume(json_str)
    assert parser.get() == {"key1": "value1", "key4": {"nestedKey": "nestedValue"}}


# Below are unit tests for external functions and internal methods of StreamingJsonParser

def test_skip_ws_skips_leading_whitespace():
    """Test that skip_ws correctly skips all whitespace characters."""
    parser = StreamingJsonParser()
    s = " \n\t\rabc"
    assert parser._skip_ws(s, 0) == 4  # pylint: disable=protected-access
    assert parser._skip_ws(s, 4) == 4  # pylint: disable=protected-access
    assert parser._skip_ws(s, len(s)) == len(s)  # pylint: disable=protected-access



@pytest.mark.parametrize('s, expected_val, expected_completed',
                         [('"incomplete', 'incomplete', False),
                         ('"complete"', 'complete', True),
                         ('""', '', True)])
def test_read_string_various_cases(s, expected_val, expected_completed):
    """Test read_string function with complete, incomplete, and empty strings."""
    parser = StreamingJsonParser()
    result_val, i, completed = parser._read_string(s, 0)  # pylint: disable=protected-access
    assert completed is expected_completed
    assert result_val == expected_val
    assert i == len(s)


@pytest.mark.parametrize('s, expected_val, expected_invalid',
                         [('"world"', 'world', False),
                         ('"world', 'world',  False),
                            ('[1,2,3]', None, True)])
def test_read_value_string(s, expected_val, expected_invalid):
    """Test _read_value method with strings and invalid values."""
    parser = StreamingJsonParser()
    val, _, invalid = parser._read_value(s, 0)  # pylint: disable=protected-access
    assert val == expected_val
    assert invalid is expected_invalid
    assert invalid is expected_invalid

def test_parse_object_returns_partial_for_incomplete_object():
    """Test _parse_object returns partial flag for incomplete objects."""
    parser = StreamingJsonParser()
    s = '{"key": "value", "incomplete": '
    parser.consume(s)
    obj, _, partial, invalid = parser._parse_object(s, 0)  # pylint: disable=protected-access
    assert partial is True
    assert invalid is False
    assert obj == {"key": "value"}
    assert parser.get() == {"key": "value"}


def test_parse_object_returns_correct_if_json_has_unsupported_construct():
    """Test _parse_object skips unsupported constructs and continues parsing."""
    parser = StreamingJsonParser()
    s = '{"key": "value", "invalid": [1, 2, 3]}'
    obj, _, partial, invalid = parser._parse_object(s, 0)  # pylint: disable=protected-access
    assert invalid is False  # Parser successfully skips invalid values and continues
    assert partial is False  # Object is complete
    assert obj == {"key": "value"}

def test_parse_object_returns_complete_for_valid_object():
    """Test _parse_object correctly parses complete valid object."""
    parser = StreamingJsonParser()
    s = '{"key":  {"another": "item"}}'
    obj, _, partial, invalid = parser._parse_object(s, 0)  # pylint: disable=protected-access
    assert partial is False
    assert invalid is False
    assert obj ==  {"key":  {"another": "item"}}


def test_skip_invalid_value_skips_simple_array():
    """Test _skip_invalid_value correctly skips a simple array."""
    parser = StreamingJsonParser()
    s = '[1, 2, 3], "next": "value"}'
    i = parser._skip_invalid_value(s, 0)
    assert i == 9  # Should skip to after the closing bracket
    assert s[i] == ','


def test_skip_invalid_value_skips_nested_arrays():
    """Test _skip_invalid_value correctly skips nested arrays."""
    parser = StreamingJsonParser()
    s = '[1, [2, 3], 4], "next": "value"}'
    i = parser._skip_invalid_value(s, 0)
    assert i == 14  # Should skip the entire nested array
    assert s[i] == ','


def test_skip_invalid_value_skips_boolean():
    """Test _skip_invalid_value correctly skips boolean values."""
    parser = StreamingJsonParser()
    s = 'true, "next": "value"}'
    i = parser._skip_invalid_value(s, 0)
    assert i == 4  # Should skip "true"
    assert s[i] == ','


def test_skip_invalid_value_skips_float():
    """Test _skip_invalid_value correctly skips numeric values."""
    parser = StreamingJsonParser()
    s = '123.456, "next": "value"}'
    i = parser._skip_invalid_value(s, 0)
    assert i == 7  # Should skip "123.456"
    assert s[i] == ','


def test_skip_invalid_value_stops_at_closing_brace():
    """Test _skip_invalid_value stops correctly at closing brace."""
    parser = StreamingJsonParser()
    s = 'true}'
    i = parser._skip_invalid_value(s, 0)
    assert i == 4  # Should skip "true"
    assert s[i] == '}'
