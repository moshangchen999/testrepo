import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import numpy as np # Added for np.ceil
import re
import time
import toml
import os
from collections import defaultdict

# 页面配置
st.set_page_config(
    page_title="临床试验运营数据看板",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 自定义CSS样式（用于st.container卡片）
st.markdown("""
<style>
    .stCard {
        background-color: #fff;
        border: 1px solid #e0e0e0;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.08);
        padding: 20px 10px 10px 10px;
        margin: 10px 0px 10px 0px;
        height: 350px;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: flex-start;
    }
    .stCardTitle {
        font-size: 18px;
        font-weight: bold;
        color: #333;
        margin-bottom: 10px;
        text-align: center;
    }
    .stCardNumber {
        font-size: 32px;
        font-weight: bold;
        color: #1976d2;
        text-align: center;
        margin-bottom: 8px;
    }
    .stCardSubtitle {
        text-align: center;
        font-weight: bold;
        margin-bottom: 0px;
    }
    .card-content {
        min-height: 180px;
        height: 180px;
        overflow-y: auto;
        display: flex;
        align-items: center;
        justify-content: center;
        color: #666;
        /* font-style: italic; */
        font-style: normal;
    }
</style>
""", unsafe_allow_html=True)

st.title("🏥 临床试验运营数据看板")
st.markdown("---")

# 数据上传
uploaded_file = st.file_uploader("请上传包含 study_number, study_ctn_plan_date, study_ctn_actual_date 字段的CSV", type=["csv"])
df = None
if uploaded_file:
    try:
        df = pd.read_csv(uploaded_file, encoding="utf-8")
    except UnicodeDecodeError:
        uploaded_file.seek(0)
        df = pd.read_csv(uploaded_file, encoding="gbk")
    # 字段名标准化
    df.columns = [col.strip().lower().replace(" ", "_") for col in df.columns]
    required_cols = ["study_number", "study_ctn_plan_date", "study_ctn_actual_date"]
    if not all(col in df.columns for col in required_cols):
        st.error(f"CSV缺少必要字段: {required_cols}")
        df = None
    else:
        df['study_number'] = df['study_number'].astype(str)
        # 对所有以_date结尾的字段做标准化
        for col in df.columns:
            if col.endswith('_date'):
                df[col] = pd.to_datetime(df[col], errors='coerce')

# === 新增：卡片A和卡片B单独一行 ===
row_top = st.columns(2)

def render_risk_results(results, title):
    from collections import defaultdict
    study_msgs = defaultdict(set)
    for study, ta, sourcing, reason in results:
        study_msgs[(study, ta, sourcing)].add(reason)
    html = ''
    if study_msgs:
        if title:
            html = f'<div style="line-height:1.25;"><span style="font-size:18px;font-weight:bold;color:#1976d2;display:inline-block;margin-bottom:16px;">{title}</span><br>'
        else:
            html = '<div style="line-height:1.25;">'
        for (study, ta, sourcing), msgs in study_msgs.items():
            msg_list = sorted(msgs)
            # 主bullet符号改为◦
            prefix = f'◦ <b>{study}</b> '
            if ta or sourcing:
                prefix += f'（{ta + ("/" if ta and sourcing else "") + sourcing}）'
            prefix += '：'
            if len(msg_list) > 0:
                # 子bullet符号改为•
                html += f'<div style="margin-bottom:2px;">{prefix}<ul style="margin:0 0 0 18px;padding:0;list-style-type:disc;">'
                for msg in msg_list:
                    html += f'<li style="margin:0 0 0 0;padding:0 0 0 0;word-break:break-all;list-style-type:disc;">{msg}</li>'
                html += '</ul></div>'
        html += '</div>'
    return html

with row_top[0]:
    with st.container():
        st.markdown('''
<style>
.milestone5wks-title-flex {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  position: relative;
}
.milestone5wks-title {
  font-size: 18px;
  font-weight: bold;
  color: #222;
  margin-bottom: 0px;
  text-align: center;
  display: flex;
  align-items: center;
  justify-content: center;
}
.milestone5wks-balloon {
  margin-left: 10px;
  cursor: pointer;
  position: relative;
  font-size: 22px;
  line-height: 1;
  display: inline-block;
}
.milestone5wks-balloon .balloon-tooltip {
  visibility: hidden;
  opacity: 0;
  min-width: 340px;
  max-width: 900px;
  background: #fffbe7;
  color: #333;
  text-align: left;
  border-radius: 8px;
  border: 1px solid #e0e0e0;
  padding: 12px 16px;
  position: absolute;
  z-index: 10;
  top: 32px;
  left: 50%;
  transform: translateX(-50%);
  font-size: 15px;
  box-shadow: 0 2px 8px rgba(25,118,210,0.08);
  transition: opacity 0.2s;
  line-height: 1.7;
}
.milestone5wks-balloon .balloon-tooltip .nowrap-line {
  white-space: nowrap;
  display: block;
}
.milestone5wks-balloon:hover .balloon-tooltip {
  visibility: visible;
  opacity: 1;
}
</style>
<div class="milestone5wks-title-flex" style="border:2px solid #1976d2;border-radius:10px;padding:8px 0 0 0;box-shadow:0 2px 8px rgba(25,118,210,0.08);">
  <span class="milestone5wks-title">Missed Milestones in Last 5wks</span>
  <span class="milestone5wks-balloon">🎈
    <span class="balloon-tooltip">
      <span class="nowrap-line"><b>Target:</b></span>
      <span class="nowrap-line">Leading Site EC Approval Date≤ CTN</span>
      <span class="nowrap-line">Leading Site  Signed Contract Available Date （main）≤ CTN</span>
      <span class="nowrap-line">Country Package Ready≤ CTN-12wks</span>
      <span class="nowrap-line">Country Contract Template Available≤ CTN-12wks</span>
      <span class="nowrap-line">IMP Ready≤ CTN+8.5wks</span>
      <span class="nowrap-line">Facility Ready≤ CTN+8.5wks</span>
      <span class="nowrap-line">HGRAC Initial Approval≤ CTN+8.5wks</span>
      <span class="nowrap-line">FSA Date≤ CTN+9wks</span>
      <span class="nowrap-line">FPS Date≤ CTN+12wks</span>
      <span class="nowrap-line">25% SA Date≤ CTN+13wks</span>
      <span class="nowrap-line">75% SA Date≤ CTN+19wks</span>
    </span>
  </span>
</div>
<div style="height: 10px;"></div>
''', unsafe_allow_html=True)
        # === 新增内容区域A逻辑 ===
        if df is not None:
            now = pd.Timestamp.now()
            five_weeks_ago = now - pd.Timedelta(weeks=5)
            milestone_defs = [
                ("FSA", "study_fsa_actual_date", "study_fsa_plan_date", 9),
                ("FPS", "study_fps_actual_date", "study_fps_plan_date", 12),
                ("25% SA", "site_sa_actual_date", "site_sa_plan_date", 13, 0.25),
                ("75% SA", "site_sa_actual_date", "site_sa_plan_date", 19, 0.75),
                ("IMP", "study_imp_ready_actual_date", "study_imp_ready_plan_date", 8.5),
                ("Facility", "study_sfr_actual_date", "study_sfr_plan_date", 8.5),
                ("HGRAC", "study_hia_actual_date", "study_hia_plan_date", 8.5),
                ("Leading EC Approval", "ec_approval_actual_date", "ec_approval_plan_date", 0, "leading"),
                ("Leading Contract", "contract_signoff_actual_date", "contract_signoff_plan_date", 0, "leading"),
                ("Country Package", "country_package_ready_actual_date", "country_package_ready_plan_date", -12)
            ]
            # study维度收集超期milestone
            study_miss = {}
            for study in df['study_number'].dropna().unique():
                study_df = df[df['study_number'] == study]
                # 获取TA/Sourcing
                ta = study_df['clintrack_ta_desc'].iloc[0] if 'clintrack_ta_desc' in study_df.columns else ''
                sourcing = study_df['sourcing_strategy'].iloc[0] if 'sourcing_strategy' in study_df.columns else ''
                # CTN基准
                ctn_actual = study_df['study_ctn_actual_date'].iloc[0] if 'study_ctn_actual_date' in study_df.columns else pd.NaT
                ctn_plan = study_df['study_ctn_plan_date'].iloc[0] if 'study_ctn_plan_date' in study_df.columns else pd.NaT
                ctn_base = pd.to_datetime(ctn_actual) if pd.notna(ctn_actual) else (pd.to_datetime(ctn_plan) if pd.notna(ctn_plan) else None)
                if ctn_base is None:
                    continue
                missed = []
                for m in milestone_defs:
                    m_name = m[0]
                    actual_col = m[1]
                    plan_col = m[2]
                    week_offset = m[3]
                    # 特殊处理25%/75% SA和leading site
                    if m_name in ["25% SA", "75% SA"]:
                        # 只统计site_scope
                        site_scope = study_df[
                            (study_df['ssus'].notna()) |
                            ((study_df['ssus'].isna()) & (study_df['site_status'] == 'Initiating')) |
                            (
                                (study_df['ssus_assignment_date'].notna()) &
                                (study_df['study_fsa_actual_date'].notna()) &
                                (pd.to_datetime(study_df['ssus_assignment_date'], errors='coerce') <= pd.to_datetime(study_df['study_fsa_actual_date'], errors='coerce'))
                            )
                        ].copy() if 'ssus' in study_df.columns and 'site_status' in study_df.columns and 'ssus_assignment_date' in study_df.columns and 'study_fsa_actual_date' in study_df.columns else study_df.copy()
                        n_sites = len(site_scope)
                        if n_sites == 0:
                            continue
                        frac = m[4]
                        n_frac = max(1, int(np.ceil(n_sites * frac)))
                        
                        # 修改：按照正确的75% SA逻辑，与Study Details表格保持一致
                        site_scope['sa_actual'] = pd.to_datetime(site_scope['site_sa_actual_date'], errors='coerce')
                        site_scope['sa_plan'] = pd.to_datetime(site_scope['site_sa_plan_date'], errors='coerce')
                        
                        # 按actual日期排序，如果actual为空则用plan日期
                        site_scope['sa_date'] = site_scope['sa_actual'].fillna(site_scope['sa_plan'])
                        top_sites = site_scope.sort_values('sa_date').head(n_frac)
                        
                        # 检查是否有足够的数据量
                        top_sites_actual = top_sites['sa_actual']
                        top_sites_plan = top_sites['sa_plan']
                        target = ctn_base + pd.Timedelta(weeks=week_offset)
                        
                        # 只统计目标日期在过去5周内
                        if target is not None and five_weeks_ago <= target <= now:
                            # 1. 检查是否有足够数量的actual site activation date（第75分位的site有actual日期）
                            if top_sites_actual.notna().all():
                                sa_actual_max = top_sites_actual.max()
                                if sa_actual_max > target:
                                    missed.append(m_name)
                            # 2. 检查是否有足够数量的plan site activation date（第75分位的site有plan日期）
                            elif top_sites['sa_date'].notna().all():
                                sa_date_max = top_sites['sa_date'].max()
                                if sa_date_max > target:
                                    missed.append(m_name)
                            # 3. 当数据缺失时，不纳入统计
                    elif len(m) == 5 and m[4] == "leading":
                        # 只看leading site
                        if 'leading_site_or_not' in study_df.columns:
                            lead_rows = study_df[study_df['leading_site_or_not'].astype(str).str.upper() == 'YES']
                        else:
                            lead_rows = study_df
                        if lead_rows.empty:
                            continue
                        actual = lead_rows[actual_col].iloc[0] if actual_col in lead_rows.columns else pd.NaT
                        plan = lead_rows[plan_col].iloc[0] if plan_col in lead_rows.columns else pd.NaT
                        target = ctn_base + pd.Timedelta(weeks=week_offset)
                        # 只统计目标日期在5周内
                        if target is not None and five_weeks_ago <= target <= now:
                            # 超期完成
                            if pd.notna(actual) and actual > target:
                                missed.append(m_name)
                            # 超期未完成
                            elif pd.isna(actual) and now > target:
                                missed.append(m_name)
                    else:
                        actual = study_df[actual_col].dropna().sort_values().iloc[0] if actual_col in study_df.columns and study_df[actual_col].notna().any() else pd.NaT
                        plan = study_df[plan_col].dropna().sort_values().iloc[0] if plan_col in study_df.columns and study_df[plan_col].notna().any() else pd.NaT
                        target = ctn_base + pd.Timedelta(weeks=week_offset)
                        # 只统计目标日期在5周内
                        if target is not None and five_weeks_ago <= target <= now:
                            # 超期完成
                            if pd.notna(actual) and actual > target:
                                missed.append(m_name)
                            # 超期未完成
                            elif pd.isna(actual) and now > target:
                                missed.append(m_name)
                if missed:
                    study_miss[study] = {
                        'ta': ta,
                        'sourcing': sourcing,
                        'milestones': missed
                    }
            # 按优先级排序
            priority = ["FSA", "FPS", "25% SA", "75% SA", "IMP", "Facility", "HGRAC", "Leading EC Approval", "Leading Contract", "Country Package"]
            def sort_milestones(milestones):
                return sorted(milestones, key=lambda x: priority.index(x) if x in priority else 99)
            # 渲染为bulleted HTML
            html = '<div style="line-height:1.25;">'
            for study, info in study_miss.items():
                ta = info['ta']
                sourcing = info['sourcing']
                ms = sort_milestones(info['milestones'])
                ms_str = ', '.join(ms)
                html += f'<div style="margin-bottom:2px;">• <b>{study}</b> '
                if ta or sourcing:
                    html += f'（{ta + ("/" if ta and sourcing else "") + sourcing}）'
                html += f'：{ms_str}</div>'
            html += '</div>'
            if study_miss:
                st.markdown(f'<div class="card-content" style="border:2px solid #1976d2;border-radius:10px;padding:16px;box-shadow:0 2px 8px rgba(25,118,210,0.08);line-height:1.25;color:#222;">{html}</div>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="card-content">近5周无超期milestone</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="card-content">请上传包含 study_number, study_ctn_plan_date, study_ctn_actual_date 字段的CSV</div>', unsafe_allow_html=True)
with row_top[1]:
    with st.container():
        st.markdown('<div class="stCardTitle" style="border:2px solid #1976d2;border-radius:10px;padding:8px 0 0 0;box-shadow:0 2px 8px rgba(25,118,210,0.08);">Milestone with Potential Risks</div>', unsafe_allow_html=True)
        if df is not None:
            now = pd.Timestamp.now()
            five_weeks_later = now + pd.Timedelta(weeks=5)
            milestone_defs = [
                ("Leading EC Approval", "ec_approval_plan_date", 0, "Leading EC Approval计划晚于CTN"),
                ("Leading Contract", "contract_signoff_plan_date", 0, "Leading Contract计划晚于CTN"),
                ("Country Package", "country_package_ready_plan_date", -12, "Country Package计划晚于CTN-12wks"),
                ("IMP", "study_imp_ready_plan_date", 8.5, "IMP计划晚于CTN+8.5wks，FSA和FPS可能受影响"),
                ("Facility", "study_sfr_plan_date", 8.5, "Facility计划晚于CTN+8.5wks，FSA和FPS可能受影响"),
                ("HGRAC", "study_hia_plan_date", 8.5, "HGRAC计划晚于CTN+8.5wks，FSA和FPS可能受影响"),
                ("FSA", "study_fsa_plan_date", 9, "FSA计划晚于CTN+9wks"),
                ("FPS", "study_fps_plan_date", 12, "FPS计划晚于CTN+12wks"),
                ("25% SA", "site_sa_plan_date", 13, "25% SA计划晚于CTN+13wks", 0.25),
                ("75% SA", "site_sa_plan_date", 19, "75% SA计划晚于CTN+19wks", 0.75)
            ]
            results = []  # 未来5周内
            results_later = []  # 未来5周之后
            study_list = df['study_number'].dropna().unique()
            for study in study_list:
                study_df = df[df['study_number'] == study]
                ta = study_df['clintrack_ta_desc'].iloc[0] if 'clintrack_ta_desc' in study_df.columns else ''
                sourcing = study_df['sourcing_strategy'].iloc[0] if 'sourcing_strategy' in study_df.columns else ''
                ctn_actual = study_df['study_ctn_actual_date'].iloc[0] if 'study_ctn_actual_date' in study_df.columns else pd.NaT
                ctn_plan = study_df['study_ctn_plan_date'].iloc[0] if 'study_ctn_plan_date' in study_df.columns else pd.NaT
                ctn_base = pd.to_datetime(ctn_actual) if pd.notna(ctn_actual) else (pd.to_datetime(ctn_plan) if pd.notna(ctn_plan) else None)
                if ctn_base is None:
                    continue
                for m in milestone_defs:
                    m_name = m[0]
                    plan_col = m[1]
                    week_offset = m[2]
                    reason = m[3]
                    # 25%/75% SA特殊处理
                    if m_name in ["25% SA", "75% SA"]:
                        frac = m[4]
                        site_scope = study_df[
                            (study_df['ssus'].notna()) |
                            ((study_df['ssus'].isna()) & (study_df['site_status'] == 'Initiating')) |
                            (
                                (study_df['ssus_assignment_date'].notna()) &
                                (study_df['study_fsa_actual_date'].notna()) &
                                (pd.to_datetime(study_df['ssus_assignment_date'], errors='coerce') <= pd.to_datetime(study_df['study_fsa_actual_date'], errors='coerce'))
                            )
                        ].copy() if 'ssus' in study_df.columns and 'site_status' in study_df.columns and 'ssus_assignment_date' in study_df.columns and 'study_fsa_actual_date' in study_df.columns else study_df.copy()
                        n_sites = len(site_scope)
                        if n_sites == 0:
                            continue
                        n_frac = max(1, int(np.ceil(n_sites * frac)))
                        site_scope['sa_plan'] = pd.to_datetime(site_scope['site_sa_plan_date'], errors='coerce')
                        site_scope['sa_actual'] = pd.to_datetime(site_scope['site_sa_actual_date'], errors='coerce')
                        
                        # 按actual日期排序，如果actual为空则用plan日期
                        site_scope['sa_date'] = site_scope['sa_actual'].fillna(site_scope['sa_plan'])
                        top_sites = site_scope.sort_values('sa_date').head(n_frac)
                        
                        # 修改：按照正确的25%/75% SA逻辑，与Study Details表格保持一致
                        # 检查是否有足够的数据量
                        top_sites_actual = top_sites['sa_actual']
                        top_sites_plan = top_sites['sa_plan']
                        
                        # 1. 检查前25%/75分位的site是否都有actual日期
                        if top_sites_actual.notna().all():
                            # 如果前25%/75分位的site都有actual日期，说明milestone已完成，跳过风险判断
                            continue
                        # 2. 检查前25%/75分位的site是否都有日期（actual或plan）
                        # 如果某个site没有plan日期，它必须有actual日期
                        elif top_sites['sa_date'].notna().all():
                            # 取第25%/75分位那家site的日期（优先actual，没有actual的用plan）
                            sa_date_max = top_sites['sa_date'].max()
                            target = ctn_base + pd.Timedelta(weeks=week_offset)
                            if now < target <= five_weeks_later and sa_date_max > target:
                                results.append((study, ta, sourcing, reason))
                            elif target > five_weeks_later and sa_date_max > target:
                                results_later.append((study, ta, sourcing, reason))
                        # 3. 当数据缺失时，不纳入风险判断
                    else:
                        # 新增：FPS相关逻辑前，判断FSA未完成影响
                        if m_name == "FPS":
                            fsa_actual = study_df['study_fsa_actual_date'].dropna() if 'study_fsa_actual_date' in study_df.columns else pd.Series(dtype='datetime64[ns]')
                            fsa_target = ctn_base + pd.Timedelta(weeks=9)
                            fps_target = ctn_base + pd.Timedelta(weeks=12)
                            if now > fsa_target and now <= fps_target and fsa_actual.empty:
                                results.append((study, ta, sourcing, 'FSA尚未完成，FPS可能受影响'))
                        plan = study_df[plan_col].dropna().sort_values().iloc[0] if plan_col in study_df.columns and study_df[plan_col].notna().any() else pd.NaT
                        target = ctn_base + pd.Timedelta(weeks=week_offset)
                        if pd.notna(plan):
                            if now < target <= five_weeks_later and plan > target:
                                results.append((study, ta, sourcing, reason))
                            elif target > five_weeks_later and plan > target:
                                results_later.append((study, ta, sourcing, reason))
            # 分为左右两列展示
            col_left, col_right = st.columns(2)
            with col_left:
                html_left = render_risk_results(results, 'Milestone Risks in Next 5wks') if results else ''
                if html_left:
                    # 固定卡片高度为180px，标题始终可见，内容区overflow-y: auto，内容左对齐
                    st.markdown('''
<div style="border:2px solid #1976d2;border-radius:10px;padding:0;box-shadow:0 2px 8px rgba(25,118,210,0.08);background:#fff;height:180px;display:flex;flex-direction:column;">
  <div style="font-size:18px;font-weight:bold;color:#1976d2;padding:16px 16px 8px 16px;border-bottom:1px solid #e0e0e0;position:sticky;top:0;z-index:2;background:#fff;flex-shrink:0;">Milestone Risks in Next 5wks</div>
  <div style="flex:1 1 auto;overflow-y:auto;padding:12px 16px 16px 16px;text-align:left;">''' + html_left.replace('Milestone Risks in Next 5wks','') + '''</div>
</div>
''', unsafe_allow_html=True)
                else:
                    st.markdown('''
<div style="border:2px solid #1976d2;border-radius:10px;padding:0;box-shadow:0 2px 8px rgba(25,118,210,0.08);background:#fff;height:180px;display:flex;flex-direction:column;">
  <div style="font-size:18px;font-weight:bold;color:#1976d2;padding:16px 16px 8px 16px;border-bottom:1px solid #e0e0e0;position:sticky;top:0;z-index:2;background:#fff;flex-shrink:0;">Milestone Risks in Next 5wks</div>
  <div style="flex:1 1 auto;overflow-y:auto;padding:12px 16px 16px 16px;text-align:left;">No milestone with potential risks in next 5wks</div>
</div>
''', unsafe_allow_html=True)
            with col_right:
                html_right = render_risk_results(results_later, 'Milestone Risks Beyond Next 5wks') if results_later else ''
                if html_right:
                    # 固定卡片高度为180px，标题始终可见，内容区overflow-y: auto
                    st.markdown('''
<div style="border:2px solid #1976d2;border-radius:10px;padding:0;box-shadow:0 2px 8px rgba(25,118,210,0.08);background:#fff;height:180px;display:flex;flex-direction:column;">
  <div style="font-size:18px;font-weight:bold;color:#1976d2;padding:16px 16px 8px 16px;border-bottom:1px solid #e0e0e0;position:sticky;top:0;z-index:2;background:#fff;flex-shrink:0;">Milestone Risks Beyond Next 5wks</div>
  <div style="flex:1 1 auto;overflow-y:auto;padding:12px 16px 16px 16px;">''' + html_right.replace('Milestone Risks Beyond Next 5wks','') + '''</div>
</div>
''', unsafe_allow_html=True)
                else:
                    st.markdown('''
<div style="border:2px solid #1976d2;border-radius:10px;padding:0;box-shadow:0 2px 8px rgba(25,118,210,0.08);background:#fff;height:180px;display:flex;flex-direction:column;">
  <div style="font-size:18px;font-weight:bold;color:#1976d2;padding:16px 16px 8px 16px;border-bottom:1px solid #e0e0e0;position:sticky;top:0;z-index:2;background:#fff;flex-shrink:0;">Milestone Risks Beyond Next 5wks</div>
  <div style="flex:1 1 auto;overflow-y:auto;padding:12px 16px 16px 16px;">No milestone with potential risks beyond next 5wks</div>
</div>
''', unsafe_allow_html=True)
        else:
            st.markdown('<div class="card-content">请上传包含 study_number, study_ctn_plan_date, study_ctn_actual_date 字段的CSV</div>', unsafe_allow_html=True)

# 增加上下间距
st.markdown('<div style="height: 32px;"></div>', unsafe_allow_html=True)

# === 原有5个卡片一行 ===
cols = st.columns(5)
for i, col in enumerate(cols):
    with col:
        if i == 0:
            with st.container():
                st.markdown('<div class="stCardTitle">Total Study</div>', unsafe_allow_html=True)
                if df is not None:
                    total_study = df['study_number'].nunique()
                    st.markdown(f'<div class="stCardNumber">{total_study}</div>', unsafe_allow_html=True)
                    # 计算每个study_number的最新一条（去重）
                    study_df = df.drop_duplicates(subset=['study_number'], keep='first').copy()
                    now = pd.Timestamp.now()
                    next_3m = now + pd.DateOffset(months=3)
                    # 三种状态分组
                    obtained = study_df['study_ctn_actual_date'].notna()
                    planned_next_3m = (
                        study_df['study_ctn_actual_date'].isna() & (
                            (study_df['study_ctn_plan_date'].between(now, next_3m)) |
                            (study_df['study_ctn_plan_date'] < now)
                        )
                    )
                    after_3m = (
                        study_df['study_ctn_actual_date'].isna() & (
                            study_df['study_ctn_plan_date'].isna() |
                            (study_df['study_ctn_plan_date'] > next_3m)
                        )
                    )
                    obtained_count = obtained.sum()
                    planned_next_3m_count = planned_next_3m.sum()
                    after_3m_count = after_3m.sum()
                    st.markdown('<div class="stCardSubtitle">CTN Status</div>', unsafe_allow_html=True)
                    fig = go.Figure(
                        go.Bar(
                            x=['CTN Obtained', 'Planned in next 3M', 'After 3M'],
                            y=[obtained_count, planned_next_3m_count, after_3m_count],
                            marker_color=['#1976d2', '#ffb300', '#bdbdbd'],
                            text=[obtained_count, planned_next_3m_count, after_3m_count],
                            textposition='auto',
                            textfont=dict(size=13, color='white', family='Microsoft YaHei, Open Sans, verdana, arial, sans-serif'),
                            insidetextfont=dict(size=13, color='white', family='Microsoft YaHei, Open Sans, verdana, arial, sans-serif'),
                        )
                    )
                    fig.update_traces(textfont=dict(size=13, color='white', family='Microsoft YaHei, Open Sans, verdana, arial, sans-serif'), insidetextfont=dict(size=13, color='white', family='Microsoft YaHei, Open Sans, verdana, arial, sans-serif'))
                    fig.update_layout(
                        height=300,
                        width=450,
                        margin=dict(l=0, r=0, t=20, b=0),
                        showlegend=False,
                        yaxis=dict(
                            title='Study Count',
                            dtick=1,
                            showticklabels=False,
                            tickfont=dict(size=16, color='#6D4C41', family='Microsoft YaHei, Open Sans, verdana, arial, sans-serif')
                        ),
                        xaxis=dict(
                            tickfont=dict(size=15, color='black', family='Microsoft YaHei, Open Sans, verdana, arial, sans-serif')
                        ),
                        font=dict(family="Microsoft YaHei, Open Sans, verdana, arial, sans-serif")
                    )
                    st.plotly_chart(fig, use_container_width=False, key='card_1_main')
                else:
                    st.markdown('<div class="card-content">请上传包含 study_number, study_ctn_plan_date, study_ctn_actual_date 字段的CSV</div>', unsafe_allow_html=True)
        elif i == 1:
            with st.container():
                st.markdown('<div class="stCardTitle">CTN-FSA</div>', unsafe_allow_html=True)
                st.markdown('<div style="text-align:center;color:#222;font-size:13px;margin-bottom:4px;">Target: 9 Weeks</div>', unsafe_allow_html=True)
                if df is not None:
                    # 修改：包含所有有CTN日期的study，而不仅仅是有FSA计划或实际日期的study
                    study_df = df.drop_duplicates(subset=['study_number'], keep='first').copy()
                    # 需要的字段
                    for colname in ['study_ctn_actual_date', 'study_ctn_plan_date', 'study_fsa_actual_date', 'study_fsa_plan_date']:
                        if colname not in study_df.columns:
                            study_df[colname] = pd.NaT
                    # 计算CTN日期（优先actual）
                    study_df['ctn_date'] = study_df['study_ctn_actual_date']
                    study_df.loc[study_df['ctn_date'].isna(), 'ctn_date'] = study_df['study_ctn_plan_date']
                    # 只保留有CTN日期的study（这样能包含所有需要统计的study，包括那些没有FSA日期但已经超过目标日期的）
                    study_df = study_df[study_df['ctn_date'].notna()].copy()
                    now = pd.Timestamp.now()
                    n_total = study_df['study_number'].nunique()
                    meet = []
                    miss = []
                    in_progress_miss = []
                    in_progress_pred_meet = []
                    in_progress_pred_miss = []
                    for idx, row in study_df.iterrows():
                        ctn = pd.to_datetime(row['ctn_date'], errors='coerce')
                        fsa_actual = pd.to_datetime(row['study_fsa_actual_date'], errors='coerce')
                        fsa_plan = pd.to_datetime(row['study_fsa_plan_date'], errors='coerce')
                        if pd.isna(ctn):
                            # 没有CTN，只能预测
                            if pd.notna(fsa_plan):
                                delta = (fsa_plan - now).days
                                if delta <= 63:
                                    in_progress_pred_meet.append(row['study_number'])
                                else:
                                    in_progress_pred_miss.append(row['study_number'])
                            else:
                                continue
                        elif pd.notna(fsa_actual) and pd.notna(ctn):
                            delta = (fsa_actual - ctn).days
                            if delta <= 63:
                                meet.append(row['study_number'])
                            else:
                                miss.append(row['study_number'])
                        else:
                            # 没有FSA actual
                            if pd.notna(ctn) and (now - ctn).days > 63:
                                in_progress_miss.append(row['study_number'])
                            else:
                                if pd.notna(fsa_plan) and pd.notna(ctn):
                                    delta = (fsa_plan - ctn).days
                                    if delta <= 63:
                                        in_progress_pred_meet.append(row['study_number'])
                                    else:
                                        in_progress_pred_miss.append(row['study_number'])
                                else:
                                    continue
                    # 统计数量
                    n_meet = len(set(meet))
                    n_miss = len(set(miss))
                    n_in_progress_miss = len(set(in_progress_miss))
                    n_in_progress_pred_meet = len(set(in_progress_pred_meet))
                    n_in_progress_pred_miss = len(set(in_progress_pred_miss))
                    n_sum = n_meet + n_miss + n_in_progress_miss + n_in_progress_pred_meet + n_in_progress_pred_miss
                    # 百分比
                    percent_now = n_meet / n_total * 100 if n_total else 0
                    percent_pred = (n_meet + n_in_progress_pred_meet) / n_total * 100 if n_total else 0
                    # 百分比数值（居中）
                    st.markdown(
                        f'<div class="stCardNumber" style="text-align:center;">{percent_now:.0f}% <span style="font-size:16px;color:#888;">({percent_pred:.0f}%)</span></div>',
                        unsafe_allow_html=True
                    )

                    # 饼图展示各状态占比
                    # 统计各状态的study_number列表
                    meet_set = set(meet)
                    miss_set = set(miss)
                    in_progress_miss_set = set(in_progress_miss)
                    in_progress_pred_meet_set = set(in_progress_pred_meet)
                    in_progress_pred_miss_set = set(in_progress_pred_miss)

                    labels = [
                        f"Meet ({', '.join(meet_set)})" if meet_set else "Meet",
                        f"Miss ({', '.join(miss_set)})" if miss_set else "Miss",
                        f"In progress-miss ({', '.join(in_progress_miss_set)})" if in_progress_miss_set else "In progress-miss",
                        f"In progress-prediction meet ({', '.join(in_progress_pred_meet_set)})" if in_progress_pred_meet_set else "In progress-prediction meet",
                        f"In progress-prediction miss ({', '.join(in_progress_pred_miss_set)})" if in_progress_pred_miss_set else "In progress-prediction miss"
                    ]
                    values = [
                        len(meet_set),
                        len(miss_set),
                        len(in_progress_miss_set),
                        len(in_progress_pred_meet_set),
                        len(in_progress_pred_miss_set)
                    ]
                    colors = ['#43a047', '#e53935', '#ffb300', '#1976d2', '#bdbdbd']

                    # 饼图
                    fig2 = go.Figure(go.Pie(
                        labels=labels,
                        values=values,
                        marker_colors=colors,
                        textinfo='percent',
                        hole=0.4,
                        textfont=dict(size=13, color='white', family='Microsoft YaHei, Open Sans, verdana, arial, sans-serif'),
                        insidetextfont=dict(size=13, color='white', family='Microsoft YaHei, Open Sans, verdana, arial, sans-serif'),
                        insidetextfont_weight='bold'
                    ))
                    fig2.update_traces(textfont=dict(size=13, color='white', family='Microsoft YaHei, Open Sans, verdana, arial, sans-serif'), insidetextfont=dict(size=13, color='white', family='Microsoft YaHei, Open Sans, verdana, arial, sans-serif'))
                    fig2.update_layout(
                        height=210,
                        width=210,
                        margin=dict(l=0, r=0, t=20, b=0),
                        showlegend=False,
                        font=dict(size=18, color='#6D4C41')
                    )
                    # 三列布局，饼图在中间列
                    col_left, col_center, col_right = st.columns([1, 2, 1])
                    with col_left:
                        st.write("")  # 占位
                    with col_center:
                        st.plotly_chart(fig2, use_container_width=False, key='card_2_pie')
                        # 颜色注解一行一个，项目号多时自动换行
                        legend_html = '<div style="width:280px;display:block;margin:0 auto;">'
                        for color, label in zip(colors, labels):
                            legend_html += (
                                f'<div style="display:flex;align-items:center;margin:2px 0;max-width:280px;">'
                                f'<span style="display:inline-block;width:14px;height:14px;background:{color};border-radius:3px;margin-right:6px;"></span>'
                                f'<span style="font-size:14px;color:#222;font-weight:bold;word-break:break-all;">{label}</span>'
                                f'</div>'
                            )
                        legend_html += '</div>'
                        st.markdown(legend_html, unsafe_allow_html=True)
                    with col_right:
                        st.write("")  # 占位
                else:
                    st.markdown('<div class="card-content">请上传包含 study_number, study_ctn_plan_date, study_ctn_actual_date, study_fsa_actual_date, study_fsa_plan_date 字段的CSV</div>', unsafe_allow_html=True)
        elif i == 2:
            with st.container():
                st.markdown('<div class="stCardTitle">CTN-FPS</div>', unsafe_allow_html=True)
                st.markdown('<div style="text-align:center;color:#222;font-size:13px;margin-bottom:4px;">Target: 12 Weeks</div>', unsafe_allow_html=True)
                if df is not None:
                    # 修改：包含所有有CTN日期的study，而不仅仅是有FPS计划或实际日期的study
                    study_df = df.drop_duplicates(subset=['study_number'], keep='first').copy()
                    # 需要的字段
                    for colname in ['study_ctn_actual_date', 'study_ctn_plan_date', 'study_fps_actual_date', 'study_fps_plan_date']:
                        if colname not in study_df.columns:
                            study_df[colname] = pd.NaT
                    # 计算CTN日期（优先actual）
                    study_df['ctn_date'] = study_df['study_ctn_actual_date']
                    study_df.loc[study_df['ctn_date'].isna(), 'ctn_date'] = study_df['study_ctn_plan_date']
                    # 只保留有CTN日期的study（这样能包含所有需要统计的study，包括那些没有FPS日期但已经超过目标日期的）
                    study_df = study_df[study_df['ctn_date'].notna()].copy()
                    now = pd.Timestamp.now()
                    n_total = study_df['study_number'].nunique()
                    meet = []
                    miss = []
                    in_progress_miss = []
                    in_progress_pred_meet = []
                    in_progress_pred_miss = []
                    for idx, row in study_df.iterrows():
                        ctn = pd.to_datetime(row['ctn_date'], errors='coerce')
                        fps_actual = pd.to_datetime(row['study_fps_actual_date'], errors='coerce')
                        fps_plan = pd.to_datetime(row['study_fps_plan_date'], errors='coerce')
                        if pd.isna(ctn):
                            # 没有CTN，只能预测
                            if pd.notna(fps_plan):
                                delta = (fps_plan - now).days
                                if delta <= 84:
                                    in_progress_pred_meet.append(row['study_number'])
                                else:
                                    in_progress_pred_miss.append(row['study_number'])
                            else:
                                continue
                        elif pd.notna(fps_actual) and pd.notna(ctn):
                            delta = (fps_actual - ctn).days
                            if delta <= 84:
                                meet.append(row['study_number'])
                            else:
                                miss.append(row['study_number'])
                        else:
                            # 没有FPS actual
                            if pd.notna(ctn) and (now - ctn).days > 12*7:
                                in_progress_miss.append(row['study_number'])
                            else:
                                if pd.notna(fps_plan) and pd.notna(ctn):
                                    delta = (fps_plan - ctn).days
                                    if delta <= 84:
                                        in_progress_pred_meet.append(row['study_number'])
                                    else:
                                        in_progress_pred_miss.append(row['study_number'])
                                else:
                                    continue
                    # 统计数量
                    meet_set = set(meet)
                    miss_set = set(miss)
                    in_progress_miss_set = set(in_progress_miss)
                    in_progress_pred_meet_set = set(in_progress_pred_meet)
                    in_progress_pred_miss_set = set(in_progress_pred_miss)
                    n_meet = len(meet_set)
                    n_miss = len(miss_set)
                    n_in_progress_miss = len(in_progress_miss_set)
                    n_in_progress_pred_meet = len(in_progress_pred_meet_set)
                    n_in_progress_pred_miss = len(in_progress_pred_miss_set)
                    n_sum = n_meet + n_miss + n_in_progress_miss + n_in_progress_pred_meet + n_in_progress_pred_miss
                    # 百分比
                    percent_now = n_meet / n_total * 100 if n_total else 0
                    percent_pred = (n_meet + n_in_progress_pred_meet) / n_total * 100 if n_total else 0
                    # 百分比数值（居中）
                    st.markdown(
                        f'<div class="stCardNumber" style="text-align:center;">{percent_now:.0f}% <span style="font-size:16px;color:#888;">({percent_pred:.0f}%)</span></div>',
                        unsafe_allow_html=True
                    )
                    # 饼图
                    labels = [
                        f"Meet ({', '.join(meet_set)})" if meet_set else "Meet",
                        f"Miss ({', '.join(miss_set)})" if miss_set else "Miss",
                        f"In progress-miss ({', '.join(in_progress_miss_set)})" if in_progress_miss_set else "In progress-miss",
                        f"In progress-prediction meet ({', '.join(in_progress_pred_meet_set)})" if in_progress_pred_meet_set else "In progress-prediction meet",
                        f"In progress-prediction miss ({', '.join(in_progress_pred_miss_set)})" if in_progress_pred_miss_set else "In progress-prediction miss"
                    ]
                    values = [
                        n_meet,
                        n_miss,
                        n_in_progress_miss,
                        n_in_progress_pred_meet,
                        n_in_progress_pred_miss
                    ]
                    colors = ['#43a047', '#e53935', '#ffb300', '#1976d2', '#bdbdbd']
                    fig3 = go.Figure(
                        go.Pie(
                            labels=labels,
                            values=values,
                            marker_colors=colors,
                            textinfo='percent',
                            hole=0.4,
                            textfont=dict(size=13, color='white', family='Microsoft YaHei, Open Sans, verdana, arial, sans-serif'),
                            insidetextfont=dict(size=13, color='white', family='Microsoft YaHei, Open Sans, verdana, arial, sans-serif'),
                            insidetextfont_weight='bold'
                        )
                    )
                    fig3.update_traces(textfont=dict(size=13, color='white', family='Microsoft YaHei, Open Sans, verdana, arial, sans-serif'), insidetextfont=dict(size=13, color='white', family='Microsoft YaHei, Open Sans, verdana, arial, sans-serif'))
                    fig3.update_layout(
                        height=210,
                        width=210,
                        margin=dict(l=0, r=0, t=20, b=0),
                        showlegend=False,
                        font=dict(size=18, color='#6D4C41')
                    )
                    # 三列布局，饼图在中间列
                    col_left, col_center, col_right = st.columns([1, 2, 1])
                    with col_left:
                        st.write("")  # 占位
                    with col_center:
                        st.plotly_chart(fig3, use_container_width=False, key='card_3_pie')
                        # 颜色注解一行一个，项目号多时自动换行
                        legend_html = '<div style="width:280px;display:block;margin:0 auto;">'
                        for color, label in zip(colors, labels):
                            legend_html += (
                                f'<div style="display:flex;align-items:center;margin:2px 0;max-width:280px;">'
                                f'<span style="display:inline-block;width:14px;height:14px;background:{color};border-radius:3px;margin-right:6px;"></span>'
                                f'<span style="font-size:14px;color:#222;font-weight:bold;word-break:break-all;">{label}</span>'
                                f'</div>'
                            )
                        legend_html += '</div>'
                        st.markdown(legend_html, unsafe_allow_html=True)
                    with col_right:
                        st.write("")  # 占位
                else:
                    st.markdown('<div class="card-content">请上传包含 study_number, study_ctn_plan_date, study_ctn_actual_date, study_fps_actual_date, study_fps_plan_date 字段的CSV</div>', unsafe_allow_html=True)
        elif i == 3:
            st.markdown('<div class="stCardTitle">CTN-25% Site Activation</div>', unsafe_allow_html=True)
            st.markdown('<div style="text-align:center;color:#222;font-size:13px;margin-bottom:4px;">Target: 13 Weeks</div>', unsafe_allow_html=True)
            if df is not None:
                # 需要的字段
                for colname in [
                    'study_number', 'site_no', 'study_ctn_actual_date', 'study_ctn_plan_date',
                    'site_sa_actual_date', 'site_sa_plan_date', 'ssus', 'site_status',
                    'ssus_assignment_date', 'study_fsa_actual_date'
                ]:
                    if colname not in df.columns:
                        df[colname] = pd.NA

                now = pd.Timestamp.now()
                days_limit = 91

                # Study列表
                study_list = df['study_number'].dropna().unique()
                meet, miss, in_progress_miss, in_progress_pred_meet, in_progress_pred_miss = [], [], [], [], []

                for study in study_list:
                    study_df = df[df['study_number'] == study].copy()
                    # Site Scope筛选
                    site_scope = study_df[
                        (study_df['ssus'].notna()) |
                        ((study_df['ssus'].isna()) & (study_df['site_status'] == 'Initiating')) |
                        (
                            (study_df['ssus_assignment_date'].notna()) &
                            (study_df['study_fsa_actual_date'].notna()) &
                            (pd.to_datetime(study_df['ssus_assignment_date'], errors='coerce') <= pd.to_datetime(study_df['study_fsa_actual_date'], errors='coerce'))
                        )
                    ].copy()
                    if site_scope.empty:
                        continue

                    # 25% site数
                    n_sites = len(site_scope)
                    n_25 = max(1, int(np.ceil(n_sites * 0.25)))

                    # 计算CTN日期（优先actual）
                    ctn_actual = pd.to_datetime(study_df['study_ctn_actual_date'].iloc[0], errors='coerce')
                    ctn_plan = pd.to_datetime(study_df['study_ctn_plan_date'].iloc[0], errors='coerce')
                    ctn_date = ctn_actual if pd.notna(ctn_actual) else ctn_plan

                    # 25% site的激活日期（优先actual）
                    site_scope['sa_date'] = pd.to_datetime(site_scope['site_sa_actual_date'], errors='coerce')
                    site_scope.loc[site_scope['sa_date'].isna(), 'sa_date'] = pd.to_datetime(site_scope['site_sa_plan_date'], errors='coerce')

                    # 25% site的 site_sa_actual_date
                    top_sites = site_scope.sort_values('sa_date').head(n_25)
                    top_sites_actual = pd.to_datetime(top_sites['site_sa_actual_date'], errors='coerce')
                    top_sites_plan = pd.to_datetime(top_sites['site_sa_plan_date'], errors='coerce')

                    # 新增：如果top_sites的actual和plan都全为NA，则跳过该study
                    if top_sites_actual.isna().all() and top_sites_plan.isna().all():
                        continue

                    # Meet/Miss 只有当25% site的 site_sa_actual_date都非空
                    if top_sites_actual.notna().all() and pd.notna(ctn_date):
                        delta = (top_sites_actual - ctn_date).dt.days.max()
                        if delta <= days_limit:
                            meet.append(study)
                        else:
                            miss.append(study)
                    else:
                        # 其余逻辑保持不变，进入 in progress/prediction 分组
                        if pd.notna(ctn_date) and (now - ctn_date).days > days_limit:
                            in_progress_miss.append(study)
                        else:
                            # 预测
                            top_sites['sa_plan'] = pd.to_datetime(top_sites['site_sa_plan_date'], errors='coerce')
                            ctn_for_pred = ctn_date if pd.notna(ctn_date) else ctn_plan
                            if pd.notna(ctn_for_pred):
                                sa_plan_min = top_sites['sa_plan'].min()
                                if pd.notna(sa_plan_min):
                                    delta = (sa_plan_min - ctn_for_pred).days
                                    if delta <= days_limit:
                                        in_progress_pred_meet.append(study)
                                    else:
                                        in_progress_pred_miss.append(study)
                                else:
                                    in_progress_pred_miss.append(study)
                            else:
                                in_progress_pred_miss.append(study)

                # 统计数量
                meet_set = set(meet)
                miss_set = set(miss)
                in_progress_miss_set = set(in_progress_miss)
                in_progress_pred_meet_set = set(in_progress_pred_meet)
                in_progress_pred_miss_set = set(in_progress_pred_miss)
                n_total = len(study_list)
                n_meet = len(meet_set)
                n_miss = len(miss_set)
                n_in_progress_miss = len(in_progress_miss_set)
                n_in_progress_pred_meet = len(in_progress_pred_meet_set)
                n_in_progress_pred_miss = len(in_progress_pred_miss_set)
                # 百分比
                percent_now = n_meet / n_total * 100 if n_total else 0
                percent_pred = (n_meet + n_in_progress_pred_meet) / n_total * 100 if n_total else 0
                # 百分比数值（居中）
                st.markdown(
                    f'<div class="stCardNumber" style="text-align:center;">{percent_now:.0f}% <span style="font-size:16px;color:#888;">({percent_pred:.0f}%)</span></div>',
                    unsafe_allow_html=True
                )
                # 饼图
                labels = [
                    f"Meet ({', '.join(meet_set)})" if meet_set else "Meet",
                    f"Miss ({', '.join(miss_set)})" if miss_set else "Miss",
                    f"In progress-miss ({', '.join(in_progress_miss_set)})" if in_progress_miss_set else "In progress-miss",
                    f"In progress-prediction meet ({', '.join(in_progress_pred_meet_set)})" if in_progress_pred_meet_set else "In progress-prediction meet",
                    f"In progress-prediction miss ({', '.join(in_progress_pred_miss_set)})" if in_progress_pred_miss_set else "In progress-prediction miss"
                ]
                values = [
                    n_meet,
                    n_miss,
                    n_in_progress_miss,
                    n_in_progress_pred_meet,
                    n_in_progress_pred_miss
                ]
                colors = ['#43a047', '#e53935', '#ffb300', '#1976d2', '#bdbdbd']
                fig4 = go.Figure(go.Pie(
                    labels=labels,
                    values=values,
                    marker_colors=colors,
                    textinfo='percent',
                    hole=0.4,
                    textfont=dict(size=13, color='white', family='Microsoft YaHei, Open Sans, verdana, arial, sans-serif'),
                    insidetextfont=dict(size=13, color='white', family='Microsoft YaHei, Open Sans, verdana, arial, sans-serif'),
                    insidetextfont_weight='bold'
                ))
                fig4.update_traces(textfont=dict(size=13, color='white', family='Microsoft YaHei, Open Sans, verdana, arial, sans-serif'), insidetextfont=dict(size=13, color='white', family='Microsoft YaHei, Open Sans, verdana, arial, sans-serif'))
                fig4.update_layout(
                    height=210,
                    width=210,
                    margin=dict(l=0, r=0, t=20, b=0),
                    showlegend=False,
                    font=dict(size=18, color='#6D4C41')
                )
                # 三列布局，饼图在中间列
                col_left, col_center, col_right = st.columns([1, 2, 1])
                with col_left:
                    st.write("")  # 占位
                with col_center:
                    st.plotly_chart(fig4, use_container_width=False, key='card_4_pie')
                    # 颜色注解一行一个，项目号多时自动换行
                    legend_html = '<div style="width:280px;display:block;margin:0 auto;">'
                    for color, label in zip(colors, labels):
                        legend_html += (
                            f'<div style="display:flex;align-items:center;margin:2px 0;max-width:280px;">'
                            f'<span style="display:inline-block;width:14px;height:14px;background:{color};border-radius:3px;margin-right:6px;"></span>'
                            f'<span style="font-size:14px;color:#222;font-weight:bold;word-break:break-all;">{label}</span>'
                            f'</div>'
                        )
                    legend_html += '</div>'
                    st.markdown(legend_html, unsafe_allow_html=True)
                with col_right:
                    st.write("")  # 占位
            else:
                st.markdown('<div class="card-content">请上传包含 study_number, site_no, study_ctn_actual_date, study_ctn_plan_date, site_sa_actual_date, site_sa_plan_date, ssus, site_status, ssus_assignment_date, study_fsa_actual_date 字段的CSV</div>', unsafe_allow_html=True)
        elif i == 4:
            st.markdown('<div class="stCardTitle">CTN-75% Site Activation</div>', unsafe_allow_html=True)
            st.markdown('<div style="text-align:center;color:#222;font-size:13px;margin-bottom:4px;">Target: 19 Weeks</div>', unsafe_allow_html=True)
            # 删除 'Mdn duration of each process' 这一行
            if df is not None:
                # 需要的字段
                for colname in [
                    'study_number', 'site_no', 'study_ctn_actual_date', 'study_ctn_plan_date',
                    'site_sa_actual_date', 'site_sa_plan_date', 'ssus', 'site_status',
                    'ssus_assignment_date', 'study_fsa_actual_date'
                ]:
                    if colname not in df.columns:
                        df[colname] = pd.NA
                now = pd.Timestamp.now()
                days_limit = 133
                # Study列表
                study_list = df['study_number'].dropna().unique()
                meet, miss, in_progress_miss, in_progress_pred_meet, in_progress_pred_miss = [], [], [], [], []
                for study in study_list:
                    study_df = df[df['study_number'] == study].copy()
                    # Site Scope筛选
                    site_scope = study_df[
                        (study_df['ssus'].notna()) |
                        ((study_df['ssus'].isna()) & (study_df['site_status'] == 'Initiating')) |
                        (
                            (study_df['ssus_assignment_date'].notna()) &
                            (study_df['study_fsa_actual_date'].notna()) &
                            (pd.to_datetime(study_df['ssus_assignment_date'], errors='coerce') <= pd.to_datetime(study_df['study_fsa_actual_date'], errors='coerce'))
                        )
                    ].copy()
                    if site_scope.empty:
                        continue
                    # 75% site数
                    n_sites = len(site_scope)
                    n_75 = max(1, int(np.ceil(n_sites * 0.75)))
                    # 计算CTN日期（优先actual）
                    ctn_actual = pd.to_datetime(study_df['study_ctn_actual_date'].iloc[0], errors='coerce')
                    ctn_plan = pd.to_datetime(study_df['study_ctn_plan_date'].iloc[0], errors='coerce')
                    ctn_date = ctn_actual if pd.notna(ctn_actual) else ctn_plan
                    # 75% site的激活日期（优先actual）
                    site_scope['sa_date'] = pd.to_datetime(site_scope['site_sa_actual_date'], errors='coerce')
                    site_scope.loc[site_scope['sa_date'].isna(), 'sa_date'] = pd.to_datetime(site_scope['site_sa_plan_date'], errors='coerce')
                    # 75% site的 site_sa_actual_date
                    top_sites = site_scope.sort_values('sa_date').head(n_75)
                    top_sites_actual = pd.to_datetime(top_sites['site_sa_actual_date'], errors='coerce')
                    top_sites_plan = pd.to_datetime(top_sites['site_sa_plan_date'], errors='coerce')

                    # 修改：按照正确的75% SA逻辑，与Study Details表格保持一致
                    # 1. 检查是否有足够数量的actual site activation date（第75分位的site有actual日期）
                    if top_sites_actual.notna().all() and pd.notna(ctn_date):
                        # 取第75分位那家site的actual的activation日期
                        sa_date = top_sites_actual.max()
                        delta = (sa_date - ctn_date).days
                        if delta <= days_limit:
                            meet.append(study)
                        else:
                            miss.append(study)
                    # 2. 检查是否有足够数量的plan site activation date（第75分位的site有plan日期）
                    elif top_sites['sa_date'].notna().all() and pd.notna(ctn_date):
                        # 取第75分位那家site的activation日期（优先actual，没有actual的用plan）
                        sa_date = top_sites['sa_date'].max()
                        delta = (sa_date - ctn_date).days
                        if delta <= days_limit:
                            in_progress_pred_meet.append(study)
                        else:
                            in_progress_pred_miss.append(study)
                    # 3. 当数据缺失时，不纳入统计
                    else:
                        continue
                # 统计数量
                meet_set = set(meet)
                miss_set = set(miss)
                in_progress_miss_set = set(in_progress_miss)
                in_progress_pred_meet_set = set(in_progress_pred_meet)
                in_progress_pred_miss_set = set(in_progress_pred_miss)
                n_total = len(study_list)
                n_meet = len(meet_set)
                n_miss = len(miss_set)
                n_in_progress_miss = len(in_progress_miss_set)
                n_in_progress_pred_meet = len(in_progress_pred_meet_set)
                n_in_progress_pred_miss = len(in_progress_pred_miss_set)
                # 百分比
                percent_now = n_meet / n_total * 100 if n_total else 0
                percent_pred = (n_meet + n_in_progress_pred_meet) / n_total * 100 if n_total else 0
                # 百分比数值（居中）
                st.markdown(
                    f'<div class="stCardNumber" style="text-align:center;">{percent_now:.0f}% <span style="font-size:16px;color:#888;">({percent_pred:.0f}%)</span></div>',
                    unsafe_allow_html=True
                )
                # 饼图
                labels = [
                    f"Meet ({', '.join(meet_set)})" if meet_set else "Meet",
                    f"Miss ({', '.join(miss_set)})" if miss_set else "Miss",
                    f"In progress-miss ({', '.join(in_progress_miss_set)})" if in_progress_miss_set else "In progress-miss",
                    f"In progress-prediction meet ({', '.join(in_progress_pred_meet_set)})" if in_progress_pred_meet_set else "In progress-prediction meet",
                    f"In progress-prediction miss ({', '.join(in_progress_pred_miss_set)})" if in_progress_pred_miss_set else "In progress-prediction miss"
                ]
                values = [
                    n_meet,
                    n_miss,
                    n_in_progress_miss,
                    n_in_progress_pred_meet,
                    n_in_progress_pred_miss
                ]
                colors = ['#43a047', '#e53935', '#ffb300', '#1976d2', '#bdbdbd']
                fig5 = go.Figure(go.Pie(
                    labels=labels,
                    values=values,
                    marker_colors=colors,
                    textinfo='percent',
                    hole=0.4,
                    textfont=dict(size=13, color='white', family='Microsoft YaHei, Open Sans, verdana, arial, sans-serif'),
                    insidetextfont=dict(size=13, color='white', family='Microsoft YaHei, Open Sans, verdana, arial, sans-serif'),
                    insidetextfont_weight='bold'
                ))
                fig5.update_traces(textfont=dict(size=13, color='white', family='Microsoft YaHei, Open Sans, verdana, arial, sans-serif'), insidetextfont=dict(size=13, color='white', family='Microsoft YaHei, Open Sans, verdana, arial, sans-serif'))
                fig5.update_layout(
                    height=210,
                    width=210,
                    margin=dict(l=0, r=0, t=20, b=0),
                    showlegend=False,
                    font=dict(size=18, color='#6D4C41')
                )
                # 三列布局，饼图在中间列
                col_left, col_center, col_right = st.columns([1, 2, 1])
                with col_left:
                    st.write("")  # 占位
                with col_center:
                    st.plotly_chart(fig5, use_container_width=False, key=f'card_5_pie_{int(time.time()*1000)}')
                    # 颜色注解一行一个，项目号多时自动换行
                    legend_html = '<div style="width:280px;display:block;margin:0 auto;">'
                    for color, label in zip(colors, labels):
                        legend_html += (
                            f'<div style="display:flex;align-items:center;margin:2px 0;max-width:280px;">'
                            f'<span style="display:inline-block;width:14px;height:14px;background:{color};border-radius:3px;margin-right:6px;"></span>'
                            f'<span style="font-size:14px;color:#222;font-weight:bold;word-break:break-all;">{label}</span>'
                            f'</div>'
                        )
                    legend_html += '</div>'
                    st.markdown(legend_html, unsafe_allow_html=True)
                with col_right:
                    st.write("")  # 占位
            else:
                st.markdown('<div class="card-content">请上传包含 study_number, site_no, study_ctn_actual_date, study_ctn_plan_date, site_sa_actual_date, site_sa_plan_date, ssus, site_status, ssus_assignment_date, study_fsa_actual_date 字段的CSV</div>', unsafe_allow_html=True)
        else:
            with st.container():
                st.markdown(f"""
                <div class="stCardTitle">卡片 {i+1}</div>
                <div class="card-content">
                    内容区域 {i+1}
                </div>
                """, unsafe_allow_html=True)

def safe_date_str(date):
    if pd.isna(date) or str(date).strip().upper() in ["", "NAN", "NONE", "NULL", "[NULL]"]:
        return ""
    try:
        return pd.to_datetime(date).strftime('%Y-%m-%d')
    except Exception:
        return ""

# --- Study Details Table ---
st.markdown("---")
if df is not None:
    # 生成表格数据
    details = []
    study_list = df['study_number'].dropna().unique()
    for idx, study in enumerate(study_list, 1):
        study_df = df[df['study_number'] == study]
        # TA
        ta = study_df['clintrack_ta_desc'].iloc[0] if 'clintrack_ta_desc' in study_df.columns else ''
        # Study
        study_no = study
        # Sourcing
        sourcing = study_df['sourcing_strategy'].iloc[0] if 'sourcing_strategy' in study_df.columns else ''
        # CTN
        ctn_actual = study_df['study_ctn_actual_date'].iloc[0] if 'study_ctn_actual_date' in study_df.columns else pd.NaT
        ctn_plan = study_df['study_ctn_plan_date'].iloc[0] if 'study_ctn_plan_date' in study_df.columns else pd.NaT
        ctn_html = ''
        now = pd.Timestamp.now()
        def ctn_block(ctn_date, color, prefix):
            if pd.isna(ctn_date) or str(ctn_date).strip().upper() in ["", "NAN", "NONE", "NULL", "[NULL]"]:
                return ''
            try:
                ctn_dt = pd.to_datetime(ctn_date)
                weeks = (now - ctn_dt).days / 7
                weeks_str = f"+{weeks:.1f}" if weeks >= 0 else f"{weeks:.1f}"
                sign = '+' if weeks >= 0 else ''
                today_str = f"Today=CTN{sign}{weeks:.1f}w"
                return f"<div style='color:{color}'><span style='font-weight:bold'>{prefix}{ctn_dt.strftime('%Y-%m-%d')}</span><br><span style='font-size:14px;color:#6D4C41;font-weight:bold'>{today_str}</span></div>"
            except Exception:
                return ''
        if pd.notna(ctn_actual):
            ctn_html = ctn_block(ctn_actual, '#222', 'A:')
        elif pd.notna(ctn_plan):
            ctn_html = ctn_block(ctn_plan, '#1976d2', 'P:')
        else:
            ctn_html = ''
        # --- 辅助函数 ---
        def week_diff_str(date, ctn, threshold=None, reverse=False):
            if pd.isna(date) or pd.isna(ctn):
                return '', '#222'
            try:
                d1 = pd.to_datetime(date)
                d2 = pd.to_datetime(ctn)
                weeks = (d1 - d2).days / 7
                weeks_str = f"{weeks:.1f}w"
                # 判断是否超期
                color = '#222'
                if threshold is not None:
                    if reverse:
                        if weeks > threshold:
                            color = 'red'
                    else:
                        if weeks > threshold:
                            color = 'red'
                return weeks_str, color
            except Exception:
                return '', '#222'

        # 获取CTN基准日期
        ctn_base = None
        if pd.notna(ctn_actual):
            ctn_base = pd.to_datetime(ctn_actual)
        elif pd.notna(ctn_plan):
            ctn_base = pd.to_datetime(ctn_plan)
        # 移除所有调试输出
        # （删除所有st.write([CTN调试]...)、st.write([调试]...)等相关行）

        # 状态灯函数
        def status_light(color):
            return f"<span style='display:inline-block;width:14px;height:14px;border-radius:50%;background:{color};margin-right:2px;vertical-align:middle;'></span>"
        # 灯颜色定义
        COLOR_GREEN = '#43a047'
        COLOR_YELLOW = '#ffb300'
        COLOR_RED = '#e53935'
        # 灯逻辑判断函数
        def get_status_color(actual, plan, target, now):
            if pd.notna(actual):
                if target is not None and actual > target:
                    return COLOR_RED  # actual超期
                else:
                    return COLOR_GREEN  # actual未超期
            else:
                if target is not None and now > target:
                    return COLOR_RED  # 没有actual且已超期
                elif pd.notna(plan) and plan > target:
                    return COLOR_YELLOW  # plan大于目标日期且actual为空，黄灯
                else:
                    return ''  # 其他情况无灯
        # Leading EC Approval
        ec_approval = ''
        if 'leading_site_or_not' in study_df.columns:
            lead_rows = study_df[study_df['leading_site_or_not'].astype(str).str.upper() == 'YES']
            ec_actual = lead_rows['ec_approval_actual_date'].iloc[0] if 'ec_approval_actual_date' in lead_rows.columns and not lead_rows.empty else pd.NaT
            ec_plan = lead_rows['ec_approval_plan_date'].iloc[0] if 'ec_approval_plan_date' in lead_rows.columns and not lead_rows.empty else pd.NaT
            ec_target = ctn_base  # threshold=0, target=ctn_base
            color = get_status_color(ec_actual, ec_plan, ec_target, now)
            if pd.notna(ec_actual):
                weeks_str, _ = week_diff_str(ec_actual, ctn_base, threshold=0, reverse=False)
                date_color = '#222'
                weeks_color = 'red' if color == COLOR_RED else '#888'
                ec_approval = status_light(color) + f"<span style='color:{date_color};font-weight:bold'>A:{safe_date_str(ec_actual)} (<span style='color:{weeks_color}'>{weeks_str}</span>)</span>"
            elif pd.notna(ec_plan):
                weeks_str, _ = week_diff_str(ec_plan, ctn_base, threshold=0, reverse=False)
                date_color = 'red' if ec_plan < now else '#1976d2'
                weeks_color = 'red' if color == COLOR_RED else '#888'
                ec_approval = status_light(color) + f"<span style='color:{date_color};font-weight:bold'>P:{safe_date_str(ec_plan)} (<span style='color:{weeks_color}'>{weeks_str}</span>)</span>"
            else:
                ec_approval = status_light(color)
        # Leading Contract
        contract = ''
        if 'leading_site_or_not' in study_df.columns:
            lead_rows = study_df[study_df['leading_site_or_not'].astype(str).str.upper() == 'YES']
            contract_actual = lead_rows['contract_signoff_actual_date'].iloc[0] if 'contract_signoff_actual_date' in lead_rows.columns and not lead_rows.empty else pd.NaT
            contract_plan = lead_rows['contract_signoff_plan_date'].iloc[0] if 'contract_signoff_plan_date' in lead_rows.columns and not lead_rows.empty else pd.NaT
            contract_target = ctn_base
            color = get_status_color(contract_actual, contract_plan, contract_target, now)
            if pd.notna(contract_actual):
                weeks_str, _ = week_diff_str(contract_actual, ctn_base, threshold=0, reverse=False)
                date_color = '#222'
                weeks_color = 'red' if color == COLOR_RED else '#888'
                contract = status_light(color) + f"<span style='color:{date_color};font-weight:bold'>A:{safe_date_str(contract_actual)} (<span style='color:{weeks_color}'>{weeks_str}</span>)</span>"
            elif pd.notna(contract_plan):
                weeks_str, _ = week_diff_str(contract_plan, ctn_base, threshold=0, reverse=False)
                date_color = 'red' if contract_plan < now else '#1976d2'
                weeks_color = 'red' if color == COLOR_RED else '#888'
                contract = status_light(color) + f"<span style='color:{date_color};font-weight:bold'>P:{safe_date_str(contract_plan)} (<span style='color:{weeks_color}'>{weeks_str}</span>)</span>"
            else:
                contract = status_light(color)
        # Country Package
        cp_actual = study_df['country_package_ready_actual_date'].dropna().sort_values().iloc[0] if 'country_package_ready_actual_date' in study_df.columns and study_df['country_package_ready_actual_date'].notna().any() else pd.NaT
        cp_plan = study_df['country_package_ready_plan_date'].dropna().sort_values().iloc[0] if 'country_package_ready_plan_date' in study_df.columns and study_df['country_package_ready_plan_date'].notna().any() else pd.NaT
        cp_target = ctn_base + pd.Timedelta(weeks=-12) if pd.notna(ctn_base) else None
        color = get_status_color(cp_actual, cp_plan, cp_target, now)
        if pd.notna(cp_actual):
            weeks_str, _ = week_diff_str(cp_actual, ctn_base, threshold=-12, reverse=False)
            date_color = '#222'
            weeks_color = 'red' if color == COLOR_RED else '#888'
            cp_line1 = status_light(color) + f"<span style='color:{date_color};font-weight:bold'>A:{safe_date_str(cp_actual)} (<span style='color:{weeks_color}'>{weeks_str}</span>)</span>"
        elif pd.notna(cp_plan):
            weeks_str, _ = week_diff_str(cp_plan, ctn_base, threshold=-12, reverse=False)
            date_color = 'red' if cp_plan < now else '#1976d2'
            weeks_color = 'red' if color == COLOR_RED else '#888'
            cp_line1 = status_light(color) + f"<span style='color:{date_color};font-weight:bold'>P:{safe_date_str(cp_plan)} (<span style='color:{weeks_color}'>{weeks_str}</span>)</span>"
        else:
            cp_line1 = status_light(color)
        # 新增：Country Package target日期
        if cp_target:
            cp_line2 = f"<span style='color:#888;font-size:12px;'>Target: {cp_target.strftime('%Y-%m-%d')}</span>"
        else:
            cp_line2 = ""
        country_package = f"{cp_line1}<br>{cp_line2}"
        # IMP
        imp_actual = study_df['study_imp_ready_actual_date'].dropna().sort_values().iloc[0] if 'study_imp_ready_actual_date' in study_df.columns and study_df['study_imp_ready_actual_date'].notna().any() else pd.NaT
        imp_plan = study_df['study_imp_ready_plan_date'].dropna().sort_values().iloc[0] if 'study_imp_ready_plan_date' in study_df.columns and study_df['study_imp_ready_plan_date'].notna().any() else pd.NaT
        imp_target = ctn_base + pd.Timedelta(weeks=8.5) if pd.notna(ctn_base) else None
        color = get_status_color(imp_actual, imp_plan, imp_target, now)
        if pd.notna(imp_actual):
            weeks_str, _ = week_diff_str(imp_actual, ctn_base, threshold=8.5, reverse=False)
            date_color = '#222'
            weeks_color = 'red' if color == COLOR_RED else '#888'
            imp_line1 = status_light(color) + f"<span style='color:{date_color};font-weight:bold'>A:{safe_date_str(imp_actual)} (<span style='color:{weeks_color}'>{weeks_str}</span>)</span>"
        elif pd.notna(imp_plan):
            weeks_str, _ = week_diff_str(imp_plan, ctn_base, threshold=8.5, reverse=False)
            date_color = 'red' if imp_plan < now else '#1976d2'
            weeks_color = 'red' if color == COLOR_RED else '#888'
            imp_line1 = status_light(color) + f"<span style='color:{date_color};font-weight:bold'>P:{safe_date_str(imp_plan)} (<span style='color:{weeks_color}'>{weeks_str}</span>)</span>"
        else:
            imp_line1 = status_light(color)
        # 新增：IMP target日期
        if imp_target:
            imp_line2 = f"<span style='color:#888;font-size:12px;'>Target: {imp_target.strftime('%Y-%m-%d')}</span>"
        else:
            imp_line2 = ""
        imp_display = f"{imp_line1}<br>{imp_line2}"
        # Facility
        sfr_actual = study_df['study_sfr_actual_date'].dropna().sort_values().iloc[0] if 'study_sfr_actual_date' in study_df.columns and study_df['study_sfr_actual_date'].notna().any() else pd.NaT
        sfr_plan = study_df['study_sfr_plan_date'].dropna().sort_values().iloc[0] if 'study_sfr_plan_date' in study_df.columns and study_df['study_sfr_plan_date'].notna().any() else pd.NaT
        sfr_target = ctn_base + pd.Timedelta(weeks=8.5) if pd.notna(ctn_base) else None
        color = get_status_color(sfr_actual, sfr_plan, sfr_target, now)
        if pd.notna(sfr_actual):
            weeks_str, _ = week_diff_str(sfr_actual, ctn_base, threshold=8.5, reverse=False)
            date_color = '#222'
            weeks_color = 'red' if color == COLOR_RED else '#888'
            sfr_line1 = status_light(color) + f"<span style='color:{date_color};font-weight:bold'>A:{safe_date_str(sfr_actual)} (<span style='color:{weeks_color}'>{weeks_str}</span>)</span>"
        elif pd.notna(sfr_plan):
            weeks_str, _ = week_diff_str(sfr_plan, ctn_base, threshold=8.5, reverse=False)
            date_color = 'red' if sfr_plan < now else '#1976d2'
            weeks_color = 'red' if color == COLOR_RED else '#888'
            sfr_line1 = status_light(color) + f"<span style='color:{date_color};font-weight:bold'>P:{safe_date_str(sfr_plan)} (<span style='color:{weeks_color}'>{weeks_str}</span>)</span>"
        else:
            sfr_line1 = status_light(color)
        # 新增：Facility target日期
        if sfr_target:
            sfr_line2 = f"<span style='color:#888;font-size:12px;'>Target: {sfr_target.strftime('%Y-%m-%d')}</span>"
        else:
            sfr_line2 = ""
        sfr_display = f"{sfr_line1}<br>{sfr_line2}"
        # HGRAC
        hia_actual = study_df['study_hia_actual_date'].dropna().sort_values().iloc[0] if 'study_hia_actual_date' in study_df.columns and study_df['study_hia_actual_date'].notna().any() else pd.NaT
        hia_plan = study_df['study_hia_plan_date'].dropna().sort_values().iloc[0] if 'study_hia_plan_date' in study_df.columns and study_df['study_hia_plan_date'].notna().any() else pd.NaT
        hia_target = ctn_base + pd.Timedelta(weeks=8.5) if pd.notna(ctn_base) else None
        color = get_status_color(hia_actual, hia_plan, hia_target, now)
        if pd.notna(hia_actual):
            weeks_str, _ = week_diff_str(hia_actual, ctn_base, threshold=8.5, reverse=False)
            date_color = '#222'
            weeks_color = 'red' if color == COLOR_RED else '#888'
            hia_line1 = status_light(color) + f"<span style='color:{date_color};font-weight:bold'>A:{safe_date_str(hia_actual)} (<span style='color:{weeks_color}'>{weeks_str}</span>)</span>"
        elif pd.notna(hia_plan):
            weeks_str, _ = week_diff_str(hia_plan, ctn_base, threshold=8.5, reverse=False)
            date_color = 'red' if hia_plan < now else '#1976d2'
            weeks_color = 'red' if color == COLOR_RED else '#888'
            hia_line1 = status_light(color) + f"<span style='color:{date_color};font-weight:bold'>P:{safe_date_str(hia_plan)} (<span style='color:{weeks_color}'>{weeks_str}</span>)</span>"
        else:
            hia_line1 = status_light(color)
        # 新增：HGRAC target日期
        if hia_target:
            hia_line2 = f"<span style='color:#888;font-size:12px;'>Target: {hia_target.strftime('%Y-%m-%d')}</span>"
        else:
            hia_line2 = ""
        hia_display = f"{hia_line1}<br>{hia_line2}"
        # FSA
        fsa_actual = study_df['study_fsa_actual_date'].dropna().sort_values().iloc[0] if 'study_fsa_actual_date' in study_df.columns and study_df['study_fsa_actual_date'].notna().any() else pd.NaT
        fsa_plan = study_df['study_fsa_plan_date'].dropna().sort_values().iloc[0] if 'study_fsa_plan_date' in study_df.columns and study_df['study_fsa_plan_date'].notna().any() else pd.NaT
        fsa_target = ctn_base + pd.Timedelta(weeks=9) if pd.notna(ctn_base) else None
        color = get_status_color(fsa_actual, fsa_plan, fsa_target, now)
        # 第一行：plan/actual日期及与CTN的周数差
        if pd.notna(fsa_actual):
            weeks_str, _ = week_diff_str(fsa_actual, ctn_base, threshold=9, reverse=False)
            date_color = '#222'
            weeks_color = 'red' if color == COLOR_RED else '#888'
            fsa_line1 = status_light(color) + f"<span style='color:{date_color};font-weight:bold'>A:{safe_date_str(fsa_actual)} (<span style='color:{weeks_color}'>{weeks_str}</span>)</span>"
        elif pd.notna(fsa_plan):
            weeks_str, _ = week_diff_str(fsa_plan, ctn_base, threshold=9, reverse=False)
            date_color = 'red' if fsa_plan < now else '#1976d2'
            weeks_color = 'red' if color == COLOR_RED else '#888'
            fsa_line1 = status_light(color) + f"<span style='color:{date_color};font-weight:bold'>P:{safe_date_str(fsa_plan)} (<span style='color:{weeks_color}'>{weeks_str}</span>)</span>"
        else:
            fsa_line1 = status_light(color)
        # 第二行：target日期（CTN+9w）
        if fsa_target:
            fsa_line2 = f"<span style='color:#888;font-size:12px;'>Target: {fsa_target.strftime('%Y-%m-%d')}</span>"
        else:
            fsa_line2 = ""
        fsa_display = f"{fsa_line1}<br>{fsa_line2}"

        # FPS
        fps_actual = study_df['study_fps_actual_date'].dropna().sort_values().iloc[0] if 'study_fps_actual_date' in study_df.columns and study_df['study_fps_actual_date'].notna().any() else pd.NaT
        fps_plan = study_df['study_fps_plan_date'].dropna().sort_values().iloc[0] if 'study_fps_plan_date' in study_df.columns and study_df['study_fps_plan_date'].notna().any() else pd.NaT
        fps_target = ctn_base + pd.Timedelta(weeks=12) if pd.notna(ctn_base) else None
        color = get_status_color(fps_actual, fps_plan, fps_target, now)
        # 第一行：plan/actual日期及与CTN的周数差
        if pd.notna(fps_actual):
            weeks_str, _ = week_diff_str(fps_actual, ctn_base, threshold=21, reverse=False)
            date_color = '#222'
            weeks_color = 'red' if color == COLOR_RED else '#888'
            fps_line1 = status_light(color) + f"<span style='color:{date_color};font-weight:bold'>A:{safe_date_str(fps_actual)} (<span style='color:{weeks_color}'>{weeks_str}</span>)</span>"
        elif pd.notna(fps_plan):
            weeks_str, _ = week_diff_str(fps_plan, ctn_base, threshold=21, reverse=False)
            date_color = 'red' if fps_plan < now else '#1976d2'
            weeks_color = 'red' if color == COLOR_RED else '#888'
            fps_line1 = status_light(color) + f"<span style='color:{date_color};font-weight:bold'>P:{safe_date_str(fps_plan)} (<span style='color:{weeks_color}'>{weeks_str}</span>)</span>"
        else:
            fps_line1 = status_light(color)
        if fps_target:
            fps_line2 = f"<span style='color:#888;font-size:12px;'>Target: {fps_target.strftime('%Y-%m-%d')}</span>"
        else:
            fps_line2 = ""
        fps_display = f"{fps_line1}<br>{fps_line2}"

        # 25% SA
        sa_25_display = ''
        sa_75_display = ''
        if 'site_no' in study_df.columns:
            # site_scope筛选逻辑与饼图一致
            site_scope = study_df[
                (study_df['ssus'].notna()) |
                ((study_df['ssus'].isna()) & (study_df['site_status'] == 'Initiating')) |
                (
                    (study_df['ssus_assignment_date'].notna()) &
                    (study_df['study_fsa_actual_date'].notna()) &
                    (pd.to_datetime(study_df['ssus_assignment_date'], errors='coerce') <= pd.to_datetime(study_df['study_fsa_actual_date'], errors='coerce'))
                )
            ].copy()
            n_sites = len(site_scope)
            # 25% SA
            n_25 = max(1, int(np.ceil(n_sites * 0.25)))
            site_scope['sa_date'] = pd.to_datetime(site_scope['site_sa_actual_date'], errors='coerce')
            site_scope.loc[site_scope['sa_date'].isna(), 'sa_date'] = pd.to_datetime(site_scope['site_sa_plan_date'], errors='coerce')
            top_sites_25 = site_scope.sort_values('sa_date').head(n_25)
            top_sites_25_actual = pd.to_datetime(top_sites_25['site_sa_actual_date'], errors='coerce')
            sa_25_target = ctn_base + pd.Timedelta(weeks=13) if pd.notna(ctn_base) else None
            if top_sites_25_actual.notna().all() and pd.notna(ctn_base):
                sa_date = top_sites_25_actual.max()
                color = get_status_color(sa_date, pd.NaT, sa_25_target, now)
                weeks_str, _ = week_diff_str(sa_date, ctn_base, threshold=13, reverse=False)
                date_color = '#222'
                weeks_color = 'red' if color == COLOR_RED else '#888'
                sa_25_line1 = status_light(color) + f"<span style='color:{date_color};font-weight:bold'>A:{safe_date_str(sa_date)} (<span style='color:{weeks_color}'>{weeks_str}</span>)</span>"
            elif top_sites_25['sa_date'].notna().all() and pd.notna(ctn_base):
                sa_date = top_sites_25['sa_date'].max()
                color = get_status_color(pd.NaT, sa_date, sa_25_target, now)
                weeks_str, _ = week_diff_str(sa_date, ctn_base, threshold=13, reverse=False)
                date_color = 'red' if sa_date < now else '#1976d2'
                weeks_color = 'red' if color == COLOR_RED else '#888'
                sa_25_line1 = status_light(color) + f"<span style='color:{date_color};font-weight:bold'>P:{safe_date_str(sa_date)} (<span style='color:{weeks_color}'>{weeks_str}</span>)</span>"
            else:
                color = COLOR_RED if sa_25_target and now > sa_25_target else ''
                sa_25_line1 = (status_light(color) if color else '') + '<span style="color:#888">No Valid Data</span>'
            # target
            if sa_25_target:
                sa_25_line2 = f"<span style='color:#888;font-size:12px;'>Target: {sa_25_target.strftime('%Y-%m-%d')}, {n_25} sites</span>"
            else:
                sa_25_line2 = ''
            sa_25_display = f"{sa_25_line1}<br>{sa_25_line2}"
            # 75% SA
            n_75 = max(1, int(np.ceil(n_sites * 0.75)))
            top_sites_75 = site_scope.sort_values('sa_date').head(n_75)
            top_sites_75_actual = pd.to_datetime(top_sites_75['site_sa_actual_date'], errors='coerce')
            sa_75_target = ctn_base + pd.Timedelta(weeks=19) if pd.notna(ctn_base) else None
            
            # 修改：按照正确的75% SA逻辑
            # 1. 检查是否有足够数量的actual site activation date（第75分位的site有actual日期）
            if top_sites_75_actual.notna().all() and pd.notna(ctn_base):
                # 取第75分位那家site的actual的activation日期
                sa_date = top_sites_75_actual.max()
                color = get_status_color(sa_date, pd.NaT, sa_75_target, now)
                weeks_str, _ = week_diff_str(sa_date, ctn_base, threshold=19, reverse=False)
                date_color = '#222'
                weeks_color = 'red' if color == COLOR_RED else '#888'
                sa_75_line1 = status_light(color) + f"<span style='color:{date_color};font-weight:bold'>A:{safe_date_str(sa_date)} (<span style='color:{weeks_color}'>{weeks_str}</span>)</span>"
            # 2. 检查是否有足够数量的plan site activation date（第75分位的site有plan日期）
            elif top_sites_75['sa_date'].notna().all() and pd.notna(ctn_base):
                # 取第75分位那家site的activation日期（优先actual，没有actual的用plan）
                sa_date = top_sites_75['sa_date'].max()
                color = get_status_color(pd.NaT, sa_date, sa_75_target, now)
                weeks_str, _ = week_diff_str(sa_date, ctn_base, threshold=19, reverse=False)
                date_color = 'red' if sa_date < now else '#1976d2'
                weeks_color = 'red' if color == COLOR_RED else '#888'
                sa_75_line1 = status_light(color) + f"<span style='color:{date_color};font-weight:bold'>P:{safe_date_str(sa_date)} (<span style='color:{weeks_color}'>{weeks_str}</span>)</span>"
            # 3. 当数据缺失时，展示no valid data
            else:
                color = COLOR_RED if sa_75_target and now > sa_75_target else ''
                sa_75_line1 = (status_light(color) if color else '') + '<span style="color:#888">No Valid Data</span>'
            # target
            if sa_75_target:
                sa_75_line2 = f"<span style='color:#888;font-size:12px;'>Target: {sa_75_target.strftime('%Y-%m-%d')}, {n_75} sites</span>"
            else:
                sa_75_line2 = ''
            sa_75_display = f"{sa_75_line1}<br>{sa_75_line2}"
        else:
            color = COLOR_RED if sa_25_target and now > sa_25_target else ''
            color_75 = COLOR_RED if sa_75_target and now > sa_75_target else ''
            sa_25_display = (status_light(color) if color else '') + '<span style="color:#888">No Valid Data</span>'
            sa_75_display = (status_light(color_75) if color_75 else '') + '<span style="color:#888">No Valid Data</span>'

        # Country Contract
        contract_actual = study_df['main_contract_tmpl_actual_date'].dropna().sort_values().iloc[0] if 'main_contract_tmpl_actual_date' in study_df.columns and study_df['main_contract_tmpl_actual_date'].notna().any() else pd.NaT
        contract_plan = study_df['main_contract_tmpl_plan_date'].dropna().sort_values().iloc[0] if 'main_contract_tmpl_plan_date' in study_df.columns and study_df['main_contract_tmpl_plan_date'].notna().any() else pd.NaT
        contract_target = ctn_base + pd.Timedelta(weeks=-12) if pd.notna(ctn_base) else None
        def get_contract_status_light(actual, plan, target, now):
            if pd.notna(actual):
                if target is not None and actual > target:
                    return COLOR_RED
                else:
                    return COLOR_GREEN
            else:
                if target is not None and now > target:
                    return COLOR_RED
                elif pd.notna(plan) and plan > target:
                    return COLOR_YELLOW
                else:
                    return ''
        contract_color = get_contract_status_light(contract_actual, contract_plan, contract_target, now)
        if pd.notna(contract_actual):
            weeks_str, weeks_color = week_diff_str(contract_actual, ctn_base, threshold=-12, reverse=False)
            date_color = '#222'
            weeks_color = 'red' if contract_color == COLOR_RED else '#888'
            contract_line1 = status_light(contract_color) + f"<span style='color:{date_color};font-weight:bold'>A:{safe_date_str(contract_actual)} (<span style='color:{weeks_color}'>{weeks_str}</span>)</span>"
        elif pd.notna(contract_plan):
            weeks_str, weeks_color = week_diff_str(contract_plan, ctn_base, threshold=-12, reverse=False)
            date_color = 'red' if contract_plan < now else '#1976d2'
            weeks_color = 'red' if contract_color == COLOR_RED else '#888'
            contract_line1 = status_light(contract_color) + f"<span style='color:{date_color};font-weight:bold'>P:{safe_date_str(contract_plan)} (<span style='color:{weeks_color}'>{weeks_str}</span>)</span>"
        else:
            contract_line1 = status_light(contract_color)
        if contract_target:
            contract_line2 = f"<span style='color:#888;font-size:12px;'>Target: {contract_target.strftime('%Y-%m-%d')}</span>"
        else:
            contract_line2 = ''
        country_contract = f"{contract_line1}<br>{contract_line2}"

        details.append({
            'No': idx,
            'TA': ta,
            'Study': study_no,
            'Sourcing': sourcing,
            'CTN': ctn_html,
            'Leading EC Approval': ec_approval,
            'Leading Contract': contract,
            'Country Package': country_package,
            'Country Contract': country_contract,
            'IMP': imp_display,
            'Facility': sfr_display,
            'HGRAC': hia_display,
            'FSA': fsa_display,
            'FPS': fps_display,
            '25% SA': sa_25_display,
            '75% SA': sa_75_display
        })
    # === Country Contract 列填充 ===
    def get_country_contract_display(study):
        study_row = df[df['study_number'] == study]
        if study_row is None or study_row.empty:
            return ''
        actual = study_row['main_contract_tmpl_actual_date'].dropna().sort_values().iloc[0] if 'main_contract_tmpl_actual_date' in study_row.columns and study_row['main_contract_tmpl_actual_date'].notna().any() else pd.NaT
        plan = study_row['main_contract_tmpl_plan_date'].dropna().sort_values().iloc[0] if 'main_contract_tmpl_plan_date' in study_row.columns and study_row['main_contract_tmpl_plan_date'].notna().any() else pd.NaT
        # 获取CTN基准
        ctn_actual = study_row['study_ctn_actual_date'].iloc[0] if 'study_ctn_actual_date' in study_row.columns and not study_row.empty else pd.NaT
        ctn_plan = study_row['study_ctn_plan_date'].iloc[0] if 'study_ctn_plan_date' in study_row.columns and not study_row.empty else pd.NaT
        ctn_base = pd.to_datetime(ctn_actual) if pd.notna(ctn_actual) else (pd.to_datetime(ctn_plan) if pd.notna(ctn_plan) else None)
        now = pd.Timestamp.now()
        target = ctn_base + pd.Timedelta(weeks=-12) if ctn_base is not None else None
        COLOR_GREEN = '#43a047'
        COLOR_YELLOW = '#ffb300'
        COLOR_RED = '#e53935'
        def status_light(color):
            return f"<span style='display:inline-block;width:14px;height:14px;border-radius:50%;background:{color};margin-right:2px;vertical-align:middle;'></span>"
        def week_diff_str(date, ctn, threshold=None):
            if pd.isna(date) or pd.isna(ctn):
                return '', '#222'
            try:
                d1 = pd.to_datetime(date)
                d2 = pd.to_datetime(ctn)
                weeks = (d1 - d2).days / 7
                weeks_str = f"{weeks:.1f}w"
                color = '#222'
                if threshold is not None:
                    if weeks > threshold:
                        color = 'red'
                return weeks_str, color
            except Exception:
                return '', '#222'
        # actual优先
        html = ''
        if pd.notna(actual) and ctn_base is not None:
            weeks_str, weeks_color = week_diff_str(actual, ctn_base, threshold=-12)
            if actual > target:
                color = COLOR_RED
            else:
                color = COLOR_GREEN
            html = status_light(color) + f"<span style='color:#222;font-weight:bold'>A:{safe_date_str(actual)} (<span style='color:{weeks_color}'>{weeks_str}</span>)</span>"
        elif pd.notna(plan) and ctn_base is not None:
            weeks_str, weeks_color = week_diff_str(plan, ctn_base, threshold=-12)
            if plan > target:
                color = COLOR_YELLOW
            else:
                color = ''
            # 日期颜色
            if plan < now:
                date_color = 'red'
            else:
                date_color = '#1976d2'
            html = (status_light(color) if color else '') + f"<span style='color:{date_color};font-weight:bold'>P:{safe_date_str(plan)} (<span style='color:{weeks_color}'>{weeks_str}</span>)</span>"
        else:
            html = ''
        return html
    details_df = pd.DataFrame(details)
    if not details_df.empty and 'Country Contract' in details_df.columns:
        details_df['Country Contract'] = details_df['Study'].apply(get_country_contract_display)
    # 转为DataFrame
    details_df = pd.DataFrame(details)

    # 增加排序列：优先用actual，无则用plan
    def get_ctn_sort_val(row):
        study = row['Study']
        study_row = df[df['study_number'] == study]
        if study_row is not None and not study_row.empty:
            study_row = study_row.drop_duplicates(subset=['study_number'], keep='first')
            ctn_actual = study_row['study_ctn_actual_date'].iloc[0] if study_row is not None and not study_row.empty and 'study_ctn_actual_date' in study_row.columns else pd.NaT
            ctn_plan = study_row['study_ctn_plan_date'].iloc[0] if study_row is not None and not study_row.empty and 'study_ctn_plan_date' in study_row.columns else pd.NaT
            if pd.notna(ctn_actual):
                return pd.to_datetime(ctn_actual, errors='coerce')
            elif pd.notna(ctn_plan):
                return pd.to_datetime(ctn_plan, errors='coerce')
        return pd.NaT
    details_df['ctn_sort'] = details_df.apply(get_ctn_sort_val, axis=1)
    # 排序后重置序号
    details_df = details_df.sort_values('ctn_sort', ascending=True, na_position='last').reset_index(drop=True)
    details_df['No'] = range(1, len(details_df) + 1)
    details_df = details_df.drop(columns=['ctn_sort'])

    # ==== 构建CTN分组映射（提前） ====
    ctn_group_map = {}
    for idx, row in details_df.iterrows():
        study = row['Study']
        study_row = df[df['study_number'] == study].drop_duplicates(subset=['study_number'], keep='first')
        ctn_actual = study_row['study_ctn_actual_date'].iloc[0] if 'study_ctn_actual_date' in study_row.columns else pd.NaT
        ctn_plan = study_row['study_ctn_plan_date'].iloc[0] if 'study_ctn_plan_date' in study_row.columns else pd.NaT
        now = pd.Timestamp.now()
        next_3m = now + pd.DateOffset(months=3)
        if pd.notna(ctn_actual):
            ctn_group_map[study] = 'CTN obtained'
        elif pd.notna(ctn_plan):
            if ctn_plan <= next_3m:
                ctn_group_map[study] = 'Planned in next 3M'
            else:
                ctn_group_map[study] = 'After 3M'
        else:
            ctn_group_map[study] = 'After 3M'

    # ==== 全局筛选逻辑（提前到所有卡片之前） ====
    # 先定义全部选项
    all_study_options = details_df['Study'].dropna().unique().tolist()
    all_ta_options = details_df['TA'].dropna().unique().tolist()
    all_sourcing_options = details_df['Sourcing'].dropna().unique().tolist()
    ctn_options = ['CTN obtained', 'Planned in next 3M', 'After 3M']
    
    # ==== 横向紧凑布局：标题和筛选框同一行 ====
    col_title, col_study, col_ctn, col_ta, col_sourcing, col_milestone = st.columns([2, 1, 1, 1, 1, 1])
    with col_title:
        st.markdown('''
<style>
.study-details-btn {
    display: inline-block;
    padding: 8px 24px;
    font-size: 18px;
    font-weight: bold;
    color: #1976d2;
    background: #f5faff;
    border: 2px solid #1976d2;
    border-radius: 8px;
    cursor: pointer;
    transition: background 0.2s, color 0.2s;
    margin-bottom: 0;
    box-shadow: 0 2px 8px rgba(25,118,210,0.08);
}
.study-details-btn:hover {
    background: #e3f0fc;
    color: #0d47a1;
}
.study-details-balloon {
    margin-left: 10px;
    cursor: pointer;
    position: relative;
    font-size: 22px;
    line-height: 1;
    display: inline-block;
}
.study-details-balloon .balloon-tooltip {
    visibility: hidden;
    opacity: 0;
    min-width: 340px;
    max-width: 900px;
    background: #fffbe7;
    color: #333;
    text-align: left;
    border-radius: 8px;
    border: 1px solid #e0e0e0;
    padding: 12px 16px;
    position: absolute;
    z-index: 9999;
    top: 32px;
    left: 50%;
    transform: translateX(-50%);
    font-size: 15px;
    box-shadow: 0 2px 8px rgba(25,118,210,0.08);
    transition: opacity 0.2s;
    line-height: 1.7;
}
.study-details-balloon .balloon-tooltip .nowrap-line {
    white-space: nowrap;
    display: block;
}
.study-details-balloon:hover .balloon-tooltip {
    visibility: visible;
    opacity: 1;
}

.study-details-unicorn {
    margin-left: 10px;
    cursor: pointer;
    position: relative;
    font-size: 22px;
    line-height: 1;
    display: inline-block;
}
.study-details-unicorn .unicorn-tooltip {
    visibility: hidden;
    opacity: 0;
    min-width: 320px;
    max-width: 600px;
    background: #ffeaea;
    color: #b71c1c;
    text-align: left;
    border-radius: 8px;
    border: 1px solid #e57373;
    padding: 12px 16px;
    position: absolute;
    z-index: 9999;
    top: 32px;
    left: 50%;
    transform: translateX(-50%);
    font-size: 15px;
    box-shadow: 0 2px 8px rgba(183,28,28,0.08);
    transition: opacity 0.2s;
    line-height: 1.7;
}
.study-details-unicorn .unicorn-tooltip .nowrap-line {
    white-space: nowrap;
    display: block;
}
.study-details-unicorn:hover .unicorn-tooltip {
    visibility: visible;
    opacity: 1;
}
</style>
<div style="display:flex;align-items:center;gap:8px;">
  <div class="study-details-btn">Study Details</div>
  <span class="study-details-balloon">🎈
    <span class="balloon-tooltip">
      <span class="nowrap-line"><b>Target:</b></span>
      <span class="nowrap-line">Leading Site EC Approval Date≤ CTN</span>
      <span class="nowrap-line">Leading Site  Signed Contract Available Date （main）≤ CTN</span>
      <span class="nowrap-line">Country Package Ready≤ CTN-12wks</span>
      <span class="nowrap-line">Country Contract Template Available≤ CTN-12wks</span>
      <span class="nowrap-line">IMP Ready≤ CTN+8.5wks</span>
      <span class="nowrap-line">Facility Ready≤ CTN+8.5wks</span>
      <span class="nowrap-line">HGRAC Initial Approval≤ CTN+8.5wks</span>
      <span class="nowrap-line">FSA Date≤ CTN+9wks</span>
      <span class="nowrap-line">FPS Date≤ CTN+12wks</span>
      <span class="nowrap-line">25% SA Date≤ CTN+13wks</span>
      <span class="nowrap-line">75% SA Date≤ CTN+19wks</span>
    </span>
  </span>
  <span class="study-details-unicorn">🦄
    <span class="unicorn-tooltip">
      <span class="nowrap-line"><b>图标说明：</b></span>
      <span class="nowrap-line"><span style='color:#e53935;font-weight:bold;'>●</span> 红灯 = Miss</span>
      <span class="nowrap-line"><span style='color:#43a047;font-weight:bold;'>●</span> 绿灯 = Meet</span>
      <span class="nowrap-line"><span style='color:#ffb300;font-weight:bold;'>●</span> 黄灯 = Plan date &gt; Target date</span>
      <span class="nowrap-line"><span style='color:#1976d2;font-weight:bold;'>蓝色日期</span> = Plan date</span>
      <span class="nowrap-line"><span style='color:#e53935;font-weight:bold;'>红色日期</span> = Plan date overdue</span>
      <span class="nowrap-line"><span style='background:#fffde7;padding:2px 6px;border-radius:4px;'>黄色高光</span> = Target date in next 5wks</span>
    </span>
  </span>
</div>
''', unsafe_allow_html=True)
    with col_study:
        study_selected = st.multiselect(
            '', options=all_study_options, default=[], key='study_multiselect_final',
            placeholder='Study', label_visibility='collapsed')
    with col_ctn:
        ctn_selected = st.multiselect(
            '', options=ctn_options, default=[], key='ctn_multiselect_final',
            placeholder='CTN', label_visibility='collapsed')
    with col_ta:
        ta_selected = st.multiselect(
            '', options=all_ta_options, default=[], key='ta_multiselect_final',
            placeholder='TA', label_visibility='collapsed')
    with col_sourcing:
        sourcing_selected = st.multiselect(
            '', options=all_sourcing_options, default=[], key='sourcing_multiselect_final',
            placeholder='Sourcing', label_visibility='collapsed')
    with col_milestone:
        milestone_next5w = st.checkbox('Milestone in Next 5 weeks', key='milestone_next5w')

    # ==== 根据筛选过滤原始df（全局联动） ====
    import pandas as pd
    # 构建筛选mask
    mask = pd.Series([True] * len(details_df), index=details_df.index)
    if study_selected:
        mask &= details_df['Study'].isin(study_selected)
    if ta_selected:
        mask &= details_df['TA'].isin(ta_selected)
    if ctn_selected:
        mask &= details_df['Study'].map(ctn_group_map).isin(ctn_selected)
    if sourcing_selected:
        mask &= details_df['Sourcing'].isin(sourcing_selected)
    # 新增：Milestone in Next 5 weeks筛选
    if milestone_next5w:
        # 未来5周内有target milestone且该milestone的actual日期为空的study
        now = pd.Timestamp.now()
        five_weeks_later = now + pd.Timedelta(weeks=5)
        milestone_plan_actual = [
            # (plan_col, actual_col, week_offset)
            ('study_fsa_plan_date', 'study_fsa_actual_date', 9),
            ('study_fps_plan_date', 'study_fps_actual_date', 12),
            ('site_sa_plan_date', 'site_sa_actual_date', 13),
            ('site_sa_plan_date', 'site_sa_actual_date', 19),
            ('study_imp_ready_plan_date', 'study_imp_ready_actual_date', 8.5),
            ('study_sfr_plan_date', 'study_sfr_actual_date', 8.5),
            ('study_hia_plan_date', 'study_hia_actual_date', 8.5),
            ('ec_approval_plan_date', 'ec_approval_actual_date', 0),
            ('contract_signoff_plan_date', 'contract_signoff_actual_date', 0),
            ('country_package_ready_plan_date', 'country_package_ready_actual_date', -12),
            ('main_contract_tmpl_plan_date', 'main_contract_tmpl_actual_date', -12)
        ]
        studies_with_milestone = set()
        for idx, row in df.iterrows():
            ctn_actual = row['study_ctn_actual_date'] if 'study_ctn_actual_date' in row else pd.NaT
            ctn_plan = row['study_ctn_plan_date'] if 'study_ctn_plan_date' in row else pd.NaT
            ctn_base = pd.to_datetime(ctn_actual) if pd.notna(ctn_actual) else (pd.to_datetime(ctn_plan) if pd.notna(ctn_plan) else None)
            if ctn_base is None:
                continue
            for plan_col, actual_col, week_offset in milestone_plan_actual:
                plan_date = row[plan_col] if plan_col in row else pd.NaT
                actual_date = row[actual_col] if actual_col in row else pd.NaT
                if pd.notna(plan_date):
                    plan_date = pd.to_datetime(plan_date, errors='coerce')
                    target = ctn_base + pd.Timedelta(weeks=week_offset)
                    if now < target <= five_weeks_later and pd.isna(actual_date):
                        studies_with_milestone.add(row['study_number'])
                        break
        mask &= details_df['Study'].isin(studies_with_milestone)
    
    # 获取筛选后的study列表
    filtered_studies = details_df[mask]['Study'].tolist()
    
    # 全局过滤原始df（所有卡片都使用这个过滤后的df）
    if filtered_studies:
        df_filtered = df[df['study_number'].isin(filtered_studies)].copy()
    else:
        df_filtered = df.copy()  # 没选时显示全部
    
    # 更新details_df用于表格显示
    filtered_details_df = details_df[mask].copy()
    
    # ==== 表格居中渲染 ====
    def render_html_table(df, raw_df=None):
        # ==== 25% SA和75% SA高亮study集合 ====
        highlight_25sa_studies = set()
        highlight_75sa_studies = set()
        now = pd.Timestamp.now()
        five_weeks_later = now + pd.Timedelta(weeks=5)
        if raw_df is not None and 'study_number' in raw_df.columns:
            for study in raw_df['study_number'].dropna().unique():
                study_df = raw_df[raw_df['study_number'] == study]
                # 计算CTN基准
                ctn_actual = study_df['study_ctn_actual_date'].iloc[0] if 'study_ctn_actual_date' in study_df.columns else pd.NaT
                ctn_plan = study_df['study_ctn_plan_date'].iloc[0] if 'study_ctn_plan_date' in study_df.columns else pd.NaT
                ctn_base = pd.to_datetime(ctn_actual) if pd.notna(ctn_actual) else (pd.to_datetime(ctn_plan) if pd.notna(ctn_plan) else None)
                if ctn_base is None:
                    continue
                # site_scope筛选
                if all(col in study_df.columns for col in ['ssus', 'site_status', 'ssus_assignment_date', 'study_fsa_actual_date']):
                    site_scope = study_df[
                        (study_df['ssus'].notna()) |
                        ((study_df['ssus'].isna()) & (study_df['site_status'] == 'Initiating')) |
                        (
                            (study_df['ssus_assignment_date'].notna()) &
                            (study_df['study_fsa_actual_date'].notna()) &
                            (pd.to_datetime(study_df['ssus_assignment_date'], errors='coerce') <= pd.to_datetime(study_df['study_fsa_actual_date'], errors='coerce'))
                        )
                    ].copy()
                else:
                    site_scope = study_df.copy()
                n_sites = len(site_scope)
                if n_sites == 0:
                    continue
                # 25% SA
                n_25 = max(1, int(np.ceil(n_sites * 0.25)))
                site_scope['sa_plan'] = pd.to_datetime(site_scope['site_sa_plan_date'], errors='coerce')
                site_scope['sa_actual'] = pd.to_datetime(site_scope['site_sa_actual_date'], errors='coerce')
                top_sites_25 = site_scope.sort_values('sa_plan').head(n_25)
                sa_25_target = ctn_base + pd.Timedelta(weeks=13)
                if now < sa_25_target <= five_weeks_later and top_sites_25['sa_actual'].isna().any():
                    highlight_25sa_studies.add(study)
                # 75% SA
                n_75 = max(1, int(np.ceil(n_sites * 0.75)))
                top_sites_75 = site_scope.sort_values('sa_plan').head(n_75)
                sa_75_target = ctn_base + pd.Timedelta(weeks=19)
                if now < sa_75_target <= five_weeks_later and top_sites_75['sa_actual'].isna().any():
                    highlight_75sa_studies.add(study)
        columns = list(df.columns)
        column_widths = {
            'No': '50px',
            'TA': '110px',
            'Study': '90px',
            'Sourcing': '110px',
            'CTN': '180px',
            'Leading EC Approval': '200px',
            'Leading Contract': '200px',
            'Country Package': '200px',
            'Country Contract': '200px',
            'IMP': '200px',
            'Facility': '200px',
            'HGRAC': '200px',
            'FSA': '200px',
            'FPS': '200px',
            '25% SA': '200px',
            '75% SA': '200px'
        }
        fixed_columns = ['No', 'TA', 'Study', 'Sourcing', 'CTN']
        fixed_bg = '#fff'
        # 构建表头
        new_headers = []
        left_offset = 0
        for idx, col in enumerate(columns):
            th_style = (
                f'border:1px solid #ccc;border-bottom:2px solid #ccc;padding:4px 8px;'
                f'background:#e6f4ea;text-align:center;white-space:nowrap;overflow:hidden;'
                f'text-overflow:ellipsis;width:{column_widths.get(col, "120px")};'
                f'max-width:{column_widths.get(col, "120px")};vertical-align:middle;'
            )
            if col in fixed_columns:
                th_style += (
                    f'position:sticky;top:0;left:{left_offset}px;z-index:20;'
                    f'background:#e6f4ea;box-shadow:2px 0 0 #ccc;'
                )
                left_offset += int(column_widths[col][:-2])
            else:
                th_style += 'position:sticky;top:0;z-index:10;'
            new_headers.append(f'<th style="{th_style}">{col}</th>')
        html = '<div style="overflow-y:auto; max-height:480px; width:100%; border-top:2px solid #ccc; border-bottom:2px solid #ccc;">'
        html += '<table style="width:100%;border-collapse:separate;border-spacing:0;table-layout:fixed;">'
        html += '<thead><tr>' + ''.join(new_headers) + '</tr></thead><tbody>'
        highlight_cols = {
            'Country Package':    ('country_package_ready_plan_date', 'country_package_ready_actual_date', -12),
            'Country Contract':   ('main_contract_tmpl_plan_date', 'main_contract_tmpl_actual_date', -12),
            'IMP':                ('study_imp_ready_plan_date', 'study_imp_ready_actual_date', 8.5),
            'Facility':           ('study_sfr_plan_date', 'study_sfr_actual_date', 8.5),
            'HGRAC':              ('study_hia_plan_date', 'study_hia_actual_date', 8.5),
            'FSA':                ('study_fsa_plan_date', 'study_fsa_actual_date', 9),
            'FPS':                ('study_fps_plan_date', 'study_fps_actual_date', 12),
            '25% SA':             ('site_sa_plan_date', 'site_sa_actual_date', 13),
            '75% SA':             ('site_sa_plan_date', 'site_sa_actual_date', 19),
            'Leading EC Approval':('ec_approval_plan_date', 'ec_approval_actual_date', 0),
            'Leading Contract':   ('contract_signoff_plan_date', 'contract_signoff_actual_date', 0)
        }
        n_rows = len(df)
        for row_idx, (_, row) in enumerate(df.iterrows()):
            tr_style = ''
            if row_idx == n_rows - 1:
                tr_style += 'border-bottom:2px solid #ccc;'
            html += f'<tr style="{tr_style}">'  # 应用tr的style
            left_offset_td = 0
            for col_idx, (col, cell) in enumerate(zip(df.columns, row)):
                style = f"border:1px solid #ccc;padding:4px 8px;text-align:center;width:{column_widths.get(col, '120px')};word-break:break-all;white-space:pre-line;max-height:120px;overflow-y:auto;vertical-align:middle;background:{fixed_bg};"
                if col in fixed_columns:
                    style += f'position:sticky;left:{left_offset_td}px;z-index:5;background:{fixed_bg};box-shadow:2px 0 0 #ccc;'
                    left_offset_td += int(column_widths[col][:-2])
                else:
                    style += 'z-index:1;'
                # 新增：25% SA和75% SA集合高亮
                if col == '25% SA' and row['Study'] in highlight_25sa_studies:
                    style += "background:#fffde7;"
                if col == '75% SA' and row['Study'] in highlight_75sa_studies:
                    style += "background:#fffde7;"
                # 判断是否需要高亮
                if col in highlight_cols and raw_df is not None:
                    plan_col, actual_col, week_offset = highlight_cols[col]
                    study = row['Study'] if 'Study' in row else None
                    if study and 'study_number' in raw_df.columns:
                        orig_rows = raw_df[raw_df['study_number'] == study]
                        if not orig_rows.empty:
                            orig_row = orig_rows.iloc[0]
                            ctn_actual = orig_row['study_ctn_actual_date'] if 'study_ctn_actual_date' in orig_row else pd.NaT
                            ctn_plan = orig_row['study_ctn_plan_date'] if 'study_ctn_plan_date' in orig_row else pd.NaT
                            ctn_base = pd.to_datetime(ctn_actual) if pd.notna(ctn_actual) else (pd.to_datetime(ctn_plan) if pd.notna(ctn_plan) else None)
                            plan_date = orig_row[plan_col] if plan_col in orig_row else pd.NaT
                            actual_date = orig_row[actual_col] if actual_col in orig_row else pd.NaT
                            # 新增：CTN计划日期在未来5周内，且Leading EC Approval/Contract的actual为空，单元格高亮为黄色
                            if col in ['Leading EC Approval', 'Leading Contract'] and pd.isna(ctn_actual) and pd.notna(ctn_plan) and ctn_base is not None:
                                target = ctn_base + pd.Timedelta(weeks=week_offset)
                                if now < target <= five_weeks_later and pd.isna(actual_date):
                                    style += "background:#fffde7;"  # 更亮的黄色
                            # 原有高亮逻辑
                            if pd.isna(actual_date) and ctn_base is not None:
                                target = ctn_base + pd.Timedelta(weeks=week_offset)
                                # 调试YO45758的FPS
                                if study == 'YO45758' and col == 'FPS':
                                    print(f"YO45758 FPS Debug:")
                                    print(f"  plan_date: {plan_date}")
                                    print(f"  actual_date: {actual_date}")
                                    print(f"  ctn_base: {ctn_base}")
                                    print(f"  target: {target}")
                                    print(f"  now: {now}")
                                    print(f"  five_weeks_later: {five_weeks_later}")
                                    print(f"  condition: now <= target <= five_weeks_later = {now <= target <= five_weeks_later}")
                                # 修改：检查Target日期是否在未来5周内，而不是plan_date
                                if now <= target <= five_weeks_later:
                                    style += "background:#fff9e5;"  # 浅黄色
                if col in ['TA', 'Study', 'Sourcing']:
                    html += f'<td style="{style}font-weight:bold;">{cell}</td>'
                else:
                    html += f'<td style="{style}">{cell}</td>'
            html += '</tr>'
        html += '</tbody></table></div>'
        return html
    st.markdown(render_html_table(filtered_details_df, raw_df=df), unsafe_allow_html=True)
    
    # ==== 所有卡片使用过滤后的df ====
    # 将df替换为df_filtered，这样所有卡片都显示筛选后的数据
    df = df_filtered
else:
    st.markdown('<div class="card-content">请上传包含 study_number, study_ctn_plan_date, study_ctn_actual_date 字段的CSV</div>', unsafe_allow_html=True)

# 在表格下方增加5个卡片，风格与第一行一致，内容留空
st.markdown("---")
cards = st.columns(5)
for j, card in enumerate(cards):
    with card:
        if j == 1:
            # 原卡片6内容（Site Selection & SSUS Assignment）
            st.markdown('<div class="stCardTitle">Site Selection & SSUS Assignment</div>', unsafe_allow_html=True)
            st.markdown('<div style="text-align:center;color:#222;font-size:13px;margin-bottom:4px;">vs country package ready date</div>', unsafe_allow_html=True)
            if df is not None and 'site_select_actual_date' in df.columns and 'study_number' in df.columns and 'ssus_assignment_date' in df.columns and 'country_package_ready_actual_date' in df.columns:
                # 计算每个study的country_package_ready_date（优先actual，无则plan）
                study_package_dates = {}
                for study, group in df.groupby('study_number'):
                    actual_dates = group['country_package_ready_actual_date'].dropna()
                    plan_dates = group['country_package_ready_plan_date'].dropna() if 'country_package_ready_plan_date' in group.columns else []
                    if not actual_dates.empty:
                        study_package_dates[study] = actual_dates.min()
                    elif len(plan_dates) > 0:
                        study_package_dates[study] = plan_dates.min()
                # 只保留有country_package_ready_date的study的数据
                df_valid = df[df['study_number'].isin(study_package_dates.keys())].copy()
                
                # Site Selection vs country package ready
                site_selection_deltas = []
                for study, group in df_valid.groupby('study_number'):
                    package_date = study_package_dates[study]
                    for _, row in group.iterrows():
                        if pd.notna(row['site_select_actual_date']):
                            delta_weeks = (row['site_select_actual_date'] - package_date).days / 7
                            site_selection_deltas.append(delta_weeks)
                
                # SSUS Assignment vs country package ready
                ssus_deltas = []
                for study, group in df_valid.groupby('study_number'):
                    package_date = study_package_dates[study]
                    for _, row in group.iterrows():
                        if pd.notna(row['ssus_assignment_date']):
                            delta_weeks = (row['ssus_assignment_date'] - package_date).days / 7
                            ssus_deltas.append(delta_weeks)
                
                # 分组统计
                bins = [-float('inf'), 0, 2, 4, 8, float('inf')]
                labels = ['Before Package Ready', '≤2w', '2-4w', '4-8w', '>8w']
                
                # Site Selection分组
                if site_selection_deltas:
                    cats_site = pd.cut(site_selection_deltas, bins=bins, labels=labels, right=True, include_lowest=True)
                    value_counts_site = pd.value_counts(cats_site, sort=False)
                    values_site = value_counts_site.values.tolist()
                else:
                    values_site = [0] * len(labels)
                
                # SSUS Assignment分组
                if ssus_deltas:
                    cats_ssus = pd.cut(ssus_deltas, bins=bins, labels=labels, right=True, include_lowest=True)
                    value_counts_ssus = pd.value_counts(cats_ssus, sort=False)
                    values_ssus = value_counts_ssus.values.tolist()
                else:
                    values_ssus = [0] * len(labels)
                
                st.markdown('<div style="display:flex;justify-content:flex-start;margin-left:106px;">', unsafe_allow_html=True)
                bar_fig = go.Figure(go.Bar(
                    x=labels,
                    y=values_site,
                    name='Site Selection',
                    marker_color='#1976d2',
                    text=values_site,
                    textposition='auto',
                    offsetgroup=0,
                    textfont=dict(size=12, color='white', family='Microsoft YaHei, Open Sans, verdana, arial, sans-serif')
                ))
                bar_fig.add_trace(go.Bar(
                    x=labels,
                    y=values_ssus,
                    name='SSUS Assignment',
                    marker_color='#ffb300',
                    text=values_ssus,
                    textposition='auto',
                    offsetgroup=1,
                    textfont=dict(size=12, color='black', family='Microsoft YaHei, Open Sans, verdana, arial, sans-serif')
                ))
                bar_fig.update_layout(
                    barmode='group',
                    height=270,  # 或更大
                    width=480,   # 或更大
                    margin=dict(l=0, r=0, t=20, b=0),
                    yaxis=dict(title='', showticklabels=False, showgrid=False, tickfont=dict(size=16, color='#222')),
                    xaxis=dict(
                        tickfont=dict(
                            size=14,
                            color='#222'
                        )
                    ),
                    legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='center', x=0.5),
                    font=dict(family='Microsoft YaHei, Open Sans, verdana, arial, sans-serif')
                )
                st.plotly_chart(bar_fig, use_container_width=False, key='card_10_bar')
                st.markdown('</div>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="card-content">请上传包含 study_number, site_select_actual_date, ssus_assignment_date, country_package_ready_actual_date 字段的CSV</div>', unsafe_allow_html=True)
        elif j == 0:
            # 原卡片7内容（Total Site）
            st.markdown('<div class="stCardTitle" style="margin-bottom:1px;">Total Site</div>', unsafe_allow_html=True)
            st.markdown('<style>div[data-testid="column"]:nth-child(1) > div {max-width:280px; min-width:280px; padding-top:4px; padding-bottom:4px;}</style>', unsafe_allow_html=True)
            if df is not None and 'study_site_number' in df.columns:
                total_site = df['study_site_number'].nunique()
                st.markdown(f'<div class="stCardNumber" style="font-size:24px;margin-top:1px;margin-bottom:1px;">{total_site}</div>', unsafe_allow_html=True)
                st.markdown('<div style="text-align:center;color:#222;font-size:13px;margin-bottom:0px;">Count of Process Complete</div>', unsafe_allow_html=True)
                steps = [
                    ('GCP', 'site_gcp_actual_date'),
                    ('EC', 'ec_approval_actual_date'),
                    ('Main Contract', 'contract_signoff_actual_date'),
                    ('Commitment Letter', 'comm_ltr_obt_actual_date'),
                    ('SSU Last Step', None),
                    ('Activation', 'site_sa_actual_date')
                ]
                def get_last_step(row):
                    ec = row.get('ec_approval_actual_date')
                    contract = row.get('contract_signoff_actual_date')
                    comm = row.get('comm_ltr_obt_actual_date')
                    crc_type = str(row.get('crc_contract_type', '')).strip()
                    crc_impact = str(row.get('crc_contract_impact_sa', '')).strip().upper()
                    crc = row.get('crc_contract_signoff_actual_date') if (crc_type == '三方' and crc_impact == 'YES') else None

                    steps = [ec, contract, comm]
                    if crc is not None:
                        steps.append(crc)

                    if pd.notna(row.get('site_sa_actual_date')):
                        # 宽松：只要有一个非空
                        steps_non_na = [d for d in steps if pd.notna(d)]
                        return max(steps_non_na) if steps_non_na else pd.NaT
                    else:
                        # 严格：所有纳入的步骤都必须非空
                        if all(pd.notna(d) for d in steps):
                            return max(steps)
                        else:
                            return pd.NaT
                df['ssu_last_step_actual'] = df.apply(get_last_step, axis=1)
                result = []
                for step_name, col in steps:
                    if step_name == 'SSU Last Step':
                        complete = df['ssu_last_step_actual'].notna().sum()
                    else:
                        complete = df[col].notna().sum() if col in df.columns else 0
                    result.append({'step': step_name, 'Complete': complete})
                st.markdown('<style>.progress-row{display:flex;align-items:center;margin-bottom:12px;}.progress-row:last-child{margin-bottom:0px;}.progress-label{width:100px;text-align:right;font-size:16px;white-space:nowrap;}.progress-bar-wrap{flex:0 0 180px;max-width:180px;min-width:180px;margin:0 1px;}.progress-bar-bg{background:#eee;border-radius:8px;height:16px;position:relative;width:180px;}.progress-bar-fill{background:#43a047;height:16px;border-radius:8px 0 0 8px;position:absolute;top:0;left:0;}.progress-bar-text{position:absolute;top:0;left:50%;transform:translateX(-50%);font-size:12px;color:#222;font-family:Microsoft YaHei, Open Sans, verdana, arial, sans-serif;font-weight:bold;line-height:16px;}</style>', unsafe_allow_html=True)
                for r in result:
                    percent = r['Complete'] / total_site if total_site else 0
                    percent_width = int(percent * 100)
                    st.markdown(f'''
                    <div class="progress-row">
                        <div class="progress-label">{r['step']}</div>
                        <div class="progress-bar-wrap">
                            <div class="progress-bar-bg">
                                <div class="progress-bar-fill" style="width:{percent_width}%;background:#43a047;"></div>
                                <div class="progress-bar-text" style="font-size:12px;color:#222;font-family:Microsoft YaHei, Open Sans, verdana, arial, sans-serif;font-weight:bold;">
                                    {r['Complete']}/{total_site}
                                </div>
                            </div>
                        </div>
                    </div>
                    ''', unsafe_allow_html=True)
                # Total Site卡片内容保持不变，移除tab
            else:
                st.markdown('<div class="card-content">请上传包含 study_site_number 字段的CSV</div>', unsafe_allow_html=True)
        elif j == 2:
            st.markdown('<div class="stCardTitle">Country Package & Main Contract Template</div>', unsafe_allow_html=True)
            st.markdown('<div style="text-align:center;color:#222;font-size:13px;margin-bottom:4px;">vs CTN date</div>', unsafe_allow_html=True)
            if df is not None and 'study_number' in df.columns and 'country_package_ready_actual_date' in df.columns and 'main_contract_tmpl_actual_date' in df.columns and ('study_ctn_actual_date' in df.columns or 'study_ctn_plan_date' in df.columns):
                # 只保留有country_package_ready_actual_date或main_contract_tmpl_actual_date的study
                study_df = df.drop_duplicates(subset=['study_number'], keep='first').copy()
                # 计算CTN日期（优先actual）
                study_df['ctn_date'] = study_df['study_ctn_actual_date']
                study_df.loc[study_df['ctn_date'].isna(), 'ctn_date'] = study_df['study_ctn_plan_date']
                # 只保留ctn_date非空的
                study_df = study_df[study_df['ctn_date'].notna()].copy()
                # 计算country_package_ready_actual_date与ctn_date的周差
                bins = [-float('inf'), -12, -8, -4, 0, float('inf')]
                labels = ['before CTN-12w', '-12~-8w', '-8~-4w', '-4~0w', 'after CTN']
                # Country Package
                cp_deltas = (study_df['country_package_ready_actual_date'] - study_df['ctn_date']).dt.days / 7
                cp_cats = pd.cut(cp_deltas, bins=bins, labels=labels, right=True, include_lowest=True)
                cp_counts = cp_cats.value_counts(sort=False)
                cp_values = cp_counts.values.tolist()
                # Main Contract
                mc_deltas = (study_df['main_contract_tmpl_actual_date'] - study_df['ctn_date']).dt.days / 7
                if not mc_deltas.empty:
                    mc_cats = pd.cut(mc_deltas, bins=bins, labels=labels, right=True, include_lowest=True)
                    mc_counts = mc_cats.value_counts(sort=False)
                    mc_values = mc_counts.values.tolist()
                else:
                    mc_values = [0] * len(labels)
                # 绘制分组柱状图
                st.markdown('<div style="display:flex;justify-content:flex-start;margin-left:106px;">', unsafe_allow_html=True)
                bar_fig = go.Figure(go.Bar(
                    x=labels,
                    y=cp_values,
                    name='Country Package',
                    marker_color='#1976d2',
                    text=cp_values,
                    textposition='auto',
                    offsetgroup=0,
                    textfont=dict(size=12, color='white', family='Arial')
                ))
                bar_fig.add_trace(go.Bar(
                    x=labels,
                    y=mc_values,
                    name='Main Contract',
                    marker_color='#ffb300',
                    text=mc_values,
                    textposition='auto',
                    offsetgroup=1,
                    textfont=dict(size=12, color='black', family='Microsoft YaHei, Open Sans, verdana, arial, sans-serif')
                ))
                bar_fig.update_layout(
                    barmode='group',
                    height=270,
                    width=480,
                    margin=dict(l=0, r=0, t=20, b=0),
                    yaxis=dict(title='', showticklabels=False, showgrid=False, tickfont=dict(size=16, color='#222')),
                    xaxis=dict(
                        tickfont=dict(
                            size=16,
                            color='#222'
                        )
                    ),
                    legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='center', x=0.5, font=dict(size=16, color='#6D4C41')),
                    font=dict(size=18, color='#6D4C41')
                )
                st.plotly_chart(bar_fig, use_container_width=False, key='card_7_bar')
                st.markdown('</div>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="card-content">请上传包含 study_number, country_package_ready_actual_date, main_contract_tmpl_actual_date, study_ctn_actual_date/study_ctn_plan_date 字段的CSV</div>', unsafe_allow_html=True)
        elif j == 3:
            st.markdown('<div class="stCardTitle">Site Process Median Duration</div>', unsafe_allow_html=True)
            st.markdown('<div style="text-align:center;color:#222;font-size:13px;margin-bottom:4px;">Mdn duration of each process</div>', unsafe_allow_html=True)
            if df is not None:
                flows = [
                    ('CTN-GCP', 'site_gcp_actual_date', 'study_ctn_actual_date'),
                    ('CTN-EC', 'ec_approval_actual_date', 'study_ctn_actual_date'),
                    ('CTN-Contract', 'contract_signoff_actual_date', 'study_ctn_actual_date'),
                    ('CTN-SA', 'site_sa_actual_date', 'study_ctn_actual_date'),
                    ('GCP-EC', 'ec_approval_actual_date', 'site_gcp_actual_date'),
                    ('GCP-Contract', 'contract_signoff_actual_date', 'site_gcp_actual_date'),
                    ('Comm Ltr-HGRAC', 'comm_ltr_obt_actual_date', 'study_hia_actual_date'),
                ]
                medians = []
                for flow_name, end_col, start_col in flows:
                    if end_col in df.columns and start_col in df.columns:
                        valid = df[end_col].notna() & df[start_col].notna()
                        days = (df.loc[valid, end_col] - df.loc[valid, start_col]).dt.days
                        if not days.empty:
                            median_val = int(np.median(days))
                        else:
                            median_val = None
                    else:
                        median_val = None
                    medians.append(median_val)
                # 用横向bar图展示
                import plotly.graph_objects as go
                bar_fig = go.Figure(
                    go.Bar(
                        y=[f[0] for f in flows],
                        x=[m if m is not None else 0 for m in medians],
                        text=[str(m) if m is not None else '—' for m in medians],
                        textposition='inside',
                        marker_color='#1976d2',
                        orientation='h',
                        textfont=dict(size=12, color='white', family='Microsoft YaHei, Open Sans, verdana, arial, sans-serif')
                    )
                )
                bar_fig.update_layout(
                    height=330,
                    width=570,
                    margin=dict(l=0, r=0, t=20, b=0),
                    xaxis=dict(title='', showgrid=True, tickfont=dict(size=16, color='#222')),
                    yaxis=dict(title='', tickfont=dict(size=16, color='#222')),
                    font=dict(size=18, color='#6D4C41')
                )
                st.plotly_chart(bar_fig, use_container_width=False, key='card_8_bar')
            else:
                st.markdown('<div class="card-content">请上传包含相关actual date字段的CSV</div>', unsafe_allow_html=True)
        elif j == 4:
            st.markdown('<div class="stCardTitle">Leading Site Process Median Duration</div>', unsafe_allow_html=True)
            st.markdown('<div style="text-align:center;color:#222;font-size:13px;margin-bottom:4px;">Mdn duration of each process (leading site)</div>', unsafe_allow_html=True)
            if df is not None:
                flows = [
                    ('Package-Country to Site', 'site_package_actual_date', 'country_package_ready_actual_date'),
                    ('Site package-GCP', 'site_gcp_actual_date', 'site_package_actual_date'),
                    ('GCP-EC', 'ec_approval_actual_date', 'site_gcp_actual_date'),
                    ('GCP-Contract', 'contract_signoff_actual_date', 'site_gcp_actual_date'),
                    ('Comm Ltr-CTN', 'comm_ltr_obt_actual_date', 'study_ctn_actual_date'),
                    ('CTN-SA', 'site_sa_actual_date', 'study_ctn_actual_date'),
                ]
                # 只保留leading site
                if 'leading_site_or_not' in df.columns:
                    df_lead = df[df['leading_site_or_not'].astype(str).str.upper() == 'YES'].copy()
                else:
                    df_lead = df.copy()  # 没有该字段则全用
                medians = []
                for flow_name, end_col, start_col in flows:
                    if end_col in df_lead.columns and start_col in df_lead.columns:
                        valid = df_lead[end_col].notna() & df_lead[start_col].notna()
                        days = (df_lead.loc[valid, end_col] - df_lead.loc[valid, start_col]).dt.days
                        if not days.empty:
                            median_val = int(np.median(days))
                        else:
                            median_val = None
                    else:
                        median_val = None
                    medians.append(median_val)
                # 用横向bar图展示
                import plotly.graph_objects as go
                bar_fig = go.Figure(
                    go.Bar(
                        y=[f[0] for f in flows],
                        x=[m if m is not None else 0 for m in medians],
                        text=[str(m) if m is not None else '—' for m in medians],
                        textposition='inside',
                        marker_color='#1976d2',
                        orientation='h',
                        textfont=dict(size=12, color='white', family='Microsoft YaHei, Open Sans, verdana, arial, sans-serif')
                    )
                )
                bar_fig.update_layout(
                    height=330,
                    width=570,
                    margin=dict(l=0, r=0, t=20, b=0),
                    xaxis=dict(title='', showgrid=True, tickfont=dict(size=16, color='#222')),
                    yaxis=dict(title='', tickfont=dict(size=16, color='#222')),
                    font=dict(size=18, color='#6D4C41')
                )
                st.plotly_chart(bar_fig, use_container_width=False, key='card_9_bar')
            else:
                st.markdown('<div class="card-content">请上传包含相关actual date字段的CSV</div>', unsafe_allow_html=True)
        else:
            with st.container():
                st.markdown(f"""
                <div class="stCardTitle">卡片 {j+6}</div>
                <div class="card-content">
                    内容区域 {j+6}
                </div>
                """, unsafe_allow_html=True)

