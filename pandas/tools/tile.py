"""
Quantilization functions and related stuff
"""

from pandas.core.api import DataFrame, Series
from pandas.core.factor import Factor
import pandas.core.algorithms as algos
import pandas.core.common as com
import pandas.core.nanops as nanops

import numpy as np


def cut(x, bins, right=True, labels=None, retbins=False, precision=3):
    """
    Return indices of half-open bins to which each value of `x` belongs.

    Parameters
    ----------
    x : array-like
        Input array to be binned. It has to be 1-dimensional.
    bins : int or sequence of scalars
        If `bins` is an int, it defines the number of equal-width bins in the
        range of `x`. However, in this case, the range of `x` is extended
        by .1% on each side to include the min or max values of `x`. If
        `bins` is a sequence it defines the bin edges allowing for
        non-uniform bin width. No extension of the range of `x` is done in
        this case.
    right : bool, optional
        Indicates whether the bins include the rightmost edge or not. If
        right == True (the default), then the bins [1,2,3,4] indicate
        (1,2], (2,3], (3,4].
    labels : array or boolean, default None
        Labels to use for bin edges, or False to return integer bin labels
    retbins : bool, optional
        Whether to return the bins or not. Can be useful if bins is given
        as a scalar.

    Returns
    -------
    out : ndarray of labels
        Same shape as `x`. Array of strings by default, integers if
        labels=False
    bins : ndarray of floats
        Returned only if `retbins` is True.

    Notes
    -----
    The `cut` function can be useful for going from a continuous variable to
    a categorical variable. For example, `cut` could convert ages to groups
    of age ranges.

    Any NA values will be NA in the result

    Examples
    --------
    >>> cut(np.array([.2, 1.4, 2.5, 6.2, 9.7, 2.1]), 3, retbins=True)
    (array([(0.191, 3.367], (0.191, 3.367], (0.191, 3.367], (3.367, 6.533],
           (6.533, 9.7], (0.191, 3.367]], dtype=object),
     array([ 0.1905    ,  3.36666667,  6.53333333,  9.7       ]))
    >>> cut(np.ones(5), 4, labels=False)
    array([2, 2, 2, 2, 2])
    """
    #NOTE: this binning code is changed a bit from histogram for var(x) == 0
    if not np.iterable(bins):
        if np.isscalar(bins) and bins < 1:
            raise ValueError("`bins` should be a positive integer.")
        try: # for array-like
            sz = x.size
        except AttributeError:
            x = np.asarray(x)
            sz = x.size
        if sz == 0:
            # handle empty arrays. Can't determine range, so use 0-1.
            rng = (0, 1)
        else:
            rng = (nanops.nanmin(x), nanops.nanmax(x))
        mn, mx = [mi + 0.0 for mi in rng]

        if mn == mx: # adjust end points before binning
            mn -= .001 * mn
            mx += .001 * mx
            bins = np.linspace(mn, mx, bins+1, endpoint=True)
        else: # adjust end points after binning
            bins = np.linspace(mn, mx, bins+1, endpoint=True)
            adj = (mx - mn) * 0.001 # 0.1% of the range
            if right:
                bins[0] -= adj
            else:
                bins[-1] += adj

    else:
        bins = np.asarray(bins)
        if (np.diff(bins) < 0).any():
            raise ValueError('bins must increase monotonically.')

    return _bins_to_cuts(x, bins, right=right, labels=labels,
                         retbins=retbins, precision=precision)



def qcut(x, q=4, labels=None, retbins=False, precision=3):
    """
    Quantile-based discretization function. Discretize variable into
    equal-sized buckets based on rank or based on sample quantiles. For example
    1000 values for 10 quantiles would produce 1000 integers from 0 to 9
    indicating the

    Parameters
    ----------
    x : ndarray or Series
    q : integer or array of quantiles
        Number of quantiles. 10 for deciles, 4 for quartiles, etc. Alternately
        array of quantiles, e.g. [0, .25, .5, .75, 1.] for quartiles. Array of
        quantiles must span [0, 1]
    labels : array or boolean, default None
        Labels to use for bin edges, or False to return integer bin labels
    retbins : bool, optional
        Whether to return the bins or not. Can be useful if bins is given
        as a scalar.

    Returns
    -------

    Notes
    -----

    Examples
    --------
    """
    if com.is_integer(q):
        quantiles = np.linspace(0, 1, q + 1)
    else:
        quantiles = q
    bins = algos.quantile(x, quantiles)
    bins[0] -= 0.001 * (x.max() - x.min())

    return _bins_to_cuts(x, bins, labels=labels, retbins=retbins,
                         precision=precision)


