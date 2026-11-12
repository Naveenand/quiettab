OPEN, CLOSE = "([{", ")]}"
MAX_LINES = 8          # block mode: never suggest more than this many lines
MIN_REPEAT_CHARS = 15  # ignore tiny suggestions like "}" or "i++;" in the repeat check


def cut_at_suffix_closer(text: str, suffix: str) -> str:
    """Mid-line: if the rest of the line already starts with a closer like ) or ",
    stop where the model writes that same closer (at bracket depth 0)."""
    rest = suffix.split("\n", 1)[0].strip()
    if not rest or rest[0] not in ")]}\"';":
        return text
    target, depth = rest[0], 0
    for i, ch in enumerate(text):
        if ch == target and depth == 0:
            return text[:i]
        if ch in OPEN:
            depth += 1
        elif ch in CLOSE:
            depth -= 1
    return text


def cut_at_unbalanced_close(text: str) -> str:
    """Block mode: stop at a } ) ] that closes something opened BEFORE the suggestion."""
    depth = 0
    for i, ch in enumerate(text):
        if ch in OPEN:
            depth += 1
        elif ch in CLOSE:
            depth -= 1
            if depth < 0:
                return text[:i]
    return text


def cut_at_dedent(text: str, base_indent: int) -> str:
    """Block mode: stop at the first line indented LESS than where the cursor is."""
    lines = text.split("\n")
    kept = [lines[0]]
    for line in lines[1:]:
        if line.strip() and len(line) - len(line.lstrip()) < base_indent:
            break
        kept.append(line)
    return "\n".join(kept)


def cut_at_block_end(text: str, base_indent: int) -> str:
    """Block mode: if the first line opens a block ("...:"), stop after that block's body,
    at the next line back at the cursor's indent (except else/elif/except/finally)."""
    lines = text.split("\n")
    if not lines[0].rstrip().endswith(":"):
        return text
    kept, seen_body = [lines[0]], False
    for line in lines[1:]:
        s = line.strip()
        indent = len(line) - len(line.lstrip())
        if s and indent <= base_indent and seen_body and not s.startswith(("else", "elif", "except", "finally")):
            break
        if s and indent > base_indent:
            seen_body = True
        kept.append(line)
    return "\n".join(kept)


def trim_suffix_overlap(text: str, suffix: str, min_overlap: int = 3) -> str:
    """If the suggestion ENDS with code that already comes right after the cursor, cut that part.
    e.g. text = "foo(x);\\n}"  suffix = "}\\n..."  -> overlap is only 1 char, kept
         text = "return a + b;"  suffix = "return a + b;\\n}"  -> everything overlaps -> "" """
    t = text.rstrip()
    head = suffix.lstrip()
    for k in range(min(len(t), len(head)), min_overlap - 1, -1):
        if t.endswith(head[:k]):
            return t[:-k].rstrip()
    return text


def _real_lines(s: str) -> set[str]:
    """Lines with real content (4+ chars after stripping), whitespace-trimmed."""
    return {line.strip() for line in s.split("\n") if len(line.strip()) >= 4}


def is_repeat(text: str, prefix: str, suffix: str) -> bool:
    """True if most lines the suggestion would create already exist elsewhere in the file window."""
    cursor_line = prefix.rsplit("\n", 1)[-1]
    above = prefix.rsplit("\n", 1)[0] if "\n" in prefix else ""
    below = suffix.split("\n", 1)[1] if "\n" in suffix else ""
    seen = _real_lines(above) | _real_lines(below)

    # the lines as they'd look after accepting (first line includes what you already typed)
    new_lines = [l.strip() for l in (cursor_line + text).split("\n") if len(l.strip()) >= 4]
    if len(new_lines) < 2 or sum(len(l) for l in new_lines) < MIN_REPEAT_CHARS:
        return False   # one line repeating is normal in real code -> only judge multi-line copies
    copied = sum(1 for l in new_lines if l in seen)
    return copied / len(new_lines) >= 0.6


def clean(text: str, prefix: str, suffix: str, single_line: bool) -> str:
    cursor_line = prefix.rsplit("\n", 1)[-1]
    base_indent = len(cursor_line) - len(cursor_line.lstrip())
    if single_line:
        out = cut_at_suffix_closer(text, suffix)
    else:
        out = cut_at_unbalanced_close(text)
        out = cut_at_dedent(out, base_indent)
        out = cut_at_block_end(out, base_indent)
        out = "\n".join(out.split("\n")[:MAX_LINES])
    out = trim_suffix_overlap(out, suffix)
    if is_repeat(out, prefix, suffix):
        return ""
    return out.rstrip()