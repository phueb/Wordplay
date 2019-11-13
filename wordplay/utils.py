import pandas as pd
import numpy as np
from scipy.cluster.hierarchy import linkage, dendrogram
from scipy.signal import lfilter
from cytoolz import itertoolz
from typing import Optional, Set

from scipy.stats import linregress


def smooth(l, strength):
    b = [1.0 / strength] * strength
    a = 1
    result = lfilter(b, a, l)
    return result


def roll_mean(l, size):
    result = pd.DataFrame(l).rolling(size).mean().values.flatten()
    return result


def split(l, split_size):
    for i in range(0, len(l), split_size):
        yield l[i:i + split_size]


def fit_line(x, y, eval_x=None):
    poly = np.polyfit(x, y, 1)
    result = np.poly1d(poly)(eval_x or x)
    return result


def get_sliding_windows(window_size, tokens):

    if not isinstance(window_size, int):
        raise TypeError('This function was changed by PH in May 2019 because'
                        'previously used sklearn Countvectorizer uses stopwords'
                        ' and removes punctuation')
    res = list(itertoolz.sliding_window(window_size, tokens))
    return res


def reorder_parts_from_midpoint(parts: np.ndarray
                                ) -> np.ndarray:
    """
    deterministically reorder partitions such that the first partitions
    are guaranteed to be mid-partitions
    """
    # roll such that both matrices start at midpoints, and then get every other row
    a = np.roll(parts, len(parts) // 2, axis=0)[::-2]
    b = np.roll(parts, len(parts) // 2, axis=0)[::+2]
    # interleave rows of a and b
    res = np.hstack((a, b)).reshape(parts.shape)
    assert len(res) == len(parts)
    return res


def to_corr_mat(data_mat):
    mns = data_mat.mean(axis=1, keepdims=True)
    stds = data_mat.std(axis=1, ddof=1, keepdims=True) + 1e-6  # prevent np.inf (happens when dividing by zero)
    deviated = data_mat - mns
    zscored = deviated / stds
    res = np.matmul(zscored, zscored.T) / len(data_mat)  # it matters which matrix is transposed
    return res


def cluster(mat: np.ndarray,
            dg0: dict,
            dg1: dict,
            original_row_words: Optional[Set[str]] = None,
            original_col_words: Optional[Set[str]] = None,
            method: str = 'complete',
            metric: str = 'cityblock'):
    print('Clustering...')
    #
    if dg0 is None:
        lnk0 = linkage(mat, method=method, metric=metric)
        dg0 = dendrogram(lnk0,
                         ax=None,
                         color_threshold=None,
                         no_labels=True,
                         no_plot=True)
    res = mat[dg0['leaves'], :]  # reorder rows
    #
    if dg1 is None:
        lnk1 = linkage(mat.T, method=method, metric=metric)
        dg1 = dendrogram(lnk1,
                         ax=None,
                         color_threshold=None,
                         no_labels=True,
                         no_plot=True)
    #
    res = res[:, dg1['leaves']]  # reorder cols
    if original_row_words is None and original_col_words is None:
        return res, dg0, dg1
    else:
        row_labels = np.array(original_row_words)[dg0['leaves']]
        col_labels = np.array(original_col_words)[dg1['leaves']]
        return res, row_labels, col_labels, dg0, dg1


def plot_best_fit_line(ax, x, y, fontsize, color='red', zorder=3, x_pos=0.75, y_pos=0.75, plot_p=True):
    try:
        best_fit_fxn = np.polyfit(x, y, 1, full=True)
    except Exception as e:  # cannot fit line
        print('rnnlab: Cannot fit line.', e)
        return
    slope = best_fit_fxn[0][0]
    intercept = best_fit_fxn[0][1]
    xl = [min(x), max(x)]
    yl = [slope * xx + intercept for xx in xl]
    # plot line
    ax.plot(xl, yl, linewidth=2, c=color, zorder=zorder)
    # plot rsqrd
    variance = np.var(y)
    residuals = np.var([(slope * xx + intercept - yy) for xx, yy in zip(x, y)])
    Rsqr = np.round(1 - residuals / variance, decimals=3)
    if Rsqr > 0.5:
        fontsize += 5
    ax.text(x_pos, y_pos, '$R^2$ = {}'.format(Rsqr), transform=ax.transAxes, fontsize=fontsize)
    if plot_p:
        p = np.round(linregress(x, y)[3], decimals=8)
        ax.text(x_pos, y_pos - 0.05, 'p = {}'.format(p), transform=ax.transAxes, fontsize=fontsize - 2)