import { LocalStorageService } from './storage';
import { UIManager } from './ui';
import './style.css';

function initApp() {
  try {
    const storage = new LocalStorageService();
    new UIManager(storage);
  } catch (e) {
    console.error('Failed to initialize app:', e);
    alert('Failed to initialize the app. Please check if localStorage is available.');
  }
}

document.addEventListener('DOMContentLoaded', initApp);