// ===== УПРАВЛЕНИЕ ТЕМОЙ =====

const ThemeManager = {
  STORAGE_KEY: 'app-theme',
  
  init() {
    this.loadTheme();
    this.addThemeToggleListener();
  },
  
  loadTheme() {
    const savedTheme = localStorage.getItem(this.STORAGE_KEY);
    const theme = savedTheme || 'light';
    this.setTheme(theme);
  },
  
  setTheme(theme) {
    if (theme === 'dark') {
      document.documentElement.setAttribute('data-theme', 'dark');
    } else {
      document.documentElement.removeAttribute('data-theme');
    }
    localStorage.setItem(this.STORAGE_KEY, theme);
  },
  
  toggleTheme() {
    const currentTheme = document.documentElement.getAttribute('data-theme');
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
    this.setTheme(newTheme);
    return newTheme;
  },
  
  getCurrentTheme() {
    return document.documentElement.getAttribute('data-theme') || 'light';
  },
  
  addThemeToggleListener() {
    // Создаём кнопку переключения темы
    const toggleButton = document.createElement('button');
    toggleButton.className = 'theme-toggle-btn';
    toggleButton.setAttribute('type', 'button');
    toggleButton.setAttribute('title', 'Переключить тему');
    toggleButton.innerHTML = this.getThemeIcon();
    
    // Добавляем стили для кнопки
    this.addToggleButtonStyles();
    
    // Добавляем кнопку в navbar
    const navbar = document.querySelector('.navbar');
    if (navbar) {
      navbar.appendChild(toggleButton);
    }
    
    // Обработчик клика
    toggleButton.addEventListener('click', () => {
      const newTheme = this.toggleTheme();
      toggleButton.innerHTML = this.getThemeIcon();
      
      // Анимация кнопки
      toggleButton.style.transform = 'rotate(360deg) scale(1.2)';
      setTimeout(() => {
        toggleButton.style.transform = 'rotate(0deg) scale(1)';
      }, 300);
    });
  },
  
  getThemeIcon() {
    const currentTheme = this.getCurrentTheme();
    if (currentTheme === 'dark') {
      // Иконка солнца (для тёмной темы)
      return `
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <circle cx="12" cy="12" r="5"></circle>
          <line x1="12" y1="1" x2="12" y2="3"></line>
          <line x1="12" y1="21" x2="12" y2="23"></line>
          <line x1="4.22" y1="4.22" x2="5.64" y2="5.64"></line>
          <line x1="18.36" y1="18.36" x2="19.78" y2="19.78"></line>
          <line x1="1" y1="12" x2="3" y2="12"></line>
          <line x1="21" y1="12" x2="23" y2="12"></line>
          <line x1="4.22" y1="19.78" x2="5.64" y2="18.36"></line>
          <line x1="18.36" y1="5.64" x2="19.78" y2="4.22"></line>
        </svg>
      `;
    } else {
      // Иконка луны (для светлой темы)
      return `
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path>
        </svg>
      `;
    }
  },
  
  addToggleButtonStyles() {
    const styles = document.createElement('style');
    styles.textContent = `
      .theme-toggle-btn {
        position: fixed;
        top: 20px;
        right: 20px;
        width: 44px;
        height: 44px;
        border-radius: 50%;
        border: 1px solid var(--line);
        background: var(--panel);
        color: var(--text);
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
        transition: all 0.3s ease;
        z-index: 100;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
      }
      
      .theme-toggle-btn:hover {
        transform: scale(1.1);
        box-shadow: 0 4px 12px rgba(108, 99, 255, 0.3);
        border-color: var(--purple);
        color: var(--purple);
      }
      
      [data-theme="dark"] .theme-toggle-btn {
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
      }
      
      @media (max-width: 980px) {
        .theme-toggle-btn {
          top: 10px;
          right: 10px;
          width: 40px;
          height: 40px;
        }
      }
    `;
    document.head.appendChild(styles);
  }
};

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', () => {
  ThemeManager.init();
});