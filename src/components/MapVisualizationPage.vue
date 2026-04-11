<template>
  <section class="visual-page">
    <div class="visual-top">
      <div ref="mapContainer" class="visual-map"></div>
      <template v-if="isLoaded">
        <div v-if="!mapApiKey && !mapReady" class="visual-map-empty">请输入设置中的 Mapbox 地图 Key 以启用可视化。</div>
        <div v-else-if="mapApiKey && !mapReady" class="visual-map-empty">正在加载地图资源...</div>
      </template>
      <div v-if="isProcessing" class="visual-map-mask">
        <div class="mask-card">正在处理数据并加载地图要素...</div>
      </div>
      <div class="draw-fab-group">
        <button
          class="draw-fab"
          :class="{ active: drawMode === 'point' }"
          type="button"
          :disabled="isProcessing"
          title="绘制点"
          @click="toggleDrawMode('point')"
        >
          <MapPin :size="18" :stroke-width="2.5" />
          <span class="draw-label">点</span>
        </button>
        <button
          class="draw-fab"
          :class="{ active: drawMode === 'line' }"
          type="button"
          :disabled="isProcessing"
          title="绘制线"
          @click="toggleDrawMode('line')"
        >
          <Minus :size="18" :stroke-width="2.5" />
          <span class="draw-label">线</span>
        </button>
        <button
          class="draw-fab"
          :class="{ active: drawMode === 'polygon' }"
          type="button"
          :disabled="isProcessing"
          title="绘制面"
          @click="toggleDrawMode('polygon')"
        >
          <Square :size="18" :stroke-width="2.5" />
          <span class="draw-label">面</span>
        </button>
      </div>
    </div>

    <div class="visual-bottom">
      <div class="dataset-tabs" role="tablist">
        <div v-for="dataset in datasets" :key="dataset.id" class="dataset-tab-item">
          <button
            :class="['mode-button', { active: dataset.id === activeDatasetId }]"
            type="button"
            @click="activeDatasetId = dataset.id"
          >
            {{ dataset.name }} ({{ dataset.rows.length }})
          </button>
          <button
            class="icon-button dataset-visibility"
            type="button"
            @click="toggleDatasetVisibility(dataset.id)"
            :title="dataset.visible !== false ? '隐藏图层' : '显示图层'"
          >
            <Eye v-if="dataset.visible !== false" :size="18" />
            <EyeOff v-else :size="18" />
          </button>
          <button
            class="icon-button dataset-style"
            type="button"
            @click="openStyleConfig(dataset.id)"
            aria-label="数据集样式设置"
            title="样式设置"
          >
            <Settings :size="18" />
          </button>
          <button
            v-if="dataset.id === activeDatasetId"
            class="icon-button dataset-delete"
            type="button"
            :disabled="datasets.length <= 1"
            @click="removeDataset(dataset.id)"
            aria-label="删除当前数据集"
          >
            <X :size="18" />
          </button>
        </div>
        <button class="add-dataset" type="button" @click="addDataset">
          <Plus :size="16" style="margin-right: 4px" />
          添加数据集
        </button>
      </div>

      <div class="dataset-toolbar">
        <div
          class="dropzone visual-dropzone"
          :class="{ active: isDragging, flash: dropzoneFlash }"
          title="可自动识别geojson和csv格式数据。csv格式必须有一行表头，且表头至少包含经度与纬度字段（如：经度/纬度、lon/lng/longitude/long 与 lat/latitude，不区分大小写）"
          @dragover.prevent="handleDragOver"
          @dragleave.prevent="handleDragLeave"
          @drop.prevent="handleFileDrop"
          @click="triggerFilePicker"
        >
          <input
            ref="dataFileInput"
            class="visually-hidden"
            type="file"
            accept=".geojson,.json,.csv,.xlsx,.xls"
            :disabled="isProcessing"
            @change="handleFileUpload"
          />
          <div v-if="!isProcessing" class="dropzone-content">
            <p class="main-text">拖放文件或点击上传</p>
            <p class="sub-text">支持 GeoJSON/CSV/Excel (需包含经纬度字段)</p>
          </div>
          <p v-else>正在处理...</p>
        </div>
        <button class="secondary action-button" type="button" @click="showPaste = !showPaste" :disabled="isProcessing">粘贴数据</button>
              </div>

      <div v-if="showPaste" class="paste-box">
        <div class="paste-input-wrap">
          <textarea
            v-model="pasteInput"
            rows="4"
            placeholder="支持粘贴 geojson / csv / wkt (POINT, LINESTRING, POLYGON, MULTIPOLYGON)"
          />
          <button
            v-if="pasteInput"
            class="paste-close"
            type="button"
            aria-label="清空粘贴内容"
            title="清空"
            @click="clearPasteInput"
          >
            <X :size="16" />
          </button>
        </div>
        <button class="primary" type="button" @click="handlePasteImport" :disabled="isProcessing">解析并导入</button>
      </div>

      <div v-if="activeDataset" class="table-tools">
        <div class="filter-row">
          <span>筛选：</span>
          <button
            type="button"
            class="secondary small"
            :class="{ active: geometryFilter === 'all' }"
            @click="setGeometryFilter('all')"
          >
            全部
          </button>
          <button
            type="button"
            class="secondary small"
            :class="{ active: geometryFilter === 'point' }"
            @click="setGeometryFilter('point')"
          >
            点
          </button>
          <button
            type="button"
            class="secondary small"
            :class="{ active: geometryFilter === 'line' }"
            @click="setGeometryFilter('line')"
          >
            线
          </button>
          <button
            type="button"
            class="secondary small"
            :class="{ active: geometryFilter === 'polygon' }"
            @click="setGeometryFilter('polygon')"
          >
            面
          </button>
          <button type="button" class="secondary small add-field-btn" @click="addColumnField">新增字段</button>
        </div>
      </div>

      <div v-if="activeDataset" class="table-wrap">
        <a-table
          :dataSource="filteredRows"
          :columns="tableColumns"
          :rowKey="record => record.featureKey"
          :rowClassName="record => record.featureKey === selectedFeatureKey ? 'table-row-active' : ''"
          v-model:current="currentPage"
          v-model:pageSize="pageSize"
          :pagination="{ 
            showSizeChanger: true, 
            pageSizeOptions: ['10', '20', '50', '100', '200', '500', '1000'],
            showTotal: total => `共 ${total} 条`
          }"
          size="small"
          bordered
          :scroll="{ x: 'max-content' }"
        >
          <template #customFilterDropdown="{ setSelectedKeys, selectedKeys, confirm, clearFilters, column }">
            <div style="padding: 8px">
              <a-input
                ref="searchInput"
                :placeholder="`搜索 ${column.title}`"
                :value="selectedKeys[0]"
                style="width: 188px; margin-bottom: 8px; display: block"
                @change="e => setSelectedKeys(e.target.value ? [e.target.value] : [])"
                @pressEnter="confirm()"
              />
              <a-space>
                <a-button
                  type="primary"
                  size="small"
                  style="width: 90px"
                  @click="confirm()"
                >
                  <template #icon><Search :size="14" /></template>
                  确定
                </a-button>
                <a-button size="small" style="width: 90px" @click="clearFilters()">
                  重置
                </a-button>
              </a-space>
            </div>
          </template>
          <template #customFilterIcon="{ filtered }">
            <Search :size="14" :style="{ color: filtered ? '#1890ff' : undefined }" />
          </template>
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'geometryType'">
              <span class="geometry-badge">{{ record.geometryType }}</span>
            </template>
            <template v-else-if="activeDataset.extraColumns.includes(column.key)">
              <template v-if="isEditingCell(record.featureKey, column.key)">
                <input
                  class="cell-editor"
                  :value="editingValue"
                  @input="editingValue = $event.target.value"
                  @blur="handleEditorBlur(record, column.key)"
                  @keydown.enter.prevent="saveEditCell(record, column.key)"
                  @keydown.esc.prevent="handleEditorEsc"
                />
              </template>
              <button v-else class="cell-value-btn" type="button" @click="startEditCell(record, column.key)">
                {{ record.properties[column.key] ?? '-' }}
              </button>
            </template>
            <template v-else-if="column.key === 'actions'">
              <div style="display: flex; gap: 8px;">
                <button class="secondary small" type="button" @click="locateFeature(record)">定位</button>
                <button class="secondary small" type="button" @click="removeFeature(record.featureKey)">删除</button>
              </div>
            </template>
          </template>
        </a-table>
      </div>
    </div>
    
    <div v-if="styleConfigDatasetId !== null" class="settings-backdrop" @click.self="closeStyleConfig">
      <div class="style-modal" role="dialog" aria-modal="true" aria-label="数据集样式设置">
        <div class="style-modal-header">
          <h3>数据集样式配置（{{ datasets.find((d) => d.id === styleConfigDatasetId)?.name }}）</h3>
          <button class="icon-button" type="button" @click="closeStyleConfig">
            <X :size="18" />
          </button>
        </div>
        <div class="style-columns">
          <section class="style-column">
            <h4>点</h4>
            <label>颜色 <input v-model="styleDraft.point.color" type="color" /></label>
            <label>半径 <input v-model.number="styleDraft.point.radius" type="number" min="2" max="30" /></label>
            <label>透明度 <input v-model.number="styleDraft.point.opacity" type="number" min="0" max="1" step="0.1" /></label>
            <label>描边颜色 <input v-model="styleDraft.point.strokeColor" type="color" /></label>
            <label>描边宽度 <input v-model.number="styleDraft.point.strokeWidth" type="number" min="0" max="10" /></label>
          </section>
          <section class="style-column">
            <h4>线</h4>
            <label>颜色 <input v-model="styleDraft.line.color" type="color" /></label>
            <label>线宽 <input v-model.number="styleDraft.line.width" type="number" min="1" max="20" /></label>
            <label>透明度 <input v-model.number="styleDraft.line.opacity" type="number" min="0" max="1" step="0.1" /></label>
          </section>
          <section class="style-column">
            <h4>面</h4>
            <label>填充色 <input v-model="styleDraft.polygon.fillColor" type="color" /></label>
            <label>填充透明度 <input v-model.number="styleDraft.polygon.fillOpacity" type="number" min="0" max="1" step="0.1" /></label>
            <label>边框色 <input v-model="styleDraft.polygon.lineColor" type="color" /></label>
            <label>边框宽度 <input v-model.number="styleDraft.polygon.lineWidth" type="number" min="1" max="10" /></label>
          </section>
        </div>
        <div class="style-modal-actions">
          <button class="secondary" type="button" @click="closeStyleConfig">取消</button>
          <button class="primary" type="button" @click="saveStyleConfig">保存</button>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import mapboxgl from "mapbox-gl";
