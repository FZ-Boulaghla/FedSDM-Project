
import numpy as np
import flwr as fl
from .model_autoencoder import build_autoencoder
from .config import ENCODING_DIM, BATCH_SIZE

class ECGClient(fl.client.NumPyClient):
    def __init__(self, cid: int, Xc: np.ndarray, yc: np.ndarray, input_dim: int):
        self.cid = cid
        self.Xc_norm = Xc[yc == 0]
        self.model = build_autoencoder(input_dim=input_dim, encoding_dim=ENCODING_DIM)

    def get_parameters(self, config):
        return self.model.get_weights()

    def fit(self, parameters, config):
        self.model.set_weights(parameters)
        local_epochs = int(config.get("local_epochs", 5))
        self.model.fit(self.Xc_norm, self.Xc_norm, epochs=local_epochs, batch_size=BATCH_SIZE, verbose=0)
        return self.model.get_weights(), len(self.Xc_norm), {}

    def evaluate(self, parameters, config):
        self.model.set_weights(parameters)
        loss = self.model.evaluate(self.Xc_norm, self.Xc_norm, verbose=0)
        return float(loss), len(self.Xc_norm), {"mse": float(loss)}
