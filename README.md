# Ask Moussa

Ask Moussa est un chatbot qui répond aux questions sur le parcours de Moussa Keita : formation, compétences, projets et recherche de stage ou d'alternance. Il est intégré à son portfolio ([moussa197.github.io](https://moussa197.github.io/)).

C'est une API **Python / FastAPI** qui s'appuie sur l'API **Claude** (modèle `claude-haiku-4-5`). Elle suit le principe du **RAG** (*Retrieval-Augmented Generation*) : Claude ne répond pas de mémoire, mais uniquement à partir des documents fournis dans le dossier `data/`.

## Comment ça marche

Quand un visiteur pose une question (`POST /chat`) :

1. **CORS** : seul le portfolio est autorisé à appeler l'API depuis un navigateur.
2. **Validation** : une question vide ou de plus de 500 caractères est refusée (422), sans appeler Claude.
3. **Limite de requêtes** : au-delà de 10 questions par minute ou 30 par jour pour une même IP, ou de 300 par jour au total, la question est refusée (429).
4. **Prompt** : les règles du chatbot et les trois documents de `data/` sont envoyés à Claude avec la question.
5. **Génération** : Claude rédige une réponse courte, dans la langue du visiteur, à partir des documents uniquement.

Les documents sont chargés et le prompt est construit **une seule fois**, au démarrage du serveur.

## Choix techniques

- **Tous les documents à chaque question, sans base vectorielle.** La base de connaissances ne fait qu'environ 4 000 tokens : elle tient entièrement dans le contexte de Claude. Une recherche par embeddings serait plus complexe, plus lourde et moins fiable à cette échelle.
- **Des dépendances minimales.** L'hébergement gratuit de Render limite la mémoire à 512 Mo. Pas de LangChain, de PyTorch ni de base vectorielle : seulement FastAPI, uvicorn, le SDK officiel `anthropic` et `python-dotenv`.
- **Un rate limiting écrit à la main.** C'est une « fenêtre glissante » d'une centaine de lignes, sans dépendance. Un verrou la protège des accès simultanés, et elle est testée avec une fausse horloge, sans aucune attente.
- **Une défense contre l'injection de prompt en plusieurs couches.** Les règles sont dans le prompt système. La question est encadrée par des balises `<question>` et neutralisée : un visiteur ne peut pas fermer la balise. Le prompt précise que la question n'est jamais une instruction. Enfin, les longueurs des questions et des réponses sont limitées.
- **Des tests sans aucun appel réel.** Le client Claude est injecté dans le code, ce qui permet de le remplacer par un faux dans les tests. Les tests ne consomment donc aucun crédit et ne dépendent pas du réseau.
- **Des erreurs neutres pour le visiteur, et des journaux utiles pour le développeur.** Une panne de Claude renvoie un message générique (503). Le journal note le type d'erreur et l'identifiant de la requête, mais jamais la question du visiteur.

Le détail de l'architecture et des décisions se trouve dans [PLAN.md](PLAN.md).

## Méthode de travail

J'ai développé ce projet en orchestrant plusieurs agents IA (Claude Code), en gardant le rôle de superviseur et d'architecte :

- **Un cadre fixé en amont.** J'ai écrit les règles du projet dans [CLAUDE.md](CLAUDE.md) : contraintes techniques, sécurité, comportement du chatbot et mode de collaboration. J'ai validé le plan d'architecture ([PLAN.md](PLAN.md)) avant toute ligne de code.
- **Une étape à la fois.** Pour chaque fonctionnalité, l'agent explique ses choix et les alternatives, puis n'implémente qu'après ma validation. Chaque étape se termine par des tests pytest que je lance et vérifie, puis par un commit que je fais moi-même.
- **Des décisions humaines.** Je tranche les compromis. Par exemple, j'ai réduit le délai d'attente de l'API Claude pour qu'un visiteur ne patiente jamais jusqu'à 90 secondes.
- **Des tests réels et des corrections.** Mes essais dans `/docs` ont révélé des problèmes que les tests automatiques ne pouvaient pas voir, et je les ai fait corriger :
  - une panne de crédit renvoyait une erreur 500 brute, elle renvoie désormais un 503 neutre ;
  - les réponses contenaient du Markdown, tutoyaient le visiteur et étaient trop longues pour une bulle de chat.
- **Des agents spécialisés** : planification de l'architecture, écriture des tests, revue de code et revue de sécurité.

## Installation

