from datetime import datetime, timedelta

import numpy as np

from pandas import Series, TimeSeries, DataFrame, Panel, isnull, notnull

from pandas.tseries.index import date_range
from pandas.tseries.offsets import Minute, BDay
from pandas.tseries.period import period_range, PeriodIndex
from pandas.tseries.resample import DatetimeIndex, TimeGrouper
import pandas.tseries.offsets as offsets

import unittest
import nose

from pandas.util.testing import assert_series_equal, assert_almost_equal
import pandas.util.testing as tm

bday = BDay()


def _skip_if_no_pytz():
    try:
        import pytz
    except ImportError:
        raise nose.SkipTest


class TestResample(unittest.TestCase):

    def setUp(self):
        dti = DatetimeIndex(start=datetime(2005,1,1),
                            end=datetime(2005,1,10), freq='Min')

        self.series = Series(np.random.rand(len(dti)), dti)

    def test_custom_grouper(self):

        dti = DatetimeIndex(freq='Min', start=datetime(2005,1,1),
                            end=datetime(2005,1,10))

        data = np.array([1]*len(dti))
        s = Series(data, index=dti)

        b = TimeGrouper(Minute(5))
        g = s.groupby(b)

        # check all cython functions work
        funcs = ['add', 'mean', 'prod', 'ohlc', 'min', 'max', 'var']
        for f in funcs:
            g._cython_agg_general(f)

        b = TimeGrouper(Minute(5), closed='right', label='right')
        g = s.groupby(b)
        # check all cython functions work
        funcs = ['add', 'mean', 'prod', 'ohlc', 'min', 'max', 'var']
        for f in funcs:
            g._cython_agg_general(f)


        self.assertEquals(g.ngroups, 2593)
        self.assert_(notnull(g.mean()).all())

        # construct expected val
        arr = [1] + [5] * 2592
        idx = dti[0:-1:5]
        idx = idx.append(dti[-1:])
        expect = Series(arr, index=idx)

        # cython returns float for now
        result = g.agg(np.sum)
        assert_series_equal(result, expect.astype(float))

        data = np.random.rand(len(dti), 10)
        df = DataFrame(data, index=dti)
        r = df.groupby(b).agg(np.sum)

        self.assertEquals(len(r.columns), 10)
        self.assertEquals(len(r.index), 2593)

    def test_resample_basic(self):
        rng = date_range('1/1/2000 00:00:00', '1/1/2000 00:13:00', freq='min')
        s = Series(np.random.randn(14), index=rng)
        result = s.resample('5min', how='mean', closed='right', label='right')
        expected = Series([s[0], s[1:6].mean(), s[6:11].mean(), s[11:].mean()],
                          index=date_range('1/1/2000', periods=4, freq='5min'))
        assert_series_equal(result, expected)

        result = s.resample('5min', how='mean', closed='left', label='right')
        expected = Series([s[:5].mean(), s[5:10].mean(), s[10:].mean()],
                          index=date_range('1/1/2000 00:05', periods=3,
                                           freq='5min'))
        assert_series_equal(result, expected)

        s = self.series
        result = s.resample('5Min', how='last')
        grouper = TimeGrouper(Minute(5), closed='right', label='right')
        expect = s.groupby(grouper).agg(lambda x: x[-1])
        assert_series_equal(result, expect)

        # from daily
        dti = DatetimeIndex(start=datetime(2005,1,1), end=datetime(2005,1,10),
                            freq='D')

        s = Series(np.random.rand(len(dti)), dti)

        # to weekly
        result = s.resample('w-sun', how='last')

        self.assertEquals(len(result), 3)
        self.assert_((result.index.dayofweek == [6,6,6]).all())
        self.assertEquals(result.irow(0), s['1/2/2005'])
        self.assertEquals(result.irow(1), s['1/9/2005'])
        self.assertEquals(result.irow(2), s.irow(-1))

        result = s.resample('W-MON', how='last')
        self.assertEquals(len(result), 2)
        self.assert_((result.index.dayofweek == [0,0]).all())
        self.assertEquals(result.irow(0), s['1/3/2005'])
        self.assertEquals(result.irow(1), s['1/10/2005'])

        result = s.resample('W-TUE', how='last')
        self.assertEquals(len(result), 2)
        self.assert_((result.index.dayofweek == [1,1]).all())
        self.assertEquals(result.irow(0), s['1/4/2005'])
        self.assertEquals(result.irow(1), s['1/10/2005'])

        result = s.resample('W-WED', how='last')
        self.assertEquals(len(result), 2)
        self.assert_((result.index.dayofweek == [2,2]).all())
        self.assertEquals(result.irow(0), s['1/5/2005'])
        self.assertEquals(result.irow(1), s['1/10/2005'])

        result = s.resample('W-THU', how='last')
        self.assertEquals(len(result), 2)
        self.assert_((result.index.dayofweek == [3,3]).all())
        self.assertEquals(result.irow(0), s['1/6/2005'])
        self.assertEquals(result.irow(1), s['1/10/2005'])

        result = s.resample('W-FRI', how='last')
        self.assertEquals(len(result), 2)
        self.assert_((result.index.dayofweek == [4,4]).all())
        self.assertEquals(result.irow(0), s['1/7/2005'])
        self.assertEquals(result.irow(1), s['1/10/2005'])

        # to biz day
        result = s.resample('B', how='last')
        self.assertEquals(len(result), 6)
        self.assert_((result.index.dayofweek == [0,1,2,3,4,0]).all())
        self.assertEquals(result.irow(0), s['1/3/2005'])
        self.assertEquals(result.irow(1), s['1/4/2005'])
        self.assertEquals(result.irow(5), s['1/10/2005'])

    def test_resample_frame_basic(self):
        df = tm.makeTimeDataFrame()

        b = TimeGrouper('M')
        g = df.groupby(b)

        # check all cython functions work
        funcs = ['add', 'mean', 'prod', 'min', 'max', 'var']
        for f in funcs:
            g._cython_agg_general(f)

        result = df.resample('A')
        assert_series_equal(result['A'], df['A'].resample('A'))

        result = df.resample('M')
        assert_series_equal(result['A'], df['A'].resample('M'))

        df.resample('M', kind='period')
        df.resample('W-WED', kind='period')

    def test_resample_loffset(self):
        rng = date_range('1/1/2000 00:00:00', '1/1/2000 00:13:00', freq='min')
        s = Series(np.random.randn(14), index=rng)

        result = s.resample('5min', how='mean', closed='right', label='right',
                            loffset=timedelta(minutes=1))
        idx = date_range('1/1/2000', periods=4, freq='5min')
        expected = Series([s[0], s[1:6].mean(), s[6:11].mean(), s[11:].mean()],
                          index=idx + timedelta(minutes=1))
        assert_series_equal(result, expected)

        expected = s.resample('5min', how='mean', closed='right', label='right',
                              loffset='1min')
        assert_series_equal(result, expected)

        expected = s.resample('5min', how='mean', closed='right', label='right',
                              loffset=Minute(1))
        assert_series_equal(result, expected)

        self.assert_(result.index.freq == Minute(5))

                # from daily
        dti = DatetimeIndex(start=datetime(2005,1,1), end=datetime(2005,1,10),
                            freq='D')
        ser = Series(np.random.rand(len(dti)), dti)

        # to weekly
        result = ser.resample('w-sun', how='last')
        expected = ser.resample('w-sun', how='last', loffset=-bday)
        self.assertEqual(result.index[0] - bday, expected.index[0])

    def test_resample_upsample(self):
        # from daily
        dti = DatetimeIndex(start=datetime(2005,1,1), end=datetime(2005,1,10),
                            freq='D')

        s = Series(np.random.rand(len(dti)), dti)

        # to minutely, by padding
        result = s.resample('Min', fill_method='pad')
        self.assertEquals(len(result), 12961)
        self.assertEquals(result[0], s[0])
        self.assertEquals(result[-1], s[-1])

    def test_upsample_with_limit(self):
        rng = date_range('1/1/2000', periods=3, freq='5t')
        ts = Series(np.random.randn(len(rng)), rng)

        result = ts.resample('t', fill_method='ffill', limit=2)
        expected = ts.reindex(result.index, method='ffill', limit=2)
        assert_series_equal(result, expected)

    def test_resample_ohlc(self):
        s = self.series

        grouper = TimeGrouper(Minute(5), closed='right', label='right')
        expect = s.groupby(grouper).agg(lambda x: x[-1])
        result = s.resample('5Min', how='ohlc')

        self.assertEquals(len(result), len(expect))
        self.assertEquals(len(result.columns), 4)

        xs = result.irow(-1)
        self.assertEquals(xs['open'], s[-5])
        self.assertEquals(xs['high'], s[-5:].max())
        self.assertEquals(xs['low'], s[-5:].min())
        self.assertEquals(xs['close'], s[-1])

        xs = result.irow(1)
        self.assertEquals(xs['open'], s[1])
        self.assertEquals(xs['high'], s[1:6].max())
        self.assertEquals(xs['low'], s[1:6].min())
        self.assertEquals(xs['close'], s[5])

    def test_resample_reresample(self):
        dti = DatetimeIndex(start=datetime(2005,1,1), end=datetime(2005,1,10),
                            freq='D')
        s = Series(np.random.rand(len(dti)), dti)
        bs = s.resample('B')
        result = bs.resample('8H')
        self.assertEquals(len(result), 22)
        self.assert_(isinstance(result.index.freq, offsets.DateOffset))
        self.assert_(result.index.freq == offsets.Hour(8))

    def test_resample_timestamp_to_period(self):
        ts = _simple_ts('1/1/1990', '1/1/2000')

        result = ts.resample('A-DEC', kind='period')
        expected = ts.resample('A-DEC')
        expected.index = period_range('1990', '2000', freq='a-dec')
        assert_series_equal(result, expected)

        result = ts.resample('A-JUN', kind='period')
        expected = ts.resample('A-JUN')
        expected.index = period_range('1990', '2000', freq='a-jun')
        assert_series_equal(result, expected)

        result = ts.resample('M', kind='period')
        expected = ts.resample('M')
        expected.index = period_range('1990-01', '2000-01', freq='M')
        assert_series_equal(result, expected)

        result = ts.resample('M', kind='period')
        expected = ts.resample('M')
        expected.index = period_range('1990-01', '2000-01', freq='M')
        assert_series_equal(result, expected)

    def test_ohlc_5min(self):
        def _ohlc(group):
            if isnull(group).all():
                return np.repeat(np.nan, 4)
            return [group[0], group.max(), group.min(), group[-1]]

        rng = date_range('1/1/2000 00:00:00', '1/1/2000 5:59:50',
                         freq='10s')
        ts = Series(np.random.randn(len(rng)), index=rng)

        resampled = ts.resample('5min', how='ohlc')

        self.assert_((resampled.ix['1/1/2000 00:00'] == ts[0]).all())

        exp = _ohlc(ts[1:31])
        self.assert_((resampled.ix['1/1/2000 00:05'] == exp).all())

        exp = _ohlc(ts['1/1/2000 5:55:01':])
        self.assert_((resampled.ix['1/1/2000 6:00:00'] == exp).all())

    def test_downsample_non_unique(self):
        rng = date_range('1/1/2000', '2/29/2000')
        rng2 = rng.repeat(5).values
        ts = Series(np.random.randn(len(rng2)), index=rng2)

        result = ts.resample('M', how='mean')

        expected = ts.groupby(lambda x: x.month).mean()
        self.assertEquals(len(result), 2)
        assert_almost_equal(result[0], expected[1])
        assert_almost_equal(result[1], expected[2])

    def test_asfreq_non_unique(self):
        # GH #1077
        rng = date_range('1/1/2000', '2/29/2000')
        rng2 = rng.repeat(2).values
        ts = Series(np.random.randn(len(rng2)), index=rng2)

        self.assertRaises(Exception, ts.asfreq, 'B')

    def test_resample_axis1(self):
        rng = date_range('1/1/2000', '2/29/2000')
        df = DataFrame(np.random.randn(3, len(rng)), columns=rng,
                       index=['a', 'b', 'c'])

        result = df.resample('M', axis=1)
        expected = df.T.resample('M').T
        tm.assert_frame_equal(result, expected)

    def test_resample_panel(self):
        rng = date_range('1/1/2000', '6/30/2000')
        n = len(rng)

        panel = Panel(np.random.randn(3, n, 5),
                      items=['one', 'two', 'three'],
                      major_axis=rng,
                      minor_axis=['a', 'b', 'c', 'd', 'e'])

        result = panel.resample('M', axis=1)

        def p_apply(panel, f):
            result = {}
            for item in panel.items:
                result[item] = f(panel[item])
            return Panel(result, items=panel.items)

        expected = p_apply(panel, lambda x: x.resample('M'))
        tm.assert_panel_equal(result, expected)

        panel2 = panel.swapaxes(1, 2)
        result = panel2.resample('M', axis=2)
        expected = p_apply(panel2, lambda x: x.resample('M', axis=1))
        tm.assert_panel_equal(result, expected)

    def test_resample_panel_numpy(self):
        rng = date_range('1/1/2000', '6/30/2000')
        n = len(rng)

        panel = Panel(np.random.randn(3, n, 5),
                      items=['one', 'two', 'three'],
                      major_axis=rng,
                      minor_axis=['a', 'b', 'c', 'd', 'e'])

        result = panel.resample('M', how=lambda x: x.mean(), axis=1)
        expected = panel.resample('M', how='mean', axis=1)
        tm.assert_panel_equal(result, expected)

    def test_resample_anchored_ticks(self):
        # If a fixed delta (5 minute, 4 hour) evenly divides a day, we should
        # "anchor" the origin at midnight so we get regular intervals rather
        # than starting from the first timestamp which might start in the middle
        # of a desired interval

        rng = date_range('1/1/2000 04:00:00', periods=86400, freq='s')
        ts = Series(np.random.randn(len(rng)), index=rng)
        ts[:2] = np.nan # so results are the same

        freqs = ['t', '5t', '15t', '30t', '4h', '12h']
        for freq in freqs:
            result = ts[2:].resample(freq, closed='left', label='left')
            expected = ts.resample(freq, closed='left', label='left')
            assert_series_equal(result, expected)

    def test_resample_base(self):
        rng = date_range('1/1/2000 00:00:00', '1/1/2000 02:00', freq='s')
        ts = Series(np.random.randn(len(rng)), index=rng)

        resampled = ts.resample('5min', base=2)
        exp_rng = date_range('1/1/2000 00:02:00', '1/1/2000 02:02',
                             freq='5min')
        self.assert_(resampled.index.equals(exp_rng))

    def test_resample_daily_anchored(self):
        rng = date_range('1/1/2000 0:00:00', periods=10000, freq='T')
        ts = Series(np.random.randn(len(rng)), index=rng)
        ts[:2] = np.nan # so results are the same

        result = ts[2:].resample('D', closed='left', label='left')
        expected = ts.resample('D', closed='left', label='left')
        assert_series_equal(result, expected)

    def test_resample_to_period_monthly_buglet(self):
        # GH #1259

        rng = date_range('1/1/2000','12/31/2000')
        ts = Series(np.random.randn(len(rng)), index=rng)

        result = ts.resample('M', kind='period')
        exp_index = period_range('Jan-2000', 'Dec-2000', freq='M')
        self.assert_(result.index.equals(exp_index))

    def test_resample_empty(self):
        ts = _simple_ts('1/1/2000', '2/1/2000')[:0]

        result = ts.resample('A')
        self.assert_(len(result) == 0)
        self.assert_(result.index.freqstr == 'A-DEC')

        result = ts.resample('A', kind='period')
        self.assert_(len(result) == 0)
        self.assert_(result.index.freqstr == 'A-DEC')

    def test_weekly_resample_buglet(self):
        # #1327
        rng = date_range('1/1/2000', freq='B', periods=20)
        ts = Series(np.random.randn(len(rng)), index=rng)

        resampled = ts.resample('W')
        expected = ts.resample('W-SUN')
        assert_series_equal(resampled, expected)


