"""Security gate: two jobs, both independent of which model is plugged in.

1. INPUT  - secrets in your code never reach the model or the logs.
            Like blacking out a card number before photocopying a page.
            redact(text) replaces the secret value with REDACTED; the rest of the code stays as is.
            If the secret is on the line you're typing, we don't call the model at all.

2. OUTPUT - QuietTab refuses to suggest secrets or known-dangerous code
            (TLS checks off, SQL built from strings, yaml.load, eval(input()), ...).
            Like a spell checker for security that removes the word before you see it.
            Each refusal has a rule id, so it can be counted, audited and turned off per team.

A company can change what each rule does in security_policy.json:
    {"rules": {"shell_true": "warn", "pickle_load": "off"}}
    block = never show it,  warn = show it but log the rule id,  off = ignore the rule.
"""
import json
import math
import os
import re
from pathlib import Path

PLACEHOLDER = "REDACTED"

# ---------------------------------------------------------------- secrets ----
# (rule id, regex, which group is the secret value: 0 = the whole match)
SECRET_RULES = [
    # header + real key data after it (a lone header string, e.g. in a parser, is not a secret)
    ("private_key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----(?=[\s\S]{0,80}?[A-Za-z0-9+/]{20})"
                               r"(?:[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----|[\s\S]*)"), 0),
    ("aws_access_key", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"), 0),
    ("github_token", re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{36,255}|github_pat_[A-Za-z0-9_]{60,255})\b"), 0),
    ("gitlab_token", re.compile(r"\bglpat-[A-Za-z0-9_\-]{20,}\b"), 0),
    ("slack_token", re.compile(r"\bxox[abposr]-[A-Za-z0-9-]{10,}\b"), 0),
    ("slack_webhook", re.compile(r"https://hooks\.slack\.com/services/[A-Za-z0-9/]{20,}"), 0),
    ("google_api_key", re.compile(r"\bAIza[0-9A-Za-z_\-]{35}\b"), 0),
    ("stripe_key", re.compile(r"\b(?:sk|rk)_(?:live|test)_[0-9A-Za-z]{16,}\b"), 0),
    # OpenAI / Anthropic style: sk-..., must mix upper case and digits (so "sk-learn-compatible" is fine)
    ("llm_api_key", re.compile(r"\bsk-(?:proj-|svcacct-|ant-(?:api\d\d-)?)?(?=[A-Za-z0-9_-]*\d)(?=[A-Za-z0-9_-]*[A-Z])[A-Za-z0-9_-]{20,}"), 0),
    ("huggingface_token", re.compile(r"\bhf_[A-Za-z0-9]{30,}\b"), 0),
    ("npm_token", re.compile(r"\bnpm_[A-Za-z0-9]{36}\b"), 0),
    ("jwt", re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}"), 0),
    ("url_password", re.compile(r"\b[a-z][a-z0-9+.\-]*://[^\s:/@'\"]+:([^\s@/'\"]{3,})@"), 1),
    # password = "....", api_key: '....'  (only if the value looks like a real secret, see looks_secret)
    ("assigned_secret", re.compile(
        r"(?i)\b[A-Za-z0-9_]*(?:password|passwd|pwd|secret|token|api_?key|access_?key|private_?key|auth_?key)[A-Za-z0-9_]*"
        r"[\"']?\s*(?::=|==|=|:)\s*([\"'])([^\"'\s]{8,})\1"), 2),
    # a long random-looking string with no keyword around it (e.g. a pasted key)
    ("high_entropy_string", re.compile(r"([\"'])([A-Za-z0-9+/=_\-]{32,})\1"), 2),
]
PLACEHOLDER_WORDS = {"password", "passwd", "secret", "changeme", "changeit", "example", "redacted",
                     "xxxxxxxx", "your_token", "your-api-key", "token", "dummy", "placeholder", "pass",
                     "tiger", "postgres", "root", "admin", "user", "guest", "test", "mysql"}
ALPHABETS = ("abcdef", "ABCDEF", "012345", "qwerty")


