"""Extra property factories for regionprops_table.

Each factory returns a list of scalar callables with semantic column names,
compatible with ``skimage.measure.regionprops_table(extra_properties=...)``.

Features:
    - Radial distribution  (CellProfiler MeasureObjectIntensityDistribution)
    - Granularity spectrum (CellProfiler MeasureGranularity)
    - GLCM texture         (CellProfiler MeasureTexture)
    - Pearson correlation  (CellProfiler MeasureCorrelation)
"""

from __future__ import annotations

import logging
from typing import Sequence, Tuple

import numpy as np
from scipy.ndimage import distance_transform_edt
from skimage.feature import graycomatrix, graycoprops
from skimage.morphology import disk, dilation, erosion
from skimage.transform import resize

log = logging.getLogger(__name__)


def _named(fn, name: str):
    fn.__name__ = name
    fn.__qualname__ = name
    return fn


# ═══════════════════════════════════════════════════════════════════════════
# 1. RADIAL DISTRIBUTION
# ═══════════════════════════════════════════════════════════════════════════

def _radial_all(
    regionmask: np.ndarray,
    intensity: np.ndarray,
    *,
    nbins: int,
    channel: int,
) -> np.ndarray:
    """Fraction of total object intensity in each radial shell.

    Returns ``(nbins,)`` array: index 0 = outermost ring, last = centre.
    """
    img = intensity[..., channel] if intensity.ndim == 3 else intensity
    img = img.astype(float)
    mask = regionmask.astype(bool)
    if not mask.any():
        return np.zeros(nbins)

    dist = distance_transform_edt(mask)
    max_d = dist[mask].max()
    if max_d == 0:
        return np.zeros(nbins)

    norm = dist[mask] / (max_d + 1e-9)
    bin_idx = np.clip(np.floor(norm * nbins).astype(int), 0, nbins - 1)
    total = img[mask].sum()
    if total == 0:
        return np.zeros(nbins)
    fracs = np.array([img[mask][bin_idx == b].sum() / total for b in range(nbins)])
    return fracs[::-1]  # outermost first


def make_radial_distribution(
    nbins: int = 4,
    channel: int = 0,
) -> list:
    """Radial distribution callables.

    Columns: ``radial_bin{i}_ch{channel}`` (i=0 → outermost).
    """
    fns = []
    for b in range(nbins):
        def _fn(mask, intensity, _b=b, _nbins=nbins, _ch=channel):
            return float(_radial_all(mask, intensity, nbins=_nbins, channel=_ch)[_b])
        fns.append(_named(_fn, f"radial_bin{b}_ch{channel}"))
    return fns


# ═══════════════════════════════════════════════════════════════════════════
# 2. GRANULARITY
# ═══════════════════════════════════════════════════════════════════════════

def _granularity_all(
    regionmask: np.ndarray,
    intensity: np.ndarray,
    *,
    scales: tuple,
    channel: int,
    subsample_size: float,
    element_size: int,
) -> np.ndarray:
    """Granularity spectrum — fraction of texture removed at each scale."""
    img = intensity[..., channel] if intensity.ndim == 3 else intensity
    img = img.astype(float)
    mask = regionmask.astype(bool)
    masked = img * mask

    h, w = masked.shape[:2]
    if subsample_size < 1:
        nh = max(1, round(h * subsample_size))
        nw = max(1, round(w * subsample_size))
    elif max(h, w) > subsample_size:
        factor = subsample_size / max(h, w)
        nh = max(1, round(h * factor))
        nw = max(1, round(w * factor))
    else:
        nh, nw = h, w
    if (nh, nw) != (h, w):
        masked = resize(masked, (nh, nw), anti_aliasing=True, order=3)
        mask = resize(mask.astype(float), (nh, nw), order=0) > 0.5

    current = masked.copy()
    prev_mean = current[mask].mean() if mask.any() else 0.0
    result = np.zeros(len(scales))
    if prev_mean == 0:
        return result

    for i, s in enumerate(scales):
        radius = max(1, round(s * element_size / 10))
        se = disk(radius)
        opened = dilation(erosion(current, se), se)
        curr_mean = opened[mask].mean() if mask.any() else 0.0
        result[i] = (prev_mean - curr_mean) / prev_mean if prev_mean > 0 else 0.0
        current = opened
        prev_mean = curr_mean

    return result


def make_granularity(
    scales: Sequence[int] = tuple(range(1, 17)),
    channel: int = 0,
    subsample_size: float = 256,
    element_size: int = 10,
) -> list:
    """Granularity callables.

    Columns: ``granularity_scale{s}_ch{channel}``.
    """
    scales = tuple(scales)
    log.debug("Granularity: scales=%s, element_size=%s, subsample=%s", scales, element_size, subsample_size)
    fns = []
    for i, s in enumerate(scales):
        def _fn(mask, intensity, _i=i, _scales=scales, _ch=channel,
                _sub=subsample_size, _el=element_size):
            return float(
                _granularity_all(mask, intensity, scales=_scales, channel=_ch,
                                 subsample_size=_sub, element_size=_el)[_i]
            )
        fns.append(_named(_fn, f"granularity_scale{s}_ch{channel}"))
    return fns


