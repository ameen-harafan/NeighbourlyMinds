<template>
  <div class="walk-planner">
    <div class="planner-nav-bar">
      <button 
        type="button" 
        class="return-outing-btn"
        @click="navigateTo('prepare-activity')"
        aria-label="Return to Outing Preparation"
      >
        &larr; Back to Outing Preparation
      </button>
    </div>

    <div class="planner-header">
      <h1 class="planner-title">Plan a Safe Walk</h1>
      <p class="planner-subtitle">Step {{ currentStep }} of 2: {{ stepTitle }}</p>
    </div>

    <!-- Step 1: Route Planning -->
    <div v-show="currentStep === 1" class="step-container">
      <RoutingView @routeCalculated="handleRouteCalculated" />
      
      <div class="step-actions">
        <button 
          @click="nextStep" 
          :disabled="!isRouteReady"
          class="next-step-btn"
        >
          Next Step: Pocket Card &rarr;
        </button>
      </div>
    </div>

    <!-- Step 2: Pocket Card -->
    <div v-show="currentStep === 2" class="step-container">
      <button 
        @click="prevStep"
        class="back-step-btn"
      >
        &larr; Back to Route Options
      </button>

      <PocketCardGenerator :routeStats="routeStats" />

      <div class="finish-walk-row">
        <button 
          type="button" 
          class="return-outing-btn"
          @click="navigateTo('prepare-activity')"
        >
          &larr; Return to Outing Preparation
        </button>
      </div>
    </div>
  </div>
</template>

<script>
import RoutingView from './RoutingView.vue'
import PocketCardGenerator from './PocketCardGenerator.vue'
import { outingScheduleStore } from '../store'

export default {
  name: 'WalkPlanner',
  inject: {
    navigateTo: {
      from: 'navigateTo',
      default: () => () => {}
    }
  },
  components: {
    RoutingView,
    PocketCardGenerator
  },
  data() {
    return {
      currentStep: 1,
      isRouteReady: false,
      routeStats: null
    }
  },
  mounted() {
    if (outingScheduleStore.plannerStep) {
      this.currentStep = outingScheduleStore.plannerStep;
      outingScheduleStore.plannerStep = 1;
    }
  },
  computed: {
    stepTitle() {
      return this.currentStep === 1 ? 'Choose Your Destination' : 'Print Your Pocket Support Card';
    }
  },
  methods: {
    handleRouteCalculated(stats) {
      this.isRouteReady = true;
      this.routeStats = stats;
    },
    nextStep() {
      if (this.isRouteReady) {
        this.currentStep = 2;
        window.scrollTo(0, 0);
      }
    },
    prevStep() {
      this.currentStep = 1;
    }
  }
}
</script>

<style scoped>
.walk-planner {
  max-width: 900px;
  margin: 3rem auto;
  padding: 2.5rem;
  background: white;
  border-radius: 16px;
  box-shadow: 0 10px 25px rgba(0,0,0,0.05);
  border: 2px solid #e0f2fe; /* Light blue */
}

.planner-nav-bar {
  margin-bottom: 1.25rem;
}

.return-outing-btn {
  background: #f1f5f9;
  border: 1px solid #cbd5e1;
  color: #334155;
  font-size: 0.95rem;
  font-weight: 700;
  padding: 0.5rem 1rem;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
}

.return-outing-btn:hover {
  background: #e2e8f0;
  color: #0f172a;
}

.finish-walk-row {
  margin-top: 2rem;
  padding-top: 1.5rem;
  border-top: 2px solid #f1f5f9;
  display: flex;
  justify-content: flex-start;
}

.planner-header {
  text-align: center;
  margin-bottom: 2rem;
  border-bottom: 2px solid #f1f5f9;
  padding-bottom: 1.5rem;
}

.planner-title {
  font-size: 2.2rem;
  font-weight: 800;
  color: #1c2e28;
  margin-bottom: 0.5rem;
  text-align: center;
}

.planner-subtitle {
  font-size: 1.15rem;
  color: #4b6358;
  text-align: center;
}

.step-container {
  transition: opacity 0.3s ease;
}

.step-actions {
  margin-top: 2rem;
  padding-top: 1.5rem;
  border-top: 1.5px solid #d8e5df;
  display: flex;
  justify-content: flex-end;
}

.next-step-btn {
  background: #175d52;
  color: #ffffff;
  font-size: 1.1rem;
  font-weight: 700;
  padding: 0.95rem 2rem;
  border: none;
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.2s ease;
  box-shadow: 0 2px 6px rgba(23, 93, 82, 0.2);
}

.next-step-btn:hover:not(:disabled) {
  background: #0f4038;
  transform: translateY(-1px);
  box-shadow: 0 4px 10px rgba(23, 93, 82, 0.25);
}

.next-step-btn:disabled {
  background: #a3c4bd;
  cursor: not-allowed;
  box-shadow: none;
}

.back-step-btn {
  background: transparent;
  color: #175d52;
  font-size: 1.05rem;
  font-weight: 700;
  border: none;
  cursor: pointer;
  display: flex;
  align-items: center;
  margin-bottom: 1.5rem;
  padding: 0.5rem 0.75rem;
  border-radius: 8px;
  transition: all 0.2s ease;
}

.back-step-btn:hover {
  background: #eef6f3;
  color: #0f4038;
}
</style>
