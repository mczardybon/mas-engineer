"""Control file: NO bugs expected.

Clean, working code. All 3 sub-agents should report 0 findings on this file.
This tests for false positives.
"""


def add(a: int, b: int) -> int:
    """Add two integers."""
    return a + b


def greet(name: str) -> str:
    """Return a greeting."""
    return f"Hello, {name}!"


def main() -> int:
    result = add(2, 3)
    print(greet("world"))
    return result


if __name__ == "__main__":
    main()