def _bins_to_cuts(x, bins, right=True, labels=None, retbins=False,
                  precision=3, name=None):
    if name is None and isinstance(x, Series):
        name = x.name
    x = np.asarray(x)

    side = 'left' if right else 'right'
    ids = bins.searchsorted(x, side=side)

    na_mask = com.notnull(x)
    above = na_mask & (ids == len(bins))
    below = na_mask & (ids == 0)

    if above.any():
        raise ValueError('Values fall past last bin: %s' % str(x[above]))

    if below.any():
        raise ValueError('Values fall before first bin: %s' % str(x[below]))

    mask = com.isnull(x)
    has_nas = mask.any()

    if labels is not False:
        if labels is None:
            fmt = lambda v: _format_label(v, precision=precision)
            if right:
                levels = ['(%s, %s]' % (fmt(a), fmt(b))
                           for a, b in zip(bins, bins[1:])]
            else:
                levels = ['[%s, %s)' % (fmt(a), fmt(b))
                           for a, b in zip(bins, bins[1:])]
        else:
            if len(labels) != len(bins) - 1:
                raise ValueError('Bin labels must be one fewer than '
                                 'the number of bin edges')
            levels = labels

        levels = np.asarray(levels, dtype=object)

        if has_nas:
            np.putmask(ids, mask, 0)

        fac = Factor(ids - 1, levels, name=name)
    else:
        fac = ids - 1
        if has_nas:
            fac = ids.astype(np.float64)
            np.putmask(fac, mask, np.nan)

    if not retbins:
        return fac

    return fac, bins


def _format_label(x, precision=3):
    fmt_str = '%%.%dg' % precision
    if com.is_float(x):
        frac, whole = np.modf(x)
        sgn = '-' if x < 0 else ''
        whole = abs(whole)
        if frac != 0.0:
            val = fmt_str % frac
            if 'e' in val:
                return _trim_zeros(fmt_str % x)
            else:
                val = _trim_zeros(val)
                if '.' in val:
                    return sgn + '.'.join(('%d' % whole, val.split('.')[1]))
                else:
                    return sgn + '.'.join(('%d' % whole, val))
        else:
            return sgn + '%d' % whole
    else:
        return str(x)

def _trim_zeros(x):
    while len(x) > 1 and x[-1] == '0':
        x = x[:-1]
    if len(x) > 1 and x[-1] == '.':
        x = x[:-1]
    return x

def bucket(series, k, by=None):
    """
    Produce DataFrame representing quantiles of a Series

    Parameters
    ----------
    series : Series
    k : int
        number of quantiles
    by : Series or same-length array
        bucket by value

    Returns
    -------
    DataFrame
    """
    if by is None:
        by = series
    else:
        by = by.reindex(series.index)

    split = _split_quantile(by, k)
    mat = np.empty((len(series), k), dtype=float) * np.NaN

    for i, v in enumerate(split):
        mat[:, i][v] = series.take(v)

    return DataFrame(mat, index=series.index, columns=np.arange(k) + 1)

def _split_quantile(arr, k):
    arr = np.asarray(arr)
    mask = np.isfinite(arr)
    order = arr[mask].argsort()
    n = len(arr)

    return np.array_split(np.arange(n)[mask].take(order), k)

def bucketcat(series, cats):
    """
    Produce DataFrame representing quantiles of a Series

    Parameters
    ----------
    series : Series
    cat : Series or same-length array
        bucket by category; mutually exxlusive with 'by'

    Returns
    -------
    DataFrame
    """
    if not isinstance(series, Series):
        series = Series(series, index=np.arange(len(series)))

    cats = np.asarray(cats)

    unique_labels = np.unique(cats)
    unique_labels = unique_labels[com.notnull(unique_labels)]

    # group by
    data = {}

    for label in unique_labels:
        data[label] = series[cats == label]

    return DataFrame(data, columns=unique_labels)

