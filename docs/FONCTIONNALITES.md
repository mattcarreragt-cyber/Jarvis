# 📚 Tout ce que JARVIS sait faire — catalogue complet

Référence de **toutes** les fonctionnalités, avec **comment les déclencher** et
**où ça tourne**. Tape simplement la phrase dans le chat (ou utilise le bouton).

> Légende palier : 🟢 Unraid (toujours) · 🟡 Kubuntu (GPU, se réveille) · 🔵 RunPod (cloud, option)

---

## 1. Conversation & assistance

| Tu veux… | Dis / fais… | Agent | Palier |
|----------|-------------|-------|--------|
| Discuter, poser une question | « explique-moi la photosynthèse » | chat | 🟡 |
| Raisonnement / analyse poussée | « **analyse** ma stratégie 2026 » | chat (deep) | 🟡 |
| Très gros modèle (72B) | « **réflexion profonde** sur… » | chat (xl) | 🔵 |

Le bon modèle est choisi automatiquement selon les mots (`fast` / `deep` / `xl`).

---

## 2. Mémoire (ce que JARVIS retient sur toi)

| Action | Exemple |
|--------|---------|
| Retenir un fait | « **souviens-toi que** je préfère le café noir » |
| Lister | « **que sais-tu sur moi ?** » |
| Tout oublier | « **oublie tout** » |
| Gérer visuellement | bouton 🧠 (voir / supprimer un par un) |

Les faits sont **réinjectés automatiquement** dans tes conversations. 🟢

---

## 3. Recherche dans tes documents (RAG)

| Action | Exemple |
|--------|---------|
| Ajouter un document | bouton 📤 (txt, md, pdf, docx, xlsx, pptx, images) |
| Chercher dedans | « **cherche** la clause de garantie » |
| Chercher dans Nextcloud | « cherche dans **mon nextcloud** les chiffres Q1 » |
| Synchroniser Nextcloud | bouton ☁ → SYNCHRONISER |

Sans GPU = recherche par mots-clés. Avec GPU = recherche par **sens** + réponse rédigée. 🟡

---

## 4. Marketing Xenum

| Action | Exemple |
|--------|---------|
| Rédiger un post | « **rédige un post** Instagram pour Xenum » |
| Idées de campagne | « idées de **campagne** Xenum » |
| Fiche produit | « **caractéristiques** du produit X » |

S'appuie sur tes documents ingérés (tag `xenum`). 🟡 (génère du vrai contenu avec le GPU)

---

## 5. Génération d'images

| Action | Exemple | Palier |
|--------|---------|--------|
| Créer une image | « **génère une image** d'un moteur premium » | 🟡 SDXL |

Résultat affiché dans le chat **et** rangé dans la galerie (bouton ⊞). 🟡

---

## 6. Génération de vidéo

| Action | Exemple | Palier |
|--------|---------|--------|
| Texte → vidéo | « **génère une vidéo de 10s** d'un chat cosmique » | 🟡 AnimateDiff / 🔵 HD |
| Image → vidéo | bouton 🎬 **Animer** → choisis une image | 🟡 SVD |
| Suivre l'avancement | bouton 🎬 **Jobs** | — |

La vidéo prend plusieurs minutes : elle apparaît dans Jobs puis la galerie. 🟡

---

## 7. Génération audio / musique

| Action | Exemple | Palier |
|--------|---------|--------|
| Musique / son / jingle | « **compose une musique** électro de 20s » | 🟡 Stable Audio |

Lecteur audio dans le chat + galerie. 🟡

---

## 8. Voix (parler & écouter)

| Action | Comment |
|--------|---------|
| Parler à JARVIS | bouton 🎙️ micro (parle, il transcrit et répond) |
| Réponses à voix haute | bouton 🔊 (active la lecture automatique) |

STT = Whisper sur Kubuntu 🟡 · TTS = Piper sur Unraid 🟢
> Le micro nécessite HTTPS ou localhost (sécurité navigateur).

---

## 9. Agenda — rappels & automatisations

| Action | Exemple |
|--------|---------|
| Rappel ponctuel | « **rappelle-moi** d'appeler Paul **à 14h30** » |
| Rappel différé | « **dans 20 minutes**, sortir le plat » |
| Automatisation quotidienne | « **chaque jour à 8h**, résume mes nouveaux fichiers » |
| Récurrent | « **toutes les 2 heures**, vérifie l'espace disque » |
| Voir / annuler | bouton 🔔 (onglet Tâches) · « annule tout » |

