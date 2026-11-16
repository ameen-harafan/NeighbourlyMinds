<script setup lang="ts">
import { inject } from 'vue'
import type { ViewState } from '../App.vue'

const navigateTo = inject<(view: ViewState) => void>('navigateTo', () => {})

const handleAction = () => {
  navigateTo('bathroom-compare')
}
</script>

<template>
  <div class="task-rehearsal-page">
    <!-- Top Screen Header Bar -->
    <header class="page-header">
      <h2 class="page-title">Task Rehearsal</h2>
    </header>

    <!-- Main Content Area -->
    <main>
      <!-- Page Description -->
      <section class="description-section">
        <p class="page-subtitle">
          Give the user a small everyday task and show where the environment creates unnecessary decision work.
        </p>
      </section>

      <!-- Task Exercise Card Container -->
      <article class="exercise-card">
        <!-- Task Badges/Tags -->
        <div class="card-tags">
          <span class="badge-solid">TASK</span>
          <span class="badge-outline">Bathroom</span>
        </div>

        <!-- Task Title & Subtitle -->
        <h2 class="card-title">Find and use the bathroom safely at night.</h2>
        <p class="card-subtitle">This is an environment interaction exercise (not a cognitive test).</p>

        <!-- 2-Column Task Grid -->
        <div class="task-columns">
          <!-- Before Change Section -->
          <section class="column before-column">
            <p class="column-overline">BEFORE CHANGE</p>
            <h3 class="column-title">Try the task</h3>
            <p class="column-text">
              The task contains multiple visual cues. Notice which elements compete for attention.
            </p>

            <!-- Step-by-Step Task Items -->
            <ol class="step-list">
              <li class="step-item">
                <span class="step-badge">1</span>
                <div class="step-content">
                  <h4 class="step-title">Find the entrance</h4>
                  <p class="step-description">Doorway is not strongly distinguished.</p>
                </div>
              </li>
              <li class="step-item">
                <span class="step-badge">2</span>
                <div class="step-content">
                  <h4 class="step-title">Identify the fixture</h4>
                  <p class="step-description">Fixture and background are visually similar.</p>
                </div>
              </li>
              <li class="step-item">
                <span class="step-badge">3</span>
                <div class="step-content">
                  <h4 class="step-title">Ignore competing information</h4>
                  <p class="step-description">Visual clutter adds another decision.</p>
                </div>
              </li>
            </ol>
          </section>

          <!-- What the Environment is Asking Section -->
          <section class="column environment-column">
            <p class="column-overline">WHAT THE ENVIRONMENT IS ASKING</p>

            <!-- Environment Metric Cards -->
            <ul class="metrics-grid">
              <li class="metric-card">
                <strong class="metric-number">4</strong>
                <p class="metric-label">ambiguous decision points</p>
              </li>
              <li class="metric-card">
                <strong class="metric-number">3</strong>
                <p class="metric-label">similar visual cues</p>
              </li>
              <li class="metric-card">
                <strong class="metric-number">1</strong>
                <p class="metric-label">clear landmark</p>
              </li>
            </ul>

            <!-- Key Learning Callout -->
            <aside class="key-learning-card">
              <h4 class="key-learning-title">Key Learning</h4>
              <p class="key-learning-text">
                The task can become easier when the environment presents clearer cues.
              </p>
            </aside>
          </section>
        </div>

        <!-- Action Button -->
        <div class="card-actions">
          <button class="action-btn" type="button" @click="handleAction">
            See before &amp; after &rarr;
          </button>
        </div>
      </article>
    </main>
  </div>
</template>

<style scoped>
.task-rehearsal-page {
  max-width: 900px;
  margin: 0 auto;
  padding: 2rem;
  font-family: inherit;
}

.page-header {
  margin-bottom: 1rem;
}

