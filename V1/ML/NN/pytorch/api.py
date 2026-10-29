"""House price API (network WITH hidden layers, Option 2): loads the PyTorch model saved by house.ipynb and serves predictions.

Run:    python api_hidden.py
Docs:   http://127.0.0.1:8000/docs      (Swagger UI: try POST /predict here)
Postman: POST http://127.0.0.1:8000/predict  with a JSON body (see the example in /docs)
"""
from pathlib import Path

import joblib
import numpy as np
import torch
import torch.nn as nn
import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel, Field

MODEL_DIR = Path(__file__).parent / "model"

# the order must be the same as the columns used for training in the notebook
FEATURES = ["sqft", "bedrooms", "bathrooms", "age", "floors", "garage", "lot_size", "city_index"]


# same network as in the notebook (the saved weights only fit this exact shape)
class HousePricePredictor(nn.Module):
    def __init__(self):
        super().__init__()
        self.network = nn.Sequential(
            nn.Linear(8, 16),
            nn.ReLU(),
            nn.Linear(16, 8),
            nn.ReLU(),
            nn.Linear(8, 4),
            nn.ReLU(),
            nn.Linear(4, 1),
        )

    def forward(self, x):
        return self.network(x)


# load once when the server starts
model = HousePricePredictor()
model.load_state_dict(torch.load(MODEL_DIR / "house_model_hidden.pt", weights_only=True))
model.eval()
x_scaler = joblib.load(MODEL_DIR / "x_scaler.pkl")
y_scaler = joblib.load(MODEL_DIR / "y_scaler.pkl")


def predict_price(house: dict) -> float:
    """house = {"sqft": 2000, "bedrooms": 3, ...}  ->  predicted price in dollars"""
    row = np.array([[house[name] for name in FEATURES]], dtype=np.float32)
    scaled = torch.from_numpy(x_scaler.transform(row).astype(np.float32))    # 1. scale like in training
    with torch.no_grad():
        out = model(scaled)                                                  # 2. model prediction
    return float(y_scaler.inverse_transform(out.numpy())[0][0])              # 3. back to dollars


class House(BaseModel):
    sqft: float = Field(..., gt=0, description="living area in square feet")
    bedrooms: int = Field(..., ge=0)
    bathrooms: int = Field(..., ge=0)
    age: int = Field(..., ge=0, description="age of the house in years")
    floors: int = Field(..., ge=1)
    garage: int = Field(..., ge=0, description="garage spaces")
    lot_size: float = Field(..., gt=0, description="lot size in sqft")
    city_index: int = Field(..., ge=0, description="city code, 0 to 9 in the training data")

    model_config = {
        "json_schema_extra": {
            "example": {"sqft": 2000, "bedrooms": 3, "bathrooms": 2, "age": 10,
                        "floors": 1, "garage": 1, "lot_size": 5000, "city_index": 4}
        }
    }


app = FastAPI(title="House Price API (hidden layers)", description="PyTorch neural network with hidden layers, served with FastAPI")


@app.get("/")
def health():
    return {"status": "ok", "message": "House price API is running. Open /docs to try it."}


@app.post("/predict")
def predict(house: House):
    return {"predicted_price": round(predict_price(house.model_dump()), 2)}


if __name__ == "__main__":
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