def entropy(s: str) -> float:
    """Bits per character. English words ~2.5-3.5, random base64 ~5+, hex hashes max 4."""
    return -sum(s.count(c) / len(s) * math.log2(s.count(c) / len(s)) for c in set(s)) if s else 0.0


def looks_secret(value: str, strict: bool) -> bool:
    """Is this string a real secret, or a placeholder / normal word / env var name?"""
    v = value.lower()
    if v in PLACEHOLDER_WORDS or any(ch in value for ch in "${}<>%") or re.fullmatch(r"[A-Z0-9_]+", value) \
            or re.fullmatch(r"[a-z_.]+", value) or v.startswith(("http", "test", "fake", "dummy", "example")):
        return False
    if any(a in value for a in ALPHABETS) or value.startswith(("sha256/", "sha1/", "md5/", "xn--")) \
            or any(w in v for w in ("password", "secret", "token", "example")):   # alphabets, cert pins, punycode, names
        return False
    kinds = sum(bool(re.search(p, value)) for p in (r"[a-z]", r"[A-Z]", r"\d", r"[^A-Za-z0-9]"))
    digits = sum(c.isdigit() for c in value)
    if strict:   # no keyword nearby: must look truly random (hex hashes, UUIDs, names and paths stay)
        wordy = (re.search(r"[a-z]{7,}|[A-Z]{7,}", value) is not None
                 or len(re.findall(r"[A-Z][a-z]{3,}", value)) >= 4)
        return kinds >= 3 and digits >= 2 and not wordy and entropy(value) >= 4.3
    # after "password =" etc.: a real secret mixes kinds of characters and has a digit
    return kinds >= 2 and digits >= 1 and entropy(value) >= 2.5


def find_secrets(text: str) -> list[tuple[int, int, str]]:
    """(start, end, rule id) of every secret value, non-overlapping, left to right."""
    spans = []
    for rule, rx, group in SECRET_RULES:
        for m in rx.finditer(text):
            start, end = m.span(group)
            if rule in ("url_password", "assigned_secret", "high_entropy_string") \
                    and not looks_secret(m.group(group), strict=rule == "high_entropy_string"):
                continue
            if all(end <= s or start >= e for s, e, _ in spans):
                spans.append((start, end, rule))
    return sorted(spans)


def redact(text: str) -> tuple[str, list[str]]:
    """Replace each secret value with REDACTED. Returns (new text, rule ids found)."""
    spans = find_secrets(text)
    for start, end, _ in reversed(spans):
        text = text[:start] + PLACEHOLDER + text[end:]
    return text, [r for _, _, r in spans]


# The START of a known key format: someone is typing or pasting a key right now
SECRET_START = re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{4,}|\bgh[pousr]_[A-Za-z0-9]{4,}|\bgithub_pat_|\bglpat-|\bxox[abposr]-|"
                          r"\bAIza[0-9A-Za-z_\-]{4,}|\b[sr]k_live_|\bsk-(?:proj|ant|svcacct)-|\bhf_[A-Za-z0-9]{6,}|"
                          r"-----BEGIN [A-Z ]*PRIVATE KEY")


def secret_near_cursor(prefix: str, suffix: str) -> str | None:
    """A secret (or the start of one) on the line being typed -> don't call the model at all:
    we'd have to hide exactly what you're typing, and the model would see part of a real key."""
    line = prefix.rsplit("\n", 1)[-1] + suffix.split("\n", 1)[0]
    spans = find_secrets(line)
    if spans:
        return spans[0][2]
    return "secret_being_typed" if SECRET_START.search(line) else None


# ------------------------------------------------------------ insecure code ----
def _yaml_unsafe(m: re.Match, around: str) -> bool:
    """yaml.load(x) with no Loader, or with Loader / UnsafeLoader / FullLoader, can run code."""
    line_end = m.string.find("\n", m.start())
    loader = re.search(r"Loader\s*=\s*([\w.]+)", m.string[m.start():line_end if line_end >= 0 else None])
    return loader is None or loader.group(1).split(".")[-1] in ("Loader", "UnsafeLoader", "FullLoader")


HTTP_CONTEXT = re.compile(r"\b(?:requests|httpx|aiohttp|urllib3|session|Session|client|Client|http)\b|"
                          r"\.(?:get|post|put|patch|delete|head|request|stream|urlopen)\s*\(")


