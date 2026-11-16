<script setup lang="ts">
import { ref, onMounted, onUnmounted, inject } from "vue";
import type { ViewState } from '../App.vue'
import ActionCard from "./ActionCard.vue";
import whiteOnWhiteImg from '../assets/white_on_white.jpg';
import iconExplore from '../assets/icon_explore.jpg';
import iconIdentify from '../assets/icon_identify.jpg';
import iconAdapt from '../assets/icon_adapt.jpg';

const navigateTo = inject<(view: ViewState) => void>('navigateTo', () => {})

const scrollContainer = ref<HTMLElement | null>(null);
const cardRefs = ref<HTMLElement[]>([]);
const activeIndex = ref(0);

const environments = [
  {
    title: "Sample Bathroom Guide",
    description: "Contrast, lighting, fixtures, glare and decision points.",
    buttonText: "Open interactive guide",
    buttonStyle: "solid",
    icon: "🛁",
  },
  {
    title: "Sample Kitchen Guide",
    description: "Familiar zones, clutter, surfaces and object distinction.",
    buttonText: "Open interactive guide",
    buttonStyle: "solid",
    icon: "🍽️",
  },
  {
    title: "Saved Room Layouts",
    description: "Review and manage your saved high-contrast color choices.",
    buttonText: "View saved layouts",
    buttonStyle: "solid",
    icon: "💾",
  },
  /*
  {
    title: "Entrance",
    description: "Thresholds, entrance clarity and familiar cues.",
    buttonText: "See build note",
    buttonStyle: "outline",
    icon: "🚪",
  },
  {
    title: "Hallway",
    description: "Similar doors, signs and ambiguous decision points.",
    buttonText: "See build note",
    buttonStyle: "outline",
    icon: "↔️",
  },
  {
    title: "Community facility",
    description: "Corridor wayfinding — what went wrong?",
    buttonText: "Open corridor sim",
    buttonStyle: "solid",
    icon: "🏛️",
  },
  */
] as const;

const scrollLeft = () => {
  if (scrollContainer.value && cardRefs.value.length > 0) {
    const firstCard = cardRefs.value[0];
    if (firstCard) {
      const cardWidth = firstCard.offsetWidth + 24; // width + gap
      scrollContainer.value?.scrollBy({ left: -cardWidth, behavior: "smooth" });
    }
  }
};

const scrollRight = () => {
  if (scrollContainer.value && cardRefs.value.length > 0) {
    const firstCard = cardRefs.value[0];
    if (firstCard) {
      const cardWidth = firstCard.offsetWidth + 24;
      scrollContainer.value?.scrollBy({ left: cardWidth, behavior: "smooth" });
    }
  }
};

const handleScroll = () => {
  if (!scrollContainer.value) return;

  const containerCenter =
    scrollContainer.value.scrollLeft + scrollContainer.value.clientWidth / 2;

  let minDistance = Infinity;
  let newActiveIndex = 0;

  cardRefs.value.forEach((card, index) => {
    if (!card) return;
    const cardCenter =
      card.offsetLeft +
      card.clientWidth / 2 -
      scrollContainer.value!.offsetLeft;
    const distance = Math.abs(containerCenter - cardCenter);

    if (distance < minDistance) {
      minDistance = distance;
      newActiveIndex = index;
    }
  });

  activeIndex.value = newActiveIndex;
};

onMounted(() => {
  if (scrollContainer.value) {
    scrollContainer.value.addEventListener("scroll", handleScroll);
    setTimeout(handleScroll, 100);
  }
});

onUnmounted(() => {
  if (scrollContainer.value) {
    scrollContainer.value.removeEventListener("scroll", handleScroll);
  }
});
</script>

