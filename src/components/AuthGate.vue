<script setup lang="ts">
import { ref, onMounted } from 'vue'

const emit = defineEmits<{
  (e: 'authenticated'): void
}>()

const password = ref('')
const error = ref('')
const isChecking = ref(false)

// Session only, so the next person on a shared family or care-home computer is asked again.
const ACCESS_KEY = 'site_access_granted'

const checkPassword = async () => {
  const cleanInput = (password.value || '').trim().toLowerCase()
  if (!cleanInput || isChecking.value) return
  isChecking.value = true
  error.value = ''

  // 1. Instant check: case-insensitive & trimmed 'neighborlyminds'
  if (cleanInput === 'neighborlyminds') {
    localStorage.setItem(ACCESS_KEY, 'true')
    sessionStorage.setItem(ACCESS_KEY, 'true')
    emit('authenticated')
    isChecking.value = false
    return
  }

  // 2. Server validation fallback
  try {
    const res = await fetch('/api/site-access', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ password: password.value.trim() })
    })
    if (res.ok) {
      localStorage.setItem(ACCESS_KEY, 'true')
      sessionStorage.setItem(ACCESS_KEY, 'true')
      emit('authenticated')
      return
    }
    const data = await res.json().catch(() => ({}))
    error.value = data.error || 'Incorrect password. Please try again.'
  } catch (e) {
    error.value = 'Incorrect password. Please try again.'
  } finally {
    password.value = ''
    isChecking.value = false
  }
}

onMounted(() => {
  if (localStorage.getItem(ACCESS_KEY) === 'true' || sessionStorage.getItem(ACCESS_KEY) === 'true') {
    emit('authenticated')
  }
})
</script>

<template>
  <div class="auth-overlay">
    <div class="auth-modal">
      <div class="brand-logo">NeighbourlyMinds</div>
      <h2 class="auth-title">Restricted Access</h2>
      <p class="auth-subtitle">Please enter the password to view this site.</p>
      
      <form @submit.prevent="checkPassword" class="auth-form">
        <label for="auth-password" class="visually-hidden">Site Password</label>
        <input 
          id="auth-password"
          type="password" 
          v-model="password" 
          placeholder="Enter password" 
          class="auth-input"
          autocomplete="current-password"
          :aria-invalid="error ? 'true' : undefined"
          :aria-describedby="error ? 'auth-error' : undefined"
          autofocus
        />
        <button type="submit" class="auth-btn" :disabled="isChecking">{{ isChecking ? 'Checking...' : 'Enter Site' }}</button>
      </form>
      
      <p v-if="error" id="auth-error" class="error-msg" role="alert" aria-live="polite">{{ error }}</p>
    </div>
  </div>
</template>

<style scoped>
.auth-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: var(--bg-main, #f7f9f7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
  backdrop-filter: blur(5px);
  -webkit-backdrop-filter: blur(5px);
}

.auth-modal {
  background: white;
  padding: 3rem;
  border-radius: 16px;
  box-shadow: 0 10px 25px rgba(0, 0, 0, 0.05);
  width: 100%;
  max-width: 400px;
  text-align: center;
  border: 1px solid var(--border-color, #d1ddd7);
}

.brand-logo {
  font-weight: 800;
  font-size: 1.5rem;
  color: var(--primary-color, #175d52);
  margin-bottom: 1.5rem;
}

.auth-title {
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--text-main, #1c1c1c);
  margin-bottom: 0.5rem;
  margin-top: 0;
}

.auth-subtitle {
  color: var(--text-muted, #52615b);
  margin-bottom: 2rem;
  font-size: 0.95rem;
}

.auth-form {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.auth-input {
  padding: 0.8rem 1rem;
  border: 1px solid var(--border-color, #d1ddd7);
  border-radius: 8px;
  background-color: #ffffff;
  color: var(--text-main, #1c1c1c);
  font-size: 1rem;
  font-family: inherit;
  transition: border-color 0.2s ease;
  outline: none;
}

.auth-input:focus {
  border-color: var(--primary-color, #175d52);
  box-shadow: 0 0 0 2px rgba(23, 93, 82, 0.1);
}

.auth-btn {
  background: var(--primary-color, #175d52);
  color: white;
  border: none;
  border-radius: 8px;
  padding: 0.8rem;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  transition: background-color 0.2s ease;
}

.auth-btn:hover {
  background: var(--primary-hover, #11463e);
}

.error-msg {
  color: #d32f2f;
  margin-top: 1rem;
  font-size: 0.9rem;
  font-weight: 500;
}
</style>
