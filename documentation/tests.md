# Tests

## Stratégie

| Type | Objectif | Exemple |
|---|---|---|
| **Unitaires** | Vérifier une fonction isolée | `check_tcp` sur un port ouvert / fermé |
| **Intégration** | Vérifier que plusieurs parties fonctionnent ensemble (route, base, templates) | création d'un équipement par le formulaire, puis affichage |
| **Qualification** | Vérifier que le produit respecte le cahier des charges | tableau des [critères d'acceptation](cahier-des-charges.md#criteres-dacceptation) |

## Lancer les tests

```bash
cd backend
. .venv/bin/activate
python -m pytest -q
```

Avec la couverture de code :

```bash
pip install pytest-cov
python -m pytest --cov=app --cov-report=term
```

## Organisation

| Fichier | Contenu |
|---|---|
| `tests/test_models.py` | contraintes de la base, mots de passe hachés |
| `tests/test_auth.py` | connexion, déconnexion, rôles, redirection sécurisée, journal d'audit |
| `tests/test_checks.py` | contrôles ICMP, DNS, TCP et enregistrement de l'historique |
| `tests/test_devices.py` | CRUD équipements et sites, recherche, filtres, pagination, droits |
| `tests/test_vlans.py` | VLAN, association aux équipements, VLAN d'administration unique |
| `tests/test_dashboard.py` | calcul des indicateurs du tableau de bord |

Les tests utilisent une base SQLite en mémoire : ils sont rapides et n'ont pas besoin de PostgreSQL. Les types spécifiques à PostgreSQL (`INET`, `CIDR`, `JSONB`) ont un repli en texte pour SQLite.

## Résultats

<!-- À METTRE À JOUR avant la livraison : nombre de tests et couverture issus de la CI -->
Au 15 novembre 2026 : **70 tests automatiques** sur la branche principale, tous réussis.

La suite complète a également été exécutée contre un PostgreSQL réel pour vérifier les types et contraintes propres à PostgreSQL.

## Tests manuels

Le contrôle ICMP dépend de la commande `ping` du système et d'un réseau réel : il est vérifié manuellement dans le conteneur Docker (voir [Installation](installation.md)).
