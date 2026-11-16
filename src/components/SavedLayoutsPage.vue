<script setup lang="ts">
import { ref, computed, inject } from 'vue'
import type { ViewState } from '../App.vue'
import { bathroomStore, kitchenStore, type LayoutState } from '../store'
import RoomVisualizer from './RoomVisualizer.vue'
import KitchenVisualizer from './KitchenVisualizer.vue'

const navigateTo = inject<(view: ViewState) => void>('navigateTo', () => {})

const allLayouts = computed(() => {
  return [...bathroomStore.savedLayouts, ...kitchenStore.savedLayouts].sort((a, b) => {
    // Sort by timestamp if possible, otherwise just use id (which is Date.now)
    return parseInt(b.id) - parseInt(a.id)
  })
})

const selectedLayout = ref<LayoutState | null>(null)
const statusAnnouncement = ref('')

const selectLayout = (layout: LayoutState) => {
  selectedLayout.value = layout
  statusAnnouncement.value = `Selected ${layout.name} for ${layout.room === 'bathroom' ? 'Bathroom' : 'Kitchen'}.`
}

const deleteLayout = (layout: LayoutState) => {
  if (layout.room === 'bathroom') {
    bathroomStore.savedLayouts = bathroomStore.savedLayouts.filter(l => l.id !== layout.id)
  } else {
    kitchenStore.savedLayouts = kitchenStore.savedLayouts.filter(l => l.id !== layout.id)
  }
  statusAnnouncement.value = `Deleted layout ${layout.name}.`
  if (selectedLayout.value?.id === layout.id) {
    selectedLayout.value = allLayouts.value[0] || null
  }
}

const editLayout = () => {
  if (!selectedLayout.value) return
  
  if (selectedLayout.value.room === 'bathroom') {
    bathroomStore.savedStates = JSON.parse(JSON.stringify(selectedLayout.value.states))
    navigateTo('bathroom-task')
  } else {
    kitchenStore.savedStates = JSON.parse(JSON.stringify(selectedLayout.value.states))
    navigateTo('kitchen-task')
  }
}
</script>

<template>
  <div class="saved-layouts-page">
    <div class="visually-hidden" aria-live="polite" aria-atomic="true">
      {{ statusAnnouncement }}
    </div>

    <header class="page-header">
      <h1 class="page-title">Your Saved Layouts</h1>
      <p class="page-subtitle">
        Review your saved environments. Select a layout to view it, or click Edit to continue making adjustments.
      </p>
    </header>

    <div v-if="allLayouts.length === 0" class="empty-state">
      <h2>No layouts saved yet</h2>
      <p>Try making some adjustments in the Kitchen or Bathroom tasks and hit "Save Layout" on the compare screen.</p>
      <button class="btn-primary" @click="navigateTo('explore')">Explore Rooms</button>
    </div>

    <div class="layouts-workspace" v-else>
      <div class="layouts-sidebar" role="region" aria-label="Saved layouts list">
        <div 
          v-for="layout in allLayouts" 
          :key="layout.id" 
          role="button"
          tabindex="0"
          :aria-pressed="selectedLayout?.id === layout.id"
          :aria-label="'Select layout ' + layout.name + ', saved on ' + layout.timestamp"
          :class="['layout-card', { active: selectedLayout?.id === layout.id }]"
          @click="selectLayout(layout)"
          @keydown.enter="selectLayout(layout)"
          @keydown.space.prevent="selectLayout(layout)"
        >
          <div class="layout-icon" aria-hidden="true">
            {{ layout.room === 'bathroom' ? '🛁' : '🍽️' }}
          </div>
          <div class="layout-info">
            <h3 class="layout-name">{{ layout.name }}</h3>
            <span class="layout-date">{{ layout.timestamp }}</span>
          </div>
          <button 
            type="button"
            class="btn-delete" 
            @click.stop="deleteLayout(layout)" 
            @keydown.enter.stop="deleteLayout(layout)"
            @keydown.space.stop="deleteLayout(layout)"
            :aria-label="'Delete saved layout ' + layout.name"
            title="Delete layout"
          >
            🗑️<span class="visually-hidden">Delete</span>
          </button>
        </div>
      </div>

      <div class="layout-viewer">
        <div v-if="!selectedLayout" class="viewer-empty">
          <p>Select a layout from the sidebar to view it here.</p>
        </div>
        <div v-else class="viewer-content">
          <div class="viewer-header">
            <h2>{{ selectedLayout.name }}</h2>
            <button class="btn-primary" @click="editLayout">← Edit this layout</button>
          </div>
          <div class="visualizer-container">
            <RoomVisualizer v-if="selectedLayout.room === 'bathroom'" :itemStates="selectedLayout.states" :hide-markers="true" />
            <KitchenVisualizer v-else :itemStates="selectedLayout.states" :hide-markers="true" />
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.saved-layouts-page {
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

.page-title {
  font-size: 2.5rem;
  font-weight: 800;
  color: var(--color-text-main);
  margin-bottom: 0.5rem;
}

.page-subtitle {
  font-size: 1.2rem;
  color: var(--color-text-muted);
  max-width: 600px;
}

.empty-state {
  text-align: center;
  padding: 4rem 2rem;
  background: white;
  border-radius: 16px;
  border: 1px dashed var(--color-border);
  margin-top: 2rem;
}

.empty-state h2 {
  color: var(--color-text-main);
  margin-bottom: 1rem;
}

.empty-state p {
  color: var(--color-text-muted);
  margin-bottom: 2rem;
}

.layouts-workspace {
  display: flex;
  gap: 2rem;
  margin-top: 2rem;
  align-items: flex-start;
}

.layouts-sidebar {
  width: 350px;
  display: flex;
  flex-direction: column;
  gap: 1rem;
  max-height: 70vh;
  overflow-y: auto;
  padding-right: 0.5rem;
}

.layout-card {
  display: flex;
  align-items: center;
  gap: 1rem;
  background: white;
  border: 2px solid var(--color-border);
  border-radius: 12px;
  padding: 1.25rem;
  cursor: pointer;
  transition: all 0.2s ease;
}

.layout-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0,0,0,0.05);
}

