from abc import ABC, abstractmethod
import numpy as np
import logging
from pyflink.datastream import DataStream
from pyflink.datastream.window import TumblingProcessingTimeWindows, TimeWindow
from pyflink.datastream.functions import WindowFunction
from pyflink.common.time import Time

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    )
    logger.addHandler(handler)


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
            try:
                prices = np.array(values)
                if len(prices) < 2:
                    logger.warning(
                        f"Not enough data points for RSI calculation: {len(prices)}"
                    )
                    return {"value": 50.0, "status": "insufficient_data"}

                # Remove any zero or negative prices
                prices = prices[prices > 0]
                if len(prices) < 2:
                    logger.warning("Not enough valid prices after filtering")
                    return {"value": 50.0, "status": "invalid_prices"}

                # Calculate price changes
                deltas = np.diff(prices)
                gains = deltas.copy()
                losses = deltas.copy()

                # Separate gains and losses
                gains[gains < 0] = 0
                losses[losses > 0] = 0
                losses = abs(losses)

                # Calculate average gains and losses
                avg_gain = np.mean(gains) if len(gains) > 0 else 0
                avg_loss = np.mean(losses) if len(losses) > 0 else 0

                # Handle edge cases
                if avg_loss == 0:
                    rsi = 100.0 if avg_gain > 0 else 50.0
                else:
                    rs = avg_gain / avg_loss
                    rsi = 100 - (100 / (1 + rs))

                logger.info(
                    f"RSI Calculation - Prices: {len(prices)}, "
                    f"Gains: {avg_gain:.2f}, Losses: {avg_loss:.2f}, RSI: {rsi:.2f}"
                )
                return {"value": float(rsi), "status": "success"}

            except Exception as e:
                logger.error(f"Error calculating RSI: {str(e)}, Values: {values}")
                return {"value": 50.0, "status": "error", "error": str(e)}

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
            try:
                prices = np.array(values)
                if len(prices) < max(
                    self.fast_period, self.slow_period, self.signal_period
                ):
                    logger.warning(
                        f"Not enough data points for MACD calculation: {len(prices)}"
                    )
                    return {"macd": 0, "signal": 0, "histogram": 0}

                ema_fast = np.mean(prices[-self.fast_period :])  # noqa: E203
                ema_slow = np.mean(prices[-self.slow_period :])  # noqa: E203
                macd_line = ema_fast - ema_slow
                signal_line = np.mean(prices[-self.signal_period :])  # noqa: E203
                histogram = macd_line - signal_line

                logger.info(
                    f"MACD Calculation - Num prices: {len(prices)}, MACD: {macd_line:.2f}, Signal: {signal_line:.2f}"  # noqa: E501
                )
                return {
                    "macd": macd_line,
                    "signal": signal_line,
                    "histogram": histogram,
                }
            except Exception as e:
                logger.error(f"Error calculating MACD: {str(e)}, Values: {values}")
                return {"macd": 0, "signal": 0, "histogram": 0}

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
            try:
                prices = np.array(values)
                if len(prices) < 2:
                    logger.warning(
                        f"Not enough data points for Bollinger Bands calculation: {len(prices)}"  # noqa: E501
                    )
                    return {"middle": prices[0], "upper": prices[0], "lower": prices[0]}

                sma = np.mean(prices)
                std = np.std(prices)
                upper_band = sma + (self.num_std * std)
                lower_band = sma - (self.num_std * std)

                logger.info(
                    f"Bollinger Bands - Num prices: {len(prices)}, SMA: {sma:.2f}, Upper: {upper_band:.2f}, Lower: {lower_band:.2f}"  # noqa: E501
                )
                return {"middle": sma, "upper": upper_band, "lower": lower_band}
            except Exception as e:
                logger.error(
                    f"Error calculating Bollinger Bands: {str(e)}, Values: {values}"
                )
                return {"middle": 0, "upper": 0, "lower": 0}

        return (
            stream.key_by(lambda x: "all")
            .window(TumblingProcessingTimeWindows.of(Time.minutes(self.window_size)))
            .apply(WindowAnalysisFunction(calculate_bollinger))
        )
