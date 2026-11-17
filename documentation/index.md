# Portail NetOps

Portail web de **gestion et de supervision d'une infrastructure réseau**, réalisé dans le cadre du module R504 (Cycle de vie d'un projet informatique), IUT de Kourou.

## Le besoin

Une entreprise multi-sites veut permettre à son équipe informatique de suivre son infrastructure réseau. Les informations sur les équipements étaient dispersées entre plusieurs fichiers et outils. Le portail les centralise et permet de **vérifier leur disponibilité**.

## Ce que fait l'application

- Recenser des **équipements** (switches, routeurs, firewalls, serveurs) avec leur adresse IP, leur type, leur constructeur, leur modèle, leur version d'OS, leur site, leurs VLAN et une description.
- **Rechercher et filtrer** les équipements (texte, type, site, constructeur, VLAN).
- Lancer des **contrôles** : ping (ICMP), résolution DNS, ouverture d'un port TCP, avec historique des résultats.
- Afficher un **tableau de bord** : équipements en ligne, hors ligne, jamais contrôlés, disponibilité, équipements à surveiller.
- Gérer deux **profils** : administrateur (créer, modifier, supprimer) et utilisateur (consulter uniquement).

## Technologies

| Rôle | Choix | Justification |
|---|---|---|
| Langage et framework | Python, Flask | Python permet de faire nativement les trois contrôles (ping, DNS, TCP) ; Flask est léger et facile à prendre en main à plusieurs |
| Base de données | PostgreSQL | Base relationnelle avec contraintes d'intégrité et types adaptés au réseau (`INET`, `CIDR`) |
| Accès aux données | SQLAlchemy, Alembic | Modèles en Python, requêtes paramétrées, migrations versionnées |
| Déploiement | Docker, docker-compose | Installation reproductible sur une machine vierge |
| Qualité | pytest, GitLab CI | Tests automatiques et pipeline |

## Où lire quoi

- Comprendre le besoin : [Cahier des charges](cahier-des-charges.md)
- Comprendre le code : [Architecture](architecture.md) et [Base de données](base-de-donnees.md)
- Installer : [Installation et déploiement](installation.md)
- Utiliser : [Guide utilisateur](guide-utilisateur.md)
