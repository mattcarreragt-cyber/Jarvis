# Configuration Kubuntu — Nœud de Calcul GPU

Ce fichier contient toutes les commandes à exécuter **sur la machine Kubuntu**.  
Unraid est déjà configuré et opérationnel ; ce guide concerne uniquement le nœud GPU.

---

## 1. Pré-requis système

```bash
# Mettre à jour le système
sudo apt update && sudo apt upgrade -y

# Outils de base
sudo apt install -y curl wget git build-essential
```

---

## 2. Drivers NVIDIA

```bash
# Vérifier le GPU détecté
lspci | grep -i nvidia

# Installer les drivers (remplace 535 par la version recommandée pour ta carte)
sudo apt install -y nvidia-driver-535 nvidia-utils-535

# Redémarrer
sudo reboot

# Vérifier après redémarrage
nvidia-smi
```

---

## 3. Docker + NVIDIA Container Toolkit

```bash
# Installer Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# Installer NVIDIA Container Toolkit
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list \
  | sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' \
  | sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list

sudo apt update && sudo apt install -y nvidia-container-toolkit
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker

# Test
docker run --rm --gpus all nvidia/cuda:12.3.0-base-ubuntu22.04 nvidia-smi
```

---

## 4. Déploiement des services GPU

### 4a. Copier docker-compose.kubuntu.yml

Depuis le dépôt Jarvis (transférer le fichier sur Kubuntu) :

```bash
# Sur Unraid — copier via scp (remplace KUBUNTU_IP)
scp /mnt/user/appdata/jarvis/docker-compose.kubuntu.yml user@KUBUNTU_IP:~/jarvis/

# Sur Kubuntu — créer le dossier
mkdir -p ~/jarvis && cd ~/jarvis
```

### 4b. Créer le fichier .env Kubuntu

```bash
cat > ~/jarvis/.env << 'EOF'
# Ollama
OLLAMA_HOST=0.0.0.0

# ComfyUI (facultatif)
COMFYUI_PORT=8188

# Whisper
WHISPER_PORT=9000
EOF
```

### 4c. Lancer les services

```bash
cd ~/jarvis
docker compose -f docker-compose.kubuntu.yml up -d

# Vérifier
docker compose -f docker-compose.kubuntu.yml ps
```

---

## 5. Télécharger les modèles Ollama

> **Dimensionné pour ta carte 8 Go VRAM + 64 Go RAM.** Voir `config/capabilities.yaml`
> pour le budget VRAM et le champ `vram_gb` de chaque capacité.

```bash
# Attendre qu'Ollama soit lancé (environ 10 secondes)
sleep 10

# Modèle rapide (chat.fast) — ~5 Go VRAM, 100% GPU
docker exec kubuntu-ollama ollama pull qwen2.5:7b

# Modèle profond (chat.deep) — ~9 Go, offload CPU partiel (OK avec 64 Go RAM)
docker exec kubuntu-ollama ollama pull qwen2.5:14b

# Embeddings (mémoire sémantique) — ~0,5 Go
docker exec kubuntu-ollama ollama pull nomic-embed-text

# Vérifier les modèles disponibles
docker exec kubuntu-ollama ollama list
```

> **Important (8 Go VRAM) :** configure Ollama pour ne garder qu'**un seul modèle**
> chargé à la fois, sinon `qwen2.5:7b` + `qwen2.5:14b` tenteraient de cohabiter et
> satureraient la VRAM. Ajoute ces variables au service `ollama` de
> `docker-compose.kubuntu.yml` :
>
> ```yaml
>     environment:
>       OLLAMA_MAX_LOADED_MODELS: "1"   # un seul LLM résident à la fois
>       OLLAMA_KEEP_ALIVE: "5m"          # décharge après 5 min d'inactivité
> ```
>
> Le scheduler de JARVIS décharge en plus automatiquement les LLM avant une
> génération d'image (ComfyUI/SDXL occupe quasiment tout le GPU). Voir
> `_free_vram_for()` dans `api/app/orchestration/scheduler.py`.

> **Modèle plus profond (optionnel)** : `qwen2.5:32b` (~20 Go) tournera surtout
> en RAM/CPU (lent mais possible avec tes 64 Go). Si tu le veux, pull-le et passe
> `chat.deep` dessus dans `capabilities.yaml` + `CHAT_MODEL_DEEP` dans
> `api/app/llm/ollama.py`.

