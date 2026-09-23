# 🧠 Cognivex - Multi-Modal Breast Cancer Analytics & Subtype Classification Platform

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://your-streamlit-app-link.streamlit.app)
[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)


**Cognivex** is an advanced, cloud-integrated machine learning and clinical analytics platform designed for comprehensive breast cancer patient profiling, multi-modal survival analysis, subtype classification, and model explainability using SHAP.

---
## 🚀 Live Demo
live application link: 
https://oncomap-cognivex.streamlit.app/
---

## 🔬 End-to-End Project Workflow & Architecture

### EDA & Advanced Feature Engineering
* **Dimensionality Reduction:** Cleaned and processed raw multi-omic datasets, reducing **694 initial features** down to a highly optimized and predictive subset containing **21 clinical features, 50 genes, and 18 mutated features**.
* **Feature Selection Techniques:** Applied statistical feature engineering, model-based feature selection, and ANOVA tests to isolate the most clinically relevant biomarkers.

###  Multi-Modal Survival Analysis (`lifelines`)
* **Clinical-Only Baseline:** Modeled patient survival probabilities utilizing standard clinical parameters using the `lifelines` library.
* **Multi-Modal Integration:** Evaluated shifts and performance changes in survival predictions upon combining clinical metrics with genomic and mutation profiles.

###  Subtype Classification Pipeline
Trained and benchmarked multiple state-of-the-art machine learning algorithms for robust breast cancer subtype classification:
* **Logistic Regression**
* **Random Forest**
* **XGBoost**
* **Support Vector Machines (SVM)**

### Cloud Database Integration
* Securely connected with **Azure Cosmos DB** to dynamically fetch, manage, and store patient records and analytical insights in real time.

###  Patient-Centric Predictive Insights
* Generates granular, individual-level predictions for both patient survival probabilities and molecular subtypes through an intuitive interface.

### Explainablity with SHAP
* Integrated **SHAP (SHapley Additive exPlanations)** to ensure clinical transparency, utilizing:
  * **Bar Plots** for global feature importance.
  * **Decision Plots** for multi-feature pathway evaluations.
  * **Force Plots** for individualized patient prediction breakdowns.

---


## 🛠️ Tech Stack & Libraries
* **Frontend & UI:** Streamlit
* **Survival Analysis:** `lifelines`
* **Machine Learning & Modeling:** Scikit-Learn(Logistic Regression, Random Forest, SVM), XGBoost, Joblib
* **Explainable AI:** SHAP
* **Cloud Infrastructure:** Azure Cosmos DB (`azure-cosmos`)
* **Environment/Config:** Python-Dotenv, Streamlit Secrets (TOML)

---

## ⚙️ Installation & Local Setup

1. **Clone the repository:**
   ```bash
   git clone [https://github.com/HIMA6768/Cognivex.git](https://github.com/HIMA6768/Cognivex.git)
   cd Cognivex
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Environment Secrets:**
   Setup Streamlit Cloud Secrets (TOML format) or a `.env` file locally:
   ```toml
   URL = "your_azure_cosmos_url"
   KEY = "your_azure_cosmos_key"
   database = "breastcancer_DB"
   container = "patient_details"
   ```

4. **Run the application locally:**
   ```bash
   streamlit run app.py
   ```

---
## 👥 Contributors
* Sajal Kumar
*  Himadri Ghosh
* Anay Mishra
* Ajiti Kumari Shaw
* Saurav Kumar
* Siddharth Thakur


