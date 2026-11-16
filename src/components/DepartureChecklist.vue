<script setup lang="ts">
import { ref, toRef } from 'vue'
import type { DestinationAnchor } from '../utils/activityData'
import { useDepartureChecklist, type ChecklistItem } from '../composables/useDepartureChecklist'

const props = defineProps<{
  destination: string
  currentAnchor?: DestinationAnchor
}>()

const emit = defineEmits<{
  (e: 'continue'): void
}>()

const destRef = toRef(props, 'destination')
const anchorRef = toRef(props, 'currentAnchor')

const {
  checkedItems,
  departureChecklist,
  toggleChecklistItem,
  addCustomItem,
  editCustomItem,
  deleteCustomItem,
  checkedCount,
  allChecked,
  resetChecklist,
} = useDepartureChecklist(destRef, anchorRef)

// Checklist interactive item editing & adding state
const editingItemId = ref<string | null>(null)
const editItemTitle = ref('')
const editInputRef = ref<HTMLInputElement | null>(null)

const isAddingItem = ref(false)
const newItemTitle = ref('')
const newItemInputRef = ref<HTMLInputElement | null>(null)

const quickSuggestions = [
  { icon: '🦯', title: 'Walking stick / cane' },
  { icon: '👓', title: 'Reading glasses' },
  { icon: '📝', title: 'Shopping list / notes' },
  { icon: '👒', title: 'Sun hat & sunglasses' },
  { icon: '📄', title: 'Appointment paperwork' }
]

const startEditItem = (item: ChecklistItem) => {
  editingItemId.value = item.id
  editItemTitle.value = item.title
  setTimeout(() => {
    editInputRef.value?.focus()
  }, 60)
}

const saveEditItem = (id: string) => {
  if (editItemTitle.value.trim()) {
    editCustomItem(id, editItemTitle.value.trim())
  }
  editingItemId.value = null
  editItemTitle.value = ''
}

const cancelEditItem = () => {
  editingItemId.value = null
  editItemTitle.value = ''
}

const openAddItem = () => {
  isAddingItem.value = true
  newItemTitle.value = ''
  setTimeout(() => {
    newItemInputRef.value?.focus()
  }, 60)
}

const cancelAddItem = () => {
  isAddingItem.value = false
  newItemTitle.value = ''
}

const submitNewItem = () => {
  if (newItemTitle.value.trim()) {
    addCustomItem(newItemTitle.value.trim())
    newItemTitle.value = ''
    isAddingItem.value = false
  }
}

const addChipItem = (chip: { icon: string; title: string }) => {
  addCustomItem(chip.title, chip.icon)
  isAddingItem.value = false
}

const handleDeleteItem = (id: string) => {
  if (editingItemId.value === id) {
    cancelEditItem()
  }
  deleteCustomItem(id)
}
</script>