---

## 5bis. Modèle SDXL pour ComfyUI (génération d'images)

L'agent `image` utilise ComfyUI. Il faut télécharger un checkpoint SDXL dans le
dossier `checkpoints` de ComfyUI (volume `comfyui_models`).

```bash
# Télécharger SDXL base (~6.6 Go) dans le volume monté par ComfyUI
docker exec jarvis-compute-comfyui-1 sh -c '
  cd /opt/ComfyUI/models/checkpoints && \
  wget -O sd_xl_base_1.0.safetensors \
  https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0/resolve/main/sd_xl_base_1.0.safetensors
'
# (adapte le nom du conteneur si besoin : docker ps | grep comfyui)
```

> Le nom du fichier doit correspondre à `COMFYUI_CHECKPOINT` (défaut
> `sd_xl_base_1.0.safetensors`, configurable dans le `.env` Unraid).

> **VRAM 8 Go :** SDXL occupe quasiment tout le GPU. C'est pour ça que la capacité
> `image` est marquée `exclusive` dans `capabilities.yaml` — JARVIS décharge
> automatiquement les modèles Ollama avant chaque génération, puis Ollama les
> recharge à la demande pour le chat suivant.

Test rapide depuis Unraid :
```bash
curl "http://KUBUNTU_IP:8188/system_stats"   # ComfyUI répond
```

---

## 5ter. Génération de vidéo (ComfyUI + AnimateDiff)

L'agent `video` produit des clips 10-20 s (512×512) en **asynchrone** via
AnimateDiff + fenêtres de contexte glissantes — la seule approche viable sur 8 Go.

### Nœuds custom ComfyUI requis

```bash
# Dans le conteneur ComfyUI, installer les custom nodes
docker exec jarvis-compute-comfyui-1 sh -c '
  cd /opt/ComfyUI/custom_nodes && \
  git clone https://github.com/Kosinkadink/ComfyUI-AnimateDiff-Evolved.git && \
  git clone https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite.git
'
# Redémarrer ComfyUI
docker restart jarvis-compute-comfyui-1
```

### Modèles requis

```bash
docker exec jarvis-compute-comfyui-1 sh -c '
  # Checkpoint SD1.5 (~4 Go)
  cd /opt/ComfyUI/models/checkpoints && \
  wget -O v1-5-pruned-emaonly.safetensors \
  https://huggingface.co/runwayml/stable-diffusion-v1-5/resolve/main/v1-5-pruned-emaonly.safetensors && \
  # Module de mouvement AnimateDiff (~1.7 Go)
  mkdir -p /opt/ComfyUI/models/animatediff_models && \
  cd /opt/ComfyUI/models/animatediff_models && \
  wget -O mm_sd_v15_v2.ckpt \
  https://huggingface.co/guoyww/animatediff/resolve/main/mm_sd_v15_v2.ckpt
'
```

> **Le workflow est paramétrable.** JARVIS lit `config/comfyui_video_workflow.json`
> (monté en volume sur Unraid) et y injecte le prompt, le nombre de frames et le fps
> via les tokens `__PROMPT__`, `__NEG__`, `__FRAMES__`, `__FPS__`.
> Si tes noms de nœuds diffèrent : construis le workflow dans ComfyUI, fais
> **Workflow → Export (API)**, et remplace le fichier en gardant les tokens aux bons
> endroits (texte positif, négatif, `batch_size` du latent, `frame_rate` du
> VideoCombine). Aucun redémarrage nécessaire (rechargé à chaud).

> **8 Go VRAM :** comme l'image, la vidéo est `exclusive` — les LLM sont déchargés
> avant. Durée 10-20 s = ~5-15 min de calcul. Si OOM, baisse `VIDEO_FPS` ou la
> résolution dans le workflow (512→384), ou réduis `context_length`.

> **Aucun filtre de contenu :** les modèles AnimateDiff/SVD locaux ne font aucune
> modération — c'est le fonctionnement normal des modèles open en local (lab hors ligne).

### Image → vidéo (animer une image existante, SVD)

L'icône 🎬 *« Animer une image »* du dashboard envoie une image à ComfyUI qui
l'anime via **Stable Video Diffusion**. Modèle requis :

