"""
ECG Noise Generator for Robustness Testing
Simulates realistic ECG noise sources:
- Baseline wander
- Powerline interference (50/60 Hz)
- Muscle noise (EMG)
- Motion artifacts
- Quantization noise
"""

import numpy as np
from scipy.signal import butter, filtfilt
from typing import Tuple


class ECGNoiseGenerator:
    """Generate realistic ECG noise for robustness testing"""
    
    def __init__(self, sampling_rate: int = 360, random_seed: int = 42):
        """
        Args:
            sampling_rate: Sampling rate in Hz
            random_seed: For reproducibility
        """
        self.fs = sampling_rate
        np.random.seed(random_seed)
    
    def add_white_gaussian_noise(self, signal: np.ndarray, snr_db: float = 20.0) -> np.ndarray:
        """
        Add Additive White Gaussian Noise (AWGN)
        SNR (Signal-to-Noise Ratio) in dB
        
        Args:
            signal: Input signal
            snr_db: SNR in dB (higher = less noise)
            
        Returns:
            Noisy signal
        """
        signal_power = np.mean(signal ** 2)
        snr_linear = 10 ** (snr_db / 10)
        noise_power = signal_power / snr_linear
        noise = np.random.normal(0, np.sqrt(noise_power), len(signal))
        return signal + noise
    
    def add_powerline_interference(self, signal: np.ndarray, 
                                   frequency: float = 50.0, 
                                   amplitude: float = 0.1) -> np.ndarray:
        """
        Add 50/60 Hz powerline interference
        
        Args:
            signal: Input signal
            frequency: Powerline frequency (50 or 60 Hz)
            amplitude: Relative amplitude of interference
            
        Returns:
            Signal with powerline interference
        """
        t = np.arange(len(signal)) / self.fs
        interference = amplitude * np.sin(2 * np.pi * frequency * t)
        return signal + interference
    
    def add_baseline_wander(self, signal: np.ndarray, 
                           freq_range: Tuple[float, float] = (0.1, 0.5),
                           amplitude: float = 0.1) -> np.ndarray:
        """
        Add low-frequency baseline wander (respiratory artifact)
        
        Args:
            signal: Input signal
            freq_range: Frequency range (Hz) for baseline wander
            amplitude: Amplitude of wander
            
        Returns:
            Signal with baseline wander
        """
        t = np.arange(len(signal)) / self.fs
        n_components = 3
        wander = np.zeros_like(signal)
        
        for i in range(n_components):
            freq = np.random.uniform(freq_range[0], freq_range[1])
            phase = np.random.uniform(0, 2*np.pi)
            wander += amplitude * np.sin(2 * np.pi * freq * t + phase)
        
        return signal + wander / n_components
    
    def add_emg_noise(self, signal: np.ndarray, 
                      amplitude: float = 0.05,
                      freq_range: Tuple[float, float] = (20, 100)) -> np.ndarray:
        """
        Add Electromyography (EMG) muscle noise
        High-frequency noise, non-stationary
        
        Args:
            signal: Input signal
            amplitude: Amplitude of EMG noise
            freq_range: Frequency range (Hz)
            
        Returns:
            Signal with EMG noise
        """
        # Generate EMG-like noise (filtered white noise)
        emg = np.random.normal(0, amplitude, len(signal))
        
        # Band-pass filter to EMG frequency range
        low_freq = freq_range[0] / (self.fs / 2)
        high_freq = freq_range[1] / (self.fs / 2)
        
        if 0 < low_freq < high_freq < 1:
            b, a = butter(4, [low_freq, high_freq], btype='band')
            emg = filtfilt(b, a, emg)
        
        return signal + emg
    
    def add_motion_artifact(self, signal: np.ndarray,
                           amplitude: float = 0.15,
                           burst_prob: float = 0.05) -> np.ndarray:
        """
        Add motion artifacts (sudden signal jumps/spikes)
        
        Args:
            signal: Input signal
            amplitude: Amplitude of artifacts
            burst_prob: Probability of artifact occurrence
            
        Returns:
            Signal with motion artifacts
        """
        noisy = signal.copy()
        n_samples = len(signal)
        
        # Random motion artifact bursts
        for i in range(n_samples):
            if np.random.rand() < burst_prob:
                # Artifact duration
                duration = np.random.randint(1, int(0.05 * self.fs))  # Max 50ms
                end_idx = min(i + duration, n_samples)
                
                # Artifact shape (exponential decay)
                t_decay = np.arange(end_idx - i) / self.fs
                artifact = amplitude * np.exp(-5 * t_decay) * np.random.randn()
                noisy[i:end_idx] += artifact
        
        return noisy
    
    def add_quantization_noise(self, signal: np.ndarray, bits: int = 12) -> np.ndarray:
        """
        Add quantization noise from ADC (Analog-to-Digital Converter)
        Simulates limited bit resolution
        
        Args:
            signal: Input signal (should be normalized to [-1, 1])
            bits: Number of ADC bits
            
        Returns:
            Quantized signal
        """
        # Quantization levels
        levels = 2 ** bits
        quantized = np.round(signal * (levels / 2)) / (levels / 2)
        
        # Add quantization error
        noise = (signal - quantized) * np.random.uniform(-0.5, 0.5, len(signal))
        
        return quantized + noise
    
    def add_realistic_noise(self, signal: np.ndarray,
                           snr_db: float = 20.0,
                           add_awgn: bool = True,
                           add_powerline: bool = True,
                           add_baseline: bool = True,
                           add_emg: bool = False,
                           add_motion: bool = False) -> np.ndarray:
        """
        Add combination of realistic ECG noise sources
        
        Args:
            signal: Input signal
            snr_db: SNR in dB
            add_awgn: Add white Gaussian noise
            add_powerline: Add 50/60 Hz interference
            add_baseline: Add baseline wander
            add_emg: Add muscle noise
            add_motion: Add motion artifacts
            
        Returns:
            Noisy signal
        """
        noisy = signal.copy()
        
        if add_awgn:
            noisy = self.add_white_gaussian_noise(noisy, snr_db)
        
        if add_powerline:
            # Randomly choose 50 or 60 Hz
            freq = 50 if np.random.rand() < 0.5 else 60
            noisy = self.add_powerline_interference(noisy, frequency=freq, amplitude=0.05)
        
        if add_baseline:
            noisy = self.add_baseline_wander(noisy, amplitude=0.08)
        
        if add_emg:
            noisy = self.add_emg_noise(noisy, amplitude=0.03)
        
        if add_motion:
            noisy = self.add_motion_artifact(noisy, amplitude=0.1, burst_prob=0.02)
        
        return noisy
    
    def create_noise_levels(self, signal: np.ndarray, 
                           noise_configs: list = None) -> dict:
        """
        Create multiple noise-level variants of a signal
        for robustness testing
        
        Args:
            signal: Input signal
            noise_configs: List of noise configuration dicts
                          Format: {'name': str, 'snr_db': float, ...}
            
        Returns:
            Dictionary with noisy variants
        """
        if noise_configs is None:
            noise_configs = [
                {'name': 'clean', 'snr_db': 100, 'add_noise': False},
                {'name': 'low_noise', 'snr_db': 30},
                {'name': 'medium_noise', 'snr_db': 20},
                {'name': 'high_noise', 'snr_db': 10},
                {'name': 'extreme_noise', 'snr_db': 5},
            ]
        
        variants = {}
        
        for config in noise_configs:
            name = config.pop('name', 'unknown')
            add_noise = config.pop('add_noise', True)
            
            if add_noise:
                noisy = self.add_realistic_noise(signal, **config)
            else:
                noisy = signal.copy()
            
            variants[name] = noisy
        
        return variants


