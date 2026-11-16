<script setup lang="ts">
import { inject, ref, computed } from 'vue'
import type { ViewState } from '../App.vue'
import KitchenVisualizer from './KitchenVisualizer.vue'
import { kitchenStore } from '../store'

const navigateTo = inject<(view: ViewState) => void>('navigateTo', () => {})

const beforeStates = {
  1: { contrast: 0, color: '#3b5a51' },
  2: { contrast: 0, color: '#94c0b4' },
  3: { contrast: 0, color: '#ff5555' },
  4: { contrast: 0, color: '#4a6b8c' },
  5: { contrast: 0, color: '#d9a05b' },
  6: { contrast: 0, color: '#7b9eb0' }
}

const afterStates = computed(() => kitchenStore.savedStates)

const layoutName = ref('')
const saveLayout = () => {
  if (!layoutName.value.trim()) return
  const newLayout = {
    id: Date.now().toString(),
    name: layoutName.value.trim(),
    timestamp: new Date().toLocaleDateString(),
    room: 'kitchen' as const,
    states: JSON.parse(JSON.stringify(kitchenStore.savedStates))
  }
  kitchenStore.savedLayouts.push(newLayout)
  layoutName.value = ''
  navigateTo('saved-layouts')
}
</script>

<template>
  <div class="kitchen-comparison-page">
    <header class="page-header">
      <div class="header-content">
        <div class="title-container">
          <span class="pill-badge">Before / After</span>
          <h1 class="page-title">See what changed</h1>
          <p class="page-subtitle">
            Show specific environmental differences instead of an arbitrary cognitive accessibility score.
          </p>
        </div>
        <div class="actions-container">
          <button class="back-btn" @click="navigateTo('kitchen-task')">← Keep Editing</button>
          <button class="back-btn" @click="navigateTo('bathroom-task')">Bathroom Guide</button>
          <button class="back-btn" @click="navigateTo('saved-layouts')">Saved Layouts</button>
        </div>
      </div>
    </header>

    <div class="split-view-container">
      <div class="view-panel">
        <div class="panel-label">Before</div>
        <KitchenVisualizer :itemStates="beforeStates" />
      </div>
      
      <div class="view-divider">
        <span class="arrow-icon">→</span>
      </div>
      
      <div class="view-panel">
        <div class="panel-label">After</div>
        <KitchenVisualizer :itemStates="afterStates" />
        
        <div class="save-layout-form">
          <label for="kitchen-layout-name" class="visually-hidden">Name this layout</label>
          <input 
            id="kitchen-layout-name"
            v-model="layoutName" 
            type="text" 
            placeholder="Name this layout (e.g. Max Contrast)" 
            @keyup.enter="saveLayout" 
            aria-label="Name this layout"
          />
          <button class="save-btn" @click="saveLayout" :disabled="!layoutName.trim()">Save Layout</button>
        </div>
      </div>
    </div>

  </div>
</template>

<style scoped>
.kitchen-comparison-page {
  width: 100%;
  max-width: 100%;
  margin: 0;
  padding: 1rem 2rem;
  font-family: inherit;
  box-sizing: border-box;
}

.page-header {
  margin-bottom: 2rem;
}

.header-content {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}

.title-container {
  max-width: 70%;
}

.pill-badge {
  display: inline-block;
  font-size: 0.75rem;
  font-weight: 700;
  text-transform: uppercase;
  color: var(--color-primary);
  letter-spacing: 0.05em;
  margin-bottom: 0.75rem;
}

.page-title {
  font-size: 2rem;
  font-weight: 800;
  color: var(--color-text-main);
  margin-bottom: 0.5rem;
}

.page-subtitle {
  font-size: 1.1rem;
  color: var(--color-text-muted);
  line-height: 1.5;
}

.actions-container {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 0.75rem;
}

.back-btn {
  background: white;
  border: 1px solid var(--color-border);
  border-radius: 20px;
  padding: 0.5rem 1.5rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
  box-shadow: 0 1px 3px rgba(0,0,0,0.05);
}

