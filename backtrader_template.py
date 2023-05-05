######################################################################################################################
# pip uninstall backtrader                                                                                           #
# pip install git+https://github.com/mementum/backtrader.git@0fa63ef4a35dc53cc7320813f8b15480c8f85517#egg=backtrader #
# pip install matplotlib==3.6.2                                                                                      #
######################################################################################################################
import backtrader as bt
import backtrader.indicators as btind
import statistics
import math

class BaseStrategy(bt.Strategy):
    params = (
        ('printlog', False),
    )

    def log(self, txt, dt=None, doprint=False):
        if self.params.printlog or doprint:
            dt = dt or self.datas[0].datetime.datetime(0)
            print('%s, %s' % (dt.isoformat(), txt))

    def __init__(self):
        # Keep a reference to the "close" line in the data[0] dataseries
        self.dataclose = self.datas[0].close

        # To keep track of pending orders and buy price/commission
        self.order = None
        self.buyprice = None
        self.buycomm = None

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            # Buy/Sell order submitted/accepted to/by broker - Nothing to do
            return

            # Check if an order has been completed
            # Attention: broker could reject order if not enough cash
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log('BUY EXECUTED, Price: %.2f, Cost: %.2f, Comm %.2f' %
                         (order.executed.price,
                          order.executed.value,
                          order.executed.comm))

                self.buyprice = order.executed.price
                self.buycomm = order.executed.comm

            elif order.issell():
                self.log('SELL EXECUTED, Price: %.2f, Cost: %.2f, Comm %.2f' %
                         (order.executed.price,
                          order.executed.value,
                          order.executed.comm))

            self.bar_executed = len(self)

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('Order Canceled/Margin/Rejected')

            # Write down: no pending order
        self.order = None

    def next(self):
        # Simply log the closing price of the series from the reference
        self.log('Close, %.2f' % self.dataclose[0])

        # Check if an order is pending ... if yes, we cannot send a 2nd one
        if self.order:
            return

        # Check if we are in the market
        if not self.position:
            self.buy_condition()

        else:
            self.sell_condition()

    #if you want to print the result
    # def stop(self):
    #     self.print()

    def buy_condition(self):
        return

    def sell_condition(self):
        return

    def print(self):
        print(self.__class__.__name__, self.broker.getvalue(), self.params.__dict__)

class Vix_Fix_Indicator(bt.Indicator):
    params = (
        ("pd", 22),  # LookBack Period Standard Deviation High
        ("bbl", 20),  # Bolinger Band Length
        ("mult", 2),  # Bollinger Band Standard Deviation Up
        ("lb", 50),
        ("ph", 0.85),
        ("pl", 1.01),
        ("hp", False),
        ("sd", False),
    )

    lines = ("wvf", "bbands_top", "bbands_bot", "range_high", "range_low")

    def next(self):
        self.lines.wvf[0] = 0.0
        self.lines.bbands_top[0] = 0.0
        self.lines.bbands_bot[0] = 0.0

        close_list = self.datas[0].close.get(size=self.params.pd).tolist()
        if (len(close_list) == self.params.pd):
            max_close_list = max(close_list)
            self.lines.wvf[0] = ((max_close_list - self.datas[0].low[0]) / max_close_list) * 100

            sdev = self.params.mult * statistics.stdev(self.lines.wvf.get(size=self.params.bbl))
            datasum = math.fsum(self.lines.wvf.get(size=self.params.bbl))
            midline = datasum / self.params.bbl

            self.lines.bbands_top[0] = midline + sdev
            self.lines.bbands_bot[0] = midline - sdev

            range = self.lines.wvf.get(size=self.params.lb).tolist()
            if (len(range) == self.params.lb):
                self.lines.range_high[0] = max(range) * self.params.ph
                self.lines.range_low[0] = min(range) * self.params.pl

            #print(self.lines.max[0], self.lines.wvf[0], self.lines.bbands_top[0], self.lines.bbands_bot[0], self.lines.range_high[0], self.lines.range_low[0])