import * as XLSX from "xlsx";
import { Eye, EyeOff, Settings, MapPin, Minus, Square, X, Plus, Filter, FilterX, Search } from "lucide-vue-next";

const props = defineProps({
  mapApiKey: { type: String, default: "" },
});

const createDefaultDatasetStyle = () => ({
  point: { color: "#f97316", radius: 6, opacity: 1, strokeColor: "#ffffff", strokeWidth: 1 },
  line: { color: "#0ea5e9", width: 3, opacity: 1 },
  polygon: { fillColor: "#2563eb", fillOpacity: 0.2, lineColor: "#1d4ed8", lineWidth: 1 },
});

const mapContainer = ref(null);
const mapReady = ref(false);
const isLoaded = ref(false);
const showPaste = ref(false);
const pasteInput = ref("");
const isProcessing = ref(false);
const dataFileInput = ref(null);
const isDragging = ref(false);
const dropzoneFlash = ref(false);

const datasets = ref([{ id: 1, name: "数据集 1", rows: [], extraColumns: [], visible: true, filters: {} }]);
const datasetStyles = ref({ 1: createDefaultDatasetStyle() });
const styleConfigDatasetId = ref(null);
const styleDraft = ref(createDefaultDatasetStyle());
const activeDatasetId = ref(1);
const selectedFeatureKey = ref("");
const geometryFilter = ref("all");
const currentPage = ref(1);
const pageSize = ref(20);
const editingCell = ref({ featureKey: "", column: "" });
const editingValue = ref("");
const skipBlurSave = ref(false);

const rowElementMap = new Map();
const featureCounter = ref(1);
let map = null;
const drawMode = ref("none");
const drawingCoords = ref([]);
let mapPopup = null;
const pointLayerPrefix = "viz-dataset-point-layer-";
const pointSourcePrefix = "viz-dataset-point-source-";

const activeDataset = computed(() => datasets.value.find((d) => d.id === activeDatasetId.value));



