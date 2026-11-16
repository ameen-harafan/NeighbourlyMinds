<script setup lang="ts">
defineProps<{
  title: string
  description: string
  buttonText: string
  buttonStyle?: 'solid' | 'outline'
}>()
</script>

<template>
  <div 
    class="action-card" 
    @click="$emit('actionClick')"
    role="button"
    tabindex="0"
    :aria-label="title + ': ' + buttonText"
    @keydown.enter="$emit('actionClick')"
    @keydown.space.prevent="$emit('actionClick')"
  >
    <div class="card-content">
      <div class="card-header">
        <div class="icon-wrapper" aria-hidden="true">
          <slot name="icon"></slot>
        </div>
        <h3 class="card-title">{{ title }}</h3>
      </div>
      <p class="card-description">{{ description }}</p>
      <button 
        type="button"
        :class="['card-button', buttonStyle === 'outline' ? 'outline' : 'solid']"
        tabindex="-1"
        aria-hidden="true"
      >
        {{ buttonText }}
        <span class="btn-arrow" v-if="buttonStyle === 'solid'">&rarr;</span>
      </button>
    </div>
  </div>
</template>

<style scoped>
.action-card {
  display: flex;
  flex-direction: column;
  border-radius: 16px;
  border: 1px solid #e5e0d8;
  background-color: white;
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.05);
  transition: transform 0.2s ease, box-shadow 0.2s ease;
  overflow: hidden;
  height: 100%;
  cursor: pointer;
}

.action-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 10px 25px rgba(0, 0, 0, 0.08);
}

.action-card:focus-visible {
  outline: 3px solid #f59e0b;
  outline-offset: 2px;
}

.card-content {
  padding: 2rem;
  display: flex;
  flex-direction: column;
  flex: 1;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin-bottom: 1rem;
}

.icon-wrapper {
  background-color: var(--color-bg-sage, #f4f6f5);
  border-radius: 12px;
  width: 50px;
  height: 50px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.5rem;
  flex-shrink: 0;
}

.card-title {
  font-size: 1.25rem;
  font-weight: 800;
  color: var(--color-text-main);
  margin: 0;
  line-height: 1.3;
}

.card-description {
  font-size: 1rem;
  color: var(--color-text-muted);
  margin-bottom: 2rem;
  line-height: 1.5;
  flex: 1; /* Push button to bottom */
}

.card-button {
  width: 100%;
  padding: 1rem 1.5rem;
  border-radius: 12px;
  font-weight: 700;
  font-size: 1rem;
  cursor: pointer;
  transition: all 0.2s ease;
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 0.5rem;
}

.card-button.solid {
  background-color: var(--color-primary);
  color: white;
  border: none;
  box-shadow: 0 4px 15px rgba(23, 93, 82, 0.15);
}

.card-button.solid:hover {
  background-color: #124b42;
  box-shadow: 0 6px 20px rgba(23, 93, 82, 0.25);
  transform: translateY(-2px);
}

.card-button.outline {
  background-color: transparent;
  color: var(--color-text-main);
  border: 2px solid #d1ddd7;
}

.card-button.outline:hover {
  background-color: rgba(23,93,82,0.05);
  border-color: var(--color-primary);
}

.btn-arrow {
  font-size: 1.1rem;
  transition: transform 0.2s ease;
}

.card-button.solid:hover .btn-arrow {
  transform: translateX(4px);
}
</style>