.page-title {
  font-size: 2rem;
  font-weight: 800;
  color: var(--color-text-main, #1c1c1c);
  margin-bottom: 0.5rem;
}

.description-section {
  margin-bottom: 2rem;
}

.page-subtitle {
  font-size: 1.1rem;
  color: var(--color-text-muted, #666666);
  line-height: 1.5;
}

/* Exercise Card Container */
.exercise-card {
  background-color: #ffffff;
  border: 1px solid var(--color-border-light, #e5e5e5);
  border-radius: 16px;
  padding: 2.5rem;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.04);
}

.card-tags {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 1.25rem;
}

.badge-solid {
  background-color: var(--color-bg-sage, #e9eee9);
  color: var(--color-primary, #175d52);
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: 0.05em;
  padding: 0.3rem 0.8rem;
  border-radius: 20px;
  text-transform: uppercase;
}

.badge-outline {
  border: 1px solid var(--color-border-light, #e5e5e5);
  color: var(--color-text-muted, #666666);
  font-size: 0.8rem;
  font-weight: 600;
  padding: 0.3rem 0.8rem;
  border-radius: 20px;
}

.card-title {
  font-size: 1.75rem;
  font-weight: 800;
  color: var(--color-text-main, #1c1c1c);
  margin-bottom: 0.5rem;
  line-height: 1.3;
}

.card-subtitle {
  font-size: 1rem;
  color: var(--color-text-muted, #666666);
  margin-bottom: 2rem;
}

/* 2-Column Task Grid */
.task-columns {
  display: grid;
  grid-template-columns: 1fr;
  gap: 2rem;
  margin-bottom: 2rem;
}

.column {
  display: flex;
  flex-direction: column;
}

.column-overline {
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: 0.05em;
  color: var(--color-primary, #175d52);
  text-transform: uppercase;
  margin-bottom: 0.5rem;
}

.column-title {
  font-size: 1.25rem;
  font-weight: 700;
  color: var(--color-text-main, #1c1c1c);
  margin-bottom: 0.5rem;
}

.column-text {
  font-size: 0.95rem;
  color: var(--color-text-muted, #666666);
  line-height: 1.5;
  margin-bottom: 1.5rem;
}

/* Step-by-Step Task Items */
.step-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 0.85rem;
}

.step-item {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 0.9rem 1.25rem;
  border: 1px solid var(--color-border-light, #e5e5e5);
  border-radius: 12px;
  background-color: #ffffff;
  box-shadow: 0 2px 5px rgba(0, 0, 0, 0.02);
  transition: transform 0.2s, box-shadow 0.2s;
}

.step-item:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 10px rgba(0, 0, 0, 0.05);
}

.step-badge {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background-color: var(--color-bg-sage, #e9eee9);
  color: var(--color-primary, #175d52);
  font-weight: 700;
  font-size: 0.9rem;
  flex-shrink: 0;
}

.step-content {
  display: flex;
  flex-direction: column;
}

.step-title {
  font-size: 1rem;
  font-weight: 700;
  color: var(--color-text-main, #1c1c1c);
  margin: 0 0 0.2rem 0;
}

.step-description {
  font-size: 0.85rem;
  color: var(--color-text-muted, #666666);
  line-height: 1.4;
  margin: 0;
}

/* Environment Metric Cards */
.metrics-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 0.75rem;
  list-style: none;
  padding: 0;
  margin: 0 0 1.5rem 0;
}

.metric-card {
  border: 1px solid var(--color-border-light, #e5e5e5);
  border-radius: 12px;
  padding: 1.25rem 0.5rem;
  text-align: center;
  background-color: #ffffff;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  box-shadow: 0 2px 5px rgba(0, 0, 0, 0.02);
  transition: transform 0.2s, box-shadow 0.2s;
}

.metric-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 10px rgba(0, 0, 0, 0.05);
}

.metric-number {
  font-size: 1.75rem;
  font-weight: 800;
  color: var(--color-text-main, #1c1c1c);
  margin-bottom: 0.35rem;
  line-height: 1;
}

.metric-label {
  font-size: 0.8rem;
  color: var(--color-text-muted, #666666);
  line-height: 1.3;
  margin: 0;
}

/* Key Learning Callout */
.key-learning-card {
  background-color: var(--color-bg-sage, #e9eee9);
  border-left: 4px solid var(--color-primary, #175d52);
  border-radius: 0 12px 12px 0;
  padding: 1.25rem 1.5rem;
  margin-top: auto;
}

.key-learning-title {
  font-size: 1.05rem;
  font-weight: 700;
  color: var(--color-text-main, #1c1c1c);
  margin: 0 0 0.4rem 0;
}

.key-learning-text {
  font-size: 0.95rem;
  color: var(--color-text-main, #1c1c1c);
  line-height: 1.5;
  margin: 0;
}

/* Action Button */
.card-actions {
  margin-top: 1rem;
}

.action-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background-color: var(--color-primary, #175d52);
  color: #ffffff;
  border: none;
  border-radius: 8px;
  padding: 0.85rem 1.75rem;
  font-size: 1rem;
  font-weight: 700;
  cursor: pointer;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.08);
  transition: all 0.2s cubic-bezier(0.25, 0.8, 0.25, 1);
}

.action-btn:hover {
  background-color: var(--color-primary-hover, #124b42);
  transform: translateY(-2px);
  box-shadow: 0 6px 12px rgba(0, 0, 0, 0.12);
}

.action-btn:active {
  transform: translateY(0);
}

@media (min-width: 768px) {
  .task-columns {
    grid-template-columns: 1fr 1fr;
    gap: 2.5rem;
  }
}
</style>
