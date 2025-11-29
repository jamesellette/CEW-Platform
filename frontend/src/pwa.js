/**
 * PWA Utilities for CEW Training Platform
 * Provides helpers for service worker, notifications, and offline support
 */

// Check if the app is running as a PWA (installed)
export function isPWAInstalled() {
  return window.matchMedia('(display-mode: standalone)').matches ||
         window.navigator.standalone === true;
}

// Check if service worker is supported
export function isServiceWorkerSupported() {
  return 'serviceWorker' in navigator;
}

// Check if push notifications are supported
export function isPushNotificationSupported() {
  return 'PushManager' in window && 'Notification' in window;
}

// Get current notification permission status
export function getNotificationPermission() {
  if (!('Notification' in window)) {
    return 'unsupported';
  }
  return Notification.permission;
}

// Request notification permission
export async function requestNotificationPermission() {
  if (!('Notification' in window)) {
    return false;
  }
  
  try {
    const permission = await Notification.requestPermission();
    return permission === 'granted';
  } catch (error) {
    console.error('Error requesting notification permission:', error);
    return false;
  }
}

// Subscribe to push notifications
export async function subscribeToPushNotifications(vapidPublicKey) {
  if (!isPushNotificationSupported()) {
    throw new Error('Push notifications are not supported');
  }
  
  const permission = await requestNotificationPermission();
  if (!permission) {
    throw new Error('Notification permission denied');
  }
  
  const registration = await navigator.serviceWorker.ready;
  
  // Convert VAPID key from base64 to Uint8Array
  const convertedVapidKey = urlBase64ToUint8Array(vapidPublicKey);
  
  const subscription = await registration.pushManager.subscribe({
    userVisibleOnly: true,
    applicationServerKey: convertedVapidKey
  });
  
  return subscription;
}

// Unsubscribe from push notifications
export async function unsubscribeFromPushNotifications() {
  const registration = await navigator.serviceWorker.ready;
  const subscription = await registration.pushManager.getSubscription();
  
  if (subscription) {
    await subscription.unsubscribe();
    return true;
  }
  
  return false;
}

// Get current push subscription
export async function getPushSubscription() {
  if (!isServiceWorkerSupported()) {
    return null;
  }
  
  const registration = await navigator.serviceWorker.ready;
  return registration.pushManager.getSubscription();
}

// Show a local notification (not push)
export async function showLocalNotification(title, options = {}) {
  const permission = await requestNotificationPermission();
  if (!permission) {
    return null;
  }
  
  const registration = await navigator.serviceWorker.ready;
  
  return registration.showNotification(title, {
    icon: '/icons/icon-192x192.png',
    badge: '/icons/icon-72x72.png',
    ...options
  });
}

// Check if online
export function isOnline() {
  return navigator.onLine;
}

// Add online/offline event listeners
export function addNetworkListeners(onOnline, onOffline) {
  window.addEventListener('online', onOnline);
  window.addEventListener('offline', onOffline);
  
  // Return cleanup function
  return () => {
    window.removeEventListener('online', onOnline);
    window.removeEventListener('offline', onOffline);
  };
}

// Send message to service worker
export async function sendMessageToServiceWorker(message) {
  if (!isServiceWorkerSupported()) {
    return null;
  }
  
  const registration = await navigator.serviceWorker.ready;
  
  if (registration.active) {
    registration.active.postMessage(message);
    return true;
  }
  
  return false;
}

// Clear all caches
export async function clearAllCaches() {
  if ('caches' in window) {
    const cacheNames = await caches.keys();
    await Promise.all(cacheNames.map(name => caches.delete(name)));
    return true;
  }
  return false;
}

// Get cache storage usage
export async function getCacheStorageUsage() {
  if ('storage' in navigator && 'estimate' in navigator.storage) {
    const estimate = await navigator.storage.estimate();
    return {
      quota: estimate.quota,
      usage: estimate.usage,
      percentUsed: ((estimate.usage / estimate.quota) * 100).toFixed(2)
    };
  }
  return null;
}

// Register for background sync
export async function registerBackgroundSync(tag) {
  if (!('sync' in ServiceWorkerRegistration.prototype)) {
    return false;
  }
  
  const registration = await navigator.serviceWorker.ready;
  await registration.sync.register(tag);
  return true;
}

// Helper: Convert base64 VAPID key to Uint8Array
function urlBase64ToUint8Array(base64String) {
  const padding = '='.repeat((4 - base64String.length % 4) % 4);
  const base64 = (base64String + padding)
    .replace(/-/g, '+')
    .replace(/_/g, '/');
  
  const rawData = window.atob(base64);
  const outputArray = new Uint8Array(rawData.length);
  
  for (let i = 0; i < rawData.length; ++i) {
    outputArray[i] = rawData.charCodeAt(i);
  }
  
  return outputArray;
}

// PWA install prompt handler
let deferredPrompt = null;

export function initInstallPrompt() {
  window.addEventListener('beforeinstallprompt', (e) => {
    e.preventDefault();
    deferredPrompt = e;
  });
}

export function canInstallPWA() {
  return deferredPrompt !== null;
}

export async function promptPWAInstall() {
  if (!deferredPrompt) {
    return false;
  }
  
  deferredPrompt.prompt();
  const { outcome } = await deferredPrompt.userChoice;
  deferredPrompt = null;
  
  return outcome === 'accepted';
}

// Export all utilities
export default {
  isPWAInstalled,
  isServiceWorkerSupported,
  isPushNotificationSupported,
  getNotificationPermission,
  requestNotificationPermission,
  subscribeToPushNotifications,
  unsubscribeFromPushNotifications,
  getPushSubscription,
  showLocalNotification,
  isOnline,
  addNetworkListeners,
  sendMessageToServiceWorker,
  clearAllCaches,
  getCacheStorageUsage,
  registerBackgroundSync,
  initInstallPrompt,
  canInstallPWA,
  promptPWAInstall
};