# ==== Leading Site Details 独立区域 ====
st.markdown("---")
st.markdown('<div style="margin-top:-25px;padding-top:0;"></div>', unsafe_allow_html=True)

# 添加tab样式
st.markdown('''
<style>
/* 放大tab字体、加粗、深咖啡色 */
div[data-baseweb="tab"] button {
    font-size: 20px !important;
    font-weight: bold !important;
    color: #6D4C41 !important;
}
/* 减少tab与分割线的间距 */
div[data-baseweb="tab-list"] {
    margin-top: -25px !important;
}
</style>
''', unsafe_allow_html=True)
st.markdown('''
<style>
/* 兼容新版Streamlit tab标题样式 */
div[data-baseweb="tab-list"] button[role="tab"] {
    font-size: 20px !important;
    font-weight: bold !important;
    color: #6D4C41 !important;
}
</style>
''', unsafe_allow_html=True)
st.markdown('''
<style>
/* Streamlit 1.18+ tab标题样式 */
div[data-baseweb="tab-list"] button[role="tab"] > div {
    font-size: 20px !important;
    font-weight: bold !important;
    color: #6D4C41 !important;
}
/* 兼容旧版Streamlit tab标题样式 */
div[data-baseweb="tab-list"] button[role="tab"] span {
    font-size: 20px !important;
    font-weight: bold !important;
    color: #6D4C41 !important;
}
/* 再加一层，防止被外部样式覆盖 */
div[data-baseweb="tab-list"] button[role="tab"] * {
    font-size: 20px !important;
    font-weight: bold !important;
    color: #6D4C41 !important;
}
</style>
''', unsafe_allow_html=True)

