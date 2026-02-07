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
Etat reel (thesis corpus): voir `backend/docs/PIPELINE_AUDIT_2026-02-02.md` + la section ci-dessous.

<a id="kb-state-thesis"></a>
## Etat reel — Thesis Corpus (2026-02-07) ✅

Ce qui est vrai **maintenant** (verifie sur la stack locale):

- Corpus PDF: **129/129** dans `/LAB/@thesis/layra/backend/data/pdfs/`.
- Extractions: **129/129** dans `/LAB/@thesis/layra/backend/data/extractions/`.
- Milvus (docker-compose):
  - Patch vectors: `colpali_kanna_128` (`row_count`: **3,561,575**, dim=128)
    - Index: HNSW `metric=IP`, `M=32`, `efConstruction=500`
  - Page sparse sidecar: `colpali_kanna_128_pages_sparse` (`row_count`: **4,691**)
    - Index: `SPARSE_INVERTED_INDEX` `metric=IP`, `drop_ratio_build=0.2`
  - Alias KB (utilise par le backend):
    - `colqwenthesis_fbd5d3a6_3911_4be0_a4b3_864ec91bc3c1` -> `colpali_kanna_128`
- MongoDB (`chat_mongodb`) `knowledge_bases`:
  - `knowledge_base_id`: `thesis_fbd5d3a6-3911-4be0-a4b3-864ec91bc3c1` (129 fichiers)
  - Note: selon le mode, la collection Mongo `files` peut etre vide; la liste des fichiers peut etre
    portee par le doc `knowledge_bases.files`.
- Thesis preview assets:
  - Les `search-preview` renvoient des URLs type `/api/v1/thesis/page-image` (servees depuis les PDFs locaux),
    pas des presigned URLs MinIO.

Qualite des donnees (important):

- Le backend derive le nom de la sidecar sparse a partir du **vrai** nom de la collection (alias resolu).
- Page grouping doit etre fait sur `(file_id, page_number)` (pas `image_id`).

### Historical snapshot (2026-01-30, miko)

Cette section decrit un ancien etat "miko" et une consolidation effectuee en 2026-01.
Elle est conservee a titre historique et peut etre stale par rapport au corpus thesis actuel.

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

PATCH = "colpali_kanna_128"
SPARSE = "colpali_kanna_128_pages_sparse"
ALIAS = "colqwenthesis_fbd5d3a6_3911_4be0_a4b3_864ec91bc3c1"

client = MilvusClient(uri="http://milvus-standalone:19530")
print("collections:", client.list_collections())
print("patch row_count:", client.get_collection_stats(PATCH)["row_count"])
print("sparse row_count:", client.get_collection_stats(SPARSE)["row_count"])
print("alias:", client.describe_alias(ALIAS))
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

kb_id = "thesis_fbd5d3a6-3911-4be0-a4b3-864ec91bc3c1"
kb = db.knowledge_bases.find_one({"knowledge_base_id": kb_id}, {"knowledge_base_name": 1, "files": 1, "is_delete": 1})
print("kb:", {"id": kb_id, "name": (kb or {}).get("knowledge_base_name"), "is_delete": (kb or {}).get("is_delete")})
print("kb.files len:", len(((kb or {}).get("files")) or []))
print("files docs count:", db.files.count_documents({"knowledge_db_id": kb_id}))
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
