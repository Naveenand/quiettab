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