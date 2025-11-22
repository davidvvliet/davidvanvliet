"""
Generate 2D visualization of spherical harmonic orbital (2,1,0) - pz orbital
"""

import numpy as np
import matplotlib.pyplot as plt
from scipy.special import sph_harm
from matplotlib.colors import LinearSegmentedColormap

def generate_orbital_2_1_0(size=512, scale=3.0):
    """
    Generate 2D cross-section of (2,1,0) orbital
    
    Parameters:
    size: Resolution of the image (size x size pixels)
    scale: Scale factor for the orbital size
    """
    # Create coordinate grid
    x = np.linspace(-scale, scale, size)
    z = np.linspace(-scale, scale, size)
    X, Z = np.meshgrid(x, z)
    
    # Convert to spherical coordinates
    # For 2D cross-section through xz plane (y=0)
    r = np.sqrt(X**2 + Z**2)
    theta = np.arccos(np.clip(Z / (r + 1e-10), -1, 1))  # Polar angle
    phi = np.arctan2(0, X)  # Azimuthal angle (0 for xz plane)
    
    # Calculate spherical harmonic Y_1^0
    # Y_1^0(θ, φ) = √(3/4π) * cos(θ)
    Y = sph_harm(0, 1, phi, theta)  # m=0, l=1
    
    # Probability density |Y|²
    probability = np.abs(Y)**2
    
    # Normalize and apply radial decay
    # For n=2 orbital, add radial part: R(r) ~ r * exp(-r/2)
    # Adjusted decay rate to make orbital wider
    radial = r * np.exp(-r / 4)
    probability = probability * radial
    
    # Normalize to 0-1 range
    probability = probability / (probability.max() + 1e-10)
    
    return probability, X, Z

def create_colormap():
    """Create custom colormap with smooth gray to green gradient"""
    # #0a0a0a = rgb(10, 10, 10) = normalized (0.039, 0.039, 0.039)
    colors = [
        (0.039, 0.039, 0.039, 1.0),  # #0a0a0a background
        (0.05, 0.05, 0.05, 0.3),     # Very dark gray
        (0.08, 0.08, 0.08, 0.4),     # Dark gray
        (0.12, 0.12, 0.12, 0.5),     # Medium-dark gray
        (0.18, 0.18, 0.18, 0.6),     # Medium gray
        (0.25, 0.25, 0.25, 0.7),     # Light gray
        (0.15, 0.25, 0.15, 0.75),    # Gray-green transition
        (0.05, 0.35, 0.05, 0.8),     # Dark green
        (0.0, 0.5, 0.0, 0.85),       # Medium-dark green
        (0.0, 0.7, 0.0, 0.92),       # Medium green
        (0.0, 0.85, 0.0, 0.96),      # Bright green
        (0.0, 1.0, 0.0, 1.0),        # Brightest green (#00ff00)
    ]
    return LinearSegmentedColormap.from_list('orbital', colors, N=512)

def render_orbital(output_path='../public/orbital-2-1-0.png', size=1024, scale=16.0):
    """Render the orbital and save as PNG"""
    probability, X, Z = generate_orbital_2_1_0(size, scale)
    
    # Create figure with dark background
    fig, ax = plt.subplots(figsize=(8, 8), facecolor='#0a0a0a')
    ax.set_facecolor('#0a0a0a')
    
    # Create custom colormap
    cmap = create_colormap()
    
    # Apply Gaussian blur effect by smoothing
    from scipy.ndimage import gaussian_filter
    smoothed = gaussian_filter(probability, sigma=size/100)
    
    # Render with glow effect
    im = ax.imshow(smoothed, extent=[-scale, scale, -scale, scale], 
                   cmap=cmap, origin='lower', interpolation='bilinear')
    
    # Remove axes
    ax.axis('off')
    
    # Save with high DPI
    plt.tight_layout(pad=0)
    plt.savefig(output_path, dpi=300, 
                facecolor='#0a0a0a', edgecolor='none', pad_inches=0)
    plt.close()
    
    print(f"Orbital visualization saved to {output_path}")

if __name__ == "__main__":
    render_orbital()

