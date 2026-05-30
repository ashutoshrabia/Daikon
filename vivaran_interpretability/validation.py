import json
import os
from pathlib import Path
from typing import Any, Dict, Optional
import numpy as np
import pandas as pd

PATH = os.path.dirname(os.path.realpath(__file__))

_MODEL = None
_SCALER = None
_FIRST6 = None
_BOOL_COLS = None
_SEL_DICT = None


def _sanitize_token(token: str) -> str:

    out = []
    for ch in str(token):
        if ch.isalnum() or ch == "_":
            out.append(ch)
        else:
            out.append("_")
    return "".join(out)


def _to_int_if_possible(val: Any) -> Optional[int]:
    try:
        if isinstance(val, bool):
            return int(val)
        if isinstance(val, (int, np.integer)):
            return int(val)
        if isinstance(val, (float, np.floating)):
            return int(round(float(val)))
        if isinstance(val, str) and val.strip() != "":
            return int(float(val))
    except (ValueError, TypeError):
        return None
    return None


def _load_oracle() -> None:
    global _MODEL, _SCALER, _FIRST6, _BOOL_COLS, _SEL_DICT
    if _MODEL is not None:
        return

    import joblib
    import tensorflow as tf

    base_df = pd.read_csv(Path(PATH) / "adult1.csv")
    _FIRST6 = base_df.columns[:6].tolist()
    _BOOL_COLS = base_df.columns[6 : 6 + 102].tolist()
    _SCALER = joblib.load(Path(PATH) / "scaler_first6.joblib")
    _MODEL = tf.keras.models.load_model(Path(PATH) / "nn_accept_reject_model.h5")

    with open(Path(PATH) / "sel_dicts" / "adult.json", "r", encoding="utf-8") as f:
        _SEL_DICT = json.load(f)


def _normalize_keys(row: Dict[str, Any]) -> Dict[str, Any]:
    """
    Provide alias keys so both typed and sanitized names are accepted.
    Example: marital-status -> marital_status.
    """
    out = dict(row)
    for key, val in list(row.items()):
        skey = _sanitize_token(key)
        if skey not in out:
            out[skey] = val
    return out


def _typed_or_encoded_to_onehot(cex: Dict[str, Any]) -> pd.DataFrame:
    """
    Convert a counterexample from typed/SMT format to one-hot NN input format.
    """
    _load_oracle()
    cex = _normalize_keys(cex)

    # Start from all-zero one-hot row.
    onehot_row: Dict[str, Any] = {col: 0.0 for col in (_FIRST6 + _BOOL_COLS)}

    # 1) Numeric features expected by the NN.
    for col in _FIRST6:
        if col in cex:
            try:
                onehot_row[col] = float(cex[col])
            except (ValueError, TypeError):
                onehot_row[col] = 0.0

    # 2) If cex already contains one-hot columns, use them directly.
    for col in _BOOL_COLS:
        if col in cex:
            onehot_row[col] = 1.0 if bool(cex[col]) else 0.0

    # 3) Map typed categorical values / indices to one-hot columns.
    for cat_col, options in _SEL_DICT.items():
        value = cex.get(cat_col, None)
        if value is None:
            value = cex.get(_sanitize_token(cat_col), None)
        if value is None:
            continue

        category = None
        idx = _to_int_if_possible(value)
        if idx is not None and 0 <= idx < len(options):
            category = options[idx]
        elif isinstance(value, str):
            # already a category name in typed domain
            category = value

        if category is None:
            continue

        onehot_col = f"{cat_col}__{_sanitize_token(category)}"
        if onehot_col in onehot_row:
            onehot_row[onehot_col] = 1.0

    return pd.DataFrame([onehot_row], columns=_FIRST6 + _BOOL_COLS)


def _predict_label(cex: Dict[str, Any]) -> int:
    """Return 1 for accepted, 0 for rejected."""
    _load_oracle()
    onehot_df = _typed_or_encoded_to_onehot(cex)

    x_num = _SCALER.transform(onehot_df[_FIRST6])
    x_bool = onehot_df[_BOOL_COLS].astype("float32").values
    x = np.hstack([x_num, x_bool]).astype("float32")

    proba = float(_MODEL.predict(x, batch_size=1, verbose=0).ravel()[0])
    return 1 if proba >= 0.5 else 0


def validate_counter_ex(cex: Dict[str, Any], url_end: str) -> str:
    
    return "accepted" if _predict_label(cex) == 1 else "rejected"
