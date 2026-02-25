"""
ECG-Specific Metrics and Evaluation
Metrics relevant to cardiac anomaly detection and signal quality
"""

import numpy as np
import pandas as pd
from sklearn.metrics import (
    roc_curve, auc, precision_recall_curve,
    confusion_matrix, f1_score, fbeta_score,
    accuracy_score, precision_score, recall_score
)
from typing import Dict, Tuple, List


class ECGMetrics:
    """Cardiac-specific evaluation metrics"""
    
    @staticmethod
    def sensitivity_specificity(y_true: np.ndarray, y_pred: np.ndarray) -> Tuple[float, float]:
        """
        Sensitivity (Recall/True Positive Rate): P(detected | anomaly)
        Specificity (True Negative Rate): P(not detected | normal)
        Critical for medical applications
        
        Returns:
            (sensitivity, specificity)
        """
        tn, fp, fn, tp = confusion_matrix(y_true, y_pred).ravel()
        sensitivity = tp / (tp + fn) if (tp + fn) > 0 else 0
        specificity = tn / (tn + fp) if (tn + fp) > 0 else 0
        return sensitivity, specificity
    
    @staticmethod
    def positive_predictive_value(y_true: np.ndarray, y_pred: np.ndarray) -> float:
        """
        PPV (Positive Predictive Value): P(anomaly | predicted anomaly)
        What proportion of positive predictions are correct?
        """
        return precision_score(y_true, y_pred, zero_division=0)
    
    @staticmethod
    def negative_predictive_value(y_true: np.ndarray, y_pred: np.ndarray) -> float:
        """
        NPV (Negative Predictive Value): P(normal | predicted normal)
        What proportion of negative predictions are correct?
        """
        tn, fp, fn, tp = confusion_matrix(y_true, y_pred).ravel()
        npv = tn / (tn + fn) if (tn + fn) > 0 else 0
        return npv
    
    @staticmethod
    def calculate_youden_index(y_true: np.ndarray, y_pred: np.ndarray) -> float:
        """
        Youden's J-index: sensitivity + specificity - 1
        Optimal threshold combines sensitivity and specificity
        Range: [-1, 1], higher is better
        """
        sens, spec = ECGMetrics.sensitivity_specificity(y_true, y_pred)
        return sens + spec - 1
    
    @staticmethod
    def calculate_matthews_correlation(y_true: np.ndarray, y_pred: np.ndarray) -> float:
        """
        Matthews Correlation Coefficient (MCC)
        Balanced measure for binary classification
        Range: [-1, 1], considers all confusion matrix elements
        """
        tn, fp, fn, tp = confusion_matrix(y_true, y_pred).ravel()
        
        denom = (tp + fp) * (tp + fn) * (tn + fp) * (tn + fn)
        if denom == 0:
            return 0
        
        mcc = (tp*tn - fp*fn) / np.sqrt(denom)
        return mcc
    
    @staticmethod
    def calculate_f_beta_scores(y_true: np.ndarray, y_pred: np.ndarray,
                                betas: List[float] = None) -> Dict[str, float]:
        """
        Calculate F-beta scores for different trade-offs
        F1 (beta=1): Balance precision/recall
        F2 (beta=2): Emphasize recall (catch anomalies)
        F0.5 (beta=0.5): Emphasize precision (minimize false alarms)
        """
        if betas is None:
            betas = [0.5, 1.0, 2.0]
        
        scores = {}
        for beta in betas:
            scores[f'F{beta}'] = fbeta_score(y_true, y_pred, beta=beta)
        
        return scores
    
    @staticmethod
    def calculate_roc_auc(y_true: np.ndarray, y_score: np.ndarray) -> Tuple[float, np.ndarray, np.ndarray]:
        """
        ROC-AUC computed from probability scores
        
        Returns:
            (auc_score, fpr, tpr)
        """
        fpr, tpr, _ = roc_curve(y_true, y_score)
        auc_score = auc(fpr, tpr)
        return auc_score, fpr, tpr
    
    @staticmethod
    def calculate_pr_auc(y_true: np.ndarray, y_score: np.ndarray) -> Tuple[float, np.ndarray, np.ndarray]:
        """
        Precision-Recall AUC (better for imbalanced datasets)
        
        Returns:
            (pr_auc, precision, recall)
        """
        precision, recall, _ = precision_recall_curve(y_true, y_score)
        pr_auc = auc(recall, precision)
        return pr_auc, precision, recall
    
    @staticmethod
    def reconstruction_error_stats(X_true: np.ndarray, X_recon: np.ndarray) -> Dict[str, float]:
        """
        Compute reconstruction error statistics
        Used for anomaly threshold determination
        
        Args:
            X_true: Original signals
            X_recon: Reconstructed signals
            
        Returns:
            Statistics dictionary
        """
        errors = np.mean((X_true - X_recon) ** 2, axis=1)
        
        return {
            'mean_error': np.mean(errors),
            'std_error': np.std(errors),
            'median_error': np.median(errors),
            'min_error': np.min(errors),
            'max_error': np.max(errors),
            'q25_error': np.percentile(errors, 25),
            'q75_error': np.percentile(errors, 75),
            'q95_error': np.percentile(errors, 95),
        }
    
    @staticmethod
    def find_optimal_threshold_f2(y_true: np.ndarray, y_score: np.ndarray,
                                  n_thresholds: int = 100) -> Tuple[float, float]:
        """
        Find optimal threshold by maximizing F2-score
        Emphasizes detection of anomalies (recall > precision)
        
        Args:
            y_true: True binary labels
            y_score: Anomaly scores (higher = more anomalous)
            n_thresholds: Number of thresholds to test
            
        Returns:
            (optimal_threshold, max_f2)
        """
        thresholds = np.linspace(y_score.min(), y_score.max(), n_thresholds)
        best_f2 = -1
        optimal_thresh = thresholds[0]
        
        for thresh in thresholds:
            y_pred = (y_score > thresh).astype(int)
            f2 = fbeta_score(y_true, y_pred, beta=2, zero_division=0)
            
            if f2 > best_f2:
                best_f2 = f2
                optimal_thresh = thresh
        
        return optimal_thresh, best_f2
    
    @staticmethod
    def find_optimal_threshold_youden(y_true: np.ndarray, y_score: np.ndarray,
                                      n_thresholds: int = 100) -> Tuple[float, float]:
        """
        Find optimal threshold by maximizing Youden's J-index
        Balances sensitivity and specificity
        
        Returns:
            (optimal_threshold, max_youden)
        """
        thresholds = np.linspace(y_score.min(), y_score.max(), n_thresholds)
        best_youden = -2
        optimal_thresh = thresholds[0]
        
        for thresh in thresholds:
            y_pred = (y_score > thresh).astype(int)
            youden = ECGMetrics.calculate_youden_index(y_true, y_pred)
            
            if youden > best_youden:
                best_youden = youden
                optimal_thresh = thresh
        
        return optimal_thresh, best_youden


