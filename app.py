"""Readmission follow-up planner (Streamlit).
Run from the project folder after notebooks 01-06:  streamlit run app.py
Uses only the held-out test set, so every score shown is out-of-sample.
"""
from pathlib import Path
import altair as alt
import joblib
import numpy as np
import pandas as pd
import streamlit as st

PROC, MOD = Path("data/processed"), Path("models")
TARGET, ID = "readmit_30", "patient_nbr"
WHAT_IF = ["discharge_disposition_id", "number_inpatient", "number_emergency",
           "number_outpatient", "time_in_hospital", "num_medications"]

st.set_page_config(page_title="Readmission follow-up planner", page_icon="🏥", layout="wide")


@st.cache_resource
def load_model():
    return joblib.load(MOD / "lgbm_calibrated.joblib")


@st.cache_data
def load_test():
    pred = pd.read_parquet(PROC / "test_predictions.parquet")
    df = pd.read_parquet(PROC / "model_table.parquet")
    test_ids = set(pd.read_parquet(PROC / "test_patients.parquet")[ID])
    test = df[df[ID].isin(test_ids)].reset_index(drop=True)
    if len(test) != len(pred) or not (test[ID].values == pred[ID].values).all():
        raise ValueError("Test rows don't line up with test_predictions.parquet. Rerun notebook 04.")
    test["p_risk"] = pred["p_risk"].values
    test = test.sort_values("p_risk", ascending=False, kind="stable").reset_index(drop=True)
    test["rank"] = np.arange(1, len(test) + 1)
    test["risk_percentile"] = 100 * (1 - (test["rank"] - 1) / len(test))
    return test


def policy_curve(y, cost_readmit, cost_pp, effect):
    """y must already be sorted by risk, highest first."""
    k = np.arange(1, len(y) + 1)
    prevented = effect * np.cumsum(y)
    return pd.DataFrame({"share": k / len(y), "called": k, "prevented": prevented,
                         "precision": np.cumsum(y) / k, "recall": np.cumsum(y) / y.sum(),
                         "net": prevented * cost_readmit - k * cost_pp,
                         "net_random": k * (y.mean() * effect * cost_readmit - cost_pp)})


try:
    test, model = load_test(), load_model()
except FileNotFoundError as e:
    st.error(f"Missing file: {e.filename}. Run notebooks 01 to 04 first, then start the app from the project folder.")
    st.stop()

features = [c for c in test.columns if c not in (TARGET, ID, "p_risk", "rank", "risk_percentile")]
N, y = len(test), test[TARGET].to_numpy()

# ---------- Sidebar: program assumptions ----------
st.sidebar.header("Program assumptions")
cost_readmit = st.sidebar.number_input("Cost of one readmission ($)", 1_000, 50_000, 15_000, step=500)
cost_pp = st.sidebar.number_input("Program cost per patient ($)", 10, 2_000, 200, step=10)
effect = st.sidebar.slider("Readmissions prevented among patients called (%)", 0, 50, 20) / 100
capacity = st.sidebar.slider("Share of discharges the team can call (%)", 1, 100, 10)
st.sidebar.caption(f"Break-even risk: a patient is worth calling above "
                   f"{cost_pp / max(effect * cost_readmit, 1e-9):.1%} predicted risk.")

curve = policy_curve(y, cost_readmit, cost_pp, effect)
k = max(int(round(capacity / 100 * N)), 1)
row, best = curve.iloc[k - 1], curve.loc[curve["net"].idxmax()]
scale = 1000 / N

st.title("Readmission follow-up planner")
st.write("Ranks diabetic inpatients by 30-day readmission risk and shows what a follow-up program "
         "of a given size would cost and prevent. Scores come from a calibrated LightGBM model, "
         f"shown on {N:,} held-out test encounters (UCI Diabetes 130-US Hospitals).")

plan, worklist, patient = st.tabs(["Plan the program", "Call list", "Patient detail"])

# ---------- Tab 1: plan ----------
with plan:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Patients called per 1,000 discharges", f"{row['called'] * scale:.0f}")
    c2.metric("Readmissions prevented per 1,000", f"{row['prevented'] * scale:.1f}")
    c3.metric("Net benefit per 1,000", f"${row['net'] * scale:,.0f}",
              delta=f"${(row['net'] - row['net_random']) * scale:,.0f} vs random calling")
    c4.metric("Share of all readmissions reached", f"{row['recall']:.0%}")

    if best["net"] > 0:
        st.write(f"With these assumptions, net benefit peaks when **{best['share']:.0%}** of discharges are called "
                 f"(\\${best['net'] * scale:,.0f} per 1,000). At your capacity of {capacity}%, each readmission "
                 f"prevented costs **\\${cost_pp / max(row['precision'] * effect, 1e-9):,.0f}** in program spend.")
    else:
        st.warning("With these assumptions the program costs more than it saves at every size.")

    idx = np.unique(np.linspace(0, N - 1, 200).astype(int))
    chart = pd.DataFrame({"% of discharges called": curve["share"].iloc[idx] * 100,
                          "Highest risk first (model)": curve["net"].iloc[idx] * scale,
                          "At random": curve["net_random"].iloc[idx] * scale}).set_index("% of discharges called")
    st.line_chart(chart, y_label="Net benefit per 1,000 discharges ($)", color=["#2a6f97", "#9aa5ae"])
    st.caption("Net benefit = readmissions prevented × readmission cost − patients called × program cost "
               "(payer / health-system view). The program effect is an assumption, not estimated from this data.")

