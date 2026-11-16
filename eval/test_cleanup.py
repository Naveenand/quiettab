"""Cleanup rules (server/cleanup.py). Run:  cd server && python -m pytest test_cleanup.py -q
(also works as a plain script: python test_cleanup.py)"""
from cleanup import clean


def test_mid_line_closer_already_typed():
    # mid-line, IntelliJ already added ")" after the cursor
    assert clean("10; j++) {", "for (int j = 0; j < ", ")", True) == "10; j++"
    assert clean('"hi")', "IO.println(", ")", True) == '"hi"'
    assert clean("bar(x))", "print(", ")", True) == "bar(x)"


def test_block_mode_stops_in_the_right_place():
    # don't repeat main's closing brace
    java = "for (int j = 0; j < 3; j++) {\n        IO.println(j);\n    }\n}"
    assert clean(java, "void main() {\n    ", "\n}", False) == "for (int j = 0; j < 3; j++) {\n        IO.println(j);\n    }"
    # stop when the next function starts
    py = "return a + b\n\ndef sub(a, b):\n    return a - b"
    assert clean(py, "def add(a, b):\n    ", "\n", False) == "return a + b"


def test_brackets_inside_strings():   # Fix 14
    # mid-line: the "(" inside the string must not hide the real ")" closer
    assert clean('"(")', "print(", ")", True) == '"("'
    assert clean('"a)b", x)', "f(", ")", True) == '"a)b", x'
    # mid-line, cursor INSIDE a string: stop at the quote that closes it
    assert clean('lo world")', 'print("hel', '")', True) == "lo world"
    # escaped quote inside the string doesn't end it
    assert clean('"say \\"(\\"")', "print(", ")", True) == '"say \\"(\\""'
    # single quotes too
    assert clean("'[', 2]", "x = [", "]", True) == "'[', 2"
    # block mode: a ")" inside a string must not cut the block early
    blk = 'print(")")\n    return x'
    assert clean(blk, "def f(x):\n    ", "\n", False) == blk
    # block mode: a real unbalanced close still cuts (old behavior kept)
    assert clean("a = 1\n}", "void f() {\n    ", "\n}", False) == "a = 1"


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)