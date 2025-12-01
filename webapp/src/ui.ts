import type { Save, SaveStorage, UIElements, LeagueConfig, Settings } from './types';

export class UIManager {
  private currentSave: Save | null = null;
  private elements: UIElements;
  private settings: Settings = { theme: 'light' };
  private readonly API_URL = 'http://localhost:5000';

  private hideEditor(): void {
    const { saveTitle, saveContent } = this.elements;
    if (saveTitle) saveTitle.style.display = 'none';
    if (saveContent) saveContent.style.display = 'none';
    this.resetLeagueData();
  }

  private toggleSidebar(): void {
    const container = document.querySelector('.sidebar-container') as HTMLElement;
    if (container) {
      const isCollapsed = container.classList.toggle('collapsed');
      
      // Update collapse button icon
      if (this.elements.collapseButton) {
        this.elements.collapseButton.textContent = isCollapsed ? '›' : '‹';
      }

      // Update margins for content areas
      const margin = isCollapsed ? '30px' : '250px';
      const savesContent = document.querySelector('.saves-content') as HTMLElement;
      const contentArea = document.querySelector('.content') as HTMLElement;
      
      if (savesContent) {
        savesContent.style.marginLeft = margin;
      }
      if (contentArea) {
        contentArea.style.marginLeft = margin;
      }

      // Store collapse state
      localStorage.setItem('sidebarCollapsed', isCollapsed.toString());
    }
  }

  private loadSidebarState(): void {
    const container = document.querySelector('.sidebar-container') as HTMLElement;
    if (container && this.elements.collapseButton) {
      const isCollapsed = localStorage.getItem('sidebarCollapsed') === 'true';
      if (isCollapsed) {
        container.classList.add('collapsed');
        this.elements.collapseButton.textContent = '›';
        
        // Update margins for content areas
        const margin = '30px';
        const savesContent = document.querySelector('.saves-content') as HTMLElement;
        const contentArea = document.querySelector('.content') as HTMLElement;
        
        if (savesContent) {
          savesContent.style.marginLeft = margin;
        }
        if (contentArea) {
          contentArea.style.marginLeft = margin;
        }
      } else {
        this.elements.collapseButton.textContent = '‹';
        const margin = '250px';
        const savesContent = document.querySelector('.saves-content') as HTMLElement;
        const contentArea = document.querySelector('.content') as HTMLElement;
        if (savesContent) {
          savesContent.style.marginLeft = margin;
        }
        if (contentArea) {
          contentArea.style.marginLeft = margin;
        }
      }
    }
  }

