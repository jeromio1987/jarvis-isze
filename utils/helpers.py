import pandas as pd


def load_excel(path: str) -> pd.DataFrame:
    """Load an Excel file and return a DataFrame."""
    return pd.read_excel(path, engine="openpyxl")


def df_to_markdown(df: pd.DataFrame) -> str:
    """Convert a DataFrame to a markdown table string."""
    return df.to_markdown(index=False)


def isze_price_calc(
    bp_jpy: float,
    fx_rate: float,
    source_discount: float,
    class_factor: float,
) -> float:
    """
    ISZE FOB pricing formula.

    SP = FOB_EUR / class_factor
    FOB_EUR = bp_jpy / fx_rate * source_discount

    Args:
        bp_jpy: Base price in JPY (from IML)
        fx_rate: JPY/EUR exchange rate
        source_discount: Source discount factor (e.g. 0.62 for Japan, 0.611 for Thailand)
        class_factor: ABC class factor (markup divisor)

    Returns:
        EUR selling price
    """
    fob_eur = bp_jpy / fx_rate * source_discount
    return fob_eur / class_factor
