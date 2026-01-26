# Notes sur le Schéma Workflow Layra (Interne)

## 1. Loop Node
**Type:** `"loop"`

**Data:**
```json
{
  "loopType": "count", // ou "condition"
  "maxCount": "10",    // Si count. Peut être une variable {{len_axes}} ? A vérifier.
  "condition": "i < 10" // Si condition
}
```

**Edges (Connexions):**
Le nœud Loop a des "handles" spécifiques pour diriger le flux.

1.  **Entrée dans la boucle (Start Loop) :**
    *   Source: `loop_node`
    *   SourceHandle: `"loop_body"`
    *   Target: `first_node_inside`

2.  **Fermeture de l'itération (Next Iteration) :**
    *   Le dernier nœud de la séquence interne doit pointer vers le `loop_node`.
    *   Source: `last_node_inside`
    *   Target: `loop_node`

3.  **Sortie de la boucle (Loop Finished) :**
    *   Source: `loop_node`
    *   SourceHandle: `"loop_next"`
    *   Target: `node_after_loop`

**Mécanique d'itération sur liste :**
Layra ne semble pas avoir de "ForEach" natif sur une liste JSON. Il faut utiliser un pattern `Loop Index` + `Code Node`.
*   Le moteur maintient `loop_index` (int).
*   Dans la boucle, un Code Node doit faire : `current_item = my_list[loop_index]`.

## 2. Condition Node
**Type:** `"condition"`

**Data:**
```json
{
  "conditions": {
    "0": "variable == 'value'",
    "1": "variable != 'value'"
  }
}
```

**Edges:**
1.  **Branches :**
    *   Source: `condition_node`
    *   SourceHandle: `"condition-0"` (correspond à la clé "0")
    *   Target: `target_node_0`

## 3. Variables Globales
Accessibles partout. Les Code Nodes lisent/écrivent via `inputs` et return dict. Les LLM Nodes lisent via `{{var}}` et écrivent via `output_variable` (JSON parsing auto).
