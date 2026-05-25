"""Adapter / Pipeline 层内部异常（与 app.errors 中的 AppException 区分）。"""


class DataSourceError(Exception):
    """所有数据源相关的失败"""


class AdapterNotFound(DataSourceError):
    pass


class FetchFailure(DataSourceError):
    pass
