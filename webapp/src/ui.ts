import type { Save, SaveStorage, UIElements } from './types';

export class UIManager {
  private currentSave: Save | null = null;
  private elements: UIElements;

  constructor(
    private readonly storage: SaveStorage
  ) {
    this.elements = this.getElements();
    this.setupListeners();
    this.refreshSavesList();
  }

  private getElements(): UIElements {
    return {
      saveList: document.getElementById('saveList') as HTMLDivElement,
      newSaveBtn: document.getElementById('newSave') as HTMLButtonElement,
      newSaveModal: document.getElementById('newSaveModal') as HTMLDivElement,
      newSaveTitle: document.getElementById('newSaveTitle') as HTMLInputElement,
      createSaveBtn: document.getElementById('createSave') as HTMLButtonElement,
      cancelSaveBtn: document.getElementById('cancelSave') as HTMLButtonElement,
      saveTitle: document.getElementById('saveTitle') as HTMLInputElement,
      saveContent: document.getElementById('saveContent') as HTMLTextAreaElement,
      saveButton: document.getElementById('saveButton') as HTMLButtonElement,
      deleteButton: document.getElementById('deleteButton') as HTMLButtonElement
    };
  }

  private setupListeners(): void {
    const {
      newSaveBtn,
      createSaveBtn,
      cancelSaveBtn,
      saveButton,
      deleteButton,
      saveTitle,
      newSaveTitle
    } = this.elements;

    // New save
    newSaveBtn.addEventListener('click', () => this.showNewSaveModal());
    createSaveBtn.addEventListener('click', () => this.handleCreateSave());
    cancelSaveBtn.addEventListener('click', () => this.hideNewSaveModal());
    
    // Save changes
    saveButton.addEventListener('click', () => this.handleSaveChanges());
    saveTitle.addEventListener('change', () => this.handleSaveChanges());
    
    // Delete
    deleteButton.addEventListener('click', () => this.handleDelete());

    // Modal enter key
    newSaveTitle.addEventListener('keyup', (e) => {
      if (e.key === 'Enter') this.handleCreateSave();
      if (e.key === 'Escape') this.hideNewSaveModal();
    });
  }

  private showNewSaveModal(): void {
    const { newSaveModal, newSaveTitle } = this.elements;
    newSaveModal.classList.add('show');
    newSaveTitle.value = '';
    newSaveTitle.focus();
  }

  private hideNewSaveModal(): void {
    const { newSaveModal, newSaveTitle } = this.elements;
    newSaveModal.classList.remove('show');
    newSaveTitle.value = '';
  }

  private refreshSavesList(): void {
    const { saveList } = this.elements;
    const saves = this.storage.loadSaves();
    
    saveList.innerHTML = '';
    
    if (saves.length === 0) {
      const emptyMessage = document.createElement('div');
      emptyMessage.className = 'save-item';
      emptyMessage.style.color = '#666';
      emptyMessage.textContent = 'No saves yet';
      saveList.appendChild(emptyMessage);
      return;
    }

    saves.forEach(save => {
      const item = document.createElement('div');
      item.className = 'save-item';
      if (this.currentSave?.id === save.id) {
        item.classList.add('active');
      }

      const title = document.createElement('span');
      title.textContent = save.title;
      item.appendChild(title);

      const date = document.createElement('small');
      date.style.color = '#666';
      date.style.fontSize = '0.8em';
      date.textContent = new Date(save.updated).toLocaleDateString();
      item.appendChild(date);

      item.addEventListener('click', () => this.loadSave(save));
      saveList.appendChild(item);
    });
  }

  private loadSave(save: Save): void {
    const { saveTitle, saveContent, saveButton, deleteButton } = this.elements;
    
    this.currentSave = save;
    
    saveTitle.style.display = 'block';
    saveContent.style.display = 'block';
    saveButton.style.display = 'block';
    deleteButton.style.display = 'block';

    saveTitle.value = save.title;
    saveContent.value = save.content;
    
    this.refreshSavesList();
  }

  private handleCreateSave(): void {
    const { newSaveTitle } = this.elements;
    const title = newSaveTitle.value.trim();
    if (!title) return;

    const save = this.storage.createSave(title);
    this.hideNewSaveModal();
    this.refreshSavesList();
    this.loadSave(save);
  }

  private handleSaveChanges(): void {
    if (!this.currentSave) return;

    const { saveTitle, saveContent } = this.elements;
    
    this.currentSave = {
      ...this.currentSave,
      title: saveTitle.value,
      content: saveContent.value,
      updated: Date.now()
    };

    this.storage.updateSave(this.currentSave);
    this.refreshSavesList();
  }

  private handleDelete(): void {
    if (!this.currentSave || !confirm('Delete this save?')) return;

    this.storage.deleteSave(this.currentSave.id);
    this.hideEditor();
    this.currentSave = null;
    this.refreshSavesList();
  }

  private hideEditor(): void {
    const { saveTitle, saveContent, saveButton, deleteButton } = this.elements;
    saveTitle.style.display = 'none';
    saveContent.style.display = 'none';
    saveButton.style.display = 'none';
    deleteButton.style.display = 'none';
  }
}