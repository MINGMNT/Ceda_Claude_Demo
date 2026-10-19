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

st.set_page_config(page_title="ออกแบบเสายาว ACI 318-19", page_icon="🏛️", layout="wide")

# Colour palette shared by CSS, cards and charts
C_INDIGO, C_CYAN, C_TEAL = "#6C4CF5", "#00B4D8", "#06D6A0"
C_AMBER, C_ORANGE, C_CORAL = "#FFB703", "#FB8500", "#EF476F"

st.markdown(
    """
    <style>
    /* ---------- page ---------- */
    .block-container {padding-top: 3.2rem;}
    .hero {
        display:flex; align-items:center; gap:22px; padding:26px 30px; border-radius:20px; color:#fff;
        background: linear-gradient(120deg, #6C4CF5 0%, #3A86FF 45%, #00B4D8 75%, #06D6A0 100%);
        box-shadow: 0 10px 30px rgba(108,76,245,.25); margin-bottom: 18px;
    }
    .hero-icon {font-size:3.2rem; background:rgba(255,255,255,.18); border-radius:18px; padding:8px 16px;}
    .hero h1 {color:#fff; font-size:2rem; margin:0; padding:0; line-height:1.25;}
    .hero p  {color:rgba(255,255,255,.92); margin:6px 0 10px 0;}
    .chip {display:inline-block; background:rgba(255,255,255,.22); border:1px solid rgba(255,255,255,.35);
           padding:3px 12px; border-radius:999px; font-size:.82rem; margin-right:6px;}

    /* ---------- sidebar ---------- */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #EDE8FF 0%, #E3F4FF 55%, #E2FBF3 100%);
    }
    section[data-testid="stSidebar"] [data-testid="stExpander"] details {
        background:#ffffffcc; border:none; border-left:5px solid #6C4CF5; border-radius:12px;
        box-shadow:0 2px 8px rgba(31,35,64,.06);
    }
    section[data-testid="stSidebar"] [data-testid="stExpander"] summary p {font-weight:700; color:#3b2db3;}
    .side-title {font-size:1.25rem; font-weight:800; margin:4px 0 10px 0;
                 background:linear-gradient(90deg,#6C4CF5,#00B4D8); -webkit-background-clip:text; color:transparent;}

    /* ---------- tabs as pills ---------- */
    div[role="tablist"] {gap:8px; border-bottom:none !important; box-shadow:none !important; padding-bottom:6px;}
    [data-testid="stTab"] {background:#fff; border-radius:999px !important; padding:8px 18px !important;
        border:1px solid #e1e3f0 !important; box-shadow:0 1px 3px rgba(0,0,0,.05);}
    [data-testid="stTab"]::after, [data-testid="stTab"]::before {display:none !important;}
    [data-testid="stTab"][aria-selected="true"] {background:linear-gradient(90deg,#6C4CF5,#3A86FF);
        border-color:transparent !important;}
    [data-testid="stTab"][aria-selected="true"] p {color:#fff !important; font-weight:700;}

    /* ---------- status banners ---------- */
    .ok, .ng {padding:18px 22px; border-radius:16px; font-size:1.3rem; font-weight:700; color:#fff;}
    .ok {background:linear-gradient(90deg,#06D6A0,#1B9AAA); box-shadow:0 8px 20px rgba(6,214,160,.25);}
    .ng {background:linear-gradient(90deg,#EF476F,#FB8500); box-shadow:0 8px 20px rgba(239,71,111,.25);}
    .warn {background:#FFF6E0; border-left:5px solid #FFB703; color:#7a4b00; padding:10px 14px; border-radius:10px; margin-bottom:8px;}

    /* ---------- metric cards ---------- */
    .card {background:#fff; border-radius:16px; padding:16px 18px; border-top:5px solid var(--c);
           box-shadow:0 4px 14px rgba(31,35,64,.07); height:100%;}
    .card-top {font-size:.85rem; color:#6b6f8a; display:flex; align-items:center; gap:8px;}
    .card-icon {display:inline-flex; width:30px; height:30px; border-radius:10px; align-items:center; justify-content:center;
                background:color-mix(in srgb, var(--c) 16%, white); font-size:1rem;}
    .card-val {font-size:1.75rem; font-weight:800; color:var(--c); margin-top:6px;}
    .card-sub {font-size:.8rem; color:#8a8fa8;}

    /* ---------- panels / chips ---------- */
    .panel-title {font-weight:800; font-size:1.1rem; margin:6px 0 10px 0; color:#1F2340;}
    .panel-title span {display:inline-block; width:10px; height:22px; border-radius:4px; margin-right:8px;
                       vertical-align:-4px; background:var(--c);}
    .check {padding:8px 12px; border-radius:10px; margin-bottom:6px;}
    .check.pass {background:#E3FBF3; border-left:4px solid #06D6A0;}
    .check.fail {background:#FFE8EE; border-left:4px solid #EF476F;}
    .check b {color:#1F2340; font-weight:600;}
    .check i {display:block; font-style:normal; font-size:.85rem; color:#555a75; margin-left:26px;}
    .step {display:inline-flex; align-items:center; justify-content:center; width:34px; height:34px; border-radius:50%;
           color:#fff; font-weight:800; margin-right:10px; background:var(--c);}
    .step-h {font-size:1.2rem; font-weight:800; margin:4px 0 6px 0; color:#1F2340;}
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
        <span class="chip">📘 ACI 318-19</span><span class="chip">📏 mm · MPa · kN · kN·m</span>
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
    fc = st.number_input("f'c (MPa)", 15.0, 100.0, 28.0, 1.0, help="กำลังอัดคอนกรีตทรงกระบอก")
    fy = st.number_input("fy (MPa)", 240.0, 700.0, 420.0, 10.0, help="กำลังครากเหล็กยืน (SD40 = 390, Grade 60 = 420)")
    Es = st.number_input("Es (MPa)", 150000.0, 210000.0, 200000.0, 1000.0)
    Ec_auto = st.checkbox("Ec = 4700√f'c (19.2.2.1)", value=True)
    Ec = aci.Ec_normal(fc) if Ec_auto else st.number_input("Ec (MPa)", 10000.0, 60000.0, aci.Ec_normal(fc), 500.0)
    agg = st.number_input("ขนาดมวลรวมใหญ่สุด (mm)", 10.0, 40.0, 20.0, 5.0)

with sb.expander("📐 2) หน้าตัดและเหล็กเสริม", expanded=True):
    shape_lbl = st.radio("รูปทรงหน้าตัด", ["สี่เหลี่ยม", "วงกลม"], horizontal=True)
    shape = "rect" if shape_lbl == "สี่เหลี่ยม" else "circ"
    trans_lbl = st.radio("เหล็กเสริมทางขวาง", ["ปลอกเดี่ยว (Tied)", "ปลอกเกลียว (Spiral)"], horizontal=True)
    transverse = "tied" if trans_lbl.startswith("ปลอกเดี่ยว") else "spiral"

    if shape == "rect":
        c1, c2 = st.columns(2)
        b = c1.number_input("b (mm)", 150.0, 3000.0, 500.0, 25.0, help="ด้านตั้งฉากกับทิศทางการดัด")
        h = c2.number_input("h (mm)", 150.0, 3000.0, 500.0, 25.0, help="ด้านในทิศทางการดัด (ความลึก)")
    else:
        D = st.number_input("เส้นผ่านศูนย์กลาง D (mm)", 200.0, 3000.0, 500.0, 25.0)

    cover = st.number_input("ระยะหุ้มถึงผิวเหล็กปลอก (mm)", 20.0, 100.0, 40.0, 5.0)
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
    st.info(f"เหล็กยืน {sec.n_bars}-{bar_lbl}  •  Ast = {sec.Ast:,.0f} mm²  •  ρg = {sec.Ast / sec.Ag * 100:.2f}%")

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
    Pu_kN = st.number_input("Pu (kN) — แรงอัด", 0.0, 100000.0, 2000.0, 50.0)
    if frame == "nonsway":
        M2_in = st.number_input("|M2| โมเมนต์ปลายที่มากกว่า (kN·m)", 0.0, 50000.0, 150.0, 5.0)
        M1_in = st.number_input("|M1| โมเมนต์ปลายที่น้อยกว่า (kN·m)", 0.0, 50000.0, 100.0, 5.0)
        curv = st.radio("รูปแบบการดัด", ["ดัดโค้งทางเดียว (Single)", "ดัดโค้งสองทาง (Double)"],
                        help="Single curvature → M1/M2 เป็นลบ")
        transverse_load = st.checkbox("มีแรงกระทำทางขวางระหว่างจุดรองรับ (Cm = 1.0)")
        if M1_in > M2_in:
            st.warning("|M1| ต้องไม่เกิน |M2| — ระบบสลับค่าให้อัตโนมัติ")
            M1_in, M2_in = M2_in, M1_in
    else:
        st.caption("ใส่เครื่องหมาย: ค่าเครื่องหมายเดียวกันที่ปลายบน/ล่าง = ดัดโค้งทางเดียว")
        c1, c2 = st.columns(2)
        Mns_top = c1.number_input("Mns ปลายบน", -50000.0, 50000.0, 40.0, 5.0, help="จากแรงที่ไม่ทำให้เซ (เช่น D, L)")
        Mns_bot = c2.number_input("Mns ปลายล่าง", -50000.0, 50000.0, 20.0, 5.0)
        Ms_top = c1.number_input("Ms ปลายบน", -50000.0, 50000.0, 80.0, 5.0, help="จากแรงที่ทำให้เซ (เช่น W, E)")
        Ms_bot = c2.number_input("Ms ปลายล่าง", -50000.0, 50000.0, -70.0, 5.0)
        ds_method = st.radio("วิธีคำนวณ δs", ["ดัชนีเสถียรภาพ Q", "ΣPu / ΣPc"], horizontal=True)
        if ds_method.startswith("ดัชนี"):
            Q = st.number_input("Q (6.6.4.4.1)", 0.0, 0.99, 0.10, 0.01)
            sumPu = sumPc = None
        else:
            Q = None
            sumPu = st.number_input("ΣPu ทั้งชั้น (kN)", 0.0, 1e7, 20000.0, 500.0)
            sumPc = st.number_input("ΣPc ทั้งชั้น (kN)", 1.0, 1e8, 150000.0, 1000.0,
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
Pu = Pu_kN * 1e3
lu = lu_m * 1e3
diag = aci.interaction_diagram(sec, fc, fy, Es, transverse)

if frame == "nonsway":
    sign = -1.0 if curv.startswith("ดัดโค้งทางเดียว") else 1.0
    res = aci.nonsway_magnification(sec, Pu, sign * M1_in * 1e6, M2_in * 1e6, k, lu, Ec, Es,
                                    beta_dns, ei_method, transverse_load, Po=diag.Po)
    M_first = M2_in * 1e6
else:
    res = aci.sway_magnification(sec, Pu, Mns_top * 1e6, Mns_bot * 1e6, Ms_top * 1e6, Ms_bot * 1e6,
                                 k, lu, Ec, Es, beta_dns, ei_method,
                                 "Q" if Q is not None else "sum", Q=Q,
                                 sumPu=None if sumPu is None else sumPu * 1e3,
                                 sumPc=None if sumPc is None else sumPc * 1e3, Po=diag.Po)
    M_first = max(abs(Mns_top + Ms_top), abs(Mns_bot + Ms_bot)) * 1e6

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


def kNm(x):
    return f"{x / 1e6:,.1f}" if math.isfinite(x) else "∞"


def sci(x):
    """LaTeX scientific notation, e.g. 2.13 \\times 10^{9}."""
    if x == 0:
        return "0"
    e = int(math.floor(math.log10(abs(x))))
    return rf"{x / 10 ** e:.3f}\times10^{{{e}}}"


def kN(x):
    return f"{x / 1e3:,.0f}" if math.isfinite(x) else "∞"


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
    dc_color = C_TEAL if ratio <= 0.9 else (C_AMBER if ratio <= 1.0 else C_CORAL)
    c = st.columns(5)
    card(c[0], "📏", "ความชะลูด kℓu/r", f"{res.klu_r:.1f}", f"ขีดจำกัด {res.limit:.1f}", C_INDIGO)
    card(c[1], "🏛️", "ประเภทเสา", "เสายาว" if res.slender else "เสาสั้น",
         "ต้องขยายโมเมนต์" if res.slender else "ไม่ต้องขยายโมเมนต์", C_CYAN if res.slender else C_TEAL)
    if frame == "sway":
        card(c[2], "🔁", "δs / δ", f"{res.delta_s:.2f} / {res.delta:.2f}", "ตัวขยายโมเมนต์", C_ORANGE)
    else:
        card(c[2], "🔁", "δns", f"{res.delta:.3f}" if math.isfinite(res.delta) else "∞", "ตัวขยายโมเมนต์", C_ORANGE)
    card(c[3], "🌀", "Mc ออกแบบ", kNm(Mc), f"kN·m (จาก {kNm(M_first)})", "#3A86FF")
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
                bar=dict(color="#1F2340", thickness=0.25),
                steps=[dict(range=[0, 70], color="#B8F2E0"), dict(range=[70, 90], color="#9BE7F0"),
                       dict(range=[90, 100], color="#FFE29A"), dict(range=[100, 150], color="#FFB3C4")],
                threshold=dict(line=dict(color=C_CORAL, width=4), thickness=0.85, value=100),
            ),
        ))
        gauge.update_layout(height=250, margin=dict(l=25, r=25, t=10, b=0), paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(gauge, width="stretch")
    with g2:
        panel_title("กำลังของหน้าตัด", C_INDIGO)
        st.dataframe(pd.DataFrame({
            "รายการ": ["Po", "Pn,max", "φPn,max", "φMn ที่แนวรัศมี", "φPn ที่แนวรัศมี", "φMn,b / φPn,b (สมดุล)"],
            "ค่า": [f"{kN(diag.Po)} kN", f"{kN(diag.Pn_max)} kN", f"{kN(diag.phiPn_max)} kN",
                    f"{kNm(phiMn_ray)} kN·m", f"{kN(phiPn_ray)} kN",
                    f"{kNm(diag.balanced[0])} kN·m / {kN(diag.balanced[1])} kN"],
        }), hide_index=True, width="stretch")
    with g3:
        panel_title("ตรวจสอบรายละเอียดเหล็กเสริม", C_TEAL)
        html = "".join(
            f'<div class="check {"pass" if ok else "fail"}"><b>{"✅" if ok else "❌"} {name}</b><i>{val}</i></div>'
            for name, ok, val in detail)
        st.markdown(html, unsafe_allow_html=True)
        if transverse == "tied":
            st.markdown(f"ℹ️ ระยะเรียงปลอกสูงสุด (25.7.2.1) = **{aci.tie_spacing(sec):.0f} mm**")
        elif sec.shape == "circ":
            rho_s = 0.45 * (sec.Ag / (math.pi * (sec.h - 2 * sec.cover) ** 2 / 4) - 1) * fc / fy
            st.markdown(f"ℹ️ ρs ขั้นต่ำของปลอกเกลียว (25.7.3.3) = **{rho_s:.4f}**")

    if res.notes:
        panel_title("หมายเหตุ", C_AMBER)
        for n in res.notes:
            st.markdown(f'<div class="warn">⚠️ {n}</div>', unsafe_allow_html=True)

# --------------------------------------------------------- Interaction diagram
with tab_pm:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=diag.Mn / 1e6, y=diag.Pn / 1e3, name="กำลังระบุ (Mn, Pn)",
                             line=dict(color=C_CYAN, dash="dash", width=2)))
    fig.add_trace(go.Scatter(x=diag.phiMn / 1e6, y=diag.phiPn / 1e3, name="กำลังออกแบบ (φMn, φPn)",
                             line=dict(color=C_INDIGO, width=3.5), fill="tozerox",
                             fillcolor="rgba(108,76,245,0.12)"))
    fig.add_trace(go.Scatter(x=[M_first / 1e6], y=[Pu / 1e3], mode="markers", name="แรงอันดับหนึ่ง (Pu, M2)",
                             marker=dict(size=14, color=C_AMBER, symbol="circle", line=dict(color="#fff", width=2))))
    if math.isfinite(Mc):
        fig.add_trace(go.Scatter(x=[Mc / 1e6], y=[Pu / 1e3], mode="markers",
                                 name="แรงหลังขยายโมเมนต์ (Pu, Mc)",
                                 marker=dict(size=20, color=C_CORAL if ratio > 1 else C_TEAL,
                                             symbol="star", line=dict(color="#fff", width=1.5))))
        fig.add_trace(go.Scatter(x=[0, phiMn_ray / 1e6], y=[0, phiPn_ray / 1e3], mode="lines",
                                 name="แนวรัศมี", line=dict(color="#8a8fa8", width=1.5, dash="dot")))
        if M_first > 0:
            fig.add_annotation(x=Mc / 1e6, y=Pu / 1e3, ax=M_first / 1e6, ay=Pu / 1e3,
                               xref="x", yref="y", axref="x", ayref="y",
                               showarrow=True, arrowhead=3, arrowwidth=2, arrowcolor=C_ORANGE)
    fig.add_trace(go.Scatter(x=[diag.balanced[0] / 1e6], y=[diag.balanced[1] / 1e3], mode="markers",
                             name="จุดสมดุล", marker=dict(size=11, color=C_ORANGE, symbol="diamond")))
    fig.update_layout(
        height=620, xaxis_title="M (kN·m)", yaxis_title="P (kN)",
        legend=dict(orientation="h", y=-0.2), margin=dict(l=20, r=20, t=30, b=40),
        hovermode="closest", template="plotly_white",
        paper_bgcolor="#fff", plot_bgcolor="#FBFAFF", font=dict(color="#1F2340"),
    )
    fig.update_xaxes(zeroline=True, zerolinecolor="#b9bcd3", gridcolor="#ECEAF7", rangemode="tozero")
    fig.update_yaxes(zeroline=True, zerolinecolor="#b9bcd3", gridcolor="#ECEAF7")
    st.plotly_chart(fig, width="stretch")

    with st.expander("ตารางจุดบน Interaction Diagram"):
        sel = np.linspace(0, len(diag.Mn) - 1, 40).astype(int)
        df = pd.DataFrame({
            "c (mm)": [f"{x:.0f}" if np.isfinite(x) else "∞" for x in diag.c[sel]],
            "Pn (kN)": diag.Pn[sel] / 1e3, "Mn (kN·m)": diag.Mn[sel] / 1e6, "φ": diag.phi[sel],
            "φPn (kN)": diag.phiPn[sel] / 1e3, "φMn (kN·m)": diag.phiMn[sel] / 1e6,
        })
        st.dataframe(df.style.format(precision=2), width="stretch", hide_index=True)
        st.download_button("⬇️ ดาวน์โหลด CSV", pd.DataFrame({
            "c_mm": diag.c, "Pn_kN": diag.Pn / 1e3, "Mn_kNm": diag.Mn / 1e6, "phi": diag.phi,
            "phiPn_kN": diag.phiPn / 1e3, "phiMn_kNm": diag.phiMn / 1e6,
        }).to_csv(index=False).encode("utf-8"), "interaction_diagram.csv", "text/csv")

# ---------------------------------------------------------- Calculation tab
with tab_calc:
    step_header(1, "คุณสมบัติหน้าตัด", C_INDIGO)
    dim = f"b \\times h = {sec.b:.0f} \\times {sec.h:.0f}" if sec.shape == "rect" else f"D = {sec.h:.0f}"
    st.latex(rf"{dim}\ \text{{mm}},\quad A_g = {sec.Ag:.0f}\ \text{{mm}}^2,\quad "
             rf"I_g = {sci(sec.Ig)}\ \text{{mm}}^4")
    st.latex(rf"A_{{st}} = {sec.Ast:.0f}\ \text{{mm}}^2,\quad \rho_g = {sec.Ast / sec.Ag:.4f},\quad "
             rf"I_{{se}} = {sci(sec.Ise)}\ \text{{mm}}^4")
    st.latex(rf"E_c = {Ec:.0f}\ \text{{MPa}},\quad \beta_1 = {aci.beta1(fc):.3f},\quad "
             rf"r = {'0.25D' if sec.shape == 'circ' else '0.30h'} = {sec.r:.1f}\ \text{{mm}}\ (6.2.5.2)")

    step_header(2, "ตรวจสอบความชะลูด (6.2.5.1)", "#3A86FF")
    if psiA is not None:
        st.latex(rf"\psi_A = {psiA:.2f},\ \psi_B = {psiB:.2f}\ \Rightarrow\ k = {k:.3f}")
    st.latex(rf"\frac{{k\ell_u}}{{r}} = \frac{{{res.k:.3f}\times{lu:.0f}}}{{{res.r:.1f}}} = {res.klu_r:.2f}")
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
        step_header(3, "ความแข็งแรงประสิทธิผลและแรงวิกฤต (6.6.4.4)", C_CYAN)
        if ei_method == "a":
            st.latex(rf"(EI)_{{eff}} = \frac{{0.4E_cI_g}}{{1+\beta_{{dns}}}} = {sci(res.EI)}\ \text{{N·mm}}^2")
        elif ei_method == "b":
            st.latex(rf"(EI)_{{eff}} = \frac{{0.2E_cI_g + E_sI_{{se}}}}{{1+\beta_{{dns}}}} = "
                     rf"{sci(res.EI)}\ \text{{N·mm}}^2")
        else:
            I = res.extra.get("I", 0.0)
            st.latex(rf"I = \left(0.80 + 25\frac{{A_{{st}}}}{{A_g}}\right)\left(1 - \frac{{M_u}}{{P_uh}} - "
                     rf"0.5\frac{{P_u}}{{P_o}}\right)I_g = {sci(I)}\ (0.35I_g \le I \le 0.875I_g)")
            st.latex(rf"(EI)_{{eff}} = \frac{{E_cI}}{{1+\beta_{{dns}}}} = {sci(res.EI)}\ \text{{N·mm}}^2")
        k_pc = 1.0 if frame == "sway" else res.k
        st.latex(rf"P_c = \frac{{\pi^2(EI)_{{eff}}}}{{(k\ell_u)^2}} = \frac{{\pi^2 \times {sci(res.EI)}}}"
                 rf"{{({k_pc:.3f}\times{lu:.0f})^2}} = {res.Pc / 1e3:.1f}\ \text{{kN}}")

        step = 4
        if frame == "sway":
            step_header(4, "ตัวขยายโมเมนต์จากการเซ δs (6.6.4.6)", C_ORANGE)
            if Q is not None:
                st.latex(rf"\delta_s = \frac{{1}}{{1-Q}} = \frac{{1}}{{1-{Q:.3f}}} = {res.delta_s:.3f}")
            else:
                st.latex(rf"\delta_s = \frac{{1}}{{1-\frac{{\Sigma P_u}}{{0.75\Sigma P_c}}}} = "
                         rf"\frac{{1}}{{1-\frac{{{sumPu:.0f}}}{{0.75\times{sumPc:.0f}}}}} = {res.delta_s:.3f}")
            if "M_top" in res.extra:
                st.latex(rf"M_{{top}} = M_{{ns}} + \delta_sM_s = {Mns_top:.1f} + {res.delta_s:.3f}({Ms_top:.1f}) = "
                         rf"{res.extra['M_top'] / 1e6:.1f}\ \text{{kN·m}}")
                st.latex(rf"M_{{bot}} = M_{{ns}} + \delta_sM_s = {Mns_bot:.1f} + {res.delta_s:.3f}({Ms_bot:.1f}) = "
                         rf"{res.extra['M_bot'] / 1e6:.1f}\ \text{{kN·m}}")
            step = 5

        step_header(step, "ตัวขยายโมเมนต์ตามความยาวเสา δ (6.6.4.5)", C_AMBER)
        m12 = res.extra.get("M1_M2", 0.0)
        st.latex(rf"M_1 = {res.M1 / 1e6:.1f},\ M_2 = {res.M2 / 1e6:.1f}\ \text{{kN·m}},\quad "
                 rf"M_1/M_2 = {m12:.3f}")
        st.latex(rf"M_{{2,min}} = P_u(15 + 0.03h) = {Pu / 1e3:.0f}(15 + 0.03\times{sec.h:.0f})/1000 = "
                 rf"{res.M2_min / 1e6:.1f}\ \text{{kN·m}}")
        cm_expr = "1.0" if (res.use_min or (frame == "nonsway" and transverse_load)) else "0.6 - 0.4(M_1/M_2)"
        st.latex(rf"C_m = {cm_expr} = {res.Cm:.3f}")
        if res.unstable:
            st.error("Pu ≥ 0.75Pc → ไม่มีเสถียรภาพ")
        else:
            st.latex(rf"\delta = \frac{{C_m}}{{1 - \frac{{P_u}}{{0.75P_c}}}} = "
                     rf"\frac{{{res.Cm:.3f}}}{{1 - \frac{{{Pu / 1e3:.0f}}}{{0.75\times{res.Pc / 1e3:.0f}}}}}"
                     rf" = {res.delta:.3f}\ \ (\ge 1.0)")
            M2d = max(res.M2, res.M2_min)
            st.latex(rf"M_c = \delta M_2 = {res.delta:.3f}\times{M2d / 1e6:.1f} = "
                     rf"{res.extra.get('Mc_length', res.Mc) / 1e6 if frame == 'sway' else res.Mc / 1e6:.1f}"
                     rf"\ \text{{kN·m}}")
            if frame == "sway":
                st.latex(rf"M_{{u,design}} = \max(M_2,\ \delta M_2) = {res.Mc / 1e6:.1f}\ \text{{kN·m}}")

    step_header("✓", "ตรวจสอบกำลัง (22.4, 21.2.2)", C_TEAL if ratio <= 1 else C_CORAL)
    st.latex(rf"P_o = 0.85f'_c(A_g - A_{{st}}) + f_yA_{{st}} = {diag.Po / 1e3:.0f}\ \text{{kN}}")
    st.latex(rf"\phi P_{{n,max}} = {0.75 if transverse == 'spiral' else 0.65}\times"
             rf"{0.85 if transverse == 'spiral' else 0.80}P_o = {diag.phiPn_max / 1e3:.0f}\ \text{{kN}}")
    if math.isfinite(ratio):
        st.latex(rf"(P_u, M_c) = ({Pu / 1e3:.0f},\ {Mc / 1e6:.1f})\quad \text{{vs}}\quad "
                 rf"(\phi P_n, \phi M_n) = ({phiPn_ray / 1e3:.0f},\ {phiMn_ray / 1e6:.1f})")
        rel, verdict = (r"\le", "OK") if ratio <= 1 else (">", "NG")
        st.latex(rf"D/C = {ratio:.3f}\ {rel}\ 1.0\ \Rightarrow\ \text{{{verdict}}}")

# ---------------------------------------------------------- Section tab
with tab_sec:
    fs = go.Figure()
    if sec.shape == "rect":
        bx, hy = sec.b / 2, sec.h / 2
        fs.add_shape(type="rect", x0=-bx, y0=-hy, x1=bx, y1=hy,
                     line=dict(color="#7d7f99", width=2), fillcolor="#E4E1F5")
        ti = sec.cover + dt / 2
        fs.add_shape(type="rect", x0=-bx + ti, y0=-hy + ti, x1=bx - ti, y1=hy - ti,
                     line=dict(color=C_CYAN, width=max(2, dt / 3)))
    else:
        R = sec.h / 2
        fs.add_shape(type="circle", x0=-R, y0=-R, x1=R, y1=R,
                     line=dict(color="#7d7f99", width=2), fillcolor="#E4E1F5")
        ti = R - sec.cover - dt / 2
        fs.add_shape(type="circle", x0=-ti, y0=-ti, x1=ti, y1=ti,
                     line=dict(color=C_CYAN, width=max(2, dt / 3)))
    for bar in sec.bars:
        y = sec.h / 2 - bar.d
        fs.add_shape(type="circle", x0=bar.x - db / 2, y0=y - db / 2, x1=bar.x + db / 2, y1=y + db / 2,
                     line=dict(color="#7a2e00", width=1.5), fillcolor=C_ORANGE)
    fs.add_annotation(x=0, y=sec.h / 2 * 1.18, text="▲ ผิวรับแรงอัด", showarrow=False,
                      font=dict(color=C_INDIGO, size=14))
    lim = max(sec.b, sec.h) / 2 * 1.3
    fs.update_xaxes(range=[-lim, lim], scaleanchor="y", scaleratio=1, showgrid=False, title="mm")
    fs.update_yaxes(range=[-lim, lim], showgrid=False)
    fs.update_layout(height=520, margin=dict(l=10, r=10, t=10, b=10), plot_bgcolor="#fff", paper_bgcolor="#fff")

    c1, c2 = st.columns([3, 2])
    c1.plotly_chart(fs, width="stretch")
    with c2:
        st.markdown(f"""
- **หน้าตัด:** {"สี่เหลี่ยม %.0f × %.0f mm" % (sec.b, sec.h) if sec.shape == "rect" else "วงกลม D = %.0f mm" % sec.h}
- **เหล็กยืน:** {sec.n_bars}-{bar_lbl} (Ast = {sec.Ast:,.0f} mm²)
- **เหล็กปลอก:** {tie_lbl} {"@ ≤ %.0f mm" % aci.tie_spacing(sec) if transverse == "tied" else "(ปลอกเกลียว)"}
- **ระยะหุ้ม:** {sec.cover:.0f} mm
- **ρg:** {sec.Ast / sec.Ag * 100:.2f} %
""")
        st.dataframe(pd.DataFrame({
            "x (mm)": [round(b_.x, 1) for b_ in sec.bars],
            "d (mm)": [round(b_.d, 1) for b_ in sec.bars],
            "As (mm²)": [round(b_.area, 1) for b_ in sec.bars],
        }), hide_index=True, width="stretch", height=260)

st.divider()
st.caption("⚠️ โปรแกรมนี้เป็นเครื่องมือช่วยออกแบบเบื้องต้น ผู้ใช้ต้องตรวจสอบผลโดยวิศวกรผู้มีใบอนุญาตก่อนใช้งานจริง • "
           "สมมติฐาน: คอนกรีตน้ำหนักปกติ, ดัดแกนเดียว, r ตาม 6.2.5.2, วิธีขยายโมเมนต์ 6.6.4")
