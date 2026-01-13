# src/state.py
import json, os

def load_state(state_path):
    """
    Returns a dict with at least the key 'processed_ids' (list).
    Handles missing file, null JSON, or malformed JSON by returning a default.
    """
    if os.path.exists(state_path):
        try:
            with open(state_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if not isinstance(data, dict):
                    # if file contains null or non-dict, return default
                    return {"processed_ids": []}
                # ensure key exists
                if "processed_ids" not in data or not isinstance(data["processed_ids"], list):
                    data["processed_ids"] = list(data.get("processed_ids") or [])
                return data
        except (json.JSONDecodeError, ValueError):
            # malformed file -> return default
            return {"processed_ids": []}
        except Exception:
            # any other read error -> return default (safe fallback)
            return {"processed_ids": []}
    # file doesn't exist -> default
    return {"processed_ids": []}

def save_state(state_path, state):
    os.makedirs(os.path.dirname(state_path) or ".", exist_ok=True)
    # ensure saved structure is serializable and contains processed_ids list
    out = {
        "processed_ids": list(state.get("processed_ids", []))
    }
    with open(state_path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
