<script setup lang="ts">
import { ref, computed, onMounted, inject, onUnmounted } from "vue";
import type { ViewState } from "../App.vue";
import heroImage from '../assets/landing_hero_cartoon.jpg';
import heroCopy from '../data/hero_copy.json';
import VisualIntroPage from './VisualIntroPage.vue';

const navigateTo = inject<(view: ViewState) => void>("navigateTo", () => {});

// Demographic Data State
const dementiaEstimate = ref<number | null>(null);
const councils = ref<string[]>([]);
const councilCodes = new Map<string, number>();
const dataError = ref("");
let estimateRequest = 0;
const selectedCouncil = ref("Frankston");

// Custom Dropdown State
const isOpen = ref(false);
const searchQuery = ref("");
const dropdownRef = ref<HTMLElement | null>(null);

const filteredCouncils = computed(() => {
  if (!searchQuery.value) return councils.value;
  const q = searchQuery.value.toLowerCase();
  return councils.value.filter(c => c.toLowerCase().includes(q));
});

const selectCouncil = (c: string) => {
  selectedCouncil.value = c;
  isOpen.value = false;
  searchQuery.value = "";
  fetchEstimate();
};

const handleClickOutside = (event: MouseEvent) => {
  if (dropdownRef.value && !dropdownRef.value.contains(event.target as Node)) {
    isOpen.value = false;
  }
};

const fetchEstimate = async () => {
  const request = ++estimateRequest;
  dementiaEstimate.value = null;
  try {
    const response = await fetch(`/api/councils/${encodeURIComponent(selectedCouncil.value)}/dementia`);
    if (response.ok) {
      const data = await response.json();
      dementiaEstimate.value = data.rounded_estimate;
    }
  } catch (error) {
    console.error("Failed to fetch estimate", error);
  }
};

onMounted(async () => {
  document.addEventListener('mousedown', handleClickOutside);
  try {
    const response = await fetch("/api/councils");
    if (response.ok) {
      const councilData = await response.json();
      councils.value = councilData.map((row: any) => row.lga_name);
    }
  } catch (error) {
    console.error("Failed to fetch councils", error);
  }

  await fetchEstimate();
});

onUnmounted(() => {
  document.removeEventListener('mousedown', handleClickOutside);
});

const scrollToData = () => {
  const dataSection = document.getElementById("mission-section");
  if (dataSection) {
    dataSection.scrollIntoView({ behavior: "smooth" });
  }
};

const handleDashboard = () => {
  navigateTo("explore");
};
</script>

