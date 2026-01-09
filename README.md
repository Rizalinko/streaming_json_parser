# Streaming JSON Parser

A lightweight, incremental JSON parser in Python that can return the best-effort parsed state at any time—ideal for handling partial responses from streaming sources like LLM output. The parser supports a subset of JSON where values are strings or nested objects (no arrays, no escape sequences, and no duplicate keys).

## Problem Statement

Given a streaming JSON input, we need to:
- Consume arbitrary chunks of text via `consume(buffer: str)`.
- Expose the current parse state via `get()`, even if the input is incomplete.
- Include partially parsed string values, but only emit key/value pairs once the value type is determined.
- Avoid emitting partially parsed keys.  
  - Example: `{"test": "hello", "worl` is represented as `{"test": "hello"}` (key `worl` is not emitted until its value type is known).
  - Example: `{"test": "hello", "country": "Switzerl` is represented as `{"test": "hello", "country": "Switzerl"}`.

## Supported JSON Subset

- Value types: strings and objects.
- Strings: no escape sequences are expected/handled.
- Objects: keys are strings; duplicate keys are not expected.
- Arrays, numbers, booleans, and null are out of scope.

## API

### `StreamingJsonParser`

- `__init__()`: Initialize parser state.
- `consume(buffer: str) -> None`: Feed the parser with the next chunk of JSON text.
- `get() -> object`: Return the best-effort parsed Python object (dicts/strings) reflecting all consumed input.

## Usage

```py
from streaming_json_parser import StreamingJsonParser

parser = StreamingJsonParser()
parser.consume('{"foo":')
parser.consume('"bar"}')
print(parser.get())  # {"foo": "bar"}
```

### Examples (from requirements)

```py
def test_streaming_json_parser():
    parser = StreamingJsonParser()
    parser.consume('{"foo": "bar"}')
    assert parser.get() == {"foo": "bar"}

def test_chunked_streaming_json_parser():
    parser = StreamingJsonParser()
    parser.consume('{"foo":')
    parser.consume('"bar')
    assert parser.get() == {"foo": "bar"}

def test_partial_streaming_json_parser():
    parser = StreamingJsonParser()
    parser.consume('{"foo": "bar')
    assert parser.get() == {"foo": "bar"}
```

## Design Notes

- **Streaming-friendly:** Maintains internal state across `consume` calls.
- **Partial output:** Emits only validated key/value pairs; string values can be partial.
- **Efficiency:** Single-pass incremental parsing without loading the full input.

## Assumptions

- Inputs are UTF-8 text.
- No escape sequences in strings.
- No duplicate keys.
- Only string and object value types are present.

## Getting Started

1. Ensure Python 3.9+ (adjust if your code supports other versions).
2. Install dependencies (if any). If none, skip.
3. Run tests:
   ```bash
   python -m pytest
   ```
   or
   ```bash
   python -m unittest
   ```

## File Naming for Submission

Per the prompt, submit as a single Python file named:
```
$givenName_$familyName_streaming_json_parser.py
```

## Future Improvements

- Support additional JSON types (arrays, numbers, booleans, null).
- Handle string escape sequences.
- Detect and report duplicate keys.
- Add error recovery for malformed input.
