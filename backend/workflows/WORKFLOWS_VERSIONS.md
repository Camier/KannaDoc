# Workflows - Versions et Expérimentation

## 📁 Structure des Workflows

```
backend/workflows/
├── thesis_plan_fr_interconnexions/        # Version ACTIVE (modifiable)
├── thesis_plan_fr_interconnexions_bak_20260207/  # Sauvegarde (read-only)
├── thesis_plan_fr_interconnexions_exp/     # Version EXPÉRIMENTALE (pour tests)
├── thesis_blueprint_minutieux/             # Référence (ne pas modifier)
└── thesis_blueprint_v3/                    # Référence (ne pas modifier)
```

---

## 🔄 Versions Disponibles

### 1. `thesis_plan_fr_interconnexions` ⚡ **ACTIVE**
- **Statut**: Version active utilisée pour les générations
- **Date dernière modif**: 2026-02-07 20:54
- **Fichiers**:
  - `run.py` (55KB) - Runner principal avec HARD RAG
  - `touch_and_go.py` - Validateur
  - `patch_pont_fins.py` - Correctif ponts fins
  - `slim_plan.py` - Compresseur de plan
  - `outputs/` - 59 fichiers de sortie

**État**: Fonctionnel avec correctifs déterministes (headfix, pontpatch, xlinksfix)

---

### 2. `thesis_plan_fr_interconnexions_bak_20260207` 💾 **SAUVEGARDE**
- **Statut**: Snapshot figé du 2026-02-07
- **Usage**: Référence en cas de problème
- **Contenu**: Copie complète de la version active (tous les outputs inclus)

⚠️ **NE PAS MODIFIER** - Cette version sert de référence

---

### 3. `thesis_plan_fr_interconnexions_exp` 🧪 **EXPÉRIMENTAL**
- **Statut**: Zone de test sûre
- **Usage**: Essayer des modifications risquées
- **Fichiers copiés**:
  - `run.py`
  - `touch_and_go.py`
  - `patch_pont_fins.py`
  - `slim_plan.py`
  - `README.md`
  - `outputs/` (vide, pour nouveaux tests)

**Idées d'expérimentation**:
- Split de `part3_system` en nodes séparés
- Nouveaux prompts anti-hallucination
- Validation progressive après chaque part

---

## 🚀 Workflow d'Expérimentation Recommandé

```bash
# 1. Partir de la version expérimentale
cd backend/workflows/thesis_plan_fr_interconnexions_exp/

# 2. Faire les modifications
# (éditer run.py, touch_and_go.py, etc.)

# 3. Tester sur un sujet simple
python3 -u run.py --hard-rag --max-repair-iter 1

# 4. Si ça marche, merger dans la version active
cp run.py ../thesis_plan_fr_interconnexions/

# 5. Sinon, restaurer depuis la sauvegarde
cp ../thesis_plan_fr_interconnexions_bak_20260207/run.py run.py
```

---

## 📊 État Actuel du Workflow Actif

| Composant | État | Notes |
|-----------|------|-------|
| `run.py` | ✅ Fonctionnel | HARD RAG + fixes déterministes |
| `touch_and_go.py` | ✅ Fonctionnel | Accepte "Pont fin :" et "Pont fin:" |
| `patch_pont_fins.py` | ✅ Fonctionnel | Regex améliorée |
| `slim_plan.py` | ✅ Fonctionnel | Réduit verbosité de 57% |
| Dernier output valide | ✅ OK | `plan_999..._slim.md` - 228 lignes |

---

## 🔧 Modifications Récentes (dans run.py)

1. **HARD RAG** (Stage 0) :
   - `_list_knowledge_bases()` - Liste les KB
   - `_pick_default_kb_id()` - Choix automatique
   - `_ensure_base_used()` - Force base_used

2. **Correctifs déterministes** :
   - `_maybe_local_fix_heading_levels()` - Corrige #### ###
   - `_maybe_local_fix_crosslinks_and_mermaid()` - 12 liens + Mermaid
   - `_rewrite_mermaid_block()` - Reconstruction cohérente

3. **Prompts durcis** :
   - "Ne pas produire de JSON"
   - "Pas de faits chiffrés inventés"
   - Puces ≤ 14 mots
   - 1 lien immuno ↔ addiction requis

---

*Document créé le 2026-02-07*
