# 🔐 Accès sécurisé partout via Tailscale (HTTPS + micro)

Objectif : accéder à JARVIS **de n'importe où**, en **HTTPS valide**, sans ouvrir
aucun port sur Internet — et débloquer le **micro / wake word** (qui exige un
*secure context* HTTPS).

Tu as déjà Tailscale sur Unraid (`tower.tail248307.ts.net`). On va utiliser
**Tailscale Serve** pour ajouter le TLS devant le dashboard et l'API.

---

## 1. Pourquoi pas juste `http://tower.tail248307.ts.net:1200` ?

Parce que c'est du **HTTP**. Les navigateurs n'autorisent le micro (`getUserMedia`,
Web Speech) **que** sur `https://` ou `localhost`. Sans TLS, le chat texte marche
mais la voix reste bloquée. `tailscale serve` règle ça en fournissant un vrai
certificat Let's Encrypt sur ton domaine `*.ts.net`.

---

## 2. Pré-requis (une seule fois, dans l'admin Tailscale)

1. **HTTPS activé** sur ton tailnet : https://login.tailscale.com/admin/dns
   → section *HTTPS Certificates* → **Enable HTTPS**.
2. **MagicDNS** activé (normalement déjà le cas, vu que tu as un nom `*.ts.net`).

> On utilise **Serve** (accès réservé à TES appareils du tailnet), pas **Funnel**
> (qui exposerait sur l'Internet public). C'est ce que tu veux : privé + partout.

---

## 3. Configuration (sur Unraid, où tourne Tailscale)

On expose **deux** services HTTPS sur le même nom d'hôte, sur deux ports :

| URL Tailscale | → cible locale | Service |
|---|---|---|
| `https://tower.tail248307.ts.net` (443) | `127.0.0.1:1200` | Dashboard |
| `https://tower.tail248307.ts.net:8443` | `127.0.0.1:4500` | API |

```bash
# Dashboard sur le port HTTPS standard 443
tailscale serve --bg --https=443 http://127.0.0.1:1200

# API sur le port HTTPS 8443 (même certificat, même nom d'hôte)
tailscale serve --bg --https=8443 http://127.0.0.1:4500

# Vérifie
tailscale serve status
```

> Si `tailscale` n'est pas dans le PATH sur Unraid (plugin), utilise le chemin
> complet, p. ex. `/usr/local/emhttp/plugins/tailscale/...` ou la commande fournie
> par le plugin. Le sous-commande est identique : `tailscale serve ...`.

Le **même certificat** `tower.tail248307.ts.net` couvre tous les ports → pas
d'erreur TLS, et la page (443) peut appeler l'API (8443) sans *mixed content*.

---

## 4. Pointer le dashboard vers l'API HTTPS

Le dashboard « cuit » l'URL de l'API au moment du build. Édite `.env` sur Unraid :

```bash
nano /mnt/user/appdata/jarvis/.env
```

Ajoute :
```ini
API_PUBLIC_URL=https://tower.tail248307.ts.net:8443
```

Puis **rebuild le dashboard** (l'URL est un build arg) :
```bash
cd /mnt/user/appdata/jarvis
docker compose up -d --build dashboard
```

---

## 5. Utilisation

- Depuis **n'importe quel appareil de ton tailnet** (téléphone, PC, en 4G/5G) :
  ouvre **`https://tower.tail248307.ts.net`**.
- Cadenas vert ✅ → *secure context* → le bouton 👂 micro / « Hey Jarvis » et la
  dictée vocale fonctionnent.
- Aucun port ouvert sur la box, aucun reverse-proxy à maintenir.

---

## 6. Et l'APK Android ?

Deux options, toutes deux compatibles :
- **Le plus simple** : installe l'app Tailscale sur le téléphone, et pointe l'APK
  (ou la PWA) sur `https://tower.tail248307.ts.net`. Tu profites du TLS + de l'accès
  partout sans rien changer d'autre.
- L'APK Capacitor peut aussi taper directement l'IP LAN en HTTP quand tu es à la
  maison (le micro natif Android ne dépend pas du secure-context navigateur), mais
  passer par Tailscale HTTPS uniformise tout (maison **et** extérieur).

Dans `scripts/build-apk.sh`, mets simplement :
```bash
NEXT_PUBLIC_API_URL=https://tower.tail248307.ts.net:8443 ./scripts/build-apk.sh
```

---

## 7. Dépannage

| Symptôme | Cause / solution |
|---|---|
| Cadenas barré / `NET::ERR_CERT` | HTTPS pas activé dans l'admin Tailscale (étape 2). |
| Micro toujours bloqué | Tu accèdes encore en `http://...:1200`. Utilise l'URL `https://` (Serve). |
| `Erreur de connexion à l'API` | `API_PUBLIC_URL` absent du `.env` **ou** dashboard pas rebuild. Refais `docker compose up -d --build dashboard`. Vérifie `tailscale serve status`. |
| `mixed content blocked` (console) | La page est en HTTPS mais l'API en HTTP. Assure-toi que `API_PUBLIC_URL` commence par `https://`. |
| `tailscale serve` « command not found » | Utilise le binaire du plugin Tailscale d'Unraid, ou installe le paquet. |
| Marche à la maison, pas dehors | L'appareil distant doit aussi être connecté au **même tailnet** (app Tailscale lancée). |

---

## 8. Revenir en arrière

```bash
tailscale serve --https=443 off
tailscale serve --https=8443 off
```
Et retire `API_PUBLIC_URL` du `.env`, puis rebuild le dashboard.
