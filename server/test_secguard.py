"""Security gate tests: things it must catch, and safe look-alikes it must leave alone.
Run:  cd server && python -m pytest test_secguard.py -q
The keys below are FAKE (right shape, random letters) and are built at runtime so
GitHub's secret scanning doesn't flag this file."""
from secguard import check_suggestion, redact, redact_event, secret_near_cursor

AWS = "AKIA" + "Q7L2X9P4M8N3B5V6"
GH = "ghp_" + "a1B2c3D4e5F6g7H8i9J0k1L2m3N4o5P6q7R8"
OPENAI = "sk-proj-" + "Zx9Qw8Er7Ty6Ui5Op4As3Df2Gh1Jk0"
STRIPE = "sk_live_" + "4eC39HqLyjWDarjtT1zdp7dc"
PEM = ("-----BEGIN RSA PRIVATE KEY-----\nMIIEowIBAAKCAQEA7" + "x9Kq2Lm4Np8Rt1Vw5Yz3Bc6Df0Gh7Jk9Mn2Pq4St6Uv8Wx0Ya3Bc5"
       + "\n-----END RSA PRIVATE KEY-----")


# ------------------------------------------------------------ input redaction ----
def test_known_key_formats_are_redacted():
    for secret in (AWS, GH, OPENAI, STRIPE):
        out, rules = redact(f'client = Client(key="{secret}")\nprint(1)')
        assert secret not in out and "REDACTED" in out and rules, secret
        assert out.endswith('")\nprint(1)')          # the code around it is untouched


def test_private_key_block_redacted():
    out, rules = redact(f"KEY = '''{PEM}'''")
    assert "MIIEow" not in out and rules == ["private_key"]


def test_assigned_secrets_redacted_but_placeholders_kept():
    assert redact('db_password = "hunter2Hunter2!"')[0] == 'db_password = "REDACTED"'
    assert redact('API_KEY: "9f8e7d6c5b4a3f2e1d0c"')[0] == 'API_KEY: "REDACTED"'
    for safe in ('password = "password"', 'token = "${GITHUB_TOKEN}"', 'secret_name = "MY_SECRET_NAME"',
                 'password = "changeme"', 'token_type = "bearer_token"', 'api_key = os.environ["API_KEY"]'):
        assert redact(safe)[0] == safe, safe


def test_url_password_redacted():
    assert redact('url = "postgres://admin:S3cr3tPw@db:5432/app"')[0] == 'url = "postgres://admin:REDACTED@db:5432/app"'
    assert redact('url = "postgres://user:password@localhost/db"')[1] == []


def test_normal_code_untouched():
    code = ('sha = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"\n'   # hex hash
            'uid = "123e4567-e89b-12d3-a456-426614174000"\n'                              # UUID
            'from sklearn.linear_model import LogisticRegression  # sk-learn-compatible-estimator\n'
            'model.eval()\npassword_field = form.cleaned_data["password"]\n')
    assert redact(code) == (code, [])


def test_real_world_lookalikes_not_redacted():
    for safe in ('engine = create_engine("postgresql+psycopg2://scott:tiger@localhost/test")',
                 'uri = "postgresql://postgres:postgres@localhost:5432/pandas"',
                 'SALT_CHARS = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"',
                 '"Cryptography_HAS_TLSv1_3_FUNCTIONS": cryptography_has_tlsv13_functions,',
                 'mod = "next/dist/compiled/webpack/NodeEnvironmentPlugin"',
                 'pin = "sha256/afwiKY3RxoMmLkuRW1l7QsPZTJPwDS2pdDROQjXw8ig="',
                 'private static final String SECRET_FIELD = "secretField";',
                 'SECRET_KEY_INSECURE_PREFIX = "django-insecure-"',
                 "PASSWORDFILE = '/etc/passwd'",
                 'def set_password_and_save(self, user, password_field_name="password1", commit=True):',
                 'punycode = "xn--n8jok5ay5dzabd5bym9f0cm5685rrjetr6pdxa",',
                 'builder.add("example.com", "md5/DmxUShsZuNiqPQsX2Oi9uv2sCnw=")',
                 'const FULL_HASH_TOKEN_PREFIX = "@@webpackFullHash";',
                 '_SK_START = b"-----BEGIN OPENSSH PRIVATE KEY-----"'):
        assert redact(safe) == (safe, []), safe


def test_random_key_without_keyword_is_redacted():
    key = "Zq8" + "Lw3Rt9Xk2Vb7Nm4Pd6Hs1Jf5Gc0Ya8Ue"
    assert redact(f'headers = {{"X-Key": "{key}"}}')[0] == 'headers = {"X-Key": "REDACTED"}'


def test_tls_rule_uses_context_above_cursor():
    # multi-line call: the HTTP client is on the line above, the suggestion only adds verify=False
    assert check_suggestion("verify=False,", "    ", context="r = requests.post(\n    url,")[0] == "tls_verify_off"


