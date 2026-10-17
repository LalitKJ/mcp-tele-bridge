import os
import pandas as pd


def save_messages(messages: list[dict], csv_file: str) -> int:
    """
    Append messages to a CSV file, skipping any msg_id already present.

    Args:
        messages: List of serialized message dicts (must contain 'msg_id').
        csv_file: Absolute or relative path to the target CSV file.

    Returns:
        Number of new rows actually written (0 if all were duplicates).
    """
    if not messages:
        return 0

    df_new = pd.DataFrame(messages)

    if os.path.isfile(csv_file) and os.path.getsize(csv_file) > 0:
        df_existing = pd.read_csv(csv_file)
        existing_ids: set[int] = set(df_existing["msg_id"])
        df_new = df_new[~df_new["msg_id"].isin(existing_ids)]

    if df_new.empty:
        return 0

    # Write header only when creating the file for the first time
    write_header = not (os.path.isfile(csv_file) and os.path.getsize(csv_file) > 0)
    df_new.to_csv(csv_file, mode="a", header=write_header, index=False)
    return len(df_new)