<template>
  <section id="step3-section" class="guided-step-card departure-checklist-section" aria-labelledby="step3-heading">
    <div class="step-badge-row">
      <span class="step-badge highlight-badge">STEP 3</span>
      <span class="step-badge-label">Departure Checklist</span>
    </div>
    
    <div class="checklist-header-row">
      <div class="checklist-title-group">
        <h2 id="step3-heading" class="step-card-title">Before You Step Out: Peace of Mind Checklist</h2>
        <p class="step-card-desc">
          Tap each item as you get ready. Taking a moment before you leave reduces worry and ensures you have what you need.
        </p>
      </div>

      <div class="checklist-counter-badge" :class="{ 'all-done': allChecked }">
        <span class="counter-num">{{ checkedCount }} of {{ departureChecklist.length }}</span>
        <span class="counter-label">{{ allChecked ? 'All Set! ✨' : 'Ready' }}</span>
      </div>
    </div>

    <!-- Checklist Items -->
    <div class="checklist-items-grid" role="group" aria-label="Pre-departure essentials checklist">
      <div
        v-for="item in departureChecklist"
        :key="item.id"
        class="checklist-card"
        :class="{
          'checked': checkedItems[item.id],
          'is-custom': item.isCustom,
          'is-editing': editingItemId === item.id
        }"
        @click="editingItemId !== item.id && toggleChecklistItem(item.id)"
        role="checkbox"
        :aria-checked="!!checkedItems[item.id]"
        tabindex="0"
        @keydown.space.prevent="editingItemId !== item.id && toggleChecklistItem(item.id)"
        @keydown.enter.prevent="editingItemId !== item.id && toggleChecklistItem(item.id)"
      >
        <div class="check-box-indicator" aria-hidden="true">
          <span v-if="checkedItems[item.id]" class="check-tick">✓</span>
        </div>

        <div class="checklist-item-icon" aria-hidden="true">{{ item.icon }}</div>

        <!-- Inline Editing State -->
        <div v-if="editingItemId === item.id" class="checklist-inline-edit" @click.stop>
          <input
            ref="editInputRef"
            v-model="editItemTitle"
            type="text"
            class="edit-inline-input"
            maxlength="70"
            aria-label="Edit item title"
            @keydown.space.stop
            @keydown.enter.stop.prevent="saveEditItem(item.id)"
            @keydown.esc.stop.prevent="cancelEditItem"
          />
          <div class="inline-edit-actions">
            <button 
              type="button" 
              class="save-btn" 
              @click.stop="saveEditItem(item.id)"
            >
              Save
            </button>
            <button 
              type="button" 
              class="cancel-btn" 
              @click.stop="cancelEditItem"
            >
              Cancel
            </button>
          </div>
        </div>

        <!-- Normal Item State -->
        <div v-else class="checklist-item-text">
          <div class="checklist-title-row">
            <strong class="checklist-item-title">{{ item.title }}</strong>
            <span v-if="item.isCustom" class="custom-item-tag">My Outing Item</span>
          </div>
          <span v-if="item.hint" class="checklist-item-hint">{{ item.hint }}</span>
        </div>

        <!-- Action buttons for custom items (Edit & Delete) -->
        <div v-if="item.isCustom && editingItemId !== item.id" class="custom-card-actions" @click.stop>
          <button
            type="button"
            class="card-action-btn edit-action-btn"
            title="Edit item name"
            aria-label="Edit item"
            @click.stop="startEditItem(item)"
          >
            ✏️ <span class="action-btn-text">Edit</span>
          </button>
          <button
            type="button"
            class="card-action-btn delete-action-btn"
            title="Remove item"
            aria-label="Remove item"
            @click.stop="handleDeleteItem(item.id)"
          >
            ✕ <span class="action-btn-text">Remove</span>
          </button>
        </div>
      </div>
    </div>

    <!-- Add Custom Item Area -->
    <div class="add-custom-item-container">
      <div v-if="isAddingItem" class="add-item-box" role="region" aria-label="Add custom checklist item">
        <div class="add-item-input-row">
          <span class="add-item-icon-bubble" aria-hidden="true">🎯</span>
          <input
            ref="newItemInputRef"
            v-model="newItemTitle"
            type="text"
            class="new-item-text-input"
            placeholder="e.g. Walking stick, reading glasses, letter..."
            maxlength="70"
            aria-label="New checklist item name"
            @keydown.enter.prevent="submitNewItem"
            @keydown.esc.prevent="cancelAddItem"
          />
          <button
            type="button"
            class="add-confirm-btn"
            :disabled="!newItemTitle.trim()"
            @click="submitNewItem"
          >
            Add Item
          </button>
          <button
            type="button"
            class="add-cancel-btn"
            @click="cancelAddItem"
          >
            Cancel
          </button>
        </div>

        <!-- Quick Suggestion Chips -->
        <div class="quick-suggestions-bar">
          <span class="quick-suggestions-label">Quick suggestions:</span>
          <div class="quick-chips-wrapper">
            <button
              v-for="chip in quickSuggestions"
              :key="chip.title"
              type="button"
              class="quick-chip-button"
              @click="addChipItem(chip)"
            >
              <span class="chip-icon" aria-hidden="true">{{ chip.icon }}</span>
              <span>{{ chip.title }}</span>
            </button>
          </div>
        </div>
      </div>

      <button
        v-else
        type="button"
        class="add-item-trigger-card"
        @click="openAddItem"
      >
        <span class="plus-circle" aria-hidden="true">+</span>
        <div class="add-trigger-text">
          <strong>Add more items for your trip</strong>
          <span>Add your personalised items to the checklist</span>
        </div>
      </button>
    </div>

    <!-- Reassurance Banner when completed -->
    <div v-if="allChecked" class="checklist-complete-banner" role="status">
      <span class="celebrate-icon" aria-hidden="true">🌟</span>
      <div class="complete-text">
        <strong>You are all set for a calm, confident outing!</strong>
        <p>Everything is checked off. You are ready for a calm, confident walk!</p>
      </div>
      <button type="button" class="reset-check-btn" @click.stop="resetChecklist">
        Reset Checklist
      </button>
    </div>

    <!-- Navigation to Pocket Card -->
    <div class="step-actions-row step3-actions">
      <button 
        type="button" 
        class="next-step-btn final-pocket-btn"
        @click="emit('continue')"
      >
        View My Pocket Card & Route &rarr;
      </button>
    </div>
  </section>
