"""Self-tuning silence: learn, per repo, how likely YOU are to accept a suggestion.

The frozen gate (gate.json) was trained offline on one set of repos. On new code its numbers drift
(your own measurement: 60% precision on your repos, 16% on Real-FIM). Like a thermostat that came
set to a factory temperature: this file keeps re-reading the room and adjusts.

How it works, in four plain steps:
  1. Every suggestion has p_good from the frozen gate. Every shown suggestion ends as accepted
     (Tab, typed it, partial, followed) or rejected. Those outcomes arrive through /log.
  2. Per repo we fit  q = sigmoid(a * logit(p_good) + b + c * is_block)  = "chance YOU accept this".
     Day one (no data) the fit equals the frozen gate exactly; each outcome moves it a little.
     Repos with little data borrow strength from all your repos (user level), which borrow from the gate.
  3. Show a suggestion when q >= tau (default 0.30: Cursor's reward math, +0.75 accept / -0.25 reject,
     says showing pays off above 25%). tau is the one knob a user or admin turns: "how quiet".
  3b. Recent outcomes count more: an outcome from `half_life` labels ago counts half (code and habits change).
  4. Exploration: a hidden suggestion just below tau is shown 5% of the time (flagged explore=true).
     Without this, the gate could never learn that it is too quiet: it would never see those outcomes.

Everything is recomputed from events.jsonl, so any number this reports can be re-derived and audited.
No numpy needed: 3 parameters, solved with a few Newton steps in plain Python.
"""
import json
import math
import random
import threading
from collections import OrderedDict, deque
from pathlib import Path

GOOD = {"accepted", "typed_through", "partial", "followed"}
BAD = {"rejected"}


def logit(p: float) -> float:
    p = min(max(p, 1e-6), 1 - 1e-6)
    return math.log(p / (1 - p))


def sigmoid(z: float) -> float:
    return 1 / (1 + math.exp(-z)) if z >= 0 else math.exp(z) / (1 + math.exp(z))


def _solve3(H, g):
    """Solve H x = g for a 3x3 system (Gaussian elimination with pivoting)."""
    m = [row[:] + [g[i]] for i, row in enumerate(H)]
    for col in range(3):
        piv = max(range(col, 3), key=lambda r: abs(m[r][col]))
        m[col], m[piv] = m[piv], m[col]
        for r in range(3):
            if r != col and m[col][col]:
                f = m[r][col] / m[col][col]
                m[r] = [m[r][k] - f * m[col][k] for k in range(4)]
    return [m[i][3] / m[i][i] if m[i][i] else 0.0 for i in range(3)]


def fit(rows, prior, strength: float, min_slope: float = 0.1, weights=None):
    """MAP logistic regression: rows of (logit p_good, is_block, accepted 0/1), Gaussian prior around `prior`.
    `strength` = how many 'pretend outcomes' the prior is worth; small = learns fast, large = steady.
    `weights` = how much each row counts (recent outcomes count more)."""
    theta = list(prior)
    weights = weights or [1.0] * len(rows)
    for _ in range(30):
        g = [strength * (theta[i] - prior[i]) for i in range(3)]
        H = [[strength if i == j else 0.0 for j in range(3)] for i in range(3)]
        for (x, blk, y), wt in zip(rows, weights):
            f = (x, 1.0, blk)
            q = sigmoid(theta[0] * x + theta[1] + theta[2] * blk)
            r, w = (q - y) * wt, q * (1 - q) * wt
            for i in range(3):
                g[i] += r * f[i]
                for j in range(3):
                    H[i][j] += w * f[i] * f[j]
        step = _solve3(H, g)
        theta = [theta[i] - step[i] for i in range(3)]
        if max(abs(s) for s in step) < 1e-7:
            break
    theta[0] = max(theta[0], min_slope)      # a more confident model never means LESS likely to be accepted
    return tuple(theta)


