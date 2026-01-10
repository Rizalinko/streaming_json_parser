"""
Streaming JSON parser: a class to efficiently parse JSON objects from a stream of text input.

The class has a variable-length internal buffer that accumulates incoming text chunks.
The parser attempts to parse complete JSON objects
from the buffer whenever requested, returning the last successfully parsed object.

The following assumptions are made for the simplification:
- The strings have no escape characters, therefore during the parsing we do not check for them.
- The parsed JSON should only contain objects (dictionaries including nested dictionaries)
and strings as values, thus anything else (numbers, arrays, booleans, null) is
considered invalid and ignored.
           Example of input:
                '{"key1": "value1", "key2": {"nestedKey": "nestedValue"}}'
           Output:
                {"key1": "value1", "key2": {"nestedKey": "nestedValue"}}

           Example of input with invalid constructs:
                '{"key1": "value1", "key2": ["arrayValue1", "array 2"],
                 "key3": true, "key4": {"nestedKey": "nestedValue"}}'
           Output:
                {"key1": "value1", "key4": {"nestedKey": "nestedValue"}}


One implementation trade off is that the parser does not remove processed data from the buffer.
This simplifies the implementation at the cost of potentially higher memory usage
if the buffer grows large with many incomplete JSON objects.
When the large in size JSON objects are expected (order of hunders of MBs),
I would suggest implementing trimming of the buffer to remove processed data
up to the last complete JSON object.

Another implementation detail is that helper methods are all instance methods rather
than static methods. While this is less efficient, it improves code readability.
"""


from typing import Any



class StreamingJsonParser:
    """
    A streaming JSON parser that processes JSON objects incrementally from text chunks.

    Only supports JSON objects (dictionaries) and string values. Invalid constructs
    like arrays, numbers, booleans, and null are skipped.
    """
    def __init__(self) -> None:
        self._buffer: str = ""
        self._result: dict[str, Any] = {}

    def _skip_ws(self, s: str, i: int) -> int:
        """
        Skip whitespace characters in string s starting at index i.
        Returns the index of the first non-whitespace character.
        """
        while i < len(s) and s[i].isspace():
            i += 1

    def _read_string(self, s: str, i: int) -> tuple[str, int, bool]:
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


    def consume(self, chunk: str) -> None:
        """Add a chunk of text to the internal buffer for parsing."""
        self._buffer += chunk

    def get(self) -> dict[str, Any]:
        """
        Parse and return the last successfully parsed JSON object from the buffer.
        Returns an empty dict if no valid object can be parsed.
        """
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
        i = self._skip_ws(s, i)
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
                    _, i, _ = self._read_string(s, i)
                    continue
                i += 1
            return i

        # Skip boolean, null, or number (anything that's not a quote or brace)
        while i < len(s) and s[i] not in (',', '}', ' ', '\t', '\n', '\r'):
            i += 1

        return i

    def _read_value(self, s: str, i: int) -> tuple[Any, int,  bool]:
        """
        Returns (value for key, next_index, partial, invalid)
        partial=True means input ended before value fully closed.
        invalid=True means encountered unsupported value (e.g., number or a list).
        """
        i = self._skip_ws(s, i)
        if i >= len(s):
            return None, i, False

        ch = s[i]
        if ch == '"':
            val, nxt_idx, _ = self._read_string(s, i)
            return val, nxt_idx,  False
        if ch == "{":
            obj, nxt_idx, _, invalid = self._parse_object(s, i)
            return obj, nxt_idx,  invalid

        # Anything else is invalid for our simplified grammar
        return None, i, True

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
            i = self._skip_ws(s, i)
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
            key, i, key_completed = self._read_string(s, i)
            if not key_completed:
                # if the key is not complete, return the state of the object so far
                return obj, i, True, False

            # parse the value
            i = self._skip_ws(s, i)
            if i >= len(s):
                return obj, i, True, False
            if s[i] != ":":
                return obj, i, True, False
            i += 1

            value, i, invalid = self._read_value(s, i)
            if invalid:
                # Skip over the invalid construct
                i = self._skip_invalid_value(s, i)
            elif value:
                obj[key] = value

            i = self._skip_ws(s, i)
            if i >= len(s):
                return obj, i, True, False
            if s[i] == ",":
                i += 1
                # Support trailing comma followed immediately by closing brace.
                i = self._skip_ws(s, i)
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
