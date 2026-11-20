# JAL-RAKSHAK Streamlit starter

## 1. Folder structure

Place your existing files like this:

```text
JAL-RAKSHAK/
├── app.py
├── requirements.txt
├── swq_risk/
│   ├── __init__.py
│   ├── config.py
│   ├── features.py
│   ├── inference.py
│   └── labels.py
└── models/
    ├── model_metadata.json
    ├── risk_model_cold.joblib
    └── risk_model_full.joblib
```

The `swq_risk` Python files and `models` files are your supplied existing files. Do not retrain or rename the models.

## 2. Windows setup

Open PowerShell in this folder:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

If activation is blocked in this PowerShell session:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\venv\Scripts\Activate.ps1
```

## 3. Run

```powershell
streamlit run app.py
```

## Important

The model metadata specifies NumPy 2.5.4, pandas 3.0.6 and scikit-learn 1.9.1. Use matching versions where available because joblib models can be version-sensitive.

The supplied inference module labels water-pollution risk, not human disease cases. TDS and turbidity are accepted but are explicitly not used by the current model. The app shows that warning rather than implying otherwise.
