# RUNBOOK — Docker Compose “clean env” (anti pollution)

## TL;DR (à faire systématiquement)

Dans ce repo, **ne lance pas** `docker compose ...` directement depuis un shell potentiellement pollué.

Utilise:

```bash
./scripts/compose-clean up -d --build
./scripts/compose-clean logs -f --tail=200 backend
./scripts/compose-clean ps
```

Diagramme de déploiement (vue minimale): [DEPLOYMENT_DIAGRAM](DEPLOYMENT_DIAGRAM.md)
Etat reel (KB miko): voir la section "Etat reel — Thesis Corpus (2026-01-29)" plus bas.

<a id="kb-state-miko"></a>
## Etat reel — Thesis Corpus (2026-01-30) ✅ CONSOLIDATED

Ce qui est vrai **maintenant** (verifie sur la stack locale):

- Corpus PDF: 129/129 fichiers dans `/app/literature/corpus`.
- Embeddings: 129/129 JSON dans `/app/embeddings_output`.
- Milvus:
  - **Collection active (unique)** `colqwenmiko_e6643365_8b03_4bea_a69b_7a1df00ec653`
    - `row_count`: **3,562,057** vectors
    - `file_id` prefix: `miko_`
    - Fields: `pk`, `vector`, `sparse_vector`, `image_id`, `page_number`, `file_id`
    - Index: HNSW M=48, efConstruction=1024
  - ~~Collection legacy `thesis_fbd5d3a6...`~~ **DELETED** (2026-01-30)
- MongoDB `knowledge_bases`:
  - `knowledge_base_id`: `miko_e6643365-8b03_4bea-a69b_7a1df00ec653` (129 fichiers, active)
  - `knowledge_base_id`: `miko_0ecb4105-9d53-4214-9884-1a17b0743b47` (empty smoke test)
  - ~~`thesis_fbd5d3a6...`~~ **DELETED** (was duplicate with schema drift)
- MongoDB `files` (KB miko):
  - 129 docs `miko_`
  - images totales: **5,732**
  - `minio_url` manquant: **0** (toutes presignees)
  - `minio_filename` manquant: **0**
- MinIO (bucket `minio-file`):
  - objets totaux: **5,862** (129 PDFs + 5,733 images)
  - images miko verifiees: **5,732/5,732** presentes
  - ~~`thesis/` prefix~~ **DELETED** (129 duplicate PDFs removed)
- Utilisateurs (MySQL): **existant** (au moins `miko`, `thesis`, + users de test).
  UI login: `thesis` / `thesis123` (password reset 2026-01-30).

Qualite des donnees (important):

- **Mismatch resolu**: 129/129 `file_id` du KB actif (`miko_...`) ont des embeddings dans Milvus.
- **Vectors per image**: ~621 (ColQwen multi-vector embeddings).
- Embeddings: dim mismatch **0**; NaN/Inf **sanitize 482** vecteurs (PDF `2025 - ed. - The Indigenous World.pdf`).
- `files` `miko_`: images totales = **5,732**; `minio_url` manquant **0**.
- MinIO: tous les `minio_filename` des images miko existent.
- **Sparse vectors**: present in collection, ready for hybrid search.

### Consolidation effectuee (2026-01-30)

| Action | Details |
|--------|---------|
| Soft deleted thesis_fbd KB | `is_delete: true` in MongoDB |
| Hard deleted thesis_fbd KB | MongoDB KB doc + 396 file docs removed |
| Dropped thesis Milvus collection | 4.3M vectors removed |
| Dropped empty miko_0ecb collection | 0 vectors, smoke test artifact |
| Deleted MinIO thesis/ prefix | 129 duplicate PDFs removed |
| Preserved shared images | 5,732 images kept (used by miko KB) |
| Verified RAG pipeline | embed: 0.64s, search: 7.4s, LLM: 200 OK |

Note Milvus:

- `get_collection_stats` peut retourner `row_count: 0` meme si des vecteurs existent.
  Verifier via `search` (voir commande ci-dessous).
- Milvus 2.6 utilise `MINIO_ACCESS_KEY_ID` / `MINIO_SECRET_ACCESS_KEY`.
  Si erreur “Access Key Id …”, verifier les env sur `milvus-standalone`.

Commandes de verification (dans le container backend):

