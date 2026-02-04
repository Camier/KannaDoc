# Code Node: Parse Seed Axes (Layra Protocol)
def main(inputs):
    import json

    raw_data = inputs.get("seed_axes_json", "{}")

    # Layra variables are usually string-wrapped python objects
    if isinstance(raw_data, str):
        try:
            # Try to strip markdown and load
            clean = raw_data
            if "```json" in raw_data:
                clean = raw_data.split("```json")[1].split("```")[0]
            data = json.loads(clean)
        except (json.JSONDecodeError, ValueError, IndexError):
            data = {}
    else:
        data = raw_data

    axes = data.get("seed_axes", [])
    if not axes and "axes" in data:
        axes = data["axes"]

    print("####Global variable updated####")
    print(f"seed_axes = {json.dumps(axes)}")
    print(f"axes_count = {len(axes)}")
    print(f"loop_idx = 0")
