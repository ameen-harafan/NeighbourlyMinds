<script setup lang="ts">
import { ref, computed, provide, onMounted, onUnmounted, watch } from 'vue'
import ExplorePage from './components/ExplorePage.vue'
import BathroomTask from './components/BathroomTask.vue'
import BathroomComparison from './components/BathroomComparison.vue'
import KitchenTask from './components/KitchenTask.vue'
import KitchenComparison from './components/KitchenComparison.vue'
import TaskRehearsalPage from './components/TaskRehearsalPage.vue'
import LandingPage from './components/LandingPage.vue'
import SavedLayoutsPage from './components/SavedLayoutsPage.vue'
import DaytimeSensorySchedule from './components/DaytimeSensorySchedule.vue'
import ActivityPreparationPage from './components/ActivityPreparationPage.vue'
import EnvironmentAuditor from './components/EnvironmentAuditor.vue'
import WalkPlanner from './components/WalkPlanner.vue'

export type ViewState = 'intro' | 'landing-page' | 'explore' | 'bathroom-task' | 'bathroom-contrast' | 'bathroom-compare' | 'kitchen-task' | 'kitchen-compare' | 'task-rehearsal' | 'saved-layouts' | 'sensory-schedule' | 'prepare-activity' | 'auditor' | 'walk-planner'
const currentView = ref<ViewState>('landing-page')

const viewTitles: Record<ViewState, string> = {
  'intro': 'Welcome',
  'landing-page': 'Home',
  'explore': 'Indoor Guides',
  'bathroom-task': 'Bathroom Guide',
  'bathroom-contrast': 'Bathroom Contrast',
  'bathroom-compare': 'Bathroom Comparison',
  'kitchen-task': 'Kitchen Guide',
  'kitchen-compare': 'Kitchen Comparison',
  'task-rehearsal': 'Task Rehearsal',
  'saved-layouts': 'Saved Layouts',
  'sensory-schedule': 'Daytime Sensory Schedule',
  'prepare-activity': 'Activity Preparation',
  'auditor': 'Environment Auditor',
  'walk-planner': 'Plan a Safe Walk',
}

const navigationHistory = ref<ViewState[]>(['landing-page'])

const scrollToVisualIntro = () => {
  if (currentView.value !== 'landing-page') {
    navigateTo('landing-page')
  }
  setTimeout(() => {
    const el = document.getElementById('visual-intro-section')
    if (el) {
      el.scrollIntoView({ behavior: 'smooth' })
    }
  }, 120)
}

const previousViewTitle = computed(() => {
  if (navigationHistory.value.length > 1) {
    const prev = navigationHistory.value[navigationHistory.value.length - 2]
    return (prev && viewTitles[prev]) ? viewTitles[prev] : 'previous page'
  }
  return 'Home'
})

// Reset any previously cached text sizing classes
if (typeof document !== 'undefined') {
  document.documentElement.classList.remove('text-normal', 'text-large', 'text-xlarge', 'large-text')
  localStorage.removeItem('app_text_size')
}

const navigateTo = (view: ViewState, pushHistory = true) => {
  currentView.value = view
  window.scrollTo({ top: 0, behavior: 'smooth' })
  
  if (pushHistory) {
    window.history.pushState({ view }, '', `#${view}`)
    if (navigationHistory.value[navigationHistory.value.length - 1] !== view) {
      navigationHistory.value.push(view)
    }
  }
}

const goBack = () => {
  if (navigationHistory.value.length > 1) {
    navigationHistory.value.pop() // remove current
    const target = navigationHistory.value[navigationHistory.value.length - 1]
    if (target) {
      currentView.value = target
      window.scrollTo({ top: 0, behavior: 'smooth' })
      window.history.replaceState({ view: target }, '', `#${target}`)
      return
    }
  }
  // Safe fallback to landing page if arrived directly or history empty
  navigateTo('landing-page')
}

const handlePopState = (event: PopStateEvent) => {
  if (event.state && event.state.view) {
    const target = event.state.view as ViewState
    currentView.value = target
    if (navigationHistory.value[navigationHistory.value.length - 1] !== target) {
      navigationHistory.value.push(target)
    }
  } else {
    // Fallback if no state, parse hash
    const hash = window.location.hash.replace('#', '')
    if (hash) {
      navigateTo(hash as ViewState, false)
    } else {
      navigateTo('landing-page', false)
    }
  }
}

const showScrollTop = ref(false)

const handleScroll = () => {
  showScrollTop.value = window.scrollY > 300
}

