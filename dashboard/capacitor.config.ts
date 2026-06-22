import type { CapacitorConfig } from '@capacitor/cli';

/**
 * Configuration Capacitor — emballe la webapp statique (out/) en APK Android.
 * Voir docs/MOBILE_ANDROID.md pour le flux complet.
 */
const config: CapacitorConfig = {
  appId: 'com.jarvis.app',
  appName: 'JARVIS',
  webDir: 'out',
  server: {
    // Origine http://localhost dans la WebView → appels http://IP:8000 sans
    // erreur de contenu mixte ; cleartext autorise le HTTP en clair (LAN).
    androidScheme: 'http',
    cleartext: true,
  },
};

export default config;
