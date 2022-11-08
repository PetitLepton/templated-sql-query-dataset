# Standard Library
import json

from pathlib import Path

# Third-party
import pandas
import pytest

from sqlalchemy import create_engine

from src.templated_sql_query_dataset import TemplatedSQLQueryDataSet


# This is a test


class TestTemplatedSQLQueryDataSet:
    @pytest.mark.parametrize(
        "input,expected",
        [
            ([1, 2], "(1,2)"),
            ((1, 2), "(1,2)"),
            ({1, 2}, ("(1,2)")),
            (("a", "b"), "('a','b')"),
            ([1], "(1)"),
            (1, "1"),
            ("a", "'a'"),
        ],
    )
    def test__transform_to_sql_compatible_string(self, input, expected):
        assert (
            TemplatedSQLQueryDataSet._transform_to_sql_compatible_string(input)
            == expected
        )

    def test_load(self, tmp_path: Path):

        # Feed database
        db = f"sqlite:///{tmp_path.as_posix()}/test.db"
        pandas.DataFrame({"name": ["User 1", "User 2", "User 3"]}).to_sql(
            "users", con=create_engine(url=db)
        )

        template_path = tmp_path / "template.sql"
        template_path.write_text(
            "SELECT * FROM users WHERE name IN {{ selected_users }}"
        )

        _parameters_path = tmp_path / "parameters.json"
        with _parameters_path.open("w") as f:
            json.dump({"selected_users": ("User 1", "User 2")}, f)

        _templated_sql_query_dataset = TemplatedSQLQueryDataSet(
            template={"filepath": template_path.as_posix()},
            parameters={"filepath": _parameters_path.as_posix()},
            credentials={"con": db},
        )

        assert _templated_sql_query_dataset._filepath == template_path.as_posix()

        results = _templated_sql_query_dataset._load()
        pandas.testing.assert_series_equal(
            results["name"], pandas.Series(["User 1", "User 2"], name="name")
        )
