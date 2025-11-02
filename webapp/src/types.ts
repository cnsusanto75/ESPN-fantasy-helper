export interface LeagueConfig {
  leagueId: number;
  year: number;
  s2: string;
  swid: string;
  teamId?: number;  // Optional because it's set after initial validation
}

export interface Save extends LeagueConfig {
  id: string;
  created: number;
  updated: number;
  teamId: number;  // Required once saved
}

export interface SaveStorage {
  loadSaves(): Save[];
  saveToPersistence(saves: Save[]): void;
  createSave(config: Omit<Save, 'id' | 'created' | 'updated'>): Save;
  updateSave(save: Save): void;
  deleteSave(id: string): void;
}

export interface UIElements {
  saveList: HTMLDivElement | null;
  newSaveBtn: HTMLButtonElement | null;
  newSaveModal: HTMLDivElement | null;
  leagueIdInput: HTMLInputElement | null;
  yearInput: HTMLInputElement | null;
  s2Input: HTMLInputElement | null;
  swidInput: HTMLInputElement | null;
  createSaveBtn: HTMLButtonElement | null;
  cancelSaveBtn: HTMLButtonElement | null;
  saveTitle: HTMLInputElement | null;
  saveContent: HTMLTextAreaElement | null;
  saveButton: HTMLButtonElement | null;
  deleteButton: HTMLButtonElement | null;
}