const scrollToTop = () => {
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

onMounted(() => {
  window.addEventListener('popstate', handlePopState)
  window.addEventListener('scroll', handleScroll, { passive: true })
  
  // Handle initial load
  const hash = window.location.hash.replace('#', '')
  if (hash === 'intro' || hash === 'visual-intro') {
    navigateTo('landing-page', false)
    setTimeout(() => {
      document.getElementById('visual-intro-section')?.scrollIntoView({ behavior: 'smooth' })
    }, 150)
  } else if (hash && hash !== 'landing-page') {
    navigateTo(hash as ViewState, false)
  } else {
    navigateTo('landing-page', false)
    window.history.replaceState({ view: 'landing-page' }, '', '#landing-page')
  }
})

onUnmounted(() => {
  window.removeEventListener('popstate', handlePopState)
  window.removeEventListener('scroll', handleScroll)
})

// Provide navigation to all child components
provide('navigateTo', navigateTo)
provide('goBack', goBack)
</script>

<template>
  <a href="#main-content" class="skip-link">Skip to main content</a>
  
  <main class="app-container" id="main-content" tabindex="-1">
    <header class="app-header" role="banner">
      <div class="header-left">
        <div class="brand-logo" @click="navigateTo('landing-page')" role="button" tabindex="0" aria-label="NeighbourlyMinds Home" @keypress.enter="navigateTo('landing-page')">
          <img src="./assets/Logo.jpeg" alt="" class="nav-logo-img" aria-hidden="true" />
          NeighbourlyMinds
        </div>
      </div>
      
      <nav class="main-nav" aria-label="Main Navigation">
        <button 
          type="button"
          class="nav-link" 
          :class="{ active: currentView === 'landing-page' }"
          :aria-current="currentView === 'landing-page' ? 'page' : undefined"
          @click="navigateTo('landing-page')"
        >
          Home
        </button>
        <button 
          type="button"
          class="nav-link" 
          :class="{ active: ['explore', 'bathroom-task', 'bathroom-contrast', 'bathroom-compare', 'kitchen-task', 'kitchen-compare', 'saved-layouts'].includes(currentView) }"
          :aria-current="['explore', 'bathroom-task', 'bathroom-contrast', 'bathroom-compare', 'kitchen-task', 'kitchen-compare', 'saved-layouts'].includes(currentView) ? 'page' : undefined"
          @click="navigateTo('explore')"
        >
          Indoor Guides
        </button>
        <button 
          type="button"
          class="nav-link" 
          :class="{ active: currentView === 'auditor' }"
          :aria-current="currentView === 'auditor' ? 'page' : undefined"
          @click="navigateTo('auditor')"
        >
          Environment Auditor
        </button>
        <button 
          type="button"
          class="nav-link" 
          :class="{ active: ['prepare-activity', 'sensory-schedule', 'walk-planner'].includes(currentView) }"
          :aria-current="['prepare-activity', 'sensory-schedule', 'walk-planner'].includes(currentView) ? 'page' : undefined"
          @click="navigateTo('prepare-activity')"
        >
          Outing Prep
        </button>
        <button 
          type="button"
          class="nav-link" 
          @click="scrollToVisualIntro"
        >
          Visual Intro
        </button>
      </nav>
    </header>

    <div class="view-content" :class="{ 'landing-view': currentView === 'landing-page' }">
      <LandingPage v-if="currentView === 'landing-page' || currentView === 'intro'" />
      <TaskRehearsalPage v-else-if="currentView === 'task-rehearsal'" />
      <ExplorePage v-else-if="currentView === 'explore'" />
      <BathroomTask v-else-if="currentView === 'bathroom-task'" />
      <BathroomComparison v-else-if="currentView === 'bathroom-compare'" />
      <KitchenTask v-else-if="currentView === 'kitchen-task'" />
      <KitchenComparison v-else-if="currentView === 'kitchen-compare'" />
      <SavedLayoutsPage v-else-if="currentView === 'saved-layouts'" />
      <DaytimeSensorySchedule v-else-if="currentView === 'sensory-schedule'" />
      <ActivityPreparationPage v-else-if="currentView === 'prepare-activity'" />
      <EnvironmentAuditor v-else-if="currentView === 'auditor'" />
      <WalkPlanner v-else-if="currentView === 'walk-planner'" />
    </div>

    <!-- Global Return to Top Button (WCAG 2.4.1 / 2.5.5) -->
    <button 
      type="button" 
      v-show="showScrollTop" 
      @click="scrollToTop" 
      class="global-scroll-top-btn" 
      aria-label="Return to Top"
      title="Return to Top"
    >
      &uarr;
    </button>
  </main>
</template>

<style>
:root {
  --bg-main: #f7f9f7;
  --bg-surface: #ffffff;
  --text-main: #1c1c1c;
  --text-muted: #52615b;
  --primary-color: #175d52;
  --primary-hover: #11463e;
  --border-color: #d1ddd7;
  --header-bg: rgba(255, 255, 255, 0.95);
  --font-scale: 1;

  /* Aliases for child components */
  --color-background: var(--bg-surface);
  --color-background-soft: var(--bg-main);
  --color-text-main: var(--text-main);
  --color-text-muted: var(--text-muted);
  --color-primary: var(--primary-color);
  --color-primary-hover: var(--primary-hover);
  --color-bg-sage: #e9eee9;
  --color-border: var(--border-color);
  --color-border-light: #e5e5e5;
}

html.large-text,
html.text-large {
  --font-scale: 1.25;
}

html.text-xlarge {
  --font-scale: 1.5;
}

html {
  font-size: calc(16px * var(--font-scale));
  transition: font-size 0.3s ease;
}

body {
  margin: 0;
  padding: 0;
  background-color: var(--bg-main);
  color: var(--text-main);
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  transition: background-color 0.3s ease, color 0.3s ease;
}

/* Skip Navigation Link (WCAG 2.4.1) */
.skip-link {
  position: absolute;
  top: -100px;
  left: 1.5rem;
  background: var(--primary-color, #175d52);
  color: #ffffff;
  padding: 0.75rem 1.25rem;
  border-radius: 0 0 8px 8px;
  font-weight: 700;
  font-size: 1rem;
  z-index: 10001;
  text-decoration: none;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.25);
  transition: top 0.2s ease-in-out;
}

.skip-link:focus {
  top: 0;
  outline: 3px solid #f59e0b;
  outline-offset: 2px;
}

/* Global Focus-Visible Styling (WCAG 2.4.7) */
:focus-visible {
  outline: 3px solid var(--primary-color, #175d52);
  outline-offset: 2px;
}

/* Visually Hidden Utility for Screen Readers (WCAG 1.3.1) */
.visually-hidden {
  position: absolute !important;
  width: 1px !important;
  height: 1px !important;
  padding: 0 !important;
  margin: -1px !important;
  overflow: hidden !important;
  clip: rect(0, 0, 0, 0) !important;
  white-space: nowrap !important;
  border: 0 !important;
}

button:focus-visible,
a:focus-visible,
input:focus-visible,
select:focus-visible,
div[tabindex="0"]:focus-visible {
  outline: 3px solid var(--primary-color, #175d52);
  outline-offset: 2px;
}

.app-container {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background-color: var(--bg-main);
  outline: none;
}

.view-content {
  flex: 1;
  padding-top: 70px; /* Space for fixed header */
  background-color: var(--bg-main);
  display: flex;
  flex-direction: column;
}

.view-content.landing-view {
  background: var(--bg-main);
}

/* Standard App Header */
.app-header {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  min-height: 70px;
  background: var(--header-bg);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  border-bottom: 1px solid var(--border-color);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.5rem 2rem;
  z-index: 1000;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.brand-logo {
  font-weight: 800;
  font-size: 1.2rem;
  color: var(--primary-color);
  cursor: pointer;
  white-space: nowrap;
  display: flex;
  align-items: center;
  gap: 0.4rem;
}

.nav-logo-img {
  height: 36px;
  width: auto;
  border-radius: 6px;
  object-fit: contain;
}

.main-nav {
  display: flex;
  gap: 0.5rem;
  align-items: center;
  overflow-x: auto;
  scrollbar-width: none;
}

.main-nav::-webkit-scrollbar {
  display: none;
}

.nav-link {
  background: transparent;
  border: none;
  font-size: 0.95rem;
  font-weight: 600;
  color: var(--text-muted);
  cursor: pointer;
  padding: 0.45rem 0.85rem;
  border-radius: 8px;
  white-space: nowrap;
  transition: all 0.2s ease;
}

.nav-link:hover {
  color: var(--primary-color);
  background: rgba(23, 93, 82, 0.05);
}

.nav-link.active {
  color: var(--primary-color);
  background: rgba(23, 93, 82, 0.12);
  font-weight: 700;
}



@media (max-width: 768px) {
  .app-header {
    padding: 0 0.75rem;
    gap: 0.5rem;
  }
  .main-nav {
    max-width: 100%;
  }
  .nav-link {
    font-size: 0.85rem;
    padding: 0.35rem 0.6rem;
  }

  .global-scroll-top-btn {
    bottom: 20px;
    right: 20px;
    width: 44px;
    height: 44px;
    font-size: 1.3rem;
  }
}

/* Global Return to Top Button (Fixed Bottom-Right) */
.global-scroll-top-btn {
  position: fixed;
  bottom: 24px;
  right: 24px;
  width: 50px;
  height: 50px;
  border-radius: 50%;
  background: var(--primary-color, #175d52);
  background: linear-gradient(135deg, #175d52 0%, #11463e 100%);
  color: #ffffff;
  border: 2px solid #ffffff;
  font-size: 1.5rem;
  font-weight: 700;
  cursor: pointer;
  box-shadow: 0 4px 14px rgba(23, 93, 82, 0.35);
  display: flex;
  align-items: center;
  justify-content: center;
  transition: transform 0.2s ease, box-shadow 0.2s ease, background 0.2s ease;
  z-index: 9999;
}

.global-scroll-top-btn:hover {
  transform: translateY(-3px) scale(1.05);
  box-shadow: 0 6px 20px rgba(23, 93, 82, 0.45);
  background: #11463e;
}

.global-scroll-top-btn:focus-visible {
  outline: 3px solid #f59e0b;
  outline-offset: 3px;
}

@media (prefers-reduced-motion: reduce) {
  .global-scroll-top-btn {
    transition: none;
  }
  .global-scroll-top-btn:hover {
    transform: none;
  }
}
</style>