<template>
  <div class="landing-page">
    <!-- Hero Section -->
    <section class="hero-section" aria-label="Introduction">
      <div class="hero-container">
        <!-- Left: Text Content -->
        <div class="hero-content">
          <div class="hero-badge" aria-hidden="true">{{ heroCopy.hero.secondaryBadge }}</div>
          <h1 class="main-title">{{ heroCopy.hero.headline }}</h1>
          <p class="subtitle">
            {{ heroCopy.hero.subtitle }}
          </p>

          <div class="hero-actions">
            <button 
              type="button" 
              class="primary-btn hero-primary-cta" 
              @click="scrollToData"
              :aria-label="heroCopy.hero.primaryCta.ariaLabel"
            >
              {{ heroCopy.hero.primaryCta.text }} &darr;
            </button>
          </div>
        </div>
        
        <!-- Right: Image -->
        <div class="hero-image-wrapper">
          <img :src="heroImage" alt="Friendly older adult in an accessible living room" class="hero-image" />
        </div>
      </div>
    </section>

    <!-- Community Context & Reassurance Section (Balanced Spacing) -->
    <section class="reassurance-section" aria-label="Community Context">
      <div class="reassurance-container">
        <div class="demo-card">
          <span class="overline">{{ heroCopy.demographics.overline }}</span>
          <div class="lga-selection">
            <span class="lga-text">{{ heroCopy.demographics.intro }}</span>
            
            <!-- Custom Accessible Dropdown -->
            <div class="custom-select-wrapper" ref="dropdownRef">
              <button 
                type="button"
                class="custom-selected-value accessible-select" 
                @click="isOpen = !isOpen"
                aria-haspopup="listbox"
                :aria-expanded="isOpen"
              >
                {{ selectedCouncil || 'Select an LGA' }}
                <span class="dropdown-icon" :class="{ 'open': isOpen }" aria-hidden="true">▼</span>
              </button>
              
              <div v-show="isOpen" class="dropdown-list-container">
                <div class="dropdown-search">
                  <input 
                    type="text" 
                    v-model="searchQuery" 
                    placeholder="Search regions..." 
                    class="search-input"
                    @click.stop
                  />
                </div>
                <ul class="dropdown-list" role="listbox">
                  <li 
                    v-for="c in filteredCouncils" 
                    :key="c" 
                    class="dropdown-item" 
                    :class="{ 'selected': c === selectedCouncil }"
                    @click="selectCouncil(c)"
                    role="option"
                    :aria-selected="c === selectedCouncil"
                  >
                    {{ c }}
                  </li>
                  <li v-if="filteredCouncils.length === 0" class="dropdown-empty">
                    No matches found.
                  </li>
                </ul>
              </div>
            </div>
            <!-- End Custom Dropdown -->

            <span class="lga-text">,</span>
          </div>
          
          <p v-if="dataError" role="alert">{{ dataError }}</p>
          <h3 v-else class="estimate-heading">
            an estimated 
            <span class="highlight-number">
              {{ dementiaEstimate !== null ? dementiaEstimate.toLocaleString() : "..." }}
            </span> 
            {{ heroCopy.demographics.outro }}
          </h3>
          <p class="demo-description">
            {{ heroCopy.demographics.description }}
          </p>
        </div>
      </div>
    </section>

    <!-- Visual Interactive Simulation Section -->
    <section id="visual-intro-section" class="landing-visual-intro-section" aria-label="Visual Interactive Simulation">
      <VisualIntroPage />
    </section>

    <!-- Main Content Section: 3 Gateways -->
    <section id="mission-section" class="main-content-section" aria-label="Explore NeighbourlyMinds Services">
      <div class="content-container">
        
        <div class="mission-block">
          <h2>{{ heroCopy.gateways.title }}</h2>
          <p class="mission-intro">
            {{ heroCopy.gateways.intro }}
          </p>

          <div class="gateway-cards-grid">
            <!-- 1. Indoor Room Guides -->
            <div 
              class="gateway-card" 
              @click="navigateTo('explore')" 
              role="button" 
              tabindex="0" 
              aria-label="Open Indoor Room Guides"
              @keypress.enter="navigateTo('explore')"
            >
              <div class="gateway-icon-badge" aria-hidden="true">🛋️</div>
              <span class="gateway-tag">INDOOR SPACES</span>
              <h3 class="gateway-title">Indoor Room Guides</h3>
              <p class="gateway-desc">
                Discover high-contrast bathroom and kitchen adjustments to eliminate hidden barriers and make everyday objects clear.
              </p>
              <div class="gateway-action">
                <span class="gateway-btn">Explore Room Guides</span>
              </div>
            </div>

            <!-- 2. Scan a Room & Public Corridors for Hazards (Second) -->
            <div 
              class="gateway-card" 
              @click="navigateTo('auditor')" 
              role="button" 
              tabindex="0" 
              aria-label="Open Environment & Public Corridor Auditor"
              @keypress.enter="navigateTo('auditor')"
            >
              <div class="gateway-icon-badge" aria-hidden="true">🏛️</div>
              <span class="gateway-tag">CIVIC AUDIT & SCAN</span>
              <h3 class="gateway-title">Audit Spaces & Corridors</h3>
              <p class="gateway-desc">
                Audit photos of confusing public hallways or rooms for doorway contrast and glare barriers, and automatically draft accessibility feedback to your local council.
              </p>
              <div class="gateway-action">
                <span class="gateway-btn">Open Environment Auditor</span>
              </div>
            </div>

            <!-- 3. Plan a Stress-Free Outing (Last) -->
            <div 
              class="gateway-card" 
              @click="navigateTo('prepare-activity')" 
              role="button" 
              tabindex="0" 
              aria-label="Start Outing Preparation"
              @keypress.enter="navigateTo('prepare-activity')"
            >
              <div class="gateway-icon-badge" aria-hidden="true">🚶</div>
              <span class="gateway-tag">OUTINGS & WALKS</span>
              <h3 class="gateway-title">Plan a Stress-Free Outing</h3>
              <p class="gateway-desc">
                Find quiet daytime hours (9 AM – 5 PM), preview familiar landmarks along the way, and generate a printable pocket support card.
              </p>
              <div class="gateway-action">
                <span class="gateway-btn">Start Outing Prep</span>
              </div>
            </div>
          </div>
        </div>

      </div>
    </section>
  </div>
</template>

<style scoped>
.landing-page {
  flex: 1;
  display: flex;
  flex-direction: column;
  width: 100%;
  background-color: var(--bg-main, #f7f9f7);
}

/* --- Hero Section --- */
.hero-section {
  background-color: var(--color-bg-sage, #f4f6f5);
  padding: 4rem 2rem;
  display: flex;
  justify-content: center;
}

.hero-container {
  max-width: 1200px;
  width: 100%;
  display: flex;
  align-items: stretch;
  gap: 4rem;
}

.hero-content {
  flex: 1;
  animation: fadeUp 0.8s ease-out;
}

.hero-image-wrapper {
  flex: 1;
  display: flex;
}

.hero-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
  border-radius: 20px;
  box-shadow: 0 10px 30px rgba(0,0,0,0.05);
}

.hero-badge {
  display: inline-block;
  font-size: 0.95rem;
  font-weight: 800;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--color-primary);
  background: rgba(23, 93, 82, 0.08);
  border: 1px solid rgba(23, 93, 82, 0.2);
  padding: 0.4rem 1rem;
  border-radius: 999px;
  margin-bottom: 1.25rem;
}

