import streamlit as st
import numpy as np
from datetime import date

# ======================
# EVIDENCE BASE (2023-24)
# ======================
THERAPY_DB = {
    "statin": {
        "moderate": {
            "rrr": 0.25,
            "ldl_reduction": 0.30,
            "source": "CTT Lancet 2010 (PMID: 21067804)"
        },
        "high": {
            "rrr": 0.35,
            "ldl_reduction": 0.50,
            "source": "TNT NEJM 2005 (PMID: 15930428)"
        }
    },
    "ezetimibe": {
        "rrr": 0.06,
        "ldl_reduction": 0.20,
        "source": "IMPROVE-IT NEJM 2015 (PMID: 26039521)",
        "max_combination_rrr": 0.40
    }
}

# =================
# CORE CALCULATIONS
# =================
def calculate_smart2_risk(age, sex, diabetes, smoker, egfr, vasc_count, ldl, sbp):
    """2023 ESC Guidelines SMART-2 Update"""
    coefficients = {
        'intercept': -8.1937,
        'age': 0.0650 if age < 70 else 0.0700,
        'female': -0.3372,
        'diabetes': 0.5200 if diabetes else 0,
        'smoker': 0.8100 if smoker else 0,
        'egfr<30': 0.9235 if egfr < 30 else 0,
        'egfr30-60': 0.5539 if 30 <= egfr < 60 else 0,
        'polyvascular': 0.6000 if vasc_count >= 2 else 0,
        'ldl': 0.2500 * (ldl - 2.5),
        'sbp': 0.0090 * (sbp - 120)
    }
    
    lp = sum(coefficients.values())
    risk_percent = 100 * (1 - np.exp(-np.exp(lp) * 10))
    return max(1.0, min(99.0, round(risk_percent, 1)))

def main():
    st.set_page_config(
        page_title="PRIME CVD Risk Calculator",
        layout="wide",
        page_icon="🫀"
    )
    
    # Header
    col1, col2 = st.columns([5,1])
    with col1:
        st.title("PRIME SMART-2 CVD Risk Calculator")
    with col2:
        st.markdown("""
        <div style="border:2px solid #0056b3; padding:1rem; border-radius:0.5rem; text-align:center;">
        <strong style="font-size:1.5rem;">PRIME</strong><br>
        <span style="font-size:0.8rem;">Cardiology</span>
        </div>
        """, unsafe_allow_html=True)
    
    # Sidebar - Patient Profile
    with st.sidebar:
        st.header("Patient Profile")
        
        # Add unique keys to all widgets
        age = st.slider("Age (years)", 30, 90, 65, key="age_slider")
        sex = st.radio("Sex", ["Male", "Female"], key="sex_radio")
        diabetes = st.checkbox("Diabetes mellitus", key="diabetes_check")
        smoker = st.checkbox("Current smoker", key="smoker_check")
        egfr = st.slider("eGFR (mL/min/1.73m²)", 15, 120, 90, key="egfr_slider")
        
        st.subheader("Vascular Disease")
        cad = st.checkbox("Coronary artery disease", key="cad_check")
        stroke = st.checkbox("Prior stroke/TIA", key="stroke_check")
        pad = st.checkbox("Peripheral artery disease", key="pad_check")
        vasc_count = sum([cad, stroke, pad])
        
        st.subheader("Biomarkers")
        ldl = st.number_input("LDL-C (mmol/L)", 1.0, 10.0, 3.5, key="ldl_input")
        sbp = st.number_input("SBP (mmHg)", 90, 220, 140, key="sbp_input")
    
    # Main Content
    tab1, tab2 = st.tabs(["Risk Assessment", "Therapy Optimizer"])
    
    with tab1:
        # Risk Calculation
        baseline_risk = calculate_smart2_risk(age, sex, diabetes, smoker, egfr, vasc_count, ldl, sbp)
        
        st.subheader("Baseline Risk Estimation")
        col1, col2 = st.columns(2)
        with col1:
            st.metric("10-Year CVD Risk", f"{baseline_risk}%", key="risk_metric")
        
        # Risk Factors Summary
        with st.expander("Key Risk Factors", key="risk_factors_expander"):
            risk_factors = [
                f"Age {age}",
                sex,
                f"LDL-C {ldl} mmol/L",
                f"SBP {sbp} mmHg"
            ]
            if diabetes:
                risk_factors.append("Diabetes")
            if smoker:
                risk_factors.append("Current smoker")
            if egfr < 60:
                risk_factors.append(f"eGFR {egfr}")
            if vasc_count > 0:
                risk_factors.append(f"{vasc_count} vascular territories")
            
            st.write(", ".join(risk_factors))
    
    with tab2:
        st.header("Therapy Optimization")
        selected_therapies = []
        
        # Therapy Selection
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### Lipid Management")
            statin = st.selectbox(
                "Statin intensity",
                ["None", "Moderate", "High"],
                key="statin_select"
            )
            
            if statin != "None":
                selected_therapies.append({
                    "name": f"{statin} statin",
                    "rrr": THERAPY_DB["statin"][statin.lower()]["rrr"]
                })
                
                if st.checkbox("Add Ezetimibe", key="ezetimibe_check"):
                    selected_therapies.append({
                        "name": "Ezetimibe",
                        "rrr": THERAPY_DB["ezetimibe"]["rrr"]
                    })
        
        # Results Calculation
        if selected_therapies:
            total_rrr = sum(t['rrr'] for t in selected_therapies)
            projected_risk = baseline_risk * (1 - min(0.75, total_rrr))  # Cap at 75% RRR
            
            st.subheader("Projected Outcomes")
            st.metric(
                "Projected Risk",
                f"{projected_risk:.1f}%",
                delta=f"-{baseline_risk - projected_risk:.1f}% ARR",
                delta_color="inverse",
                key="projected_metric"
            )
    
    # Footer
    st.divider()
    st.caption(f"""
    *PRIME Cardiology • {date.today().strftime('%Y-%m-%d')}*
    """)

if __name__ == "__main__":
    main()
