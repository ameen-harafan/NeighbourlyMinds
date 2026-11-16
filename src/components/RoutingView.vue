<template>
  <div class="routing-view">
    <div class="routing-grid">
      <div class="controls">
        <div class="input-group">
          <label for="start-location">Starting Point</label>
          <input 
            id="start-location" 
            type="text" 
            v-model="startQuery" 
            placeholder="e.g., My Home, 123 Main St" 
            class="location-input"
          />
        </div>
        <div class="input-group">
          <label for="end-location">Destination</label>
          <input 
            id="end-location" 
            type="text" 
            v-model="endQuery" 
            placeholder="e.g., Red Brick Post Office" 
            class="location-input"
          />
        </div>
        
        <button 
          @click="handleCalculate" 
          class="calculate-btn"
          :disabled="!canCalculate"
        >
          {{ loading ? statusMessage : 'Find Straightest Path' }}
        </button>

        <div v-if="geocodeError" class="error-message">
          {{ geocodeError }}
        </div>

        <div v-if="routeStats" class="stats-panel">
          <h3>Route Comfort</h3>
          <ul>
            <li>
              <span>Tree Shade:</span> 
              <strong>{{ Number(routeStats.shade_percentage).toFixed(1) }}%</strong>
            </li>
            <li>
              <span>Resting Benches:</span> 
              <strong>{{ routeStats.bench_count }} nearby</strong>
            </li>
          </ul>
        </div>
      </div>

      <div class="map-container">
        <div v-if="!routeStats && !loading" class="map-empty">
          Type your locations and click "Find Straightest Path"
        </div>
        <div v-else-if="loading" class="map-loading">
          {{ statusMessage }}
        </div>
        <div v-else class="map-success">
          <svg class="success-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
          <h4>Straight path ready</h4>
          <p>No map. Follow the landmark checklist below.</p>
        </div>
      </div>
    </div>
    
    <div v-if="landmarks.length > 0" class="landmarks-section">
      <h3>Landmark checklist</h3>
      <div class="timeline">
        <div v-for="(landmark, index) in landmarks" :key="index" class="timeline-item">
          <div class="timeline-dot"></div>
          <div class="timeline-content">
            <span class="timeline-name">{{ landmark.instruction || landmark.landmark_name }}</span>
            <span class="timeline-distance">{{ landmarkSubtitle(landmark) }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { outingScheduleStore } from '../store'

export default {
  name: 'RoutingView',
  emits: ['routeCalculated', 'destinationChanged'],
  data() {
    return {
      startQuery: '',
      endQuery: outingScheduleStore.destination || '',
      startCoords: null,
      endCoords: null,
      loading: false,
      statusMessage: 'Calculating Safe Route...',
      geocodeError: null,
      routeStats: null,
      landmarks: []
    }
  },
  mounted() {
    if (!this.endQuery && outingScheduleStore.destination) {
      this.endQuery = outingScheduleStore.destination;
    }
    this.loadGoogleMapsScript();
  },
  computed: {
    canCalculate() {
      return this.startQuery.trim().length > 0 && this.endQuery.trim().length > 0 && !this.loading;
    }
  },
  watch: {
    startQuery() {
      this.startCoords = null;
    },
    endQuery(newVal) {
      this.endCoords = null;
      if (newVal) {
        outingScheduleStore.destination = newVal;
        this.$emit('destinationChanged', newVal);
      }
    }
  },
  methods: {
    loadGoogleMapsScript() {
      const apiKey = import.meta.env.VITE_GOOGLE_MAPS_API_KEY;
      if (!apiKey || apiKey === 'your_google_maps_api_key_here') {
        console.warn('Google Maps API key is missing or not configured in .env');
        return;
      }
      
      if (window.google && window.google.maps) {
        this.initAutocomplete();
        return;
      }

      if (document.getElementById('google-maps-script')) {
        return;
      }

      const script = document.createElement('script');
      script.id = 'google-maps-script';
      script.src = `https://maps.googleapis.com/maps/api/js?key=${apiKey}&libraries=places`;
      script.async = true;
      script.defer = true;
      script.onload = () => {
        this.initAutocomplete();
      };
      document.head.appendChild(script);
    },
    
    initAutocomplete() {
      const startInput = document.getElementById('start-location');
      const endInput = document.getElementById('end-location');
      
      const options = {
        componentRestrictions: { country: 'au' },
        fields: ['formatted_address', 'geometry', 'name'],
        bounds: new window.google.maps.LatLngBounds(
          new window.google.maps.LatLng(-38.5, 144.5), 
          new window.google.maps.LatLng(-37.5, 145.5)
        )
      };

      const startAutocomplete = new window.google.maps.places.Autocomplete(startInput, options);
      const endAutocomplete = new window.google.maps.places.Autocomplete(endInput, options);

      startAutocomplete.addListener('place_changed', () => {
        const place = startAutocomplete.getPlace();
        if (place.geometry && place.geometry.location) {
          this.startQuery = place.formatted_address || place.name;
          this.$nextTick(() => {
            this.startCoords = { lat: place.geometry.location.lat(), lon: place.geometry.location.lng() };
          });
        }
      });

      endAutocomplete.addListener('place_changed', () => {
        const place = endAutocomplete.getPlace();
        if (place.geometry && place.geometry.location) {
          this.endQuery = place.formatted_address || place.name;
          this.$nextTick(() => {
            this.endCoords = { lat: place.geometry.location.lat(), lon: place.geometry.location.lng() };
            outingScheduleStore.destination = this.endQuery;
            outingScheduleStore.destinationCoords = this.endCoords;
            this.$emit('destinationChanged', {
              name: this.endQuery,
              coords: this.endCoords
            });
          });
        }
      });
    },

    landmarkSubtitle(landmark) {
      if (landmark.space_use) return landmark.space_use;
      if (landmark.distance) return `${Math.round(landmark.distance)}m from this point`;
      return 'Visible landmark';
    },

    async geocodeLocation(query, existingCoords) {
      // If user selected from dropdown, coords are already available
      if (existingCoords) {
         return existingCoords;
      }

      // Fallback for manual typing without selecting from dropdown
      if (!window.google || !window.google.maps) {
        // Fallback to nominatim if google maps isn't loaded
        const safeQuery = encodeURIComponent(`${query}, Melbourne, Victoria`);
        const response = await fetch(`https://nominatim.openstreetmap.org/search?format=json&q=${safeQuery}&limit=1`);
        const data = await response.json();
        
        if (data && data.length > 0) {
          return { lon: parseFloat(data[0].lon), lat: parseFloat(data[0].lat) };
        }
        return null;
      }
      
      const geocoder = new window.google.maps.Geocoder();
      return new Promise((resolve, reject) => {
        geocoder.geocode({ address: query + ", Melbourne, VIC, Australia" }, (results, status) => {
          if (status === 'OK' && results[0]) {
            resolve({
              lat: results[0].geometry.location.lat(),
              lon: results[0].geometry.location.lng()
            });
          } else {
            reject(new Error("Could not find location: " + query));
          }
        });
      });
    },
    
    async handleCalculate() {
      if (!this.startQuery || !this.endQuery) return;
      
      this.loading = true;
      this.geocodeError = null;
      this.routeStats = null;
      
      try {
        this.statusMessage = 'Finding locations...';
        
        // 1. Geocode both locations
        const startCoords = await this.geocodeLocation(this.startQuery, this.startCoords);
        if (!startCoords) throw new Error(`Could not find location: ${this.startQuery}`);
        
        const endCoords = await this.geocodeLocation(this.endQuery, this.endCoords);
        if (!endCoords) throw new Error(`Could not find location: ${this.endQuery}`);
        
        // 2. Fetch the straight route
        this.statusMessage = 'Analyzing Topography for Safest Path...';
        const url = `/api/routes/straight?start_lon=${startCoords.lon}&start_lat=${startCoords.lat}&end_lon=${endCoords.lon}&end_lat=${endCoords.lat}`;
        const response = await fetch(url);
        const data = await response.json();
        
        if (!response.ok) {
           throw new Error(data.error || 'Failed to generate route');
        }
        
        if (data.features && data.features.length > 0) {
          const props = data.features[0].properties;
          this.landmarks = props.landmarks || [];
          this.endCoords = endCoords;
          outingScheduleStore.destination = this.endQuery;
          outingScheduleStore.destinationCoords = endCoords;
          this.routeStats = {
            destination: this.endQuery,
            destinationCoords: endCoords,
            startCoords,
            shade_percentage: Number(props.shade_percentage) || 0,
            bench_count: Number(props.bench_count) || 0,
            landmarks: this.landmarks
          };
          try {
            localStorage.setItem('neighborly-saved-checklist', JSON.stringify(this.routeStats));
          } catch (storageError) {
            console.warn('Could not save checklist', storageError);
          }
          this.$emit('routeCalculated', this.routeStats);
        } else {
          throw new Error('No safe route could be found between these locations.');
        }
      } catch (error) {
        console.error("Error calculating route:", error);
        this.geocodeError = error.message;
      } finally {
        this.loading = false;
        this.statusMessage = 'Calculating Safe Route...';
      }
    }
  }
}
</script>

<style scoped>
.routing-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 1.5rem;
}