<template>
  <div class="explore-page">
    <header class="page-header">
      <div class="header-top-row">
        <div>
          <h1 class="page-title">Explore Guides</h1>
          <p class="page-subtitle">
            Find hidden barriers and test adjustments to make spaces easier to navigate.
          </p>
        </div>
        <div class="quick-jump-pills" role="navigation" aria-label="Quick jump to room guides">
          <button type="button" class="pill-btn" aria-label="Open Bathroom guide" @click="navigateTo('bathroom-task')">Bathroom</button>
          <button type="button" class="pill-btn" aria-label="Open Kitchen guide" @click="navigateTo('kitchen-task')">Kitchen</button>
          <button type="button" class="pill-btn" aria-label="Open Saved Layouts" @click="navigateTo('saved-layouts')">Saved Layouts</button>
        </div>
      </div>
    </header>

    <section class="explore-section">
      <div class="white-on-white-example">
        <div class="example-text">
          <h3>The "White on White" Barrier</h3>
          <p>
            When objects like light switches or doors match the color of their surroundings, they can become invisible to someone experiencing cognitive changes. 
            <strong>Our interactive guides help you identify and fix these hidden barriers.</strong>
          </p>
        </div>
        <div class="example-image">
          <img :src="whiteOnWhiteImg" alt="White light switch on a white wall demonstrating poor contrast" />
        </div>
      </div>
    </section>

    <section class="explore-section">
      <h2 class="section-title">How it works</h2>
      <div class="card-grid cols-3">
        <div class="illustrated-step-card">
          <img :src="iconExplore" alt="" aria-hidden="true" class="step-icon" />
          <h3 class="step-title">1. Explore Spaces</h3>
          <p class="step-desc">Look around virtual rooms like the kitchen and bathroom.</p>
        </div>

        <div class="illustrated-step-card">
          <img :src="iconIdentify" alt="" aria-hidden="true" class="step-icon" />
          <h3 class="step-title">2. Identify Barriers</h3>
          <p class="step-desc">Find objects like switches or rails that blend into their surroundings.</p>
        </div>

        <div class="illustrated-step-card">
          <img :src="iconAdapt" alt="" aria-hidden="true" class="step-icon" />
          <h3 class="step-title">3. Adapt & Modify</h3>
          <p class="step-desc">Test high-contrast colors, lighting, and save your customized layout.</p>
        </div>
      </div>
    </section>

    <section class="explore-section">
      <h2 class="section-title">Environment library</h2>
      <div class="card-grid cols-3">
        <div
          v-for="(env, index) in environments"
          :key="env.title"
          :ref="(el) => { if (el) cardRefs[index] = el as HTMLElement }"
          class="card-wrapper"
        >
          <ActionCard
            :title="env.title"
            :description="env.description"
            :buttonText="env.buttonText"
            :buttonStyle="env.buttonStyle"
            @actionClick="
              env.title === 'Sample Bathroom Guide' ? navigateTo('bathroom-task') : 
              env.title === 'Sample Kitchen Guide' ? navigateTo('kitchen-task') : 
              env.title === 'Saved Room Layouts' ? navigateTo('saved-layouts') : null
            "
          >
            <template #icon>{{ env.icon }}</template>
          </ActionCard>
        </div>
      </div>
    </section>

    <!-- Practise everyday activities (disabled for Iteration 1) -->
    <!--
    <section class="explore-section">
      <h2 class="section-title">Practise everyday activities</h2>
      <div class="card-grid cols-2">
        <ActionCard
          title="Library visit task"
          description="Environmental surprise during a familiar outing."
          buttonText="Start library task"
          buttonStyle="solid"
          @actionClick="navigateTo('task-rehearsal')"
        >
          <template #icon>📚</template>
        </ActionCard>

        <ActionCard
          title="Grocery shopping task"
          description="Product moved, competing signs, changed checkout."
          buttonText="Start grocery task"
          buttonStyle="outline"
          @actionClick="navigateTo('task-rehearsal')"
        >
          <template #icon>🛒</template>
        </ActionCard>
      </div>
    </section>
    -->
  </div>
</template>

<style scoped>
.explore-page {
  max-width: 900px;
  margin: 0 auto;
  padding: 2rem 1rem 4rem 1rem;
  font-family: inherit;
  box-sizing: border-box;
}

.page-header {
  margin-bottom: 2rem;
}

.header-top-row {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 1.5rem;
  flex-wrap: wrap;
}

.quick-jump-pills {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
  margin-top: 0.5rem;
}

