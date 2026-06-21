# 👶 JARVIS pour les débutants — pas à pas, zéro jargon

Ce guide s'adresse à quelqu'un qui **n'y connaît rien en informatique**. On va y
aller doucement, en expliquant chaque mot. Prends ton temps, fais une étape à la fois.

---

## 1. C'est quoi JARVIS, en fait ?

JARVIS est un **assistant intelligent privé** (comme un ChatGPT), mais qui tourne
**chez toi**, sur tes propres machines. Rien ne part sur Internet sans ton accord.
Tu lui parles (texte ou voix) et il peut :
- répondre à tes questions,
- chercher dans tes documents,
- générer des images, des vidéos, de la musique,
- piloter ta maison connectée,
- te faire des rappels.

---

## 2. De quoi as-tu besoin ?

Deux ordinateurs sur le **même réseau** (ta box Internet) :

1. **Un serveur Unraid** 🧠 — c'est ton « cerveau », allumé en permanence. Il fait
   tourner l'interface et la mémoire. (Tu en as déjà un.)
2. **Un PC avec une carte graphique** 💪 (appelé « Kubuntu » ici) — c'est le
   « muscle » qui fabrique les images, vidéos, et fait réfléchir l'IA. Il peut
   rester éteint : JARVIS le réveille tout seul quand il en a besoin.

> Tu peux commencer **avec Unraid seul**. L'assistant marchera déjà (recherche,
> mémoire, rappels). Le PC graphique s'ajoute après.

---

## 3. Vocabulaire de survie (5 mots)

- **Terminal** : une fenêtre noire où on tape des commandes. On copie/colle, c'est tout.
- **Docker** : un système qui installe des logiciels dans des « boîtes » isolées,
  proprement, sans rien casser. JARVIS s'installe en boîtes Docker.
