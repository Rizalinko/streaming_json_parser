"""
Streaming JSON parser: a class to efficiently parse JSON objects from a stream of text input.

The class has a variable-length internal buffer that accumulates incoming text chunks. The parser attempts to parse complete JSON objects
from the buffer whenever requested, returning the last successfully parsed object.

The following assumptions are made for the simplification:
- The strings have no escape characters, therefore during the parsing we do not check for them.
- !!! The parsed JSON should only contain objects (dictionaries including nested dictionaries) and strings as values, thus anything else
(numbers, arrays, booleans, null) is considered invalid and ignored.
           Example of input:
                '{"key1": "value1", "key2": {"nestedKey": "nestedValue"}}'
           Output:
                {"key1": "value1", "key2": {"nestedKey": "nestedValue"}}

           Example of input with invalid constructs:
                '{"key1": "value1", "key2": ["arrayValue1", "array 2"], "key3": true, "key4": {"nestedKey": "nestedValue"}}'
           Output:
                {"key1": "value1", "key4": {"nestedKey": "nestedValue"}}
"""


from typing import Any


def skip_ws(s: str, i: int) -> int:
    while i < len(s) and s[i].isspace():
        i += 1
    return i


def read_string(s: str, i: int) -> tuple[str, int, bool]:
    """
    Read a JSON string starting at s[i] (which must be a quote).
    Returns (value, next_index, completed_flag).
    completed_flag == False means the string was partial (no closing quote).
    """
    i += 1  # Skip the opening '"'
    out = []
    while i < len(s):
        ch = s[i]
        if ch == '"':
            return "".join(out), i + 1, True

        out.append(ch)
        i += 1

    # Ran out of input; return partial string.
    return "".join(out), i, False



class StreamingJsonParser:
    def __init__(self) -> None:
        self._buffer: str = ""
        self._result: dict[str, Any] = {}

    def consume(self, chunk: str) -> None:
        self._buffer += chunk

    def get(self) -> dict[str, Any]:
        # Attempt to parse from the first '{' found.
        start = self._buffer.find("{")
        if start == -1:
            return {}

        obj, invalid = self._parse_from(start)
        if invalid:
            # If invalid, reset to empty.
            self._result = {}
        else:
            self._result = obj

        return self._result

    def _skip_invalid_value(self, s: str, i: int) -> int:
        """
        Skip over an invalid value construct (array, number, boolean, null).
        Returns the index after the invalid construct.
        """
        i = skip_ws(s, i)
        if i >= len(s):
            return i

        ch = s[i]

        # Skip array
        if ch == '[':
            depth = 1
            i += 1
            while i < len(s) and depth > 0:
                if s[i] == '[':
                    depth += 1
                elif s[i] == ']':
                    depth -= 1
                elif s[i] == '"':
                    # Skip strings inside arrays
                    _, i, _ = read_string(s, i)
                    continue
                i += 1
            return i

        # Skip boolean, null, or number (anything that's not a quote or brace)
        while i < len(s) and s[i] not in (',', '}', ' ', '\t', '\n', '\r'):
            i += 1

        return i

    def _read_value(self, s: str, i: int) -> tuple[Any, int, bool, bool]:
        """
        Returns (value for key, next_index, partial, invalid)
        partial=True means input ended before value fully closed.
        invalid=True means encountered unsupported value (e.g., number or a list).
        """
        i = skip_ws(s, i)
        if i >= len(s):
            return None, i, True, False

        ch = s[i]
        if ch == '"':
            val, nxt_idx, completed = read_string(s, i)
            partial = not completed
            return val, nxt_idx, partial, False
        if ch == "{":
            obj, nxt_idx, partial, invalid = self._parse_object(s, i)
            return obj, nxt_idx, partial, invalid

        # Anything else is invalid for our simplified grammar
        return None, i, False, True

    def _parse_object(self, s: str, i: int) -> tuple[dict[str, Any], int, bool, bool]:
        """
        Parse an object starting at s[i] == '{'.
        Returns (obj, next_index, partial, invalid).
        partial=True if input ended before object closed.
        invalid=True if an unsupported construct was found.
        """
        i += 1  # Skip the opening '{'
        obj: dict[str, Any] = {}

        while True:
            # parse the key
            i = skip_ws(s, i)
            if i >= len(s):
                return obj, i, True, False
            if s[i] == "}":
                return obj, i + 1, False, False
            if s[i] == ",":
                i += 1
                continue

            if s[i] != '"':
                # Unexpected token; treat as partial.
                return obj, i, True, False
            key, i, key_completed = read_string(s, i)
            if not key_completed:
                # if the key is not complete, return the state of the object so far
                return obj, i, True, False

            # parse the value
            i = skip_ws(s, i)
            if i >= len(s):
                return obj, i, True, False
            if s[i] != ":":
                return obj, i, True, False
            i += 1

            value, i, val_partial, invalid = self._read_value(s, i)
            if invalid:
                # Skip over the invalid construct
                i = self._skip_invalid_value(s, i)
            elif value:
                obj[key] = value

            i = skip_ws(s, i)
            if i >= len(s):
                return obj, i, True, False
            if s[i] == ",":
                i += 1
                # Support trailing comma followed immediately by closing brace.
                i = skip_ws(s, i)
                if i < len(s) and s[i] == "}":
                    return obj, i + 1, False, False
                continue
            if s[i] == "}":
                return obj, i + 1, False, False

            # Anything else: treat as partial/unknown but keep what we have.
            return obj, i, True, False

    def _parse_from(self, start: int) -> tuple[dict[str, Any], bool]:
        """
        Attempt to parse an object from buffer[start:].
        Returns (object, invalid_flag).
        """
        obj, _, _, invalid = self._parse_object(self._buffer, start)
        return obj, invalid