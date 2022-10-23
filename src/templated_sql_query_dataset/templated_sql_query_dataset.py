# Standard Library
import copy
from pathlib import PurePosixPath
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union
import logging

# Third-party
import pandas as pd

from jinja2 import Template
from kedro.extras.datasets.pandas import SQLQueryDataSet
from kedro.extras.datasets.json import JSONDataSet
from kedro.io.core import get_filepath_str

logger = logging.getLogger()


class TemplatedSQLQueryDataSet(SQLQueryDataSet):
    """Class extending SQLQueryDataSet with query templating

    Parameters
    ----------
    template
        Dictionary with a single key `filepath` which points to the Jinja template
    parameters
        Dictionary with the parameters feeding the Jinja template
    credentials
    load_args
    fs_args

    For the behavior of credentials, load_args and fs_args, please refer to the documentation of SQLQueryDataSet.

    Example
    -------
    .. code-block:: yaml

        >>> templated_query:
        >>>   type: <path to the dataset module>.TemplatedSQLQueryDataSet
        >>>   filepath: "select shuttle, shuttle_id from spaceflights.shuttles;"
        >>>   credentials: db_credentials
    """

    def __init__(
        self,
        template: Dict[str, str],
        parameters: Dict[str, str],
        credentials: Optional[Dict[str, Any]] = None,
        load_args: Optional[Dict[str, Any]] = None,
        fs_args: Optional[Dict[str, Any]] = None,
    ) -> None:

        filepath = template["filepath"]

        self._query_parameters = JSONDataSet(
            filepath=parameters.get("filepath", "")
        ).load()

        super().__init__(
            "",
            credentials or {},
            load_args or {},
            fs_args or {},
            filepath=filepath,
        )

    @staticmethod
    def _transform_to_sql_compatible_string(
        data: Sequence[Union[str, int, float]]
    ) -> str:

        if isinstance(data, (list, tuple, set)):
            # We use repr() and not str() here to ensure that a string "a" leads to
            # "'a'" with quotes compatible with SQL. We did not use repr(tup(iterable))
            # as it has a leading comma when iterable contains a unique element
            return f"({','.join([repr(value) for value in data])})"

        return repr(data)

    @property
    def _parsed_query_parameters(self) -> Dict[str, str]:
        return {
            query_parameter: self._transform_to_sql_compatible_string(value)
            for query_parameter, value in self._query_parameters.items()
        }

    def _load(self) -> pd.DataFrame:
        load_args = copy.deepcopy(self._load_args)
        engine = self.engines[self._connection_str]  # type: ignore

        if self._filepath:
            load_path = get_filepath_str(PurePosixPath(self._filepath), self._protocol)
            with self._fs.open(load_path, mode="r") as fs_file:
                template = fs_file.read()

        load_args["sql"] = Template(source=template).render(
            **self._parsed_query_parameters
        )
        logger.debug(load_args["sql"])
        return pd.read_sql_query(con=engine, **load_args)