st.markdown('<div style="margin-top:-30px;">', unsafe_allow_html=True)
tabs = st.tabs(["Leading Site", "HGRAC", "IMP"])
st.markdown('</div>', unsafe_allow_html=True)
with tabs[0]:
    if df is not None and 'leading_site_or_not' in df.columns:
        # 获取所有leading site数据
        leading_sites = df[df['leading_site_or_not'].astype(str).str.upper() == 'YES'].copy()
        
        if not leading_sites.empty:
            # 生成Leading Site Details表格数据
            leading_details = []
            for idx, row in leading_sites.iterrows():
                # 序号 - 将在排序后重新赋值
                seq_num = idx + 1
                
                # TA, Study - 从study details表格获取相同逻辑
                study = row['study_number']
                study_df = df[df['study_number'] == study]
                ta = study_df['clintrack_ta_desc'].iloc[0] if study_df is not None and not study_df.empty and 'clintrack_ta_desc' in study_df.columns else ''
                study_no = study
                sourcing = study_df['sourcing_strategy'].iloc[0] if study_df is not None and not study_df.empty and 'sourcing_strategy' in study_df.columns else ''
                
                # Site信息
                site_number_raw = row['study_site_number'] if 'study_site_number' in row else ''
                # 去掉小数点，转换为整数
                try:
                    if pd.notna(site_number_raw) and str(site_number_raw).strip() != '':
                        site_number = str(int(float(site_number_raw)))
                    else:
                        site_number = ''
                except (ValueError, TypeError):
                    site_number = str(site_number_raw) if pd.notna(site_number_raw) else ''
                site_name = row['site_name'] if 'site_name' in row else ''
                
                # 日期字段处理函数
                def format_date_display(actual_date, plan_date, study=None, is_ec_approval=False, is_contract_signoff=False):
                    # 灯颜色定义
                    COLOR_GREEN = '#43a047'
                    COLOR_YELLOW = '#ffb300'
                    COLOR_RED = '#e53935'
                    
                    # 灯逻辑判断函数
                    def get_status_color(actual, plan, target, now):
                        if pd.notna(actual):
                            if target is not None and actual > target:
                                return COLOR_RED  # actual超期
                            else:
                                return COLOR_GREEN  # actual未超期
                        else:
                            if target is not None and now > target:
                                return COLOR_RED  # 没有actual且已超期
                            elif pd.notna(plan) and plan > target:
                                return COLOR_YELLOW  # plan大于目标日期且actual为空，黄灯
                            else:
                                return ''  # 其他情况无灯
                    
                    def status_light(color):
                        return f"<span style='display:inline-block;width:14px;height:14px;border-radius:50%;background:{color};margin-right:2px;vertical-align:middle;'></span>"
                    
                    # 对于EC Approval和Contract Signoff，添加红黄绿灯
                    if (is_ec_approval or is_contract_signoff) and study:
                        # 获取该study的CTN基准日期
                        study_row = df[df['study_number'] == study]
                        if not study_row.empty:
                            study_row = study_row.drop_duplicates(subset=['study_number'], keep='first')
                            ctn_actual = study_row['study_ctn_actual_date'].iloc[0] if 'study_ctn_actual_date' in study_row.columns else pd.NaT
                            ctn_plan = study_row['study_ctn_plan_date'].iloc[0] if 'study_ctn_plan_date' in study_row.columns else pd.NaT
                            ctn_base = pd.to_datetime(ctn_actual) if pd.notna(ctn_actual) else (pd.to_datetime(ctn_plan) if pd.notna(ctn_plan) else None)
                            
                            if ctn_base is not None:
                                now = pd.Timestamp.now()
                                target = ctn_base  # threshold=0, target=ctn_base
                                color = get_status_color(actual_date, plan_date, target, now)
                                
                                if pd.notna(actual_date):
                                    weeks_str, _ = week_diff_str(actual_date, ctn_base, threshold=0, reverse=False)
                                    date_color = '#222'
                                    weeks_color = 'red' if color == COLOR_RED else '#888'
                                    return status_light(color) + f"<span style='color:{date_color};font-weight:bold'>A:{safe_date_str(actual_date)} (<span style='color:{weeks_color}'>{weeks_str}</span>)</span>"
                                elif pd.notna(plan_date):
                                    weeks_str, _ = week_diff_str(plan_date, ctn_base, threshold=0, reverse=False)
                                    date_color = 'red' if plan_date < now else '#1976d2'
                                    weeks_color = 'red' if color == COLOR_RED else '#888'
                                    return status_light(color) + f"<span style='color:{date_color};font-weight:bold'>P:{safe_date_str(plan_date)} (<span style='color:{weeks_color}'>{weeks_str}</span>)</span>"
                                else:
                                    return status_light(color)
                    
                    # 原有逻辑（非EC Approval和Contract Signoff）
                    if pd.notna(actual_date):
                        date_color = '#222'  # 黑色
                        return f"<span style='color:{date_color};font-weight:bold'>A:{safe_date_str(actual_date)}</span>"
                    elif pd.notna(plan_date):
                        now = pd.Timestamp.now()
                        date_color = 'red' if plan_date < now else '#1976d2'  # 红色或蓝色
                        return f"<span style='color:{date_color};font-weight:bold'>P:{safe_date_str(plan_date)}</span>"
                    else:
                        return ""
                
                # 各日期字段
                site_package = format_date_display(
                    row.get('site_package_actual_date'), 
                    row.get('site_package_plan_date')
                )
                gcp_acceptance = format_date_display(
                    row.get('site_gcp_actual_date'), 
                    row.get('site_gcp_plan_date')
                )
                ec_submission = format_date_display(
                    row.get('ec_sub_actual_date'), 
                    row.get('ec_sub_plan_date')
                )
                ec_meeting = format_date_display(
                    row.get('ec_meeting_actual_date'), 
                    row.get('ec_meeting_plan_date')
                )
                ec_approval = format_date_display(
                    row.get('ec_approval_actual_date'), 
                    row.get('ec_approval_plan_date'),
                    study=study_no,
                    is_ec_approval=True
                )
                contract_gcp_review = format_date_display(
                    row.get('draft_contract_gcp_review_actual_date'), 
                    row.get('draft_contract_gcp_review_plan_date')
                )
                contract_negotiation = format_date_display(
                    row.get('main_contract_neg_comp_actual_date'), 
                    row.get('main_contract_neg_comp_plan_date')
                )
                contract_signoff = format_date_display(
                    row.get('contract_signoff_actual_date'), 
                    row.get('contract_signoff_plan_date'),
                    study=study_no,
                    is_contract_signoff=True
                )
                comm_ltr_sent = format_date_display(
                    row.get('comm_ltr_sent_actual_date'), 
                    row.get('comm_ltr_sent_plan_date')
                )
                comm_ltr_obtain = format_date_display(
                    row.get('comm_ltr_obt_actual_date'), 
                    row.get('comm_ltr_obt_plan_date')
                )
                site_activation = format_date_display(
                    row.get('site_sa_actual_date'), 
                    row.get('site_sa_plan_date')
                )
                
                leading_details.append({
                    'No': seq_num,
                    'TA': ta,
                    'Study': study_no,
                    'Site#': site_number,
                    'Site Name': site_name,
                    'Site Package Ready': site_package,
                    'GCP Acceptance': gcp_acceptance,
                    'EC Submission': ec_submission,
                    'EC Meeting': ec_meeting,
                    'EC Approval': ec_approval,
                    'Contract GCP Review': contract_gcp_review,
                    'Contract Neg. Compl.': contract_negotiation,
                    'Contract Signoff': contract_signoff,
                    'Commt. Ltr Sent': comm_ltr_sent,
                    'Commt. Ltr Obtain': comm_ltr_obtain,
                    'SA': site_activation
                })
            
            # 转为DataFrame
            leading_details_df = pd.DataFrame(leading_details)
            
            # 排序：按study CTN日期升序排列
            def get_ctn_sort_val_for_leading(row):
                study = row['Study']
                study_row = df[df['study_number'] == study]
                if study_row is not None and not study_row.empty:
                    study_row = study_row.drop_duplicates(subset=['study_number'], keep='first')
                    ctn_actual = study_row['study_ctn_actual_date'].iloc[0] if study_row is not None and not study_row.empty and 'study_ctn_actual_date' in study_row.columns else pd.NaT
                    ctn_plan = study_row['study_ctn_plan_date'].iloc[0] if study_row is not None and not study_row.empty and 'study_ctn_plan_date' in study_row.columns else pd.NaT
                    if pd.notna(ctn_actual):
                        return pd.to_datetime(ctn_actual, errors='coerce')
                    elif pd.notna(ctn_plan):
                        return pd.to_datetime(ctn_plan, errors='coerce')
                return pd.NaT
            
            leading_details_df['ctn_sort'] = leading_details_df.apply(get_ctn_sort_val_for_leading, axis=1)
            leading_details_df = leading_details_df.sort_values('ctn_sort', ascending=True, na_position='last').reset_index(drop=True)
            leading_details_df['No'] = range(1, len(leading_details_df) + 1)
            leading_details_df = leading_details_df.drop(columns=['ctn_sort'])
            
            # 应用筛选器（与Study Details表格联动）
            if 'filtered_studies' in locals() and filtered_studies:
                leading_details_df = leading_details_df[leading_details_df['Study'].isin(filtered_studies)].copy()
                leading_details_df['No'] = range(1, len(leading_details_df) + 1)
            
            # 渲染表格（优化列宽）
            def render_leading_site_table(df):
                # 定义列宽
                column_widths = {
                    'No': '60px',
                    'TA': '80px',
                    'Study': '100px',
                    'Site#': '60px',
                    'Site Name': '220px',
                    'Site Package Ready': '180px',
                    'GCP Acceptance': '180px',
                    'EC Submission': '180px',
                    'EC Meeting': '180px',
                    'EC Approval': '180px',
                    'Contract GCP Review': '180px',
                    'Contract Neg. Compl.': '180px',
                    'Contract Signoff': '180px',
                    'Commt. Ltr Sent': '180px',
                    'Commt. Ltr Obtain': '180px',
                    'SA': '180px'
                }
                
                # 前5列固定
                fixed_columns = ['No', 'TA', 'Study', 'Site#', 'Site Name']
                fixed_bg = '#fff'
                
                # 构建表头
                columns = list(df.columns)
                new_headers = []
                left_offset = 0
                for idx, col in enumerate(columns):
                    th_style = (
                        f'border:1px solid #ccc;border-bottom:2px solid #ccc;padding:4px 8px;'
                        f'background:#e6f4ea;text-align:center;white-space:nowrap;overflow:hidden;'
                        f'text-overflow:ellipsis;width:{column_widths.get(col, "120px")};'
                        f'max-width:{column_widths.get(col, "120px")};vertical-align:middle;'
                    )
                    if col in fixed_columns:
                        th_style += (
                            f'position:sticky;top:0;left:{left_offset}px;z-index:20;'
                            f'background:#e6f4ea;box-shadow:2px 0 0 #ccc;'
                        )
                        left_offset += int(column_widths[col][:-2])
                    else:
                        th_style += 'position:sticky;top:0;z-index:10;'
                    new_headers.append(f'<th style="{th_style}">{col}</th>')
                
                html = '<div style="overflow-y:auto; max-height:480px; width:100%; border-top:2px solid #ccc; border-bottom:2px solid #ccc;">'
                html += '<table style="width:100%;border-collapse:separate;border-spacing:0;table-layout:fixed;">'
                html += '<thead><tr>' + ''.join(new_headers) + '</tr></thead><tbody>'
                
                n_rows = len(df)
                for row_idx, (_, row) in enumerate(df.iterrows()):
                    tr_style = ''
                    if row_idx == n_rows - 1:
                        tr_style += 'border-bottom:2px solid #ccc;'
                    html += f'<tr style="{tr_style}">'
                    
                    left_offset_td = 0
                    for col_idx, (col, cell) in enumerate(zip(df.columns, row)):
                        style = f"border:1px solid #ccc;padding:4px 8px;text-align:center;width:{column_widths.get(col, '120px')};word-break:break-all;white-space:pre-line;max-height:120px;overflow-y:auto;vertical-align:middle;background:{fixed_bg};"
                        
                        if col in fixed_columns:
                            style += f'position:sticky;left:{left_offset_td}px;z-index:5;background:{fixed_bg};box-shadow:2px 0 0 #ccc;'
                            left_offset_td += int(column_widths[col][:-2])
                        else:
                            style += 'z-index:1;'
                        
                        if col == 'TA':
                            html += f'<td style="{style}font-weight:bold;white-space:normal;word-break:break-word;">{cell}</td>'
                        elif col in ['Study', 'Site Name']:
                            html += f'<td style="{style}font-weight:bold;white-space:nowrap;">{cell}</td>'
                        elif col == 'Site Name':
                            html += f'<td style="{style}white-space:normal;word-wrap:break-word;">{cell}</td>'
                        else:
                            html += f'<td style="{style}white-space:nowrap;">{cell}</td>'
                    html += '</tr>'
                html += '</tbody></table></div>'
                return html
            
            st.markdown(render_leading_site_table(leading_details_df), unsafe_allow_html=True)
        else:
            st.markdown('<div class="card-content">没有找到Leading Site数据</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="card-content">请上传包含 leading_site_or_not 字段的CSV</div>', unsafe_allow_html=True)