def _simple_ts(start, end, freq='D'):
    rng = date_range(start, end, freq=freq)
    return Series(np.random.randn(len(rng)), index=rng)

def _simple_pts(start, end, freq='D'):
    rng = period_range(start, end, freq=freq)
    return TimeSeries(np.random.randn(len(rng)), index=rng)


from pandas.tseries.frequencies import MONTHS, DAYS
from pandas.util.compat import product


class TestResamplePeriodIndex(unittest.TestCase):

    def test_basic_downsample(self):
        ts = _simple_pts('1/1/1990', '6/30/1995', freq='M')
        result = ts.resample('a-dec')

        expected = ts.groupby(ts.index.year).mean()
        expected.index = period_range('1/1/1990', '6/30/1995',
                                      freq='a-dec')
        assert_series_equal(result, expected)

        # this is ok
        assert_series_equal(ts.resample('a-dec'), result)
        assert_series_equal(ts.resample('a'), result)

    def test_not_subperiod(self):
        # These are incompatible period rules for resampling
        ts = _simple_pts('1/1/1990', '6/30/1995', freq='w-wed')
        self.assertRaises(ValueError, ts.resample, 'a-dec')
        self.assertRaises(ValueError, ts.resample, 'q-mar')
        self.assertRaises(ValueError, ts.resample, 'M')
        self.assertRaises(ValueError, ts.resample, 'w-thu')

    def test_basic_upsample(self):
        ts = _simple_pts('1/1/1990', '6/30/1995', freq='M')
        result = ts.resample('a-dec')

        resampled = result.resample('D', fill_method='ffill', convention='end')

        expected = result.to_timestamp('D', how='end')
        expected = expected.asfreq('D', 'ffill').to_period()

        assert_series_equal(resampled, expected)

    def test_upsample_with_limit(self):
        rng = period_range('1/1/2000', periods=5, freq='A')
        ts = Series(np.random.randn(len(rng)), rng)

        result = ts.resample('M', fill_method='ffill', limit=2)
        expected = ts.asfreq('M').reindex(result.index, method='ffill',
                                          limit=2)
        assert_series_equal(result, expected)

    def test_annual_upsample(self):
        targets = ['D', 'B', 'M']

        for month in MONTHS:
            ts = _simple_pts('1/1/1990', '12/31/1995', freq='A-%s' % month)

            for targ, conv, meth in product(targets, ['start', 'end'],
                                            ['ffill', 'bfill']):
                result = ts.resample(targ, fill_method=meth,
                                     convention=conv)
                expected = result.to_timestamp(targ, how=conv)
                expected = expected.asfreq(targ, meth).to_period()
                assert_series_equal(result, expected)

        df = DataFrame({'a' : ts})
        rdf = df.resample('D', fill_method='ffill')
        exp = df['a'].resample('D', fill_method='ffill')
        assert_series_equal(rdf['a'], exp)

    def test_quarterly_upsample(self):
        targets = ['D', 'B', 'M']

        for month in MONTHS:
            ts = _simple_pts('1/1/1990', '12/31/1995', freq='Q-%s' % month)

            for targ, conv in product(targets, ['start', 'end']):
                result = ts.resample(targ, fill_method='ffill',
                                     convention=conv)
                expected = result.to_timestamp(targ, how=conv)
                expected = expected.asfreq(targ, 'ffill').to_period()
                assert_series_equal(result, expected)

    def test_monthly_upsample(self):
        targets = ['D', 'B']

        ts = _simple_pts('1/1/1990', '12/31/1995', freq='M')

        for targ, conv in product(targets, ['start', 'end']):
            result = ts.resample(targ, fill_method='ffill',
                                 convention=conv)
            expected = result.to_timestamp(targ, how=conv)
            expected = expected.asfreq(targ, 'ffill').to_period()
            assert_series_equal(result, expected)

    def test_weekly_upsample(self):
        targets = ['D', 'B']

        for day in DAYS:
            ts = _simple_pts('1/1/1990', '12/31/1995', freq='W-%s' % day)

            for targ, conv in product(targets, ['start', 'end']):
                result = ts.resample(targ, fill_method='ffill',
                                     convention=conv)
                expected = result.to_timestamp(targ, how=conv)
                expected = expected.asfreq(targ, 'ffill').to_period()
                assert_series_equal(result, expected)

    def test_resample_to_timestamps(self):
        ts = _simple_pts('1/1/1990', '12/31/1995', freq='M')

        result = ts.resample('A-DEC', kind='timestamp')
        expected = ts.to_timestamp(how='end').resample('A-DEC')
        assert_series_equal(result, expected)

    def test_resample_to_quarterly(self):
        for month in MONTHS:
            ts = _simple_pts('1990', '1992', freq='A-%s' % month)
            quar_ts = ts.resample('Q-%s' % month, fill_method='ffill')

            stamps = ts.to_timestamp('D', how='end')
            qdates = period_range(stamps.index[0], stamps.index[-1],
                                  freq='Q-%s' % month)

            expected = stamps.reindex(qdates.to_timestamp('D', 'e'),
                                      method='ffill')
            expected.index = qdates

            assert_series_equal(quar_ts, expected)

        # conforms, but different month
        ts = _simple_pts('1990', '1992', freq='A-JUN')

        for how in ['start', 'end']:
            result = ts.resample('Q-MAR', convention=how, fill_method='ffill')
            expected = ts.asfreq('Q-MAR', how=how).to_timestamp('D')
            expected = expected.resample('Q-MAR', fill_method='ffill')
            assert_series_equal(result, expected.to_period('Q-MAR'))

    def test_resample_fill_missing(self):
        rng = PeriodIndex([2000, 2005, 2007, 2009], freq='A')

        s = TimeSeries(np.random.randn(4), index=rng)

        stamps = s.to_timestamp()

        filled = s.resample('A')
        expected = stamps.resample('A').to_period('A')
        assert_series_equal(filled, expected)

        filled = s.resample('A', fill_method='ffill')
        expected = stamps.resample('A', fill_method='ffill').to_period('A')
        assert_series_equal(filled, expected)

    def test_cant_fill_missing_dups(self):
        rng = PeriodIndex([2000, 2005, 2005, 2007, 2007], freq='A')
        s = TimeSeries(np.random.randn(5), index=rng)
        self.assertRaises(Exception, s.resample, 'A')

    def test_resample_5minute(self):
        rng = period_range('1/1/2000', '1/5/2000', freq='T')
        ts = TimeSeries(np.random.randn(len(rng)), index=rng)

        result = ts.resample('5min')
        expected = ts.to_timestamp().resample('5min')
        assert_series_equal(result, expected)

    def test_upsample_daily_business_daily(self):
        ts = _simple_pts('1/1/2000', '2/1/2000', freq='B')

        result = ts.resample('D')
        expected = ts.asfreq('D').reindex(period_range('1/3/2000', '2/1/2000'))
        assert_series_equal(result, expected)

        ts = _simple_pts('1/1/2000', '2/1/2000')
        result = ts.resample('H', convention='s')
        exp_rng = period_range('1/1/2000', '2/1/2000', freq='H')
        expected = ts.asfreq('H', how='s').reindex(exp_rng)
        assert_series_equal(result, expected)

    def test_resample_empty(self):
        ts = _simple_pts('1/1/2000', '2/1/2000')[:0]

        result = ts.resample('A')
        self.assert_(len(result) == 0)

    def test_resample_irregular_sparse(self):
        dr = date_range(start='1/1/2012', freq='5min', periods=1000)
        s = Series(np.array(100), index=dr)
        # subset the data.
        subset = s[:'2012-01-04 07:00']

        result = subset.resample('10min', how=len)
        expected = s.resample('10min', how=len).ix[result.index]
        assert_series_equal(result, expected)

    def test_resample_weekly_all_na(self):
        rng = date_range('1/1/2000', periods=10, freq='W-WED')
        ts = Series(np.random.randn(len(rng)), index=rng)

        result = ts.resample('W-THU')

        self.assert_(result.isnull().all())

        result = ts.resample('W-THU', fill_method='ffill')[:-1]
        expected = ts.asfreq('W-THU', method='ffill')
        assert_series_equal(result, expected)

    def test_resample_tz_localized(self):
        dr = date_range(start='2012-4-13', end='2012-5-1')
        ts = Series(range(len(dr)), dr)

        ts_utc = ts.tz_localize('UTC')
        ts_local = ts_utc.tz_convert('America/Los_Angeles')

        result = ts_local.resample('W')

        ts_local_naive = ts_local.copy()
        ts_local_naive.index = [x.replace(tzinfo=None)
                                for x in ts_local_naive.index.to_pydatetime()]

        exp = ts_local_naive.resample('W').tz_localize('America/Los_Angeles')

        assert_series_equal(result, exp)

    def test_closed_left_corner(self):
        # #1465
        s = Series(np.random.randn(21),
                   index=date_range(start='1/1/2012 9:30',
                                    freq='1min', periods=21))
        s[0] = np.nan

        result = s.resample('10min', how='mean',closed='left', label='right')
        exp = s[1:].resample('10min', how='mean',closed='left', label='right')
        assert_series_equal(result, exp)

        result = s.resample('10min', how='mean',closed='left', label='left')
        exp = s[1:].resample('10min', how='mean',closed='left', label='left')
        assert_series_equal(result, exp)

