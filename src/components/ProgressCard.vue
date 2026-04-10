<template>
  <div class="card">
    <h2>3. 进度</h2>
    <div class="progress">
      <div class="progress-row">
        <span>{{ progressLabel }}</span>
        <strong>{{ progress.current || "-" }}</strong>
      </div>
      <div class="progress-row">
        <span>已请求数量</span>
        <strong>{{ progress.processed }}</strong>
      </div>
      <div class="progress-row">
        <span>待请求数量</span>
        <strong>{{ progress.pending }}</strong>
      </div>
      <div class="progress-bar">
        <div class="progress-fill" :style="{ width: progress.percent + '%' }"></div>
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  progressLabel: { type: String, required: true },
  progress: { type: Object, required: true },
});
</script>