def test_secret_on_cursor_line_skips_model():
    assert secret_near_cursor(f'key = "{AWS[:10]}', f'{AWS[10:]}"\n') == "aws_access_key"
    assert secret_near_cursor("x = ", "\n") is None
    assert secret_near_cursor('key = "AKIAQ7L2', '"\n') == "secret_being_typed"        # half-typed key
    assert secret_near_cursor('client = OpenAI(api_key="sk-proj-', '")\n') == "secret_being_typed"
    assert secret_near_cursor("ask = ", "\n") is None and secret_near_cursor("risk_level = ", "\n") is None


def test_events_are_redacted_before_logging():
    e = redact_event({"event": "shown", "text": f'token="{GH}"', "p_good": 0.7})
    assert GH not in e["text"] and e["p_good"] == 0.7


# ------------------------------------------------------------ output gate ----
MUST_BLOCK = [  # (line already typed, suggestion, rule)
    ("r = requests.get(url, ", "verify=False)", "tls_verify_off"),
    ("ctx = ", "ssl._create_unverified_context()", "tls_unverified_context"),
    ("const agent = new https.Agent({ ", "rejectUnauthorized: false })", "tls_reject_unauthorized_off"),
    ("tr := &http.Transport{TLSClientConfig: &tls.Config{", "InsecureSkipVerify: true}}", "tls_insecure_skip_verify"),
    ("conn.", "setHostnameVerifier((hostname, session) -> true);", "tls_trust_all"),
    ("cur.", 'execute(f"SELECT * FROM users WHERE name = \'{name}\'")', "sql_fstring"),
    ("cur.", 'execute("SELECT * FROM users WHERE id = " + user_id)', "sql_string_build"),
    ("cur.", 'execute("DELETE FROM t WHERE id = %s" % tid)', "sql_string_build"),
    ("ResultSet rs = stmt.", 'executeQuery("SELECT * FROM users WHERE id=" + id);', "sql_string_build"),
    ("result = ", "eval(input())", "eval_untrusted"),
    ("cfg = ", "yaml.load(open(path))", "yaml_unsafe_load"),
    ("h = ", "hashlib.md5(password.encode()).hexdigest()", "weak_password_hash"),
    ("claims = jwt.decode(tok, ", 'options={"verify_signature": False})', "jwt_no_verify"),
    ("cipher = AES.new(key, ", "AES.MODE_ECB)", "ecb_mode"),
    ("", 'os.system(f"rm -rf {path}")', "os_system_interpolated"),
    ("client = OpenAI(api_key=", f'"{OPENAI}")', "secret"),
    ("aws_key = ", f'"{AWS}"', "secret"),
]

MUST_ALLOW = [  # safe look-alikes
    ("r = requests.get(url, ", "verify=True, timeout=5)"),
    ("cur.", 'execute("SELECT * FROM users WHERE id = %s", (user_id,))'),
    ("cur.", 'execute("SELECT * FROM users WHERE id = ?", [user_id])'),
    ("cfg = ", "yaml.safe_load(open(path))"),
    ("cfg = ", "yaml.load(f, Loader=yaml.SafeLoader)"),
    ("", "model.eval()"),
    ("digest = ", "hashlib.sha256(data).hexdigest()"),
    ("etag = ", "hashlib.md5(content).hexdigest()"),
    ("", 'print(f"selected {n} items")'),
    ("x = ", "json.loads(text)"),
    # false alarms found by scanning 3.5M lines of real code (pandas, ansible, urllib3, okhttp, ...)
    ("res = data._mgr.take(indexer[q_idx], ", "verify=False)"),                  # pandas: not TLS
    ("file_data = ", "yaml.load(yamlfile, Loader=AnsibleLoader)"),             # explicit safe loader
    ("if context.verify_mode ", "!= ssl.CERT_NONE:"),                           # a comparison, not turning TLS off
    ("data = ", "yaml.load(trust_as_template(f), Loader=AnsibleLoader)"),      # nested brackets, explicit loader
    ("", '"from \'sha1\' to \'sha256\' in Django 2028. Pass an explicit "'),     # "Pass" is not "password"
]


def test_insecure_suggestions_blocked():
    for line, sugg, rule in MUST_BLOCK:
        blocked, _ = check_suggestion(sugg, line)
        assert blocked == rule, (line + sugg, blocked)


def test_safe_suggestions_allowed():
    for line, sugg in MUST_ALLOW:
        assert check_suggestion(sugg, line) == (None, []), line + sugg


def test_only_what_the_suggestion_adds_counts():
    # the user ALREADY typed verify=False; the suggestion only closes the call -> not QuietTab's doing
    assert check_suggestion(")", "r = requests.get(url, verify=False") == (None, [])
    # ... but if the suggestion completes the dangerous word, it counts
    assert check_suggestion("alse)", "r = requests.get(url, verify=F")[0] == "tls_verify_off"


def test_warn_rules_show_but_report():
    assert check_suggestion("subprocess.run(cmd, shell=True)", "") == (None, ["shell_true"])


def test_policy_can_change_actions():
    policy = {"tls_verify_off": "off", "shell_true": "block", "secret": "block"}
    assert check_suggestion("verify=False)", "requests.get(url, ", policy) == (None, [])
    assert check_suggestion("subprocess.run(cmd, shell=True)", "", policy)[0] == "shell_true"


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