```bash
# Milvus: confirmer presence de vecteurs par un search
python3 - <<'PY'
import json, os
from pymilvus import MilvusClient

COLLECTION = "colqwenmiko_e6643365_8b03_4bea_a69b_7a1df00ec653"

client = MilvusClient(uri="http://milvus-standalone:19530")
stats = client.get_collection_stats(COLLECTION)
print("collection:", COLLECTION)
print("row_count:", stats["row_count"])
print("collections:", client.list_collections())
client.close()
PY

# MongoDB: etat KB + verif images
python3 - <<'PY'
import os
from pymongo import MongoClient

user = os.environ.get("MONGODB_ROOT_USERNAME")
password = os.environ.get("MONGODB_ROOT_PASSWORD")
uri = f"mongodb://{user}:{password}@mongodb:27017/admin"
mc = MongoClient(uri)
db = mc.chat_mongodb

print("knowledge_bases:")
for kb in db.knowledge_bases.find({}, {"knowledge_base_id": 1, "username": 1, "is_delete": 1}):
    print(" -", kb.get("knowledge_base_id"), "is_delete:", kb.get("is_delete", False))

kb_id = "miko_e6643365-8b03_4bea-a69b_7a1df00ec653"
stats = {"files": 0, "images_total": 0, "missing_minio_url": 0}
for doc in db.files.find({"knowledge_db_id": kb_id}, {"images": 1}):
    stats["files"] += 1
    for img in doc.get("images", []):
        stats["images_total"] += 1
        if not img.get("minio_url"):
            stats["missing_minio_url"] += 1

print("miko_stats:", stats)
mc.close()
PY
```

## Pourquoi c’est nécessaire (root cause)

Docker Compose fait de l’interpolation de variables (`${VAR}`) et la règle importante est:

> **Les variables exportées dans ton shell host prennent priorité sur les valeurs du fichier `.env`.**

Conséquence typique:
- tu as `MILVUS_URI=http://127.0.0.1:19530` exporté sur le host,
- le `docker-compose.yml` contient `MILVUS_URI=${MILVUS_URI}`,
- le container backend reçoit `MILVUS_URI=http://127.0.0.1:19530`,
- et **dans un container**, `127.0.0.1` pointe sur lui-même → backend ne peut pas joindre Milvus (`milvus-standalone`), crash/erreurs.

## Le wrapper `./scripts/compose-clean`

`./scripts/compose-clean` est un wrapper qui:
- force l’exécution depuis la racine du repo (là où `.env` est attendu),
- force `--env-file .env`,
- lance `docker compose` sous un environnement *quasi vide* (`env -i`),
- ne préserve que quelques variables host nécessaires à Docker (PATH/HOME/DOCKER_*…),
- empêche donc l’override silencieux de `.env` par ton shell.

Afficher l’aide:

```bash
./scripts/compose-clean --help
```

## Commandes “standard” (safe)

### Démarrer / rebuild
```bash
./scripts/compose-clean up -d --build
```

### Recreate ciblé (ex: backend + nginx)
```bash
./scripts/compose-clean up -d --build --force-recreate backend nginx
```

### Logs
```bash
./scripts/compose-clean logs -f --tail=200 backend
./scripts/compose-clean logs -f --tail=200 kafka
```

### Shell / exec dans un container
```bash
./scripts/compose-clean exec -T backend python -V
```

### Arrêt / nettoyage
```bash
./scripts/compose-clean stop
./scripts/compose-clean down
```

## Debug “pollution” (sans afficher de secrets)

Pour vérifier si ton shell est pollué par des variables de la stack, fais juste un “presence check”
(ne dump pas les valeurs si c’est sensible):

```bash
env | rg -n '^(MILVUS_URI|DB_URL|MONGODB_URL|REDIS_URL|SECRET_KEY|MYSQL_PASSWORD)=' || true
```

## Bonus: éviter les expansions `$...` et backticks dans les rapports/scripts

Si tu génères des fichiers “report”/markdown/config via heredoc, **quote le delimiter** pour empêcher:
- `${VAR}` (expansion)
- `` `cmd` `` (exécution)

Safe patterns:

```bash
python - <<'PY' > artifacts/report.md
print("ACCESS_TOKEN_EXPIRE_MINUTES=11520")
PY

cat <<'EOF' > artifacts/report.txt
Littéral: ${NE_SERA_PAS_EXPANSE}
Littéral: `ne_sera_pas_execute`
EOF
```

## Hygiène repo / secrets (à appliquer)

### 1) Ne jamais committer `.env`

- `.env` contient des secrets (tokens, passwords, `SECRET_KEY`, etc.) et **ne doit pas être versionné**.
- Dans ce repo, `.gitignore` ignore `.env`.
- Workflow recommandé:

```bash
cp .env.example .env
$EDITOR .env
```

Si `.env` a déjà été commité dans ton historique git, il faut aussi le retirer de l’index (sans effacer ton fichier local):

```bash
git rm --cached .env
```

### 2) Artifacts / transcripts / fichiers de session

- Tout ce qui est dans `artifacts/` est considéré comme **local** (rapports, logs, audits) et est ignoré par git.
- Les transcripts type `session-ses_*.md` doivent rester hors des fichiers versionnés (risque de fuite d’infos + bruit).

### 3) Quarantaine des scripts “dangereux”

Si tu vois des scripts qui:
- modifient `.env` automatiquement,
- ou génèrent des fichiers via heredoc non-quoté,

considère-les comme “quarantaine” et ne les utilise pas pour opérer la stack. Dans ce repo, le chemin “safe” est:

```bash
./scripts/compose-clean ...
./scripts/start_layra.sh
```
