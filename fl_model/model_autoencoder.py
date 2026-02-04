
import tensorflow as tf
from tensorflow.keras import layers, models, optimizers

def build_autoencoder(input_dim: int, encoding_dim: int):
    inputs = layers.Input(shape=(input_dim,), name="input_ecg")
    x = layers.Dense(128, activation='relu')(inputs)
    x = layers.Dense(96, activation='relu')(x)
    x = layers.Dense(64, activation='relu')(x)
    code = layers.Dense(encoding_dim, activation='relu', name='code')(x)
    x = layers.Dense(64, activation='relu')(code)
    x = layers.Dense(96, activation='relu')(x)
    x = layers.Dense(128, activation='relu')(x)
    outputs = layers.Dense(input_dim, activation='sigmoid', name='recon')(x)
    model = models.Model(inputs, outputs, name="autoencoder_ecg")
    model.compile(optimizer=optimizers.Adam(1e-3), loss='mse')
    return model
