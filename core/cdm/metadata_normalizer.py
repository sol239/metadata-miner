"""Convert tabular extraction results into validated metadata records."""

from typing import TypeVar

import pandas as pd
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class MetadataNormalizer:
    """Map DataFrame columns and validate each row against a model."""

    @staticmethod
    def normalize(
        df: pd.DataFrame,
        model: type[T],
        field_mapping: dict[str, str] | None = None,
    ) -> list[T]:
        """Return validated records without modifying the source DataFrame.

        Args:
            df: Extracted catalog rows.
            model: Pydantic model describing one result row.
            field_mapping: Source column names mapped to model field names.

        Returns:
            Validated models in source row order, or an empty list.

        Raises:
            pydantic.ValidationError: A row does not match the model.
        """
        if field_mapping:
            df = df.rename(columns=field_mapping)
        # Convert pandas NaN, NaT and NA to Python None before validation.
        records = df.astype(object).where(pd.notna(df), None).to_dict(orient="records")
        return [model.model_validate(record) for record in records]