# ---------- Tab 2: call list ----------
with worklist:
    show = [c for c in ["age_num", "male", "discharge_disposition_id", "number_inpatient", "number_emergency",
                        "time_in_hospital", "num_medications"] if c in test]
    calls = test.head(k)[["rank", ID, "p_risk"] + show].rename(columns={"p_risk": "predicted_risk"})
    st.write(f"Top **{k:,}** encounters ({capacity}% of discharges), highest risk first. "
             f"{calls['predicted_risk'].min():.1%} is the lowest risk on the list.")
    st.dataframe(calls.style.format({"predicted_risk": "{:.1%}"}), hide_index=True, width="stretch")
    st.download_button("Download call list (CSV)", calls.to_csv(index=False), "call_list.csv", "text/csv")

# ---------- Tab 3: patient detail ----------
with patient:
    r = st.number_input("Risk rank (1 = highest)", 1, N, 1)
    rec = test.iloc[r - 1]
    x = test.loc[[r - 1], features]
    a, b, c = st.columns(3)
    a.metric("Predicted 30-day readmission risk", f"{rec['p_risk']:.1%}")
    b.metric("Risk percentile", f"{rec['risk_percentile']:.1f}")
    c.metric("On the call list?", "Yes" if r <= k else "No")
    st.caption(f"Actual outcome in the test data: {'readmitted within 30 days' if rec[TARGET] == 1 else 'not readmitted'}.")

    left, right = st.columns(2)
    with left:
        st.subheader("What drives this score")
        try:
            lgbm = model.estimator.estimator          # CalibratedClassifierCV -> FrozenEstimator -> LGBMClassifier
            contrib = pd.Series(lgbm.predict(x, pred_contrib=True)[0][:-1], index=features)
            top = contrib.reindex(contrib.abs().sort_values(ascending=False).index).head(8)
            plot = pd.DataFrame({"feature": [f"{f} = {x.iloc[0][f]}" for f in top.index], "contribution": top.values})
            plot["direction"] = np.where(plot["contribution"] > 0, "Raises risk", "Lowers risk")
            st.altair_chart(
                alt.Chart(plot).mark_bar().encode(
                    x=alt.X("contribution:Q", title="Contribution to risk (log-odds)"),
                    y=alt.Y("feature:N", sort="-x", title=None, axis=alt.Axis(labelLimit=320)),
                    color=alt.Color("direction:N", title=None,
                                    scale=alt.Scale(domain=["Raises risk", "Lowers risk"], range=["#c1666b", "#2a6f97"])),
                    tooltip=["feature", alt.Tooltip("contribution:Q", format=".3f")]),
                width="stretch")
            st.caption("SHAP contributions from the underlying LightGBM model: the 8 features that move this score most.")
        except Exception as e:
            st.info(f"Contributions unavailable for this model ({type(e).__name__}).")

    with right:
        st.subheader("What if")
        st.write("Change a field to see how the score moves.")
        edited = x.copy()
        for f in [f for f in WHAT_IF if f in features]:
            col = test[f]
            if isinstance(col.dtype, pd.CategoricalDtype):
                cats = list(col.cat.categories)
                v = st.selectbox(f, cats, index=cats.index(x.iloc[0][f]) if x.iloc[0][f] in cats else 0, key=f"w_{f}_{r}")
                edited[f] = pd.Categorical([v], categories=col.cat.categories, ordered=col.cat.ordered)
            elif pd.api.types.is_numeric_dtype(col):
                v = st.number_input(f, int(col.min()), int(col.max()), int(x.iloc[0][f]), key=f"w_{f}_{r}")
                edited[f] = np.array([v]).astype(col.dtype)
        try:
            new = model.predict_proba(edited)[0, 1]
            st.metric("Re-scored risk", f"{new:.1%}", delta=f"{(new - rec['p_risk']) * 100:+.1f} points",
                      delta_color="inverse")
        except Exception as e:
            st.error(f"Could not re-score: {e}")