- **`.env`** : un petit fichier texte où tu mets tes réglages (mots de passe, adresses).
- **IP** : l'adresse d'une machine sur ton réseau, genre `192.168.1.50`.
- **Conteneur** : une « boîte » Docker qui tourne (l'interface, la base de données…).

---

## 4. Installation sur Unraid, étape par étape

### Étape A — Trouver l'adresse (IP) de ton Unraid
Dans l'interface Unraid, en haut, tu vois quelque chose comme `192.168.1.50`.
**Note-la**, on s'en sert partout. On l'appellera `IP_UNRAID`.

### Étape B — Ouvrir le terminal
Dans l'interface web d'Unraid, en haut à droite, clique sur l'icône **`>_`**.
Une fenêtre noire s'ouvre. C'est le terminal.

### Étape C — Télécharger JARVIS
Copie-colle ces lignes **une par une**, en appuyant sur Entrée après chacune :
```bash
mkdir -p /mnt/user/appdata/jarvis
cd /mnt/user/appdata/jarvis
git clone -b claude/gallant-euler-h0syfh https://github.com/mattcarreragt-cyber/jarvis.git .
```
> Si ça dit que `git` n'existe pas : installe le plugin **NerdTools** depuis
> *Apps* (Community Applications) et active `git`, puis recommence.

### Étape D — Créer tes réglages
```bash
cp .env.example .env
nano .env
```
Une sorte d'éditeur de texte s'ouvre dans le terminal. Modifie ces lignes
(avec les flèches du clavier pour te déplacer) :

- `POSTGRES_PASSWORD=changeme` → remplace `changeme` par un mot de passe à toi
  (par ex. `MonMotDePasse123`). Mets le **même** dans la ligne `DATABASE_URL`
  (entre `jarvis:` et `@postgres`).
- `HOST_IP=192.168.1.XX` → mets ton `IP_UNRAID`.
- `API_KEY=` → **laisse vide** pour commencer (plus simple). On sécurisera après.

Pour **sauvegarder** : appuie sur `Ctrl` + `O`, puis `Entrée`, puis `Ctrl` + `X` pour quitter.

### Étape E — Démarrer JARVIS
```bash
docker compose up -d --build
```
⏳ La première fois, ça prend quelques minutes (il fabrique les boîtes). Patiente
jusqu'à ce que la main revienne (le curseur qui clignote).

### Étape F — Vérifier que ça tourne
```bash
docker compose ps
```
Tu dois voir plusieurs lignes avec `Up` ou `healthy`. C'est bon signe !

### Étape G — Ouvrir l'interface 🎉
Dans ton navigateur (Chrome, Firefox…), va à l'adresse :
```
http://IP_UNRAID:3000
```
(remplace `IP_UNRAID` par ton adresse). Tu vois l'orbe bleu de JARVIS ? **Bravo !**

---

## 5. Tes premiers essais

Dans la zone de chat à droite, tape et appuie sur Entrée :

| Tu tapes… | JARVIS… |
|-----------|---------|
| `cpu et ram de la machine` | te donne l'état de ton serveur |
| `souviens-toi que j'aime le thé vert` | mémorise l'info |
| `que sais-tu sur moi ?` | te répète ce qu'il a retenu |
| `rappelle-moi d'appeler Paul à 18h` | crée un rappel (cloche 🔔 en haut) |

> Si tu tapes `raconte une blague` et qu'il dit « GPU indisponible », c'est
> **normal** : ça veut dire que le PC graphique (Kubuntu) n'est pas encore branché.
> Voir l'étape suivante.

---

## 6. Ajouter le PC graphique (pour images, vidéos, vraie discussion)

Cette partie est plus technique. Elle est détaillée dans **`KUBUNTU_SETUP.md`**.
En résumé, sur le PC graphique tu vas :
1. installer les pilotes de la carte graphique,
2. installer Docker,
3. lancer Ollama (le moteur de l'IA) et ComfyUI (le moteur d'images),
4. télécharger les « modèles » (les cerveaux de l'IA),
5. activer le réveil automatique (Wake-on-LAN).

> Pas à l'aise ? Demande à quelqu'un de te suivre sur cette partie. Une fois faite,
> tout devient automatique : tu n'auras plus à y toucher.

---

## 7. À quoi servent les boutons en haut de l'interface ?

| Icône | Nom | Ça sert à… |
|-------|-----|-----------|
| 🔔 | Agenda | voir tes rappels et notifications |
| 🔊 | Voix | activer la lecture à voix haute des réponses |
| 📤 | Upload | ajouter un document à la base de connaissances |
| ☁ | Nextcloud | gérer la synchro de tes fichiers cloud |
| 🎬 | Jobs | suivre les vidéos en cours de génération |
| 🎬 | Animer | transformer une image en petite vidéo |
| ⊞ | Galerie | revoir toutes les images/vidéos/sons créés |
| ⚙ | Système | voir l'état des machines + sauvegarder/restaurer |
| 🔗 | Webhooks | créer des déclencheurs externes (ex. Home Assistant) |
| 📊 | Stats | voir comment tu utilises JARVIS |
| 🧠 | Mémoire | voir/effacer ce que JARVIS a retenu |
| 🕑 | Historique | retrouver/exporter tes anciennes conversations |
| 🎙️ (en bas) | Micro | parler à JARVIS au lieu de taper |

> 📖 Pour la liste **complète** de tout ce que JARVIS sait faire avec des
> exemples de phrases, voir **`FONCTIONNALITES.md`**.

---

## 8. Quand quelque chose ne marche pas

Pas de panique. Le fichier **`DEPANNAGE_COMPLET.md`** liste les problèmes courants
et leur solution, en langage simple. Le réflexe n°1 :
```bash
cd /mnt/user/appdata/jarvis
docker compose logs -f api
```
Ça affiche ce que fait JARVIS « en direct ». Si tu vois du rouge, copie-le et
demande de l'aide.

---

## 9. Ce qu'il faut retenir

- Unraid = toujours allumé (le cerveau).
- Le PC graphique = se réveille tout seul (le muscle).
- Tu parles, JARVIS choisit tout seul comment répondre.
- Tout reste **chez toi**.

Prends ton temps, va étape par étape, et garde `DEPANNAGE_COMPLET.md` sous la main. 🚀