class Laguerre(bt.Indicator):

    params = (
        ('short_gamma', 0.4),
        ('long_gamma', 0.8),
        ('pctile', 90),
        ('wrnpctile', 70),
        ('lkbT',200),
        ('lkbB',200),
    )

    lines = ("pctRankT", "pctRankB", "pctileB", "wrnpctileB", "ppoT", "ppoB")

    lmas_l0, lmas_l1, lmas_l2, lmas_l3 = 0.0, 0.0, 0.0, 0.0
    lmal_l0, lmal_l1, lmal_l2, lmal_l3 = 0.0, 0.0, 0.0, 0.0

    def next(self):

        #lmas
        lmas0_1 = self.lmas_l0  # cache previous intermediate values
        lmas1_1 = self.lmas_l1
        lmas2_1 = self.lmas_l2

        g = self.p.short_gamma  # avoid more lookups
        self.lmas_l0 = l0 = (1.0 - g) * (self.datas[0].high + self.datas[0].low)/2 + g * lmas0_1
        self.lmas_l1 = l1 = -g * l0 + lmas0_1 + g * lmas1_1
        self.lmas_l2 = l2 = -g * l1 + lmas1_1 + g * lmas2_1
        self.lmas_l3 = l3 = -g * l2 + lmas2_1 + g * self.lmas_l3

        self.lmas = lmas = (self.lmas_l0 + 2*self.lmas_l1 + 2*self.lmas_l2 + self.lmas_l3)/6
        
        #lmal
        lmal0_1 = self.lmal_l0  # cache previous intermediate values
        lmal1_1 = self.lmal_l1
        lmal2_1 = self.lmal_l2

        g = self.p.long_gamma  # avoid more lookups
        self.lmal_l0 = l0 = (1.0 - g) * (self.datas[0].high + self.datas[0].low)/2 + g * lmal0_1
        self.lmal_l1 = l1 = -g * l0 + lmal0_1 + g * lmal1_1
        self.lmal_l2 = l2 = -g * l1 + lmal1_1 + g * lmal2_1
        self.lmal_l3 = l3 = -g * l2 + lmal2_1 + g * self.lmal_l3

        lmal = (self.lmal_l0 + 2 * self.lmal_l1 + 2 * self.lmal_l2 + self.lmal_l3) / 6

        self.lines.pctileB[0] = self.params.pctile * -1
        self.lines.wrnpctileB[0] = self.params.wrnpctile * -1

        self.lines.ppoT[0] = (lmas - lmal) / lmal * 100
        self.lines.ppoB[0] = (lmal - lmas) / lmal * 100

        ppoT_list = self.lines.ppoT.get(size=self.params.lkbT).tolist()
        if (len(ppoT_list) == self.params.lkbT):
            self.lines.pctRankT[0] = sum(self.lines.ppoT[0] >= i for i in ppoT_list) / len(ppoT_list) * 100

        ppoB_list = self.lines.ppoB.get(size=self.params.lkbB).tolist()
        if (len(ppoB_list) == self.params.lkbB):
            self.lines.pctRankB[0] = sum(self.lines.ppoB[0] >= i for i in ppoB_list) / len(ppoB_list) * -100

