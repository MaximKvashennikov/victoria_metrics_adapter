import json

import allure
import requests
from random import randint
from datetime import datetime, timedelta
from typing import List, Tuple, Union
from src.config.settings import settings
from src.helpers.retry_helper import RetryHelper


class VictoriaMetricsClient:
    SERIES = '/prometheus/api/v1/series'
    QUERY_RANGE = '/prometheus/api/v1/query_range'
    IMPORT = '/api/v1/import'
    DELETE_SERIES = '/api/v1/admin/tsdb/delete_series'


    def __init__(self):
        self.address = settings.url
        self.auth = (settings.vm_user, settings.vm_user)
        self.get = requests.get
        self.post = requests.post

    @allure.step("Импорт данных в VictoriaMetrics")
    def victoria_import(self, data: dict) -> None:
        """
        Импортирует метрики в VictoriaMetrics

        :param data: Словарь с метрикой
        :return: None
        """
        response = self.post(
            self.address + self.IMPORT,
            data=json.dumps(data),
            auth=self.auth,
            verify=False,
        )

        assert response.status_code == 204, (
            f'Код ответа {response.status_code} != 204 при импорте данных в VictoriaMetrics'
        )

    @allure.step("Удаление временного ряда в VictoriaMetrics")
    def victoria_delete_metric(self, metrics: list) -> None:
        """
        Удаялет временной ряд метрики целиком.

        :param metrics: Список Метрик, вможно с фильтрацией PromQL, например,
        tme_routes_routes_step_security{security="Unsafe", step_count="2"}
        :return:
        """

        response = self.post(
            self.address + self.DELETE_SERIES,
            auth=self.auth,
            verify=False,
            params={'match[]': metrics}
        )

        assert response.status_code == 204, (
            f'Код ответа {response.status_code} != 204 при удалении данных в VictoriaMetrics'
        )

    @allure.step("Пполучить данные метрик VictoriaMetrics")
    def victoria_get_metrics(self, metrics: list) -> dict:
        """
        Возвращает информацию по метрикам без временного ряда.

        :param metrics: Список Метрик, возможно с фильтрацией PromQL, например,
        tme_routes_routes_step_security{security="Unsafe", step_count="2"}
        :return: dict
        """
        response_body = self.get(
            self.address + self.SERIES,
            auth=self.auth,
            verify=False,
            params={'match[]': metrics},
        ).json()

        return response_body

    @allure.step("Получение данных в заданном временном интервале из VictoriaMetrics")
    def get_metric_range_data(
            self,
            metrics: list,
            step: int = 60,
            start: datetime = datetime.now() - timedelta(minutes=60),
            end: datetime = datetime.now()
    ) -> list:
        """
        Возвращает метрики и их значения в выбронном временном ряду

        :param metrics: Список Метрик, вможно с фильтрацией PromQL, например,
        tme_routes_routes_step_security{security="Unsafe", step_count="2"}

        :param step: Шаг интервала в секундах
        :param start: Начало интервала в формате datetime
        :param end: Конец интервала  в формате datetime, по умолчанию текущий datetime
        :return: list: Список метрик
        """
        params = {
            'query': metrics,
            'start': start.timestamp(),
            'end': end.timestamp(),
            'step': step
        }
        response = self.get(
            self.address + self.QUERY_RANGE,
            params=params,
            auth=self.auth,
            verify=False)

        if response.status_code == 200:
            return response.json()['data']['result']
        raise f'Ошибка при получении данных метрик: {response.status_code}'

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
        :return: Кортеж из списков:
        Список значений timestamps с типом int,
        Список значений value с типом int или float.
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
        :param security:  Лейбл метрики, действие будет приизведено только над метриками с безопасностью security
        :param step_count: Лейбл метрики, действие будет приизведено только над метриками для шага step_count,
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

        data = {"metric": {"__name__": metric_name,
                           "job": "Tme",
                           "instance": "6c65dfec-d15c-45a2-83ef-a7b42fb32527",
                           "application_id": "BaseApp-a9506d78",
                           "application_instance_id": "Modelling",
                           "security": f"{security}",
                           "service_instance_id": "6c65dfec-d15c-45a2-83ef-a7b42fb32527",
                           "service_name": "Tme",
                           "service_version": "1.0.0",
                           "telemetry_sdk_language": "dotnet",
                           "telemetry_sdk_name": "opentelemetry",
                           "telemetry_sdk_version": "1.6.0"},
                "values": values,
                "timestamps": timestamps}

        data_for_delete = f'{metric_name}{{security="{security}"}}'

        if step_count:
            data["metric"].update({"step_count": f"{step_count}"})
            data_for_delete = f'{metric_name}{{security="{security}", step_count="{step_count}"}}'

        if risk_name:
            data["metric"].update({"risk_name": f"{risk_name}"})
            data_for_delete = f'{metric_name}{{security="{security}", risk_name="{risk_name}"}}'

        if delete_metrics_first:
            self.victoria_delete_metric([data_for_delete])
            self._ensure_metrics_deleted(data_for_delete)

        self.victoria_import(data)

    def _ensure_metrics_deleted(self, metric: str) -> None:
        RetryHelper(
            max_retries=3,
            delay=2.0,
            retry_condition=lambda response: not response.get('data'),
        ).execute(self.victoria_get_metrics, [metric])


if __name__ == "__main__":
    vm = VictoriaMetricsClient()
    vm.victoria_import_tme_routes_metric(
        metric_name='TestMetric',
        start=datetime.now() - timedelta(hours=3),
        end=datetime.now()
    )

    # vm.victoria_import_tme_routes_metric(
    #     metric_name='TestMetric',
    #     value=4,
    #     start=datetime.now() - timedelta(hours=3),
    #     end=datetime.now(),
    #     delete_metrics_first=True
    # )
