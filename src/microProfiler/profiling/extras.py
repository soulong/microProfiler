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
) -> np.ndarray:
    """Fraction of total object intensity in each radial shell.

    Returns ``(nbins,)`` array: index 0 = outermost ring, last = centre.
    """
    img = intensity.astype(float)
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
    return fracs


def make_radial_distribution(
    nbins: int = 4,
    ch_name: str = "ch0",
) -> list:
    """Create radial distribution callables for ``regionprops_table``.

    Parameters
    ----------
    nbins : int
        Number of radial bins (default ``4``).
    ch_name : str
        Channel name suffix for output columns.

    Returns
    -------
    list of callable
        One callable per bin.  Each returns ``float`` — the fraction of
        total object intensity in that radial shell.

    Output columns
    --------------
    ``radial_bin{i}_{ch_name}`` where i=1 is the outermost ring and
    i=nbins is the centre.
    """
    _state = {"key": None, "result": None}

    def _compute(mask, intensity):
        key = (id(mask), mask.shape, mask.sum())
        if _state["key"] != key:
            _state["key"] = key
            _state["result"] = _radial_all(mask, intensity, nbins=nbins)
        return _state["result"]

    fns = []
    for b in range(nbins):
        def _fn(mask, intensity, _b=b):
            return float(_compute(mask, intensity)[_b])
        fns.append(_named(_fn, f"radial_bin{b + 1}_{ch_name}"))
    return fns


# ═══════════════════════════════════════════════════════════════════════════
# 2. GRANULARITY
# ═══════════════════════════════════════════════════════════════════════════

def _granularity_all(
    regionmask: np.ndarray,
    intensity: np.ndarray,
    *,
    radii: tuple,
    subsample_size: float,
) -> np.ndarray:
    """Granularity spectrum — fraction of texture removed at each feature radius.

    *radii* are user-facing pixel sizes (before subsampling).  The image is
    resized once, then the effective disk radius for each entry is
    ``round(radius * subsample_ratio)``.
    """
    img = intensity.astype(float)
    mask = regionmask.astype(bool)
    masked = img * mask

    h, w = masked.shape[:2]
    if subsample_size <= 1:
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

    subsample_ratio = nh / h if (nh, nw) != (h, w) else 1.0

    effective_radii = [max(1, round(r * subsample_ratio)) for r in radii]

    current = masked.copy()
    result = np.zeros(len(radii))

    for i in range(len(radii)):
        eff_r = effective_radii[i]
        se = disk(eff_r)
        closed = dilation(erosion(current, se), se)

        if eff_r > 1:
            inner = erosion(mask, disk(eff_r))
        else:
            inner = mask

        if not inner.any():
            result[i] = 0.0
            current = closed
            continue

        prev_mean = current[inner].mean()
        curr_mean = closed[inner].mean()
        result[i] = (prev_mean - curr_mean) / prev_mean if prev_mean > 0 else 0.0
        current = closed

    return result


