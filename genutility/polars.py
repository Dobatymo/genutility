from typing import Optional, Type, Union

import numpy as np
import polars as pl
from typing_extensions import final


@final
class _Unset:
    pass


def pl_index(df: pl.DataFrame, indices: np.ndarray, index_col: str = "index") -> pl.DataFrame:
    assert index_col not in df.columns

    return (
        df.with_row_index(index_col)
        .join(
            pl.DataFrame({index_col: indices}),
            on=index_col,
            how="inner",
            validate="1:1",
            maintain_order="left",
        )
        .drop(index_col)
    )


def pl_islice(df: pl.DataFrame, start: Optional[int], stop: Union[int, None, Type[_Unset]] = _Unset) -> pl.DataFrame:
    if start is None and stop is None:
        return df
    elif stop is _Unset:
        return df.slice(0, start)
    elif start is None:
        return df.slice(0, stop)
    elif stop is None:
        return df.slice(start, None)
    else:
        return df.slice(start, stop - start)
