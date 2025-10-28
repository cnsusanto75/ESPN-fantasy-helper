import type { Save, SaveStorage } from './types';

export class LocalStorageService implements SaveStorage {
  private readonly STORAGE_KEY = 'webapp_saves';

  constructor() {
    this.checkAvailability();
  }

  private checkAvailability(): void {
    try {
      localStorage.setItem('test', 'test');
      localStorage.removeItem('test');
    } catch (e) {
      throw new Error('LocalStorage is not available');
    }
  }

  loadSaves(): Save[] {
    try {
      return JSON.parse(localStorage.getItem(this.STORAGE_KEY) || '[]');
    } catch (e) {
      console.error('Failed to load saves:', e);
      return [];
    }
  }

  saveToPersistence(saves: Save[]): void {
    try {
      localStorage.setItem(this.STORAGE_KEY, JSON.stringify(saves));
    } catch (e) {
      console.error('Failed to persist saves:', e);
      throw e;
    }
  }

  createSave(title: string, content: string = ''): Save {
    const save: Save = {
      id: Date.now().toString(),
      title: title.trim() || 'Untitled',
      content,
      created: Date.now(),
      updated: Date.now()
    };

    const saves = this.loadSaves();
    saves.unshift(save);
    this.saveToPersistence(saves);
    return save;
  }

  updateSave(save: Save): void {
    const saves = this.loadSaves();
    const index = saves.findIndex(s => s.id === save.id);
    if (index === -1) return;

    saves[index] = {
      ...save,
      updated: Date.now()
    };
    
    this.saveToPersistence(saves);
  }

  deleteSave(id: string): void {
    const saves = this.loadSaves();
    const filtered = saves.filter(s => s.id !== id);
    this.saveToPersistence(filtered);
  }
}