def add_noise_to_dataset(X: np.ndarray, y: np.ndarray,
                         noise_levels: list = None,
                         sampling_rate: int = 360) -> Tuple[dict, dict]:
    """
    Add realistic noise to ECG dataset at multiple levels
    
    Args:
        X: ECG signals (n_samples, n_features)
        y: Labels
        noise_levels: List of SNR values in dB
        sampling_rate: Sampling rate in Hz
        
    Returns:
        (X_noisy_dict, y_dict) - Dictionaries with noisy variants
    """
    if noise_levels is None:
        noise_levels = [30, 20, 10, 5]
    
    generator = ECGNoiseGenerator(sampling_rate=sampling_rate)
    X_noisy_dict = {}
    y_dict = {}
    
    # Original clean version
    X_noisy_dict['clean'] = X.copy()
    y_dict['clean'] = y.copy()
    
    # Noisy versions
    for snr in noise_levels:
        X_noisy = np.zeros_like(X)
        for i in range(len(X)):
            X_noisy[i] = generator.add_realistic_noise(X[i], snr_db=snr)
        
        X_noisy_dict[f'snr_{snr}dB'] = X_noisy
        y_dict[f'snr_{snr}dB'] = y.copy()
    
    return X_noisy_dict, y_dict


# Example usage
if __name__ == "__main__":
    generator = ECGNoiseGenerator(sampling_rate=360)
    
    # Generate a simple test signal
    t = np.linspace(0, 1, 360)
    signal = 2 * np.sin(2*np.pi*5*t) + 0.5*np.sin(2*np.pi*10*t)
    
    # Add various noise types
    noisy_awgn = generator.add_white_gaussian_noise(signal, snr_db=20)
    noisy_powerline = generator.add_powerline_interference(signal, frequency=50)
    noisy_baseline = generator.add_baseline_wander(signal)
    noisy_realistic = generator.add_realistic_noise(signal, snr_db=20)
    
    print("✓ Noise generation examples created")
    print(f"  Original signal range: [{signal.min():.4f}, {signal.max():.4f}]")
    print(f"  AWGN noisy range: [{noisy_awgn.min():.4f}, {noisy_awgn.max():.4f}]")
    print(f"  Realistic noisy range: [{noisy_realistic.min():.4f}, {noisy_realistic.max():.4f}]")
