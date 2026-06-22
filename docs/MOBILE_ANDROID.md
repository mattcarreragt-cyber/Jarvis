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

## 3. Étape 2 — APK via Capacitor (scaffolding **déjà en place**)

[Capacitor](https://capacitorjs.com) emballe la **même** webapp en APK (WebView).
Le projet est déjà configuré : `capacitor.config.ts`, `next.config.ts` (export
conditionnel), scripts npm et `scripts/build-apk.sh`. **Aucune réécriture.**

### Pré-requis (sur TA machine, pas le serveur)
- Node 18+ et **Android Studio** (SDK + JDK 17).

### Build, étape par étape
```bash
cd dashboard
npm install                       # dépendances web normales

# 1) Build statique + install Capacitor à la demande + cap sync, pointant vers ton API Unraid
NEXT_PUBLIC_API_URL=http://192.168.1.50:8000 \
NEXT_PUBLIC_API_KEY=ta-cle-ou-vide \
  ./scripts/build-apk.sh          # build out/ + (1ʳᵉ fois) install Capacitor + cap add android + cap sync

# 2) Ouvre Android Studio et compile
npx cap open android              # puis : Build > Build Bundle(s)/APK(s) > Build APK
```
L'APK se trouve ensuite dans `android/app/build/outputs/apk/`.

> Raccourci : `npm run apk` (= `./scripts/build-apk.sh`).
> `next export` n'existe plus en Next 16 : le statique est produit par
> `BUILD_TARGET=export next build` → dossier `out/` (déjà câblé).

> ⚠️ **Important** : Capacitor **n'est volontairement pas** dans `package.json`.
> Il ne sert qu'à fabriquer l'APK sur **ta** machine et casserait le `npm ci` du
> build Docker (lockfile désynchronisé). Le script `build-apk.sh` l'installe à la
> demande avec `npm install --no-save`, sans modifier le lockfile.

### a) Permission micro (pour la voix / wake word)
Après `cap add android`, édite `android/app/src/main/AndroidManifest.xml` et ajoute
dans `<manifest>` :
```xml
<uses-permission android:name="android.permission.RECORD_AUDIO" />
<uses-permission android:name="android.permission.INTERNET" />
```
La WebView Capacitor accorde `getUserMedia` une fois la permission Android donnée
(Android demandera l'autorisation au 1ᵉʳ usage du micro).

### b) HTTP en clair sur le LAN
`capacitor.config.ts` met déjà `androidScheme: 'http'` + `cleartext: true`, donc
les appels vers `http://192.168.1.50:8000` passent sans erreur de contenu mixte.
(Hors maison, préfère un reverse-proxy **HTTPS** — voir §6.)

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
