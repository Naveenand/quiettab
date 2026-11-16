from cleanup import clean

# mid-line, IntelliJ already added ")" after the cursor
assert clean("10; j++) {", "for (int j = 0; j < ", ")", True) == "10; j++"
assert clean('"hi")', "IO.println(", ")", True) == '"hi"'
assert clean("bar(x))", "print(", ")", True) == "bar(x)"

# block mode: don't repeat main's closing brace
java = "for (int j = 0; j < 3; j++) {\n        IO.println(j);\n    }\n}"
assert clean(java, "void main() {\n    ", "\n}", False) == "for (int j = 0; j < 3; j++) {\n        IO.println(j);\n    }"

# block mode: stop when the next function starts
py = "return a + b\n\ndef sub(a, b):\n    return a - b"
assert clean(py, "def add(a, b):\n    ", "\n", False) == "return a + b"

print("all cleanup tests passed")

# ---- Fix 14: brackets inside strings ----
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
print("string-bracket tests passed")
