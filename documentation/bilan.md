# Bilan et perspectives

## Ce qui a été réalisé

- Application web complète : équipements, sites, VLAN, contrôles ICMP/DNS/TCP avec historique, tableau de bord, authentification à deux profils, journal d'audit.
- Base PostgreSQL avec contraintes d'intégrité et migrations versionnées.
- Déploiement par Docker Compose, avec application automatique des migrations.
- Suite de tests automatiques exécutée en intégration continue.
- Documentation technique et guide utilisateur.

## Limites connues

- Les contrôles sont **lancés manuellement** : pas de planification automatique.
- Pas d'**HTTPS** natif (reverse proxy à ajouter), pas de **limitation des tentatives de connexion**, pas de **CSP**.
- L'état d'un équipement est celui de **son dernier contrôle**, tous types confondus.
- Les contrôles partent du serveur : ils dépendent de ce que ce serveur peut atteindre sur le réseau.
- Pas d'import/export des équipements (CSV).

## Perspectives

1. **Contrôles automatiques planifiés** avec alertes en cas de changement d'état.
2. **HTTPS** via Caddy ou Nginx, cookie de session `Secure`.
3. **Limitation des tentatives de connexion** et politique de mot de passe renforcée.
4. **Import/export CSV** des équipements.
5. **État par type de contrôle** (disponibilité ICMP distincte de la disponibilité d'un service TCP).
6. **Supervision SNMP** et récupération automatique des informations (modèle, version d'OS).
7. **Sauvegardes automatiques** de la base.
