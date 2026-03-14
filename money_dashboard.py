import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import date, timedelta
import json
import os

# ─── CONFIG ────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="💰 Money Management Dashboard",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── CONSTANTS ─────────────────────────────────────────────────────────────────
INITIAL_CAPITAL = 20_000
TARGET_CAPITAL  = 150_000
MARTINGALE_BETS = [300, 700, 1_650, 3_800, 8_750]   # ไม้ 1-5
ODDS            = 1.80                                # ค่าน้ำ
DATA_FILE       = "mm_data.json"

# ─── CUSTOM CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Sarabun:wght@300;400;600;700&display=swap');

  html, body, [class*="css"] { font-family: 'Sarabun', sans-serif; }

  /* dark card */
  .metric-card {
    background: linear-gradient(135deg, #0f2027, #203a43, #2c5364);
    border-radius: 16px;
    padding: 20px 24px;
    border: 1px solid rgba(255,255,255,0.08);
    box-shadow: 0 8px 32px rgba(0,0,0,0.4);
    text-align: center;
    color: #fff;
    margin-bottom: 8px;
  }
  .metric-card .label  { font-size: 0.78rem; letter-spacing: 2px; text-transform: uppercase; color: #90caf9; }
  .metric-card .value  { font-family: 'Space Mono', monospace; font-size: 1.9rem; font-weight: 700; margin: 4px 0; }
  .metric-card .sub    { font-size: 0.75rem; color: #b0bec5; }
  .green  { color: #69f0ae !important; }
  .red    { color: #ff5252 !important; }
  .yellow { color: #ffd740 !important; }

  /* sidebar */
  section[data-testid="stSidebar"] { background: #0d1b2a; }
  section[data-testid="stSidebar"] * { color: #cfd8dc !important; }

  /* title */
  .dashboard-title {
    font-family: 'Space Mono', monospace;
    font-size: 2rem; font-weight: 700;
    background: linear-gradient(90deg, #29b6f6, #69f0ae);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    margin-bottom: 4px;
  }
  .dashboard-sub { color: #78909c; font-size: 0.9rem; margin-bottom: 24px; }

  /* martingale table */
  .mg-table { width:100%; border-collapse:collapse; font-family:'Space Mono',monospace; font-size:0.85rem; }
  .mg-table th { background:#1a3a5c; color:#90caf9; padding:8px 12px; text-align:left; }
  .mg-table td { padding:8px 12px; border-bottom:1px solid rgba(255,255,255,0.05); color:#cfd8dc; }
  .mg-table tr:hover td { background:rgba(41,182,246,0.08); }
</style>
""", unsafe_allow_html=True)


# ─── DATA PERSISTENCE ──────────────────────────────────────────────────────────
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"records": []}

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def to_df(records):
    if not records:
        return pd.DataFrame(columns=["date","wins","losses","max_step","pnl","equity"])
    df = pd.DataFrame(records)
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)
    return df


# ─── MARTINGALE CALCULATOR ─────────────────────────────────────────────────────
def calc_daily_pnl(wins: int, losses: int, max_step: int) -> float:
    """
    คำนวณ PnL รายวันแบบง่าย:
      - ชนะ: ได้กำไรเท่ากับ bet ไม้แรก × (odds-1) = 300×0.8 = 240 บาท/รอบ
      - แพ้ series ไปถึงไม้ max_step: เสียตามตาราง Martingale
    """
    profit_per_win = MARTINGALE_BETS[0] * (ODDS - 1)   # ~240
    loss_at_step   = sum(MARTINGALE_BETS[:max_step])     # เสียสะสมถึงไม้ max_step

    # แต่ละ series แพ้ทั้งหมด max_step ครั้ง  ชนะ 1 ครั้ง = net กำไร 1 unit
    pnl = (wins * profit_per_win) - (losses * loss_at_step)
    return round(pnl, 2)


# ─── SESSION STATE ─────────────────────────────────────────────────────────────
if "data" not in st.session_state:
    st.session_state.data = load_data()


# ════════════════════════════════════════════════════════════════════════════════
# SIDEBAR – INPUT FORM
# ════════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("## 📋 บันทึกผลรายวัน")
    st.markdown("---")

    input_date  = st.date_input("📅 วันที่", value=date.today())
    wins        = st.number_input("✅ จำนวนครั้งที่ชนะ (series)", min_value=0, value=0, step=1)
    losses      = st.number_input("❌ จำนวนครั้งที่แพ้ (series)", min_value=0, value=0, step=1)
    max_step    = st.selectbox("⚠️ ไม้สูงสุดที่ถูกใช้วันนี้", options=[1,2,3,4,5],
                               format_func=lambda x: f"ไม้ {x}  (เดิมพัน {MARTINGALE_BETS[x-1]:,} บาท)")
    note        = st.text_input("📝 หมายเหตุ", placeholder="เช่น ช่วยเช้า, ไม่เล่นช่วงบ่าย")

    st.markdown("---")
    add_btn    = st.button("➕ บันทึกผล", use_container_width=True, type="primary")
    clear_btn  = st.button("🗑️ ล้างข้อมูลทั้งหมด", use_container_width=True)

    if add_btn:
        pnl = calc_daily_pnl(wins, losses, max_step)
        records = st.session_state.data["records"]

        # หา equity ล่าสุด
        prev_equity = INITIAL_CAPITAL
        if records:
            prev_equity = records[-1]["equity"]

        record = {
            "date":     str(input_date),
            "wins":     wins,
            "losses":   losses,
            "max_step": max_step,
            "pnl":      pnl,
            "equity":   round(prev_equity + pnl, 2),
            "note":     note,
        }
        # ป้องกัน duplicate วันเดิม
        existing = [i for i, r in enumerate(records) if r["date"] == str(input_date)]
        if existing:
            records[existing[0]] = record
            st.success("✏️ อัปเดตข้อมูลวันนี้แล้ว")
        else:
            records.append(record)
            st.success(f"✅ บันทึกแล้ว | PnL = {pnl:+,.0f} ฿")

        save_data(st.session_state.data)
        st.rerun()

    if clear_btn:
        st.session_state.data = {"records": []}
        save_data(st.session_state.data)
        st.success("🗑️ ล้างข้อมูลแล้ว")
        st.rerun()

    # Martingale reference table
    st.markdown("---")
    st.markdown("### 📊 ตาราง Martingale")
    rows = ""
    cum  = 0
    for i, b in enumerate(MARTINGALE_BETS, 1):
        cum += b
        profit = b * (ODDS - 1)
        rows += f"<tr><td>ไม้ {i}</td><td>{b:,}</td><td>{cum:,}</td><td>+{profit:.0f}</td></tr>"
    st.markdown(f"""
    <table class="mg-table">
      <tr><th>ไม้</th><th>เดิมพัน ฿</th><th>สะสม ฿</th><th>ถ้าชนะ</th></tr>
      {rows}
    </table>""", unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════════════════════
# MAIN DASHBOARD
# ════════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="dashboard-title">💰 Money Management Dashboard</div>', unsafe_allow_html=True)
st.markdown('<div class="dashboard-sub">Martingale 5 ไม้ · ทุนตั้งต้น 20,000 ฿ · เป้าหมาย 150,000 ฿ · ค่าน้ำ 1.80</div>', unsafe_allow_html=True)

df = to_df(st.session_state.data["records"])

# ─── KPI CARDS ─────────────────────────────────────────────────────────────────
current_equity = df["equity"].iloc[-1] if len(df) else INITIAL_CAPITAL
total_pnl      = current_equity - INITIAL_CAPITAL
progress_pct   = min((current_equity - INITIAL_CAPITAL) / (TARGET_CAPITAL - INITIAL_CAPITAL) * 100, 100)
total_wins     = int(df["wins"].sum())   if len(df) else 0
total_losses   = int(df["losses"].sum()) if len(df) else 0
win_rate       = total_wins / (total_wins + total_losses) * 100 if (total_wins + total_losses) > 0 else 0
step5_days     = int((df["max_step"] == 5).sum()) if len(df) else 0

equity_color = "green" if current_equity >= INITIAL_CAPITAL else "red"
pnl_color    = "green" if total_pnl >= 0 else "red"

c1, c2, c3, c4, c5 = st.columns(5)

for col, label, val, sub, color in [
    (c1, "EQUITY ปัจจุบัน",    f"{current_equity:,.0f} ฿", f"เริ่มต้น {INITIAL_CAPITAL:,} ฿", equity_color),
    (c2, "กำไร / ขาดทุนรวม",   f"{total_pnl:+,.0f} ฿",    f"Progress {progress_pct:.1f}%",    pnl_color),
    (c3, "Win Rate",            f"{win_rate:.1f}%",          f"W:{total_wins}  L:{total_losses}", "yellow"),
    (c4, "วันที่ถึงไม้ 5",      f"{step5_days} วัน",        f"จากทั้งหมด {len(df)} วัน",        "red" if step5_days > 0 else "green"),
    (c5, "เหลือถึงเป้า",        f"{max(TARGET_CAPITAL-current_equity,0):,.0f} ฿", f"เป้า {TARGET_CAPITAL:,} ฿", "yellow"),
]:
    col.markdown(f"""
    <div class="metric-card">
      <div class="label">{label}</div>
      <div class="value {color}">{val}</div>
      <div class="sub">{sub}</div>
    </div>""", unsafe_allow_html=True)

# Progress bar
st.markdown(f"""
<div style="background:#1a2a3a;border-radius:12px;height:14px;margin:8px 0 24px 0;overflow:hidden;border:1px solid rgba(255,255,255,0.08)">
  <div style="background:linear-gradient(90deg,#29b6f6,#69f0ae);width:{progress_pct:.1f}%;height:100%;border-radius:12px;transition:width .6s ease"></div>
</div>
""", unsafe_allow_html=True)

# ─── CHARTS ────────────────────────────────────────────────────────────────────
if len(df) > 0:
    col_left, col_right = st.columns([3, 2])

    # ── Equity Curve ──────────────────────────────────────────────────────────
    with col_left:
        st.markdown("#### 📈 Equity Curve vs เป้าหมาย")

        # เพิ่มจุด origin
        dates_full  = [df["date"].min() - timedelta(days=1)] + df["date"].tolist()
        equity_full = [INITIAL_CAPITAL] + df["equity"].tolist()

        fig_eq = go.Figure()

        # Target zone
        fig_eq.add_hrect(y0=TARGET_CAPITAL, y1=TARGET_CAPITAL*1.05,
                         fillcolor="rgba(105,240,174,0.06)", line_width=0)
        # Target line
        fig_eq.add_hline(y=TARGET_CAPITAL, line_dash="dot", line_color="#69f0ae",
                         annotation_text="🎯 เป้าหมาย 150k", annotation_position="top left",
                         annotation_font_color="#69f0ae")
        # Initial line
        fig_eq.add_hline(y=INITIAL_CAPITAL, line_dash="dash", line_color="#546e7a",
                         annotation_text="ทุนตั้งต้น 20k", annotation_position="bottom left",
                         annotation_font_color="#546e7a")
        # Area fill
        fig_eq.add_trace(go.Scatter(
            x=dates_full, y=equity_full,
            fill="tozeroy", fillcolor="rgba(41,182,246,0.08)",
            line=dict(color="#29b6f6", width=2.5),
            mode="lines+markers",
            marker=dict(size=6, color="#29b6f6",
                        line=dict(color="#0d1b2a", width=1.5)),
            name="Equity",
            hovertemplate="วันที่: %{x|%d/%m/%Y}<br>Equity: %{y:,.0f} ฿<extra></extra>",
        ))

        fig_eq.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(13,27,42,0.6)",
            font=dict(color="#cfd8dc", family="Sarabun"),
            margin=dict(l=0, r=0, t=10, b=0),
            height=340,
            xaxis=dict(gridcolor="rgba(255,255,255,0.05)", showgrid=True,
                       tickformat="%d/%m", tickfont=dict(size=11)),
            yaxis=dict(gridcolor="rgba(255,255,255,0.05)", showgrid=True,
                       tickformat=",.0f", ticksuffix=" ฿", tickfont=dict(size=11)),
            showlegend=False,
        )
        st.plotly_chart(fig_eq, use_container_width=True)

    # ── Daily PnL Bar ─────────────────────────────────────────────────────────
    with col_right:
        st.markdown("#### 📊 กำไร/ขาดทุนรายวัน")

        colors = ["#69f0ae" if v >= 0 else "#ff5252" for v in df["pnl"]]
        fig_bar = go.Figure(go.Bar(
            x=df["date"], y=df["pnl"],
            marker_color=colors,
            text=[f"{v:+,.0f}" for v in df["pnl"]],
            textposition="outside",
            textfont=dict(size=10, color="#cfd8dc"),
            hovertemplate="วันที่: %{x|%d/%m/%Y}<br>PnL: %{y:+,.0f} ฿<extra></extra>",
        ))
        fig_bar.add_hline(y=0, line_color="#546e7a", line_width=1)
        fig_bar.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(13,27,42,0.6)",
            font=dict(color="#cfd8dc", family="Sarabun"),
            margin=dict(l=0, r=0, t=10, b=0),
            height=340,
            xaxis=dict(gridcolor="rgba(255,255,255,0.05)", tickformat="%d/%m", tickfont=dict(size=11)),
            yaxis=dict(gridcolor="rgba(255,255,255,0.05)", tickformat="+,.0f", ticksuffix=" ฿", tickfont=dict(size=11)),
            showlegend=False,
        )
        st.plotly_chart(fig_bar, use_container_width=True)

    # ─── SUMMARY TABLE ────────────────────────────────────────────────────────
    st.markdown("#### 📋 ตารางสรุปรายวัน")

    display_df = df.copy()
    display_df["date"]      = display_df["date"].dt.strftime("%d/%m/%Y")
    display_df["equity"]    = display_df["equity"].apply(lambda x: f"{x:,.0f} ฿")
    display_df["pnl"]       = display_df["pnl"].apply(lambda x: f"{x:+,.0f} ฿")
    display_df["win_rate"]  = (display_df["wins"] /
                               (display_df["wins"] + display_df["losses"]).replace(0, 1) * 100
                               ).apply(lambda x: f"{x:.0f}%")
    display_df["max_step"]  = display_df["max_step"].apply(lambda x: f"ไม้ {x}")

    display_df = display_df[["date","wins","losses","win_rate","max_step","pnl","equity","note"]]
    display_df.columns = ["วันที่","ชนะ","แพ้","Win Rate","ไม้สูงสุด","PnL","Equity","หมายเหตุ"]

    st.dataframe(
        display_df[::-1],
        use_container_width=True,
        hide_index=True,
        column_config={
            "PnL":    st.column_config.TextColumn("PnL"),
            "Equity": st.column_config.TextColumn("Equity"),
        }
    )

    # ─── STEP 5 ANALYTICS ─────────────────────────────────────────────────────
    if step5_days > 0:
        st.warning(f"⚠️  มี **{step5_days} วัน** ที่เดินเงินถึงไม้ 5 (เดิมพัน 8,750 ฿) — คิดเป็น {step5_days/len(df)*100:.1f}% ของทุกวันที่บันทึก")

else:
    st.info("📭 ยังไม่มีข้อมูล — กรุณากรอกผลรายวันในแถบซ้ายมือเพื่อเริ่มต้น")

    # Show demo hint
    st.markdown("""
    <div style="background:rgba(41,182,246,0.08);border:1px solid rgba(41,182,246,0.2);border-radius:12px;padding:20px;margin-top:16px;color:#cfd8dc">
    <b style="color:#29b6f6">💡 วิธีใช้งาน</b><br><br>
    1. กรอก <b>วันที่</b> และจำนวน <b>ชนะ/แพ้</b> ในแต่ละวัน<br>
    2. เลือก <b>ไม้สูงสุด</b> ที่ถูกใช้วันนั้น<br>
    3. กด <b>บันทึกผล</b> เพื่อเพิ่มข้อมูล<br>
    4. กราฟและตารางจะอัปเดตอัตโนมัติ
    </div>
    """, unsafe_allow_html=True)
