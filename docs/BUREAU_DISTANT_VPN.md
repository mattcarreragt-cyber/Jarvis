# 🎮 Bureau distant (Moonlight/Sunshine) · 🔒 VPN Mullvad · ✉️ Mail

Couvre l'agent **bureau** (streaming + Wake-on-LAN), l'agent **vpn** (Mullvad),
et le point sur **Tuta Mail**.

---

## 1. Bureau distant — Sunshine (hôte) + Moonlight (client)

**Sunshine** tourne sur **Kubuntu** (il diffuse l'écran/jeux). **Moonlight** est le
client (PC, téléphone, TV). JARVIS **réveille Kubuntu** par Wake-on-LAN, vérifie
que Sunshine répond, et te dit comment te connecter.

### Utilisation (chat)
- « **réveille kubuntu** » / « **lance le streaming** » → WoL + attente de Sunshine
- « **statut sunshine** » → vérifie sans réveiller

### Endpoints
- `GET /api/remote/status` · `POST /api/remote/wake`

### Configuration JARVIS (.env)
```env
SUNSHINE_HOST=192.168.1.51     # IP de Kubuntu (sinon dérivé de KUBUNTU_URL)
SUNSHINE_PORT=47989            # port testé pour « est-ce up »
KUBUNTU_MAC=AA:BB:CC:DD:EE:FF  # déjà utilisé par le WoL
```

> Tu as déjà un **bouton WoL dans Home Assistant** : parfait, JARVIS fait la même
> chose (magic packet) et **vérifie en plus** que Sunshine est prêt.

---

## 2. Installer Sunshine sur Kubuntu

```bash
# Paquet officiel (.deb) — voir github.com/LizardByte/Sunshine/releases
sudo apt install -y ./sunshine.deb
# Démarrer au login + ouvrir l'UI de config
sunshine
```
- UI web : `https://localhost:47990` (crée un identifiant à la 1ʳᵉ ouverture).
- Autorise le pare-feu : ports **47984-47990 (TCP)** et **47998-48000 (UDP)**.
- Dans Moonlight (client), l'hôte apparaît automatiquement sur le LAN ; sinon
  ajoute l'IP de Kubuntu, puis saisis le **code PIN** affiché dans l'UI Sunshine.

---

## 3. ⚠️ Le fix « session unique » (ton problème Moonlight)

Moonlight casse si Sunshine démarre **avant** qu'une session graphique soit ouverte,
ou si l'**utilisateur change**. La solution fiable : **une seule session, en
auto-login**, et Sunshine lancé **dans cette session**.

### a) Auto-login d'un seul utilisateur (GDM / GNOME)
```bash
sudo nano /etc/gdm3/custom.conf
```
```ini
[daemon]
AutomaticLoginEnable=true
AutomaticLogin=TON_UTILISATEUR
```
> Sur SDDM (KDE) : `/etc/sddm.conf` → `[Autologin]` `User=` et `Session=`.

### b) Verrouiller sur une seule session
- Supprime les comptes/sessions superflus, ou désactive le changement rapide
  d'utilisateur. Garde **un seul** utilisateur qui s'auto-connecte.
- Évite la mise en veille qui ferme la session :
  ```bash
  sudo systemctl mask sleep.target suspend.target hibernate.target hybrid-sleep.target
  ```
  (ou règle « jamais » dans les paramètres d'énergie GNOME/KDE).

### c) Lancer Sunshine dans la session graphique (pas en root)
Active le service **utilisateur** (pas système) :
```bash
systemctl --user enable sunshine
systemctl --user start sunshine
# pour qu'il tourne sans être loggé en SSH :
sudo loginctl enable-linger TON_UTILISATEUR
```

### d) Wayland vs X11
Sunshine capture mieux en **X11**. Si la capture est noire/instable, choisis une
session **« Xorg »** à l'écran de login (roue dentée), pour ce même utilisateur.

✅ Résultat : Kubuntu démarre (WoL) → auto-login du **même** utilisateur → Sunshine
se lance dans **sa** session → Moonlight se connecte de façon stable.

---

## 4. VPN Mullvad

L'agent **vpn** vérifie ta protection et peut piloter Mullvad.

### Utilisation (chat)
- « **suis-je protégé ?** » / « **statut vpn** »
- « **connecte le vpn** » / « **déconnecte le vpn** »
- « **vpn pays se** » (code pays ISO : se=Suède, fr=France…)

### Deux niveaux de statut
- **HTTP** (`am.i.mullvad.net`) : reflète la **sortie réseau de JARVIS (Unraid)**.
  Pratique pour savoir si **le serveur** sort via Mullvad.
- **CLI via SSH** (plus précis pour un hôte donné) : configure
  ```env
  MULLVAD_SSH_HOST=192.168.1.51   # hôte où `mullvad` est installé
  MULLVAD_SSH_USER=ton_user
  ```
  JARVIS lance alors `mullvad status` / `mullvad connect` sur cet hôte (clé SSH,
  voir CYBERSECURITE.md pour le montage de la clé).

### Endpoints
- `GET /api/vpn/status` · `POST /api/vpn/control {action, location}`

---

## 5. ✉️ Tuta Mail — pourquoi ce n'est pas intégrable

**Tuta (Tutanota) est chiffré de bout en bout et n'expose ni IMAP/SMTP ni API
REST publique.** L'accès passe par leurs apps officielles (web/desktop/mobile)
qui déchiffrent localement. Il n'existe donc **aucun moyen propre** pour JARVIS
de lire/envoyer tes mails Tuta sans casser le chiffrement.

**Options réalistes :**
- garder Tuta pour la messagerie privée (hors JARVIS) ;
- si tu veux une boîte **pilotable par JARVIS** plus tard, utilise un compte
  **IMAP/SMTP** classique (ex. un alias dédié) — je pourrai alors ajouter un
  agent « mail » propre (lecture/résumé/envoi). Dis-le-moi si tu veux cette voie.

---

## 6. Dépannage

| Symptôme | Cause | Solution |
|----------|-------|----------|
| « MAC non configurée » | `KUBUNTU_MAC` vide | renseigne-la (déjà ta MAC du bouton HA) |
| WoL envoyé mais Sunshine KO | Sunshine pas lancé dans la session | voir §3 (auto-login + service user + linger) |
| Écran noir dans Moonlight | capture Wayland | passe en session **Xorg** |
| Moonlight ne voit pas l'hôte | pare-feu / sous-réseau | ouvre 47984-47990/TCP, 47998-48000/UDP ; ajoute l'IP manuellement |
| VPN « NON protégé » alors que connecté | le check HTTP reflète Unraid, pas ton PC | configure `MULLVAD_SSH_HOST` pour viser le bon hôte |
