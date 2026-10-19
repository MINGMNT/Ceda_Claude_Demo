"""
Streamlit app: Slender RC column design per ACI 318-19
Run:  streamlit run app.py
"""

import math

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import aci318_column as aci

# Units: the UI works in ksc (kgf/cm²), cm, m, tonne-force (t) and t·m;
# aci318_column works in N, mm and MPa. Convert at the boundary.
KSC = 0.0980665      # MPa per ksc
TON = 9806.65        # N per t
TM = TON * 1000.0    # N·mm per t·m

st.set_page_config(page_title="ออกแบบเสายาว ACI 318-19", page_icon="🏛️", layout="wide")

# Colour palette (navy & gold) shared by CSS, cards and charts
C_NAVY, C_BLUE, C_GREEN = "#1E3A8A", "#2563EB", "#15803D"
C_GOLD, C_BRONZE, C_RED = "#F59E0B", "#B45309", "#DC2626"

st.markdown(
    """
    <style>
    /* ---------- page ---------- */
    .block-container {padding-top: 3.2rem;}
    .hero {
        display:flex; align-items:center; gap:22px; padding:26px 30px; border-radius:20px; color:#fff;
        background: linear-gradient(120deg, #0B1F4D 0%, #1E3A8A 60%, #2B4FA8 100%);
        border-bottom: 5px solid #F59E0B;
        box-shadow: 0 10px 30px rgba(11,31,77,.30); margin-bottom: 18px;
    }
    .hero-icon {font-size:3.2rem; background:rgba(245,158,11,.22); border:1px solid rgba(245,158,11,.6); border-radius:18px; padding:8px 16px;}
    .hero h1 {color:#fff; font-size:2rem; margin:0; padding:0; line-height:1.25;}
    .hero p  {color:rgba(255,255,255,.92); margin:6px 0 10px 0;}
    .chip {display:inline-block; background:rgba(245,158,11,.16); border:1px solid rgba(245,158,11,.65); color:#FDE68A;
           padding:3px 12px; border-radius:999px; font-size:.82rem; margin-right:6px;}

    /* ---------- sidebar ---------- */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #E8EDF8 0%, #F1F4FA 55%, #FBF5E6 100%);
    }
    section[data-testid="stSidebar"] [data-testid="stExpander"] details {
        background:#ffffffcc; border:none; border-left:5px solid #F59E0B; border-radius:12px;
        box-shadow:0 2px 8px rgba(11,31,77,.07);
    }
    section[data-testid="stSidebar"] [data-testid="stExpander"] summary p {font-weight:700; color:#1E3A8A;}
    .side-title {font-size:1.25rem; font-weight:800; margin:4px 0 10px 0;
                 background:linear-gradient(90deg,#1E3A8A,#B45309); -webkit-background-clip:text; color:transparent;}

    /* ---------- tabs as pills ---------- */
    div[role="tablist"] {gap:8px; border-bottom:none !important; box-shadow:none !important; padding-bottom:6px;}
    [data-testid="stTab"] {background:#fff; border-radius:999px !important; padding:8px 18px !important;
        border:1px solid #D9DFEC !important; box-shadow:0 1px 3px rgba(0,0,0,.05);}
    [data-testid="stTab"]::after, [data-testid="stTab"]::before {display:none !important;}
    [data-testid="stTab"][aria-selected="true"] {background:linear-gradient(90deg,#0B1F4D,#1E3A8A);
        border-color:#F59E0B !important;}
    [data-testid="stTab"][aria-selected="true"] p {color:#FCD34D !important; font-weight:700;}

    /* ---------- status banners ---------- */
    .ok, .ng {padding:18px 22px; border-radius:16px; font-size:1.3rem; font-weight:700; color:#fff;}
    .ok {background:linear-gradient(90deg,#14532D,#15803D); border-left:6px solid #F59E0B; box-shadow:0 8px 20px rgba(21,128,61,.22);}
    .ng {background:linear-gradient(90deg,#7F1D1D,#DC2626); border-left:6px solid #F59E0B; box-shadow:0 8px 20px rgba(220,38,38,.22);}
    .warn {background:#FEF3C7; border-left:5px solid #F59E0B; color:#78350F; padding:10px 14px; border-radius:10px; margin-bottom:8px;}

    /* ---------- metric cards ---------- */
    .card {background:#fff; border-radius:16px; padding:16px 18px; border-top:5px solid var(--c);
           box-shadow:0 4px 14px rgba(11,31,77,.08); height:100%;}
    .card-top {font-size:.85rem; color:#64708A; display:flex; align-items:center; gap:8px;}
    .card-icon {display:inline-flex; width:30px; height:30px; border-radius:10px; align-items:center; justify-content:center;
                background:color-mix(in srgb, var(--c) 16%, white); font-size:1rem;}
    .card-val {font-size:1.75rem; font-weight:800; color:var(--c); margin-top:6px;}
    .card-sub {font-size:.8rem; color:#8791A8;}

    /* ---------- panels / chips ---------- */
    .panel-title {font-weight:800; font-size:1.1rem; margin:6px 0 10px 0; color:#0F1E3D;}
    .panel-title span {display:inline-block; width:10px; height:22px; border-radius:4px; margin-right:8px;
                       vertical-align:-4px; background:var(--c);}
    .check {padding:8px 12px; border-radius:10px; margin-bottom:6px;}
    .check.pass {background:#E8F5EC; border-left:4px solid #15803D;}
    .check.fail {background:#FDECEC; border-left:4px solid #DC2626;}
    .check b {color:#0F1E3D; font-weight:600;}
    .check i {display:block; font-style:normal; font-size:.85rem; color:#4B5670; margin-left:26px;}
    .step {display:inline-flex; align-items:center; justify-content:center; width:34px; height:34px; border-radius:50%;
           color:#fff; font-weight:800; margin-right:10px; background:var(--c);}
    .step-h {font-size:1.2rem; font-weight:800; margin:4px 0 6px 0; color:#0F1E3D;}
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="hero">
      <div class="hero-icon">🏛️</div>
      <div>
        <h1>ออกแบบเสายาว (Slender Column)</h1>
        <p>วิธีขยายโมเมนต์ (Moment Magnification Method) สำหรับเสาคอนกรีตเสริมเหล็ก</p>
        <span class="chip">📘 ACI 318-19</span><span class="chip">📏 ksc · cm · m · ตัน · ตัน-ม.</span>
        <span class="chip">↕️ ดัดแกนเดียว</span>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)


def card(col, icon, title, value, sub, color):
    col.markdown(
        f'<div class="card" style="--c:{color}"><div class="card-top"><span class="card-icon">{icon}</span>{title}</div>'
        f'<div class="card-val">{value}</div><div class="card-sub">{sub}</div></div>',
        unsafe_allow_html=True,
    )


def panel_title(text, color):
    st.markdown(f'<div class="panel-title" style="--c:{color}"><span></span>{text}</div>', unsafe_allow_html=True)


def step_header(n, text, color):
    st.markdown(f'<div class="step-h"><span class="step" style="--c:{color}">{n}</span>{text}</div>',
                unsafe_allow_html=True)


# =============================================================================
# Sidebar inputs
# =============================================================================
sb = st.sidebar
sb.markdown('<div class="side-title">⚙️ ข้อมูลออกแบบ</div>', unsafe_allow_html=True)

with sb.expander("🧱 1) วัสดุ", expanded=True):
    fc_ksc = st.number_input("f'c (ksc)", 150.0, 1000.0, 280.0, 10.0, help="กำลังอัดคอนกรีตทรงกระบอก (กก./ตร.ซม.)")
    fy_ksc = st.number_input("fy (ksc)", 2400.0, 7000.0, 4000.0, 100.0,
                             help="กำลังครากเหล็กยืน (SD30 = 3000, SD40 = 4000, SD50 = 5000)")
    Es_ksc = st.number_input("Es (ksc)", 1.5e6, 2.2e6, 2.04e6, 1e4, format="%.0f")
    fc, fy, Es = fc_ksc * KSC, fy_ksc * KSC, Es_ksc * KSC
    Ec_auto = st.checkbox("Ec = 4700√f'c [MPa] ≈ 15,000√f'c [ksc] (19.2.2.1)", value=True)
    Ec = aci.Ec_normal(fc) if Ec_auto else \
        st.number_input("Ec (ksc)", 1e5, 6e5, aci.Ec_normal(fc) / KSC, 5000.0, format="%.0f") * KSC
    agg = st.number_input("ขนาดมวลรวมใหญ่สุด (cm)", 1.0, 4.0, 2.0, 0.5) * 10.0

with sb.expander("📐 2) หน้าตัดและเหล็กเสริม", expanded=True):
    shape_lbl = st.radio("รูปทรงหน้าตัด", ["สี่เหลี่ยม", "วงกลม"], horizontal=True)
    shape = "rect" if shape_lbl == "สี่เหลี่ยม" else "circ"
    trans_lbl = st.radio("เหล็กเสริมทางขวาง", ["ปลอกเดี่ยว (Tied)", "ปลอกเกลียว (Spiral)"], horizontal=True)
    transverse = "tied" if trans_lbl.startswith("ปลอกเดี่ยว") else "spiral"

    if shape == "rect":
        c1, c2 = st.columns(2)
        b = c1.number_input("b (cm)", 15.0, 300.0, 50.0, 2.5, help="ด้านตั้งฉากกับทิศทางการดัด") * 10.0
        h = c2.number_input("h (cm)", 15.0, 300.0, 50.0, 2.5, help="ด้านในทิศทางการดัด (ความลึก)") * 10.0
    else:
        D = st.number_input("เส้นผ่านศูนย์กลาง D (cm)", 20.0, 300.0, 50.0, 2.5) * 10.0

    cover = st.number_input("ระยะหุ้มถึงผิวเหล็กปลอก (cm)", 2.0, 10.0, 4.0, 0.5) * 10.0
    c1, c2 = st.columns(2)
    bar_lbl = c1.selectbox("เหล็กยืน", list(aci.BAR_SIZES), index=4)
    tie_lbl = c2.selectbox("เหล็กปลอก", list(aci.TIE_SIZES), index=2)
    db, dt = aci.BAR_SIZES[bar_lbl], aci.TIE_SIZES[tie_lbl]

    if shape == "rect":
        c1, c2 = st.columns(2)
        n_b = c1.number_input("จำนวนเหล็กด้าน b (ต่อด้าน)", 2, 20, 4, 1, help="รวมเหล็กมุม — อยู่ที่ผิวรับแรงอัด/แรงดึง")
        n_h = c2.number_input("จำนวนเหล็กด้าน h (ต่อด้าน)", 2, 20, 4, 1, help="รวมเหล็กมุม")
        sec = aci.make_rect_section(b, h, cover, db, dt, int(n_b), int(n_h))
    else:
        n_c = st.number_input("จำนวนเหล็กยืนรอบวง", 4, 40, 8, 1)
        sec = aci.make_circ_section(D, cover, db, dt, int(n_c))
    st.info(f"เหล็กยืน {sec.n_bars}-{bar_lbl}  •  Ast = {sec.Ast / 100:,.2f} ซม.²  •  ρg = {sec.Ast / sec.Ag * 100:.2f}%")

with sb.expander("🏗️ 3) ระบบโครงสร้างและความยาว", expanded=True):
    frame_lbl = st.radio("ประเภทโครงข้อแข็ง", ["ไม่เซ (Nonsway)", "เซ (Sway)"], horizontal=True,
                         help="ACI 6.6.4.3: ถือว่าไม่เซได้ถ้า Q ≤ 0.05")
    frame = "nonsway" if frame_lbl.startswith("ไม่เซ") else "sway"
    lu_m = st.number_input("ความยาวไม่ค้ำยัน ℓu (m)", 0.5, 30.0, 5.0, 0.1)
    k_mode = st.radio("ค่า k", ["กำหนดเอง", "คำนวณจาก ψA, ψB"], horizontal=True)
    if k_mode == "กำหนดเอง":
        k_default = 1.0 if frame == "nonsway" else 1.5
        k = st.number_input("k", 0.5, 10.0, k_default, 0.05)
        psiA = psiB = None
    else:
        c1, c2 = st.columns(2)
        psiA = c1.number_input("ψA (ปลายบน)", 0.0, 100.0, 1.0, 0.1, help="ψ = Σ(EI/ℓc)เสา / Σ(EI/ℓ)คาน")
        psiB = c2.number_input("ψB (ปลายล่าง)", 0.0, 100.0, 1.0, 0.1)
        k = aci.k_nonsway(psiA, psiB) if frame == "nonsway" else aci.k_sway(psiA, psiB)
        st.success(f"k = {k:.3f}  (Alignment chart, R6.2.5)")

with sb.expander("🎯 4) แรงกระทำ (Factored)", expanded=True):
    Pu_t = st.number_input("Pu (ตัน) — แรงอัด", 0.0, 10000.0, 200.0, 5.0)
    if frame == "nonsway":
        M2_in = st.number_input("|M2| โมเมนต์ปลายที่มากกว่า (ตัน-ม.)", 0.0, 5000.0, 15.0, 0.5)
        M1_in = st.number_input("|M1| โมเมนต์ปลายที่น้อยกว่า (ตัน-ม.)", 0.0, 5000.0, 10.0, 0.5)
        curv = st.radio("รูปแบบการดัด", ["ดัดโค้งทางเดียว (Single)", "ดัดโค้งสองทาง (Double)"],
                        help="Single curvature → M1/M2 เป็นลบ")
        transverse_load = st.checkbox("มีแรงกระทำทางขวางระหว่างจุดรองรับ (Cm = 1.0)")
        if M1_in > M2_in:
            st.warning("|M1| ต้องไม่เกิน |M2| — ระบบสลับค่าให้อัตโนมัติ")
            M1_in, M2_in = M2_in, M1_in
    else:
        st.caption("หน่วย ตัน-ม. • ค่าเครื่องหมายเดียวกันที่ปลายบน/ล่าง = ดัดโค้งทางเดียว")
        c1, c2 = st.columns(2)
        Mns_top = c1.number_input("Mns ปลายบน", -5000.0, 5000.0, 4.0, 0.5, help="จากแรงที่ไม่ทำให้เซ (เช่น D, L)")
        Mns_bot = c2.number_input("Mns ปลายล่าง", -5000.0, 5000.0, 2.0, 0.5)
        Ms_top = c1.number_input("Ms ปลายบน", -5000.0, 5000.0, 8.0, 0.5, help="จากแรงที่ทำให้เซ (เช่น W, E)")
        Ms_bot = c2.number_input("Ms ปลายล่าง", -5000.0, 5000.0, -7.0, 0.5)
        ds_method = st.radio("วิธีคำนวณ δs", ["ดัชนีเสถียรภาพ Q", "ΣPu / ΣPc"], horizontal=True)
        if ds_method.startswith("ดัชนี"):
            Q = st.number_input("Q (6.6.4.4.1)", 0.0, 0.99, 0.10, 0.01)
            sumPu = sumPc = None
        else:
            Q = None
            sumPu = st.number_input("ΣPu ทั้งชั้น (ตัน)", 0.0, 1e6, 2000.0, 50.0)
            sumPc = st.number_input("ΣPc ทั้งชั้น (ตัน)", 1.0, 1e7, 15000.0, 100.0,
                                    help="ผลรวม Pc ของเสาที่ต้านการเซในชั้น (ใช้ k แบบเซ และ βds)")

with sb.expander("🔧 5) ความแข็งแรงประสิทธิผล (EI)eff", expanded=False):
    beta_dns = st.number_input("βdns", 0.0, 1.0, 0.6, 0.05,
                               help="อัตราส่วนแรงอัดคงค้างประลัยสูงสุด / แรงอัดประลัยสูงสุด (โครงเซใช้ βds สำหรับ ΣPc)")
    ei_lbl = st.radio("สูตร (EI)eff — 6.6.4.4.4",
                      ["(a) 0.4EcIg/(1+βdns)", "(b) (0.2EcIg+EsIse)/(1+βdns)", "(c) EcI/(1+βdns)"], index=1)
    ei_method = ei_lbl[1]

# =============================================================================
# Calculations
# =============================================================================
Pu = Pu_t * TON
lu = lu_m * 1e3
diag = aci.interaction_diagram(sec, fc, fy, Es, transverse)

if frame == "nonsway":
    sign = -1.0 if curv.startswith("ดัดโค้งทางเดียว") else 1.0
    res = aci.nonsway_magnification(sec, Pu, sign * M1_in * TM, M2_in * TM, k, lu, Ec, Es,
                                    beta_dns, ei_method, transverse_load, Po=diag.Po)
    M_first = M2_in * TM
else:
    res = aci.sway_magnification(sec, Pu, Mns_top * TM, Mns_bot * TM, Ms_top * TM, Ms_bot * TM,
                                 k, lu, Ec, Es, beta_dns, ei_method,
                                 "Q" if Q is not None else "sum", Q=Q,
                                 sumPu=None if sumPu is None else sumPu * TON,
                                 sumPc=None if sumPc is None else sumPc * TON, Po=diag.Po)
    M_first = max(abs(Mns_top + Ms_top), abs(Mns_bot + Ms_bot)) * TM

Mc = res.Mc
if math.isfinite(Mc):
    ratio, phiMn_ray, phiPn_ray = aci.capacity_ratio(diag, Pu, Mc)
else:
    ratio, phiMn_ray, phiPn_ray = float("inf"), 0.0, 0.0
detail = aci.detailing_checks(sec, transverse, agg)
detail_ok = all(ok for _, ok, _ in detail)
strength_ok = ratio <= 1.0 and not res.unstable and Pu <= diag.phiPn_max
overall_ok = strength_ok and detail_ok and not res.over_100

# =============================================================================
# Output
# =============================================================================
tab_sum, tab_pm, tab_calc, tab_sec = st.tabs(
    ["📋 สรุปผล", "📈 Interaction Diagram", "🧮 รายการคำนวณ", "🔲 หน้าตัดเสา"])


def tm(x):
    """N·mm -> t·m"""
    return f"{x / TM:,.2f}" if math.isfinite(x) else "∞"


def sci(x):
    """LaTeX scientific notation, e.g. 2.13 \\times 10^{9}."""
    if x == 0:
        return "0"
    e = int(math.floor(math.log10(abs(x))))
    return rf"{x / 10 ** e:.3f}\times10^{{{e}}}"


def lx(x, prec=".0f"):
    """Thousands-separated number for LaTeX (a bare comma adds a space there)."""
    return f"{x:,{prec}}".replace(",", "{,}")


def ton(x):
    """N -> t"""
    return f"{x / TON:,.1f}" if math.isfinite(x) else "∞"


# ---------------------------------------------------------------- Summary tab
with tab_sum:
    if overall_ok:
        st.markdown(f'<div class="ok">✅ ผ่าน — หน้าตัดรับแรงได้ (D/C = {ratio:.3f})</div>', unsafe_allow_html=True)
    else:
        why = []
        if res.unstable:
            why.append("เสาไม่มีเสถียรภาพ")
        if not math.isfinite(ratio) or ratio > 1.0:
            why.append(f"กำลังไม่พอ (D/C = {ratio:.3f})" if math.isfinite(ratio) else "กำลังไม่พอ")
        if Pu > diag.phiPn_max:
            why.append("Pu > φPn,max")
        if not detail_ok:
            why.append("รายละเอียดเหล็กเสริมไม่ผ่าน")
        if res.over_100:
            why.append("kℓu/r > 100 ต้องใช้การวิเคราะห์อันดับสองแบบไม่เชิงเส้น (6.2.6)")
        st.markdown(f'<div class="ng">❌ ไม่ผ่าน — {" • ".join(why)}</div>', unsafe_allow_html=True)

    st.write("")
    dc_color = C_GREEN if ratio <= 0.9 else (C_GOLD if ratio <= 1.0 else C_RED)
    c = st.columns(5)
    card(c[0], "📏", "ความชะลูด kℓu/r", f"{res.klu_r:.1f}", f"ขีดจำกัด {res.limit:.1f}", C_NAVY)
    card(c[1], "🏛️", "ประเภทเสา", "เสายาว" if res.slender else "เสาสั้น",
         "ต้องขยายโมเมนต์" if res.slender else "ไม่ต้องขยายโมเมนต์", C_BLUE if res.slender else C_GREEN)
    if frame == "sway":
        card(c[2], "🔁", "δs / δ", f"{res.delta_s:.2f} / {res.delta:.2f}", "ตัวขยายโมเมนต์", C_BRONZE)
    else:
        card(c[2], "🔁", "δns", f"{res.delta:.3f}" if math.isfinite(res.delta) else "∞", "ตัวขยายโมเมนต์", C_BRONZE)
    card(c[3], "🌀", "Mc ออกแบบ", tm(Mc), f"ตัน-ม. (จาก {tm(M_first)})", C_BLUE)
    card(c[4], "🎯", "D/C ratio", f"{ratio:.3f}" if math.isfinite(ratio) else "∞",
         "ผ่าน" if ratio <= 1 else "เกินกำลัง", dc_color)

    st.write("")
    g1, g2, g3 = st.columns([1.1, 1.3, 1.4])
    with g1:
        panel_title("การใช้กำลัง", dc_color)
        gauge = go.Figure(go.Indicator(
            mode="gauge+number", value=min(ratio, 2.0) * 100 if math.isfinite(ratio) else 200,
            number=dict(suffix="%", font=dict(size=40, color=dc_color)),
            gauge=dict(
                axis=dict(range=[0, 150], tickwidth=1, ticksuffix="%"),
                bar=dict(color="#0F1E3D", thickness=0.25),
                steps=[dict(range=[0, 70], color="#DCE5F5"), dict(range=[70, 90], color="#B9CAEB"),
                       dict(range=[90, 100], color="#FDE68A"), dict(range=[100, 150], color="#FCA5A5")],
                threshold=dict(line=dict(color=C_RED, width=4), thickness=0.85, value=100),
            ),
        ))
        gauge.update_layout(height=250, margin=dict(l=25, r=25, t=10, b=0), paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(gauge, width="stretch")
    with g2:
        panel_title("กำลังของหน้าตัด", C_NAVY)
        st.dataframe(pd.DataFrame({
            "รายการ": ["Po", "Pn,max", "φPn,max", "φMn ที่แนวรัศมี", "φPn ที่แนวรัศมี", "φMn,b / φPn,b (สมดุล)"],
            "ค่า": [f"{ton(diag.Po)} ตัน", f"{ton(diag.Pn_max)} ตัน", f"{ton(diag.phiPn_max)} ตัน",
                    f"{tm(phiMn_ray)} ตัน-ม.", f"{ton(phiPn_ray)} ตัน",
                    f"{tm(diag.balanced[0])} ตัน-ม. / {ton(diag.balanced[1])} ตัน"],
        }), hide_index=True, width="stretch")
    with g3:
        panel_title("ตรวจสอบรายละเอียดเหล็กเสริม", C_GREEN)
        html = "".join(
            f'<div class="check {"pass" if ok else "fail"}"><b>{"✅" if ok else "❌"} {name}</b><i>{val}</i></div>'
            for name, ok, val in detail)
        st.markdown(html, unsafe_allow_html=True)
        if transverse == "tied":
            st.markdown(f"ℹ️ ระยะเรียงปลอกสูงสุด (25.7.2.1) = **{aci.tie_spacing(sec) / 10:.1f} ซม.**")
        elif sec.shape == "circ":
            rho_s = 0.45 * (sec.Ag / (math.pi * (sec.h - 2 * sec.cover) ** 2 / 4) - 1) * fc / fy
            st.markdown(f"ℹ️ ρs ขั้นต่ำของปลอกเกลียว (25.7.3.3) = **{rho_s:.4f}**")

    if res.notes:
        panel_title("หมายเหตุ", C_GOLD)
        for n in res.notes:
            st.markdown(f'<div class="warn">⚠️ {n}</div>', unsafe_allow_html=True)

# --------------------------------------------------------- Interaction diagram
with tab_pm:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=diag.Mn / TM, y=diag.Pn / TON, name="กำลังระบุ (Mn, Pn)",
                             line=dict(color=C_GOLD, dash="dash", width=2)))
    fig.add_trace(go.Scatter(x=diag.phiMn / TM, y=diag.phiPn / TON, name="กำลังออกแบบ (φMn, φPn)",
                             line=dict(color=C_NAVY, width=3.5), fill="tozerox",
                             fillcolor="rgba(30,58,138,0.10)"))
    fig.add_trace(go.Scatter(x=[M_first / TM], y=[Pu / TON], mode="markers", name="แรงอันดับหนึ่ง (Pu, M2)",
                             marker=dict(size=14, color=C_GOLD, symbol="circle", line=dict(color="#fff", width=2))))
    if math.isfinite(Mc):
        fig.add_trace(go.Scatter(x=[Mc / TM], y=[Pu / TON], mode="markers",
                                 name="แรงหลังขยายโมเมนต์ (Pu, Mc)",
                                 marker=dict(size=20, color=C_RED if ratio > 1 else C_GREEN,
                                             symbol="star", line=dict(color="#fff", width=1.5))))
        fig.add_trace(go.Scatter(x=[0, phiMn_ray / TM], y=[0, phiPn_ray / TON], mode="lines",
                                 name="แนวรัศมี", line=dict(color="#8791A8", width=1.5, dash="dot")))
        if M_first > 0:
            fig.add_annotation(x=Mc / TM, y=Pu / TON, ax=M_first / TM, ay=Pu / TON,
                               xref="x", yref="y", axref="x", ayref="y",
                               showarrow=True, arrowhead=3, arrowwidth=2, arrowcolor=C_BRONZE)
    fig.add_trace(go.Scatter(x=[diag.balanced[0] / TM], y=[diag.balanced[1] / TON], mode="markers",
                             name="จุดสมดุล", marker=dict(size=11, color=C_BRONZE, symbol="diamond")))
    fig.update_layout(
        height=620, xaxis_title="M (ตัน-ม.)", yaxis_title="P (ตัน)",
        legend=dict(orientation="h", y=-0.2), margin=dict(l=20, r=20, t=30, b=40),
        hovermode="closest", template="plotly_white",
        paper_bgcolor="#fff", plot_bgcolor="#FAFBFE", font=dict(color="#0F1E3D"),
    )
    fig.update_xaxes(zeroline=True, zerolinecolor="#AEB8CF", gridcolor="#E6EAF2", rangemode="tozero")
    fig.update_yaxes(zeroline=True, zerolinecolor="#AEB8CF", gridcolor="#E6EAF2")
    st.plotly_chart(fig, width="stretch")

    with st.expander("ตารางจุดบน Interaction Diagram"):
        sel = np.linspace(0, len(diag.Mn) - 1, 40).astype(int)
        df = pd.DataFrame({
            "c (cm)": [f"{x / 10:.1f}" if np.isfinite(x) else "∞" for x in diag.c[sel]],
            "Pn (ตัน)": diag.Pn[sel] / TON, "Mn (ตัน-ม.)": diag.Mn[sel] / TM, "φ": diag.phi[sel],
            "φPn (ตัน)": diag.phiPn[sel] / TON, "φMn (ตัน-ม.)": diag.phiMn[sel] / TM,
        })
        st.dataframe(df.style.format(precision=2), width="stretch", hide_index=True)
        st.download_button("⬇️ ดาวน์โหลด CSV", pd.DataFrame({
            "c_cm": diag.c / 10, "Pn_t": diag.Pn / TON, "Mn_tm": diag.Mn / TM, "phi": diag.phi,
            "phiPn_t": diag.phiPn / TON, "phiMn_tm": diag.phiMn / TM,
        }).to_csv(index=False).encode("utf-8"), "interaction_diagram.csv", "text/csv")

# ---------------------------------------------------------- Calculation tab
with tab_calc:
    EI_TM2 = TON * 1e6  # N·mm² per t·m²
    h_cm = sec.h / 10
    step_header(1, "คุณสมบัติหน้าตัด", C_NAVY)
    dim = f"b \\times h = {sec.b / 10:.1f} \\times {h_cm:.1f}" if sec.shape == "rect" else f"D = {h_cm:.1f}"
    st.latex(rf"{dim}\ \text{{cm}},\quad A_g = {sec.Ag / 100:.1f}\ \text{{cm}}^2,\quad "
             rf"I_g = {sci(sec.Ig / 1e4)}\ \text{{cm}}^4")
    st.latex(rf"A_{{st}} = {sec.Ast / 100:.2f}\ \text{{cm}}^2,\quad \rho_g = {sec.Ast / sec.Ag:.4f},\quad "
             rf"I_{{se}} = {sci(sec.Ise / 1e4)}\ \text{{cm}}^4")
    st.latex(rf"f'_c = {fc_ksc:.0f},\ f_y = {fy_ksc:.0f},\ E_c = {lx(Ec / KSC, '.0f')}\ \text{{ksc}},\quad "
             rf"\beta_1 = {aci.beta1(fc):.3f}")
    st.latex(rf"r = {'0.25D' if sec.shape == 'circ' else '0.30h'} = {sec.r / 10:.2f}\ \text{{cm}}\ (6.2.5.2)")

    step_header(2, "ตรวจสอบความชะลูด (6.2.5.1)", C_GOLD)
    if psiA is not None:
        st.latex(rf"\psi_A = {psiA:.2f},\ \psi_B = {psiB:.2f}\ \Rightarrow\ k = {k:.3f}")
    st.latex(rf"\frac{{k\ell_u}}{{r}} = \frac{{{res.k:.3f}\times{lu / 10:.0f}}}{{{res.r / 10:.2f}}} = {res.klu_r:.2f}")
    if frame == "nonsway":
        m12 = res.extra.get("M1_M2", 0.0)
        st.latex(rf"\text{{ขีดจำกัด}} = \min\left(34 + 12\frac{{M_1}}{{M_2}},\ 40\right) = "
                 rf"\min(34 + 12({m12:.3f}),\ 40) = {res.limit:.2f}")
    else:
        st.latex(r"\text{ขีดจำกัด (โครงเซ)} = 22")
    st.markdown(f"→ {'**เสายาว** ต้องพิจารณาผลของความชะลูด' if res.slender else '**เสาสั้น** ไม่ต้องขยายโมเมนต์'}")
    if res.over_100:
        st.error("kℓu/r > 100 → ต้องใช้การวิเคราะห์อันดับสองแบบไม่เชิงเส้น (6.2.6) วิธีขยายโมเมนต์ใช้ไม่ได้")

    if res.slender:
        step_header(3, "ความแข็งแรงประสิทธิผลและแรงวิกฤต (6.6.4.4)", C_BLUE)
        EI_t = res.EI / EI_TM2
        if ei_method == "a":
            st.latex(rf"(EI)_{{eff}} = \frac{{0.4E_cI_g}}{{1+\beta_{{dns}}}} = {lx(EI_t, '.0f')}\ \text{{t·m}}^2")
        elif ei_method == "b":
            st.latex(rf"(EI)_{{eff}} = \frac{{0.2E_cI_g + E_sI_{{se}}}}{{1+\beta_{{dns}}}} = "
                     rf"{lx(EI_t, '.0f')}\ \text{{t·m}}^2")
        else:
            I = res.extra.get("I", 0.0)
            st.latex(rf"I = \left(0.80 + 25\frac{{A_{{st}}}}{{A_g}}\right)\left(1 - \frac{{M_u}}{{P_uh}} - "
                     rf"0.5\frac{{P_u}}{{P_o}}\right)I_g = {sci(I / 1e4)}\ \text{{cm}}^4\ "
                     rf"(0.35I_g \le I \le 0.875I_g)")
            st.latex(rf"(EI)_{{eff}} = \frac{{E_cI}}{{1+\beta_{{dns}}}} = {lx(EI_t, '.0f')}\ \text{{t·m}}^2")
        k_pc = 1.0 if frame == "sway" else res.k
        st.latex(rf"P_c = \frac{{\pi^2(EI)_{{eff}}}}{{(k\ell_u)^2}} = \frac{{\pi^2 \times {lx(EI_t, '.0f')}}}"
                 rf"{{({k_pc:.3f}\times{lu / 1000:.2f})^2}} = {lx(res.Pc / TON, '.1f')}\ \text{{t}}")

        step = 4
        if frame == "sway":
            step_header(4, "ตัวขยายโมเมนต์จากการเซ δs (6.6.4.6)", "#0B1F4D")
            if Q is not None:
                st.latex(rf"\delta_s = \frac{{1}}{{1-Q}} = \frac{{1}}{{1-{Q:.3f}}} = {res.delta_s:.3f}")
            else:
                st.latex(rf"\delta_s = \frac{{1}}{{1-\frac{{\Sigma P_u}}{{0.75\Sigma P_c}}}} = "
                         rf"\frac{{1}}{{1-\frac{{{sumPu:.0f}}}{{0.75\times{sumPc:.0f}}}}} = {res.delta_s:.3f}")
            if "M_top" in res.extra:
                st.latex(rf"M_{{top}} = M_{{ns}} + \delta_sM_s = {Mns_top:.2f} + {res.delta_s:.3f}({Ms_top:.2f}) = "
                         rf"{res.extra['M_top'] / TM:.2f}\ \text{{t·m}}")
                st.latex(rf"M_{{bot}} = M_{{ns}} + \delta_sM_s = {Mns_bot:.2f} + {res.delta_s:.3f}({Ms_bot:.2f}) = "
                         rf"{res.extra['M_bot'] / TM:.2f}\ \text{{t·m}}")
            step = 5

        step_header(step, "ตัวขยายโมเมนต์ตามความยาวเสา δ (6.6.4.5)", C_BRONZE)
        m12 = res.extra.get("M1_M2", 0.0)
        st.latex(rf"M_1 = {res.M1 / TM:.2f},\ M_2 = {res.M2 / TM:.2f}\ \text{{t·m}},\quad "
                 rf"M_1/M_2 = {m12:.3f}")
        st.latex(rf"M_{{2,min}} = P_u(1.5 + 0.03h) = {Pu / TON:.1f}(1.5 + 0.03\times{h_cm:.1f})/100 = "
                 rf"{res.M2_min / TM:.2f}\ \text{{t·m}}")
        cm_expr = "1.0" if (res.use_min or (frame == "nonsway" and transverse_load)) else "0.6 - 0.4(M_1/M_2)"
        st.latex(rf"C_m = {cm_expr} = {res.Cm:.3f}")
        if res.unstable:
            st.error("Pu ≥ 0.75Pc → ไม่มีเสถียรภาพ")
        else:
            st.latex(rf"\delta = \frac{{C_m}}{{1 - \frac{{P_u}}{{0.75P_c}}}} = "
                     rf"\frac{{{res.Cm:.3f}}}{{1 - \frac{{{Pu / TON:.1f}}}{{0.75\times{res.Pc / TON:.1f}}}}}"
                     rf" = {res.delta:.3f}\ \ (\ge 1.0)")
            M2d = max(res.M2, res.M2_min)
            Mc_len = res.extra.get("Mc_length", res.Mc) if frame == "sway" else res.Mc
            st.latex(rf"M_c = \delta M_2 = {res.delta:.3f}\times{M2d / TM:.2f} = {Mc_len / TM:.2f}\ \text{{t·m}}")
            if frame == "sway":
                st.latex(rf"M_{{u,design}} = \max(M_2,\ \delta M_2) = {res.Mc / TM:.2f}\ \text{{t·m}}")

    step_header("✓", "ตรวจสอบกำลัง (22.4, 21.2.2)", C_GREEN if ratio <= 1 else C_RED)
    st.latex(rf"P_o = 0.85f'_c(A_g - A_{{st}}) + f_yA_{{st}} = {lx(diag.Po / TON, '.1f')}\ \text{{t}}")
    st.latex(rf"\phi P_{{n,max}} = {0.75 if transverse == 'spiral' else 0.65}\times"
             rf"{0.85 if transverse == 'spiral' else 0.80}P_o = {lx(diag.phiPn_max / TON, '.1f')}\ \text{{t}}")
    if math.isfinite(ratio):
        st.latex(rf"(P_u, M_c) = ({Pu / TON:.1f}\ \text{{t}},\ {Mc / TM:.2f}\ \text{{t·m}})\quad \text{{vs}}\quad "
                 rf"(\phi P_n, \phi M_n) = ({phiPn_ray / TON:.1f},\ {phiMn_ray / TM:.2f})")
        rel, verdict = (r"\le", "OK") if ratio <= 1 else (">", "NG")
        st.latex(rf"D/C = {ratio:.3f}\ {rel}\ 1.0\ \Rightarrow\ \text{{{verdict}}}")

# ---------------------------------------------------------- Section tab
with tab_sec:
    fs = go.Figure()
    u = 0.1  # drawing in cm
    if sec.shape == "rect":
        bx, hy = sec.b / 2 * u, sec.h / 2 * u
        fs.add_shape(type="rect", x0=-bx, y0=-hy, x1=bx, y1=hy,
                     line=dict(color="#7A859E", width=2), fillcolor="#E3E8F1")
        ti = (sec.cover + dt / 2) * u
        fs.add_shape(type="rect", x0=-bx + ti, y0=-hy + ti, x1=bx - ti, y1=hy - ti,
                     line=dict(color=C_NAVY, width=max(2, dt / 3)))
    else:
        R = sec.h / 2 * u
        fs.add_shape(type="circle", x0=-R, y0=-R, x1=R, y1=R,
                     line=dict(color="#7A859E", width=2), fillcolor="#E3E8F1")
        ti = R - (sec.cover + dt / 2) * u
        fs.add_shape(type="circle", x0=-ti, y0=-ti, x1=ti, y1=ti,
                     line=dict(color=C_NAVY, width=max(2, dt / 3)))
    rb = db / 2 * u
    for bar in sec.bars:
        x, y = bar.x * u, (sec.h / 2 - bar.d) * u
        fs.add_shape(type="circle", x0=x - rb, y0=y - rb, x1=x + rb, y1=y + rb,
                     line=dict(color="#0B1F4D", width=1.5), fillcolor=C_GOLD)
    fs.add_annotation(x=0, y=sec.h / 2 * u * 1.18, text="▲ ผิวรับแรงอัด", showarrow=False,
                      font=dict(color=C_NAVY, size=14))
    lim = max(sec.b, sec.h) / 2 * u * 1.3
    fs.update_xaxes(range=[-lim, lim], scaleanchor="y", scaleratio=1, showgrid=False, title="cm")
    fs.update_yaxes(range=[-lim, lim], showgrid=False)
    fs.update_layout(height=520, margin=dict(l=10, r=10, t=10, b=10), plot_bgcolor="#fff", paper_bgcolor="#fff")

    c1, c2 = st.columns([3, 2])
    c1.plotly_chart(fs, width="stretch")
    with c2:
        st.markdown(f"""
- **หน้าตัด:** {"สี่เหลี่ยม %.1f × %.1f ซม." % (sec.b / 10, sec.h / 10) if sec.shape == "rect" else "วงกลม D = %.1f ซม." % (sec.h / 10)}
- **เหล็กยืน:** {sec.n_bars}-{bar_lbl} (Ast = {sec.Ast / 100:,.2f} ซม.²)
- **เหล็กปลอก:** {tie_lbl} {"@ ≤ %.1f ซม." % (aci.tie_spacing(sec) / 10) if transverse == "tied" else "(ปลอกเกลียว)"}
- **ระยะหุ้ม:** {sec.cover / 10:.1f} ซม.
- **ρg:** {sec.Ast / sec.Ag * 100:.2f} %
""")
        st.dataframe(pd.DataFrame({
            "x (cm)": [round(b_.x / 10, 2) for b_ in sec.bars],
            "d (cm)": [round(b_.d / 10, 2) for b_ in sec.bars],
            "As (cm²)": [round(b_.area / 100, 2) for b_ in sec.bars],
        }), hide_index=True, width="stretch", height=260)

st.divider()
st.caption("⚠️ โปรแกรมนี้เป็นเครื่องมือช่วยออกแบบเบื้องต้น ผู้ใช้ต้องตรวจสอบผลโดยวิศวกรผู้มีใบอนุญาตก่อนใช้งานจริง • "
           "สมมติฐาน: คอนกรีตน้ำหนักปกติ, ดัดแกนเดียว, r ตาม 6.2.5.2, วิธีขยายโมเมนต์ 6.6.4")