SQL = r"(?:SELECT|INSERT|UPDATE|DELETE|DROP|ALTER|CREATE)\b"
# a string that is clearly a SQL statement (keyword + its partner), not a log message like f"selected {n}"
SQL_STMT = r"(?:SELECT\b[\s\S]{1,200}?\bFROM|INSERT\s+INTO|UPDATE\b[\s\S]{1,100}?\bSET|DELETE\s+FROM)\b"
QUOTED = r"(\"\"\"|'''|[\"'])"          # group 1 = the opening quote; (?:(?!\1)[\s\S]) = any char before the closing one


def _world_writable(m: re.Match, around: str) -> bool:
    return bool(int(m.group(1), 8) & 0o002)


# (rule id, default action, regex, optional extra check on the match)
CODE_RULES = [
    # pandas also has verify=False (meaning something else): only flag it next to an HTTP client
    ("tls_verify_off", "block", re.compile(r"\bverify\s*=\s*False\b"), lambda m, around: HTTP_CONTEXT.search(around) is not None),
    ("tls_unverified_context", "block", re.compile(r"ssl\._create_unverified_context\s*\(|(?:verify_mode|cert_reqs)\s*=\s*[\"']?(?:ssl\.)?CERT_NONE\b|"
                                                   r"\bcheck_hostname\s*=\s*False\b"), None),
    ("tls_reject_unauthorized_off", "block", re.compile(r"rejectUnauthorized\s*:\s*false|NODE_TLS_REJECT_UNAUTHORIZED\s*=\s*[\"']?0"), None),
    ("tls_insecure_skip_verify", "block", re.compile(r"InsecureSkipVerify\s*:\s*true"), None),
    ("tls_trust_all", "block", re.compile(r"ALLOW_ALL_HOSTNAME_VERIFIER|NoopHostnameVerifier|TrustAllStrategy|"
                                          r"setHostnameVerifier\s*\(\s*\(?[\w\s,]*\)?\s*->\s*true"), None),
    ("sql_fstring", "block", re.compile(r"(?i)\b(?:execute|executemany|executescript|raw|query|exec_driver_sql|text)\s*\(\s*f([\"'])"
                                        r"(?:(?!\1)[^\n])*?" + SQL + r"(?:(?!\1)[^\n])*?\{"), None),
    ("sql_string_build", "block", re.compile(r"(?i)\b(?:execute|executemany|executeQuery|executeUpdate|prepareStatement|createQuery|createNativeQuery|query|raw)"
                                             r"\s*\(\s*([\"'])(?:(?!\1)[^\n])*" + SQL + r"(?:(?!\1)[^\n])*\1\s*(?:%|\+|\.format\s*\()"), None),
    # SQL text built anywhere, e.g. query = "SELECT * FROM t WHERE id = '%s'" % x  (also triple-quoted, multi-line)
    ("sql_string_build", "block", re.compile(r"(?i)" + QUOTED + r"(?:(?!\1)[\s\S]){0,300}?" + SQL_STMT +
                                             r"(?:(?!\1)[\s\S]){0,300}?\1\s*(?:%\s*[\w(]|\+\s*\w|\.format\s*\()"), None),
    ("sql_fstring", "block", re.compile(r"(?i)\bf" + QUOTED + r"(?:(?!\1)[\s\S]){0,300}?" + SQL_STMT +
                                        r"(?:(?!\1)[\s\S]){0,300}?\{"), None),
    ("weak_cipher", "block", re.compile(r"\b(?:ARC2|ARC4|DES|DES3|Blowfish|XOR)\.new\s*\(|\balgorithms\.(?:ARC4|Blowfish|IDEA|TripleDES)\s*\(|"
                                        r"\bmodes\.ECB\s*\(|Cipher\.getInstance\s*\(\s*\"(?:DES|DESede|RC4|AES/ECB)"), None),
    ("eval_untrusted", "block", re.compile(r"(?<![\w.$])(?:eval|exec)\s*\(\s*(?:input\s*\(|request\.|req\.|sys\.argv|params\b|location\.)"), None),
    ("yaml_unsafe_load", "block", re.compile(r"\byaml\.(?:load\s*\(([^)\n]*)\)|unsafe_load\s*\(|full_load\s*\()"),
     lambda m, around: m.group(1) is None or _yaml_unsafe(m, around)),
    ("weak_password_hash", "block", re.compile(r"(?i)(?:\b(?:md5|sha1)\b[^\n]{0,40}\b(?:password|passwd|pwd)\b|\b(?:password|passwd|pwd)\w*\s*=\s*[^\n]{0,40}\b(?:md5|sha1)\b)"), None),
    ("jwt_no_verify", "block", re.compile(r"[\"']verify_signature[\"']\s*:\s*False|algorithms\s*=\s*\[\s*[\"']none[\"']", re.I), None),
    ("ecb_mode", "block", re.compile(r"\bMODE_ECB\b|/ECB/"), None),
    ("shell_true", "warn", re.compile(r"\bshell\s*=\s*(?:True\b|1\b|[\"'](?!False|None|0)[^\"']+[\"'])"), None),
    ("os_system_interpolated", "block", re.compile(r"\bos\.(?:system|popen)\s*\(\s*(?:f[\"']|[^)\n]*\+\s*\w)"), None),
    ("pickle_load", "warn", re.compile(r"\b(?:pickle|cPickle|dill|marshal)\.loads?\s*\(|\b(?:pickle|cPickle|dill)\.Unpickler\s*\(|"
                                      r"\bjsonpickle\.(?:unpickler\.)?decode\s*\(|\bshelve\.open\s*\(|\bread_pickle\s*\("), None),
    ("eval_call", "warn", re.compile(r"(?<![\w.$])eval\s*\("), None),
    ("chmod_world_writable", "warn", re.compile(r"\bchmod\s*\(\s*[^,\n]+,\s*0o?([0-7]{1,4})\s*\)"), _world_writable),
    ("chmod_777", "warn", re.compile(r"\bchmod\s+(?:-R\s+)?[0-7]?777\b"), None),
    ("flask_debug", "warn", re.compile(r"\.run\s*\([^)\n]*\bdebug\s*=\s*True"), None),
    ("inner_html", "warn", re.compile(r"\.innerHTML\s*=\s*(?![\"'`]\s*[\"'`;])|dangerouslySetInnerHTML"), None),
]