def make_granularity(
    radii: Sequence[float] = (1, 3, 6, 8, 12),
    ch_name: str = "ch0",
    subsample_size: float = 1.0,
) -> list:
    """Create granularity callables for ``regionprops_table``.

    Parameters
    ----------
    radii : sequence of float
        Feature radii in pixels (default ``(1, 3, 6, 8, 12)``).
    ch_name : str
        Channel name suffix for output columns.
    subsample_size : float
        Subsample fraction for speed (default ``1.0`` = no subsampling).

    Returns
    -------
    list of callable
        One callable per radius.  Each returns ``float`` — the fraction
        of texture removed at that scale.

    Output columns
    --------------
    ``granularity_scale{s}_{ch_name}`` where *s* is the user-facing
    pixel radius (before subsampling).
    """
    radii = tuple(radii)
    log.debug("Granularity: radii=%s, subsample=%s", radii, subsample_size)

    _state = {"key": None, "result": None}

    def _compute(mask, intensity):
        key = (id(mask), mask.shape, mask.sum())
        if _state["key"] != key:
            _state["key"] = key
            _state["result"] = _granularity_all(
                mask, intensity, radii=radii, subsample_size=subsample_size,
            )
        return _state["result"]

    fns = []
    for i, r in enumerate(radii):
        def _fn(mask, intensity, _i=i):
            return float(_compute(mask, intensity)[_i])
        fns.append(_named(_fn, f"granularity_scale{int(r)}_{ch_name}"))
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
    props: tuple,
) -> np.ndarray:
    """GLCM features — flat array: [d0_p0, d0_p1, ..., dN_pM]."""
    if levels > 256:
        log.warning("GLCM levels=%d exceeds maximum of 256 — clamping to 256", levels)
    levels = min(levels, 256)
    img = intensity.astype(float)
    mask = regionmask.astype(bool)
    roi = img[mask]
    n_out = len(distances) * len(props)
    if roi.size == 0:
        return np.zeros(n_out)

    mn, mx = roi.min(), roi.max()
    if mx == mn:
        return np.zeros(n_out)

    bg_val = levels
    dtype = np.uint16 if levels >= 256 else np.uint8
    quantised = np.full_like(img, bg_val, dtype=dtype)
    quantised[mask] = np.clip(
        ((img[mask] - mn) / (mx - mn) * (levels - 1)).astype(int), 0, levels - 1,
    )

    results = []
    for d in distances:
        glcm_full = graycomatrix(
            quantised, distances=[d], angles=list(angles),
            levels=levels + 1, symmetric=True, normed=False,
        )
        glcm_masked = glcm_full[:levels, :levels, :, :].astype(float)
        for di in range(glcm_masked.shape[2]):
            for a in range(glcm_masked.shape[3]):
                total = glcm_masked[:, :, di, a].sum()
                if total > 0:
                    glcm_masked[:, :, di, a] /= total

        for p in props:
            if p == "asm":
                vals = graycoprops(glcm_masked, "energy")[0] ** 2
            elif p == "entropy":
                entropies = []
                for a in range(glcm_masked.shape[3]):
                    p_mat = glcm_masked[:, :, 0, a]
                    nonzero = p_mat[p_mat > 0]
                    entropies.append(float(-np.sum(nonzero * np.log2(nonzero))))
                vals = np.array(entropies)
            else:
                vals = graycoprops(glcm_masked, p)[0]
            results.append(float(vals.mean()))
    return np.array(results)


def make_glcm(
    distances: Sequence[int] = (1, 2, 4, 8),
    angles: Sequence[float] = (0, np.pi / 4, np.pi / 2, 3 * np.pi / 4),
    levels: int = 8,
    ch_name: str = "ch0",
    props: Sequence[str] = _GLCM_PROPS,
) -> list:
    """Create GLCM texture callables for ``regionprops_table``.

    Parameters
    ----------
    distances : sequence of int
        Pixel distances for GLCM computation (default ``(1, 2, 4, 8)``).
    angles : sequence of float
        GLCM angles in **radians** (default ``0, π/4, π/2, 3π/4``).
        The pipeline config accepts angles in **degrees** and converts
        automatically.
    levels : int
        Gray-level quantization (default ``8``, max ``256``).
    ch_name : str
        Channel name suffix for output columns.
    props : sequence of str
        GLCM properties to compute (default: contrast, dissimilarity,
        homogeneity, energy, correlation, ASM, entropy).

    Returns
    -------
    list of callable
        One callable per (distance, property) pair.  Each returns
        ``float``.

    Output columns
    --------------
    ``glcm_{prop}_d{distance}_{ch_name}``.
    """
    distances = tuple(distances)
    angles = tuple(angles)
    props = tuple(props)
    log.debug("GLCM: distances=%s, angles=%d, levels=%d, props=%s", distances, len(angles), levels, props)

    _state = {"key": None, "result": None}

    def _compute(mask, intensity):
        key = (id(mask), mask.shape, mask.sum())
        if _state["key"] != key:
            _state["key"] = key
            _state["result"] = _glcm_all(
                mask, intensity, distances=distances, angles=angles,
                levels=levels, props=props,
            )
        return _state["result"]

    fns = []
    for di, d in enumerate(distances):
        for pi, p in enumerate(props):
            idx = di * len(props) + pi
            def _fn(mask, intensity, _idx=idx):
                return float(_compute(mask, intensity)[_idx])
            fns.append(_named(_fn, f"glcm_{p}_d{d}_{ch_name}"))
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
    label_image : np.ndarray
        Labeled segmentation mask of shape ``(H, W)``.
    multichannel_image : np.ndarray
        Multichannel intensity image of shape ``(H, W, C)``.
    channel_pairs : list of (int, int), optional
        Pairs of channel indices.  Defaults to all unique unordered
        pairs.

    Returns
    -------
    dict
        Keys: ``"label"`` (int array), and
        ``"correlation_pearson_ch{a}_ch{b}"`` (float array) for each
        pair.
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
