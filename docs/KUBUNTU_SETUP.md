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

```bash
# Attendre qu'Ollama soit lancé (environ 10 secondes)
sleep 10

# Modèle rapide (chat.fast)
docker exec kubuntu-ollama ollama pull llama3.1:8b

# Modèle profond (chat.deep) — ~40 Go, long à télécharger
docker exec kubuntu-ollama ollama pull llama3.1:70b

# Embeddings (mémoire sémantique)
docker exec kubuntu-ollama ollama pull nomic-embed-text

# Vérifier les modèles disponibles
docker exec kubuntu-ollama ollama list
```

> **Note :** `llama3.1:70b` requiert ~48 Go de VRAM. Si ta carte n'a pas assez de mémoire,
> remplace par `llama3.1:8b` pour les deux et mets à jour `config/capabilities.yaml` en conséquence.

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
