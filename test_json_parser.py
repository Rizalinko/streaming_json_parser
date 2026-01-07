import pytest

from json_parser import StreamingJsonParser, skip_ws, read_string


def test_parser_returns_empy_json_for_empty_or_invalid_json():
    parser = StreamingJsonParser()
    parser.consume('')
    assert parser.get() == {}
    parser.consume('{}')
    assert parser.get() == {}
    parser.consume('{')
    assert parser.get() == {}
    parser.consume('just a string')
    assert parser.get() == {}


def test_parser_returns_entire_json_from_one_input():
    parser = StreamingJsonParser()
    parser.consume('{"foo": "bar", "bar": "foobar"}')
    assert parser.get() == {"foo": "bar", "bar": "foobar"}

def test_parser_returns_entire_json_from_two_inputs():
    parser = StreamingJsonParser()
    parser.consume('{"foo": "bar", ')
    parser.consume('"bar": "foobar"')
    assert parser.get() == {"foo": "bar", "bar": "foobar"}

def test_chunked_streaming_json_parser():
    parser = StreamingJsonParser()
    parser.consume('{"foo":')
    parser.consume('"bar"')
    assert parser.get() == {"foo": "bar"}

def test_parser_returns_nested_json_correctly():
    parser = StreamingJsonParser()
    parser.consume('{"foo": {"bar": "foobar"}}')
    assert parser.get() == {"foo": {"bar": "foobar"}}


def test_parser_returns_deeply_nested_json_correctly():
    parser = StreamingJsonParser()
    parser.consume('{"a": {"b": "c", "d": {"e": "f"}}}')
    """
    {"a": {
        "b": "c",
        "d": {"e": "f"}
        }
    }
    """
    assert parser.get() == {"a": {"b": "c", "d": {"e": "f"}}}

def test_parser_returns_partial_json_correctly():
    parser = StreamingJsonParser()
    parser.consume('{"test": "hello", "worl')
    assert parser.get() == {"test": "hello"}


def test_incomplete_outer_object():
    parser = StreamingJsonParser()
    parser.consume('{"foo": {"bar": "baz"')
    assert parser.get() == {"foo": {"bar": "baz"}}

def test_parser_ignores_trailing_comma():
    parser = StreamingJsonParser()
    parser.consume('{"foo": "bar",}')
    assert parser.get() == {"foo": "bar"}


def test_parser_no_op_after_completion():
    parser = StreamingJsonParser()
    parser.consume('{"foo": "bar"}')
    assert parser.get() == {"foo": "bar"}
    parser.consume('}')  # Extra closing brace should be ignored
    assert parser.get() == {"foo": "bar"}

def test_parser_handles_split_strings():
    parser = StreamingJsonParser()
    parser.consume('{"key fcxfgsdf": "hello')
    parser.consume(' world"}')
    assert parser.get() == {"key fcxfgsdf": "hello world"}


def test_parser_ignores_invalid_content():
    parser = StreamingJsonParser()
    parser.consume('{"foo": "bar"}bad_json')
    assert parser.get() == {"foo": "bar"}

def test_parser_updates_json_correctly():
    parser = StreamingJsonParser()
    parser.consume('{"test": "hello", "country": "Switzerl')
    assert parser.get() == {"test": "hello", "country": "Switzerl"}
    parser.consume('and"')
    assert parser.get() == {"test": "hello", "country": "Switzerland"}
    parser.consume('}')
    assert parser.get() == {"test": "hello", "country": "Switzerland"}

def test_parser_handles_invalid_value_types_correctly():
    parser = StreamingJsonParser()
    parser.consume('{"key1": "value1", "key2": ["arrayValue1", "array 2"], "key3": true, "key4": {"nestedKey": "nestedValue"}}')
    assert parser.get() == {"key1": "value1", "key4": {"nestedKey": "nestedValue"}}


"""
Below are unit tests for external functions and internal methods of StreamingJsonParser
"""

def test_skip_ws_skips_leading_whitespace():
    s = " \n\t\rabc"
    assert skip_ws(s, 0) == 4
    assert skip_ws(s, 4) == 4
    assert skip_ws(s, len(s)) == len(s)



@pytest.mark.parametrize('s, expected_val, expected_completed',
                         [('"incomplete', 'incomplete', False),
                         ('"complete"', 'complete', True),
                         ('""', '', True)])
def test_read_string_various_cases(s, expected_val, expected_completed):
    result_val, i, completed = read_string(s, 0)
    assert completed is expected_completed
    assert result_val == expected_val
    assert i == len(s)


@pytest.mark.parametrize('s, expected_val, expected_partial, expected_invalid',
                         [('"world"', 'world', False, False),
                         ('"world', 'world', True, False),
                            ('[1,2,3]', None, False, True)])
def test_read_value_string(s, expected_val, expected_partial, expected_invalid):
    parser = StreamingJsonParser()
    val, i, partial, invalid = parser._read_value(s, 0)
    assert val == expected_val
    assert partial is expected_partial
    assert invalid is expected_invalid

def test_parse_object_returns_partial_for_incomplete_object():
    parser = StreamingJsonParser()
    s = '{"key": "value", "incomplete": '
    parser.consume(s)
    obj, i, partial, invalid = parser._parse_object(s, 0)
    assert partial is True
    assert invalid is False
    assert obj == {"key": "value"}
    assert parser.get() == {"key": "value"}


def test_parse_object_returns_correct_if_json_has_unsupported_construct():
    parser = StreamingJsonParser()
    s = '{"key": "value", "invalid": [1, 2, 3]}'
    obj, i, partial, invalid = parser._parse_object(s, 0)
    assert invalid is True
    assert obj == {"key": "value"}

def test_parse_object_returns_complete_for_valid_object():
    parser = StreamingJsonParser()
    s = '{"key":  {"another": "item"}}'
    obj, i, partial, invalid = parser._parse_object(s, 0)
    assert partial is False
    assert invalid is False
    assert obj ==  {"key":  {"another": "item"}}