</template>

<style scoped>
.guided-step-card {
  background: #ffffff;
  border: 1.5px solid #d8e5df;
  border-radius: 16px;
  padding: 1.75rem;
  box-shadow: 0 2px 8px rgba(23, 93, 82, 0.04);
}

.departure-checklist-section {
  background: #ffffff;
  border-color: #d4e5dd;
}

/* Badges */
.step-badge-row {
  display: flex;
  align-items: center;
  gap: 0.65rem;
  margin-bottom: 0.75rem;
}

.step-badge {
  display: inline-block;
  font-size: 0.75rem;
  font-weight: 800;
  letter-spacing: 0.06em;
  padding: 0.25rem 0.65rem;
  border-radius: 6px;
  background: #e9f2ee;
  color: #175d52;
  text-transform: uppercase;
}

.step-badge.highlight-badge {
  background: #175d52;
  color: #ffffff;
}

.step-badge-label {
  font-size: 0.85rem;
  font-weight: 700;
  color: #557266;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.step-card-title {
  font-size: 1.55rem;
  font-weight: 800;
  color: #1c2e28;
  margin: 0 0 0.4rem 0;
  line-height: 1.3;
}

.step-card-desc {
  font-size: 1rem;
  color: #4b6358;
  margin: 0 0 1.5rem 0;
  line-height: 1.5;
}

.checklist-header-row {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 1.5rem;
  flex-wrap: wrap;
  margin-bottom: 0.5rem;
}

.checklist-title-group {
  flex: 1;
  min-width: 280px;
}

.checklist-counter-badge {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: #f0f7f4;
  border: 2px solid #badcd0;
  border-radius: 12px;
  padding: 0.6rem 1.25rem;
  min-width: 110px;
  transition: all 0.25s ease;
}

.checklist-counter-badge.all-done {
  background: #175d52;
  border-color: #175d52;
  color: #ffffff;
  box-shadow: 0 4px 12px rgba(23, 93, 82, 0.25);
}

.counter-num {
  font-size: 1.3rem;
  font-weight: 850;
  color: #175d52;
  line-height: 1.2;
}

.checklist-counter-badge.all-done .counter-num {
  color: #ffffff;
}

.counter-label {
  font-size: 0.78rem;
  font-weight: 750;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: #4b6358;
}

.checklist-counter-badge.all-done .counter-label {
  color: #d1fae5;
}

.checklist-items-grid {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  margin-top: 1rem;
}

.checklist-card {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1rem 1.25rem;
  background: #fbfdfc;
  border: 2px solid #e1ebe6;
  border-radius: 14px;
  cursor: pointer;
  transition: all 0.2s ease;
  min-height: 64px;
  user-select: none;
}

.checklist-card:hover {
  border-color: #175d52;
  background: #f4faf6;
}

.checklist-card:focus-visible {
  outline: 3px solid #175d52;
  outline-offset: 2px;
}

.checklist-card.checked {
  background: #f0f7f4;
  border-color: #8ec3b2;
}

.check-box-indicator {
  width: 28px;
  height: 28px;
  border: 2.5px solid #89a89d;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  background: #ffffff;
  transition: all 0.2s ease;
}

.checklist-card.checked .check-box-indicator {
  background: #175d52;
  border-color: #175d52;
}

.check-tick {
  color: #ffffff;
  font-size: 1.1rem;
  font-weight: 900;
  line-height: 1;
}

.checklist-item-icon {
  font-size: 1.6rem;
  flex-shrink: 0;
}

.checklist-item-text {
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
  flex: 1;
}

.checklist-item-title {
  font-size: 1.05rem;
  font-weight: 750;
  color: #1c2e28;
  line-height: 1.35;
}

