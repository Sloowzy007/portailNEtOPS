# Cahier des charges

!!! note "Document à relire et compléter par le groupe"
    Cette version est un point de départ rédigé à partir du sujet et de l'application réalisée.

## Contexte

Une entreprise disposant de plusieurs sites souhaite doter son équipe informatique d'un outil de suivi de son infrastructure réseau. Les informations sur les équipements sont réparties entre plusieurs fichiers et outils. L'équipe souhaite un **portail centralisé** permettant de consulter les équipements et de vérifier leur disponibilité.

## Objectifs

1. Centraliser l'inventaire des équipements réseau.
2. Permettre une recherche et un filtrage rapides.
3. Vérifier la disponibilité des équipements (ping, DNS, port TCP) et conserver l'historique.
4. Donner une vue synthétique de l'état de l'infrastructure.
5. Garantir que seuls les administrateurs peuvent modifier les données.

## Utilisateurs

| Profil | Droits |
|---|---|
| Administrateur | Créer, modifier, supprimer les équipements, sites et VLAN ; lancer des contrôles ; consulter |
| Utilisateur | Consulter uniquement |

## Fonctionnalités

- **Équipements** : créer, modifier, supprimer, consulter la fiche, rechercher et filtrer.
- **Informations minimales** : nom, adresse IP, type, constructeur, modèle, version d'OS, site, VLAN, description.
- **Sites et VLAN** : gestion des sites, des VLAN par site, association des VLAN aux équipements (un seul VLAN d'administration par équipement).
- **Supervision** : disponibilité ICMP, résolution DNS, ouverture d'un port TCP, date et résultat du dernier contrôle, historique.
- **Authentification** avec deux profils.
- **Tableau de bord** synthétique.
- **Journal d'audit** des actions de modification.

## Contraintes

- Projet versionné avec Git, hébergé sur une plateforme GitLab, avec branches et merge requests.
- Suite de tests automatisés et CI/CD.
- Documenté, déployable sur une machine vierge.
- **Aucun mot de passe ou secret dans Git.**
- Livré sous forme d'une version identifiée (v1.0.0).
- Technologies libres, avec justification des choix (voir la [Présentation](index.md)).

## Exigences de sécurité

- Mots de passe stockés sous forme de hash, jamais en clair.
- Contrôle d'accès par profil sur toutes les routes de modification.
- Protection contre les requêtes forgées (CSRF) sur tous les formulaires.
- Requêtes SQL paramétrées (pas d'injection SQL), échappement automatique des pages (pas de XSS).
- Entrées validées avant d'être utilisées dans un contrôle réseau (pas d'injection de commande).
- Secrets fournis par variables d'environnement (`.env` non versionné).

Détail dans la page [Sécurité](securite.md).

## Critères d'acceptation

| N° | Critère | Vérification |
|---|---|---|
| CA1 | Un utilisateur simple ne peut ni créer, ni modifier, ni supprimer un équipement | Test automatique `test_user_can_read_but_not_write` |
| CA2 | Un administrateur peut créer un équipement valide | `test_admin_creates_device` |
| CA3 | Une adresse IP invalide est refusée | `test_invalid_input_rejected` |
| CA4 | Deux équipements ne peuvent pas avoir la même IP sur un même site | `test_duplicate_ip_same_site_rejected` |
| CA5 | La recherche et les filtres retournent les bons équipements | `test_search_and_filters` |
| CA6 | Un contrôle TCP sur un port ouvert réussit, sur un port fermé échoue | `test_tcp_open`, `test_tcp_closed` |
| CA7 | Une résolution DNS inconnue échoue | `test_dns_failure` |
| CA8 | Une adresse malveillante n'est pas passée à la commande ping | `test_icmp_rejects_injection` |
| CA9 | Un mot de passe incorrect ne connecte pas | `test_login_wrong_password` |
| CA10 | Un seul VLAN d'administration par équipement | `test_only_one_management_vlan` |
| CA11 | Le tableau de bord reflète le dernier contrôle de chaque équipement | `test_stats_use_latest_check` |
| CA12 | L'application s'installe sur une machine vierge avec la documentation | Test manuel : voir [Installation](installation.md) |
