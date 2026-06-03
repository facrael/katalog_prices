document.addEventListener('DOMContentLoaded', () => {
  // Check if data is available
  const rawData = window.partsData || [];
  
  // Categorize items
  const categorizedData = rawData.map(item => {
    let category = 'Прочее';
    const nameLower = item.name.toLowerCase();
    
    if (nameLower.includes('аккумулятор') || nameLower.includes('акб')) {
      category = 'АКБ';
    } else if (nameLower.includes('амортизатор')) {
      category = 'Амортизаторы';
    } else if (nameLower.includes('болт') || nameLower.includes('гайка') || nameLower.includes('шайба') || nameLower.includes('винт') || nameLower.includes('шпилька') || nameLower.includes('клемма')) {
      category = 'Метизы/Клеммы';
    } else if (nameLower.includes('датчик')) {
      category = 'Датчики';
    } else if (nameLower.includes('кран') || nameLower.includes('клапан') || nameLower.includes('диафрагма')) {
      category = 'Тормозная/Пневмо';
    } else if (nameLower.includes('зеркало')) {
      category = 'Зеркала';
    } else if (nameLower.includes('генератор') || nameLower.includes('стартер') || nameLower.includes('жгут') || nameLower.includes('провод') || nameLower.includes('выключатель') || nameLower.includes('фара') || nameLower.includes('ламп')) {
      category = 'Электрика';
    } else if (nameLower.includes('фильтр') || nameLower.includes('ремень') || nameLower.includes('прокладка') || nameLower.includes('сальник') || nameLower.includes('кольцо')) {
      category = 'Расходники';
    }
    
    return { ...item, category };
  });

  // State Variables
  let filteredData = [...categorizedData];
  let currentPage = 1;
  const itemsPerPage = 25;
  let currentCategory = 'Все';
  let searchQuery = '';
  let currentSort = 'id-asc';

  // DOM Elements
  const searchInput = document.getElementById('search-input');
  const categoryTagsContainer = document.getElementById('category-tags');
  const sortSelect = document.getElementById('sort-select');
  const desktopTableBody = document.getElementById('desktop-table-body');
  const mobileCardsContainer = document.getElementById('mobile-cards-container');
  
  // Stat Elements
  const statTotal = document.getElementById('stat-total');
  const statWithPrice = document.getElementById('stat-with-price');
  const statTotalPrice = document.getElementById('stat-total-price');
  const statCategories = document.getElementById('stat-categories');

  // Pagination Elements
  const paginationInfo = document.getElementById('pagination-info');
  const prevPageBtn = document.getElementById('prev-page-btn');
  const nextPageBtn = document.getElementById('next-page-btn');
  
  // Theme Elements
  const themeToggleBtn = document.getElementById('theme-toggle-btn');
  const themeIcon = themeToggleBtn.querySelector('i') || themeToggleBtn;

  // Initialize UI
  setupTheme();
  calculateStats();
  renderCategoryTags();
  applyFilters();

  // Theme Setup
  function setupTheme() {
    const savedTheme = localStorage.getItem('theme') || 'dark';
    document.documentElement.setAttribute('data-theme', savedTheme);
    updateThemeIcon(savedTheme);
    
    themeToggleBtn.addEventListener('click', () => {
      const currentTheme = document.documentElement.getAttribute('data-theme');
      const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
      document.documentElement.setAttribute('data-theme', newTheme);
      localStorage.setItem('theme', newTheme);
      updateThemeIcon(newTheme);
    });
  }

  function updateThemeIcon(theme) {
    if (theme === 'dark') {
      themeIcon.innerHTML = '☀️';
      themeToggleBtn.title = 'Переключить на светлую тему';
    } else {
      themeIcon.innerHTML = '🌙';
      themeToggleBtn.title = 'Переключить на темную тему';
    }
  }

  // Calculate Dashboard Stats
  function calculateStats() {
    const total = categorizedData.length;
    const withPriceItems = categorizedData.filter(item => item.price !== null && item.price > 0);
    const withPrice = withPriceItems.length;
    const totalPrice = withPriceItems.reduce((sum, item) => sum + item.price, 0);
    
    // Count unique categories
    const categoriesSet = new Set(categorizedData.map(item => item.category));
    
    // Animate stats counter
    animateValue(statTotal, 0, total, 1000);
    animateValue(statWithPrice, 0, withPrice, 1000);
    animateValue(statTotalPrice, 0, totalPrice, 1000, true);
    animateValue(statCategories, 0, categoriesSet.size, 1000);
  }

  function animateValue(obj, start, end, duration, isCurrency = false) {
    let startTimestamp = null;
    const step = (timestamp) => {
      if (!startTimestamp) startTimestamp = timestamp;
      const progress = Math.min((timestamp - startTimestamp) / duration, 1);
      const currentVal = Math.floor(progress * (end - start) + start);
      
      if (isCurrency) {
        obj.textContent = currentVal.toLocaleString('ru-RU') + ' ₽';
      } else {
        obj.textContent = currentVal.toLocaleString('ru-RU');
      }
      
      if (progress < 1) {
        window.requestAnimationFrame(step);
      }
    };
    window.requestAnimationFrame(step);
  }

  // Render Category Filter Tags
  function renderCategoryTags() {
    const categories = ['Все', ...new Set(categorizedData.map(item => item.category))];
    categoryTagsContainer.innerHTML = '';
    
    categories.forEach(cat => {
      const tag = document.createElement('span');
      tag.className = `category-tag ${cat === currentCategory ? 'active' : ''}`;
      tag.textContent = cat;
      
      // Count items in category
      const count = cat === 'Все' 
        ? categorizedData.length 
        : categorizedData.filter(item => item.category === cat).length;
      
      tag.textContent += ` (${count})`;
      
      tag.addEventListener('click', () => {
        document.querySelectorAll('.category-tag').forEach(t => t.classList.remove('active'));
        tag.classList.add('active');
        currentCategory = cat;
        currentPage = 1;
        applyFilters();
      });
      
      categoryTagsContainer.appendChild(tag);
    });
  }

  // Apply Search, Category Filters, and Sort
  function applyFilters() {
    // 1. Filter by Category
    let result = categorizedData;
    if (currentCategory !== 'Все') {
      result = result.filter(item => item.category === currentCategory);
    }
    
    // 2. Filter by Search Query
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      result = result.filter(item => 
        item.name.toLowerCase().includes(query) || 
        item.catalog.toLowerCase().includes(query)
      );
    }
    
    // 3. Apply Sorting
    result.sort((a, b) => {
      if (currentSort === 'id-asc') {
        return a.id - b.id;
      } else if (currentSort === 'id-desc') {
        return b.id - a.id;
      } else if (currentSort === 'name-asc') {
        return a.name.localeCompare(b.name, 'ru');
      } else if (currentSort === 'name-desc') {
        return b.name.localeCompare(a.name, 'ru');
      } else if (currentSort === 'price-asc') {
        const pA = a.price === null ? Infinity : a.price;
        const pB = b.price === null ? Infinity : b.price;
        return pA - pB;
      } else if (currentSort === 'price-desc') {
        const pA = a.price === null ? -1 : a.price;
        const pB = b.price === null ? -1 : b.price;
        return pB - pA;
      }
      return 0;
    });
    
    filteredData = result;
    renderData();
  }

  // Render Table & Mobile Cards
  function renderData() {
    const totalItems = filteredData.length;
    const totalPages = Math.ceil(totalItems / itemsPerPage) || 1;
    
    // Clamp current page
    if (currentPage > totalPages) currentPage = totalPages;
    if (currentPage < 1) currentPage = 1;
    
    const startIndex = (currentPage - 1) * itemsPerPage;
    const endIndex = Math.min(startIndex + itemsPerPage, totalItems);
    const paginatedItems = filteredData.slice(startIndex, endIndex);

    // Update pagination UI
    prevPageBtn.disabled = currentPage === 1;
    nextPageBtn.disabled = currentPage === totalPages;
    
    if (totalItems === 0) {
      paginationInfo.innerHTML = 'Показано <span>0</span> из <span>0</span> записей';
      renderEmptyState();
      return;
    }
    
    paginationInfo.innerHTML = `Показано <span>${startIndex + 1} - ${endIndex}</span> из <span>${totalItems}</span> записей`;
    
    // Render Desktop Table
    desktopTableBody.innerHTML = '';
    paginatedItems.forEach(item => {
      const tr = document.createElement('tr');
      
      const priceHtml = item.price !== null 
        ? `<span class="part-price-badge has-price">${item.price.toLocaleString('ru-RU')} ₽</span>`
        : `<span class="part-price-badge no-price">нет цены</span>`;
        
      const linkClass = item.price !== null ? 'buy-action-btn' : 'buy-action-btn search-fallback';
      const linkText = item.price !== null ? '🛒 Купить' : '🔍 Найти';
      
      tr.innerHTML = `
        <td class="part-index">${item.id}</td>
        <td class="part-name">
          ${item.name}
          <div style="font-size: 0.75rem; color: var(--text-muted); margin-top: 0.25rem;">
            Категория: ${item.category}
          </div>
        </td>
        <td><span class="part-catalog">${item.catalog || '—'}</span></td>
        <td class="part-unit">${item.unit || 'шт.'}</td>
        <td>${priceHtml}</td>
        <td>
          <a href="${item.link}" target="_blank" class="${linkClass}">
            ${linkText}
          </a>
        </td>
      `;
      desktopTableBody.appendChild(tr);
    });
    
    // Render Mobile Cards
    mobileCardsContainer.innerHTML = '';
    paginatedItems.forEach(item => {
      const card = document.createElement('div');
      card.className = 'mobile-card';
      
      const priceHtml = item.price !== null 
        ? `<span class="part-price-badge has-price">${item.price.toLocaleString('ru-RU')} ₽</span>`
        : `<span class="part-price-badge no-price">нет цены</span>`;
        
      const linkClass = item.price !== null ? 'buy-action-btn' : 'buy-action-btn search-fallback';
      const linkText = item.price !== null ? '🛒 Купить' : '🔍 Найти';
      
      card.innerHTML = `
        <div class="mobile-card-header">
          <div>
            <span class="mobile-card-index">№ ${item.id}</span>
            <h3 class="mobile-card-title">${item.name}</h3>
          </div>
        </div>
        <div class="mobile-card-details">
          <div class="detail-row">
            <span>Артикул:</span>
            <span><span class="part-catalog">${item.catalog || '—'}</span></span>
          </div>
          <div class="detail-row">
            <span>Ед. изм:</span>
            <span>${item.unit || 'шт.'}</span>
          </div>
          <div class="detail-row">
            <span>Категория:</span>
            <span>${item.category}</span>
          </div>
        </div>
        <div class="mobile-card-footer">
          ${priceHtml}
          <a href="${item.link}" target="_blank" class="${linkClass}">
            ${linkText}
          </a>
        </div>
      `;
      mobileCardsContainer.appendChild(card);
    });
  }

  function renderEmptyState() {
    const emptyHtml = `
      <div class="empty-state">
        <div class="empty-state-icon">🔍</div>
        <h3 class="empty-state-title">Ничего не найдено</h3>
        <p class="empty-state-desc">Попробуйте изменить поисковый запрос или выбрать другую категорию.</p>
      </div>
    `;
    desktopTableBody.innerHTML = `<tr><td colspan="6">${emptyHtml}</td></tr>`;
    mobileCardsContainer.innerHTML = emptyHtml;
  }

  // Event Listeners
  searchInput.addEventListener('input', (e) => {
    searchQuery = e.target.value;
    currentPage = 1;
    applyFilters();
  });

  sortSelect.addEventListener('change', (e) => {
    currentSort = e.target.value;
    applyFilters();
  });

  prevPageBtn.addEventListener('click', () => {
    if (currentPage > 1) {
      currentPage--;
      renderData();
      window.scrollTo({ top: document.querySelector('.control-panel').offsetTop - 20, behavior: 'smooth' });
    }
  });

  nextPageBtn.addEventListener('click', () => {
    const totalPages = Math.ceil(filteredData.length / itemsPerPage);
    if (currentPage < totalPages) {
      currentPage++;
      renderData();
      window.scrollTo({ top: document.querySelector('.control-panel').offsetTop - 20, behavior: 'smooth' });
    }
  });
});
