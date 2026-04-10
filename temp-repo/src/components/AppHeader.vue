<template>
  <header class="app-header">
    <div>
      <h1>{{ headerTitle }}</h1>
      <p class="sub-title">支持地图可视化、地址编码、经纬度解码、导航距离计算四种处理方式。</p>
    </div>
    <div class="header-controls">
      <div class="mode-toggle" role="tablist" aria-label="功能切换">
        <button
          v-for="item in modeOptions"
          :key="item.value"
          type="button"
          class="mode-button"
          :class="{ active: mode === item.value }"
          role="tab"
          :aria-selected="mode === item.value"
          @click="$emit('mode-change', item.value)"
        >
          {{ item.label }}
        </button>
      </div>
      <button class="icon-button settings-button" type="button" @click="$emit('open-settings')" aria-label="打开设置">
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <path
            d="M12 8.5a3.5 3.5 0 1 1 0 7 3.5 3.5 0 0 1 0-7Zm8.94 3.5a7.2 7.2 0 0 0-.12-1.3l2.02-1.58-2-3.46-2.44.78a7.53 7.53 0 0 0-2.26-1.3l-.5-2.5h-4l-.5 2.5a7.53 7.53 0 0 0-2.26 1.3l-2.44-.78-2 3.46 2.02 1.58a7.2 7.2 0 0 0 0 2.6L2.44 13.6l2 3.46 2.44-.78a7.53 7.53 0 0 0 2.26 1.3l.5 2.5h4l.5-2.5a7.53 7.53 0 0 0 2.26-1.3l2.44.78 2-3.46-2.02-1.58c.08-.42.12-.86.12-1.3Z"
          />
        </svg>
      </button>
    </div>
  </header>
</template>

<script setup>
defineProps({
  headerTitle: { type: String, required: true },
  mode: { type: String, required: true },
  modeOptions: { type: Array, required: true },
});
defineEmits(["mode-change", "open-settings"]);
</script>