def bucketpanel(series, bins=None, by=None, cat=None):
    """
    Bucket data by two Series to create summary panel

    Parameters
    ----------
    series : Series
    bins : tuple (length-2)
        e.g. (2, 2)
    by : tuple of Series
        bucket by value
    cat : tuple of Series
        bucket by category; mutually exxlusive with 'by'

    Returns
    -------
    DataFrame
    """
    use_by = by is not None
    use_cat = cat is not None

    if use_by and use_cat:
        raise Exception('must specify by or cat, but not both')
    elif use_by:
        if len(by) != 2:
            raise Exception('must provide two bucketing series')

        xby, yby = by
        xbins, ybins = bins

        return _bucketpanel_by(series, xby, yby, xbins, ybins)

    elif use_cat:
        xcat, ycat = cat
        return _bucketpanel_cat(series, xcat, ycat)
    else:
        raise Exception('must specify either values or categories to bucket by')

def _bucketpanel_by(series, xby, yby, xbins, ybins):
    xby = xby.reindex(series.index)
    yby = yby.reindex(series.index)

    xlabels = _bucket_labels(xby.reindex(series.index), xbins)
    ylabels = _bucket_labels(yby.reindex(series.index), ybins)

    labels = _uniquify(xlabels, ylabels, xbins, ybins)

    mask = com.isnull(labels)
    labels[mask] = -1

    unique_labels = np.unique(labels)
    bucketed = bucketcat(series, labels)

    _ulist = list(labels)
    index_map = dict((x, _ulist.index(x)) for x in unique_labels)

    def relabel(key):
        pos = index_map[key]

        xlab = xlabels[pos]
        ylab = ylabels[pos]

        return '%sx%s' % (int(xlab) if com.notnull(xlab) else 'NULL',
                          int(ylab) if com.notnull(ylab) else 'NULL')

    return bucketed.rename(columns=relabel)

def _bucketpanel_cat(series, xcat, ycat):
    xlabels, xmapping = _intern(xcat)
    ylabels, ymapping = _intern(ycat)

    shift = 10 ** (np.ceil(np.log10(ylabels.max())))
    labels = xlabels * shift + ylabels

    sorter = labels.argsort()
    sorted_labels = labels.take(sorter)
    sorted_xlabels = xlabels.take(sorter)
    sorted_ylabels = ylabels.take(sorter)

    unique_labels = np.unique(labels)
    unique_labels = unique_labels[com.notnull(unique_labels)]

    locs = sorted_labels.searchsorted(unique_labels)
    xkeys = sorted_xlabels.take(locs)
    ykeys = sorted_ylabels.take(locs)

    stringified = ['(%s, %s)' % arg
                   for arg in zip(xmapping.take(xkeys), ymapping.take(ykeys))]

    result = bucketcat(series, labels)
    result.columns = stringified

    return result

def _intern(values):
    # assumed no NaN values
    values = np.asarray(values)

    uniqued = np.unique(values)
    labels = uniqued.searchsorted(values)
    return labels, uniqued


def _uniquify(xlabels, ylabels, xbins, ybins):
    # encode the stuff, create unique label
    shifter = 10 ** max(xbins, ybins)
    _xpiece = xlabels * shifter
    _ypiece = ylabels

    return _xpiece + _ypiece

def _bucket_labels(series, k):
    arr = np.asarray(series)
    mask = np.isfinite(arr)
    order = arr[mask].argsort()
    n = len(series)

    split = np.array_split(np.arange(n)[mask].take(order), k)

    mat = np.empty(n, dtype=float) * np.NaN
    for i, v in enumerate(split):
        mat[v] = i

    return mat + 1

def quantileTS(frame, percentile):
    """
    Return score at percentile for each point in time (cross-section)

    Parameters
    ----------
    frame: DataFrame
    percentile: int
       nth percentile

    Returns
    -------
    Series (or TimeSeries)
    """
    from pandas.compat.scipy import scoreatpercentile

    def func(x):
        x = np.asarray(x.valid())
        if x.any():
            return scoreatpercentile(x, percentile)
        else:
            return np.nan
    return frame.apply(func, axis=1)