class ComprehensiveEvaluation:
    """Comprehensive ECG model evaluation"""
    
    @staticmethod
    def evaluate_model(y_true: np.ndarray, y_pred: np.ndarray, 
                       y_score: np.ndarray = None,
                       X_true: np.ndarray = None,
                       X_recon: np.ndarray = None) -> pd.DataFrame:
        """
        Comprehensive evaluation with all cardiac metrics
        
        Args:
            y_true: Ground truth labels
            y_pred: Predicted binary labels
            y_score: Probability/anomaly scores (optional)
            X_true: Original signals (optional)
            X_recon: Reconstructed signals (optional)
            
        Returns:
            DataFrame with all metrics
        """
        results = {}
        
        # Basic classification metrics
        results['Accuracy'] = accuracy_score(y_true, y_pred)
        results['Precision'] = precision_score(y_true, y_pred, zero_division=0)
        results['Recall'] = recall_score(y_true, y_pred, zero_division=0)
        results['F1_Score'] = f1_score(y_true, y_pred, zero_division=0)
        
        # Cardiac-specific metrics
        sens, spec = ECGMetrics.sensitivity_specificity(y_true, y_pred)
        results['Sensitivity'] = sens
        results['Specificity'] = spec
        results['Youden_Index'] = ECGMetrics.calculate_youden_index(y_true, y_pred)
        results['PPV'] = ECGMetrics.positive_predictive_value(y_true, y_pred)
        results['NPV'] = ECGMetrics.negative_predictive_value(y_true, y_pred)
        results['MCC'] = ECGMetrics.calculate_matthews_correlation(y_true, y_pred)
        
        # F-beta scores
        f_scores = ECGMetrics.calculate_f_beta_scores(y_true, y_pred)
        results.update(f_scores)
        
        # ROC and PR AUC
        if y_score is not None:
            roc_auc, _, _ = ECGMetrics.calculate_roc_auc(y_true, y_score)
            pr_auc, _, _ = ECGMetrics.calculate_pr_auc(y_true, y_score)
            results['ROC_AUC'] = roc_auc
            results['PR_AUC'] = pr_auc
        
        # Reconstruction error stats
        if X_true is not None and X_recon is not None:
            rec_errors = ECGMetrics.reconstruction_error_stats(X_true, X_recon)
            results.update(rec_errors)
        
        return pd.DataFrame([results])
    
    @staticmethod
    def compare_noise_robustness(model, X_dict: Dict[str, np.ndarray],
                                 y_dict: Dict[str, np.ndarray]) -> pd.DataFrame:
        """
        Evaluate model robustness across noise levels
        
        Args:
            model: Trained model with predict method
            X_dict: Dictionary of signal variants {name: array}
            y_dict: Dictionary of labels {name: array}
            
        Returns:
            DataFrame comparing performance across noise levels
        """
        results_list = []
        
        for variant_name in X_dict.keys():
            X = X_dict[variant_name]
            y = y_dict[variant_name]
            
            # Get predictions
            X_recon = model.predict(X, verbose=0)
            errors = np.mean((X - X_recon) ** 2, axis=1)
            
            # Optimal threshold
            thresh, f2 = ECGMetrics.find_optimal_threshold_f2(y, errors)
            y_pred = (errors > thresh).astype(int)
            
            # Evaluate
            eval_result = ComprehensiveEvaluation.evaluate_model(y, y_pred, errors, X, X_recon)
            eval_result['Variant'] = variant_name
            eval_result['Threshold'] = thresh
            
            results_list.append(eval_result)
        
        return pd.concat(results_list, ignore_index=True)


# Example usage
if __name__ == "__main__":
    # Test metrics
    y_true = np.array([0, 0, 1, 1, 0, 1, 1, 0, 1, 0])
    y_pred = np.array([0, 0, 1, 1, 0, 0, 1, 0, 1, 0])
    y_score = np.array([0.1, 0.2, 0.9, 0.85, 0.15, 0.4, 0.95, 0.05, 0.88, 0.12])
    
    # Single evaluation
    results = ComprehensiveEvaluation.evaluate_model(y_true, y_pred, y_score)
    print("Evaluation Results:")
    print(results.T)
    
    # Find optimal thresholds
    opt_thresh_f2, best_f2 = ECGMetrics.find_optimal_threshold_f2(y_true, y_score)
    opt_thresh_youden, best_youden = ECGMetrics.find_optimal_threshold_youden(y_true, y_score)
    
    print(f"\nOptimal Threshold (F2): {opt_thresh_f2:.4f} → F2={best_f2:.4f}")
    print(f"Optimal Threshold (Youden): {opt_thresh_youden:.4f} → Youden={best_youden:.4f}")