.checklist-card.checked .checklist-item-title {
  color: #175d52;
}

.checklist-item-hint {
  font-size: 0.88rem;
  color: #557266;
  line-height: 1.4;
}

/* Custom Checklist Items & Inline Editing */
.checklist-card.is-custom {
  border-left: 5px solid #2e7d32;
}

.checklist-card.is-editing {
  border-color: #175d52;
  background: #ffffff;
  cursor: default;
}

.checklist-title-row {
  display: flex;
  align-items: center;
  gap: 0.55rem;
  flex-wrap: wrap;
}

.custom-item-tag {
  font-size: 0.72rem;
  font-weight: 750;
  background: #e8f5e9;
  color: #1b5e20;
  border: 1px solid #c8e6c9;
  border-radius: 4px;
  padding: 0.12rem 0.45rem;
  text-transform: uppercase;
  letter-spacing: 0.03em;
}

.custom-card-actions {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  margin-left: auto;
  flex-shrink: 0;
}

.card-action-btn {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  background: #ffffff;
  border: 1.5px solid #d4e5dd;
  border-radius: 7px;
  padding: 0.35rem 0.6rem;
  font-size: 0.82rem;
  font-weight: 650;
  color: #3f5d51;
  cursor: pointer;
  transition: all 0.2s ease;
  font-family: inherit;
}

.card-action-btn:hover {
  background: #f0f7f4;
  border-color: #175d52;
  color: #175d52;
}

.delete-action-btn:hover {
  background: #fef2f2;
  border-color: #ef4444;
  color: #b91c1c;
}

.checklist-inline-edit {
  display: flex;
  align-items: center;
  gap: 0.55rem;
  flex: 1;
  flex-wrap: wrap;
}

.edit-inline-input {
  flex: 1;
  min-width: 220px;
  font-size: 1rem;
  font-family: inherit;
  font-weight: 600;
  color: #1c2e28;
  padding: 0.5rem 0.75rem;
  border: 2px solid #175d52;
  border-radius: 8px;
  outline: none;
  background: #ffffff;
  box-shadow: 0 0 0 3px rgba(23, 93, 82, 0.12);
}

.inline-edit-actions {
  display: flex;
  gap: 0.4rem;
}

.save-btn {
  background: #175d52;
  color: #ffffff;
  border: none;
  border-radius: 7px;
  padding: 0.5rem 0.9rem;
  font-weight: 750;
  font-size: 0.85rem;
  cursor: pointer;
  transition: background 0.2s;
  font-family: inherit;
}

.save-btn:hover {
  background: #0f443b;
}

.cancel-btn {
  background: #ffffff;
  border: 1.5px solid #d4e5dd;
  color: #557266;
  border-radius: 7px;
  padding: 0.5rem 0.8rem;
  font-size: 0.85rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  font-family: inherit;
}

.cancel-btn:hover {
  background: #f5f5f5;
  color: #333333;
}

/* Add Custom Item Section */
.add-custom-item-container {
  margin-top: 0.85rem;
}

.add-item-trigger-card {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 0.95rem 1.25rem;
  background: #f7faf8;
  border: 2px dashed #9fc2b4;
  border-radius: 14px;
  cursor: pointer;
  text-align: left;
  transition: all 0.2s ease;
  font-family: inherit;
}

.add-item-trigger-card:hover {
  border-color: #175d52;
  background: #eef7f3;
  transform: translateY(-1px);
}

.plus-circle {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: #175d52;
  color: #ffffff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.3rem;
  font-weight: 750;
  flex-shrink: 0;
  line-height: 1;
}

.add-trigger-text {
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
}

.add-trigger-text strong {
  color: #175d52;
  font-size: 1rem;
  font-weight: 750;
}

.add-trigger-text span {
  color: #4b6358;
  font-size: 0.85rem;
}

.add-item-box {
  background: #ffffff;
  border: 2px solid #175d52;
  border-radius: 14px;
  padding: 1.15rem 1.3rem;
  box-shadow: 0 4px 16px rgba(23, 93, 82, 0.08);
}

.add-item-input-row {
  display: flex;
  align-items: center;
  gap: 0.65rem;
  flex-wrap: wrap;
}

.add-item-icon-bubble {
  font-size: 1.5rem;
  line-height: 1;
}