const geometryGroupMap = {
  Point: "point",
  MultiPoint: "point",
  LineString: "line",
  MultiLineString: "line",
  Polygon: "polygon",
  MultiPolygon: "polygon",
};

const resolveGeometryGroup = (geometryType = "") => geometryGroupMap[geometryType] || "";

const sortedRows = computed(() => {
  if (!activeDataset.value) return [];
  return [...activeDataset.value.rows].sort((a, b) => Number(a.gid) - Number(b.gid));
});

const filteredRows = computed(() => {
  if (!activeDataset.value) return [];
  let rows = sortedRows.value;
  
  if (geometryFilter.value !== "all") {
    rows = rows.filter((row) => resolveGeometryGroup(row.geometryType) === geometryFilter.value);
  }
  
  const filters = activeDataset.value.filters || {};
  const activeCols = Object.keys(filters).filter(col => filters[col] && filters[col].trim() !== '');
  
  if (activeCols.length > 0) {
    rows = rows.filter(row => {
      return activeCols.every(col => {
        const cellValue = String(row.properties[col] ?? '').toLowerCase();
        const filterValue = filters[col].trim().toLowerCase();
        return cellValue.includes(filterValue);
      });
    });
  }
  
  return rows;
});

const tableColumns = computed(() => {
  if (!activeDataset.value) return [];
  
  const baseCols = [
    { 
      title: 'GID', 
      dataIndex: 'gid', 
      key: 'gid', 
      width: 80,
      sorter: (a, b) => a.gid - b.gid
    },
    { 
      title: 'GEOMETRY', 
      dataIndex: 'geometryType', 
      key: 'geometryType', 
      width: 120,
      filters: [
        { text: 'Point', value: 'Point' },
        { text: 'LineString', value: 'LineString' },
        { text: 'Polygon', value: 'Polygon' },
        { text: 'MultiPoint', value: 'MultiPoint' },
        { text: 'MultiLineString', value: 'MultiLineString' },
        { text: 'MultiPolygon', value: 'MultiPolygon' },
      ],
      onFilter: (value, record) => record.geometryType === value,
    },
  ];

  const extraCols = activeDataset.value.extraColumns.map(col => {
    return {
      title: col,
      dataIndex: ['properties', col],
      key: col,
      sorter: (a, b) => String(a.properties[col]).localeCompare(String(b.properties[col])),
      customFilterDropdown: true,
      onFilter: (value, record) => 
        String(record.properties[col] || '')
          .toLowerCase()
          .includes(value.toLowerCase()),
      ellipsis: true,
    };
  });

  const actionCols = [
    { title: '操作', key: 'actions', width: 120, fixed: 'right' }
  ];

  return [...baseCols, ...extraCols, ...actionCols];
});

const bindRowRef = (featureKey) => (el) => {
  if (el) rowElementMap.set(featureKey, el);
  else rowElementMap.delete(featureKey);
};

const highlightFilter = (geometryType) => [
  "all",
  ["==", ["geometry-type"], geometryType],
  ["==", ["coalesce", ["get", "__featureKey"], ""], selectedFeatureKey.value || ""],
];

const syncHighlightFilters = () => {
  if (!mapReady.value || !map) return;
  const configs = [
    ["viz-highlight-fill", "Polygon"],
    ["viz-highlight-polygon-outline", "Polygon"],
    ["viz-highlight-line", "LineString"],
    ["viz-highlight-point", "Point"],
  ];
  configs.forEach(([layerId, geometryType]) => {
    if (map.getLayer(layerId)) {
      map.setFilter(layerId, highlightFilter(geometryType));
    }
  });
};




const refreshDrawSource = (mouseLngLat = null) => {
  if (!mapReady.value || !map || drawMode.value === "none") {
    map?.getSource("viz-draw-source")?.setData({ type: "FeatureCollection", features: [] });
    return;
  }

  const features = [];
  const coords = [...drawingCoords.value];

  // Add existing points
  coords.forEach((coord) => {
    features.push({
      type: "Feature",
      geometry: { type: "Point", coordinates: coord },
    });
  });

  if (coords.length > 0) {
    const displayCoords = mouseLngLat ? [...coords, [mouseLngLat.lng, mouseLngLat.lat]] : [...coords];

    if (drawMode.value === "line") {
      if (displayCoords.length >= 2) {
        features.push({
          type: "Feature",
          geometry: { type: "LineString", coordinates: displayCoords },
        });
      }
    } else if (drawMode.value === "polygon") {
      if (displayCoords.length >= 2) {
        // Show as line if not enough points for polygon yet
        features.push({
          type: "Feature",
          geometry: { type: "LineString", coordinates: displayCoords },
        });
      }
      if (displayCoords.length >= 3) {
        features.push({
          type: "Feature",
          geometry: {
            type: "Polygon",
            coordinates: [[...displayCoords, displayCoords[0]]],
          },
        });
      }
    }
  }

  map.getSource("viz-draw-source")?.setData({ type: "FeatureCollection", features });
};

const toggleDrawMode = (mode) => {
  if (drawMode.value === mode) {
    drawMode.value = "none";
    drawingCoords.value = [];
    refreshDrawSource();
    return;
  }
  drawMode.value = mode;
  drawingCoords.value = [];
  refreshDrawSource();
};

const commitDrawingByMode = () => {
  let success = false;
  if (drawMode.value === "line" && drawingCoords.value.length >= 2) {
    appendRowsFromFeatures([
      {
        type: "Feature",
        geometry: { type: "LineString", coordinates: [...drawingCoords.value] },
        properties: {},
      },
    ]);
    success = true;
  } else if (drawMode.value === "polygon" && drawingCoords.value.length >= 3) {
    const first = drawingCoords.value[0];
    const last = drawingCoords.value[drawingCoords.value.length - 1];
    const ring = first[0] === last[0] && first[1] === last[1]
      ? [...drawingCoords.value]
      : [...drawingCoords.value, first];
    appendRowsFromFeatures([
      {
        type: "Feature",
        geometry: { type: "Polygon", coordinates: [ring] },
        properties: {},
      },
    ]);
    success = true;
  }
  
  if (success) {
    drawingCoords.value = [];
    refreshDrawSource();
  }
  return success;
};

const ensureValidGeometryFilter = () => {
  if (geometryFilter.value === "all") return;
  const available = new Set((activeDataset.value?.rows || []).map((row) => resolveGeometryGroup(row.geometryType)).filter(Boolean));
  if (!available.size) {
    geometryFilter.value = "all";
    return;
  }
  if (!available.has(geometryFilter.value)) {
    geometryFilter.value = "all";
  }
};

