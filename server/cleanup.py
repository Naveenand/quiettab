OPEN, CLOSE = "([{", ")]}"


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


def clean(text: str, prefix: str, suffix: str, single_line: bool) -> str:
    cursor_line = prefix.rsplit("\n", 1)[-1]
    base_indent = len(cursor_line) - len(cursor_line.lstrip())
    if single_line:
        out = cut_at_suffix_closer(text, suffix)
    else:
        out = cut_at_unbalanced_close(text)
        out = cut_at_dedent(out, base_indent)
    return out.rstrip()