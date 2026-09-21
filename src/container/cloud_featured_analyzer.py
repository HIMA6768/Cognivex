import asyncio
import sys

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import shap
from .analyzer_model import analyze
from .fetch_data import fetch_all_id, fetch_data_by_id

def render_feature() -> None:
    st.markdown("""
        <style>
            .main { background-color: #0e1117; }
            h1 { color: #00f2fe; font-weight: 800;  }
            .card-heading {
                background-color: #2563eb;
                color: #ffffff;
                padding: 10px 15px;
                border-radius: 8px 8px 0 0;
                font-weight: 700;
                font-size: 1.1rem;
            }
            .light-card {
                background: #ffffff;
                border: 1px solid #cbd5e1;
                padding: 20px;
                border-radius: 12px;
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
                margin-bottom: 20px;
                color: #000000;
            }
            .summary-card {
                background: #f8fafc;
                border: 1px solid #3b82f6;
                padding: 25px;
                border-radius: 16px;
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
                margin-top: 20px;
                margin-bottom: 30px;
                color: #000000;
            }
            .metric-card {
                background: #ffffff;
                border: 1px solid #0284c7;
                padding: 20px;
                border-radius: 12px;
                box-shadow: 0 4px 10px rgba(0, 0, 0, 0.08);
                text-align: center;
                color: #000000;
            }
            .graph-desc {
                color: #1e293b;
                font-size: 0.9rem;
                margin-top: 10px;
                line-height: 1.4;
            }
            p, span, label, li {
                color: #000000;
            }
        </style>
    """, unsafe_allow_html=True)

    st.markdown("<h1 style='text-align: center;'> Subtype Classification</h1>", unsafe_allow_html=True)
    st.markdown("---")

    # Session State Initialization
    if "use_cosmos" not in st.session_state:
        st.session_state.use_cosmos = False
    if "cosmos_ep" not in st.session_state:
        st.session_state.cosmos_ep = ""
    if "cosmos_key" not in st.session_state:
        st.session_state.cosmos_key = ""
    if "cosmos_db" not in st.session_state:
        st.session_state.cosmos_db = "CancerDB"
    if "cosmos_container" not in st.session_state:
        st.session_state.cosmos_container = "Patients"
    if "selected_patient_id" not in st.session_state:
        st.session_state.selected_patient_id = None
    if "fetched_patient_data" not in st.session_state:
        st.session_state.fetched_patient_data = None
    if "db_error_msg" not in st.session_state:
        st.session_state.db_error_msg = None

    # Top Row: Cloud & Database Setup Expander
    with st.expander("☁️ Cloud Connector & Database Configuration", expanded=not st.session_state.get("use_cosmos", False)):
        top_col1, top_col2 = st.columns([1, 2])
        with top_col1:
            st.markdown("#### Default Database")
            if st.button("🔌 Connect Default DB", use_container_width=True):
                st.session_state.use_cosmos = False
                st.session_state.selected_patient_id = None
                st.session_state.fetched_patient_data = None
                st.session_state.db_error_msg = None
                st.rerun()
        with top_col2:
            st.markdown("#### External Cloud (Cosmos DB)")
            with st.form("cosmos_form"):
                cc1, cc2 = st.columns(2)
                with cc1:
                    cosmos_endpoint = st.text_input("Endpoint URL", value=st.session_state.cosmos_ep, key="input_cosmos_ep")
                    cosmos_db = st.text_input("Database Name", value=st.session_state.cosmos_db, key="input_cosmos_db")
                with cc2:
                    cosmos_key = st.text_input("Master Key", value=st.session_state.cosmos_key, type="password", key="input_cosmos_key")
                    cosmos_container = st.text_input("Container Name", value=st.session_state.cosmos_container, key="input_cosmos_container")
                
                connect_cosmos = st.form_submit_button("Connect & Sync External DB", use_container_width=True)

            if connect_cosmos:
                if not cosmos_endpoint or not cosmos_key:
                    st.warning("Endpoint URL ebong Master Key din.")
                    st.session_state.use_cosmos = False
                else:
                    st.session_state.cosmos_ep = cosmos_endpoint
                    st.session_state.cosmos_key = cosmos_key
                    st.session_state.cosmos_db = cosmos_db
                    st.session_state.cosmos_container = cosmos_container
                    st.session_state.use_cosmos = True
                    st.session_state.selected_patient_id = None
                    st.session_state.fetched_patient_data = None
                    st.session_state.db_error_msg = None
                    st.rerun()

    def get_all_patient_ids():
        if st.session_state.get("use_cosmos", False):
            try:
                res = fetch_all_id(
                    url=st.session_state.cosmos_ep,
                    key=st.session_state.cosmos_key,
                    database=st.session_state.cosmos_db,
                    container=st.session_state.cosmos_container
                )
                if isinstance(res, list):
                    return res
                raise ValueError(f"Invalid response from external cloud: {res}")
            except Exception as e:
                st.session_state.use_cosmos = False
                st.session_state.db_error_msg = f"External Cloud connection failed: {e}. Switched back to default database."
                st.rerun()

        try:
            res = fetch_all_id()
            return res if isinstance(res, list) else []
        except Exception as e:
            st.session_state.db_error_msg = f"Default DB fetch failed: {e}"
            return []

    def get_patient_data_by_id(pid):
        if st.session_state.get("use_cosmos", False):
            try:
                res = fetch_data_by_id(
                    id=pid,
                    url=st.session_state.cosmos_ep,
                    key=st.session_state.cosmos_key,
                    database=st.session_state.cosmos_db,
                    container=st.session_state.cosmos_container
                )
                if res and not isinstance(res, Exception):
                    return res
                raise ValueError("No valid data returned from external cloud.")
            except Exception as e:
                st.session_state.use_cosmos = False
                st.session_state.db_error_msg = f"External Cloud data fetch failed: {e}. Switched back to default database."
                st.rerun()

        return fetch_data_by_id(id=pid)

    with st.spinner("Fetching patient IDs..."):
        all_ids = get_all_patient_ids()
        id_list = []
        if isinstance(all_ids, list):
            for item in all_ids:
                if isinstance(item, dict) and "id" in item:
                    id_list.append(item["id"])
                elif isinstance(item, (str, int)):
                    id_list.append(str(item))

    # Main layout: Center Panel (Analysis) & Right Panel (Patient IDs)
    center_col, right_col = st.columns([3.3, 1.1])

    # Right Panel: Patient IDs List
    with right_col:
        st.markdown("### 📋 Patient IDs")
        st.markdown("---")
        with st.container(height=650):
            if id_list:
                prev_selected = st.session_state.selected_patient_id
                selected_id = st.radio(
                    "Select Patient",
                    options=id_list,
                    index=id_list.index(st.session_state.selected_patient_id) if st.session_state.selected_patient_id in id_list else None
                )
                
                if selected_id != prev_selected:
                    st.session_state.selected_patient_id = selected_id
                    st.session_state.fetched_patient_data = None

    # Center Panel: Main Analysis Panel
    with center_col:
        st.markdown("### 🔬 Patient Analysis Panel")
        st.markdown("---")

        if st.session_state.db_error_msg:
            st.error(st.session_state.db_error_msg)
            st.session_state.db_error_msg = None

        if st.session_state.get("use_cosmos", False):
            st.info("🌐 Status: **Connected to external cloud** (Cosmos DB active)")
        else:
            st.success("🟢 Status: **Connected to default cloud database**")

        if st.session_state.selected_patient_id and st.session_state.fetched_patient_data is None:
            with st.spinner(f"Loading data for Patient ID: {st.session_state.selected_patient_id}..."):
                try:
                    st.session_state.fetched_patient_data = get_patient_data_by_id(st.session_state.selected_patient_id)
                except Exception as e:
                    st.error(f"Error fetching data: {e}")

        fetched_data = st.session_state.fetched_patient_data

        if fetched_data:
            st.subheader("📄 Patient Data Rows")
            df_patient = pd.DataFrame([fetched_data]) if isinstance(fetched_data, dict) else pd.DataFrame(fetched_data)
            st.dataframe(df_patient, use_container_width=True, height=200)
            analyze_disabled = False
        else:
            st.info("👆 Please select a Patient ID from the right panel to proceed.")
            analyze_disabled = True

        analyze_btn = st.button("🚀 Analyze Patient Details", disabled=analyze_disabled, type="primary", use_container_width=True)

        if analyze_btn and fetched_data:
            with st.spinner("Running model inference and calculating SHAP values..."):
                prediction = analyze(fetched_data)
                subtype = prediction["subtype"]
                allclassprobabilities = prediction["probabilities"]
                shapdata = prediction["shapdata"]

                st.success("Analysis Completed Successfully!")
                st.markdown("---")

                res_col1, res_col2 = st.columns([1, 1.5])

                with res_col1:
                    st.markdown("### Predicted Subtype")
                    st.markdown(f"<div class='metric-card'><h2 style='color: #0284c7; margin:0;'><b>{str(subtype).upper()}</b></h2></div>", unsafe_allow_html=True)

                with res_col2:
                    st.markdown("### 📊 Subtype Probabilities (All Classes)")
                    for sub_name, prob_val in allclassprobabilities.items():
                        norm_val = float(prob_val) / 100.0 if float(prob_val) > 1.0 else float(prob_val)
                        display_pct = float(prob_val) if float(prob_val) > 1.0 else float(prob_val) * 100

                        col_name, col_bar = st.columns([1, 3])
                        with col_name:
                            st.markdown(f"<p style='margin:0; font-weight:600; color:#000000;'>{sub_name}</p>", unsafe_allow_html=True)
                        with col_bar:
                            st.progress(min(max(norm_val, 0.0), 1.0), text=f"{display_pct:.2f}%")

                shap_values_array = np.array(shapdata["values"])
                base_values = np.array(shapdata["basevalue"])
                data_values = np.array(shapdata["datavalues"])
                features = shapdata["features"]
                class_idx = 0

                st.markdown("---")
                st.markdown("### 🔍 Model Interpretability (SHAP Visualizations)")
                
                plot_col1, plot_col2 = st.columns(2)
                
                with plot_col1:
                    st.markdown('<div class="glass-card"><h4 style="margin-top:0;">Local Feature Bar Plot</h4>', unsafe_allow_html=True)
                    fig_bar, ax_bar = plt.subplots(figsize=(5, 4))
                    explanation_obj = shap.Explanation(values=shap_values_array[-1, :, class_idx], base_values=base_values[class_idx], data=data_values, feature_names=features)
                    shap.plots.bar(explanation_obj, max_display=10, show=False)
                    st.pyplot(fig_bar)
                    plt.close(fig_bar)
                    st.markdown('<p class="graph-desc"><b>Interpretation:</b> Top features and impacts.</p></div>', unsafe_allow_html=True)
                
                with plot_col2:
                    st.markdown('<div class="glass-card"><h4 style="margin-top:0;">Decision Plot</h4>', unsafe_allow_html=True)
                    fig_dec, ax_dec = plt.subplots(figsize=(5, 4))
                    shap.decision_plot(base_values[class_idx], shap_values_array[:, :, class_idx], features=features, show=False)
                    st.pyplot(fig_dec)
                    plt.close(fig_dec)
                    st.markdown('<p class="graph-desc"><b>Interpretation:</b> Cumulative feature trajectory.</p></div>', unsafe_allow_html=True)
                
                st.markdown('<div class="glass-card"><h4 style="margin-top:0;">Force Plot</h4>', unsafe_allow_html=True)
                shap.plots.force(base_values[class_idx], shap_values_array[-1, :, class_idx], data_values, feature_names=features, matplotlib=True, show=False)
                st.pyplot(plt.gcf())
                plt.clf()
                st.markdown('<p class="graph-desc"><b>Interpretation:</b> Feature push towards prediction.</p></div>', unsafe_allow_html=True)
                
                current_shap_vals = shap_values_array[-1, :, class_idx]
                top_indices = np.argsort(np.abs(current_shap_vals))[::-1][:5]
                top_genes_list = [(features[i], current_shap_vals[i]) for i in top_indices]
                
                top_genes_html = ""
                for rank, (g_name, g_val) in enumerate(top_genes_list, 1):
                    impact_type = "Positive" if g_val > 0 else "Negative"
                    color = "#00ffcc" if g_val > 0 else "#ff4d4d"
                    top_genes_html += f"<li><b>{rank}. {g_name}</b> (Impact: <span style='color:{color};'>{g_val:.3f}</span> - {impact_type})</li>"
                
                sorted_probs = sorted(allclassprobabilities.items(), key=lambda x: float(x[1]), reverse=True)
                top_sub, top_prob = sorted_probs[0]
                sec_sub, sec_prob = sorted_probs[1]
                
                summary_html = f"""
                <div class="summary-card">
                <h3 style="color: #00ffcc; margin-top:0;">📋 Executive Clinical & AI Summary Report</h3>
                <hr style="border-color: rgba(255,255,255,0.1);">
                <p><b>Patient ID:</b> {st.session_state.selected_patient_id} | <b>Primary Diagnosis:</b> {str(subtype).upper()}</p>
                <h4 style="margin-bottom: 5px; color: #ffffff;">🔑 Top 5 Most Effective Genes (SHAP Impact Analysis):</h4>
                <ul style="margin-top: 5px; color: #d1d5db;">
                {top_genes_html}
                </ul>
                <h4 style="margin-bottom: 5px; color: #ffffff; margin-top: 15px;">📊 Subtype Probability Distribution Insights:</h4>
                <p style="color: #fffff; line-height: 1.5;">
                The model predicts <b>{top_sub}</b> as the dominant subtype with a confidence score of <b>{float(top_prob):.2f}%</b>, 
                followed closely by <b>{sec_sub}</b> at <b>{float(sec_prob):.2f}%</b>. The remaining classes show minimal activation, 
                indicating a clear and decisive classification boundary for this patient sample.
                </p>
                <h4 style="margin-bottom: 5px; color: #ffffff; margin-top: 15px;">💡 Clinical Narrative:</h4>
                <p style="color: #fffff; line-height: 1.5;">
                Based on feature attributions, key regulatory genes like <b>{top_genes_list[0][0]}</b> played the most critical role 
                in steering the model's decision path. This profile suggests distinct molecular characteristics consistent with the 
                <b>{str(subtype).upper()}</b> classification tier.
                </p>
                </div>
                """
                st.markdown(summary_html, unsafe_allow_html=True)