class Repo:
    def __init__(self, window: int):
        self.labels = OrderedDict()          # sid -> [x, is_block, y]   (newest last)
        self.population = deque(maxlen=window)  # (x, is_block) of every candidate (shown or gated)
        self.window = window
        self.params = None
        self.unfitted = 0
        self.missed_good = 0                 # gate hid it, user typed it anyway
        self.explored = 0


class Tuner:
    def __init__(self, thr_line: float, thr_block: float, tau: float = 0.30, explore: float = 0.05,
                 strength_user: float = 10.0, strength_repo: float = 10.0, window: int = 3000,
                 refit_every: int = 10, half_life: float = 150.0, rng: random.Random | None = None):
        self.tau, self.explore, self.half_life = tau, explore, half_life
        self.strength_user, self.strength_repo = strength_user, strength_repo
        self.window, self.refit_every = window, refit_every
        self.rng = rng or random.Random()
        # day one: q(thr_line) = q(thr_block) = tau, so decisions equal the frozen gate exactly
        self.prior = (1.0, logit(tau) - logit(thr_line), logit(thr_line) - logit(thr_block))
        self.user_params = self.prior
        self.repos: dict[str, Repo] = {}
        self._lock = threading.Lock()        # the server refits in a worker thread while requests keep coming

    # ---------------------------------------------------------------- learning ----
    MAX_REPOS = 500

    def repo(self, name: str) -> Repo:
        name = name or "_"
        if name not in self.repos and len(self.repos) >= self.MAX_REPOS:
            name = "_"                       # memory stays bounded; extra repos share one pooled fit
        if name not in self.repos:
            self.repos[name] = Repo(self.window)
        return self.repos[name]

    def observe(self, event: dict, refit: bool = True):
        """Feed one /log event. Only events carrying sid + p_good matter.
        refit=True: refit right here when due (simple; used by tests and the simulation).
        refit=False: the server calls refit_due() in a worker thread instead."""
        ev, sid, p = event.get("event"), event.get("sid"), event.get("p_good")
        if not isinstance(p, (int, float)) or isinstance(p, bool) or not sid or not 0 <= p <= 1:
            return
        with self._lock:
            due = self._observe(event, ev, sid, p)
        if refit and due:
            self.refit(due)

    def _observe(self, event, ev, sid, p):
        r = self.repo(str(event.get("repo", "")))
        x, blk = logit(p), 1.0 if event.get("is_block") else 0.0
        if ev in ("shown", "gated"):
            r.population.append((x, blk))
            r.explored += bool(event.get("explore")) and ev == "shown"
        elif ev == "gated_typed":
            r.missed_good += 1
        elif ev in GOOD or ev in BAD:
            r.labels[sid] = [x, blk, 1.0 if ev in GOOD else 0.0]   # "followed" after "rejected" overwrites to 1
            r.labels.move_to_end(sid)
            while len(r.labels) > self.window:
                r.labels.popitem(last=False)
            r.unfitted += 1
            if r.unfitted >= self.refit_every:
                return r
        return None

    def due(self) -> bool:
        return any(r.unfitted >= self.refit_every for r in list(self.repos.values()))

    def refit_due(self):
        """Refit every repo with enough new outcomes (the server runs this off the request path)."""
        for r in [r for r in list(self.repos.values()) if r.unfitted >= self.refit_every]:
            self.refit(r)

    def _weighted(self, rows):
        n = len(rows)
        return rows, [0.5 ** ((n - 1 - i) / self.half_life) for i in range(n)]

    def refit(self, only: Repo | None = None):
        with self._lock:                     # copy the data quickly, then fit without holding the lock
            snap = {id(rp): [list(row) for row in rp.labels.values()] for rp in self.repos.values()}
            targets = [only] if only else list(self.repos.values())
            for rp in targets:
                rp.unfitted = 0
        rows, weights = [], []
        for data in snap.values():
            r, w = self._weighted(data)
            rows += r
            weights += w
        user = fit(rows, self.prior, self.strength_user, weights=weights)
        fitted = {}
        for rp in targets:
            data, w = self._weighted(snap[id(rp)])
            fitted[id(rp)] = fit(data, user, self.strength_repo, weights=w)
        with self._lock:
            self.user_params = user
            for rp in targets:
                rp.params = fitted[id(rp)]

    def load(self, paths):
        """Rebuild everything from the event logs (oldest file first)."""
        for path in paths:
            if Path(path).exists():
                for line in Path(path).read_text(errors="ignore").splitlines():
                    try:
                        self.observe(json.loads(line), refit=False)
                    except (json.JSONDecodeError, TypeError, AttributeError):
                        continue
        self.refit()

    # ---------------------------------------------------------------- deciding ----
    def params(self, repo: str):
        r = self.repos.get(repo or "_")
        return r.params if r and r.params else self.user_params

    def q(self, repo: str, p_good: float, is_block: bool) -> float:
        a, b, c = self.params(repo)
        return sigmoid(a * logit(p_good) + b + c * (1.0 if is_block else 0.0))

    def decide(self, repo: str, p_good: float | None, is_block: bool) -> dict:
        """-> {"show", "q", "tau", "explore"}. Explore: q in [tau/2, tau) is shown with probability `explore`."""
        if p_good is None:
            return {"show": False, "q": None, "tau": self.tau, "explore": False}
        q = self.q(repo, p_good, is_block)
        if q >= self.tau:
            return {"show": True, "q": q, "tau": self.tau, "explore": False}
        explore = q >= self.tau / 2 and self.rng.random() < self.explore
        return {"show": explore, "q": q, "tau": self.tau, "explore": explore}

    # ---------------------------------------------------------------- auditing ----
    def report(self, repo: str) -> dict:
        """Everything a user or admin needs to trust the silence: fit, show rate, precision, calibration."""
        r = self.repos.get(repo or "_")
        if r is None:
            return {"repo": repo, "labels": 0, "note": "no events yet: using your user-level fit / the frozen gate"}
        a, b, c = self.params(repo)
        qs = lambda th, rows: [sigmoid(th[0] * x + th[1] + th[2] * blk) for x, blk in rows]  # noqa: E731
        pop = list(r.population)

        def policy(th):
            q = qs(th, pop)
            shown = [v for v in q if v >= self.tau]
            # expected acceptance of what this policy shows, judged by the CURRENT fit (best estimate we have)
            judged = qs((a, b, c), [row for row, v in zip(pop, q) if v >= self.tau])
            return {"show_rate": round(len(shown) / len(q), 3) if q else None,
                    "expected_accept_rate": round(sum(judged) / len(judged), 3) if judged else None}

        labels = list(r.labels.values())
        pred = qs((a, b, c), [(x, blk) for x, blk, _ in labels])
        bins = []
        for lo in (0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9):
            idx = [i for i, v in enumerate(pred) if lo <= v < lo + 0.1 or (lo == 0.9 and v == 1.0)]
            if idx:
                bins.append({"predicted": round(sum(pred[i] for i in idx) / len(idx), 3),
                             "actual": round(sum(labels[i][2] for i in idx) / len(idx), 3), "n": len(idx)})
        ece = sum(bn["n"] * abs(bn["predicted"] - bn["actual"]) for bn in bins) / len(labels) if labels else None
        return {
            "repo": repo, "labels": len(labels), "candidates_seen": len(pop),
            "accept_rate_of_labeled": round(sum(y for *_, y in labels) / len(labels), 3) if labels else None,
            "params": {"a": round(a, 3), "b": round(b, 3), "c": round(c, 3)},
            "tau": self.tau, "explore": self.explore, "explored_shown": r.explored,
            "missed_good": r.missed_good,
            "tuned": policy((a, b, c)),
            "frozen_gate": policy(self.prior),
            "calibration": {"ece": round(ece, 3) if ece is not None else None, "bins": bins},
        }
