<template>
  <div class="app-shell">
    <AppHeader
      :header-title="headerTitle"
      :mode="mode"
      :mode-options="modeOptions"
      @mode-change="mode = $event"
      @open-settings="showSettings = true"
    />

    <MapVisualizationPage v-if="mode === 'visualize'" :map-api-key="mapApiKey" />

    <main v-else class="layout">
      <section class="panel">
        <div class="card">
          <div class="card-header">
            <h2>1. 上传 Excel</h2>
            <button
              class="icon-button"
              :class="{ pulse: mockAnimating }"
              type="button"
              @click="fillMockData"
              aria-label="一键填写 Mock 数据"
            >
              <svg viewBox="0 0 24 24" aria-hidden="true">
                <path
                  d="M12 3l1.9 4.3L18 9.2l-4.1 1.9L12 15l-1.9-3.9L6 9.2l4.1-1.9L12 3zm7 9l.9 2.1L22 15l-2.1.9L19 18l-.9-2.1L16 15l2.1-.9L19 12zM4 13l.9 2.1L7 16l-2.1.9L4 19l-.9-2.1L1 16l2.1-.9L4 13z"
                />
              </svg>
            </button>
          </div>
          <div
            class="dropzone"
            :class="{ active: isDragging, loaded: hasData, flash: dropzoneFlash }"
            @dragover.prevent="handleDragOver"
            @dragleave.prevent="handleDragLeave"
            @drop.prevent="handleFileDrop"
          >
            <input type="file" accept=".xlsx,.xls" @change="handleFileChange" />
            <p>拖放 Excel 文件到此处，或点击选择</p>
          </div>
          <p v-if="fileName" class="hint">已加载：{{ fileName }}</p>
        </div>

        <div class="card">
          <h2>2. 配置解析</h2>
          <div v-if="mode === 'geocode'">
            <label class="field">
              <span>地址列名</span>
              <select v-model="columnName">
                <option value="" disabled>请选择列名</option>
                <option v-for="header in headers" :key="header" :value="header">
                  {{ header }}
                </option>
              </select>
            </label>
          </div>
          <div v-else-if="mode === 'reverse'">
            <div class="field">
              <span>经纬度格式</span>
              <div class="option-row">
                <label class="option-pill">
                  <input
                    v-model="reverseColumnMode"
                    type="radio"
                    value="separate"
                  />
                  <span>不同列</span>
                </label>
                <label class="option-pill">
                  <input
                    v-model="reverseColumnMode"
                    type="radio"
                    value="single"
                  />
                  <span>同一列</span>
                </label>
              </div>
            </div>
            <template v-if="reverseColumnMode === 'separate'">
              <label class="field">
                <span>纬度列名</span>
                <select v-model="latColumnName">
                  <option value="" disabled>请选择列名</option>
                  <option v-for="header in headers" :key="header" :value="header">
                    {{ header }}
                  </option>
                </select>
              </label>
              <label class="field">
                <span>经度列名</span>
                <select v-model="lngColumnName">
                  <option value="" disabled>请选择列名</option>
                  <option v-for="header in headers" :key="header" :value="header">
                    {{ header }}
                  </option>
                </select>
              </label>
            </template>
            <template v-else>
              <label class="field">
                <span>经纬度列名</span>
                <select v-model="reverseColumnName">
                  <option value="" disabled>请选择列名</option>
                  <option v-for="header in headers" :key="header" :value="header">
                    {{ header }}
                  </option>
                </select>
              </label>
              <div class="field">
                <span>分隔符</span>
                <div class="option-row">
                  <label class="option-pill">
                    <input
                      v-model="reverseDelimiterMode"
                      type="radio"
                      value="auto"
                    />
                    <span>自动识别 “,”</span>
                  </label>
                  <label class="option-pill">
                    <input
                      v-model="reverseDelimiterMode"
                      type="radio"
                      value="custom"
                    />
                    <span>自定义</span>
                  </label>
                </div>
                <input
                  v-if="reverseDelimiterMode === 'custom'"
                  v-model="reverseDelimiter"
                  type="text"
                  placeholder="例如：| 或 空格"
                />
              </div>
            </template>
          </div>
          <div v-else>
            <div class="field">
              <span>路线输入类型</span>
              <div class="option-row">
                <label class="option-pill">
                  <input v-model="routeInputMode" type="radio" value="address" />
                  <span>地址</span>
                </label>
                <label class="option-pill">
                  <input v-model="routeInputMode" type="radio" value="coordinate" />
                  <span>经纬度</span>
                </label>
              </div>
              <p v-if="routeInputMode === 'coordinate'" class="coordinate-format-tip">
                经纬度的格式为 “经度,纬度” （经度在前，纬度在后，用英文逗号分隔）
              </p>
            </div>
            <label class="field">
              <span>起始地列名</span>
              <select v-model="startColumnName">
                <option value="" disabled>请选择列名</option>
                <option v-for="header in headers" :key="header" :value="header">
                  {{ header }}
                </option>
              </select>
            </label>
            <label class="field">
              <span>目的地列名</span>
              <select v-model="endColumnName">
                <option value="" disabled>请选择列名</option>
                <option v-for="header in headers" :key="header" :value="header">
                  {{ header }}
                </option>
              </select>
            </label>
          </div>
          <label class="field">
            <span>地图服务商</span>
            <select v-model="provider">
              <option value="mapbox">Mapbox</option>
              <option value="here">HERE</option>
              <option value="custom" :disabled="mode === 'reverse'">自定义接口</option>
            </select>
          </label>
          <p v-if="mode === 'reverse'" class="hint">自定义接口暂不支持反编码。</p>
          <p class="hint">服务商密钥与接口地址请在右上角设置中填写。</p>
          <div class="actions">
            <button class="primary" :disabled="!canStart" @click="handleStart">
              {{ startLabel }}
            </button>
            <button class="secondary" :disabled="!canDownload" @click="downloadExcel">
              下载结果
            </button>
          </div>
        </div>

        <ProgressCard :progress-label="progressLabel" :progress="progress" />

        <LogCard :logs="logs" />
      </section>

      <section class="map-panel">
        <div class="map-wrapper">
          <div class="map-toolbar">
            <label class="map-live-toggle">
              <input v-model="mapRealtimeUpdate" type="checkbox" />
              <span>地图实时更新</span>
            </label>
          </div>
          <div ref="mapContainer" class="map"></div>
          <div v-if="!mapLoaded" class="map-config">
            <h3>地图配置</h3>
            <p class="hint">请在设置中填写 Mapbox API Key。</p>
            <button class="secondary" @click="showSettings = true">打开设置</button>
          </div>
          <div v-if="!mapLoaded" class="map-empty">
            <p>请在设置中填写 Mapbox API Key 以加载地图。</p>
          </div>
        </div>
      </section>
    </main>

    <div v-if="showSettings" class="settings-backdrop" @click.self="showSettings = false">
      <div class="settings-modal" role="dialog" aria-modal="true" aria-label="设置">
        <div class="settings-header">
          <h2>设置</h2>
          <button class="icon-button" type="button" @click="showSettings = false" aria-label="关闭">
            ✕
          </button>
        </div>
        <div class="settings-body">
          <div class="settings-section">
            <h3>服务商密钥</h3>
            <label class="field">
              <span>Mapbox API Key</span>
              <input v-model="mapboxGeocodeApiKey" type="password" placeholder="用于编码/反编码/导航" />
            </label>
            <label class="field">
              <span>HERE API Key</span>
              <input v-model="hereGeocodeApiKey" type="password" placeholder="用于编码/反编码/导航" />
            </label>
          </div>
          <div class="settings-section">
            <h3>自定义接口</h3>
            <label class="field">
              <span>App ID</span>
              <input v-model="customAppId" type="text" placeholder="输入 App ID" />
            </label>
            <label class="field">
              <span>Credential</span>
              <input v-model="customCredential" type="password" placeholder="输入 Credential" />
            </label>
            <label class="field">
              <span>Token 接口 URL</span>
              <input v-model="customTokenUrl" type="text" placeholder="getResAppDynamicToken 接口地址" />
            </label>
            <label class="field">
              <span>地理编码接口 URL</span>
              <input v-model="customGeocodeUrl" type="text" placeholder="geographicSearch 接口地址" />
            </label>
            <label class="field">
              <span>导航接口 URL</span>
              <input v-model="customRouteUrl" type="text" placeholder="routeSearch 接口地址" />
            </label>
            <label class="field">
              <span>WebSocket 地址</span>
              <input v-model="customWebSocketUrl" type="text" placeholder="ws://localhost:8765" />
            </label>
          </div>
          <div class="settings-section">
            <h3>地图展示</h3>
            <label class="field">
              <span>Mapbox API Key</span>
              <input v-model="mapApiKey" type="password" placeholder="用于地图展示" />
            </label>
          </div>
          <div class="settings-section">
            <h3>配置文件</h3>
            <div class="actions settings-actions">
              <button class="secondary" type="button" @click="exportSettings">导出配置</button>
              <button class="secondary" type="button" @click="triggerConfigImport">导入配置</button>
              <input
                ref="configFileInput"
                class="visually-hidden"
                type="file"
                accept="application/json"
                @change="handleConfigFileChange"
              />
            </div>
            <p v-if="settingsNotice" class="hint settings-notice">{{ settingsNotice }}</p>
            <p class="hint">仅导入/导出设置中的密钥、URL 等配置项。</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import AppHeader from "./components/AppHeader.vue";
