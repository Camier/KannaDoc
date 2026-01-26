# Optimisation des Transferts CPU→GPU pour ColQwen (Layra)

## État des Lieux (Janvier 2026)
Le système utilise actuellement **ColQwen2.5** via PyTorch sur une **RTX 5000**. Lors de l'ingestion massive du corpus de thèse, un goulot d'étranglement a été identifié au niveau du prétraitement des images et de leur transfert vers la VRAM.

### Améliorations Appliquées (V1 - Ingestion Actuelle) :
- **Batch Size :** Passé de 1 à 4 (meilleur débit GPU).
- **DataLoader :** Activation de `num_workers=2` et `pin_memory=True`.
- **Quantization :** Modèle chargé en **4-bit (NF4)** via `bitsandbytes` (réduction VRAM de ~7Go à ~3Go).
- **Attention :** Forçage de l'implémentation **SDPA** (native PyTorch) pour compenser l'absence de `flash-attn`.

## Optimisation Future : Transferts Non-Bloquants
L'analyse montre que les transferts mémoire entre la RAM et la VRAM sont actuellement **synchrones**. Le CPU "attend" que les pixels soient copiés sur le GPU avant de lancer l'inférence.

### Concept Clé : `non_blocking=True`
En combinant `pin_memory=True` dans le DataLoader et `non_blocking=True` dans l'appel `.to(device)`, on active le transfert **DMA (Direct Memory Access)** asynchrone.

**Gain attendu :** 
- Réduction de la latence de **10 à 30%**.
- Le CPU peut commencer à préparer le batch $N+1$ pendant que le batch $N$ est encore en train d'être copié vers le GPU.

### Plan de Mise en Œuvre (Post-Ingestion)

#### 1. Modification du `process_query` (`colbert_service.py`)
```python
# Actuel
batch_query = {k: v.to(self.model.device) for k, v in batch_query.items()}

# Optimisé
batch_query = {k: v.to(self.model.device, non_blocking=True) for k, v in batch_query.items()}
```

#### 2. Modification du `process_image` (`colbert_service.py`)
```python
# Actuel
batch_doc = {k: v.to(self.model.device) for k, v in batch_doc.items()}

# Optimisé
batch_doc = {k: v.to(self.model.device, non_blocking=True) for k, v in batch_doc.items()}
```

## Résumé Exécutif pour la Performance
| Technique | Statut | Impact |
| :--- | :--- | :--- |
| `pin_memory=True` | ✅ Activé | Prépare la RAM pour le DMA direct. |
| `num_workers > 0` | ✅ Activé (2) | Parallélise le décodage image sur CPU. |
| `non_blocking=True`| ⏳ À faire | Rend le transfert CPU->GPU asynchrone. |
| `batch_size=4` | ✅ Activé | Maximise l'occupation des CUDA cores. |

---
*Note : Cette optimisation nécessite que les tenseurs soient dans de la "Pinned Memory" (pagée), ce qui est déjà garanti par notre configuration actuelle du DataLoader.*