const setGeometryFilter = (group) => {
  geometryFilter.value = group;
};

const isEditingCell = (featureKey, column) =>
  editingCell.value.featureKey === featureKey && editingCell.value.column === column;

const startEditCell = (row, column) => {
  editingCell.value = { featureKey: row.featureKey, column };
  editingValue.value = row.properties?.[column] ?? "";
};

const cancelEditCell = () => {
  editingCell.value = { featureKey: "", column: "" };
  editingValue.value = "";
};

const handleEditorEsc = (event) => {
  skipBlurSave.value = true;
  cancelEditCell();
  event.target?.blur();
};

const handleEditorBlur = (row, column) => {
  if (skipBlurSave.value) {
    skipBlurSave.value = false;
    return;
  }
  saveEditCell(row, column);
};

const saveEditCell = (row, column) => {
  if (!isEditingCell(row.featureKey, column)) return;
  row.properties[column] = editingValue.value;
  if (row.feature?.properties) {
    row.feature.properties[column] = editingValue.value;
  }
  cancelEditCell();
};

const addColumnField = () => {
  if (!activeDataset.value) return;
  const input = window.prompt("请输入新增字段名称");
  const column = (input || "").trim();
  if (!column) return;
  const lower = column.toLowerCase();
  if (["gid", "geometry"].includes(lower) || lower.startsWith("__")) return;
  if (activeDataset.value.extraColumns.includes(column)) return;
  activeDataset.value.extraColumns = [...activeDataset.value.extraColumns, column];
  activeDataset.value.rows.forEach((row) => {
    if (!(column in row.properties)) {
      row.properties[column] = "";
      if (row.feature?.properties) {
        row.feature.properties[column] = "";
      }
    }
  });
};

const ensureSelectedRowVisible = (featureKey) => {
  const rowIndex = filteredRows.value.findIndex((row) => row.featureKey === featureKey);
  if (rowIndex === -1) return false;
  currentPage.value = Math.floor(rowIndex / pageSize.value) + 1;
  return true;
};

const clearSelection = () => {
  selectedFeatureKey.value = "";
  syncHighlightFilters();
  if (mapPopup) {
    mapPopup.remove();
    mapPopup = null;
  }
};

const getDatasetPointLayerId = (datasetId) => `${pointLayerPrefix}${datasetId}`;
const getDatasetPointSourceId = (datasetId) => `${pointSourcePrefix}${datasetId}`;

const getInteractiveLayerIds = () => [
  "viz-fill",
  "viz-polygon-outline",
  "viz-line",
  ...datasets.value.map((dataset) => getDatasetPointLayerId(dataset.id)),
  "viz-highlight-fill",
  "viz-highlight-polygon-outline",
  "viz-highlight-line",
  "viz-highlight-point",
].filter((layerId) => map?.getLayer(layerId));


const cloneStyleConfig = (config) => JSON.parse(JSON.stringify(config));

const getDatasetStyle = (datasetId) => datasetStyles.value[datasetId] || createDefaultDatasetStyle();

const buildDatasetMatchExpression = (valueResolver, fallback) => {
  const expr = ["match", ["to-string", ["coalesce", ["get", "__datasetId"], ""]]];
  datasets.value.forEach((dataset) => {
    expr.push(String(dataset.id), valueResolver(dataset.id));
  });
  expr.push(fallback);
  return expr;
};

const applySharedGeometryStyles = () => {
  if (!mapReady.value || !map) return;
  if (map.getLayer("viz-line")) {
    map.setPaintProperty("viz-line", "line-color", buildDatasetMatchExpression((id) => getDatasetStyle(id).line.color, "#0ea5e9"));
    map.setPaintProperty("viz-line", "line-width", buildDatasetMatchExpression((id) => getDatasetStyle(id).line.width, 3));
    map.setPaintProperty("viz-line", "line-opacity", buildDatasetMatchExpression((id) => getDatasetStyle(id).line.opacity, 1));
  }
  if (map.getLayer("viz-fill")) {
    map.setPaintProperty("viz-fill", "fill-color", buildDatasetMatchExpression((id) => getDatasetStyle(id).polygon.fillColor, "#2563eb"));
    map.setPaintProperty("viz-fill", "fill-opacity", buildDatasetMatchExpression((id) => getDatasetStyle(id).polygon.fillOpacity, 0.2));
  }
  if (map.getLayer("viz-polygon-outline")) {
    map.setPaintProperty("viz-polygon-outline", "line-color", buildDatasetMatchExpression((id) => getDatasetStyle(id).polygon.lineColor, "#1d4ed8"));
    map.setPaintProperty("viz-polygon-outline", "line-width", buildDatasetMatchExpression((id) => getDatasetStyle(id).polygon.lineWidth, 1));
  }
};

const applyDatasetPointStyle = (datasetId) => {
  if (!mapReady.value || !map) return;
  const layerId = getDatasetPointLayerId(datasetId);
  const style = getDatasetStyle(datasetId).point;
  if (!map.getLayer(layerId)) return;
  map.setPaintProperty(layerId, "circle-color", style.color);
  map.setPaintProperty(layerId, "circle-radius", style.radius);
  map.setPaintProperty(layerId, "circle-opacity", style.opacity);
  map.setPaintProperty(layerId, "circle-stroke-color", style.strokeColor);
  map.setPaintProperty(layerId, "circle-stroke-width", style.strokeWidth);
};

const openStyleConfig = (datasetId) => {
  styleConfigDatasetId.value = datasetId;
  styleDraft.value = cloneStyleConfig(getDatasetStyle(datasetId));
};

const closeStyleConfig = () => {
  styleConfigDatasetId.value = null;
};

const saveStyleConfig = () => {
  const datasetId = styleConfigDatasetId.value;
  if (datasetId == null) return;
  datasetStyles.value = {
    ...datasetStyles.value,
    [datasetId]: cloneStyleConfig(styleDraft.value),
  };
  applyDatasetPointStyle(datasetId);
  applySharedGeometryStyles();
  closeStyleConfig();
};

