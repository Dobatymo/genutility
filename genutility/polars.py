import numpy as np
import polars as pl


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