.new-item-text-input {
  flex: 1;
  min-width: 240px;
  font-size: 1rem;
  font-family: inherit;
  font-weight: 600;
  color: #1c2e28;
  padding: 0.65rem 0.95rem;
  border: 2px solid #badcd0;
  border-radius: 8px;
  outline: none;
  transition: all 0.2s;
}

.new-item-text-input:focus {
  border-color: #175d52;
  box-shadow: 0 0 0 3px rgba(23, 93, 82, 0.15);
}

.add-confirm-btn {
  background: #175d52;
  color: #ffffff;
  font-weight: 750;
  font-size: 0.95rem;
  border: none;
  border-radius: 8px;
  padding: 0.65rem 1.25rem;
  cursor: pointer;
  transition: background 0.2s;
  font-family: inherit;
}

.add-confirm-btn:hover:not(:disabled) {
  background: #0f443b;
}

.add-confirm-btn:disabled {
  background: #badcd0;
  cursor: not-allowed;
}

.add-cancel-btn {
  background: transparent;
  color: #4b6358;
  font-weight: 650;
  font-size: 0.9rem;
  border: 1.5px solid #d4e5dd;
  border-radius: 8px;
  padding: 0.65rem 1rem;
  cursor: pointer;
  transition: all 0.2s;
  font-family: inherit;
}

.add-cancel-btn:hover {
  background: #f5f5f5;
  color: #222222;
}

.quick-suggestions-bar {
  margin-top: 0.9rem;
  padding-top: 0.75rem;
  border-top: 1px solid #e1ebe6;
  display: flex;
  align-items: center;
  gap: 0.65rem;
  flex-wrap: wrap;
}

.quick-suggestions-label {
  font-size: 0.82rem;
  font-weight: 750;
  color: #4b6358;
}

.quick-chips-wrapper {
  display: flex;
  flex-wrap: wrap;
  gap: 0.45rem;
}

.quick-chip-button {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  background: #f0f7f4;
  border: 1.5px solid #badcd0;
  border-radius: 20px;
  padding: 0.35rem 0.75rem;
  font-size: 0.83rem;
  font-weight: 650;
  color: #175d52;
  cursor: pointer;
  transition: all 0.2s ease;
  font-family: inherit;
}

.quick-chip-button:hover {
  background: #175d52;
  color: #ffffff;
  border-color: #175d52;
}

.checklist-complete-banner {
  margin-top: 1.5rem;
  display: flex;
  align-items: center;
  gap: 1.25rem;
  padding: 1.25rem 1.5rem;
  background: #eaf6f0;
  border: 2px solid #99d5bf;
  border-radius: 14px;
  flex-wrap: wrap;
}

.celebrate-icon {
  font-size: 2rem;
  flex-shrink: 0;
}

.complete-text {
  flex: 1;
  min-width: 240px;
}

.complete-text strong {
  display: block;
  font-size: 1.1rem;
  color: #0d4e43;
  margin-bottom: 0.25rem;
}

.complete-text p {
  margin: 0;
  font-size: 0.95rem;
  color: #274b3d;
  line-height: 1.4;
}

.reset-check-btn {
  background: #ffffff;
  border: 1.5px solid #89a89d;
  color: #1c2e28;
  font-size: 0.88rem;
  font-weight: 700;
  padding: 0.45rem 0.9rem;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.reset-check-btn:hover {
  background: #f0f7f4;
  border-color: #175d52;
}

/* Actions Row & Pocket Button */
.step-actions-row {
  display: flex;
  justify-content: flex-end;
  margin-top: 1.5rem;
  padding-top: 1rem;
  border-top: 1px dashed #d8e5df;
}

.step3-actions {
  margin-top: 2rem;
}

.next-step-btn {
  background: #175d52;
  color: white;
  border: none;
  padding: 0.85rem 1.6rem;
  border-radius: 10px;
  font-size: 1rem;
  font-weight: 700;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  transition: all 0.2s ease;
  box-shadow: 0 2px 6px rgba(23, 93, 82, 0.2);
}

.next-step-btn:hover {
  background: #0f4038;
  transform: translateY(-1px);
  box-shadow: 0 4px 10px rgba(23, 93, 82, 0.25);
}

.final-pocket-btn {
  background: #11463e;
  font-size: 1.1rem;
  padding: 1rem 2rem;
}

.final-pocket-btn:hover {
  background: #092e28;
}
</style>
