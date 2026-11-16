<template>
  <div class="pocket-card-generator">
    <div class="card-header">
      <svg class="header-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 17h2a2 2 0 002-2v-4a2 2 0 00-2-2H5a2 2 0 00-2 2v4a2 2 0 002 2h2m2 4h6a2 2 0 002-2v-4a2 2 0 00-2-2H9a2 2 0 00-2 2v4a2 2 0 002 2zm8-12V5a2 2 0 00-2-2H9a2 2 0 00-2 2v4h10z"></path></svg>
      <h2>Pocket Support Card Details</h2>
    </div>
    <p class="card-description">
      Compile your saved landmark checklist and support badges into a high-contrast card. Fold it on the yellow lines and carry it in a pocket. No map is printed.
    </p>

    <!-- Outing & Sensory Conditions Summary -->
    <div class="sensory-summary-card" v-if="hasSensorySummary">
      <div class="summary-header">
        <svg class="summary-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
        <span class="summary-badge">Planned Outing & Sensory Timing</span>
      </div>
      <div class="summary-grid">
        <div class="summary-item" v-if="destination">
          <span class="summary-label">Destination</span>
          <strong class="summary-value">{{ destination }}</strong>
        </div>
        <div class="summary-item" v-if="plannedTiming">
          <span class="summary-label">Chosen Walk Time</span>
          <strong class="summary-value highlight-time">{{ plannedTiming }}</strong>
        </div>
        <div class="summary-item">
          <span class="summary-label">Sound Environment</span>
          <strong class="summary-value">
            <template v-if="noiseLevel || decibels">
              {{ noiseLevel || 'Low' }} Noise ({{ decibels ? decibels + ' dB' : 'Calm' }})
            </template>
            <template v-else>
              Standard daytime baseline
            </template>
          </strong>
        </div>
        <div class="summary-item">
          <span class="summary-label">Footpath Traffic</span>
          <strong class="summary-value">
            <template v-if="crowdLevel || pedestrianCount">
              {{ crowdLevel || 'Light' }} Crowds (~{{ pedestrianCount ? pedestrianCount + ' people/hr' : 'Quiet' }})
            </template>
            <template v-else>
              Normal daytime flow
            </template>
          </strong>
        </div>
      </div>
      <!-- <p class="summary-note">
        This sensory timing information will be printed on Panel 4 of your physical pocket card.
      </p> -->
    </div>

    <div class="form-container">
      <div class="input-group">
        <label for="emergency-contact">Emergency Contact Name & Number</label>
        <input id="emergency-contact" aria-required="true" v-model="emergencyContact" type="text" placeholder="e.g., Jane Doe - 0400 123 456" />
      </div>
      <div class="input-group">
        <label>Support badges to print</label>
        <div class="badges-container">
          <label class="badge-option" :class="{ selected: selectedBadges.includes('speak-slowly') }">
            <input type="checkbox" value="speak-slowly" :checked="selectedBadges.includes('speak-slowly')" @change="toggleBadge('speak-slowly')" />
            <img src="/badges/speak-slowly.jpg" alt="Speak slowly" />
            <span>Speak slowly</span>
          </label>
          <label class="badge-option" :class="{ selected: selectedBadges.includes('need-help') }">
            <input type="checkbox" value="need-help" :checked="selectedBadges.includes('need-help')" @change="toggleBadge('need-help')" />
            <img src="/badges/need-help.jpg" alt="I need help finding my way" />
            <span>I need help</span>
          </label>
          <label class="badge-option" :class="{ selected: selectedBadges.includes('disoriented') }">
            <input type="checkbox" value="disoriented" :checked="selectedBadges.includes('disoriented')" @change="toggleBadge('disoriented')" />
            <img src="/badges/disoriented.svg" alt="Disoriented" />
            <span>Disoriented</span>
          </label>
        </div>
      </div>
    </div>

    <div class="actions-container">
      <button 
        @click="generateCard" 
        aria-label="Compile Pocket Card"
        class="download-btn"
        :disabled="loading"
      >
        <svg v-if="!loading" class="btn-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"></path></svg>
        <svg v-else class="btn-icon animate-spin" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
        </svg>
        <span>{{ loading ? 'Compiling pocket card...' : 'Compile Pocket Card' }}</span>
      </button>
    </div>
  </div>
</template>

<script>
import { outingScheduleStore } from '../store'