  constructor(private readonly storage: SaveStorage) {
    this.elements = this.getElements();
    this.setupListeners();
    this.refreshSavesList();
    this.loadSettings();
    this.applyTheme();
    this.loadSidebarState();
    this.resetLeagueData();
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
      tabSettings: document.getElementById('tabSettings') as HTMLButtonElement,
      settingsModal: document.getElementById('settingsModal') as HTMLDivElement,
      closeSettingsBtn: document.getElementById('closeSettings') as HTMLButtonElement,
      savesContainer: document.getElementById('savesContainer') as HTMLDivElement,
      themeToggle: document.getElementById('themeToggle') as HTMLButtonElement,
      collapseButton: document.getElementById('collapseButton') as HTMLButtonElement,
      teamRoster: document.getElementById('teamRoster') as HTMLDivElement,
      topFreeAgents: document.getElementById('topFreeAgents') as HTMLDivElement,
      playerCard: document.getElementById('playerCard') as HTMLDivElement,
      playerCardName: document.getElementById('playerCardName') as HTMLHeadingElement,
      playerCardStats: document.getElementById('playerCardStats') as HTMLDivElement,
      closePlayerCard: document.getElementById('closePlayerCard') as HTMLButtonElement
    };
  }

  private setupListeners(): void {
    const {
      newSaveBtn,
      createSaveBtn,
      cancelSaveBtn,
      saveTitle,
      tabSettings,
      themeToggle,
      collapseButton
    } = this.elements;

    // Set up sidebar collapse functionality
    if (collapseButton) {
      collapseButton.addEventListener('click', () => this.toggleSidebar());
    }

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
    if (tabSettings) {
      tabSettings.addEventListener('click', () => this.showSettingsModal());
    }
    
    const { closeSettingsBtn } = this.elements;
    if (closeSettingsBtn) {
      closeSettingsBtn.addEventListener('click', () => this.hideSettingsModal());
    }
    if (themeToggle) {
      themeToggle.addEventListener('click', () => this.toggleTheme());
    }
    
    if (saveTitle) {
      saveTitle.addEventListener('change', () => this.handleSaveChanges());
    }
    
    if (this.elements.closePlayerCard) {
      this.elements.closePlayerCard.addEventListener('click', () => this.hidePlayerCard());
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

  private showSettingsModal(): void {
    const { settingsModal } = this.elements;
    if (settingsModal) {
      settingsModal.classList.add('show');
    }
  }

  private hideSettingsModal(): void {
    const { settingsModal } = this.elements;
    if (settingsModal) {
      settingsModal.classList.remove('show');
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
      info.addEventListener('click', () => this.loadSave(save));
      
      const leagueInfo = document.createElement('div');
      leagueInfo.className = 'league-info';
      leagueInfo.textContent = `League ID: ${save.leagueId} (${save.year})`;
      info.appendChild(leagueInfo);

      const date = document.createElement('small');
      date.style.color = '#666';
      date.style.fontSize = '0.8em';
      date.textContent = `Updated: ${new Date(save.updated).toLocaleDateString()}`;
      info.appendChild(date);

      const menuContainer = document.createElement('div');
      menuContainer.className = 'menu-container';

      const menuButton = document.createElement('button');
      menuButton.className = 'menu-button';
      menuButton.innerHTML = '⋮';
      menuButton.addEventListener('click', (e) => {
        e.stopPropagation();
        this.toggleMenu(save.id);
      });

      const menuDropdown = document.createElement('div');
      menuDropdown.className = 'menu-dropdown';
      menuDropdown.id = `menu-${save.id}`;

      const deleteBtn = document.createElement('button');
      deleteBtn.className = 'menu-item delete';
      deleteBtn.textContent = 'Delete';
      deleteBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        this.handleDelete(save);
      });

      menuDropdown.appendChild(deleteBtn);
      menuContainer.appendChild(menuButton);
      menuContainer.appendChild(menuDropdown);

      item.appendChild(info);
      item.appendChild(menuContainer);
      saveList.appendChild(item);
    });
  }

  private async loadSave(save: Save): Promise<void> {
    const { leagueIdInput, yearInput, s2Input, swidInput } = this.elements;
    
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
    
    let activeSaveSet = false;
    
    try {
      // Notify backend of active save
      const response = await fetch(`${this.API_URL}/set-active-save`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          saveId: save.id,
          leagueId: save.leagueId,
          year: save.year,
          s2: save.s2,
          swid: save.swid,
          teamId: save.teamId
        })
      });

      const data: { success?: boolean; error?: string } = await response.json();

      if (!response.ok || !data.success) {
        throw new Error(data.error || 'Failed to update active save in backend');
      }

      activeSaveSet = true;
    } catch (error) {
      console.error('Error updating active save in backend:', error);
      this.resetLeagueData();
    }

    if (activeSaveSet) {
      await this.refreshLeagueData();
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

  private toggleMenu(saveId: string): void {
    const allMenus = document.querySelectorAll('.menu-dropdown');
    allMenus.forEach(menu => {
      if (menu.id !== `menu-${saveId}`) {
        menu.classList.remove('show');
      }
    });

    const menu = document.getElementById(`menu-${saveId}`);
    if (menu) {
      menu.classList.toggle('show');
      
      // Close menu when clicking outside
      const handleClickOutside = (e: MouseEvent) => {
        const target = e.target as HTMLElement;
        if (!target.closest('.menu-container')) {
          menu.classList.remove('show');
          document.removeEventListener('click', handleClickOutside);
        }
      };
      
      if (menu.classList.contains('show')) {
        setTimeout(() => {
          document.addEventListener('click', handleClickOutside);
        }, 0);
      }
    }
  }

  private async handleDelete(save: Save): Promise<void> {
    if (!confirm('Delete this league configuration?')) return;

    this.storage.deleteSave(save.id);
    if (this.currentSave?.id === save.id) {
      this.hideEditor();
      
      try {
        // Clear the active save in the backend
        await fetch(`${this.API_URL}/set-active-save`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(null)
        });
      } catch (error) {
        console.error('Error clearing active save in backend:', error);
      }
      
      this.currentSave = null;
      this.resetLeagueData();
    }
    this.refreshSavesList();
  }

  private loadSettings(): void {
    const savedSettings = localStorage.getItem('espn-helper-settings');
    if (savedSettings) {
      this.settings = JSON.parse(savedSettings);
      this.applyTheme();
    }
  }

  private saveSettings(): void {
    localStorage.setItem('espn-helper-settings', JSON.stringify(this.settings));
  }

  private toggleTheme(): void {
    this.settings.theme = this.settings.theme === 'light' ? 'dark' : 'light';
    this.saveSettings();
    this.applyTheme();
  }

  private applyTheme(): void {
    document.body.classList.remove('theme-light', 'theme-dark');
    document.body.classList.add(`theme-${this.settings.theme}`);
  }

  private resetLeagueData(): void {
    if (this.elements.teamRoster) {
      this.elements.teamRoster.textContent = 'Select a save to load your roster.';
    }
    this.renderFreeAgentsMessage('Select a save to load the best available players.');
    this.hidePlayerCard();
  }

  private async refreshLeagueData(): Promise<void> {
    if (!this.currentSave) {
      this.resetLeagueData();
      return;
    }

    await Promise.all([this.loadTeamRoster(), this.loadTopFreeAgents()]);
  }

  private renderFreeAgentsMessage(message: string): void {
    const target = this.elements.topFreeAgents;
    if (!target) return;
    target.innerHTML = '';
    const placeholder = document.createElement('div');
    placeholder.className = 'free-agents-placeholder';
    placeholder.textContent = message;
    target.appendChild(placeholder);
  }

  private async loadTeamRoster(): Promise<void> {
    const target = this.elements.teamRoster;
    if (!target || !this.currentSave) return;

    target.textContent = 'Loading roster...';

    try {
      const response = await fetch(`${this.API_URL}/get-team-roster`);
      const data: { roster?: string[]; error?: string } = await response.json();

      if (!response.ok || !Array.isArray(data.roster)) {
        throw new Error(data.error || 'Invalid roster response');
      }

      if (!data.roster.length) {
        target.textContent = 'No players found on your roster.';
        return;
      }

      target.textContent = '';
      const column = document.createElement('div');
      column.className = 'roster-column';

      const title = document.createElement('h4');
      title.textContent = 'Active Roster';
      column.appendChild(title);

      const list = document.createElement('ul');
      data.roster.forEach(player => {
        const item = document.createElement('li');
        const link = document.createElement('a');
        link.textContent = player;
        link.href = '#';
        link.className = 'player-link';
        link.addEventListener('click', (e) => {
          e.preventDefault();
          this.showPlayerCard(player);
        });
        item.appendChild(link);
        list.appendChild(item);
      });

      column.appendChild(list);
      target.appendChild(column);
    } catch (error) {
      console.error('Error fetching team roster:', error);
      target.textContent = 'Unable to load roster.';
    }
  }

  private async loadTopFreeAgents(): Promise<void> {
    const target = this.elements.topFreeAgents;
    if (!target || !this.currentSave) return;

    this.renderFreeAgentsMessage('Loading free agents...');

    try {
      const response = await fetch(`${this.API_URL}/get-top-free-agents`);
      const data: { top_free_agents?: Record<string, string[]>; error?: string } = await response.json();

      if (!response.ok || !data.top_free_agents) {
        throw new Error(data.error || 'Invalid free agent response');
      }

      target.innerHTML = '';
      const order = ['OVERALL', 'POINT GUARD', 'SHOOTING GUARD', 'SMALL FORWARD', 'POWER FORWARD', 'CENTER'];

      order.forEach((group) => {
        const players = data.top_free_agents?.[group] ?? [];
        const column = document.createElement('div');
        column.className = 'free-agents-column';

        const title = document.createElement('h4');
        title.textContent = group;
        column.appendChild(title);

        const list = document.createElement('ul');
        if (Array.isArray(players) && players.length) {
          players.forEach((player) => {
            const item = document.createElement('li');
            const link = document.createElement('a');
            link.textContent = player;
            link.href = '#';
            link.className = 'player-link';
            link.addEventListener('click', (e) => {
              e.preventDefault();
              this.showPlayerCard(player);
            });
            item.appendChild(link);
            list.appendChild(item);
          });
        } else {
          const item = document.createElement('li');
          item.textContent = 'None available';
          list.appendChild(item);
        }

        column.appendChild(list);
        target.appendChild(column);
      });
    } catch (error) {
      console.error('Error fetching free agents:', error);
      this.renderFreeAgentsMessage('Unable to load free agents.');
    }
  }

  private showPlayerCard(playerName: string): void {
    const { playerCard, playerCardName, playerCardStats } = this.elements;
    if (!playerCard || !playerCardName || !playerCardStats) return;

    playerCardName.textContent = playerName;
    playerCardStats.textContent = 'Loading stats...';
    playerCard.style.display = 'block';
    
    this.loadPlayerStats(playerName);
  }

  private hidePlayerCard(): void {
    const { playerCard } = this.elements;
    if (playerCard) {
      playerCard.style.display = 'none';
    }
  }

  private async loadPlayerStats(playerName: string): Promise<void> {
    const { playerCardStats } = this.elements;
    if (!playerCardStats) return;

    try {
      const response = await fetch(`${this.API_URL}/get-player-stats?name=${encodeURIComponent(playerName)}`);
      const data: { stats?: Record<string, any>; error?: string } = await response.json();

      if (!response.ok) {
        const errorMsg = data.error || 'Failed to load player stats';
        console.error('API Error:', errorMsg);
        playerCardStats.textContent = errorMsg;
        return;
      }

      if (!data.stats) {
        throw new Error(data.error || 'No stats data returned');
      }

      // Remove NAME from stats display
      const stats = { ...data.stats };
      delete stats['NAME'];
      delete stats['[NAME]'];

      // Format stats for display
      playerCardStats.innerHTML = '';
      const statsList = document.createElement('dl');
      statsList.className = 'player-stats-list';

      Object.entries(stats).forEach(([key, value]) => {
        const dt = document.createElement('dt');
        dt.textContent = key.replace(/[\[\]]/g, '');
        const dd = document.createElement('dd');
        dd.textContent = typeof value === 'number' ? value.toFixed(2) : String(value);
        statsList.appendChild(dt);
        statsList.appendChild(dd);
      });

      playerCardStats.appendChild(statsList);
    } catch (error) {
      console.error('Error fetching player stats:', error);
      playerCardStats.textContent = 'Unable to load player stats.';
    }
  }

}