.layout-card:focus-visible {
  outline: 3px solid #f59e0b;
  outline-offset: 2px;
}

.layout-card.active {
  border-color: var(--color-primary);
  background: var(--color-bg-sage);
}

.layout-icon {
  font-size: 2rem;
}

.layout-info {
  display: flex;
  flex-direction: column;
  flex: 1;
}

.btn-delete {
  background: transparent;
  border: 1px solid transparent;
  border-radius: 8px;
  padding: 0.5rem;
  font-size: 1.25rem;
  cursor: pointer;
  min-width: 44px;
  min-height: 44px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
  color: #ef4444;
}

.btn-delete:hover {
  background: #fee2e2;
  border-color: #fca5a5;
  transform: scale(1.05);
}

.btn-delete:focus-visible {
  outline: 3px solid #f59e0b;
  outline-offset: 2px;
  background: #fee2e2;
}

.layout-name {
  font-size: 1.1rem;
  font-weight: 700;
  color: var(--color-text-main);
  margin: 0 0 0.25rem 0;
}

.layout-date {
  font-size: 0.85rem;
  color: var(--color-text-muted);
}

.layout-viewer {
  flex: 1;
  background: white;
  border: 1px solid var(--color-border);
  border-radius: 16px;
  padding: 2rem;
  min-height: 60vh;
  box-shadow: 0 8px 30px rgba(0,0,0,0.04);
}

.viewer-empty {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--color-text-muted);
  font-size: 1.2rem;
}

.viewer-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 2rem;
}

.viewer-header h2 {
  font-size: 1.8rem;
  font-weight: 800;
  color: var(--color-text-main);
  margin: 0;
}

.btn-primary {
  background: var(--color-primary);
  color: white;
  border: none;
  border-radius: 99px;
  padding: 0.75rem 1.5rem;
  font-weight: 600;
  font-size: 1rem;
  cursor: pointer;
  transition: all 0.2s ease;
}

.btn-primary:hover {
  background: var(--color-primary-hover, #124b42);
  transform: translateY(-2px);
}

.visualizer-container {
  width: 100%;
  display: flex;
  justify-content: center;
  align-items: center;
}

.visualizer-container > * {
  width: 100%;
}
</style>