class Laguerre_Williams(BaseStrategy):
    params = (
        ('short_gamma', 0.4),
        ('long_gamma', 0.8),
        ('pctile', 90),
        ('wrnpctile', 70),
        ('lkbT',200),
        ('lkbB',200),
        ('printlog', False),
        ("pd", 22),  # LookBack Period Standard Deviation High
        ("bbl", 20),  # Bolinger Band Length
        ("mult", 2),  # Bollinger Band Standard Deviation Up
        ("lb", 50),
        ("ph", 0.85),
        ("pl", 1.01),
        ("ma1", 10),
        ('ma2', 30),
        ('n1', 10),
        ('n2', 21),
        ('obLevel1', 60),
        ('obLevel2', 53),
        ('osLevel1', -60),
        ('osLevel2', -53),
        ('ma1',5),
        ('ma2',13),
        ('rsi_period', 14),
        ('percent_period', 200),
        ('buy_limit1', 5),
        ('buy_limit2', 20),
        ('sell_limit1', 95),
        ('sell_limit2', 80),

    )

    def __init__(self):
        super().__init__()

        self.lag = Laguerre(self.datas[0],
                            short_gamma = self.params.short_gamma,
                            long_gamma=self.params.long_gamma,
                            pctile=self.params.pctile,
                            wrnpctile=self.params.wrnpctile,
                            lkbT=self.params.lkbT,
                            lkbB=self.params.lkbB,
                            )
        self.wvf = Vix_Fix_Indicator(self.datas[0],
                            pd = self.params.pd,
                            bbl=self.params.bbl,
                            mult=self.params.mult,
                            lb=self.params.lb,
                            ph=self.params.ph,
                            pl=self.params.pl,
                                     )

        ap = (self.datas[0].high + self.datas[0].low + self.datas[0].close)/3
        esa = btind.ExponentialMovingAverage(ap, period = self.params.n1)
        d = btind.ExponentialMovingAverage(abs(ap - esa), period = self.params.n1)
        ci = (ap - esa) / (0.015 * d)
        self.tci = btind.ExponentialMovingAverage(ci, period = self.params.n2)

        self.ma1 = btind.ZeroLagExponentialMovingAverage(self.datas[0], period = self.params.ma1)
        self.ma2 = btind.MovingAverageSimple(self.datas[0], period=self.params.ma2)

        self.rsi = btind.RelativeStrengthIndex(self.datas[0], period = self.params.rsi_period)
        self.prank= btind.PercentRank(self.rsi, period = self.params.percent_period) * 100

        self.pendingBuy = False
        self.pendingSell = False

    def buy_condition(self):
        if (self.wvf.lines.wvf > self.wvf.lines.bbands_top or self.wvf.lines.wvf > self.wvf.lines.range_high) and self.lag.lines.pctRankB <= self.lag.lines.pctileB and self.prank <= self.params.buy_limit1:
            self.log('PENDING BUY, %.2f %.2f %.2f' % (self.dataclose[0], self.lag.lines.pctRankB[0], self.prank[0]))
            self.pendingBuy = True

        elif(self.pendingBuy == True and self.lag.lines.pctRankB >= self.lag.lines.wrnpctileB and self.prank >= self.params.buy_limit2):
            self.pendingBuy = False
            self.log('BUY CREATE, %.2f %.2f %.2f' % (self.dataclose[0], self.lag.lines.pctRankB[0], self.prank[0]))
            self.order = self.buy()


    def sell_condition(self):
        #self.tci >= self.params.obLevel1
        if self.lag.lines.pctRankT >= self.params.pctile and self.prank >= self.params.sell_limit1:
            self.log('PENDING SELL, %.2f %.2f %.2f' % (self.dataclose[0], self.lag.lines.pctRankT[0], self.prank[0]))
            self.pendingSell = True

        elif self.pendingSell == True and self.lag.lines.pctRankT <= self.params.wrnpctile and self.prank <= self.params.sell_limit2:
            self.pendingSell = False
            self.log('SELL CREATE, %.2f %.2f %.2f' % (self.dataclose[0], self.lag.lines.pctRankT[0], self.prank[0]))
            self.order = self.sell()

import pandas as pd
class MyPandasData(bt.feeds.PandasData):
    params = (
        # ('Datetime', 'datetime'),
        ('open', 'open'),
        ('high', 'high'),
        ('low', 'low'),
        ('close', 'close'),
        ('volume', 'volume'),
        ('openinterest', None)
    )

'''
Downtrend   2021-05-09 2021-05-24
Uptrend     2021-01-27 2021-02-21
Sidetrend   2021-05-18 2021-06-10
Final       2021-04-25 2021-06-10
Full        2017-08-14 2023-03-06
'''


if __name__ == '__main__':

    start_date = "2021-05-09"
    end_date = "2021-05-24"
    
    my_data_frame = pd.read_csv('../candles/BTCUSDT_1min.csv', index_col=0, parse_dates=True)
    my_data_frame = my_data_frame.loc[start_date:end_date]
    data = MyPandasData(dataname=my_data_frame)

    cerebro = bt.Cerebro()  
    cerebro.adddata(data, 'btc') 
    cerebro.addstrategy(Laguerre_Williams) 
    cerebro.addsizer(bt.sizers.PercentSizer, percents=99)
    cerebro.broker.setcash(1000) 
    cerebro.broker.setcommission(commission=0.0001) 

    start = ('Starting Portfolio Value: {0:8.2f}'.format(cerebro.broker.getvalue()))
    cerebro.run()
    
    print(start)
    print('Final Portfolio Value: {0:8.2f}'.format(cerebro.broker.getvalue()))
    cerebro.plot(style='candlesticks', volume=True)
