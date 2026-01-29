# Code Node: Apply User Changes
# Inputs: micro_outline, user_changes
# Output: micro_outline

def main(inputs):
    micro = inputs.get("micro_outline", {})
    changes = inputs.get("user_changes", {}).get("changes", [])
    
    if "_user_log" not in micro:
        micro["_user_log"] = []
        
    for item in changes:
        # Same logic as patch, simplified for V2
        micro["_user_log"].append(item)
        
    return {"micro_outline": micro}