export default {
  name: 'PocketCardGenerator',
  props: {
    routeStats: {
      type: Object,
      default: () => null
    }
  },
  data() {
    return {
      emergencyContact: '',
      conditions: 'Early-stage dementia',
      selectedBadges: [],
      loading: false
    }
  },
  computed: {
    destination() {
      return outingScheduleStore.destination || ''
    },
    plannedTiming() {
      if (outingScheduleStore.recommendedWindow) {
        return `${outingScheduleStore.selectedDay || 'Daytime'}, ${outingScheduleStore.recommendedWindow}`
      }
      return ''
    },
    noiseLevel() {
      return outingScheduleStore.noiseLevel || ''
    },
    decibels() {
      return outingScheduleStore.decibels ? Number(outingScheduleStore.decibels).toFixed(0) : null
    },
    crowdLevel() {
      return outingScheduleStore.crowdLevel || ''
    },
    pedestrianCount() {
      return outingScheduleStore.pedestrianCount ? Math.round(Number(outingScheduleStore.pedestrianCount)) : null
    },
    hasSensorySummary() {
      return Boolean(this.destination || this.plannedTiming || this.noiseLevel)
    },
    savedChecklist() {
      if (this.routeStats && this.routeStats.landmarks) return this.routeStats;
      try {
        const saved = localStorage.getItem('neighborly-saved-checklist');
        return saved ? JSON.parse(saved) : null;
      } catch {
        return null;
      }
    }
  },
  methods: {
    toggleBadge(id) {
      if (this.selectedBadges.includes(id)) {
        this.selectedBadges = this.selectedBadges.filter((badge) => badge !== id);
      } else {
        this.selectedBadges = [...this.selectedBadges, id];
      }
    },
    async generateCard() {
      this.loading = true;
      try {
        const checklist = this.savedChecklist;
        const shade = checklist ? Number(checklist.shade_percentage) || 0 : 0;
        const benches = checklist ? Number(checklist.bench_count) || 0 : 0;
        const instructions = `Straight path. Shade ${shade.toFixed(1)}%. Park benches ${benches}.`;

        const response = await fetch('/api/pdf/pocket-card', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            routeId: 'straight-path',
            destination: this.destination,
            plannedTiming: this.plannedTiming,
            noiseLevel: this.noiseLevel,
            decibels: this.decibels,
            crowdLevel: this.crowdLevel,
            pedestrianCount: this.pedestrianCount,
            emergencyContact: this.emergencyContact,
            conditions: this.conditions,
            instructions,
            landmarks: checklist ? checklist.landmarks : [],
            badges: this.selectedBadges,
            shadePercentage: shade,
            benchCount: benches
          })
        });

        if (!response.ok) throw new Error('Failed to generate PDF');

        // Trigger download
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'Pocket-Support-Card.pdf';
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        a.remove();
      } catch (error) {
        console.error("Error generating card:", error);
        alert("Failed to generate PDF pocket card.");
      } finally {
        this.loading = false;
      }
    }
  }
}
</script>

<style scoped>
.pocket-card-generator {
  padding: 2rem;
  background: #f8fafc;
  border-radius: 12px;
  border-left: 6px solid #3b82f6;
  margin-top: 1rem;
}

.card-header {
  display: flex;
  align-items: center;
  margin-bottom: 1.5rem;
}

.header-icon {
  width: 2.5rem;
  height: 2.5rem;
  color: #2563eb;
  margin-right: 1rem;
}

.card-header h2 {
  font-size: 2.25rem;
  font-weight: 800;
  color: #0f172a;
  margin: 0;
}

.card-description {
  font-size: 1.25rem;
  color: #334155;
  margin-bottom: 2rem;
  line-height: 1.6;
}

.sensory-summary-card {
  background: #ffffff;
  border: 2px solid #93c5fd;
  border-radius: 10px;
  padding: 1.25rem 1.5rem;
  margin-bottom: 2rem;
  box-shadow: 0 2px 4px rgba(59, 130, 246, 0.08);
}

.summary-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 1rem;
}

.summary-icon {
  width: 1.5rem;
  height: 1.5rem;
  color: #2563eb;
}

.summary-badge {
  font-size: 0.95rem;
  font-weight: 800;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: #1d4ed8;
  background: #eff6ff;
  padding: 0.25rem 0.6rem;
  border-radius: 6px;
  border: 1px solid #bfdbfe;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
}

.summary-item {
  display: flex;
  flex-direction: column;
  background: #f8fafc;
  padding: 0.75rem 1rem;
  border-radius: 8px;
  border: 1px solid #e2e8f0;
}

.summary-label {
  font-size: 0.85rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: #64748b;
  margin-bottom: 0.25rem;
}

.summary-value {
  font-size: 1.1rem;
  font-weight: 800;
  color: #0f172a;
}

.summary-value.highlight-time {
  color: #1d4ed8;
}

.summary-note {
  margin-top: 0.75rem;
  font-size: 0.95rem;
  color: #475569;
  font-style: italic;
}

.form-container {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  margin-bottom: 2rem;
}

.input-group label {
  display: block;
  font-weight: 800;
  font-size: 1.25rem;
  color: #1e293b;
  margin-bottom: 0.75rem;
}

.input-group input,
.input-group textarea {
  width: 100%;
  border: 2px solid #cbd5e1;
  border-radius: 8px;
  padding: 1rem;
  font-size: 1.15rem;
  color: #334155;
  font-family: inherit;
  transition: border-color 0.2s, box-shadow 0.2s;
}

.input-group input:focus,
.input-group textarea:focus {
  outline: none;
  border-color: #3b82f6;
  box-shadow: 0 0 0 4px rgba(59, 130, 246, 0.2);
}

.actions-container {
  display: flex;
  align-items: center;
}

.download-btn {
  flex: 1;
  display: flex;
  justify-content: center;
  align-items: center;
  background: #16a34a;
  color: white;
  font-size: 1.5rem;
  font-weight: 800;
  padding: 1.25rem 2rem;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.3s ease;
  box-shadow: 0 4px 6px rgba(22, 163, 74, 0.2);
}

.download-btn:hover:not(:disabled) {
  background: #15803d;
  transform: translateY(-2px);
  box-shadow: 0 8px 15px rgba(22, 163, 74, 0.3);
}

.download-btn:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.btn-icon {
  width: 2rem;
  height: 2rem;
  margin-right: 0.75rem;
}

.badges-container {
  display: flex;
  flex-wrap: wrap;
  gap: 1rem;
  margin-top: 0.5rem;
}

.badge-option {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
  padding: 1rem;
  border: 2px solid #cbd5e1;
  border-radius: 8px;
  cursor: pointer;
  background: white;
  transition: all 0.2s ease;
}

.badge-option input {
  display: none;
}

.badge-option img {
  width: 80px;
  height: 80px;
  object-fit: contain;
  border-radius: 50%;
}

.badge-option span {
  font-weight: 600;
  color: #334155;
}

.badge-option.selected {
  border-color: #3b82f6;
  background: #eff6ff;
  box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.2);
}

.animate-spin {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.opacity-25 { opacity: 0.25; }
.opacity-75 { opacity: 0.75; }
</style>