@media (min-width: 768px) {
  .routing-grid {
    grid-template-columns: 1fr 2fr;
  }
}

.controls {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.input-group label {
  display: block;
  font-weight: 750;
  font-size: 0.95rem;
  color: #1c2e28;
  margin-bottom: 0.4rem;
}

.location-input {
  width: 100%;
  border: 1.5px solid #c2dbd1;
  border-radius: 10px;
  padding: 0.85rem 1rem;
  font-size: 1rem;
  background: #ffffff;
  color: #1c2e28;
  transition: border-color 0.2s, box-shadow 0.2s;
}

.location-input:focus {
  outline: none;
  border-color: #175d52;
  box-shadow: 0 0 0 3px rgba(23, 93, 82, 0.15);
}

.calculate-btn {
  width: 100%;
  background: #175d52;
  color: #ffffff;
  font-size: 1.05rem;
  font-weight: 700;
  padding: 0.95rem 1.25rem;
  border: none;
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.2s ease;
  margin-top: 0.5rem;
  box-shadow: 0 2px 6px rgba(23, 93, 82, 0.2);
}

.calculate-btn:hover:not(:disabled) {
  background: #0f4038;
  transform: translateY(-1px);
  box-shadow: 0 4px 10px rgba(23, 93, 82, 0.25);
}

.calculate-btn:disabled {
  background: #a3c4bd;
  cursor: not-allowed;
  box-shadow: none;
}

.error-message {
  background: #fef2f2;
  color: #b91c1c;
  border: 1.5px solid #fecaca;
  padding: 0.85rem 1rem;
  border-radius: 10px;
  font-weight: 600;
  font-size: 0.95rem;
  margin-top: 0.5rem;
}

.stats-panel {
  background: #eef6f3;
  border: 1.5px solid #c2dbd1;
  border-radius: 12px;
  padding: 1.25rem;
  margin-top: 0.75rem;
}

.stats-panel h3 {
  color: #175d52;
  font-size: 1.15rem;
  font-weight: 800;
  margin-top: 0;
  margin-bottom: 0.75rem;
}

.stats-panel ul {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
}

.stats-panel li {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 0.95rem;
  color: #1c2e28;
  font-weight: 600;
}

.stats-panel strong {
  font-size: 1.2rem;
  font-weight: 800;
  color: #175d52;
}

.map-container {
  background: #f7faf8;
  border: 2px dashed #b8d4c8;
  border-radius: 14px;
  min-height: 280px;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1.75rem;
}

.map-empty {
  color: #4b6358;
  font-size: 1.05rem;
  font-weight: 600;
  text-align: center;
  line-height: 1.5;
  max-width: 320px;
}

.map-loading {
  color: #175d52;
  font-size: 1.25rem;
  font-weight: 800;
  animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: .5; }
}

