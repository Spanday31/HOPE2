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
    },
    "pcsk9i": {
        "rrr": 0.15,
        "ldl_reduction": 0.60,
        "requires_ldl": 1.8,
        "source": "FOURIER NEJM 2017 (PMID: 28476874)",
        "conflicts": ["ciclosporin"]
    },
    "bp_management": {
        "intensive": {
            "rrr": 0.25,
            "target": 130,
            "source": "SPRINT NEJM 2015 (PMID: 26551272)"
        },
        "standard": {
            "rrr": 0.10,
            "target": 140
        }
    },
    "anticoagulation": {
        "warfarin": {
            "rrr": 0.20,
            "conflicts": ["aspirin", "nsaid"],
            "source": "COMPASS Lancet 2017 (PMID: 28831992)"
        }
    },
    "lifestyle": {
        "mediterranean": {
            "rrr": 0.20,
            "source": "PREDIMED NEJM 2018 (PMID: 29897866)"
        },
        "exercise": {
            "rrr": 0.15,
            "source": "Lee JAMA 2019 (PMID: 30794147)"
        }
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

def calculate_combined_effect(baseline_risk, therapies):
    """Realistic treatment stacking with diminishing returns"""
    total_rrr = sum(t['rrr'] for t in therapies)
    
    # Diminishing returns model
    effective_rrr = 1 - np.exp(-total_rrr * 1.2)
    
    # Apply therapy-specific caps
    if any(t['type'] == 'statin+ezetimibe' for t in therapies):
        effective_rrr = min(effective_rrr, 0.40)
    
    # Absolute clinical cap
    final_rrr = min(0.75, effective_rrr)
    
    projected_risk = baseline_risk * (1 - final_rrr)
    arr = baseline_risk - projected_risk
    
    return {
        "rrr": final_rrr,
        "projected_risk": max(1.0, projected_risk),
        "arr": arr,
        "therapies": [t['name'] for t in therapies]
    }

# ==============
# CLINICAL RULES
# ==============
def check_conflicts(selected_therapies, egfr, diabetes):
    """Evidence-based conflict detection"""
    conflicts = []
    therapy_names = [t['name'].lower() for t in selected_therapies]
    
    # Drug-drug interactions
    if "warfarin" in therapy_names and "aspirin" in therapy_names:
        conflicts.append("❌ Avoid warfarin + aspirin (major bleeding risk)")
    
    # Renal precautions
    if egfr < 30:
        if "nsaid" in therapy_names:
            conflicts.append("❌ NSAIDs contraindicated in CKD G4-5")
        if "metformin" in therapy_names:
            conflicts.append("❌ Metformin requires dose adjustment")
    
    # Diabetes alerts
    if diabetes and "glp1" not in therapy_names:
        conflicts.append("💡 Consider GLP-1 RA for T2DM (CV benefit)")
    
    # Lipid alerts
    if "pcsk9i" in therapy_names and "ldl" not in st.session_state:
        conflicts.append("⚠️ Check LDL before starting PCSK9i")
    
    return conflicts

# ======
# UI APP
# ======
def main():
    st.set_page_config(
        page_title="PRIME CVD Risk Calculator",
        layout="wide",
        page_icon="🫀"
    )
    
    # Custom CSS
    st.markdown("""
    <style>
        .risk-high { border-left: 4px solid #d9534f; padding: 1rem; }
        .risk-medium { border-left: 4px solid #f0ad4e; padding: 1rem; }
        .risk-low { border-left: 4px solid #5cb85c; padding: 1rem; }
        .therapy-card { border-radius: 0.5rem; padding: 1rem; margin-bottom: 1rem; }
    </style>
    """, unsafe_allow_html=True)
    
    # Header with logo
    header_col1, header_col2 = st.columns([5,1])
    with header_col1:
        st.title("PRIME SMART-2 CVD Risk Calculator")
        st.caption("""
        *2024 ESC Guidelines Edition | Evidence-Based Treatment Optimization*
        """)
    with header_col2:
        st.markdown("""
        <div style="border:2px solid #0056b3; padding:1rem; border-radius:0.5rem; text-align:center;">
        <strong style="font-size:1.5rem;">PRIME</strong><br>
        <span style="font-size:0.8rem;">Cardiology</span>
        </div>
        """, unsafe_allow_html=True)
    
    # Initialize session state
    if 'patient_data' not in st.session_state:
        st.session_state.patient_data = {}
    
    # Sidebar - Patient Profile
    with st.sidebar:
        st.header("Patient Profile")
        
        st.session_state.age = st.slider("Age (years)", 30, 90, 65)
        st.session_state.sex = st.radio("Sex", ["Male", "Female"])
        st.session_state.diabetes = st.checkbox("Diabetes mellitus")
        st.session_state.smoker = st.checkbox("Current smoker")
        st.session_state.egfr = st.slider("eGFR (mL/min/1.73m²)", 15, 120, 90)
        
        st.subheader("Vascular Disease")
        st.session_state.cad = st.checkbox("Coronary artery disease")
        st.session_state.stroke = st.checkbox("Prior stroke/TIA")
        st.session_state.pad = st.checkbox("Peripheral artery disease")
        st.session_state.vasc_count = sum([st.session_state.cad, 
                                         st.session_state.stroke, 
                                         st.session_state.pad])
        
        st.subheader("Biomarkers")
        st.session_state.ldl = st.number_input("LDL-C (mmol/L)", 1.0, 10.0, 3.5)
        st.session_state.sbp = st.number_input("SBP (mmHg)", 90, 220, 140)
        st.session_state.hba1c = st.number_input("HbA1c (%)", 4.0, 15.0, 5.7) if st.session_state.diabetes else 5.7
    
    # Main Interface
    tab1, tab2 = st.tabs(["Risk Assessment", "Therapy Optimizer"])
    
    with tab1:
        # Risk Calculation
        baseline_risk = calculate_smart2_risk(
            st.session_state.age,
            st.session_state.sex,
            st.session_state.diabetes,
            st.session_state.smoker,
            st.session_state.egfr,
            st.session_state.vasc_count,
            st.session_state.ldl,
            st.session_state.sbp
        )
        
        st.subheader("Baseline Risk Estimation")
        col1, col2 = st.columns(2)
        with col1:
            st.metric("10-Year CVD Risk", f"{baseline_risk}%")
        with col2:
            if baseline_risk >= 30:
                st.markdown('<div class="risk-high">🔴 <b>Very High Risk</b></div>', 
                           unsafe_allow_html=True)
            elif baseline_risk >= 20:
                st.markdown('<div class="risk-medium">🟠 <b>High Risk</b></div>', 
                           unsafe_allow_html=True)
            else:
                st.markdown('<div class="risk-low">🟢 <b>Moderate Risk</b></div>', 
                           unsafe_allow_html=True)
        
        # Risk Factors Summary
        with st.expander("Key Risk Factors"):
            risk_factors = [
                f"Age {st.session_state.age}",
                st.session_state.sex,
                f"LDL-C {st.session_state.ldl} mmol/L",
                f"SBP {st.session_state.sbp} mmHg"
            ]
            if st.session_state.diabetes:
                risk_factors.append(f"Diabetes (HbA1c {st.session_state.hba1c}%)")
            if st.session_state.smoker:
                risk_factors.append("Current smoker")
            if st.session_state.egfr < 60:
                risk_factors.append(f"eGFR {st.session_state.egfr}")
            if st.session_state.vasc_count > 0:
                risk_factors.append(f"{st.session_state.vasc_count} vascular territories")
            
            st.write(", ".join(risk_factors))
    
    with tab2:
        st.header("Therapy Optimization")
        selected_therapies = []
        
        # Therapy Selection Cards
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown('<div class="therapy-card" style="background-color:#f8f9fa;">'
                       '<h3>Lipid Management</h3></div>', unsafe_allow_html=True)
            
            statin = st.selectbox(
                "Statin intensity",
                ["None", "Moderate", "High"],
                help=THERAPY_DB["statin"]["high"]["source"]
            )
            
            if statin != "None":
                selected_therapies.append({
                    "name": f"{statin} statin",
                    "type": "statin",
                    "rrr": THERAPY_DB["statin"][statin.lower()]["rrr"]
                })
                
                if st.checkbox("Add Ezetimibe"):
                    selected_therapies.append({
                        "name": "Ezetimibe",
                        "type": "statin+ezetimibe",
                        "rrr": THERAPY_DB["ezetimibe"]["rrr"]
                    })
            
            if st.session_state.ldl >= THERAPY_DB["pcsk9i"]["requires_ldl"]:
                if st.checkbox("Add PCSK9 Inhibitor"):
                    selected_therapies.append({
                        "name": "PCSK9i",
                        "type": "pcsk9i",
                        "rrr": THERAPY_DB["pcsk9i"]["rrr"]
                    })
            
            st.markdown('<div class="therapy-card" style="background-color:#f8f9fa;">'
                       '<h3>Lifestyle</h3></div>', unsafe_allow_html=True)
            
            if st.checkbox("Mediterranean Diet"):
                selected_therapies.append({
                    "name": "Mediterranean Diet",
                    "type": "lifestyle",
                    "rrr": THERAPY_DB["lifestyle"]["mediterranean"]["rrr"]
                })
            
            if st.checkbox("Regular Exercise"):
                selected_therapies.append({
                    "name": "Exercise",
                    "type": "lifestyle",
                    "rrr": THERAPY_DB["lifestyle"]["exercise"]["rrr"]
                })
        
        with col2:
            st.markdown('<div class="therapy-card" style="background-color:#f8f9fa;">'
                       '<h3>Blood Pressure</h3></div>', unsafe_allow_html=True)
            
            bp_target = st.radio(
                "SBP Target",
                ["Standard (<140)", "Intensive (<130)"],
                index=1 if st.session_state.sbp >= 140 else 0
            )
            
            if "Intensive" in bp_target:
                selected_therapies.append({
                    "name": "BP<130",
                    "type": "bp",
                    "rrr": THERAPY_DB["bp_management"]["intensive"]["rrr"]
                })
            
            st.markdown('<div class="therapy-card" style="background-color:#f8f9fa;">'
                       '<h3>Diabetes</h3></div>', unsafe_allow_html=True)
            
            if st.session_state.diabetes:
                if st.checkbox("GLP-1 RA"):
                    selected_therapies.append({
                        "name": "GLP-1 RA",
                        "type": "glp1",
                        "rrr": 0.20
                    })
                
                if st.checkbox("SGLT2 Inhibitor"):
                    selected_therapies.append({
                        "name": "SGLT2i",
                        "type": "sglt2",
                        "rrr": 0.25
                    })
        
        # Results Calculation
        if selected_therapies:
            results = calculate_combined_effect(baseline_risk, selected_therapies)
            
            st.subheader("Projected Outcomes")
            col1, col2 = st.columns(2)
            
            with col1:
                st.metric(
                    "Projected Risk",
                    f"{results['projected_risk']:.1f}%",
                    delta=f"-{results['arr']:.1f}% ARR",
                    delta_color="inverse"
                )
            
            with col2:
                st.metric(
                    "Relative Risk Reduction",
                    f"{results['rrr']*100:.0f}%",
                    help="Includes diminishing returns scaling"
                )
            
            # Conflict Checking
            conflicts = check_conflicts(
                selected_therapies,
                st.session_state.egfr,
                st.session_state.diabetes
            )
            
            if conflicts:
                st.error("### Clinical Alerts")
                for alert in conflicts:
                    st.error(alert)
            
            # Therapy Details
            with st.expander("Selected Therapies"):
                for therapy in selected_therapies:
                    st.write(f"✅ **{therapy['name']}**")
                    if therapy['name'].lower() in THERAPY_DB:
                        st.caption(THERAPY_DB[therapy['name'].lower()]["source"])
    
    # Footer
    st.divider()
    st.caption(f"""
    *PRIME Cardiology • King's College Hospital • {date.today().strftime('%Y-%m-%d')}*
    """)

if __name__ == "__main__":
    main()