```bash
docker exec jarvis-compute-comfyui-1 sh -c '
  cd /opt/ComfyUI/models/checkpoints && \
  wget -O svd_xt.safetensors \
  https://huggingface.co/stabilityai/stable-video-diffusion-img2vid-xt/resolve/main/svd_xt.safetensors
'
```

> Workflow : `config/comfyui_img2vid_workflow.json` (tokens `__IMAGE__`,
> `__FRAMES__`, `__FPS__`). SVD produit ~2-4 s par défaut ; sur 8 Go reste en
> 1024×576. Sur RunPod, remplace par un workflow LTX/Stable-Video plus long.

### Audio / musique (Stable Audio Open)

L'agent `audio` génère musique/sons/jingles via ComfyUI. Modèle requis :

```bash
docker exec jarvis-compute-comfyui-1 sh -c '
  cd /opt/ComfyUI/models/checkpoints && \
  wget -O stable_audio_open_1.0.safetensors \
  https://huggingface.co/stabilityai/stable-audio-open-1.0/resolve/main/model.safetensors
'
# Le T5 text encoder est téléchargé automatiquement au 1er run par ComfyUI.
```

> Workflow : `config/comfyui_audio_workflow.json` (tokens `__PROMPT__`,
> `__NEG__`, `__SECONDS__`). Stable Audio Open génère jusqu'à ~47 s. Pour de la
> musique chantée, remplace par un workflow **ACE-Step**.

---

## 6. Faster-Whisper (STT)

Le service est inclus dans `docker-compose.kubuntu.yml` (image `onerahmet/openai-whisper-asr-webservice`).  
Le modèle `large-v3` est téléchargé automatiquement au premier démarrage (~3 Go).

Test :
```bash
curl http://localhost:9000/asr?task=transcribe&language=fr \
  -F "audio_file=@/chemin/vers/test.wav"
```

---

## 7. Wake-on-LAN — Configuration BIOS

Pour que Kubuntu puisse être réveillé par Unraid :

1. **Entrer dans le BIOS** (touche Del ou F2 au démarrage)
2. Chercher : `Power Management` → `Wake on LAN` → **Enabled**
3. Également activer : `Resume by PCI-E device` ou `WOL from S5`
4. **Sauvegarder et quitter**

### Récupérer l'adresse MAC de Kubuntu

```bash
ip link show | grep -A1 "ether" | grep "ether"
# Exemple : link/ether aa:bb:cc:dd:ee:ff
```

→ Copier cette adresse dans le `.env` d'Unraid : `KUBUNTU_MAC=aa:bb:cc:dd:ee:ff`

### Tester le WoL depuis Unraid

```bash
# Sur Unraid (via terminal)
# Éteindre Kubuntu proprement d'abord
# Puis depuis Unraid :
python3 -c "
import socket, struct
mac = 'aa:bb:cc:dd:ee:ff'.replace(':','')
pkt = b'\xff'*6 + bytes.fromhex(mac)*16
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
s.sendto(pkt, ('255.255.255.255', 9))
print('Magic packet envoyé')
"
```

---

## 8. Vérification finale

Depuis Unraid, vérifier que tous les services Kubuntu répondent :

```bash
# Ollama
curl http://KUBUNTU_IP:11434/api/tags

# Whisper
curl http://KUBUNTU_IP:9000/

# ComfyUI (si installé)
curl http://KUBUNTU_IP:8188/
```

Et dans l'interface JARVIS, le StatusBar devrait afficher OLLAMA, STT en vert.

---

## 9. Activer WoL dans Jarvis

Dans le `.env` sur Unraid :

```env
KUBUNTU_WOL_ENABLED=true
KUBUNTU_MAC=aa:bb:cc:dd:ee:ff   # adresse récupérée à l'étape 7
KUBUNTU_URL=http://KUBUNTU_IP:11434
KUBUNTU_WOL_TIMEOUT=120         # secondes d'attente max après WoL
```

Redémarrer l'API Jarvis pour prendre en compte les changements.

---

## Récapitulatif des ports Kubuntu

| Service        | Port  | URL de santé              |
|----------------|-------|---------------------------|
| Ollama         | 11434 | `/api/tags`               |
| Faster-Whisper | 9000  | `/`                       |
| ComfyUI        | 8188  | `/`                       |
