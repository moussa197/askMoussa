# Projets de Moussa Keita

## Ask Moussa — chatbot IA (RAG)
- Technologies : Python, FastAPI, API Claude (modèle Haiku), embeddings, pytest, JavaScript
- Type : projet personnel
- Statut : en cours de développement (septembre 2026)

Moussa a conçu un chatbot intégré à son portfolio qui répond aux questions des visiteurs sur son parcours. Il utilise la technique RAG (Retrieval-Augmented Generation) : les documents de Moussa sont découpés en morceaux, transformés en vecteurs, puis les passages les plus pertinents sont retrouvés et transmis au modèle de langage, qui rédige une réponse fondée uniquement sur ces informations, sans rien inventer.

Moussa a mené ce projet en tant que superviseur d'un flux de développement assisté par IA (Claude Code et ses agents) : il a défini l'architecture, validé chaque étape, relu et testé le code, et géré lui-même les commits. Le projet comprend des tests automatisés, une protection de la clé API, une limite de requêtes et une protection contre les tentatives de détournement du chatbot.

## MemoMakerr — application de bureau de souvenirs de voyage
- Technologies : Java 21, JavaFX (FXML, CSS), MySQL, JDBC, Maven, Leaflet.js, OpenStreetMap, Gson, BCrypt, JUnit 5, Javadoc
- Type : projet de groupe de fin de semestre, réalisé à l'ESEO pendant la première année de Bachelor (année universitaire 2025-2026)
- Équipe : 4 étudiants

MemoMakerr est une application de bureau destinée aux voyageurs, développée en équipe de quatre. Elle permet de créer des voyages, d'y ajouter des souvenirs associés à des lieux, avec des photos et une émotion (joie, nostalgie, amour, aventure, tristesse), puis de revoir son historique sur une carte interactive, une timeline et des statistiques.

Fonctionnalités : création de compte et connexion, gestion des voyages et des souvenirs, galerie de photos, recherche de villes, carte interactive avec des marqueurs colorés selon l'émotion et le tracé de l'itinéraire entre les étapes, timeline chronologique, fonctionnalité « Ce jour-là » qui retrouve les souvenirs vécus à la même date les années précédentes, badges, espace d'administration, et un bilan annuel façon « Wrapped » partageable sous forme de page web.

Aspects techniques : l'application suit une architecture MVC. Les écrans FXML passent par des contrôleurs JavaFX, qui appellent des services métier, eux-mêmes reliés à la base MySQL par des DAO et des requêtes SQL préparées. La carte est réalisée avec Leaflet.js et OpenStreetMap, intégrée dans l'application JavaFX, et la recherche de villes utilise l'API Nominatim d'OpenStreetMap. Les statistiques comprennent le nombre de pays visités, les émotions dominantes, le mois le plus actif et la distance totale parcourue, calculée avec la formule de Haversine. Le bilan annuel est converti en JSON puis encodé dans une URL de partage, sans jamais inclure les chemins locaux des photos.

Sécurité et qualité : les mots de passe sont hachés avec BCrypt, l'application gère les sessions et les rôles des utilisateurs, et le projet comprend des tests unitaires JUnit 5 ainsi qu'une documentation Javadoc.

Rôle de Moussa : Moussa a occupé plusieurs rôles au fil du projet, en alternant entre product manager, Scrum Master, lead développeur et développeur. En tant que product manager, il a contribué à définir les fonctionnalités et leurs priorités ; en tant que Scrum Master, il a animé l'organisation de l'équipe et le suivi des tâches ; en tant que lead développeur et développeur, il a participé aux choix techniques et au développement de l'application.

Organisation : l'équipe a travaillé selon la méthode Agile. Le code était partagé et versionné avec Git, et les tâches étaient réparties et suivies sur un tableau Trello.

Ce que Moussa a appris : passer d'un rôle à l'autre au sein d'une même équipe, de la vision produit à l'organisation du travail et au développement ; mener un projet en méthode Agile de la conception à la livraison ; structurer une application Java complète en architecture MVC, avec une base de données MySQL ; et intégrer des outils externes, comme une carte interactive et une API de géolocalisation, dans une application de bureau.

## Letterix — plateforme de jeux de lettres (Motus et mots mêlés)
- Technologies : PHP, MySQL, SQL, JavaScript, HTML, CSS
- Type : projet de groupe réalisé dans le cadre du cours de développement web à l'ESEO
- Équipe : 4 étudiants
- Code source : https://github.com/LoanKma/projet-web-v2

Letterix est une plateforme web de jeux de lettres développée en équipe de quatre. Ce projet de cours avait pour objectif de réunir dans une seule application tout ce qui avait été appris en HTML, CSS, JavaScript, PHP et MySQL.

Fonctionnement : le joueur arrive sur une page d'accueil et choisit entre deux jeux, un Motus et un jeu de mots mêlés. Les jeux proposent plusieurs niveaux et plusieurs niveaux de difficulté, un suivi de la progression du joueur et un classement des joueurs.

Rôle de Moussa : Moussa a été l'un des contributeurs principaux du projet. Il a codé la plupart des pages du site et réalisé l'essentiel du design et de l'interface. Il a également participé à la conception de la base de données MySQL et au développement des fonctionnalités des jeux.

Organisation : l'équipe a travaillé avec une méthode inspirée de l'Agile. Le code était partagé et versionné avec Git et GitHub, les tâches étaient réparties et suivies sur un tableau Trello, et l'équipe faisait des réunions régulières pour faire le point sur l'avancement.

Ce que Moussa a appris : à travailler efficacement en équipe sur un même code (branches Git, répartition des tâches, coordination), à mener un projet web complet de la conception à la réalisation, et à faire communiquer une interface (HTML, CSS, JavaScript) avec un serveur PHP et une base de données MySQL.

## Site de Restaurant Responsive
- Technologies : HTML, CSS, JavaScript
- Type : projet personnel, réalisé seul
- Hébergement : GitHub Pages

Moussa a créé seul un site vitrine pour un restaurant, avec une page de menu, une galerie photo et un formulaire de réservation. Le site est entièrement responsive : il s'adapte aux écrans d'ordinateur, de tablette et de téléphone grâce à Flexbox et aux media queries CSS.

Le formulaire de réservation vérifie en JavaScript que les champs sont correctement remplis, puis envoie la demande de réservation par email.

Le site est pour l'instant une réalisation de démonstration, hébergée sur GitHub Pages. Moussa envisage de le proposer à de vrais restaurateurs pour en faire un projet client.

Ce que Moussa a appris : concevoir une mise en page responsive avec Flexbox et les media queries, valider un formulaire côté client en JavaScript, et mener seul un projet de A à Z.

## Portfolio Personnel
- Technologies : HTML, CSS, JavaScript
- Lien : https://moussa197.github.io/
- Hébergement : GitHub Pages, avec un nom de domaine personnalisé
- Profil GitHub : https://github.com/moussa197

Moussa a conçu et développé lui-même son portfolio pour présenter son parcours, ses projets et ses compétences. Il comprend une page d'accueil, une section projets (avec des filtres), une section parcours (formation et expérience), une section compétences et une section contact.

Design : Moussa a choisi un style épuré et minimaliste, dans des tons noir et vert, ses couleurs préférées. Le site propose un thème clair et un thème sombre et s'adapte aux téléphones.

Le portfolio intègre aussi son assistant IA "Ask Moussa", qui permet aux visiteurs de poser directement des questions sur son parcours.

Ce que Moussa a appris : déployer un site avec GitHub Pages, configurer un nom de domaine personnalisé, et gérer un projet dans la durée avec Git et GitHub.