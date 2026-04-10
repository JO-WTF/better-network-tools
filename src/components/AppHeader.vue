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
        <Settings :size="20" />
      </button>
    </div>
  </header>
</template>

<script setup>
import { Settings } from "lucide-vue-next";

defineProps({
  headerTitle: { type: String, required: true },
  mode: { type: String, required: true },
  modeOptions: { type: Array, required: true },
});
defineEmits(["mode-change", "open-settings"]);
</script>