class TestTimeGrouper(unittest.TestCase):

    def setUp(self):
        self.ts = Series(np.random.randn(1000),
                         index=date_range('1/1/2000', periods=1000))

    def test_apply(self):
        grouper = TimeGrouper('A', label='right', closed='right')

        grouped = self.ts.groupby(grouper)

        f = lambda x: x.order()[-3:]

        applied = grouped.apply(f)
        expected = self.ts.groupby(lambda x: x.year).apply(f)

        applied.index = applied.index.droplevel(0)
        expected.index = expected.index.droplevel(0)
        assert_series_equal(applied, expected)

    def test_count(self):
        self.ts[::3] = np.nan

        grouper = TimeGrouper('A', label='right', closed='right')
        result = self.ts.resample('A', how='count')

        expected = self.ts.groupby(lambda x: x.year).count()
        expected.index = result.index

        assert_series_equal(result, expected)

    def test_numpy_reduction(self):
        result = self.ts.resample('A', how='prod', closed='right')

        expected = self.ts.groupby(lambda x: x.year).agg(np.prod)
        expected.index = result.index

        assert_series_equal(result, expected)


if __name__ == '__main__':
    nose.runmodule(argv=[__file__,'-vvs','-x','--pdb', '--pdb-failure'],
                   exit=False)

