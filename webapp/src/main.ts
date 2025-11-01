import { LocalStorageService } from './storage';
import { UIManager } from './ui';
import './style.css';

function initApp() {
  try {
    // Test localStorage availability
    if (typeof window.localStorage === 'undefined') {
      throw new Error('localStorage is not available in this browser');
    }
    
    const storage = new LocalStorageService();
    // The UIManager instance is used but not stored
    new UIManager(storage);
  } catch (e: unknown) {
    console.error('Failed to initialize app:', e);
    const errorMessage = e instanceof Error ? e.message : 'Unknown error occurred';
    alert(`Failed to initialize the app: ${errorMessage}`);
  }
}

document.addEventListener('DOMContentLoaded', initApp);