const ensureDatasetPointLayer = (datasetId) => {
  if (!mapReady.value || !map) return;
  const sourceId = getDatasetPointSourceId(datasetId);
  const layerId = getDatasetPointLayerId(datasetId);

  if (!map.getSource(sourceId)) {
    map.addSource(sourceId, {
      type: "geojson",
      data: { type: "FeatureCollection", features: [] },
    });
  }

  if (!map.getLayer(layerId)) {
    map.addLayer({
      id: layerId,
      type: "circle",
      source: sourceId,
      paint: {
        "circle-color": "#f97316",
        "circle-radius": 6,
        "circle-stroke-color": "#fff",
        "circle-stroke-width": 1,
      },
    });
  }

  applyDatasetPointStyle(datasetId);
};

const removeDatasetPointLayer = (datasetId) => {
  if (!map) return;
  const sourceId = getDatasetPointSourceId(datasetId);
  const layerId = getDatasetPointLayerId(datasetId);
  if (map.getLayer(layerId)) map.removeLayer(layerId);
  if (map.getSource(sourceId)) map.removeSource(sourceId);
};

const ensureMap = () => {
  if (!props.mapApiKey || !mapContainer.value || map) return;
  mapboxgl.accessToken = props.mapApiKey;
  map = new mapboxgl.Map({
    container: mapContainer.value,
    style: "mapbox://styles/mapbox/streets-v12",
    projection: "mercator",
    center: [116.397, 39.908],
    zoom: 4,
  });

  map.addControl(new mapboxgl.NavigationControl(), "top-right");
  map.addControl(new mapboxgl.FullscreenControl(), "top-right");

  map.on("load", () => {
    map.setProjection("mercator");
    mapReady.value = true;
    map.addSource("viz-source", { type: "geojson", data: { type: "FeatureCollection", features: [] } });
    map.addSource("viz-draw-source", { type: "geojson", data: { type: "FeatureCollection", features: [] } });

    map.addLayer({
      id: "viz-draw-polygon-fill",
      type: "fill",
      source: "viz-draw-source",
      filter: ["==", ["geometry-type"], "Polygon"],
      paint: { "fill-color": "#2563eb", "fill-opacity": 0.15 },
    });
    map.addLayer({
      id: "viz-draw-line",
      type: "line",
      source: "viz-draw-source",
      filter: ["in", ["geometry-type"], ["literal", ["LineString", "Polygon"]]],
      paint: {
        "line-color": "#2563eb",
        "line-width": 2,
        "line-dasharray": [2, 2],
      },
    });
    map.addLayer({
      id: "viz-draw-points",
      type: "circle",
      source: "viz-draw-source",
      filter: ["==", ["geometry-type"], "Point"],
      paint: {
        "circle-radius": 4,
        "circle-color": "#fff",
        "circle-stroke-color": "#2563eb",
        "circle-stroke-width": 2,
      },
    });
    map.addLayer({
      id: "viz-polygon-outline",
      type: "line",
      source: "viz-source",
      filter: ["==", ["geometry-type"], "Polygon"],
      paint: { "line-color": "#1d4ed8", "line-width": 1 },
    });
    map.addLayer({
      id: "viz-line",
      type: "line",
      source: "viz-source",
      filter: ["==", ["geometry-type"], "LineString"],
      paint: { "line-color": "#0ea5e9", "line-width": 3 },
    });
    map.addLayer({
      id: "viz-highlight-fill",
      type: "fill",
      source: "viz-source",
      filter: highlightFilter("Polygon"),
      paint: { "fill-color": "#f59e0b", "fill-opacity": 0.35 },
    });
    map.addLayer({
      id: "viz-highlight-polygon-outline",
      type: "line",
      source: "viz-source",
      filter: highlightFilter("Polygon"),
      paint: { "line-color": "#f59e0b", "line-width": 3 },
    });
    map.addLayer({
      id: "viz-highlight-line",
      type: "line",
      source: "viz-source",
      filter: highlightFilter("LineString"),
      paint: { "line-color": "#f59e0b", "line-width": 5 },
    });
    map.addLayer({
      id: "viz-highlight-point",
      type: "circle",
      source: "viz-source",
      filter: highlightFilter("Point"),
      paint: {
        "circle-color": "#f59e0b",
        "circle-radius": 8,
        "circle-stroke-color": "#fff",
        "circle-stroke-width": 2,
      },
    });

    map.on("click", (event) => {
      if (drawMode.value === "point") {
        appendRowsFromFeatures([
          {
            type: "Feature",
            geometry: { type: "Point", coordinates: [event.lngLat.lng, event.lngLat.lat] },
            properties: {},
          },
        ]);
        drawMode.value = "none";
        drawingCoords.value = [];
        return;
      }

      if (drawMode.value === "line" || drawMode.value === "polygon") {
        drawingCoords.value = [...drawingCoords.value, [event.lngLat.lng, event.lngLat.lat]];
        refreshDrawSource();
        return;
      }

      const hits = map.queryRenderedFeatures(event.point, { layers: getInteractiveLayerIds() });
      if (!hits.length) return clearSelection();
      selectFeatureFromMap(hits[0], event.lngLat);
    });

    map.on("dblclick", (event) => {
      if (drawMode.value !== "line" && drawMode.value !== "polygon") return;
      event.preventDefault();
      const committed = commitDrawingByMode();
      if (committed) {
        drawMode.value = "none";
      }
      drawingCoords.value = [];
    });

    map.on("mousemove", (event) => {
      if (drawMode.value !== "none") {
        map.getCanvas().style.cursor = "crosshair";
        if (drawingCoords.value.length > 0) {
          refreshDrawSource(event.lngLat);
        }
        return;
      }
      const hits = map.queryRenderedFeatures(event.point, { layers: getInteractiveLayerIds() });
      map.getCanvas().style.cursor = hits.length ? "pointer" : "";
    });


    applySharedGeometryStyles();
    refreshSource();
  });
};

