
import numpy as np
import flwr as fl
from flwr.common import ndarrays_to_parameters, parameters_to_ndarrays

from .config import (
    CLIENTS, ROUNDS, LOCAL_EPOCHS, ENCODING_DIM,
    MODEL_KERAS, MODEL_H5, CSV_RESULTS,
)
from .preprocess import load_dataset, make_noniid_clients
from .model_autoencoder import build_autoencoder
from .client_flower import ECGClient
from .server_strategy import SaveModelFedAvg


def main():
    # 1) Load dataset
    X_train, X_test, y_train, y_test = load_dataset()
    input_dim = X_train.shape[1]

    # 2) Partition clients (non-IID)
    client_data = make_noniid_clients(X_train, y_train, CLIENTS)

    # 3) Base model + initial params
    base_model = build_autoencoder(input_dim=input_dim, encoding_dim=ENCODING_DIM)
    initial_params = ndarrays_to_parameters(base_model.get_weights())

    # 4) client_fn (Flower 1.3.0 signature)
    def client_fn(cid: str):
        cid_int = int(cid)
        Xc, yc = client_data[cid_int]
        return ECGClient(cid_int, Xc, yc, input_dim)

    # 5) Strategy
    strategy = SaveModelFedAvg(
        fraction_fit=1.0,
        min_fit_clients=CLIENTS,
        min_available_clients=CLIENTS,
        initial_parameters=initial_params,
        on_fit_config_fn=lambda rnd: {"local_epochs": LOCAL_EPOCHS},
    )

    # 6) Run FL simulation
    history = fl.simulation.start_simulation(
        client_fn=client_fn,
        num_clients=CLIENTS,
        config=fl.server.ServerConfig(num_rounds=ROUNDS),
        strategy=strategy,
    )
    print("Simulation finished.")

    # 7) Retrieve global weights and save model
    agg_ndarrays = parameters_to_ndarrays(strategy.last_aggregated_parameters)
    global_model = build_autoencoder(input_dim=input_dim, encoding_dim=ENCODING_DIM)
    global_model.set_weights(agg_ndarrays)

    global_model.save(MODEL_KERAS.as_posix())
    try:
        global_model.save(MODEL_H5.as_posix())
    except Exception as e:
        print(f"[WARN] Could not save HDF5: {e}")

    # 8) Quick test metrics (optional minimal)
    recon_test = global_model.predict(X_test, verbose=0)
    err_test   = np.mean((X_test - recon_test)**2, axis=1)

    # Note: full evaluation/plots are in evaluate_fl.py
    import pandas as pd
    pd.DataFrame({"err_test": err_test}).to_csv(CSV_RESULTS.as_posix(), index=False)
    print(f"Saved: {MODEL_KERAS}")
    print(f"Saved: {CSV_RESULTS}")


if __name__ == "__main__":
    main()