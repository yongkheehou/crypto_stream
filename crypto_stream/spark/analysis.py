from pyspark.sql import DataFrame
from abc import ABC, abstractmethod
from pyspark.sql.functions import mean


class AnalysisOperator(ABC):
    @abstractmethod
    def process(self, stream: DataFrame) -> DataFrame:
        pass


class SimpleAnalysis(AnalysisOperator):
    def process(self, stream: DataFrame) -> DataFrame:
        return stream.groupBy("key").agg(mean("value").alias("average"))


class MovingAverageAnalysis(AnalysisOperator):
    def process(self, stream: DataFrame) -> DataFrame:
        return stream.groupBy("key").agg(mean("value").alias("moving_average"))


class AnalysisFactory:
    @staticmethod
    def get_operator(job_config):
        if job_config.analysis_type == "simple":
            return SimpleAnalysis()
        elif job_config.analysis_type == "moving_average":
            return MovingAverageAnalysis()
        else:
            raise ValueError(f"Unsupported analysis type: {job_config.analysis_type}")