Différence : ⏰ **rappel** = te notifier · 🤖 **automatisation** = JARVIS *fait* la tâche. 🟢

---

## 10. Domotique (Home Assistant) + capteurs

| Action | Exemple |
|--------|---------|
| Voir les lumières | « **liste mes lumières** » |
| Lire les capteurs | « **température du salon** », « **humidité** », « **capteurs** » |
| Agir | « **allume** light.salon » → bouton **CONFIRMER** |
| Panneau | bouton 🏠 (capteurs en direct + bascule lumières/prises) |

Toute action en chat demande **confirmation** ; dans le panneau, le bouton = action explicite. 🟢

---

## 10bis. Activation vocale « Hey Jarvis »

Bouton **👂** dans le header → écoute le mot d'activation. Dis « **Hey Jarvis** »
(app au premier plan) → JARVIS enregistre ta commande et la traite.
Écran éteint / always-on → app Android native (voir `MOBILE_ANDROID.md`). 🟢

---

## 11. Système & serveur

| Action | Exemple |
|--------|---------|
| État de la machine | « **cpu et ram** de la machine » |
| Conteneurs / stockage | « **état des conteneurs** docker », « **espace disque** du nas » |
| Vue des paliers | bouton ⚙ Système |

🟢

---

## 12. Exécution de code (bac à sable)

| Action | Exemple |
|--------|---------|
| Python | <code>\`\`\`python<br>print(6*7)<br>\`\`\`</code> |
| Bash | <code>\`\`\`bash<br>echo hello<br>\`\`\`</code> |

Tourne dans un conteneur **isolé** (sans réseau). 🟢

---

## 13. Webhooks — déclencheurs externes

| Action | Comment |
|--------|---------|
| Créer un déclencheur | bouton 🔗 → nom + message |
| Copier l'URL | bouton copier → `POST .../api/hooks/<token>` |
| Déclencher depuis HA | RESTful Command en POST sur l'URL |

Le résultat arrive dans les notifications 🔔. 🟢

---

## 14. Galerie média

Bouton ⊞ : tous tes rendus (images, vidéos, audios) au même endroit, avec
**lecture**, **téléchargement** et **suppression**. 🟢

---

## 15. Statistiques d'usage

Bouton 📊 : messages, agents les plus utilisés, activité 7 jours, méthode de
routage, taux de réussite des outils. 🟢

---

## 16. Sauvegarde & migration

Bouton ⚙ → section Sauvegarde :
- **EXPORTER** : télécharge ton « cerveau » (faits, tâches, webhooks) en JSON
- **RESTAURER** : réimporte ce JSON (pour migrer ou récupérer) 🟢

---

## 17. Bureau distant & streaming (Moonlight/Sunshine)

| Action | Exemple |
|--------|---------|
| Réveiller Kubuntu + préparer le stream | « **réveille kubuntu** », « **lance le streaming** » |
| Vérifier Sunshine | « **statut sunshine** » |
| Panneau | bouton 🖥️ (réveil + statut) |

🟢 (WoL + test Sunshine) → connexion ensuite via **Moonlight**. Voir `BUREAU_DISTANT_VPN.md`.

---

## 18. VPN Mullvad

| Action | Exemple |
|--------|---------|
| Suis-je protégé ? | « **suis-je protégé** », « **statut vpn** » |
| Connecter / déconnecter | « **connecte le vpn** », « **déconnecte le vpn** » |
| Changer de pays | « **vpn pays se** » (code ISO) |

🟢 Statut HTTP (sortie JARVIS) ou CLI via SSH (`MULLVAD_SSH_HOST`).

---

## 19. Historique & export de conversation

Bouton 🕑 : retrouve tes sessions, **restaure** une conversation, ou **exporte**-la
en **Markdown** / **JSON** pour l'archiver. 🟢

---

## En résumé : 14 agents spécialisés

`chat` · `system` · `unraid` · `home_assistant` · `recherche` · `nextcloud` ·
`marketing` · `memoire` · `agenda` · `image` · `video` · `audio` · `dev` · `echo`

Tu n'as **jamais** à choisir l'agent : tu écris, le **routeur** s'en charge
(mots-clés, puis IA pour les phrases ambiguës). Et tout se **dégrade proprement** :
une machine éteinte ne casse jamais le reste.
