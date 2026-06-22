#!/usr/bin/env bash
# Construit la webapp statique pour l'APK Android (Capacitor).
# Usage : NEXT_PUBLIC_API_URL=http://192.168.1.50:8000 [NEXT_PUBLIC_API_KEY=...] ./scripts/build-apk.sh
set -euo pipefail
cd "$(dirname "$0")/.."

: "${NEXT_PUBLIC_API_URL:?Définis NEXT_PUBLIC_API_URL (ex. http://192.168.1.50:8000)}"

echo "▶ Build statique (out/) vers API : $NEXT_PUBLIC_API_URL"
BUILD_TARGET=export npm run build

# Capacitor n'est PAS dans package.json (sinon il casserait `npm ci` du build Docker).
# On l'installe à la demande, sans toucher au lockfile, uniquement pour fabriquer l'APK.
if [ ! -d node_modules/@capacitor/cli ]; then
  echo "▶ Installation de Capacitor (à la demande, --no-save)"
  npm install --no-save @capacitor/cli@^6.2.0 @capacitor/core@^6.2.0 @capacitor/android@^6.2.0
fi

# 1ʳᵉ fois seulement : ajoute la plateforme Android
if [ ! -d android ]; then
  echo "▶ Première fois : ajout de la plateforme Android"
  npx cap add android
fi

echo "▶ Synchronisation Capacitor"
npx cap sync android

echo "✅ Terminé. Ouvre Android Studio pour compiler l'APK :"
echo "   npx cap open android   (puis Build > Build APK)"
