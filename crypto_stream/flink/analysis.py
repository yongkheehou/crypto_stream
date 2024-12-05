from abc import ABC, abstractmethod
import numpy as np
from pyflink.datastream import DataStream
from pyflink.datastream.window import TumblingProcessingTimeWindows, TimeWindow
from pyflink.datastream.functions import WindowFunction
from pyflink.common.time import Time


class WindowAnalysisFunction(WindowFunction):
    def __init__(self, func):
        self.func = func

    def apply(self, window: TimeWindow, values, out):
        result = self.func(values)
        out.collect(result)


class AnalysisOperator(ABC):
    def __init__(self, window_size: int):
        self.window_size = window_size

    @abstractmethod
    def process(self, stream: DataStream) -> DataStream:
        pass


class SimpleAnalysis(AnalysisOperator):
    def process(self, stream: DataStream) -> DataStream:
        return (
            stream.key_by(lambda x: "all")
            .window(TumblingProcessingTimeWindows.of(Time.minutes(self.window_size)))
            .apply(WindowAnalysisFunction(lambda values: np.mean(values)))
        )


class MovingAverageAnalysis(AnalysisOperator):
    def process(self, stream: DataStream) -> DataStream:
        return (
            stream.key_by(lambda x: "all")
            .window(TumblingProcessingTimeWindows.of(Time.minutes(self.window_size)))
            .apply(WindowAnalysisFunction(lambda values: np.mean(values)))
        )


class RSIAnalysis(AnalysisOperator):
    def process(self, stream: DataStream) -> DataStream:
        def calculate_rsi(values):
            prices = np.array(values)
            deltas = np.diff(prices)
            gains = deltas.copy()
            losses = deltas.copy()

            gains[gains < 0] = 0
            losses[losses > 0] = 0
            losses = abs(losses)

            avg_gain = np.mean(gains)
            avg_loss = np.mean(losses)

            if avg_loss == 0:
                return 100.0

            rs = avg_gain / avg_loss
            return 100 - (100 / (1 + rs))

        return (
            stream.key_by(lambda x: "all")
            .window(TumblingProcessingTimeWindows.of(Time.minutes(self.window_size)))
            .apply(WindowAnalysisFunction(calculate_rsi))
        )


class MACDAnalysis(AnalysisOperator):
    def __init__(self, fast_period: int, slow_period: int, signal_period: int):
        super().__init__(max(fast_period, slow_period, signal_period))
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.signal_period = signal_period

    def process(self, stream: DataStream) -> DataStream:
        def calculate_macd(values):
            prices = np.array(values)
            ema_fast = np.mean(prices[-self.fast_period :])  # noqa: E203
            ema_slow = np.mean(prices[-self.slow_period :])  # noqa: E203
            macd_line = ema_fast - ema_slow
            signal_line = np.mean(prices[-self.signal_period :])  # noqa: E203
            histogram = macd_line - signal_line
            return {"macd": macd_line, "signal": signal_line, "histogram": histogram}

        return (
            stream.key_by(lambda x: "all")
            .window(TumblingProcessingTimeWindows.of(Time.minutes(self.window_size)))
            .apply(WindowAnalysisFunction(calculate_macd))
        )


class BollingerBandsAnalysis(AnalysisOperator):
    def __init__(self, window_size: int, num_std: float):
        super().__init__(window_size)
        self.num_std = num_std

    def process(self, stream: DataStream) -> DataStream:
        def calculate_bollinger(values):
            prices = np.array(values)
            sma = np.mean(prices)
            std = np.std(prices)
            upper_band = sma + (self.num_std * std)
            lower_band = sma - (self.num_std * std)
            return {"middle": sma, "upper": upper_band, "lower": lower_band}

        return (
            stream.key_by(lambda x: "all")
            .window(TumblingProcessingTimeWindows.of(Time.minutes(self.window_size)))
            .apply(WindowAnalysisFunction(calculate_bollinger))
        )
