
from flwr.server.strategy import FedAvg

class SaveModelFedAvg(FedAvg):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.last_aggregated_parameters = None

    def aggregate_fit(self, rnd, results, failures):
        aggregated, metrics = super().aggregate_fit(rnd, results, failures)
        self.last_aggregated_parameters = aggregated
        print(f"[Server] Aggregation finished for round {rnd}")
        return aggregated, metrics
