<script setup lang="ts">
defineProps<{
  number: string
  title: string
  description: string
}>()
</script>

<template>
  <div class="step-card">
    <div class="step-number">{{ number }}</div>
    <h3 class="step-title">{{ title }}</h3>
    <p class="step-description">{{ description }}</p>
  </div>
</template>

<style scoped>
.step-card {
  border: 1px solid var(--color-border-light);
  border-radius: 12px;
  padding: 1.5rem;
  background-color: var(--color-background);
  transition: transform 0.2s, box-shadow 0.2s;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.02);
}
.step-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 12px rgba(0, 0, 0, 0.05);
}

.step-number {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background-color: var(--color-bg-sage);
  color: var(--color-primary);
  font-weight: 700;
  font-size: 0.85rem;
  margin-bottom: 1rem;
}

.step-title {
  font-size: 1.15rem;
  font-weight: 700;
  margin-bottom: 0.75rem;
  color: var(--color-text-main);
}

.step-description {
  font-size: 0.95rem;
  color: var(--color-text-muted);
  line-height: 1.5;
}
</style>
