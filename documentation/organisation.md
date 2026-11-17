# Organisation du projet

!!! note "À valider par tout le groupe"
    Cette page décrit l'organisation réelle du projet. Chaque membre vérifie ce qui le concerne.

## Équipe

| Membre | Responsabilités principales |
|---|---|
| Myindia JOSEPH | Application Flask, authentification, contrôles réseau, déploiement Docker |
| Kinberly LAURISTIN | Base de données, migrations, guide utilisateur |
| Staley TALENT | Dépôt, intégration continue, tests d'intégration, release |

## Méthode de travail

- **Issues et milestones** pour planifier les tâches, avec une personne assignée et une échéance.
- **Une branche par tâche** (`feature/<n°>-nom`), jamais de commit direct sur `main`.
- **Merge requests relues** par un autre membre avant la fusion.
- **Tests automatiques** à chaque modification.

## Chronologie

D'après l'historique Git du dépôt.

| Période | Étape |
|---|---|
| Fin octobre 2026 | Analyse du sujet, choix des technologies, schéma de base de données |
| Début novembre | Squelette Flask et Docker, modèles, authentification |
| Semaine du 8 novembre | Contrôles réseau, CRUD, VLAN, tableau de bord, version de démonstration |
| Mi-novembre | Docker avec PostgreSQL, migrations, documentation |
| 19 novembre 2026 | Livraison v1.0.0 |

## Usage d'un assistant d'IA

Un assistant d'IA (Claude, d'Anthropic) a été utilisé comme aide à la conception et à la rédaction du code, des tests et de la documentation. Le fonctionnement a été vérifié par une suite de tests automatiques.
