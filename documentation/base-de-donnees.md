# Base de données

PostgreSQL, accessible via SQLAlchemy. Le schéma évolue par **migrations Alembic** (dossier `backend/migrations/`).

## Tables

| Table | Rôle | Points importants |
|---|---|---|
| `users` | Comptes du portail | `login` et `email` uniques, `password_hash`, `role` limité à `admin` ou `user` |
| `sites` | Lieux de l'entreprise | `site_name` unique |
| `vlans` | VLAN de chaque site | numéro de 1 à 4094, unique par site, sous-réseau de type `CIDR` |
| `devices` | Équipements (table centrale) | adresse `INET`, type limité à `switch`, `router`, `firewall`, `server`, `hostname` et IP uniques par site |
| `devices_vlans` | Quel équipement est dans quel VLAN | interface, un seul VLAN d'administration par équipement |
| `checks` | Historique des contrôles | type `icmp`, `dns` ou `tcp`, résultat `success` ou `failure`, port obligatoire pour TCP |
| `audit_logs` | Journal des actions | qui, quoi, quelle ligne, détails avant/après (`JSONB`) |

## Relations

```text
sites 1 ──── n vlans
sites 1 ──── n devices
devices n ──── n vlans        (via devices_vlans)
devices 1 ──── n checks
users 1 ──── n devices        (créateur)
users 1 ──── n checks, audit_logs   (auteur)
```

## Contraintes et règles de suppression

| Mécanisme | Où | Pourquoi |
|---|---|---|
| `UNIQUE` composite `(site_id, ip_address)` et `(site_id, hostname)` | `devices` | Pas de doublon sur un même site |
| `CHECK` sur les rôles, types, résultats, numéro de VLAN | plusieurs tables | La base refuse une valeur incohérente même si le code se trompe |
| Index unique partiel `WHERE is_management` | `devices_vlans` | Un seul VLAN d'administration par équipement |
| `ON DELETE CASCADE` | `checks`, `devices_vlans`, `vlans` | Supprimer un équipement supprime son historique |
| `ON DELETE RESTRICT` | `devices.site_id` | On ne supprime pas un site qui contient des équipements |
| `ON DELETE SET NULL` | auteurs (`users`) | Supprimer un compte conserve l'historique |

## Migrations

```bash
docker compose exec web flask db migrate -m "description"   # génère un fichier de migration
docker compose exec web flask db upgrade                    # applique les migrations
```

Les migrations sont appliquées automatiquement au démarrage du conteneur `web`. Un fichier de migration généré dans le conteneur doit être copié dans le dépôt avant toute reconstruction de l'image :

```bash
docker compose cp web:/app/migrations/versions/. ./backend/migrations/versions/
```

## Sauvegarde et restauration

<!-- À COMPLÉTER par le membre BDD après test réel -->
Voir la procédure de sauvegarde (`pg_dump`) et de restauration (`psql`) à rédiger et à tester.
