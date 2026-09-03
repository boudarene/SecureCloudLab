# Security notes

Ce dépôt est un laboratoire pédagogique.

- Ne jamais committer le fichier `.env`.
- Changer le mot de passe PostgreSQL avant tout déploiement.
- Pour Internet, ajouter TLS/HTTPS et un pare-feu hôte.
- Éviter d'exposer Prometheus publiquement sans authentification.
- Maintenir les images Docker et dépendances à jour.
