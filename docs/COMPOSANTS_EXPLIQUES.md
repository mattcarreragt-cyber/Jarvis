# 🧩 Chaque composant expliqué — à quoi sert quoi

JARVIS est fait de plusieurs « briques » (logiciels). Voici, en langage clair, ce
que fait chacune, **pourquoi** elle est là, et **où** elle tourne.

---

## A. Sur Unraid (le cerveau, toujours allumé)

### 1. Le Dashboard (interface web) — port 3000
- **Ce que c'est :** la page que tu ouvres dans ton navigateur (l'orbe bleu + le chat).
- **Techno :** Next.js (React). Construit en « standalone » dans une boîte Docker.
- **Son rôle :** afficher la conversation, les boutons, les images/vidéos, et
  envoyer ce que tu tapes à l'API.
- **S'il tombe :** tu ne vois plus l'interface, mais le cerveau (API) continue.

### 2. L'API (le cerveau central) — port 8000
- **Ce que c'est :** le programme qui reçoit tes messages et décide quoi faire.
- **Techno :** FastAPI (Python).
- **Son rôle :**
  - **Router** ton message vers le bon « agent » (voir section D),
  - parler à la base de données, à la mémoire, aux machines GPU,
  - faire tourner l'**agenda** (rappels) et la **synchro Nextcloud** en fond.
- **S'il tombe :** plus rien ne répond. C'est la pièce maîtresse.

### 3. PostgreSQL (la mémoire écrite) — interne
- **Ce que c'est :** une base de données (un grand classeur rangé).
- **Son rôle :** garder **durablement** : tes conversations, les faits mémorisés
  (« j'aime le thé »), tes rappels/tâches, la liste de tes médias générés, l'état
  de la synchro Nextcloud.
- **S'il tombe :** JARVIS marche encore, mais oublie tout au redémarrage.
- **Détail :** les « migrations » (Alembic) créent/mettent à jour les tableaux
  automatiquement au démarrage.

### 4. Redis (la mémoire courte) — interne
- **Ce que c'est :** une mémoire ultra-rapide mais temporaire.
- **Son rôle :** se souvenir des **derniers échanges** d'une conversation (contexte
  immédiat) pour que JARVIS suive le fil.
- **S'il tombe :** JARVIS perd juste le fil court terme, rien de grave.

### 5. Qdrant (la mémoire « par le sens ») — interne
- **Ce que c'est :** une base de données spéciale pour la **recherche par sens**
  (pas juste par mots exacts).
- **Son rôle :** stocker tes documents découpés en morceaux pour pouvoir
  retrouver « ce qui parle de » un sujet, même sans le mot exact.
- **Deux modes :**
  - **mots-clés** (sans GPU) : marche tout de suite,
  - **sémantique** (avec GPU/embeddings) : plus précis, quand Kubuntu est allumé.

### 6. Piper (la voix de JARVIS) — port 5000, optionnel
- **Ce que c'est :** un synthétiseur vocal (texte → voix).
- **Son rôle :** lire les réponses à voix haute. Tourne sur le **processeur**
  d'Unraid (pas besoin de carte graphique).
- **S'il n'est pas installé :** la lecture vocale est juste silencieuse.

---

## B. Sur Kubuntu (le muscle GPU 8 Go, peut dormir)

### 7. Ollama (le moteur des modèles de langage) — port 11434
- **Ce que c'est :** le programme qui fait tourner les « LLM » (cerveaux de l'IA
  de texte), comme `qwen2.5:7b`.
- **Son rôle :** générer les réponses de chat, les résumés, l'analyse de documents,
  et les « embeddings » (la recherche par sens).
- **Astuce 8 Go :** réglé pour ne garder **qu'un seul modèle** en mémoire à la fois.

### 8. ComfyUI (le studio multimédia) — port 8188
- **Ce que c'est :** un moteur de génération d'images/vidéos/audio par IA.
- **Son rôle :**
  - **Images** : Stable Diffusion XL (SDXL),
  - **Vidéo (texte→vidéo)** : AnimateDiff,
  - **Vidéo (image→vidéo)** : Stable Video Diffusion (SVD),
  - **Audio/musique** : Stable Audio.
- **Détail :** JARVIS lui envoie des « workflows » (recettes) avec ta description.

### 9. Faster-Whisper (les oreilles) — port 9000
- **Ce que c'est :** un moteur de transcription (voix → texte).
- **Son rôle :** quand tu parles au micro, il transforme ta voix en texte que
  JARVIS comprend.

---

## C. Sur RunPod (le gros muscle cloud, optionnel)

### 10. RunPod (GPU loué à la demande)
- **Ce que c'est :** une carte graphique puissante louée sur Internet, à l'heure.
- **Son rôle :** faire tourner les modèles **trop gros pour 8 Go** : chat 72B,
  vidéo haute définition.
- **Détail :** JARVIS **démarre** le pod tout seul quand tu en as besoin. Tu
  l'**arrêtes** après pour ne pas payer pour rien.

---

## D. Les « agents » (les spécialistes de l'API)

JARVIS ne fait pas tout avec un seul cerveau : il a **14 agents spécialisés**.
Quand tu écris, le **routeur** choisit le bon (par mots-clés, et si besoin avec
l'aide du LLM pour les phrases ambiguës).

| Agent | Spécialité |
|-------|-----------|
| **chat** | conversation générale (par défaut) |
| **system** | état du serveur (CPU, RAM, disques) |
| **unraid** | conteneurs Docker, stockage du NAS |
| **home_assistant** | domotique (lumières, capteurs) — demande confirmation pour agir |
| **recherche** | cherche dans les documents ingérés |
| **nextcloud** | cherche dans tes fichiers Nextcloud |
| **marketing** | assistant contenu pour la marque Xenum |
| **memoire** | retient / rappelle / oublie des faits |
| **agenda** | rappels et automatisations planifiées |
| **image** | génère des images |
| **video** | génère des vidéos (texte→vidéo, image→vidéo) |
| **audio** | génère musique / sons / jingles |
| **dev** | exécute du code Python/bash en bac à sable isolé |
| **echo** | filet de sécurité technique |

---

## E. Les pièces « invisibles » qui font la magie

- **Le routeur** : lit ton message et choisit l'agent. Deux passes : mots-clés
  (instantané), puis LLM (pour les cas ambigus).
- **Le scheduler (orchestrateur de capacités)** : décide **quelle machine** et
  **quel modèle** pour chaque tâche, **réveille Kubuntu** (Wake-on-LAN) si besoin,
  et **gère la VRAM** (décharge un modèle avant d'en charger un autre sur 8 Go).
- **La mémoire à 3 niveaux** : court terme (Redis) + durable (PostgreSQL) +
  par le sens (Qdrant).
- **La galerie** : chaque image/vidéo/son généré est enregistré pour être retrouvé.
- **Le « best-effort »** : si une machine est éteinte, JARVIS ne plante pas — il
  fait au mieux (mode dégradé) et te le dit clairement.

---

## F. Pourquoi autant de pièces ?

Parce que chaque pièce fait **une** chose et la fait bien, et qu'on peut en
éteindre certaines sans tout casser :
- pas de GPU ? → recherche + mémoire + agenda marchent quand même ;
- pas de Nextcloud ? → le reste fonctionne ;
- pas de RunPod ? → on reste sur le GPU local.

C'est le principe **local-first** : ça marche chez toi, et ça se dégrade
proprement quand une brique manque.