.main-title {
  font-size: clamp(2.5rem, 4vw, 3.5rem);
  font-weight: 900;
  line-height: 1.15;
  color: var(--color-text-main);
  margin: 0 0 1.25rem 0;
  letter-spacing: -1px;
}

.subtitle {
  font-size: 1.15rem;
  line-height: 1.6;
  color: var(--color-text-muted);
  margin: 0 0 2rem 0;
}

.hero-actions {
  display: flex;
  gap: 1rem;
  flex-wrap: wrap;
  margin-top: 2rem;
}

.primary-btn, .secondary-btn {
  border-radius: 12px;
  padding: 1rem 1.5rem;
  font-size: 1rem;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.2s ease;
}

.primary-btn {
  background-color: var(--color-primary, #175d52);
  color: white;
  border: none;
  box-shadow: 0 4px 15px rgba(23, 93, 82, 0.2);
}

.primary-btn:hover {
  background-color: #124b42;
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(23, 93, 82, 0.3);
}

.secondary-btn {
  background-color: transparent;
  color: var(--color-text-main);
  border: 2px solid #d1ddd7;
}

.secondary-btn:hover {
  background-color: rgba(23,93,82,0.05);
  border-color: var(--color-primary);
}

/* --- Main Content Section --- */
.main-content-section {
  padding: 4rem 2rem;
  display: flex;
  justify-content: center;
}

.content-container {
  max-width: 1000px;
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 4rem;
}

.mission-block {
  text-align: center;
  max-width: 800px;
  margin: 0 auto;
}

.mission-block h2 {
  font-size: 2rem;
  font-weight: 800;
  color: var(--color-text-main);
  margin-bottom: 1rem;
}

.mission-intro {
  font-size: 1.15rem;
  color: var(--color-text-muted);
  line-height: 1.6;
  margin-bottom: 2rem;
  max-width: 850px;
}

.gateway-cards-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 2rem;
  margin-top: 2.5rem;
  text-align: left;
}

@media (max-width: 992px) {
  .gateway-cards-grid {
    grid-template-columns: 1fr;
  }
}

.gateway-card {
  background: white;
  border-radius: 20px;
  padding: 2.25rem 2rem;
  border: 1.5px solid var(--color-border);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.04);
  transition: all 0.25s ease;
  display: flex;
  flex-direction: column;
  cursor: pointer;
  position: relative;
}

.gateway-card:hover {
  transform: translateY(-6px);
  border-color: var(--color-primary);
  box-shadow: 0 12px 28px rgba(23, 93, 82, 0.12);
}

.gateway-card:focus-visible {
  outline: 3px solid var(--color-primary);
  outline-offset: 4px;
}

.gateway-icon-badge {
  font-size: 2.25rem;
  width: 56px;
  height: 56px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-bg-sage, #f4f6f5);
  border-radius: 14px;
  margin-bottom: 1.25rem;
}

.gateway-tag {
  display: inline-block;
  font-size: 0.75rem;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--color-primary);
  margin-bottom: 0.5rem;
}

.gateway-title {
  font-size: 1.35rem;
  font-weight: 800;
  color: var(--color-text-main);
  margin: 0 0 0.75rem 0;
  line-height: 1.3;
}

.gateway-desc {
  font-size: 1rem;
  color: var(--color-text-muted);
  line-height: 1.6;
  margin: 0 0 1.5rem 0;
  flex-grow: 1;
}

.gateway-action {
  margin-top: auto;
  padding-top: 1rem;
  border-top: 1px solid #edf2ef;
}

.gateway-btn {
  display: inline-flex;
  align-items: center;
  font-size: 1.05rem;
  font-weight: 800;
  color: var(--color-primary);
  transition: transform 0.2s ease, color 0.2s ease;
}

.gateway-card:hover .gateway-btn {
  transform: translateX(4px);
  color: var(--color-primary-hover);
}

