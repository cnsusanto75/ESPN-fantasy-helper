import type { Save, SaveStorage, UIElements, LeagueConfig } from './types';

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
      leagueIdInput: document.getElementById('leagueId') as HTMLInputElement,
      yearInput: document.getElementById('year') as HTMLInputElement,
      s2Input: document.getElementById('s2') as HTMLInputElement,
      swidInput: document.getElementById('swid') as HTMLInputElement,
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
      saveTitle
    } = this.elements;

    // Check if elements exist before adding listeners
    if (newSaveBtn) {
      newSaveBtn.addEventListener('click', () => this.showNewSaveModal());
    }
    if (createSaveBtn) {
      createSaveBtn.addEventListener('click', () => this.handleCreateSave());
    }
    if (cancelSaveBtn) {
      cancelSaveBtn.addEventListener('click', () => this.hideNewSaveModal());
    }
    
    // Save changes
    if (saveButton) {
      saveButton.addEventListener('click', () => this.handleSaveChanges());
    }
    if (saveTitle) {
      saveTitle.addEventListener('change', () => this.handleSaveChanges());
    }
    
    // Delete
    if (deleteButton) {
      deleteButton.addEventListener('click', () => this.handleDelete());
    }
  }

  private showNewSaveModal(): void {
    const { newSaveModal } = this.elements;
    if (newSaveModal) {
      newSaveModal.classList.add('show');
    }
  }

  private hideNewSaveModal(): void {
    const { newSaveModal } = this.elements;
    if (newSaveModal) {
      newSaveModal.classList.remove('show');
    }
  }

  private refreshSavesList(): void {
    const { saveList } = this.elements;
    if (!saveList) return;

    const saves = this.storage.loadSaves();
    
    saveList.innerHTML = '';
    
    if (saves.length === 0) {
      const emptyMessage = document.createElement('div');
      emptyMessage.className = 'save-item';
      emptyMessage.style.color = '#666';
      emptyMessage.textContent = 'No league configurations yet';
      saveList.appendChild(emptyMessage);
      return;
    }

    saves.forEach(save => {
      const item = document.createElement('div');
      item.className = 'save-item';
      if (this.currentSave?.id === save.id) {
        item.classList.add('active');
      }

      const info = document.createElement('div');
      info.className = 'save-info';
      
      const leagueInfo = document.createElement('div');
      leagueInfo.className = 'league-info';
      leagueInfo.textContent = `League ID: ${save.leagueId} (${save.year})`;
      info.appendChild(leagueInfo);

      const date = document.createElement('small');
      date.style.color = '#666';
      date.style.fontSize = '0.8em';
      date.textContent = `Updated: ${new Date(save.updated).toLocaleDateString()}`;
      info.appendChild(date);

      item.appendChild(info);
      item.addEventListener('click', () => this.loadSave(save));
      saveList.appendChild(item);
    });
  }

  private async loadSave(save: Save): Promise<void> {
    const { leagueIdInput, yearInput, s2Input, swidInput, saveButton, deleteButton } = this.elements;
    
    this.currentSave = save;
    
    if (leagueIdInput) {
      leagueIdInput.style.display = 'block';
      leagueIdInput.value = save.leagueId.toString();
    }
    if (yearInput) {
      yearInput.style.display = 'block';
      yearInput.value = save.year.toString();
    }
    if (s2Input) {
      s2Input.style.display = 'block';
      s2Input.value = save.s2;
    }
    if (swidInput) {
      swidInput.style.display = 'block';
      swidInput.value = save.swid;
    }
    if (saveButton) {
      saveButton.style.display = 'block';
    }
    if (deleteButton) {
      deleteButton.style.display = 'block';
    }
    
    try {
      // Notify backend of active save
      const response = await fetch('http://localhost:5000/set-active-save', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          saveId: save.id,
          leagueId: save.leagueId,
          year: save.year,
          s2: save.s2,
          swid: save.swid
        })
      });

      if (!response.ok) {
        console.error('Failed to update active save in backend');
      }
    } catch (error) {
      console.error('Error updating active save in backend:', error);
    }
    
    this.refreshSavesList();
  }

  private async showTeamSelectModal(credentials: LeagueConfig): Promise<number | null> {
    const teamSelectModal = document.getElementById('teamSelectModal') as HTMLDivElement;
    const teamSelect = document.getElementById('teamSelect') as HTMLSelectElement;
    const confirmBtn = document.getElementById('confirmTeamSelect') as HTMLButtonElement;
    const cancelBtn = document.getElementById('cancelTeamSelect') as HTMLButtonElement;

    try {
      const response = await fetch('http://localhost:5000/get-league-teams', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(credentials)
      });

      const data = await response.json();
      if ('error' in data) {
        throw new Error(data.error);
      }

      // Clear and populate team select
      teamSelect.innerHTML = '';
      Object.entries(data.teams).forEach(([id, name]) => {
        const option = document.createElement('option');
        option.value = id;
        option.textContent = name as string;
        teamSelect.appendChild(option);
      });

      // Show modal
      teamSelectModal.classList.add('show');

      // Return promise that resolves when user makes selection
      return new Promise((resolve) => {
        const handleConfirm = () => {
          const teamId = parseInt(teamSelect.value, 10);
          cleanup();
          resolve(teamId);
        };

        const handleCancel = () => {
          cleanup();
          resolve(null);
        };

        const cleanup = () => {
          confirmBtn.removeEventListener('click', handleConfirm);
          cancelBtn.removeEventListener('click', handleCancel);
          teamSelectModal.classList.remove('show');
        };

        confirmBtn.addEventListener('click', handleConfirm);
        cancelBtn.addEventListener('click', handleCancel);
      });
    } catch (error) {
      console.error('Error getting teams:', error);
      alert('Error loading teams. Please try again.');
      teamSelectModal.classList.remove('show');
      return null;
    }
  }

  private async handleCreateSave(): Promise<void> {
    const { leagueIdInput, yearInput, s2Input, swidInput } = this.elements;

    if (!leagueIdInput || !yearInput || !s2Input || !swidInput) {
      alert('Error: Form elements not found');
      return;
    }

    const leagueIdValue = leagueIdInput.value.trim();
    const yearValue = yearInput.value.trim();
    const s2Value = s2Input.value.trim();
    const swidValue = swidInput.value.trim();

    if (!leagueIdValue || !yearValue || !s2Value || !swidValue) {
      alert('Please fill in all fields');
      return;
    }

    const leagueId = parseInt(leagueIdValue, 10);
    const year = parseInt(yearValue, 10);

    if (isNaN(leagueId) || isNaN(year)) {
      alert('Please enter valid numbers for League ID and Year');
      return;
    }

    const credentials = {
      leagueId,
      year,
      s2: s2Value,
      swid: swidValue
    };

    try {
      // First validate the credentials
      const response = await fetch('http://localhost:5000/validate-league', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(credentials)
      });

      const data: { valid: boolean; error?: string } = await response.json();
      
      if (!data.valid) {
        alert(data.error || 'Invalid league credentials. Please check and try again.');
        return;
      }

      // Show team selection modal and wait for user to select their team
      const teamId = await this.showTeamSelectModal(credentials);
      
      if (teamId === null) {
        // User cancelled team selection
        return;
      }

      // Create save with selected team ID
      const save = this.storage.createSave({
        ...credentials,
        teamId
      });

      this.refreshSavesList();
      await this.loadSave(save);
      this.hideNewSaveModal();
    } catch (error) {
      console.error('Error validating league:', error);
      alert('Error validating league credentials. Please try again.');
    }
  }

  private handleSaveChanges(): void {
    if (!this.currentSave) return;

    const { leagueIdInput, yearInput, s2Input, swidInput } = this.elements;
    
    if (!leagueIdInput || !yearInput || !s2Input || !swidInput) {
      alert('Error: Form elements not found');
      return;
    }

    const updatedSave: Save = {
      ...this.currentSave,
      leagueId: parseInt(leagueIdInput.value, 10),
      year: parseInt(yearInput.value, 10),
      s2: s2Input.value,
      swid: swidInput.value,
      updated: Date.now()
    };

    this.storage.updateSave(updatedSave);
    this.currentSave = updatedSave;
    this.refreshSavesList();
  }

  private async handleDelete(): Promise<void> {
    if (!this.currentSave || !confirm('Delete this save?')) return;

    this.storage.deleteSave(this.currentSave.id);
    this.hideEditor();
    
    try {
      // Clear the active save in the backend
      await fetch('http://localhost:5000/set-active-save', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          saveId: null,
          leagueId: null,
          year: null,
          s2: null,
          swid: null
        })
      });
    } catch (error) {
      console.error('Error clearing active save in backend:', error);
    }
    
    this.currentSave = null;
    this.refreshSavesList();
  }

  private hideEditor(): void {
    const { saveTitle, saveContent, saveButton, deleteButton } = this.elements;
    
    if (saveTitle) saveTitle.style.display = 'none';
    if (saveContent) saveContent.style.display = 'none';
    if (saveButton) saveButton.style.display = 'none';
    if (deleteButton) deleteButton.style.display = 'none';
  }
}