.pill-btn {
  background: white;
  border: 1px solid var(--color-border);
  color: var(--color-primary);
  padding: 0.4rem 0.9rem;
  border-radius: 99px;
  font-size: 0.9rem;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.2s ease;
  box-shadow: 0 2px 5px rgba(0,0,0,0.03);
}

.pill-btn:hover {
  background: var(--color-primary);
  color: white;
  border-color: var(--color-primary);
  transform: translateY(-1px);
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

.explore-section {
  margin-top: 3rem;
  margin-bottom: 3rem;
}

.section-title {
  font-size: 1.5rem;
  font-weight: 800;
  color: var(--color-text-main);
  margin-bottom: 1.5rem;
}

.white-on-white-example {
  display: flex;
  background: var(--color-bg-sage);
  border: 1px solid var(--color-border);
  border-radius: 16px;
  overflow: hidden;
  align-items: center;
}

.example-text {
  flex: 1;
  padding: 2rem;
}

.example-text h3 {
  margin-top: 0;
  color: var(--color-primary);
  font-size: 1.5rem;
  margin-bottom: 1rem;
}

.example-text p {
  color: var(--color-text-muted);
  line-height: 1.6;
  font-size: 1.05rem;
}

.example-image {
  flex: 1;
  min-height: 250px;
}

.example-image img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

@media (max-width: 768px) {
  .white-on-white-example {
    flex-direction: column-reverse;
  }
}

.illustrated-step-card {
  background: white;
  border-radius: 16px;
  padding: 1.75rem 1.5rem;
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.05);
  border: 1px solid var(--color-border);
  transition: transform 0.2s ease, box-shadow 0.2s ease;
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
}

.illustrated-step-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 24px rgba(23, 93, 82, 0.08);
}

.step-icon {
  width: 88px;
  height: 88px;
  object-fit: contain;
  margin-bottom: 1.25rem;
}

.step-title {
  font-size: 1.25rem;
  font-weight: 800;
  color: var(--color-text-main);
  margin: 0 0 0.5rem 0;
}

.step-desc {
  font-size: 0.95rem;
  color: var(--color-text-muted);
  line-height: 1.5;
  margin: 0;
}

.card-grid {
  display: grid;
  gap: 1.5rem;
}

.card-wrapper {
  display: flex;
  flex-direction: column;
}

.card-grid.cols-3 {
  grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
}
.card-grid.cols-2 {
  grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
}

@media (min-width: 768px) {
  .card-grid.cols-3 {
    grid-template-columns: repeat(3, 1fr);
  }
  .card-grid.cols-2 {
    grid-template-columns: repeat(2, 1fr);
  }
}

/* Carousel Styles */
.carousel-wrapper {
  position: relative;
  display: flex;
  align-items: center;
  margin: 0 2.5rem; /* Space for the arrows */
}

.carousel-btn {
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
  z-index: 10;
  background: white;
  border: 2px solid var(--color-primary);
  border-radius: 50%;
  width: 44px;
  height: 44px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);
  color: var(--color-primary);
  font-size: 1.2rem;
  font-weight: bold;
  transition: all 0.2s;
}
.carousel-btn:hover {
  background: var(--color-bg-sage);
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.15);
}
.carousel-btn.prev {
  left: -50px;
}
.carousel-btn.next {
  right: -50px;
}

.horizontal-scroll {
  display: flex;
  gap: 1.5rem;
  overflow-x: auto;
  padding: 1rem 0 2rem 0;
  scroll-snap-type: x mandatory;
  width: 100%;
  scrollbar-width: none;
}
.horizontal-scroll::-webkit-scrollbar {
  display: none;
}

.carousel-item {
  flex: 0 0 calc((100% - 3rem) / 3); /* exactly 3 cards visible on desktop */
  scroll-snap-align: center;
  transition: transform 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
}

.carousel-item.active {
  transform: scale(1.05);
  z-index: 5;
}

@media (max-width: 850px) {
  .carousel-item {
    flex: 0 0 calc((100% - 1.5rem) / 2);
  }
}

@media (max-width: 550px) {
  .carousel-item {
    flex: 0 0 85%;
  }
  .carousel-wrapper {
    margin: 0 0.5rem;
  }
  .carousel-btn {
    display: none;
  }
}
</style>