/* --- Community Reassurance Section --- */
.reassurance-section {
  padding: 3rem 2rem 1.5rem 2rem;
  background-color: var(--bg-main, #f7f9f7);
  display: flex;
  justify-content: center;
}

.reassurance-container {
  max-width: 900px;
  width: 100%;
}

.demo-card {
  background: white;
  border: 1px solid #e5e0d8;
  border-radius: 12px;
  padding: 1.5rem 2rem;
  text-align: center;
  width: 100%;
  box-shadow: 0 4px 15px rgba(0,0,0,0.05);
  position: relative;
  z-index: 5;
}

.overline {
  display: block;
  font-size: 0.85rem;
  font-weight: 800;
  color: var(--color-primary);
  text-transform: uppercase;
  letter-spacing: 1px;
  margin-bottom: 1rem;
}

.lga-selection {
  display: flex;
  align-items: baseline;
  justify-content: center;
  gap: 0.75rem;
  margin-bottom: 0.5rem;
  flex-wrap: wrap;
}

.lga-text {
  font-size: 1.5rem;
  font-weight: 800;
  color: var(--color-text-main);
}

/* --- Custom Dropdown Styles --- */
.custom-select-wrapper {
  position: relative;
  display: inline-block;
  min-width: 240px;
  z-index: 10;
}

.custom-selected-value.accessible-select {
  font-family: inherit;
  font-size: 1.5rem;
  font-weight: 800;
  color: var(--color-primary);
  background: transparent;
  border: none;
  border-bottom: 2px solid var(--color-primary);
  padding: 0 2rem 0 0.5rem;
  cursor: pointer;
  appearance: none;
  outline: none;
  width: 100%;
  text-align: left;
  display: inline-flex;
  align-items: center;
  position: relative;
}

.custom-selected-value.accessible-select:focus-visible {
  outline: 3px solid var(--color-primary);
  outline-offset: 4px;
  border-radius: 4px;
}

.dropdown-icon {
  font-size: 0.9rem;
  color: var(--color-primary);
  position: absolute;
  right: 0.5rem;
  top: 50%;
  transform: translateY(-50%);
  pointer-events: none;
  transition: transform 0.2s ease;
}

.dropdown-icon.open {
  transform: translateY(-50%) rotate(180deg);
}

.dropdown-list-container {
  position: absolute;
  top: calc(100% + 8px);
  left: 50%;
  transform: translateX(-50%);
  width: 280px;
  background: white;
  border-radius: 12px;
  box-shadow: 0 10px 40px rgba(0,0,0,0.15);
  border: 1px solid #e5e0d8;
  z-index: 100;
  overflow: hidden;
  animation: fadeUp 0.2s ease-out;
}

.dropdown-search {
  padding: 0.75rem;
  border-bottom: 1px solid #e5e0d8;
  background: #fbfcfb;
}

.search-input {
  width: 100%;
  padding: 0.6rem 0.8rem;
  border: 1px solid #d1ddd7;
  border-radius: 8px;
  font-size: 0.95rem;
  outline: none;
  transition: border-color 0.2s;
  box-sizing: border-box;
  font-family: inherit;
}

.search-input:focus {
  border-color: var(--color-primary);
}

.dropdown-list {
  list-style: none;
  margin: 0;
  padding: 0;
  max-height: 250px;
  overflow-y: auto;
}

.dropdown-list::-webkit-scrollbar {
  width: 6px;
}
.dropdown-list::-webkit-scrollbar-track {
  background: transparent;
}
.dropdown-list::-webkit-scrollbar-thumb {
  background: #d1ddd7;
  border-radius: 4px;
}

.dropdown-item {
  padding: 0.75rem 1rem;
  font-size: 1rem;
  color: var(--color-text-main);
  cursor: pointer;
  transition: background-color 0.2s;
  text-align: left;
}

.dropdown-item:hover {
  background-color: #f4f6f5;
}

.dropdown-item.selected {
  background-color: rgba(23, 93, 82, 0.05);
  color: var(--color-primary);
  font-weight: 700;
}

.dropdown-empty {
  padding: 1rem;
  color: var(--color-text-muted);
  font-style: italic;
  font-size: 0.95rem;
}

/* --- End Dropdown Styles --- */

.estimate-heading {
  font-size: 1.15rem;
  font-weight: 800;
  color: var(--color-text-main);
  margin-bottom: 0;
  line-height: 1.4;
}

.highlight-number {
  color: var(--color-primary);
  font-size: 1.5rem;
}

/* --- Utilities --- */

@keyframes fadeUp {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

@media (max-width: 900px) {
  .hero-container {
    flex-direction: column-reverse;
    text-align: center;
    gap: 2rem;
  }
  .hero-actions {
    justify-content: center;
  }
  .how-it-works-row {
    grid-template-columns: 1fr;
  }
}

.demo-description {
  font-size: 0.95rem;
  color: var(--color-text-muted);
  line-height: 1.5;
  margin: 1rem 0 0 0;
}

.landing-visual-intro-section {
  width: 100%;
  position: relative;
  background: #f8fafc;
}
</style>