POLICY_PATH = Path(os.getenv("QT_SECURITY_POLICY", Path(__file__).parent / "security_policy.json"))


def load_policy(path: Path = POLICY_PATH) -> dict[str, str]:
    """rule id -> block / warn / off. Defaults come from CODE_RULES; the file can override any of them."""
    actions = {rule: action for rule, action, _, _ in CODE_RULES}
    actions["secret"] = "block"
    if path.exists():
        for rule, action in json.loads(path.read_text()).get("rules", {}).items():
            if rule in actions and action in ("block", "warn", "off"):
                actions[rule] = action
    return actions


POLICY = load_policy()


def check_suggestion(text: str, cursor_line: str = "", policy: dict[str, str] | None = None,
                     context: str = "") -> tuple[str | None, list[str]]:
    """Look at the line being typed + the suggestion, but only flag what the SUGGESTION adds.
    `context` = a few lines above the cursor, used only to understand a match (e.g. is this an HTTP call?).
    Returns (rule id to block or None, [rule ids to warn about])."""
    policy = POLICY if policy is None else policy
    full, start = cursor_line + text, len(cursor_line)
    around = context + "\n" + full
    if policy.get("secret") != "off" and any(e > start for _, e, _ in find_secrets(full)):
        return "secret", []
    warns = []
    for rule, _, rx, extra in CODE_RULES:
        action = policy.get(rule, "off")
        if action == "off":
            continue
        for m in rx.finditer(full):
            if m.end() > start and (extra is None or extra(m, around)):
                if action == "block":
                    return rule, warns
                warns.append(rule)
                break
    return None, warns


def redact_event(event: dict) -> dict:
    """Before writing an event to events.jsonl: black out secrets in every text field."""
    return {k: redact(v)[0] if isinstance(v, str) else v for k, v in event.items()}
