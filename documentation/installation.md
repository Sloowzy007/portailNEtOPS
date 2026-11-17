# Installation et déploiement

## Prérequis

- Une machine Linux (ou Windows/macOS avec Docker Desktop) avec **Docker** et **Docker Compose**.
- **Git**.
- Les ports **8000** (application) libre.

Vérification :

```bash
docker --version
docker compose version
```

## Installation sur une machine vierge

```bash
git clone <adresse du dépôt>
cd <dossier du dépôt>
cp .env.example .env
```

Éditer `.env` et **remplacer toutes les valeurs `CHANGE_ME`** : mot de passe de la base (aux deux endroits où il apparaît : `POSTGRES_PASSWORD` et `DATABASE_URL`) et `SECRET_KEY`. Pour générer des valeurs aléatoires :

```bash
openssl rand -hex 32
```

Puis :

```bash
docker compose up -d --build
docker compose exec web flask create-admin
```

Les migrations de la base sont appliquées automatiquement au démarrage. L'application est disponible sur `http://localhost:8000`. Se connecter avec le compte administrateur créé.

!!! warning "Le fichier .env ne doit jamais être commité"
    Il contient les secrets de l'installation. Il est exclu par `.gitignore`.

## Commandes utiles

| Action | Commande |
|---|---|
| Voir l'état des conteneurs | `docker compose ps` |
| Suivre les logs de l'application | `docker compose logs -f web` |
| Arrêter | `docker compose down` |
| Arrêter **et supprimer la base** | `docker compose down -v` |
| Mettre à jour après un `git pull` | `docker compose up -d --build` |
| Créer un administrateur | `docker compose exec web flask create-admin` |

## Fonctionnement des conteneurs

- **db** : image `postgres:16`, données dans le volume `pgdata`, vérification de santé avant le démarrage de `web`.
- **web** : image construite depuis `backend/Dockerfile` (Python 3.12, gunicorn avec workers à threads). Le paquet `iputils-ping` est installé pour le contrôle ICMP, et la capacité réseau `NET_RAW` est accordée au conteneur pour qu'il puisse lancer un ping.
- Au démarrage, `entrypoint.sh` applique les migrations (`flask db upgrade`) puis lance gunicorn.

## Utilisation pour le développement (sans Docker)

```bash
cd backend
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python -m pytest -q
```

Les tests utilisent une base SQLite en mémoire et n'ont pas besoin de PostgreSQL.

## Problèmes fréquents

| Symptôme | Cause probable | Solution |
|---|---|---|
| `externally-managed-environment` au `pip install` | Debian refuse l'installation hors environnement virtuel | Créer et activer un venv (voir ci-dessus) |
| Le ping échoue dans le conteneur | Capacité `NET_RAW` ou commande `ping` absente | Vérifier `cap_add: NET_RAW` dans `docker-compose.yml` et reconstruire l'image |
| `Can't locate revision ...` | Le fichier de migration n'est plus présent alors que la base le connaît | Le dossier `migrations/` doit être versionné dans le dépôt ; recréer la base avec `docker compose down -v` en dev |
| La première page met longtemps à s'afficher | Anciennes versions : workers gunicorn bloqués par des connexions inactives | Corrigé : workers à threads dans le `Dockerfile` |
| Les mots de passe `.env` ne correspondent pas | `POSTGRES_PASSWORD` et `DATABASE_URL` différents | Mettre la même valeur aux deux endroits, puis `docker compose down -v` et relancer |

## Sauvegarde et restauration

<!-- À COMPLÉTER par le membre BDD après test réel -->
Procédure `pg_dump` / `psql` à documenter et à tester.

## HTTPS

Le schéma du sujet prévoit un accès en HTTPS. L'application écoute en HTTP sur le port 8000 : en exploitation, on la place derrière un reverse proxy (Caddy ou Nginx) qui gère le certificat. Voir [Bilan et perspectives](bilan.md).