.map-success {
  text-align: center;
}

.success-icon {
  width: 4rem;
  height: 4rem;
  color: #175d52;
  margin: 0 auto 0.75rem;
}

.map-success h4 {
  font-size: 1.35rem;
  font-weight: 800;
  color: #1c2e28;
  margin: 0 0 0.35rem;
}

.map-success p {
  font-size: 0.95rem;
  color: #4b6358;
  margin: 0;
}

.landmarks-section {
  margin-top: 2rem;
  border-top: 1.5px solid #d8e5df;
  padding-top: 1.5rem;
}

.landmarks-section h3 {
  font-size: 1.35rem;
  font-weight: 800;
  color: #1c2e28;
  margin-top: 0;
  margin-bottom: 1.25rem;
}

.timeline {
  position: relative;
  padding-left: 2rem;
  margin-top: 1rem;
}

.timeline::before {
  content: '';
  position: absolute;
  left: 0.45rem;
  top: 0.5rem;
  bottom: 0.5rem;
  width: 4px;
  background: #c2dbd1;
  border-radius: 4px;
}

.timeline-item {
  position: relative;
  margin-bottom: 1.5rem;
}

.timeline-item:last-child {
  margin-bottom: 0;
}

.timeline-dot {
  position: absolute;
  left: -2.35rem;
  top: 0.35rem;
  width: 1.25rem;
  height: 1.25rem;
  background: #175d52;
  border: 3px solid #ffffff;
  border-radius: 50%;
  box-shadow: 0 0 0 3px rgba(23, 93, 82, 0.25);
}

.timeline-content {
  background: #ffffff;
  border: 1.5px solid #d8e5df;
  border-radius: 12px;
  padding: 1rem 1.25rem;
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  box-shadow: 0 2px 6px rgba(23, 93, 82, 0.04);
}

.timeline-name {
  font-size: 1.15rem;
  font-weight: 800;
  color: #1c2e28;
}

.timeline-distance {
  font-size: 0.95rem;
  font-weight: 600;
  color: #4b6358;
}
</style>
