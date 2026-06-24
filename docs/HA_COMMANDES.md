# 🏠 Apprendre à JARVIS à comprendre tes commandes Home Assistant

Tu peux parler/écrire **en langage naturel** (« allume la lumière du salon »,
« éteins les luminaires », « coupe la télé ») sans connaître les `entity_id`.

## Comment JARVIS comprend une commande

1. **Action** : il détecte allumer/éteindre — `allume, active, ouvre, démarre,
   mets en marche, on` / `éteins, coupe, ferme, arrête, off`.
2. **Cible** : il identifie l'entité visée, dans cet ordre :
   - **a) Tes alias** déclarés dans `config/ha_aliases.yaml` (prioritaires) ;
   - **b) Le nom convivial** (friendly_name) des entités HA : « lumière salon »
     trouve l'entité dont le nom contient « salon » dans le domaine `light`.
3. **Confirmation** : il te montre l'entité ciblée et attend ton « oui ».

> Avant, il fallait taper l'`entity_id` exact (`light.salon`) et « ON » seul
> n'était pas compris → JARVIS listait toutes les entités. C'est corrigé.

## Ajouter tes propres « phrases de compréhension »

Édite **`config/ha_aliases.yaml`** (rechargé à chaud, pas de redémarrage) :

```yaml
aliases:
  "luminaires salon": [light.salon_principal, light.salon_lampadaire]
  "lumière cuisine": light.cuisine
  "télé": media_player.tv_salon
  "volet chambre": cover.volet_chambre
  "ambiance": [light.salon_principal, light.guirlande, switch.led_meuble]
```

Règles :
- **Casse et accents ignorés.** « TÉLÉ », « tele », « télé » → pareil.
- Match = **tous les mots de l'alias présents** dans ta demande. L'alias
  `luminaires salon` matche « allume les **luminaires** du **salon** stp ».
- Une phrase peut viser **plusieurs entités** (liste) → JARVIS les actionne toutes
  d'un coup (ex. une scène « ambiance »).

## Trouver tes entity_id réels

- Dans HA : **Outils de développement → États** (colonne `entity_id`).
- Ou demande à JARVIS : « **liste les lumières** », « **liste les prises** ».

## Exemples qui marchent

| Tu dis / écris | Effet |
|---|---|
| « allume la lumière du salon » | résout `light.*salon*` → confirme → allume |
| « éteins les luminaires salon » (alias) | éteint toutes les entités de l'alias |
| « coupe la télé » (alias) | `media_player.tv_salon` → off |
| « allume light.bureau » | entity_id explicite, direct |
| « liste les lumières » | lecture (états), pas d'action |

## Dépannage

| Symptôme | Solution |
|---|---|
| « Je n'ai pas trouvé à quelle entité… » | Ajoute un alias, ou vérifie le friendly_name dans HA. |
| Mauvaise entité ciblée | Crée un alias précis pour lever l'ambiguïté. |
| « HA_TOKEN non configuré » | Renseigne `HA_URL` et `HA_TOKEN` dans `.env` (token longue durée : Profil HA → Sécurité). |
| Rien ne s'allume après confirmation | Vérifie que le token a les droits, et que l'entity_id existe. |
