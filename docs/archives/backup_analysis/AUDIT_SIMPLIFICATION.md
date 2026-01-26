# Audit des Simplifications (Thesis Workflow)

## Écarts Identifiés dans `deploy_thesis_workflow_full.py`

Le script actuel ne respecte pas la spécification "Master" sur les points suivants :

### 1. Structure du Workflow (Graphe)
- **KB Mapping Loop :** Remplacée par un nœud unique `node_kb_map` (KB Cartographer) en mode "One-Shot".
    - *Attendu :* Loop sur `seed_axes` -> RAG par axe -> Accumulation.
    - *Preuve :* Ligne 115-130 dans le script actuel.
- **Micro Outline Loop :** Remplacée par un nœud unique `node_micro` (Micro Outline Detailed).
    - *Attendu :* Loop sur `chapters` -> Micro Outline par chapitre -> Append.
    - *Preuve :* Ligne 145-156.
- **Section Coverage Loop :** Totalement absente.
- **Human Review Gate :** Totalement absent.
- **Coherence Check :** Totalement absent.

### 2. Prompts
- **Inline vs Fichier :** Le script utilise des `f-strings` ou des chaînes littérales pour certains nœuds au lieu de charger les fichiers `.txt` créés.
    - *Exemple :* Ligne 121 `system_prompt: "You are mapping the Knowledge Base..."`.
    - *Attendu :* `prompts["kb_retrieve"]`.

### 3. Code Nodes Manquants
Les scripts suivants n'ont pas été intégrés ou n'ont pas de nœuds correspondants :
- `parse_seed_axes_json.py`
- `append_to_micro_outline.py`
- `merge_sources_into_micro_outline.py`
- `coverage_scoring.py` (Node manquant)
- `apply_patch_actions.py`
- `apply_user_changes.py`

### 4. Variables Globales
- Initialisation correcte mais incomplète (manque `coverage`, `patch_actions`, etc. dans le flux de données).

## Conclusion
Le déploiement actuel est une version "MVP" (Minimum Viable Product) linéaire qui ne répond pas à l'exigence de "minutie" et de robustesse par itération. La V2 doit réimplémenter la logique de boucle et de condition.