with tabs[1]:
    if df is not None:
        # 获取CSV中的study numbers
        study_numbers = df['study_number'].unique().tolist()
        # 从数据库获取HGRAC数据
        hgrac_df = get_hgrac_data(study_numbers)
        
        if not hgrac_df.empty:
            # 生成HGRAC表格数据
            hgrac_details = []
            for idx, row in hgrac_df.iterrows():
                # 序号 - 将在排序后重新赋值
                seq_num = idx + 1
                
                # 基本信息
                ta = row.get('ta', '')
                study = row.get('study_number', '')
                
                # CTN日期处理
                ctn_actual = row.get('ctn_actual_date')
                ctn_plan = row.get('ctn_plan_date')
                if pd.notna(ctn_actual):
                    ctn_display = f"<span style='color:#222;font-weight:bold'>A:{safe_date_str(ctn_actual)}</span>"
                elif pd.notna(ctn_plan):
                    now = pd.Timestamp.now()
                    date_color = 'red' if ctn_plan < now else '#1976d2'
                    ctn_display = f"<span style='color:{date_color};font-weight:bold'>P:{safe_date_str(ctn_plan)}</span>"
                else:
                    ctn_display = ""
                
                # 审批类型
                approval_type = row.get('filling_or_approval', '')
                
                # Leading EC Approval
                leading_ec_approval = row.get('leading_site_ec_approval_actual_date')
                if pd.notna(leading_ec_approval):
                    leading_ec_display = f"<span style='color:#222;font-weight:bold'>{safe_date_str(leading_ec_approval)}</span>"
                else:
                    leading_ec_display = ""
                
                # Leading Contract
                leading_contract = row.get('leading_site_contract_signoff_actual_date')
                if pd.notna(leading_contract):
                    leading_contract_display = f"<span style='color:#222;font-weight:bold'>{safe_date_str(leading_contract)}</span>"
                else:
                    leading_contract_display = ""
                
                # 申请书定稿
                application_final = row.get('application_final_date')
                if pd.notna(application_final):
                    application_final_display = f"<span style='color:#222;font-weight:bold'>{safe_date_str(application_final)}</span>"
                else:
                    application_final_display = ""
                
                # 线上递交
                first_science = row.get('first_science_date')
                if pd.notna(first_science):
                    first_science_display = f"<span style='color:#222;font-weight:bold'>{safe_date_str(first_science)}</span>"
                else:
                    first_science_display = ""
                
                # 受理日期
                official_date = row.get('official_date')
                if pd.notna(official_date):
                    official_display = f"<span style='color:#222;font-weight:bold'>{safe_date_str(official_date)}</span>"
                else:
                    official_display = ""
                
                # 批准 - 优先取public_date，如果为空则取publish_date
                public_date = row.get('public_date')
                publish_date = row.get('publish_date')
                approval_date = public_date if pd.notna(public_date) else publish_date
                if pd.notna(approval_date):
                    approval_display = f"<span style='color:#222;font-weight:bold'>{safe_date_str(approval_date)}</span>"
                else:
                    approval_display = ""
                
                hgrac_details.append({
                    'No': seq_num,
                    'TA': ta,
                    'Study': study,
                    'CTN': ctn_display,
                    '审批类型': approval_type,
                    'Leading EC Approval': leading_ec_display,
                    'Leading Contract': leading_contract_display,
                    '申请书定稿': application_final_display,
                    '线上递交': first_science_display,
                    '受理日期': official_display,
                    '批准': approval_display
                })
            
            # 转为DataFrame
            hgrac_details_df = pd.DataFrame(hgrac_details)
            
            # 排序：按CTN日期升序排列
            def get_ctn_sort_val_for_hgrac(row):
                study = row['Study']
                study_row = hgrac_df[hgrac_df['study_number'] == study]
                if study_row is not None and not study_row.empty:
                    ctn_actual = study_row['ctn_actual_date'].iloc[0] if 'ctn_actual_date' in study_row.columns else pd.NaT
                    ctn_plan = study_row['ctn_plan_date'].iloc[0] if 'ctn_plan_date' in study_row.columns else pd.NaT
                    if pd.notna(ctn_actual):
                        return pd.to_datetime(ctn_actual, errors='coerce')
                    elif pd.notna(ctn_plan):
                        return pd.to_datetime(ctn_plan, errors='coerce')
                return pd.NaT
            
            hgrac_details_df['ctn_sort'] = hgrac_details_df.apply(get_ctn_sort_val_for_hgrac, axis=1)
            hgrac_details_df = hgrac_details_df.sort_values('ctn_sort', ascending=True, na_position='last').reset_index(drop=True)
            hgrac_details_df['No'] = range(1, len(hgrac_details_df) + 1)
            hgrac_details_df = hgrac_details_df.drop(columns=['ctn_sort'])
            
            # 应用筛选器（与Study Details表格联动）
            if 'filtered_studies' in locals() and filtered_studies:
                hgrac_details_df = hgrac_details_df[hgrac_details_df['Study'].isin(filtered_studies)].copy()
                hgrac_details_df['No'] = range(1, len(hgrac_details_df) + 1)
            
            # 渲染HGRAC表格
            def render_hgrac_table(df):
                # 定义列宽
                column_widths = {
                    'No': '60px',
                    'TA': '80px',
                    'Study': '100px',
                    'CTN': '120px',
                    '审批类型': '100px',
                    'Leading EC Approval': '160px',
                    'Leading Contract': '160px',
                    '申请书定稿': '120px',
                    '线上递交': '120px',
                    '受理日期': '120px',
                    '批准': '120px'
                }
                
                html = '<div style="overflow-x:auto;width:100%;">'
                html += '<table style="width:100%;border-collapse:collapse;table-layout:fixed;">'
                html += '<tr>' + ''.join([f'<th style="border:1px solid #ccc;padding:4px 8px;background:#f7f7f7;text-align:center;font-weight:bold;white-space:nowrap;width:{column_widths.get(col, "120px")};">{col}</th>' for col in df.columns]) + '</tr>'
                for _, row in df.iterrows():
                    html += '<tr>'
                    for col, cell in zip(df.columns, row):
                        if col in ['TA', 'Study']:
                            html += f'<td style="border:1px solid #ccc;padding:4px 8px;text-align:center;font-weight:bold;white-space:nowrap;width:{column_widths.get(col, "120px")};">{cell}</td>'
                        else:
                            html += f'<td style="border:1px solid #ccc;padding:4px 8px;text-align:center;white-space:nowrap;width:{column_widths.get(col, "120px")};">{cell}</td>'
                    html += '</tr>'
                html += '</table></div>'
                return html
            
            st.markdown(render_hgrac_table(hgrac_details_df), unsafe_allow_html=True)
        else:
            st.markdown('<div class="card-content">没有找到HGRAC数据</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="card-content">请先上传CSV文件以获取Study信息</div>', unsafe_allow_html=True)
with tabs[2]:
    st.write("(IMP内容待补充)")

st.markdown("---")
st.info("💡 卡片已创建完成，请告诉我每个卡片需要展示的内容！") 