#!/bin/sh
# Démarrage du conteneur web : applique les migrations de la base, puis lance la commande demandée
# (par défaut gunicorn, voir CMD dans le Dockerfile).
#
# POURQUOI : sans cette étape, il faudrait taper "flask db upgrade" à la main après chaque
# installation. Ici, "docker compose up" suffit pour obtenir une base prête.
# `set -e` : si la migration échoue, le conteneur s'arrête et l'erreur est visible dans les logs.
set -e

if [ -d /app/migrations ]; then
    echo "Application des migrations de la base..."
    flask --app wsgi db upgrade
else
    echo "ATTENTION : le dossier migrations/ est absent, la base n'est pas initialisée." >&2
fi

# `exec` remplace ce script par la commande (gunicorn) : il reçoit ainsi directement les signaux d'arrêt.
exec "$@"
