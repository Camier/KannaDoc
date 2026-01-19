# RUNBOOK — Docker Compose “clean env” (anti pollution)

## TL;DR (à faire systématiquement)

Dans ce repo, **ne lance pas** `docker compose ...` directement depuis un shell potentiellement pollué.

Utilise:

```bash
./compose-clean up -d --build
./compose-clean logs -f --tail=200 backend
./compose-clean ps
```

## Pourquoi c’est nécessaire (root cause)

Docker Compose fait de l’interpolation de variables (`${VAR}`) et la règle importante est:

> **Les variables exportées dans ton shell host prennent priorité sur les valeurs du fichier `.env`.**

Conséquence typique:
- tu as `MILVUS_URI=http://127.0.0.1:19530` exporté sur le host,
- le `docker-compose.yml` contient `MILVUS_URI=${MILVUS_URI}`,
- le container backend reçoit `MILVUS_URI=http://127.0.0.1:19530`,
- et **dans un container**, `127.0.0.1` pointe sur lui-même → backend ne peut pas joindre Milvus (`milvus-standalone`), crash/erreurs.

## Le wrapper `./compose-clean`

`./compose-clean` est un wrapper qui:
- force l’exécution depuis la racine du repo (là où `.env` est attendu),
- force `--env-file .env`,
- lance `docker compose` sous un environnement *quasi vide* (`env -i`),
- ne préserve que quelques variables host nécessaires à Docker (PATH/HOME/DOCKER_*…),
- empêche donc l’override silencieux de `.env` par ton shell.

Afficher l’aide:

```bash
./compose-clean --help
```

## Commandes “standard” (safe)

### Démarrer / rebuild
```bash
./compose-clean up -d --build
```

### Recreate ciblé (ex: backend + nginx)
```bash
./compose-clean up -d --build --force-recreate backend nginx
```

### Logs
```bash
./compose-clean logs -f --tail=200 backend
./compose-clean logs -f --tail=200 kafka
```

### Shell / exec dans un container
```bash
./compose-clean exec -T backend python -V
```

### Arrêt / nettoyage
```bash
./compose-clean stop
./compose-clean down
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
./compose-clean ...
./start_layra.sh
```
