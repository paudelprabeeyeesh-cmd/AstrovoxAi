// Frontend Platform - Group 8: Resizable split-pane and workspace layouts
const SplitPane = {
  _instances = new Map(),

  create(container, options = {}) {
    const {
      direction = 'horizontal',
      initialSizes = [50, 50],
      minSizes = [20, 20],
      maxSizes = [80, 80],
      resizable = true,
      gutterSize = 6,
    } = options;

    if (!container) return null;

    container.classList.add(`split-pane split-pane-${direction}`);

    const panels = Array.from(container.children);
    if (panels.length < 2) return null;

    const id = 'split-' + Date.now();
    const instance = {
      id,
      container,
      direction,
      panels,
      sizes: [...initialSizes],
      minSizes,
      maxSizes,
      gutterSize,
      isDragging: false,
      startPos: 0,
      startSizes: [],
    };

    panels.forEach((panel, idx) => {
      panel.classList.add('split-pane-panel');
      panel.style.flex = `0 0 ${initialSizes[idx]}%`;
    });

    if (resizable && panels.length === 2) {
      this._createGutter(instance);
    }

    this._instances.set(id, instance);
    return instance;
  },

  _createGutter(instance) {
    const gutter = document.createElement('div');
    gutter.className = `split-pane-gutter split-pane-gutter-${instance.direction}`;
    gutter.setAttribute('role', 'separator');
    gutter.setAttribute('aria-orientation', instance.direction === 'horizontal' ? 'vertical' : 'horizontal');
    gutter.setAttribute('tabindex', '0');
    gutter.setAttribute('aria-valuenow', '50');
    gutter.setAttribute('aria-valuemin', String(instance.minSizes[0]));
    gutter.setAttribute('aria-valuemax', String(instance.maxSizes[0]));

    const updateSize = (clientPos) => {
      if (!instance.isDragging) return;

      const rect = instance.container.getBoundingClientRect();
      const isHorizontal = instance.direction === 'horizontal';
      const pos = isHorizontal ? clientPos - rect.left : clientPos - rect.top;
      const totalSize = isHorizontal ? rect.width : rect.height;

      const percentage = Math.max(instance.minSizes[0], Math.min(instance.maxSizes[0], (pos / totalSize) * 100));
      const otherPercentage = 100 - percentage;

      instance.sizes = [percentage, otherPercentage];
      instance.panels[0].style.flex = `0 0 ${percentage}%`;
      instance.panels[1].style.flex = `0 0 ${otherPercentage}%`;
      gutter.setAttribute('aria-valuenow', String(Math.round(percentage)));
    };

    gutter.addEventListener('mousedown', (e) => {
      e.preventDefault();
      instance.isDragging = true;
      instance.startPos = instance.direction === 'horizontal' ? e.clientX : e.clientY;
      instance.startSizes = [...instance.sizes];

      document.addEventListener('mousemove', onMove);
      document.addEventListener('mouseup', onUp);
    });

    gutter.addEventListener('touchstart', (e) => {
      instance.isDragging = true;
      instance.startPos = instance.direction === 'horizontal' ? e.touches[0].clientX : e.touches[0].clientY;
      instance.startSizes = [...instance.sizes];

      document.addEventListener('touchmove', onMove, { passive: false });
      document.addEventListener('touchend', onUp);
    }, { passive: true });

    const onMove = (e) => {
      if (!instance.isDragging) return;
      const clientPos = instance.direction === 'horizontal' ? e.clientX : e.clientY;
      updateSize(clientPos);
    };

    const onUp = () => {
      instance.isDragging = false;
      document.removeEventListener('mousemove', onMove);
      document.removeEventListener('mouseup', onUp);
      document.removeEventListener('touchmove', onMove);
      document.removeEventListener('touchend', onUp);
    };

    gutter.addEventListener('keydown', (e) => {
      const step = e.shiftKey ? 5 : 1;
      let newSize = instance.sizes[0];

      if (instance.direction === 'horizontal') {
        if (e.key === 'ArrowLeft') newSize = Math.max(instance.minSizes[0], newSize - step);
        if (e.key === 'ArrowRight') newSize = Math.min(instance.maxSizes[0], newSize + step);
      } else {
        if (e.key === 'ArrowUp') newSize = Math.max(instance.minSizes[0], newSize - step);
        if (e.key === 'ArrowDown') newSize = Math.min(instance.maxSizes[0], newSize + step);
      }

      instance.sizes = [newSize, 100 - newSize];
      instance.panels[0].style.flex = `0 0 ${newSize}%`;
      instance.panels[1].style.flex = `0 0 ${100 - newSize}%`;
      gutter.setAttribute('aria-valuenow', String(Math.round(newSize)));
    });

    instance.container.insertBefore(gutter, instance.panels[1]);
  },

  getInstance(id) {
    return this._instances.get(id);
  },

  resize(id, sizes) {
    const instance = this._instances.get(id);
    if (!instance) return;

    instance.sizes = [...sizes];
    instance.panels.forEach((panel, idx) => {
      panel.style.flex = `0 0 ${sizes[idx]}%`;
    });
  },
};

window.SplitPane = SplitPane;
