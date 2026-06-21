# 📱 Mobile : PWA maintenant, app Android (APK) ensuite

Réponse à : « vaut-il mieux une app Android pour la mémoire / les ressources ? »
et comment obtenir l'APK + le wake word « Hey Jarvis ».

---

## 1. La vérité sur « mémoire » et « ressources »

| Idée reçue | Réalité |
|------------|---------|
| « Une app native économise des ressources » | **Pour le serveur : non.** Tout le calcul lourd (IA, RAG, génération) tourne sur Unraid/Kubuntu/RunPod. L'app (web ou Android) n'est qu'un **client léger** (UI + micro + affichage). |
| « Le natif garde mieux en mémoire » | **Oui, côté client.** Un onglet web peut être tué par Android ; une app native peut tourner en **service de premier plan**, garder l'état et **écouter « Hey Jarvis » écran éteint** — interdit aux navigateurs. |

➡️ **Conclusion** : passe au natif **pour le wake word always-on et la persistance**,
pas pour soulager le serveur (ça ne change rien à ce niveau).

---

## 2. Étape 1 — PWA (déjà fait, installable aujourd'hui)

Le dashboard est désormais une **PWA** :
- `app/manifest.ts` (nom, icônes, couleurs, `display: standalone`)
- icônes `public/icon-192.png` / `icon-512.png`
- thème + Apple meta dans `app/layout.tsx`

**Installer sur Android (Chrome)** : ouvre `http://IP_UNRAID:3000` → menu ⋮ →
« Ajouter à l'écran d'accueil ». L'app s'ouvre en plein écran, comme une app.

> Limite PWA : le **wake word en arrière-plan** (écran éteint) n'est pas possible
> dans le navigateur. Pour ça → étape 2.

---

## 3. Étape 2 — APK via Capacitor (quand tu voudras le natif)

[Capacitor](https://capacitorjs.com) emballe la **même** webapp dans une APK
(WebView), avec accès aux API natives. Aucune réécriture.

```bash
cd dashboard
npm i @capacitor/core @capacitor/cli @capacitor/android
npx cap init JARVIS com.jarvis.app --web-dir=out
# build statique de la webapp pointant vers ton API
NEXT_PUBLIC_API_URL=http://IP_UNRAID:8000 npm run build && npx next export -o out
npx cap add android
npx cap copy android
npx cap open android       # ouvre Android Studio → Build APK
```

> L'APK pointe vers ton API Unraid sur le LAN (ou via un reverse-proxy HTTPS pour
> l'accès hors maison + le micro).

---

## 4. Étape 3 — Wake word « Hey Jarvis »

### a) Dans la webapp (déjà fait, MVP)
Bouton **👂 oreille** dans le header → active l'écoute via l'API Web Speech
(Chrome/Edge/Chrome Android). Quand tu dis « **Hey Jarvis** » (ou « Jarvis »),
l'app enregistre ~6 s et envoie ta commande.
- Fonctionne **app au premier plan** uniquement.
- Nécessite **HTTPS ou localhost** (contrainte micro navigateur).

### b) En natif Android (always-on, écran éteint)
Pour une écoute permanente, utilise un moteur de wake word **embarqué** :
- **Picovoice Porcupine (Android)** : modèle « Hey Jarvis » en local (offline),
  très léger, dans un **Foreground Service** Android.
- Alternative open-source : **openWakeWord** / **Vosk**.

Schéma : `Foreground Service` → Porcupine détecte « Hey Jarvis » → ouvre l'app /
démarre la capture → POST `/api/voice/transcribe` → réponse (+ TTS).

> C'est la **vraie** raison de passer au natif : un service de fond persistant que
> le navigateur ne permet pas.

---

## 5. Recommandation de parcours

1. **Maintenant** : PWA installée sur ton Android (fait). Wake word quand l'app est ouverte.
2. **Ensuite** : APK Capacitor (même code) pour l'app-store-feel + permissions natives.
3. **Pour le « Hey Jarvis » écran éteint** : ajouter Porcupine + Foreground Service
   dans le projet Android Capacitor.

Tout ça **sans dupliquer le code** : une seule base (la webapp), enrichie au besoin.

---

## 6. Accès hors maison (mobile)

Pour utiliser JARVIS en 4G/5G hors du LAN :
- expose le dashboard + l'API derrière un **reverse-proxy HTTPS** (Nginx Proxy
  Manager sur Unraid) + nom de domaine, **ou**
- via ton **VPN Mullvad** / un tunnel WireGuard vers la maison.
- HTTPS est **obligatoire** pour le micro hors localhost.
