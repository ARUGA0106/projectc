import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'  # Suppress TensorFlow logs: 0 = all, 1 = warning, 2 = error, 3 = fatal

import joblib
import numpy as np
from keras.models import load_model
from keras.losses import MeanSquaredError

# ----------------------------
# 🛠 Configuration
# ----------------------------
BASE_DIR = r'C:\tanair\projectc\model'
MODEL_PATH = os.path.join(BASE_DIR, 'lstm_multi_forecast.keras')
SCALER_PATH = os.path.join(BASE_DIR, 'pollutant_scaler.pkl')

# ----------------------------
# 🔁 Model Loader
# ----------------------------
def get_lstm_model():
    print("Looking for model at:", MODEL_PATH)
    if not os.path.exists(MODEL_PATH):
        raise FileNotFoundError(f"LSTM model not found at {MODEL_PATH}")
    return load_model(MODEL_PATH, compile=False, custom_objects={'mse': MeanSquaredError()})

# ----------------------------
# 🔁 Scaler Loader
# ----------------------------
def get_scaler():
    print("Looking for scaler at:", SCALER_PATH)
    if not os.path.exists(SCALER_PATH):
        raise FileNotFoundError(f"Scaler not found at {SCALER_PATH}")
    return joblib.load(SCALER_PATH)

# ----------------------------
# 🔮 Prediction Function
# ----------------------------
def predict_next_steps(input_sequence, model=None, scaler=None):
    """
    Predict next 3 time steps based on last 10 readings.

    Parameters:
    - input_sequence: np.array of shape (1, 10, num_features)
    - model: keras.Model (optional)
    - scaler: fitted scaler (optional)

    Returns:
    - prediction_original: np.array of shape (3, num_features)
    """
    if model is None:
        model = get_lstm_model()
    if scaler is None:
        scaler = get_scaler()

    if input_sequence.shape != (1, 10, scaler.n_features_in_):
        raise ValueError(f"Expected input shape (1, 10, {scaler.n_features_in_}), but got {input_sequence.shape}")

    # Scale input
    scaled_input = scaler.transform(input_sequence.reshape(-1, scaler.n_features_in_))
    scaled_input = scaled_input.reshape(1, 10, scaler.n_features_in_)

    # Predict
    flat_prediction = model.predict(scaled_input, verbose=0)

    # Reshape and inverse transform
    prediction = flat_prediction.reshape(3, scaler.n_features_in_)
    prediction_original = scaler.inverse_transform(prediction)

    return prediction_original