import ProgressCard from "./components/ProgressCard.vue";
import LogCard from "./components/LogCard.vue";
import MapVisualizationPage from "./components/MapVisualizationPage.vue";
import { useNetworkToolsApp } from "./composables/useNetworkToolsApp";

const {
  headers,
  rows,
  fileName,
  columnName,
  latColumnName,
  lngColumnName,
  reverseColumnMode,
  reverseColumnName,
  reverseDelimiterMode,
  reverseDelimiter,
  startColumnName,
  endColumnName,
  routeInputMode,
  provider,
  mapboxGeocodeApiKey,
  hereGeocodeApiKey,
  customAppId,
  customCredential,
  customTokenUrl,
  customGeocodeUrl,
  customRouteUrl,
  customWebSocketUrl,
  mapApiKey,
  logs,
  showSettings,
  settingsNotice,
  configFileInput,
  mapContainer,
  mapLoaded,
  isDragging,
  dropzoneFlash,
  mockAnimating,
  mapRealtimeUpdate,
  mode,
  modeOptions,
  canStart,
  canDownload,
  hasData,
  headerTitle,
  startLabel,
  progressLabel,
  progress,
  handleFileChange,
  handleDragOver,
  handleDragLeave,
  handleFileDrop,
  fillMockData,
  handleStart,
  downloadExcel,
  triggerConfigImport,
  handleConfigFileChange,
  exportSettings,
} = useNetworkToolsApp();
</script>