const parseWkt = (text) => {
  const raw = text.trim();
  const upper = raw.toUpperCase();
  const extractPairs = (body) =>
    body
      .split(",")
      .map((pair) => pair.trim().split(/\s+/).map(Number))
      .filter((pair) => pair.length >= 2 && pair.every((value) => Number.isFinite(value)))
      .map((pair) => [pair[0], pair[1]]);

  if (upper.startsWith("POINT")) {
    const match = raw.match(/POINT\s*\(([^)]+)\)/i);
    if (!match) return null;
    const pair = match[1].trim().split(/\s+/).map(Number);
    if (pair.length < 2) return null;
    return { type: "Point", coordinates: [pair[0], pair[1]] };
  }
  if (upper.startsWith("LINESTRING")) {
    const match = raw.match(/LINESTRING\s*\(([^)]+)\)/i);
    if (!match) return null;
    return { type: "LineString", coordinates: extractPairs(match[1]) };
  }
  if (upper.startsWith("POLYGON")) {
    const match = raw.match(/POLYGON\s*\(\((.+)\)\)/i);
    if (!match) return null;
    return { type: "Polygon", coordinates: [extractPairs(match[1])] };
  }
  if (upper.startsWith("MULTIPOLYGON")) {
    const match = raw.match(/MULTIPOLYGON\s*\(\((.+)\)\)/i);
    if (!match) return null;
    const polygons = match[1]
      .split(/\)\s*\),\s*\(\(/)
      .map((segment) => [extractPairs(segment.replaceAll("(", "").replaceAll(")", ""))]);
    return { type: "MultiPolygon", coordinates: polygons };
  }
  return null;
};

const parseCsv = (text) => {
  const normalizedText = text.includes("\\n") ? text.replace(/\\r\\n/g, "\n").replace(/\\n/g, "\n") : text;
  const lines = normalizedText.split(/\r?\n/).filter(Boolean);
  if (lines.length < 2) return [];

  // Detect delimiter: comma or tab
  const firstLine = lines[0];
  const commaCount = (firstLine.match(/,/g) || []).length;
  const tabCount = (firstLine.match(/\t/g) || []).length;
  const delimiter = tabCount > commaCount ? "\t" : ",";

  const splitCsvLine = (line) => {
    const values = [];
    let current = "";
    let inQuotes = false;

    for (let i = 0; i < line.length; i += 1) {
      const char = line[i];
      const next = line[i + 1];

      if (char === '"') {
        if (inQuotes && next === '"') {
          current += '"';
          i += 1;
        } else {
          inQuotes = !inQuotes;
        }
        continue;
      }

      if (char === delimiter && !inQuotes) {
        values.push(current.trim());
        current = "";
        continue;
      }

      current += char;
    }

    values.push(current.trim());
    return values;
  };

  const headers = splitCsvLine(lines[0]).map((header) => header.trim());
  return lines.slice(1).map((line) => {
    const values = splitCsvLine(line);
    const row = {};
    headers.forEach((header, index) => {
      row[header] = values[index]?.trim() ?? "";
    });
    return row;
  });
};

const parseCoordinatePairsString = (value) => {
  if (typeof value !== "string" || !value.trim()) return null;
  const pairs = value
    .split(",")
    .map((segment) => segment.trim().split(/\s+/).map(Number))
    .filter((pair) => pair.length >= 2 && Number.isFinite(pair[0]) && Number.isFinite(pair[1]))
    .map((pair) => [pair[0], pair[1]]);

  if (pairs.length < 2) return null;
  if (pairs.length >= 4) {
    const first = pairs[0];
    const last = pairs[pairs.length - 1];
    const isClosed = first[0] === last[0] && first[1] === last[1];
    return {
      type: "Polygon",
      coordinates: [isClosed ? pairs : [...pairs, first]],
    };
  }
  return { type: "LineString", coordinates: pairs };
};

const detectGeometryFromRow = (row) => {
  const keys = Object.keys(row);
  const lowerKeyMap = Object.fromEntries(keys.map((key) => [key.toLowerCase(), key]));
  const normalizeHeaderKey = (key) => key.toLowerCase().replace(/[\s_-]/g, "");
  const normalizedKeyMap = Object.fromEntries(keys.map((key) => [normalizeHeaderKey(key), key]));

  const wktKey = Object.keys(lowerKeyMap).find((key) =>
    ["wkt", "geometry", "geom", "the_geom"].some((field) => key.includes(field))
  );
  if (wktKey && typeof row[lowerKeyMap[wktKey]] === "string") {
    const maybeGeometry = parseWkt(row[lowerKeyMap[wktKey]]);
    if (maybeGeometry) return maybeGeometry;
    try {
      const geometry = JSON.parse(row[lowerKeyMap[wktKey]]);
      if (geometry?.type && geometry?.coordinates) return geometry;
    } catch {
      // ignore json parse error
    }
  }

  const lngAliases = ["lng", "lon", "long", "longitude", "x", "经度", "经"];
  const latAliases = ["lat", "latitude", "y", "纬度", "纬"];
  const lngKey = Object.keys(normalizedKeyMap).find((key) => lngAliases.includes(key));
  const latKey = Object.keys(normalizedKeyMap).find((key) => latAliases.includes(key));
  if (lngKey && latKey) {
    const lng = Number(row[normalizedKeyMap[lngKey]]);
    const lat = Number(row[normalizedKeyMap[latKey]]);
    if (Number.isFinite(lng) && Number.isFinite(lat)) {
      return { type: "Point", coordinates: [lng, lat] };
    }
  }

  const coordsKey = Object.keys(lowerKeyMap).find((key) =>
    ["coords", "coordinates", "path", "boundary"].some((field) => key.includes(field))
  );
  if (coordsKey) {
    const coordValue = row[lowerKeyMap[coordsKey]];
    try {
      const parsed = JSON.parse(coordValue);
      if (Array.isArray(parsed)) {
        if (typeof parsed[0] === "number") return { type: "Point", coordinates: parsed };
        if (Array.isArray(parsed[0]) && typeof parsed[0][0] === "number") {
          return { type: "LineString", coordinates: parsed };
        }
        if (Array.isArray(parsed[0]) && Array.isArray(parsed[0][0])) {
          return { type: "Polygon", coordinates: parsed };
        }
      }
    } catch {
      const parsedPairs = parseCoordinatePairsString(coordValue);
      if (parsedPairs) return parsedPairs;
    }
  }

  return null;
};

const parseContentToFeatures = (text) => {
  const trimmed = text.trim();
  if (!trimmed) return [];

  try {
    const json = JSON.parse(trimmed);
    if (json.type === "FeatureCollection") return json.features || [];
    if (json.type === "Feature") return [json];
    if (json.type && json.coordinates) return [{ type: "Feature", geometry: json, properties: {} }];
  } catch {
    // ignore json parse error
  }

  if (/^(POINT|LINESTRING|POLYGON|MULTIPOLYGON)/i.test(trimmed)) {
    return trimmed
      .split(/\r?\n/)
      .map((line) => parseWkt(line))
      .filter(Boolean)
      .map((geometry) => ({ type: "Feature", geometry, properties: {} }));
  }

  return parseCsv(trimmed)
    .map((row) => {
      const geometry = detectGeometryFromRow(row);
      if (!geometry) return null;
      return { type: "Feature", geometry, properties: row };
    })
    .filter(Boolean);
};