Prérequis : **Python 3.12** et une clé API Anthropic ([console.anthropic.com](https://console.anthropic.com/)).

Les commandes ci-dessous sont pour Windows (PowerShell).

```powershell
git clone https://github.com/moussa197/askMoussa.git
cd askMoussa

# Environnement virtuel
python -m venv .venv
.venv\Scripts\Activate.ps1

# Dépendances (production + tests)
pip install -r requirements-dev.txt

# Fichier de configuration local
Copy-Item .env.example .env
```

Sous Linux ou macOS, activez l'environnement avec `source .venv/bin/activate`, et copiez le fichier avec `cp .env.example .env`.

Ouvrez ensuite `.env` et renseignez votre clé :

```
ANTHROPIC_API_KEY=sk-ant-...
```

Le fichier `.env` est ignoré par Git : il ne doit **jamais** être commité.

## Lancement

```powershell
uvicorn app.main:app --reload
```

Quand le terminal affiche `Application startup complete.`, ouvrez **http://127.0.0.1:8000/docs**. Cette page interactive permet de tester l'API directement dans le navigateur.

Si la clé est absente ou qu'un document de `data/` manque, le serveur refuse de démarrer et affiche un message explicite.

## Tests

```powershell
pytest -v
```

Les tests n'appellent jamais la vraie API Claude : ils utilisent de faux clients et une fausse clé. Ils fonctionnent sans connexion et sans crédits.

## Utiliser l'API

### `GET /health`

Vérifie que le service est en ligne. Elle ne fait aucun appel à Claude et n'est pas limitée.

```json
{"status": "ok"}
```

### `POST /chat`

Corps de la requête :

```json
{"question": "Quels projets a réalisés Moussa ?"}
```

Réponse :

```json
{"answer": "Moussa a notamment réalisé ..."}
```

Exemple en PowerShell :

```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/chat -ContentType "application/json" -Body '{"question": "What projects has Moussa built?"}'
```

Exemple avec `curl` (Linux, macOS, Git Bash) :

```bash
curl -X POST http://127.0.0.1:8000/chat -H "Content-Type: application/json" -d '{"question": "Quels projets a réalisés Moussa ?"}'
```

### Codes de réponse

| Code | Signification | Corps |
|---|---|---|
| 200 | Réponse de Claude | `{"answer": "..."}` |
| 422 | Question absente, vide ou trop longue (plus de 500 caractères) | `{"detail": ...}` |
| 429 | Trop de questions (limite par IP ou plafond global atteint) | `{"detail": "Trop de questions. Réessayez un peu plus tard."}` |
| 503 | Claude est indisponible (panne, délai dépassé, crédits épuisés…) | `{"detail": "Le service est momentanément indisponible. Réessayez plus tard."}` |

Dans les réponses 422, `detail` est une liste d'erreurs de validation si la question est absente ou vide, et un simple texte si elle est trop longue.

## Configuration

Toutes les variables se règlent dans `.env` en local, ou dans le tableau de bord de l'hébergeur en production. Seule la clé est obligatoire.

| Variable | Défaut | Rôle |
|---|---|---|
| `ANTHROPIC_API_KEY` | *(obligatoire)* | Clé de l'API Anthropic |
| `CLAUDE_MODEL` | `claude-haiku-4-5` | Modèle Claude utilisé |
| `CLAUDE_MAX_TOKENS` | `400` | Longueur maximale d'une réponse (en tokens) |
| `MAX_QUESTION_LENGTH` | `500` | Longueur maximale d'une question (en caractères) |
| `RATE_LIMIT_PAR_MINUTE` | `10` | Questions par minute pour une même IP |
| `RATE_LIMIT_PAR_JOUR` | `30` | Questions par 24 h pour une même IP |
| `PLAFOND_GLOBAL_JOUR` | `300` | Questions par 24 h, tous visiteurs confondus |
| `CORS_ORIGINES_DEV` | *(vide)* | Origines autorisées en plus du portfolio, séparées par des virgules (ex. `http://localhost:5500`). `*` est refusé |
| `XFF_POSITION` | *(vide)* | Position de l'IP réelle du visiteur dans l'en-tête `X-Forwarded-For` derrière un proxy (`0`, `-1`, `-2`…). Vide : IP de la connexion |

Un nombre invalide, ou un `*` dans les origines, empêche le serveur de démarrer.

## Sécurité

- La clé API ne se trouve que dans `.env`, qui n'est jamais commité, ou dans les variables d'environnement de l'hébergeur. Elle n'apparaît jamais dans les journaux ni dans l'affichage de la configuration.
- Le CORS n'autorise que `https://moussa197.github.io`, et jamais `*`.
- La longueur des questions et le nombre de requêtes sont limités avant tout appel à Claude.
- Les questions des visiteurs ne sont jamais écrites dans les journaux.

## Limites connues

- **Les compteurs de requêtes sont gardés en mémoire.** Ils repartent à zéro à chaque redémarrage du serveur, et l'hébergement gratuit se met en veille après quelques minutes d'inactivité. La **limite de dépense mensuelle** fixée dans la console Anthropic reste donc le vrai filet de sécurité.
- **Le serveur doit tourner avec un seul worker uvicorn**, sinon chaque processus aurait ses propres compteurs.
- **L'IP réelle du visiteur, derrière le proxy de l'hébergeur,** dépend de la position configurée dans `XFF_POSITION`. Cette position doit être mesurée lors du déploiement (voir [PLAN.md](PLAN.md), §4.3).

## Structure du projet

```
askMoussa/
├── app/
│   ├── config.py          # Lecture et vérification des variables d'environnement
│   ├── documents.py       # Chargement des fichiers de data/ (commentaires HTML retirés)
│   ├── prompt.py          # Règles du chatbot, documents balisés, question balisée
│   ├── claude_client.py   # Seul point d'appel à l'API Claude
│   ├── rate_limit.py      # Limites par IP et plafond global, IP du visiteur
│   └── main.py            # Application FastAPI : CORS, routes /health et /chat, erreurs
├── data/                  # Base de connaissances : cv.md, faq.md, projets.md
├── tests/                 # Tests pytest (un fichier par module, sans appel réel)
├── .env.example           # Modèle de configuration, sans vraie clé
├── requirements.txt       # Dépendances de production
├── requirements-dev.txt   # Dépendances de développement (pytest, httpx)
├── pytest.ini             # Configuration de pytest
└── PLAN.md                # Architecture détaillée et étapes du projet
```
