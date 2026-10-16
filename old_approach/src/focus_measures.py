import cv2
import numpy as np

def normalized_variance(img):
    """
    Computes the Normalized Variance focus measure.
    Focus = Variance(img) / Mean(img)
    """
    mean, stddev = cv2.meanStdDev(img)
    var = stddev[0][0] ** 2
    mean_val = mean[0][0]
    return var / mean_val if mean_val != 0 else 0.0

def tenengrad_measure(img, ksize=3):
    """
    Computes the Tenengrad (Sobel) focus measure (1st Derivative).
    Focus = Mean(Gx^2 + Gy^2)
    """
    gx = cv2.Sobel(img, cv2.CV_64F, 1, 0, ksize=ksize)
    gy = cv2.Sobel(img, cv2.CV_64F, 0, 1, ksize=ksize)
    G_sq = gx**2 + gy**2
    return np.mean(G_sq)

def variance_of_laplacian(img, ksize=3):
    """
    Computes the Variance of Laplacian (2nd Derivative).
    Highlights inflection points of edges.
    """
    img_f64 = img.astype(np.float64)
    lap = cv2.Laplacian(img_f64, cv2.CV_64F, ksize=ksize)
    return np.var(lap)

def laplacian_of_gaussian(img, ksize=3, blur_ksize=5, sigma=1.0):
    """
    Computes Laplacian of Gaussian (LoG).
    Bandpass filter: destroys high-frequency noise before finding edges.
    """
    blurred = cv2.GaussianBlur(img, (blur_ksize, blur_ksize), sigma)
    lap = cv2.Laplacian(blurred, cv2.CV_64F, ksize=ksize)
    return np.var(lap)

def brenner_gradient(img):
    """
    Computes the Brenner Gradient.
    Measures differences between pixels spaced 2 units apart.
    Focus = Mean((I(x+2,y) - I(x,y))^2) + Mean((I(x,y+2) - I(x,y))^2)
    Uses mean instead of sum for size-invariant normalization.
    """
    img_float = img.astype(np.float64)
    # Difference along x-axis with stride of 2
    diff_x = img_float[:, 2:] - img_float[:, :-2]
    # Difference along y-axis with stride of 2
    diff_y = img_float[2:, :] - img_float[:-2, :]
    
    # Normalize each component by its own number of terms
    return np.mean(diff_x**2) + np.mean(diff_y**2)
