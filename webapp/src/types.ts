export interface Save {
  id: string;
  title: string;
  content: string;
  created: number;
  updated: number;
}

export interface SaveStorage {
  loadSaves(): Save[];
  saveToPersistence(saves: Save[]): void;
  createSave(title: string, content?: string): Save;
  updateSave(save: Save): void;
  deleteSave(id: string): void;
}

export interface UIElements {
  saveList: HTMLDivElement;
  newSaveBtn: HTMLButtonElement;
  newSaveModal: HTMLDivElement;
  newSaveTitle: HTMLInputElement;
  createSaveBtn: HTMLButtonElement;
  cancelSaveBtn: HTMLButtonElement;
  saveTitle: HTMLInputElement;
  saveContent: HTMLTextAreaElement;
  saveButton: HTMLButtonElement;
  deleteButton: HTMLButtonElement;
}