const appendRowsFromFeatures = (features) => {
  if (!activeDataset.value) return;
  const start = activeDataset.value.rows.length + 1;

  const nextRows = features.map((feature, index) => {
    const gid = start + index;
    const featureKey = `d${activeDataset.value.id}-f${featureCounter.value}`;
    featureCounter.value += 1;
    
    // Sanitize feature to avoid circular structures (especially from Mapbox queryRenderedFeatures)
    const sanitizedFeature = {
      type: feature.type || "Feature",
      geometry: feature.geometry,
      properties: { ...(feature.properties || {}) }
    };

    const normalizedFeature = {
      ...sanitizedFeature,
      properties: {
        ...sanitizedFeature.properties,
        __gid: gid,
        __datasetId: activeDataset.value.id,
        __featureKey: featureKey,
      },
    };

    return {
      gid,
      featureKey,
      geometryType: normalizedFeature.geometry?.type || "Unknown",
      properties: normalizedFeature.properties || {},
      feature: normalizedFeature,
    };
  });

  const extraColumns = new Set(activeDataset.value.extraColumns);
  nextRows.forEach((row) => {
    Object.keys(row.properties || {}).forEach((key) => {
      if (!key.toLowerCase().startsWith("__") && !["gid", "geometry"].includes(key.toLowerCase())) {
        extraColumns.add(key);
      }
    });
  });

  activeDataset.value.rows.push(...nextRows);
  activeDataset.value.extraColumns = Array.from(extraColumns);
  ensureValidGeometryFilter();
  refreshSource();
};

const refreshSource = () => {
  if (!mapReady.value || !map) return;
  const allFeatures = datasets.value
    .filter((d) => d.visible !== false)
    .flatMap((dataset) => dataset.rows.map((row) => row.feature));
  map.getSource("viz-source")?.setData({ type: "FeatureCollection", features: allFeatures });

  datasets.value.forEach((dataset) => {
    ensureDatasetPointLayer(dataset.id);
    const sourceId = getDatasetPointSourceId(dataset.id);
    const pointFeatures = dataset.visible !== false
      ? dataset.rows
          .map((row) => row.feature)
          .filter((feature) => feature?.geometry?.type === "Point")
      : [];
    map.getSource(sourceId)?.setData({ type: "FeatureCollection", features: pointFeatures });
  });
  applySharedGeometryStyles();
};

const addDataset = () => {
  const nextId = Math.max(...datasets.value.map((dataset) => dataset.id)) + 1;
  datasets.value.push({ id: nextId, name: `数据集 ${nextId}`, rows: [], extraColumns: [], visible: true, filters: {} });
  datasetStyles.value = { ...datasetStyles.value, [nextId]: createDefaultDatasetStyle() };
  activeDatasetId.value = nextId;
};

const toggleDatasetVisibility = (datasetId) => {
  const dataset = datasets.value.find((d) => d.id === datasetId);
  if (dataset) {
    dataset.visible = dataset.visible === false ? true : false;
    refreshSource();
  }
};

const removeDataset = (datasetId) => {
  if (datasets.value.length <= 1) return;
  datasets.value = datasets.value.filter((dataset) => dataset.id !== datasetId);
  const nextStyles = { ...datasetStyles.value };
  delete nextStyles[datasetId];
  datasetStyles.value = nextStyles;
  removeDatasetPointLayer(datasetId);
  if (activeDatasetId.value === datasetId) {
    activeDatasetId.value = datasets.value[0]?.id ?? 1;
  }
  if (styleConfigDatasetId.value === datasetId) {
    closeStyleConfig();
  }
  clearSelection();
  refreshSource();
};

const waitForMapFlush = async () => {
  await nextTick();
  await new Promise((resolve) => {
    requestAnimationFrame(() => requestAnimationFrame(resolve));
  });
};

const importFeaturesWithMask = async (rawText) => {
  if (!rawText) return;
  isProcessing.value = true;
  try {
    const features = parseContentToFeatures(rawText);
    appendRowsFromFeatures(features);
    await waitForMapFlush();
  } finally {
    isProcessing.value = false;
  }
};

const triggerFilePicker = () => {
  dataFileInput.value?.click();
};

const handleDragOver = () => {
  isDragging.value = true;
};

const handleDragLeave = () => {
  isDragging.value = false;
};

const handleFileDrop = async (event) => {
  isDragging.value = false;
  const file = event.dataTransfer?.files?.[0];
  if (!file) return;
  
  // Trigger flash animation
  dropzoneFlash.value = true;
  setTimeout(() => {
    dropzoneFlash.value = false;
  }, 600);

  await processFile(file);
};

const processFile = async (file) => {
  if (!file) return;

  isProcessing.value = true;
  try {
    const extension = file.name.split(".").pop()?.toLowerCase();
    let features = [];

    if (extension === "xlsx" || extension === "xls") {
      const data = await file.arrayBuffer();
      const workbook = XLSX.read(new Uint8Array(data), { type: "array" });
      const sheet = workbook.Sheets[workbook.SheetNames[0]];
      const rows = XLSX.utils.sheet_to_json(sheet);
      features = rows
        .map((row) => {
          const geometry = detectGeometryFromRow(row);
          if (!geometry) return null;
          return { type: "Feature", geometry, properties: row };
        })
        .filter(Boolean);
    } else {
      const text = await file.text();
      features = parseContentToFeatures(text);
    }

    if (features.length > 0) {
      appendRowsFromFeatures(features);
      await waitForMapFlush();
    }
  } catch (error) {
    console.error("文件上传解析失败:", error);
    alert("文件解析失败，请检查文件格式是否正确。");
  } finally {
    isProcessing.value = false;
  }
};

const handleFileUpload = async (event) => {
  const file = event.target.files?.[0];
  if (!file) return;
  await processFile(file);
  event.target.value = "";
};

const handlePasteImport = async () => {
  await importFeaturesWithMask(pasteInput.value);
  pasteInput.value = "";
};

const clearPasteInput = () => {
  pasteInput.value = "";
};

