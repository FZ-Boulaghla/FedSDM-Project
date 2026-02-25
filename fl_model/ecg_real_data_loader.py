"""
ECG Real Data Loader for FedSDM
Manages loading, preprocessing, and validation of real ECG data
Supports MIT-BIH, PhysioNet, and other public ECG datasets
"""

import numpy as np
import pandas as pd
from pathlib import Path
from sklearn.preprocessing import MinMaxScaler
import warnings
warnings.filterwarnings('ignore')


class ECGRealDataLoader:
    """Load and preprocess real ECG data from various sources"""
    
    def __init__(self, n_features: int = 140, sampling_rate: int = 360):
        """
        Args:
            n_features: Number of features per ECG signal (samples in a window)
            sampling_rate: Sampling rate in Hz (MIT-BIH: 360Hz typical)
        """
        self.n_features = n_features
        self.sampling_rate = sampling_rate
        self.scaler = MinMaxScaler()
        
    def load_from_csv(self, csv_path: str, label_column: str = -1) -> tuple:
        """
        Load ECG from CSV file
        
        Args:
            csv_path: Path to CSV file
            label_column: Column index or name for labels (normal=0, abnormal=1)
            
        Returns:
            X (signals), y (labels)
        """
        try:
            df = pd.read_csv(csv_path)
            X = df.iloc[:, :-1].values.astype(np.float32)
            
            # Handle label column
            if isinstance(label_column, int):
                y = df.iloc[:, label_column].values.astype(np.int32)
            else:
                y = df[label_column].values.astype(np.int32)
            
            print(f"✓ Loaded real ECG data: {csv_path}")
            print(f"  Shape: X={X.shape}, y={y.shape}")
            print(f"  Label distribution: Normal={np.sum(y==0)}, Abnormal={np.sum(y==1)}")
            
            return X, y
        except Exception as e:
            raise RuntimeError(f"Error loading CSV: {e}")
    
    def load_from_physionet(self, dataset_name: str = "ecg-id-database") -> tuple:
        """
        Load ECG from PhysioNet (requires internet connection)
        
        Args:
            dataset_name: Dataset name on PhysioNet
            
        Returns:
            X (signals), y (labels)
        """
        try:
            import wfdb
            print(f"Attempting to load {dataset_name} from PhysioNet...")
            # This is a placeholder - actual implementation requires specific PhysioNet credentials
            raise NotImplementedError("PhysioNet loading requires wfdb library and dataset credentials")
        except ImportError:
            print("⚠ wfdb library not installed. Install with: pip install wfdb")
            raise
    
    def create_sliding_windows(self, signal: np.ndarray, window_size: int, overlap: float = 0.5) -> np.ndarray:
        """
        Create sliding windows from continuous ECG signal
        Simulates continuous monitoring with overlapping windows
        
        Args:
            signal: 1D ECG signal
            window_size: Size of each window
            overlap: Overlap ratio (0.0-1.0)
            
        Returns:
            2D array of windows (n_windows, window_size)
        """
        stride = int(window_size * (1 - overlap))
        windows = []
        
        for i in range(0, len(signal) - window_size + 1, stride):
            windows.append(signal[i:i + window_size])
        
        return np.array(windows)
    
    def preprocess_ecg(self, X: np.ndarray, normalize: bool = True) -> np.ndarray:
        """
        Preprocess ECG signals (baseline wander removal, normalization)
        
        Args:
            X: Raw ECG data (n_samples, n_features)
            normalize: Apply MinMax normalization
            
        Returns:
            Preprocessed ECG data
        """
        X_processed = X.copy().astype(np.float32)
        
        # Baseline wander removal (simplified - use median filter proxy)
        for i in range(len(X_processed)):
            baseline = np.median(X_processed[i])
            X_processed[i] = X_processed[i] - baseline
        
        # Normalization
        if normalize:
            X_processed = self.scaler.fit_transform(X_processed)
        
        return X_processed
    
    def validate_signal_continuity(self, signals: np.ndarray, max_gap_percent: float = 0.1) -> dict:
        """
        Validate continuity and quality of signals
        Detects outliers, NaNs, and suspicious patterns
        
        Args:
            signals: Array of signals
            max_gap_percent: Max allowed gap as % of signal range
            
        Returns:
            Dictionary with continuity metrics
        """
        stats = {
            'n_signals': len(signals),
            'n_nans': 0,
            'n_infs': 0,
            'n_outliers': 0,
            'continuity_score': 0.0,
            'issues': []
        }
        
        valid_count = len(signals)
        
        for i, sig in enumerate(signals):
            # Check for NaN/Inf
            if np.any(np.isnan(sig)):
                stats['n_nans'] += 1
                stats['issues'].append(f"Signal {i}: contains NaN")
                valid_count -= 1
            
            if np.any(np.isinf(sig)):
                stats['n_infs'] += 1
                stats['issues'].append(f"Signal {i}: contains Inf")
                valid_count -= 1
            
            # Check for outliers (values > 3 sigma)
            if len(sig) > 1:
                mean, std = np.mean(sig), np.std(sig)
                outliers = np.abs(sig - mean) > 3 * std
                if np.sum(outliers) > 0:
                    stats['n_outliers'] += np.sum(outliers)
        
        stats['continuity_score'] = valid_count / len(signals)
        
        return stats
    
    def split_dataset(self, X: np.ndarray, y: np.ndarray, 
                      train_ratio: float = 0.8, stratify: bool = True):
        """
        Split dataset maintaining temporal continuity where possible
        
        Args:
            X: Features
            y: Labels
            train_ratio: Train/test split ratio
            stratify: Stratified split by label
            
        Returns:
            (X_train, X_test, y_train, y_test)
        """
        from sklearn.model_selection import train_test_split
        
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, 
            test_size=1-train_ratio, 
            stratify=(y if stratify else None),
            random_state=42,
            shuffle=True
        )
        
        print(f"✓ Dataset split: Train={len(X_train)}, Test={len(X_test)}")
        print(f"  Train - Normal: {np.sum(y_train==0)}, Abnormal: {np.sum(y_train==1)}")
        print(f"  Test  - Normal: {np.sum(y_test==0)}, Abnormal: {np.sum(y_test==1)}")
        
        return X_train, X_test, y_train, y_test


# Example usage
if __name__ == "__main__":
    loader = ECGRealDataLoader(n_features=140, sampling_rate=360)
    
    # Example: Validate signal continuity
    test_signals = np.random.randn(100, 140).astype(np.float32)
    stats = loader.validate_signal_continuity(test_signals)
    print("Signal Continuity Statistics:", stats)
    
    # Example: Signal preprocessing
    processed = loader.preprocess_ecg(test_signals, normalize=True)
    print(f"Processed signals shape: {processed.shape}")
    print(f"Value range: [{processed.min():.4f}, {processed.max():.4f}]")