# ═══════════════════════════════════════════════════════════════════════════
# 3. GLCM
# ═══════════════════════════════════════════════════════════════════════════

_GLCM_PROPS = ("contrast", "dissimilarity", "homogeneity", "energy", "correlation",
               "asm", "entropy")


def _glcm_all(
    regionmask: np.ndarray,
    intensity: np.ndarray,
    *,
    distances: tuple,
    angles: tuple,
    levels: int,
    channel: int,
    props: tuple,
) -> np.ndarray:
    """GLCM features — flat array: [d0_p0, d0_p1, ..., dN_pM]."""
    levels = min(levels, 256)  # uint8 quantization: max 256 levels
    img = intensity[..., channel] if intensity.ndim == 3 else intensity
    img = img.astype(float)
    mask = regionmask.astype(bool)
    roi = img[mask]
    n_out = len(distances) * len(props)
    if roi.size == 0:
        return np.zeros(n_out)

    mn, mx = roi.min(), roi.max()
    if mx == mn:
        return np.zeros(n_out)

    quantised = np.zeros_like(img, dtype=np.uint8)
    quantised[mask] = np.clip(
        ((img[mask] - mn) / (mx - mn) * (levels - 1)).astype(int), 0, levels - 1,
    )

    results = []
    for d in distances:
        glcm = graycomatrix(
            quantised, distances=[d], angles=list(angles),
            levels=levels, symmetric=True, normed=True,
        )
        for p in props:
            if p == "asm":
                vals = graycoprops(glcm, "energy")[0] ** 2
            else:
                vals = graycoprops(glcm, p)[0]
            results.append(float(vals.mean()))
    return np.array(results)


def make_glcm(
    distances: Sequence[int] = (1, 2, 4, 8),
    angles: Sequence[float] = (0, np.pi / 4, np.pi / 2, 3 * np.pi / 4),
    levels: int = 8,
    channel: int = 0,
    props: Sequence[str] = _GLCM_PROPS,
) -> list:
    """GLCM callables.

    Columns: ``glcm_{prop}_d{distance}_ch{channel}``.
    """
    distances = tuple(distances)
    angles = tuple(angles)
    props = tuple(props)
    log.debug("GLCM: distances=%s, angles=%d, levels=%d, props=%s", distances, len(angles), levels, props)
    fns = []
    for di, d in enumerate(distances):
        for pi, p in enumerate(props):
            idx = di * len(props) + pi
            def _fn(mask, intensity, _idx=idx, _dists=distances, _angles=angles,
                    _levels=levels, _ch=channel, _props=props):
                return float(
                    _glcm_all(mask, intensity, distances=_dists, angles=_angles,
                              levels=_levels, channel=_ch, props=_props)[_idx]
                )
            fns.append(_named(_fn, f"glcm_{p}_d{d}_ch{channel}"))
    return fns


# ═══════════════════════════════════════════════════════════════════════════
# 4. PEARSON CORRELATION  (standalone, not an extra_property)
# ═══════════════════════════════════════════════════════════════════════════

def measure_channel_correlation(
    label_image: np.ndarray,
    multichannel_image: np.ndarray,
    channel_pairs: Sequence[Tuple[int, int]] | None = None,
) -> dict:
    """Pearson correlation between channel pairs, per labeled object.

    Parameters
    ----------
    label_image : (H, W) int
    multichannel_image : (H, W, C) float
    channel_pairs : list of (a, b), optional
        Defaults to all unique unordered pairs.

    Returns
    -------
    dict
        Keys: ``"label"``, ``"correlation_pearson_ch{a}_ch{b}"``.
    """
    if multichannel_image.ndim != 3:
        raise ValueError("multichannel_image must be (H, W, C)")
    n_ch = multichannel_image.shape[2]

    if channel_pairs is None:
        channel_pairs = [(a, b) for a in range(n_ch) for b in range(a + 1, n_ch)]

    labels = np.unique(label_image)
    labels = labels[labels != 0]
    n_obj = len(labels)
    result: dict = {"label": labels}

    for a, b in channel_pairs:
        ch_a = multichannel_image[..., a].astype(float)
        ch_b = multichannel_image[..., b].astype(float)
        pearson = np.full(n_obj, np.nan)
        for i, lbl in enumerate(labels):
            m = label_image == lbl
            va, vb = ch_a[m], ch_b[m]
            if va.std() > 0 and vb.std() > 0:
                pearson[i] = float(np.corrcoef(va, vb)[0, 1])
        result[f"correlation_pearson_ch{a}_ch{b}"] = pearson

    return result
