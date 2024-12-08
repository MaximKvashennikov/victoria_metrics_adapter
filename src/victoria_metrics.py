import json
import allure
import requests
from random import randint
from datetime import datetime, timedelta
from typing import List, Tuple, Union
from src.config.settings import settings
from src.helpers.retry_helper import RetryHelper
from src.models.metric_models import MetricLabel, MetricData, BaseMetricData


class VictoriaMetricsClient:
    SERIES = '/prometheus/api/v1/series'
    QUERY_RANGE = '/prometheus/api/v1/query_range'
    IMPORT = '/api/v1/import'
    DELETE_SERIES = '/api/v1/admin/tsdb/delete_series'

    def __init__(self):
        self.url = settings.url
        self.session = requests.Session()
        self.session.auth = (settings.vm_user, settings.vm_user)
        self.session.verify = False

    def _request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        response = self.session.request(method, self.url + endpoint, **kwargs)
        response.raise_for_status()
        return response

    def _ensure_metrics_deleted(self, metric: list) -> None:
        RetryHelper(
            max_retries=3,
            delay=2.0,
            retry_condition=lambda response: not response.get('data'),
        ).execute(self.victoria_get_metrics, metric)

    def _ensure_metric_range_data_exist(self, params: dict) -> list:
        result = RetryHelper(
            max_retries=5,
            delay=3.0,
            retry_condition=lambda response: response.json().get('data', {}).get('result'),
        ).execute(self._request, 'GET', self.QUERY_RANGE, params=params)
        return result.json()['data']['result']

    @allure.step("Импорт данных в VictoriaMetrics")
    def victoria_import(self, data: dict) -> None:
        self._request('POST', self.IMPORT, data=json.dumps(data))

    @allure.step("Удаление временного ряда в VictoriaMetrics")
    def victoria_delete_metric(self, metrics: list) -> None:
        self._request('POST', self.DELETE_SERIES, params={'match[]': metrics})
        self._ensure_metrics_deleted(metrics)

    @allure.step("Получить данные метрик VictoriaMetrics")
    def victoria_get_metrics(self, metrics: list) -> dict:
        response = self._request('GET', self.SERIES, params={'match[]': metrics})
        return response.json()

    @allure.step("Получение данных в заданном временном интервале из VictoriaMetrics")
    def get_metric_range_data(
            self,
            metrics: list,
            step: int = 60,
            start: datetime = datetime.now() - timedelta(hours=1),
            end: datetime = datetime.now()
    ) -> list:

        return self._ensure_metric_range_data_exist(
            params={
                'query': f'{{__name__=~"{'|'.join(metrics)}"}}',
                'start': start.timestamp(),
                'end': end.timestamp(),
                'step': step
            }
        )

    @staticmethod
    def generate_timestamps_and_values(
            start: datetime = datetime.now() - timedelta(minutes=60),
            end: datetime = datetime.now(),
            step: int = 60,
            value: Union[int, float] = None,
            min_value: int = 0,
            max_value: int = 1000
    ) -> Tuple[List[int], List[int | float]]:
        """
        Функция генерации временного ряда и значений. Используется в метриках.

        :param step: Шаг интервала в секундах
        :param start: Начало интервала в формате datetime
        :param end: Конец интервала в формате datetime, по умолчанию текущий datetime
        :param value: Значение, которое будет сгенерировано для всего временного ряда,
        по умолчанию случайное в диапазоне min_value - max_value
        :param min_value: Минимальное значение диапазона рандомных значений
        :param max_value: Максимальное значение диапазона рандомных значений
        """
        current_time = start
        timestamps = []

        while current_time < end:
            timestamps.append(int(current_time.timestamp() * 1000))
            current_time += timedelta(seconds=step)

        if value is None:
            values = [randint(min_value, max_value) for _ in timestamps]
        else:
            values = [value for _ in timestamps]

        return timestamps, values

    @allure.step("Импорт конкретной метрики в VictoriaMetrics")
    def victoria_import_concrete_metric(self, metric_data: BaseMetricData, delete_metrics_first: bool = True) -> None:
        """
        Функция импорта конкретной метрики в VictoriaMetrics.

        :param metric_data: Объект MetricData, который содержит метрику и соответствующие значения.
        :param delete_metrics_first: Флаг удаления старого временного ряда перед отправкой, по умолчанию True
        :return: None.
        """
        if delete_metrics_first:
            data_for_delete = f'{metric_data.metric.metric_name}'
            self.victoria_delete_metric([data_for_delete])

        self.victoria_import(metric_data.model_dump(by_alias=True, exclude_none=True))

    @allure.step("Импорт метрик tme_routes в VictoriaMetrics")
    def victoria_import_tme_routes_metric(
            self,
            metric_name: str,
            start: datetime = datetime.now() - timedelta(minutes=60),
            end: datetime = datetime.now(),
            step: int = 60,
            value: Union[int, float] = None,
            min_value: int = 0,
            max_value: int = 1000,
            security: str = 'Unsafe',
            step_count: int = None,
            risk_name: str = None,
            delete_metrics_first: bool = True,
    ) -> None:
        """
        Функция импорта сгенерированного временного ряда для определенной метрики.

        :param metric_name: Имя метрики
        :param step: Шаг интервала в секундах
        :param start: Начало интервала в формате datetime
        :param end: Конец интервала в формате datetime, по умолчанию текущий datetime
        :param value: Значение, которое будет сгенерировано для всего временного ряда,
        по умолчанию случайное в диапазоне min_value - max_value
        :param min_value: Минимальное значение диапазона рандомных значений
        :param max_value: Максимальное значение диапазона рандомных значений
        :param delete_metrics_first: Флаг удаления старого временного ряда перед отправкой, по умолчанию True
        :param security: Лейбл метрики, действие будет произведено только над метриками с безопасностью security
        :param step_count: Лейбл метрики, действие будет произведено только над метриками для шага step_count,
        необходимо только для метрики TME_ROUTES_STEP_SECURITY
        :param risk_name: Лейбл метрики, необходимо только для метрики TME_ROUTES_RISK_SECURITY
        :return: None.
        """

        timestamps, values = self.generate_timestamps_and_values(
            start=start,
            end=end,
            step=step,
            value=value,
            min_value=min_value,
            max_value=max_value
        )

        metric_data = MetricData(
            metric=MetricLabel(
                metric_name=metric_name,
                security=security,
                step_count=step_count,
                risk_name=risk_name
            ),
            values=values,
            timestamps=timestamps
        )

        self.victoria_import_concrete_metric(metric_data, delete_metrics_first=delete_metrics_first)



if __name__ == "__main__":
    vm = VictoriaMetricsClient()
    vm.victoria_delete_metric(['TestMetric'])

    vm.victoria_import_tme_routes_metric(
        metric_name='TestMetric1',
        value=30,
        step_count=7,
        start=datetime.now() - timedelta(hours=3),
        end=datetime.now(),
        delete_metrics_first=True
    )
    vm.victoria_import_tme_routes_metric(
        metric_name='TestMetric2',
    )

    print(vm.get_metric_range_data(metrics=['TestMetric1', 'TestMetric2']))