const extractBounds = (geometry) => {
  const values = JSON.stringify(geometry?.coordinates || [])
    .match(/-?\d+(\.\d+)?/g)
    ?.map(Number);
  if (!values || values.length < 2) return null;
  const lngs = values.filter((_, index) => index % 2 === 0);
  const lats = values.filter((_, index) => index % 2 === 1);
  if (!lngs.length || !lats.length) return null;
  return {
    minLng: Math.min(...lngs),
    minLat: Math.min(...lats),
    maxLng: Math.max(...lngs),
    maxLat: Math.max(...lats),
  };
};

const popupHtml = (properties = {}) => {
  const entries = Object.entries(properties).filter(([key]) => !key.startsWith("__"));
  if (!entries.length) return "<div style='font-size:12px;color:#64748b'>无扩展属性</div>";
  return `<div style='min-width:180px'>${entries
    .map(
      ([key, value]) =>
        `<div style='display:flex;gap:8px;font-size:12px;line-height:1.5'><strong style='min-width:80px'>${key}</strong><span>${
          value === "" || value == null ? "-" : String(value)
        }</span></div>`
    )
    .join("")}</div>`;
};

const focusRow = async (featureKey) => {
  await nextTick();
  await nextTick();
  const el = rowElementMap.get(featureKey);
  if (el) {
    el.scrollIntoView({ behavior: "smooth", block: "center" });
  }
};

const selectFeatureByMeta = async ({ datasetId, featureKey, lngLat, properties }) => {
  if (!featureKey) return;
  if (datasetId && activeDatasetId.value !== datasetId) {
    activeDatasetId.value = datasetId;
    await nextTick();
  }
  const datasetRows = (activeDataset.value?.rows || []);
  const targetRow = datasetRows.find((row) => row.featureKey === featureKey);
  if (targetRow) {
    const targetGroup = resolveGeometryGroup(targetRow.geometryType);
    if (targetGroup && geometryFilter.value !== targetGroup) {
      geometryFilter.value = targetGroup;
    }
    ensureSelectedRowVisible(featureKey);
  }

  selectedFeatureKey.value = featureKey;
  syncHighlightFilters();
  await focusRow(featureKey);

  if (mapPopup) {
    mapPopup.remove();
    mapPopup = null;
  }
  if (lngLat && map) {
    mapPopup = new mapboxgl.Popup({ closeButton: false, offset: 14 })
      .setLngLat(lngLat)
      .setHTML(popupHtml(properties))
      .addTo(map);
  }
};

const selectFeatureFromMap = async (feature, lngLat) => {
  const datasetId = Number(feature?.properties?.__datasetId);
  const featureKey = feature?.properties?.__featureKey || "";
  await selectFeatureByMeta({ datasetId, featureKey, lngLat, properties: feature?.properties || {} });
};

const locateFeature = async (row) => {
  if (!mapReady.value || !row?.feature?.geometry) return;
  const geometry = row.feature.geometry;

  if (geometry.type === "Point") {
    map.flyTo({ center: geometry.coordinates, zoom: 12 });
    await selectFeatureByMeta({
      datasetId: activeDatasetId.value,
      featureKey: row.featureKey,
      lngLat: { lng: geometry.coordinates[0], lat: geometry.coordinates[1] },
      properties: row.properties,
    });
    return;
  }

  const bounds = extractBounds(geometry);
  if (bounds) {
    map.fitBounds(
      [
        [bounds.minLng, bounds.minLat],
        [bounds.maxLng, bounds.maxLat],
      ],
      { padding: 40 }
    );
    await selectFeatureByMeta({
      datasetId: activeDatasetId.value,
      featureKey: row.featureKey,
      lngLat: { lng: (bounds.minLng + bounds.maxLng) / 2, lat: (bounds.minLat + bounds.maxLat) / 2 },
      properties: row.properties,
    });
  }
};

const removeFeature = (featureKey) => {
  if (!activeDataset.value) return;
  activeDataset.value.rows = activeDataset.value.rows.filter((row) => row.featureKey !== featureKey);
  if (selectedFeatureKey.value === featureKey) {
    clearSelection();
  }
  ensureValidGeometryFilter();
  refreshSource();
};

const STORAGE_KEY = "map_viz_app_state";

const saveState = () => {
  try {
    const state = {
      datasets: datasets.value,
      datasetStyles: datasetStyles.value,
      activeDatasetId: activeDatasetId.value,
      geometryFilter: geometryFilter.value,
      currentPage: currentPage.value,
      pageSize: pageSize.value,
      featureCounter: featureCounter.value,
    };
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  } catch (e) {
    console.warn("Failed to save state to localStorage (possibly quota exceeded)", e);
  }
};

const loadState = () => {
  const saved = localStorage.getItem(STORAGE_KEY);
  if (saved) {
    try {
      const state = JSON.parse(saved);
      if (state.datasets) datasets.value = state.datasets;
      if (state.datasetStyles) datasetStyles.value = state.datasetStyles;
      if (state.activeDatasetId) activeDatasetId.value = state.activeDatasetId;
      if (state.geometryFilter) geometryFilter.value = state.geometryFilter;
      if (state.currentPage) currentPage.value = state.currentPage;
      if (state.pageSize) pageSize.value = state.pageSize;
      if (state.featureCounter) featureCounter.value = state.featureCounter;
    } catch (e) {
      console.error("Failed to load state from localStorage", e);
    }
  }
  isLoaded.value = true;
};

loadState();

onMounted(() => {
  ensureMap();
});

watch(
  [datasets, datasetStyles, activeDatasetId, geometryFilter, currentPage, pageSize, featureCounter],
  () => {
    saveState();
  },
  { deep: true }
);

watch(
  () => props.mapApiKey,
  () => {
    ensureMap();
  }
);

watch(selectedFeatureKey, () => {
  syncHighlightFilters();
});

watch(activeDatasetId, () => {
  clearSelection();
  cancelEditCell();
  ensureValidGeometryFilter();
  currentPage.value = 1;
});


watch(drawMode, (mode) => {
  if (!map) return;
  if (mode === "line" || mode === "polygon") {
    map.doubleClickZoom.disable();
  } else {
    map.doubleClickZoom.enable();
  }
  if (mode === "none") {
    drawingCoords.value = [];
  }
  map.getCanvas().style.cursor = mode === "none" ? "" : "crosshair";
});

onBeforeUnmount(() => {
  if (mapPopup) {
    mapPopup.remove();
    mapPopup = null;
  }
  if (map) map.remove();
});
</script>