.back-btn:hover {
  background: var(--color-bg-sage);
  border-color: var(--color-primary);
}

.split-view-container {
  display: flex;
  align-items: stretch;
  justify-content: space-between;
  gap: 1rem;
  margin-top: 2rem;
}

.view-panel {
  flex: 1;
  background: white;
  border: 1px solid var(--color-border);
  border-radius: 12px;
  padding: 1.5rem;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.02);
  display: flex;
  flex-direction: column;
}

.panel-label {
  font-size: 0.75rem;
  font-weight: 700;
  text-transform: uppercase;
  color: var(--color-primary);
  letter-spacing: 0.05em;
  margin-bottom: 1rem;
}

.view-divider {
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--color-primary);
  font-weight: bold;
  font-size: 1.5rem;
}

.stats-container {
  display: flex;
  gap: 1.5rem;
  margin-top: 1.5rem;
}

.stat-card {
  flex: 1;
  background: white;
  border: 1px solid var(--color-border);
  border-radius: 12px;
  padding: 1.5rem;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.02);
}

.stat-value {
  font-size: 1.75rem;
  font-weight: 800;
  color: var(--color-text-main);
  margin-bottom: 0.5rem;
}

.stat-label {
  font-size: 0.9rem;
  color: var(--color-text-muted);
}

.action-cards-container {
  display: flex;
  gap: 1.5rem;
  margin-top: 1.5rem;
}

.action-card {
  flex: 1;
  background: white;
  border: 1px solid var(--color-border);
  border-radius: 12px;
  padding: 1.5rem;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.02);
  display: flex;
  flex-direction: column;
}

.action-card-label {
  font-size: 0.75rem;
  font-weight: 700;
  text-transform: uppercase;
  color: var(--color-primary);
  letter-spacing: 0.05em;
  margin-bottom: 0.75rem;
}

.action-card-title {
  font-size: 1.25rem;
  font-weight: 800;
  color: var(--color-text-main);
  margin-bottom: 0.5rem;
}

.action-card-text {
  font-size: 0.95rem;
  color: var(--color-text-muted);
  line-height: 1.5;
  margin-bottom: 1.5rem;
  flex-grow: 1;
}

.btn-outline {
  background: white;
  color: var(--color-text-main);
  border: 1px solid var(--color-border);
  border-radius: 8px;
  padding: 0.75rem 1rem;
  font-weight: 600;
  cursor: pointer;
  align-self: flex-start;
  transition: all 0.2s;
}

.btn-outline:hover {
  background: var(--color-bg-sage);
}

.btn-primary-small {
  background: var(--color-primary);
  color: white;
  border: none;
  border-radius: 8px;
  padding: 0.75rem 1rem;
  font-weight: 600;
  cursor: pointer;
  align-self: flex-start;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.btn-primary-small:hover {
  background: #253a33;
}

/* Save Layout Form */
.save-layout-form {
  display: flex;
  gap: 0.75rem;
  padding: 1.5rem;
  border-top: 1px solid var(--color-border);
  background: var(--color-bg-sage);
  border-radius: 0 0 12px 12px;
  margin: auto -1.5rem -1.5rem -1.5rem;
}

.save-layout-form input {
  flex: 1;
  padding: 0.75rem 1rem;
  border: 1px solid var(--color-border);
  border-radius: 8px;
  font-size: 0.95rem;
  outline: none;
  font-family: inherit;
  background: white;
  transition: all 0.2s ease;
  color: var(--color-text-main);
}

.save-layout-form input:focus {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px rgba(18, 75, 66, 0.1);
}

.save-layout-form input::placeholder {
  color: #94a3b8;
}

.save-btn {
  background: var(--color-primary);
  color: white;
  border: none;
  border-radius: 8px;
  padding: 0.75rem 1.5rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
  white-space: nowrap;
}

.save-btn:disabled {
  background: #cbd5e1;
  color: #94a3b8;
  cursor: not-allowed;
}

.save-btn:hover:not(:disabled) {
  background: #124b42;
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(18, 75, 66, 0.2);
}
</style>
