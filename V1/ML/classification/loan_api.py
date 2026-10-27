from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel, Field

MODEL_PATH = Path(__file__).parent / "loan.pkl"

app = FastAPI(title="Loan Approval Model")
model = joblib.load(MODEL_PATH)


class LoanApplication(BaseModel):
    no_of_dependents: int = Field(ge=0)
    education: str  # "Graduate" or "Not Graduate"
    self_employed: str  # "Yes" or "No"
    income_annum: float = Field(gt=0)
    loan_amount: float = Field(gt=0)
    loan_term: int = Field(gt=0)
    credit_score: float
    total_assets: float = Field(gt=0)


@app.get("/")
def health_check():
    return {"status": "ok"}


@app.post("/predict")
def predict(application: LoanApplication):
    features = pd.DataFrame(
        [
            {
                "no_of_dependents": application.no_of_dependents,
                "education": 1 if application.education.strip() == "Graduate" else 0,
                "self_employed": 1 if application.self_employed.strip() == "No" else 0,
                "income_annum": np.log(application.income_annum),
                "loan_amount": np.log(application.loan_amount),
                "loan_term": application.loan_term,
                "credit_score": application.credit_score,
                "total_assets": np.log(application.total_assets),
            }
        ]
    )
    approved = int(model.predict(features)[0]) == 1
    probability = float(model.predict_proba(features)[0][1])
    return {
        "loan_status": "Approved" if approved else "Rejected",
        "approval_probability": round(probability, 3),
    }


if __name__ == "__main__":
    uvicorn.run("loan_api:app", host="0.0.0.0", port=9090, reload=True)
