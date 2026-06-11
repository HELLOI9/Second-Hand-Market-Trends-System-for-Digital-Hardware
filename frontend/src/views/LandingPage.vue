<template>
  <div class="main-container">
    <Vue3Spline class="spline-bg" :scene="{ url: sceneUrl }" />

    <div class="content-overlay">
      <header class="top-nav">
        <RouterLink class="nav-link" :to="{ name: 'deals' }">今日捡漏</RouterLink>
        <RouterLink class="nav-link" :to="{ name: 'hardware-admin' }">订阅管理</RouterLink>
        <RouterLink class="nav-link" :to="{ name: 'alerts' }">价格提醒</RouterLink>
        <RouterLink class="nav-link" :to="{ name: 'crawler-health' }">采集健康</RouterLink>
      </header>

      <div class="center-content">
        <img class="landing-logo" :src="landingLogo" alt="HardPulse logo" />
        <h1 class="main-title">HARDPULSE</h1>
        <div class="title-row">
          <div class="sub-titles">
            <span>二手硬件行情分析平台</span>
          </div>
          <RouterLink class="enter-button" :to="{ name: 'home' }">进入看板</RouterLink>
        </div>
      </div>

      <footer class="bottom-footer">
        <span>© 2026 HardPulse</span>
      </footer>

      <div class="spline-logo-mask"></div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { Vue3Spline } from 'vue3-spline'
import landingLogo from '@/assets/landing-logo.png'

const sceneUrl = 'https://prod.spline.design/8jz9mLjGxs2xYgz5/scene.splinecode'
</script>

<style scoped>
.main-container {
  position: relative;
  width: 100vw;
  height: 100vh;
  background-color: #000;
  overflow: hidden;
  font-family: 'Courier New', Courier, monospace;
  color: #fff;
}

.spline-bg {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  z-index: 1;
  outline: none;
}

.content-overlay {
  position: relative;
  z-index: 2;
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  padding: 40px 60px;
  box-sizing: border-box;
}

.top-nav {
  display: flex;
  justify-content: space-between;
  gap: 24px;
  animation: landing-fade-up 0.6s cubic-bezier(0.2, 0.7, 0.2, 1);
}

.nav-link {
  color: #fff;
  opacity: 0.9;
  text-decoration: none;
  font-size: 20px;
  font-weight: 700;
  transition: opacity 0.22s ease, transform 0.22s ease;
}

.nav-link:hover {
  opacity: 0.66;
  transform: translateY(-1px);
}

.center-content {
  --hero-gap: 4vh;
  width: 50vw;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: var(--hero-gap);
  padding-top: 20vh;
  animation: landing-fade-up 0.82s cubic-bezier(0.18, 0.88, 0.32, 1.08);
}

.landing-logo {
  width: 14vw;
  min-width: 124px;
  margin-bottom: -4vh;
  height: auto;
  display: block;
  animation: landing-float 5s ease-in-out infinite;
}

.main-title {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
  font-size: 9vw;
  font-weight: 775;
  margin: 0;
  line-height: 1;
  letter-spacing: -0.05em;
  color: #f0f0f0;
  text-shadow: 0 0 50px rgba(255, 255, 255, 0.2), 0 10px 20px rgba(0, 0, 0, 0.5);
}

.title-row {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
}

.sub-titles {
  display: flex;
  gap: 16px;
  align-items: center;
  font-size: 32px;
  letter-spacing: 2px;
  margin-left: 2vw;
}

.enter-button {
  padding: 12px 24px;
  margin-right: 2vw;
  border: 1px solid rgba(255, 255, 255, 0.35);
  border-radius: 999px;
  color: #fff;
  text-decoration: none;
  font-size: 20px;
  font-weight: 700;
  background: rgba(255, 255, 255, 0.08);
  backdrop-filter: blur(10px);
  transition: background 0.22s ease, transform 0.22s ease, border-color 0.22s ease;
}

.enter-button:hover {
  background: rgba(255, 156, 82, 0.2);
  border-color: rgba(255, 156, 82, 0.5);
  transform: translateY(-2px);
}

.bottom-footer {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  font-size: 12px;
  animation: landing-fade-up 0.9s cubic-bezier(0.2, 0.7, 0.2, 1);
}

.spline-logo-mask {
  position: fixed;
  right: 0;
  bottom: 0;
  width: 160px;
  height: 60px;
  background-color: #000;
  z-index: 10;
}

@keyframes landing-fade-up {
  from {
    opacity: 0;
    transform: translateY(14px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes landing-float {
  0%,
  100% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(-6px);
  }
}

@media (prefers-reduced-motion: reduce) {
  .top-nav,
  .center-content,
  .landing-logo,
  .bottom-footer {
    animation: none !important;
  }

  .nav-link,
  .enter-button {
    transition: none !important;
  }
}
</style>
