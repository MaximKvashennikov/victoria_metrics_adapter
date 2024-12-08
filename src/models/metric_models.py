from pydantic import BaseModel, field_validator, Field, ConfigDict
from typing import Optional, Union, List


class BaseMetricLabel(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    metric_name: str = Field(alias="__name__")
    job: str = "Tme"
    instance: str = "6c65dfec-d15c-45a2-83ef-a7b42fb32527"
    application_id: str = "BaseApp-a9506d78"
    application_instance_id: str = "Modelling"
    service_instance_id: str = "6c65dfec-d15c-45a2-83ef-a7b42fb32527"
    service_name: str = "Tme"
    service_version: str = "1.0.0"
    telemetry_sdk_language: str = "dotnet"
    telemetry_sdk_name: str = "opentelemetry"
    telemetry_sdk_version: str = "1.6.0"

class BaseMetricData(BaseModel):
    metric: BaseMetricLabel
    values: List[Union[int, float]]
    timestamps: List[int]


class MetricLabel(BaseMetricLabel):
    security: str = "Unsafe"
    step_count: Optional[str] = None
    risk_name: Optional[str] = None

    @field_validator("step_count", mode="before")
    @classmethod
    def convert_step_count(cls, v):
        if v is not None:
            return str(v)
        return v


class MetricData(BaseMetricData):
    metric: MetricLabel

