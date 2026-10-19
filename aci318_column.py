"""
Slender reinforced-concrete column design per ACI 318-19.

Units used internally: N, mm, MPa (N/mm^2), N·mm.
Sign convention: compression positive.

Code references (ACI 318-19):
    6.2.5      Slenderness limits
    6.6.4.4    Stability properties (EI)eff, Pc
    6.6.4.5    Moment magnification - nonsway frames
    6.6.4.6    Moment magnification - sway frames
    10.6.1.1   Reinforcement ratio limits
    21.2.2     Strength reduction factor phi
    22.2.2     Equivalent rectangular stress block (beta1)
    22.4.2     Maximum axial strength Pn,max
    25.7.2     Tie spacing
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

EPS_CU = 0.003  # 22.2.2.1

# Nominal bar diameters (mm) -> area (mm^2)
BAR_SIZES = {
    "DB10": 10, "DB12": 12, "DB16": 16, "DB20": 20, "DB25": 25,
    "DB28": 28, "DB32": 32, "DB36": 36, "DB40": 40,
}
TIE_SIZES = {"RB6": 6, "RB9": 9, "DB10": 10, "DB12": 12, "DB16": 16}


def bar_area(db: float) -> float:
    return math.pi * db ** 2 / 4.0


# --------------------------------------------------------------------------
# Section definition
# --------------------------------------------------------------------------
@dataclass
class Bar:
    x: float   # mm, horizontal coordinate from section centre (for drawing)
    d: float   # mm, depth from extreme compression fibre
    area: float


@dataclass
class Section:
    shape: str                 # "rect" or "circ"
    b: float                   # mm (rect width, perpendicular to bending) / D for circular
    h: float                   # mm (depth in bending direction) / D for circular
    cover: float               # clear cover to ties/spiral, mm
    db: float                  # longitudinal bar diameter, mm
    dt: float                  # tie / spiral bar diameter, mm
    bars: list[Bar] = field(default_factory=list)

    @property
    def Ag(self) -> float:
        if self.shape == "circ":
            return math.pi * self.h ** 2 / 4.0
        return self.b * self.h

    @property
    def Ig(self) -> float:
        if self.shape == "circ":
            return math.pi * self.h ** 4 / 64.0
        return self.b * self.h ** 3 / 12.0

    @property
    def Ast(self) -> float:
        return sum(bar.area for bar in self.bars)

    @property
    def Ise(self) -> float:
        """Moment of inertia of reinforcement about the centroidal axis."""
        return sum(bar.area * (bar.d - self.h / 2.0) ** 2 for bar in self.bars)

    @property
    def r(self) -> float:
        """Radius of gyration permitted by 6.2.5.2."""
        return 0.25 * self.h if self.shape == "circ" else 0.30 * self.h

    @property
    def d_edge(self) -> float:
        """Distance from face to centre of longitudinal bars."""
        return self.cover + self.dt + self.db / 2.0

    @property
    def n_bars(self) -> int:
        return len(self.bars)


def make_rect_section(b, h, cover, db, dt, n_b, n_h) -> Section:
    """Rectangular section.

    n_b : bars along each face of width b (top & bottom faces, incl. corners)
    n_h : bars along each face of depth h (side faces, incl. corners)
    """
    sec = Section("rect", b, h, cover, db, dt)
    de = sec.d_edge
    As = bar_area(db)
    ys = np.linspace(de, h - de, n_h)
    xs_full = np.linspace(-(b / 2 - de), b / 2 - de, n_b)
    for i, d in enumerate(ys):
        if i == 0 or i == n_h - 1:
            for x in xs_full:
                sec.bars.append(Bar(float(x), float(d), As))
        else:
            for x in (xs_full[0], xs_full[-1]):
                sec.bars.append(Bar(float(x), float(d), As))
    return sec


def make_circ_section(D, cover, db, dt, n) -> Section:
    sec = Section("circ", D, D, cover, db, dt)
    rs = D / 2.0 - sec.d_edge
    As = bar_area(db)
    for i in range(n):
        th = 2 * math.pi * i / n
        sec.bars.append(Bar(rs * math.sin(th), D / 2.0 - rs * math.cos(th), As))
    return sec


# --------------------------------------------------------------------------
# Material helpers
# --------------------------------------------------------------------------
def beta1(fc: float) -> float:
    """Table 22.2.2.4.3"""
    if fc <= 28.0:
        return 0.85
    return max(0.65, 0.85 - 0.05 * (fc - 28.0) / 7.0)


def Ec_normal(fc: float) -> float:
    """19.2.2.1(b) normal-weight concrete, MPa"""
    return 4700.0 * math.sqrt(fc)


def phi_factor(eps_t: float, eps_ty: float, transverse: str) -> float:
    """Table 21.2.2 (ACI 318-19). eps_t: net tensile strain (tension +)."""
    phi_c = 0.75 if transverse == "spiral" else 0.65
    if eps_t <= eps_ty:
        return phi_c
    if eps_t >= eps_ty + 0.003:
        return 0.90
    return phi_c + (0.90 - phi_c) * (eps_t - eps_ty) / 0.003


# --------------------------------------------------------------------------
# P-M interaction diagram (strain compatibility)
# --------------------------------------------------------------------------
def _concrete_block(sec: Section, a: float) -> tuple[float, float]:
    """Area of compression block and lever arm of its centroid about section centre."""
    h = sec.h
    a = min(max(a, 0.0), h)
    if sec.shape == "rect":
        return sec.b * a, h / 2.0 - a / 2.0
    R = h / 2.0
    if a >= h:
        return math.pi * R ** 2, 0.0
    th = math.acos((R - a) / R)
    area = R ** 2 * (th - math.sin(th) * math.cos(th))
    if area <= 0:
        return 0.0, 0.0
    ybar = 2.0 * R * math.sin(th) ** 3 / (3.0 * (th - math.sin(th) * math.cos(th)))
    return area, ybar


def section_forces(sec: Section, c: float, fc: float, fy: float, Es: float):
    """Nominal (Pn, Mn, eps_t) for a neutral-axis depth c (mm)."""
    a = beta1(fc) * c
    Ac, lever = _concrete_block(sec, a)
    Cc = 0.85 * fc * Ac
    Pn = Cc
    Mn = Cc * lever
    d_t = max(bar.d for bar in sec.bars)
    for bar in sec.bars:
        eps = EPS_CU * (c - bar.d) / c
        fs = max(-fy, min(fy, Es * eps))
        if bar.d < min(a, sec.h) and fs > 0:
            fs -= 0.85 * fc  # displaced concrete
        F = fs * bar.area
        Pn += F
        Mn += F * (sec.h / 2.0 - bar.d)
    eps_t = EPS_CU * (d_t - c) / c
    return Pn, Mn, eps_t


@dataclass
class Interaction:
    Mn: np.ndarray
    Pn: np.ndarray
    phiMn: np.ndarray
    phiPn: np.ndarray
    phi: np.ndarray
    c: np.ndarray
    Po: float
    Pn_max: float
    phiPn_max: float
    Pnt: float
    balanced: tuple[float, float]  # (phiMn, phiPn) at eps_t = eps_ty


def interaction_diagram(sec: Section, fc, fy, Es, transverse="tied", n=400) -> Interaction:
    h = sec.h
    Ast = sec.Ast
    Po = 0.85 * fc * (sec.Ag - Ast) + fy * Ast            # 22.4.2.2
    Pnt = -fy * Ast                                         # 22.4.3
    ratio = 0.85 if transverse == "spiral" else 0.80        # Table 22.4.2.1
    Pn_max = ratio * Po
    phi_c = 0.75 if transverse == "spiral" else 0.65
    eps_ty = fy / Es

    cs = np.concatenate([
        np.geomspace(0.005 * h, 0.1 * h, 60, endpoint=False),
        np.linspace(0.1 * h, 1.2 * h, n, endpoint=False),
        np.geomspace(1.2 * h, 50 * h, 60),
    ])
    Mn, Pn, phis = [0.0], [Pnt], [0.90]
    for c in cs:
        P, M, et = section_forces(sec, c, fc, fy, Es)
        Pn.append(P)
        Mn.append(M)
        phis.append(phi_factor(et, eps_ty, transverse))
    Mn.append(0.0)
    Pn.append(Po)
    phis.append(phi_c)

    Mn = np.array(Mn)
    Pn = np.array(Pn)
    phis = np.array(phis)
    phiPn = np.minimum(phis * Pn, phi_c * Pn_max)
    phiMn = phis * Mn

    # balanced point (eps_t = eps_ty)
    d_t = max(bar.d for bar in sec.bars)
    cb = EPS_CU * d_t / (EPS_CU + eps_ty)
    Pb, Mb, _ = section_forces(sec, cb, fc, fy, Es)

    return Interaction(Mn, Pn, phiMn, phiPn, phis,
                       np.concatenate([[0.0], cs, [np.inf]]),
                       Po, Pn_max, phi_c * Pn_max, Pnt, (phi_c * Mb, phi_c * Pb))


def capacity_ratio(diag: Interaction, Pu: float, Mu: float) -> tuple[float, float, float]:
    """Demand/capacity ratio along the radial line from origin through (Mu, Pu).

    Returns (ratio, phiMn_at_ray, phiPn_at_ray).
    """
    Mu = abs(Mu)
    if Mu == 0 and Pu == 0:
        return 0.0, 0.0, 0.0
    M, P = diag.phiMn, diag.phiPn
    # ray: t*(Mu, Pu); segment: p0 + s*(p1-p0)
    best_t = None
    for i in range(len(M) - 1):
        x0, y0, x1, y1 = M[i], P[i], M[i + 1], P[i + 1]
        ex, ey = x1 - x0, y1 - y0
        det = Mu * (-ey) - Pu * (-ex)
        if abs(det) < 1e-12:
            continue
        t = (x0 * (-ey) - y0 * (-ex)) / det
        s = (Mu * y0 - Pu * x0) / det
        if -1e-9 <= s <= 1 + 1e-9 and t > 0:
            if best_t is None or t < best_t:
                best_t = t
    if best_t is None:
        return float("inf"), 0.0, 0.0
    return 1.0 / best_t, best_t * Mu, best_t * Pu


# --------------------------------------------------------------------------
# Effective length factor k (alignment chart equations, ACI R6.2.5)
# --------------------------------------------------------------------------
def _bisect(f, lo, hi, n=200):
    xs = np.linspace(lo, hi, n)
    vals = [f(x) for x in xs]
    for i in range(n - 1):
        if np.isfinite(vals[i]) and np.isfinite(vals[i + 1]) and vals[i] * vals[i + 1] <= 0:
            a, b = xs[i], xs[i + 1]
            fa = vals[i]
            for _ in range(80):
                m = 0.5 * (a + b)
                fm = f(m)
                if fa * fm <= 0:
                    b = m
                else:
                    a, fa = m, fm
            return 0.5 * (a + b)
    return None


def k_nonsway(psiA: float, psiB: float) -> float:
    if psiA + psiB < 1e-3:
        return 0.5
    GA, GB = max(psiA, 1e-6), max(psiB, 1e-6)

    def f(k):
        x = math.pi / k
        return (GA * GB / 4.0) * x ** 2 + (GA + GB) / 2.0 * (1.0 - x / math.tan(x)) \
            + 2.0 * math.tan(x / 2.0) / x - 1.0

    k = _bisect(f, 0.5001, 0.9999, 400)
    return 1.0 if k is None else k


def k_sway(psiA: float, psiB: float) -> float:
    if psiA + psiB < 1e-3:
        return 1.0
    GA, GB = max(psiA, 1e-6), max(psiB, 1e-6)

    def f(k):
        x = math.pi / k
        return (GA * GB * x ** 2 - 36.0) / (6.0 * (GA + GB)) - x / math.tan(x)

    k = _bisect(f, 1.0001, 20.0, 2000)
    return 20.0 if k is None else k


# --------------------------------------------------------------------------
# Slenderness & moment magnification
# --------------------------------------------------------------------------
def EI_eff(sec: Section, Ec, Es, beta_dns, method, Pu=0.0, Mu=0.0, Po=None) -> tuple[float, dict]:
    """6.6.4.4.4 (a), (b) or (c). Returns (EI_eff in N·mm², info dict)."""
    Ig = sec.Ig
    info = {}
    if method == "a":
        EI = 0.4 * Ec * Ig / (1.0 + beta_dns)
    elif method == "b":
        EI = (0.2 * Ec * Ig + Es * sec.Ise) / (1.0 + beta_dns)
    else:
        if Pu > 0 and Po:
            I = (0.80 + 25.0 * sec.Ast / sec.Ag) * (1.0 - abs(Mu) / (Pu * sec.h) - 0.5 * Pu / Po) * Ig
        else:
            I = 0.875 * Ig
        I = min(max(I, 0.35 * Ig), 0.875 * Ig)
        info["I"] = I
        EI = Ec * I / (1.0 + beta_dns)
    return EI, info


@dataclass
class SlenderResult:
    frame: str
    k: float
    lu: float
    r: float
    klu_r: float
    limit: float
    slender: bool
    over_100: bool
    EI: float = 0.0
    Pc: float = 0.0
    Cm: float = 1.0
    delta: float = 1.0
    delta_s: float = 1.0
    M1: float = 0.0
    M2: float = 0.0
    M2_min: float = 0.0
    use_min: bool = False
    Mc: float = 0.0
    unstable: bool = False
    notes: list[str] = field(default_factory=list)
    extra: dict = field(default_factory=dict)


def nonsway_magnification(sec, Pu, M1, M2, k, lu, Ec, Es, beta_dns, ei_method,
                          transverse_load=False, Po=None, check_limit=True) -> SlenderResult:
    """6.6.4.5. Moments are signed: M1/M2 negative for single curvature.

    Pu in N, M in N·mm, lu in mm.
    """
    r = sec.r
    klu_r = k * lu / r
    # 6.2.5.1 (b),(c)
    absM1, absM2 = sorted([abs(M1), abs(M2)])
    ratio = 0.0
    if absM2 > 0:
        # Sign from user: M1/M2 negative = single curvature
        ratio = math.copysign(absM1 / absM2, M1 * M2) if M1 * M2 != 0 else 0.0
    limit = min(34.0 + 12.0 * ratio, 40.0)
    res = SlenderResult("nonsway", k, lu, r, klu_r, limit, klu_r > limit, klu_r > 100)
    res.M1, res.M2 = absM1, absM2
    res.extra["M1_M2"] = ratio

    M2_min = Pu * (15.0 + 0.03 * sec.h)  # 6.6.4.5.4
    res.M2_min = M2_min

    if not res.slender and check_limit:
        res.Mc = absM2
        res.notes.append("เสาสั้น (kℓu/r ≤ ขีดจำกัด) — ไม่ต้องพิจารณาผลของความชะลูด (6.2.5.1)")
        return res

    EI, info = EI_eff(sec, Ec, Es, beta_dns, ei_method, Pu, absM2, Po)
    res.extra.update(info)
    Pc = math.pi ** 2 * EI / (k * lu) ** 2  # 6.6.4.4.2
    res.EI, res.Pc = EI, Pc

    if transverse_load:
        Cm = 1.0
        res.notes.append("มีแรงกระทำทางขวางระหว่างจุดรองรับ → Cm = 1.0 (6.6.4.5.3b)")
    else:
        Cm = 0.6 - 0.4 * ratio  # 6.6.4.5.3a

    M2_design = absM2
    if absM2 < M2_min:
        res.use_min = True
        M2_design = M2_min
        Cm = 1.0
        res.notes.append("M2 < M2,min → ใช้ M2,min และ Cm = 1.0 (6.6.4.5.4)")
    res.Cm = Cm

    if Pu >= 0.75 * Pc:
        res.unstable = True
        res.delta = float("inf")
        res.Mc = float("inf")
        res.notes.append("Pu ≥ 0.75Pc → เสาไม่มีเสถียรภาพ ต้องเพิ่มขนาดหน้าตัด")
        return res

    delta = max(1.0, Cm / (1.0 - Pu / (0.75 * Pc)))  # 6.6.4.5.2
    res.delta = delta
    res.Mc = delta * M2_design
    if delta > 1.4:
        res.notes.append("δ > 1.4 — ควรพิจารณาเพิ่มขนาดเสา (R6.2.6 แนะนำให้อัตราส่วนโมเมนต์อันดับสองต่ออันดับหนึ่ง ≤ 1.4)")
    return res


def sway_magnification(sec, Pu, Mns_top, Mns_bot, Ms_top, Ms_bot, k_sway_val, lu, Ec, Es,
                       beta_dns, ei_method, delta_s_method, Q=None,
                       sumPu=None, sumPc=None, Po=None) -> SlenderResult:
    """6.6.4.6 — sway frame. Loads in N, moments in N·mm.

    End moments use one sign convention: same sign at top and bottom = single curvature.
    """
    r = sec.r
    klu_r = k_sway_val * lu / r
    res = SlenderResult("sway", k_sway_val, lu, r, klu_r, 22.0, klu_r > 22.0, klu_r > 100)
    res.M2_min = Pu * (15.0 + 0.03 * sec.h)

    def ordered(m_top, m_bot):
        small, big = sorted([m_top, m_bot], key=abs)
        sign = -1.0 if m_top * m_bot > 0 else 1.0  # ACI: single curvature -> M1/M2 < 0
        return sign * abs(small), abs(big)

    if not res.slender:
        res.M1, res.M2 = ordered(Mns_top + Ms_top, Mns_bot + Ms_bot)
        res.M1 = abs(res.M1)
        res.Mc = res.M2
        res.notes.append("kℓu/r ≤ 22 — ไม่ต้องพิจารณาผลของความชะลูด (6.2.5.1a)")
        return res

    if delta_s_method == "Q":
        if Q >= 1.0:
            res.unstable = True
            res.delta_s = float("inf")
            res.Mc = float("inf")
            res.notes.append("Q ≥ 1 → โครงสร้างไม่มีเสถียรภาพ")
            return res
        delta_s = max(1.0, 1.0 / (1.0 - Q))  # 6.6.4.6.2(a)
        if delta_s > 1.5:
            res.notes.append("δs จากวิธี Q > 1.5 → ต้องใช้วิธี ΣPc (6.6.4.6.2b) หรือการวิเคราะห์อันดับสอง")
    else:
        if sumPu >= 0.75 * sumPc:
            res.unstable = True
            res.delta_s = float("inf")
            res.Mc = float("inf")
            res.notes.append("ΣPu ≥ 0.75ΣPc → โครงสร้างไม่มีเสถียรภาพ")
            return res
        delta_s = max(1.0, 1.0 / (1.0 - sumPu / (0.75 * sumPc)))  # 6.6.4.6.2(b)
    res.delta_s = delta_s

    M_top = Mns_top + delta_s * Ms_top  # 6.6.4.6.1
    M_bot = Mns_bot + delta_s * Ms_bot
    res.extra["M_top"], res.extra["M_bot"] = M_top, M_bot
    M1, M2 = ordered(M_top, M_bot)

    # second-order effects along the length per 6.6.4.5 with k = 1.0 (conservative)
    ns = nonsway_magnification(sec, Pu, M1, M2, 1.0, lu, Ec, Es, beta_dns, ei_method,
                               Po=Po, check_limit=False)
    res.EI, res.Pc, res.Cm, res.delta = ns.EI, ns.Pc, ns.Cm, ns.delta
    res.M1, res.M2 = ns.M1, ns.M2
    res.use_min = ns.use_min
    res.unstable = ns.unstable
    res.extra["M1_M2"] = ns.extra.get("M1_M2", 0.0)
    res.extra.update({k: v for k, v in ns.extra.items() if k == "I"})
    # design moment = larger of magnified end moment and along-length moment
    res.extra["Mc_length"] = ns.Mc
    res.Mc = max(M2, ns.Mc)
    res.notes.append("ตรวจผล P-δ ตามความยาวเสาตาม 6.6.4.5 โดยใช้ M1, M2 จาก 6.6.4.6.1 และ k = 1.0 (อนุรักษ์)")
    res.notes.extend(ns.notes)
    return res


# --------------------------------------------------------------------------
# Detailing checks
# --------------------------------------------------------------------------
def detailing_checks(sec: Section, transverse: str, agg: float = 25.0) -> list[tuple[str, bool, str]]:
    out = []
    rho = sec.Ast / sec.Ag
    out.append(("อัตราส่วนเหล็กเสริม 0.01 ≤ ρg ≤ 0.08 (10.6.1.1)",
                0.01 <= rho <= 0.08, f"ρg = {rho * 100:.2f}%"))
    nmin = 6 if transverse == "spiral" else 4
    out.append((f"จำนวนเหล็กยืนขั้นต่ำ {nmin} เส้น (10.7.3.1)",
                sec.n_bars >= nmin, f"ใช้ {sec.n_bars} เส้น"))
    s_clear_min = max(40.0, 1.5 * sec.db, 4.0 / 3.0 * agg)
    # minimum clear spacing between adjacent bars
    pts = [(b.x, b.d) for b in sec.bars]
    smin = float("inf")
    for i in range(len(pts)):
        for j in range(i + 1, len(pts)):
            dist = math.hypot(pts[i][0] - pts[j][0], pts[i][1] - pts[j][1])
            smin = min(smin, dist)
    s_clear = smin - sec.db if np.isfinite(smin) else float("inf")
    out.append((f"ระยะช่องว่างระหว่างเหล็ก ≥ {s_clear_min:.0f} mm (25.2.3)",
                s_clear >= s_clear_min, f"ช่องว่างน้อยสุด = {s_clear:.0f} mm"))
    if transverse == "tied":
        tie_min = 12.0 if sec.db > 32 else 10.0  # No.3 / No.4 (metric equivalent)
        out.append((f"ขนาดเหล็กปลอก ≥ {tie_min:.0f} mm (25.7.2.2)",
                    sec.dt >= tie_min - 0.1, f"ใช้ {sec.dt:.0f} mm"))
    return out


def tie_spacing(sec: Section) -> float:
    """25.7.2.1 maximum tie spacing (mm)."""
    least = min(sec.b, sec.h)
    return min(16.0 * sec.db, 48.0 * sec.dt, least)
