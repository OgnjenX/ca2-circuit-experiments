"""Count features and a train-only nearest-centroid binary decoder."""
import numpy as np


def spike_count_features(records, population_size, edges_ms):
    edges = np.asarray(edges_ms)
    if edges.ndim != 1 or len(edges) < 2 or not np.all(np.diff(edges) > 0):
        raise ValueError("Bin edges must increase")
    if population_size < 1 or np.any(records["id"] < 0) or np.any(records["id"] >= population_size):
        raise ValueError("Invalid population or event ID")
    result = np.zeros((population_size, len(edges)-1), dtype=float)
    bins = np.searchsorted(edges, records["t"], side="right") - 1
    keep = (bins >= 0) & (bins < len(edges)-1)
    np.add.at(result, (records["id"][keep], bins[keep]), 1)
    return result.ravel()


def centroid_accuracy(train_x, train_y, test_x, test_y):
    train_x, test_x = np.asarray(train_x, dtype=float), np.asarray(test_x, dtype=float)
    train_y, test_y = np.asarray(train_y), np.asarray(test_y)
    if train_x.ndim != 2 or test_x.ndim != 2 or train_x.shape[1] != test_x.shape[1]:
        raise ValueError("Feature dimensions differ")
    if len(train_x) != len(train_y) or len(test_x) != len(test_y) or not len(test_y):
        raise ValueError("Missing or inconsistent labels")
    if set(train_y.tolist()) != {0, 1} or not set(test_y.tolist()).issubset({0, 1}):
        raise ValueError("Binary labels required, with both classes in training")
    if not np.all(np.isfinite(train_x)) or not np.all(np.isfinite(test_x)):
        raise ValueError("Nonfinite feature")
    centroids = np.array([train_x[train_y == label].mean(axis=0) for label in (0, 1)])
    distances = ((test_x[:, None, :] - centroids[None, :, :])**2).sum(axis=2)
    # Follow the frozen experiment's isclose tie rule.
    tied = np.isclose(distances[:, 0], distances[:, 1], rtol=0, atol=1e-10)
    correct = (np.argmin(distances, axis=1) == test_y).astype(float)
    correct[tied] = 0.5
    return float(correct.mean())
