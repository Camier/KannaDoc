# Code Node: Apply Patch Actions
# Inputs: micro_outline, patch_actions
# Output: micro_outline

def main(inputs):
    micro = inputs.get("micro_outline", {})
    actions = inputs.get("patch_actions", {}).get("patch_actions", [])
    
    if "_patch_log" not in micro:
        micro["_patch_log"] = []
        
    for action_item in actions:
        action_type = action_item.get("action")
        target_id = action_item.get("target_id")
        details = action_item.get("details", {})
        
        found = False
        # Traversal to find target
        for ch in micro.get("chapters", []):
            if ch.get("chapter_id") == target_id:
                found = True
                if action_type == "rename":
                    ch["title"] = details.get("new_title", ch["title"])
                elif action_type == "remove":
                    micro["chapters"].remove(ch)
                    break # Stop iteration on list mod
            
            for sec in ch.get("sections", []):
                if sec.get("section_id") == target_id:
                    found = True
                    if action_type == "rename":
                        sec["title"] = details.get("new_title", sec["title"])
                    elif action_type == "remove":
                        ch["sections"].remove(sec)
                        break
                        
                for sub in sec.get("subsections", []):
                    if sub.get("subsection_id") == target_id:
                        found = True
                        if action_type == "rename":
                            sub["title"] = details.get("new_title", sub["title"])
                        # Add source/query logic here
                        
        micro["_patch_log"].append({
            "action": action_type,
            "target": target_id,
            "success": found
        })
        
    return {"micro_outline": micro}