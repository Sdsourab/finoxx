"""
modules/churn_predictor.py  ·  FinOx Suite
============================================
Customer Churn Predictor (Logistic Regression).

CACHING CHANGES (v2.0)
-----------------------
• _train() — wrapped with @st.cache_data. This method runs the full sklearn
  pipeline: StandardScaler, LogisticRegression (max_iter=500), train_test_split,
  roc_curve, and roc_auc_score — on every single Streamlit rerun, even when
  the data has not changed. This is the most expensive repeated computation in
  the entire codebase.

  CRASH PREVENTION — UnhashableTypeError guard:
  `self` is a class instance and is not hashable by Streamlit's content-based
  hasher. The fix is Streamlit's documented pattern: rename the `self` parameter
  to `_self`. Streamlit skips hashing any parameter whose name starts with an
  underscore (`_`). The call site `self._train(df)` requires NO changes —
  Python passes the instance as the first positional argument regardless of the
  parameter's name inside the function definition.

  Cache key is the CONTENT of `df`. When identical data is passed (sample data
  or same upload), the trained model is served from cache instantly. When the
  user uploads a different file, the content hash changes and the model retrains.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, roc_auc_score, roc_curve
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

from core.base_module import BaseModule
from utils.formatters import fmt, read_file


class ChurnPredictorModule(BaseModule):
    PAGE_ICON  = "💔"
    PAGE_TITLE = "Churn Predictor"

    FEATURES = ["Tenure_Months", "Monthly_Charges", "Total_Charges"]

    def render(self) -> None:
        self._page_header(
            "💔 Customer Churn Predictor (Logistic Regression)",
            "Upload CSV with Tenure_Months, Monthly_Charges, Total_Charges, Churn (0/1) "
            "— or use auto-generated sample data",
        )
        with st.container(border=True):
            df = self._load()
            st.markdown(
                f"**Dataset: {len(df):,} rows | Churn rate: {df['Churn'].mean():.1%}**"
            )
            model, scaler, m = self._train(df)

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Accuracy",   f"{m['acc']:.2%}")
            c2.metric("ROC-AUC",    f"{m['auc']:.3f}")
            c3.metric("Train Size", f"{m['n_train']:,}")
            c4.metric("Test Size",  f"{m['n_test']:,}")

            tab1, tab2 = st.tabs(["📈 ROC & Feature Importance", "🎯 Predict New Customer"])

            with tab1:
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=m["fpr"], y=m["tpr"], mode="lines",
                    name=f"AUC={m['auc']:.3f}",
                    line=dict(color="#1f77b4", width=2),
                ))
                fig.add_trace(go.Scatter(
                    x=[0, 1], y=[0, 1], mode="lines", name="Random",
                    line=dict(color="grey", dash="dash"),
                ))
                fig.update_layout(
                    title="ROC Curve", xaxis_title="False Positive Rate",
                    yaxis_title="True Positive Rate", template="plotly_white",
                )
                st.plotly_chart(fig, use_container_width=True)

                coef_df = pd.DataFrame({
                    "Feature":     self.FEATURES,
                    "Coefficient": model.coef_[0],
                }).sort_values("Coefficient")
                fig2 = px.bar(
                    coef_df, x="Coefficient", y="Feature", orientation="h",
                    color="Coefficient", color_continuous_scale="RdYlGn_r",
                    title="Feature Importance (Logistic Coefficients)",
                    template="plotly_white",
                )
                st.plotly_chart(fig2, use_container_width=True)

                self._insight_box(
                    what=(
                        f"Model accuracy: {m['acc']:.2%}, AUC: {m['auc']:.3f}. "
                        "Positive coefficients increase churn risk."
                    ),
                    recommendation=(
                        "Focus retention spend on short-tenure, high-monthly-charge customers. "
                        "AUC > 0.75 means the model is operationally useful for targeting."
                    ),
                    context_data={
                        "Model Accuracy":   f"{m['acc']:.2%}",
                        "ROC-AUC":          f"{m['auc']:.3f}",
                        "Train Samples":    m["n_train"],
                        "Test Samples":     m["n_test"],
                        "Churn Rate":       f"{df['Churn'].mean():.1%}",
                        "Feature Coeff":    dict(zip(self.FEATURES, [f"{c:.4f}" for c in model.coef_[0]])),
                    },
                )

            with tab2:
                st.subheader("Predict for a New Customer")
                c1, c2, c3 = st.columns(3)
                t   = c1.number_input("Tenure (Months)",   1, 120,  12, key="ch_t")
                mo  = c2.number_input("Monthly Charges",  500, 50_000, 5_000, key="ch_m")
                tot = c3.number_input("Total Charges",    500, 5_000_000, 60_000, key="ch_tot")
                prob = float(model.predict_proba(scaler.transform([[t, mo, tot]]))[0][1])
                icon = "🔴" if prob > 0.6 else ("🟡" if prob > 0.35 else "🟢")
                st.markdown(f"### {icon} Churn Probability: **{prob:.1%}**")
                st.progress(prob)
                if prob > 0.6:
                    st.error("HIGH RISK — Initiate retention outreach immediately.")
                elif prob > 0.35:
                    st.warning("MEDIUM RISK — Offer a loyalty incentive.")
                else:
                    st.success("LOW RISK — Customer appears satisfied.")

    def _load(self) -> pd.DataFrame:
        up = st.file_uploader(
            "Upload Churn CSV or Excel", type=["csv", "xlsx", "xls"], key="ch_up"
        )
        if up is not None:
            try:
                df = read_file(up)
                required = self.FEATURES + ["Churn"]
                if all(c in df.columns for c in required):
                    df["Churn"] = df["Churn"].astype(int)
                    return df
                st.warning(f"Missing columns. Need: {required}. Using sample data.")
            except Exception as exc:
                st.error(f"Could not read file: {exc}")

        rng     = np.random.default_rng(42)
        n       = 300
        tenure  = rng.integers(1, 73, n)
        monthly = rng.uniform(2_000, 12_000, n)
        total   = tenure * monthly * rng.uniform(0.8, 1.2, n)
        churn_p = 1 / (1 + np.exp(0.05 * tenure - 0.0001 * monthly + 2))
        churn   = (rng.random(n) < churn_p).astype(int)
        return pd.DataFrame({
            "Tenure_Months":   tenure,
            "Monthly_Charges": monthly,
            "Total_Charges":   total,
            "Churn":           churn,
        })

    @st.cache_data
    def _train(_self, df: pd.DataFrame) -> tuple:
        """
        Train the Logistic Regression churn model.

        NOTE: The first parameter is named `_self` (with a leading underscore)
        instead of `self`. This is the required Streamlit pattern for caching
        instance methods — Streamlit skips hashing any parameter whose name
        starts with `_`, preventing an UnhashableTypeError on the class instance.
        The call site `self._train(df)` does NOT need to change.

        The cache key is the content of `df`. Identical data → cached result.
        Different data (new upload) → cache miss → retrain.
        """
        X = df[_self.FEATURES]
        y = df["Churn"]
        X_tr, X_te, y_tr, y_te = train_test_split(
            X, y, test_size=0.3, random_state=42, stratify=y
        )
        sc      = StandardScaler()
        X_tr_s  = sc.fit_transform(X_tr)
        X_te_s  = sc.transform(X_te)
        model   = LogisticRegression(max_iter=500, random_state=42)
        model.fit(X_tr_s, y_tr)
        y_pred  = model.predict(X_te_s)
        y_prob  = model.predict_proba(X_te_s)[:, 1]
        fpr, tpr, _ = roc_curve(y_te, y_prob)
        return model, sc, {
            "acc":    accuracy_score(y_te, y_pred),
            "auc":    roc_auc_score(y_te, y_prob),
            "fpr":    fpr,
            "tpr":    tpr,
            "n_train": len(X_tr),
            "n_test":  len(X_te),
        }