import { computed, nextTick, onMounted, reactive, ref, watch } from "vue";
import mapboxgl from "mapbox-gl";
import * as XLSX from "xlsx";

export function useNetworkToolsApp() {

const headers = ref([]);
const rows = ref([]);
const fileName = ref("");
const columnName = ref("");
const latColumnName = ref("");
const lngColumnName = ref("");
const reverseColumnMode = ref("separate");
const reverseColumnName = ref("");
const reverseDelimiterMode = ref("auto");
const reverseDelimiter = ref(",");
const startColumnName = ref("");
const endColumnName = ref("");
const routeInputMode = ref("address");
const provider = ref("mapbox");
const providerApiKey = ref("");
const mapboxGeocodeApiKey = ref("");
const hereGeocodeApiKey = ref("");
const customAppId = ref("");
const customCredential = ref("");
const customTokenUrl = ref("");
const customGeocodeUrl = ref("");
const customRouteUrl = ref("");
const customToken = ref("");
const defaultWebSocketUrl = () => {
  if (typeof window === "undefined") return "ws://sim.isc.huawei.com:8765";
  const protocol = window.location.protocol === "https:" ? "wss" : "ws";
  const hostname = window.location.hostname;
  const resolvedHost =
    hostname === "0.0.0.0" || hostname === "localhost" || hostname === "127.0.0.1"
      ? "sim.isc.huawei.com"
      : hostname;
  return `${protocol}://${resolvedHost}:8765`;
};
const customWebSocketUrl = ref(defaultWebSocketUrl());
const customSocket = ref(null);
const mapApiKey = ref("");
const logs = ref([]);
const showSettings = ref(false);
const settingsNotice = ref("");
const configFileInput = ref(null);
const geocodeCache = new Map();
const reverseCache = new Map();
const routeCache = new Map();
const PERSISTENT_CACHE_BATCH = 100;
const REALTIME_REFRESH_INTERVAL_MS = 250;
const persistentCacheBuckets = {
  geocode: new Map(),
  reverse: new Map(),
  route: new Map(),
};

const buildPersistentScope = (type) => {
  if (provider.value === "custom") {
    if (type === "geocode") return `custom|${customGeocodeUrl.value || "default"}`;
    if (type === "route") return `custom|${customRouteUrl.value || "default"}`;
    return "custom|reverse";
  }
  return `${provider.value}|${type}`;
};

const getPersistentStorageKey = (type, scope) =>
  `network_tools_cache_v1_${type}_${encodeURIComponent(scope)}`;

const getPersistentBucket = (type, scope) => {
  const scopedBuckets = persistentCacheBuckets[type];
  if (!scopedBuckets) return null;
  if (scopedBuckets.has(scope)) {
    return scopedBuckets.get(scope);
  }

  const storageKey = getPersistentStorageKey(type, scope);
  let map = new Map();
  try {
    const raw = localStorage.getItem(storageKey);
    if (raw) {
      const parsed = JSON.parse(raw);
      if (parsed && typeof parsed === "object") {
        map = new Map(Object.entries(parsed));
      }
    }
  } catch (error) {
    map = new Map();
  }

  const bucket = { storageKey, map, pending: 0 };
  scopedBuckets.set(scope, bucket);
  return bucket;
};

const flushPersistentBucket = (bucket) => {
  if (!bucket || bucket.pending <= 0) return;
  const serialized = Object.fromEntries(bucket.map.entries());
  localStorage.setItem(bucket.storageKey, JSON.stringify(serialized));
  bucket.pending = 0;
};

const flushAllPersistentCaches = () => {
  Object.values(persistentCacheBuckets).forEach((scopedBuckets) => {
    scopedBuckets.forEach((bucket) => {
      flushPersistentBucket(bucket);
    });
  });
};

const getPersistentCacheValue = (type, requestKey) => {
  const scope = buildPersistentScope(type);
  const bucket = getPersistentBucket(type, scope);
  if (!bucket) return null;
  return bucket.map.get(requestKey);
};

const setPersistentCacheValue = (type, requestKey, value) => {
  if (!requestKey) return;
  const scope = buildPersistentScope(type);
  const bucket = getPersistentBucket(type, scope);
  if (!bucket) return;
  bucket.map.set(requestKey, value);
  bucket.pending += 1;
  if (bucket.pending >= PERSISTENT_CACHE_BATCH) {
    flushPersistentBucket(bucket);
  }
};


const cacheAndReturn = (type, requestKey, result) => {
  setPersistentCacheValue(type, requestKey, result);
  return result;
};
const handledRouteIndices = new Set();
const renderedPointKeys = new Set();
const renderedRouteKeys = new Set();
const mapContainer = ref(null);
const mapLoaded = ref(false);
const isDragging = ref(false);
const dropzoneFlash = ref(false);
const mockAnimating = ref(false);
const mapRealtimeUpdate = ref(true);
const geocodeState = reactive({
  total: 0,
  processed: 0,
  current: "",
  running: false,
});
const points = ref([]);
const routeLines = ref([]);
const mode = ref("visualize");

const modeOptions = [
  { value: "visualize", label: "地图可视化" },
  { value: "geocode", label: "地址编码" },
  { value: "reverse", label: "经纬度解码" },
  { value: "route", label: "导航距离计算" },
];

let mapInstance = null;
let mapMarkers = [];
let routePopup = null;
let realtimeRefreshTimer = null;
let realtimeRefreshPendingFitBounds = false;
let routeHoverHandlers = null;
const routeSourceId = "route-line";
const routeLayerId = "route-line";

const storageKeys = {
  provider: "geocode_provider",
  mapboxGeocode: "mapbox_geocode_api_key",
  hereGeocode: "here_geocode_api_key",
  mapboxMap: "mapbox_map_api_key",
  customAppId: "custom_app_id",
  customCredential: "custom_credential",
  customTokenUrl: "custom_token_url",
  customGeocodeUrl: "custom_geocode_url",
  customRouteUrl: "custom_route_url",
  customWebSocketUrl: "custom_websocket_url",
  columnName: "geocode_column_name",
  latColumnName: "reverse_lat_column_name",
  lngColumnName: "reverse_lng_column_name",
  reverseColumnMode: "reverse_column_mode",
  reverseColumnName: "reverse_column_name",
  reverseDelimiterMode: "reverse_delimiter_mode",
  reverseDelimiter: "reverse_delimiter",
  startColumnName: "route_start_column_name",
  endColumnName: "route_end_column_name",
  routeInputMode: "route_input_mode",
  mode: "geocode_mode",
  mapRealtimeUpdate: "map_realtime_update",
};

const getProviderStorageKey = (currentProvider) =>
  currentProvider === "mapbox" ? storageKeys.mapboxGeocode : storageKeys.hereGeocode;

const normalizeCoordinate = (value) => {
  const num = Number(value);
  if (!Number.isFinite(num)) return null;
  return Number(num.toFixed(6));
};

const coordPairKey = (lat, lng) => {
  const normalizedLat = normalizeCoordinate(lat);
  const normalizedLng = normalizeCoordinate(lng);
  if (!Number.isFinite(normalizedLat) || !Number.isFinite(normalizedLng)) {
    return "";
  }
  return `${normalizedLat.toFixed(6)},${normalizedLng.toFixed(6)}`;
};

const routePairKey = (originLat, originLng, destinationLat, destinationLng) => {
  const originKey = coordPairKey(originLat, originLng);
  const destinationKey = coordPairKey(destinationLat, destinationLng);
  if (!originKey || !destinationKey) {
    return "";
  }
  return `${originKey}->${destinationKey}`;
};

const buildPointKey = (point) => {
  const coordKey = coordPairKey(point.lat, point.lng);
  if (!coordKey) return "";
  return [
    point.type || "point",
    coordKey,
    point.address || "",
    point.label || "",
    point.displayMode || "",
  ].join("|");
};

const pushPointIfNeeded = (point) => {
  const lat = normalizeCoordinate(point.lat);
  const lng = normalizeCoordinate(point.lng);
  if (!Number.isFinite(lat) || !Number.isFinite(lng)) {
    return false;
  }
  const normalizedPoint = {
    ...point,
    lat,
    lng,
  };
  const key = buildPointKey(normalizedPoint);
  if (!key || renderedPointKeys.has(key)) {
    return false;
  }
  renderedPointKeys.add(key);
  points.value.push(normalizedPoint);
  return true;
};

const buildRouteLineKey = (line) => {
  const coordinates = line?.geometry?.coordinates;
  if (!Array.isArray(coordinates) || coordinates.length < 2) return "";
  const first = coordinates[0];
  const last = coordinates[coordinates.length - 1];
  return routePairKey(first?.[1], first?.[0], last?.[1], last?.[0]);
};

const pushRouteLineIfNeeded = (line) => {
  const coordinates = line?.geometry?.coordinates;
  if (!Array.isArray(coordinates) || coordinates.length < 2) {
    return false;
  }
  const normalizedCoordinates = coordinates.map((coord) => [
    normalizeCoordinate(coord?.[0]),
    normalizeCoordinate(coord?.[1]),
  ]);
  if (
    normalizedCoordinates.some(
      (coord) => !Number.isFinite(coord[0]) || !Number.isFinite(coord[1])
    )
  ) {
    return false;
  }

  const normalizedLine = {
    ...line,
    geometry: {
      ...line.geometry,
      coordinates: normalizedCoordinates,
    },
  };

  const key = buildRouteLineKey(normalizedLine);
  if (!key || renderedRouteKeys.has(key)) {
    return false;
  }
  renderedRouteKeys.add(key);
  routeLines.value.push(normalizedLine);
  return true;
};

const canStart = computed(() => {
  if (geocodeState.running || rows.value.length === 0) {
    return false;
  }
  if (provider.value === "custom") {
    if (mode.value === "reverse") {
      return false;
    }
    if (mode.value === "route") {
      return Boolean(
        customAppId.value &&
          customCredential.value &&
          customTokenUrl.value &&
          (routeInputMode.value === "address" ? customGeocodeUrl.value : true) &&
          customRouteUrl.value &&
          customWebSocketUrl.value &&
          startColumnName.value &&
          endColumnName.value
      );
    }
    return Boolean(
      customAppId.value &&
        customCredential.value &&
        customTokenUrl.value &&
        customGeocodeUrl.value &&
        customWebSocketUrl.value &&
        columnName.value
    );
  }
  if (!providerApiKey.value) {
    return false;
  }
  if (mode.value === "geocode") {
    return Boolean(columnName.value);
  }
  if (mode.value === "reverse") {
    if (reverseColumnMode.value === "single") {
      return Boolean(
        reverseColumnName.value &&
          (reverseDelimiterMode.value === "auto" || reverseDelimiter.value)
      );
    }
    return Boolean(latColumnName.value && lngColumnName.value);
  }
  return Boolean(startColumnName.value && endColumnName.value);
});

const canDownload = computed(() => {
  if (geocodeState.running) {
    return false;
  }
  if (mode.value === "route") {
    return rows.value.length > 0;
  }
  return rows.value.length > 0 && points.value.length > 0;
});

const hasData = computed(() => rows.value.length > 0);

const headerTitle = computed(() => {
  if (mode.value === "visualize") {
    return "地图数据可视化";
  }
  if (mode.value === "reverse") {
    return "Excel 经纬度批量解析地址";
  }
  if (mode.value === "route") {
    return "Excel 批量导航距离计算";
  }
  return "Excel 地址批量转经纬度";
});

const startLabel = computed(() => {
  if (mode.value === "reverse") return "开始解码";
  if (mode.value === "route") return "开始计算";
  return "开始转换";
});

const progressLabel = computed(() => {
  if (mode.value === "reverse") return "当前经纬度";
  if (mode.value === "route") return "当前路线";
  return "当前地址";
});

const progress = computed(() => {
  const percent = geocodeState.total
    ? Math.round((geocodeState.processed / geocodeState.total) * 100)
    : 0;
  return {
    current: geocodeState.current,
    processed: geocodeState.processed,
    pending: Math.max(geocodeState.total - geocodeState.processed, 0),
    percent,
  };
});

const resetProgress = () => {
  geocodeState.total = 0;
  geocodeState.processed = 0;
  geocodeState.current = "";
  geocodeState.running = false;
};

const resetFileData = () => {
  headers.value = [];
  rows.value = [];
  fileName.value = "";
  columnName.value = "";
  latColumnName.value = "";
  lngColumnName.value = "";
  reverseColumnName.value = "";
  startColumnName.value = "";
  endColumnName.value = "";
  isDragging.value = false;
  dropzoneFlash.value = false;
  mockAnimating.value = false;
};

const resetResults = () => {
  logs.value = [];
  points.value = [];
  routeLines.value = [];
  geocodeCache.clear();
  reverseCache.clear();
  routeCache.clear();
  handledRouteIndices.clear();
  renderedPointKeys.clear();
  renderedRouteKeys.clear();
  closeCustomSocket();
  resetProgress();
  refreshMarkers();
};

const loadFile = (file) => {
  if (!file) return;
  fileName.value = file.name;
  triggerDropzoneFlash();

  const reader = new FileReader();
  reader.onload = (e) => {
    const data = new Uint8Array(e.target.result);
    const workbook = XLSX.read(data, { type: "array" });
    const sheetName = workbook.SheetNames[0];
    const sheet = workbook.Sheets[sheetName];
    const sheetRows = XLSX.utils.sheet_to_json(sheet, { header: 1, raw: false });
    if (sheetRows.length === 0) return;
    headers.value = sheetRows[0].filter(Boolean).map((header) => String(header));
    const bodyRows = sheetRows.slice(1).map((row) => {
      const record = {};
      headers.value.forEach((header, index) => {
        record[header] = row[index] ?? "";
      });
      return record;
    });
    rows.value = bodyRows;
    const savedColumn = localStorage.getItem(storageKeys.columnName);
    if (savedColumn && headers.value.includes(savedColumn)) {
      columnName.value = savedColumn;
    } else {
      columnName.value = headers.value[0] || "";
    }
    const savedLatColumn = localStorage.getItem(storageKeys.latColumnName);
    if (savedLatColumn && headers.value.includes(savedLatColumn)) {
      latColumnName.value = savedLatColumn;
    } else {
      latColumnName.value = guessColumn(headers.value, ["纬度", "lat"]);
    }
    const savedLngColumn = localStorage.getItem(storageKeys.lngColumnName);
    if (savedLngColumn && headers.value.includes(savedLngColumn)) {
      lngColumnName.value = savedLngColumn;
    } else {
      lngColumnName.value = guessColumn(headers.value, ["经度", "lng", "lon"]);
    }
    const savedReverseColumn = localStorage.getItem(storageKeys.reverseColumnName);
    if (savedReverseColumn && headers.value.includes(savedReverseColumn)) {
      reverseColumnName.value = savedReverseColumn;
    } else {
      reverseColumnName.value = guessColumn(headers.value, ["坐标", "经纬度"]);
    }
    const savedReverseMode = localStorage.getItem(storageKeys.reverseColumnMode);
    if (savedReverseMode === "single" || savedReverseMode === "separate") {
      reverseColumnMode.value = savedReverseMode;
    } else if (latColumnName.value && lngColumnName.value) {
      reverseColumnMode.value = "separate";
    } else if (reverseColumnName.value) {
      reverseColumnMode.value = "single";
    }
    const savedStartColumn = localStorage.getItem(storageKeys.startColumnName);
    if (savedStartColumn && headers.value.includes(savedStartColumn)) {
      startColumnName.value = savedStartColumn;
    } else {
      startColumnName.value = headers.value[0] || "";
    }
    const savedEndColumn = localStorage.getItem(storageKeys.endColumnName);
    if (savedEndColumn && headers.value.includes(savedEndColumn)) {
      endColumnName.value = savedEndColumn;
    } else {
      endColumnName.value = headers.value[1] || headers.value[0] || "";
    }
    const savedRouteInputMode = localStorage.getItem(storageKeys.routeInputMode);
    if (savedRouteInputMode === "address" || savedRouteInputMode === "coordinate") {
      routeInputMode.value = savedRouteInputMode;
    }
    resetResults();
  };
  reader.readAsArrayBuffer(file);
};

const handleFileChange = (event) => {
  const file = event.target.files?.[0];
  loadFile(file);
};

const handleDragOver = () => {
  isDragging.value = true;
};

const handleDragLeave = () => {
  isDragging.value = false;
};

const handleFileDrop = (event) => {
  const file = event.dataTransfer?.files?.[0];
  isDragging.value = false;
  loadFile(file);
};

const fillMockData = () => {
  triggerMockAnimation();
  if (mode.value === "reverse") {
    if (reverseColumnMode.value === "single") {
      headers.value = ["经纬度", "客户"];
      rows.value = [
        { 经纬度: "31.2304,121.4737", 客户: "星云科技" },
        { 经纬度: "39.9087,116.3974", 客户: "京华贸易" },
        { 经纬度: "22.5431,114.0579", 客户: "海风智能" },
        { 经纬度: "30.2741,120.1551", 客户: "知行数据" },
        { 经纬度: "30.5728,104.0668", 客户: "西蜀科技" },
      ];
      reverseColumnName.value = "经纬度";
      reverseDelimiterMode.value = "auto";
    } else {
      headers.value = ["纬度", "经度", "客户"];
      rows.value = [
        { 纬度: 31.2304, 经度: 121.4737, 客户: "星云科技" },
        { 纬度: 39.9087, 经度: 116.3974, 客户: "京华贸易" },
        { 纬度: 22.5431, 经度: 114.0579, 客户: "海风智能" },
        { 纬度: 30.2741, 经度: 120.1551, 客户: "知行数据" },
        { 纬度: 30.5728, 经度: 104.0668, 客户: "西蜀科技" },
      ];
      latColumnName.value = "纬度";
      lngColumnName.value = "经度";
    }
  } else if (mode.value === "route") {
    headers.value = ["起点", "终点", "客户"];
    rows.value = [
      { 起点: "上海虹桥站", 终点: "上海迪士尼", 客户: "星云科技" },
      { 起点: "北京南站", 终点: "北京首都机场", 客户: "京华贸易" },
      { 起点: "深圳北站", 终点: "深圳湾口岸", 客户: "海风智能" },
      { 起点: "杭州东站", 终点: "西湖风景区", 客户: "知行数据" },
      { 起点: "成都东站", 终点: "天府国际机场", 客户: "西蜀科技" },
    ];
    startColumnName.value = "起点";
    endColumnName.value = "终点";
  } else {
    headers.value = ["地址", "客户"];
    rows.value = [
      { 地址: "上海市浦东新区世纪大道100号", 客户: "星云科技" },
      { 地址: "北京市朝阳区三里屯路11号", 客户: "联动创新" },
      { 地址: "深圳市南山区科技园科苑路15号", 客户: "海风智能" },
      { 地址: "杭州市西湖区文三路90号", 客户: "知行数据" },
      { 地址: "成都市武侯区人民南路四段27号", 客户: "西蜀科技" },
      { 地址: "上海市浦东新区世纪大道100号", 客户: "星云科技" },
    ];
    columnName.value = "地址";
  }
  fileName.value = "mock.xlsx";
  resetResults();
  triggerDropzoneFlash();
};

const triggerDropzoneFlash = () => {
  dropzoneFlash.value = false;
  requestAnimationFrame(() => {
    dropzoneFlash.value = true;
    setTimeout(() => {
      dropzoneFlash.value = false;
    }, 600);
  });
};

const triggerMockAnimation = () => {
  mockAnimating.value = false;
  requestAnimationFrame(() => {
    mockAnimating.value = true;
    setTimeout(() => {
      mockAnimating.value = false;
    }, 500);
  });
};

const guessColumn = (headerList, keywords) => {
  const lowered = headerList.map((header) => header.toLowerCase());
  const hitIndex = lowered.findIndex((header) =>
    keywords.some((keyword) => header.includes(keyword))
  );
  return headerList[hitIndex] || "";
};

const buildAddressMap = () => {
  const addressMap = new Map();
  rows.value.forEach((row, index) => {
    const address = String(row[columnName.value] ?? "").trim();
    if (!address) return;
    if (!addressMap.has(address)) {
      addressMap.set(address, []);
    }
    addressMap.get(address).push(index);
  });
  return addressMap;
};

const buildRoutePayloads = () =>
  rows.value.map((row, index) => {
    const origin = String(row[startColumnName.value] ?? "").trim();
    const destination = String(row[endColumnName.value] ?? "").trim();
    return { index, origin, destination };
  });

const parseRouteCoordinate = (value) => {
  const raw = String(value ?? "").trim();
  if (!raw) {
    return { success: false, key: "-", message: "坐标为空" };
  }
  const delimiter = raw.includes(",") ? "," : raw.includes("，") ? "，" : "";
  if (!delimiter) {
    return { success: false, key: raw, message: "无法识别坐标分隔符" };
  }
  const parts = raw.split(delimiter).map((item) => item.trim());
  if (parts.length < 2) {
    return { success: false, key: raw, message: "坐标格式不完整" };
  }
  const lng = normalizeCoordinate(parts[0]);
  const lat = normalizeCoordinate(parts[1]);
  if (!Number.isFinite(lat) || !Number.isFinite(lng)) {
    return { success: false, key: raw, message: "经度或纬度不是有效数字" };
  }
  return {
    success: true,
    key: coordPairKey(lat, lng),
    lat,
    lng,
  };
};

const closeCustomSocket = () => {
  if (customSocket.value) {
    customSocket.value.close();
    customSocket.value = null;
  }
};

const startCustomGeocode = () => {
  if (!canStart.value) return;
  closeCustomSocket();
  logs.value = [];
  points.value = [];
  routeLines.value = [];
  renderedPointKeys.clear();
  renderedRouteKeys.clear();
  geocodeState.running = true;
  geocodeState.processed = 0;
  geocodeState.current = "";

  const addressMap = buildAddressMap();
  const addresses = Array.from(addressMap.keys());
  geocodeState.total = addresses.length;
  if (addresses.length === 0) {
    geocodeState.running = false;
    return;
  }

  let socket;
  try {
    socket = new WebSocket(customWebSocketUrl.value);
  } catch (error) {
    logs.value.push({
      address: "-",
      type: "network_error",
      request: customWebSocketUrl.value,
      response: `无法连接 WebSocket: ${String(error)}`,
    });
    geocodeState.running = false;
    return;
  }

  customSocket.value = socket;

  socket.onopen = () => {
    socket.send(
      JSON.stringify({
        type: "start",
        payload: {
          config: {
            appId: customAppId.value,
            credential: customCredential.value,
            tokenUrl: customTokenUrl.value,
            geocodeUrl: customGeocodeUrl.value,
          },
          addresses,
        },
      })
    );
  };

  socket.onmessage = (event) => {
    let message;
    try {
      message = JSON.parse(event.data);
    } catch (error) {
      logs.value.push({
        address: "-",
        type: "parse_error",
        request: "WebSocket",
        response: `无法解析后端返回: ${String(error)}`,
      });
      return;
    }

    if (message.type === "progress") {
      const payload = message.payload || {};
      const address = payload.address || "-";
      geocodeState.current = address;
      if (!Number.isFinite(messagePayload.processed)) {
        geocodeState.processed += 1;
      }

      if (payload.success) {
        const normalizedLat = normalizeCoordinate(payload.lat);
        const normalizedLng = normalizeCoordinate(payload.lng);
        const locationKey = coordPairKey(normalizedLat, normalizedLng);

        if (locationKey) {
          const geocodeResult = {
            success: true,
            lat: normalizedLat,
            lng: normalizedLng,
            key: locationKey,
          };
          geocodeCache.set(address, geocodeResult);
          setPersistentCacheValue("geocode", address, geocodeResult);

          const indices = addressMap.get(address) || [];
          indices.forEach((rowIndex) => {
            rows.value[rowIndex].纬度 = normalizedLat;
            rows.value[rowIndex].经度 = normalizedLng;
          });

          pushPointIfNeeded({
            lat: normalizedLat,
            lng: normalizedLng,
            address,
          });

          if (mapRealtimeUpdate.value) {
            scheduleRealtimeRefresh({ fitBounds: false });
          }
        } else {
          logs.value.push({
            address,
            type: "no_result",
            request: payload.request || "custom",
            response: "未返回可用经纬度",
          });
        }
      } else {
        setPersistentCacheValue("geocode", address, {
          success: false,
          type: payload.errorType || "network_error",
          request: payload.request || "custom",
          response: payload.response || "请求失败",
        });
        logs.value.push({
          address,
          type: payload.errorType || "network_error",
          request: payload.request || "custom",
          response: payload.response || "请求失败",
        });
      }
    }

    if (message.type === "complete") {
      geocodeState.running = false;
      geocodeState.current = "";
      flushAllPersistentCaches();
      closeCustomSocket();
      if (mapRealtimeUpdate.value) {
        refreshMarkers();
      }
    }
  };

  socket.onerror = () => {
    logs.value.push({
      address: "-",
      type: "network_error",
      request: customWebSocketUrl.value,
      response: "WebSocket 连接异常",
    });
  };

  socket.onclose = () => {
    if (geocodeState.running) {
      geocodeState.running = false;
      geocodeState.current = "";
      flushAllPersistentCaches();
      if (mapRealtimeUpdate.value) {
        refreshMarkers();
      }
    }
    flushAllPersistentCaches();
    closeCustomSocket();
  };
};

const startCustomRoute = () => {
  if (!canStart.value) return;
  closeCustomSocket();
  logs.value = [];
  points.value = [];
  routeLines.value = [];
  handledRouteIndices.clear();
  renderedPointKeys.clear();
  renderedRouteKeys.clear();
  geocodeState.running = true;
  geocodeState.processed = 0;
  geocodeState.current = "";

  const routes = buildRoutePayloads();
  geocodeState.total = routes.length;
  if (routes.length === 0) {
    geocodeState.running = false;
    return;
  }

  let socket;
  try {
    socket = new WebSocket(customWebSocketUrl.value);
  } catch (error) {
    logs.value.push({
      address: "-",
      type: "network_error",
      request: customWebSocketUrl.value,
      response: `无法连接 WebSocket: ${String(error)}`,
    });
    geocodeState.running = false;
    return;
  }

  customSocket.value = socket;

  socket.onopen = () => {
    socket.send(
      JSON.stringify({
        type: "start",
        payload: {
          mode: "route",
          routeInputMode: routeInputMode.value,
          config: {
            appId: customAppId.value,
            credential: customCredential.value,
            tokenUrl: customTokenUrl.value,
            geocodeUrl: customGeocodeUrl.value,
            routeUrl: customRouteUrl.value,
          },
          routes: routes.map((route) => ({
            origin: route.origin,
            destination: route.destination,
          })),
        },
      })
    );
  };

  socket.onmessage = (event) => {
    let message;
    try {
      message = JSON.parse(event.data);
    } catch (error) {
      logs.value.push({
        address: "-",
        type: "parse_error",
        request: "WebSocket",
        response: `无法解析后端返回: ${String(error)}`,
      });
      return;
    }

    if (message.type === "progress") {
      const messagePayload = message.payload || {};
      const payloads = Array.isArray(messagePayload.results)
        ? messagePayload.results
        : [messagePayload];

      if (Number.isFinite(messagePayload.processed)) {
        geocodeState.processed = messagePayload.processed;
      }

      payloads.forEach((payload) => {
      const routeIndex = Number(payload.index);
      const route = Number.isFinite(routeIndex) ? routes[routeIndex] : null;
      const routeKey = route ? `${route.origin}=>${route.destination}` : "";
      const address = route ? `${route.origin} -> ${route.destination}` : "-";
      geocodeState.current = address;

      if (Number.isFinite(payload.processed)) {
        geocodeState.processed = payload.processed;
      } else {
        geocodeState.processed += 1;
      }

      if (payload.success && route) {
        if (handledRouteIndices.has(routeIndex)) {
          return;
        }
        handledRouteIndices.add(routeIndex);

        const distanceKm = payload.distanceKm;
        const durationMin = payload.durationMin;

        if (distanceKm != null && durationMin != null) {
          rows.value[route.index]["导航距离(km)"] = distanceKm;
          rows.value[route.index]["导航时间(min)"] = durationMin;

          let originLat = normalizeCoordinate(payload.originLat);
          let originLng = normalizeCoordinate(payload.originLng);
          let destinationLat = normalizeCoordinate(payload.destinationLat);
          let destinationLng = normalizeCoordinate(payload.destinationLng);

          if (
            routeInputMode.value === "coordinate" &&
            (!Number.isFinite(originLat) || !Number.isFinite(originLng))
          ) {
            const parsedOrigin = parseRouteCoordinate(route.origin);
            if (parsedOrigin.success) {
              originLat = parsedOrigin.lat;
              originLng = parsedOrigin.lng;
            }
          }

          if (
            routeInputMode.value === "coordinate" &&
            (!Number.isFinite(destinationLat) || !Number.isFinite(destinationLng))
          ) {
            const parsedDestination = parseRouteCoordinate(route.destination);
            if (parsedDestination.success) {
              destinationLat = parsedDestination.lat;
              destinationLng = parsedDestination.lng;
            }
          }

          const pairKey = routePairKey(originLat, originLng, destinationLat, destinationLng);

          if (pairKey) {
            const routeResult = {
              success: true,
              failed: false,
              distanceKm,
              durationMin,
              line: {
                type: "LineString",
                coordinates: [
                  [originLng, originLat],
                  [destinationLng, destinationLat],
                ],
              },
              origin: { lat: originLat, lng: originLng },
              destination: { lat: destinationLat, lng: destinationLng },
              key: pairKey,
            };
            setPersistentCacheValue("route", pairKey, routeResult);
            if (routeKey) {
              routeCache.set(routeKey, routeResult);
            }

            pushPointIfNeeded({
              lat: originLat,
              lng: originLng,
              type: "origin",
              label: "起点",
              address: route.origin,
              displayMode: routeInputMode.value === "coordinate" ? "coordinate-only" : "full",
            });

            pushPointIfNeeded({
              lat: destinationLat,
              lng: destinationLng,
              type: "destination",
              failed: false,
              label: "终点",
              address: route.destination,
              displayMode: routeInputMode.value === "coordinate" ? "coordinate-only" : "full",
            });

            pushRouteLineIfNeeded({
              distanceKm,
              durationMin,
              failed: false,
              geometry: {
                type: "LineString",
                coordinates: [
                  [originLng, originLat],
                  [destinationLng, destinationLat],
                ],
              },
            });

            if (mapRealtimeUpdate.value) {
              scheduleRealtimeRefresh({ fitBounds: false });
            }
          } else {
            logs.value.push({
              address,
              type: "no_result",
              request: payload.request || "custom",
              response: "未返回可用导航坐标",
            });
          }
        } else {
          logs.value.push({
            address,
            type: "no_result",
            request: payload.request || "custom",
            response: "未返回可用导航数据",
          });
        }
      } else {
        const payloadOriginLat = normalizeCoordinate(payload.originLat);
        const payloadOriginLng = normalizeCoordinate(payload.originLng);
        const payloadDestinationLat = normalizeCoordinate(payload.destinationLat);
        const payloadDestinationLng = normalizeCoordinate(payload.destinationLng);
        const parsedOrigin = parseRouteCoordinate(route?.origin || "");
        const parsedDestination = parseRouteCoordinate(route?.destination || "");
        const originCoords =
          Number.isFinite(payloadOriginLat) && Number.isFinite(payloadOriginLng)
            ? { lat: payloadOriginLat, lng: payloadOriginLng }
            : parsedOrigin.success
              ? { lat: parsedOrigin.lat, lng: parsedOrigin.lng }
              : null;
        const destinationCoords =
          Number.isFinite(payloadDestinationLat) && Number.isFinite(payloadDestinationLng)
            ? { lat: payloadDestinationLat, lng: payloadDestinationLng }
            : parsedDestination.success
              ? { lat: parsedDestination.lat, lng: parsedDestination.lng }
              : null;

        let failedRouteResult = {
          success: false,
          type: payload.errorType || "network_error",
          request: payload.request || "custom",
          response: payload.response || "请求失败",
        };

        if (originCoords && destinationCoords) {
          pushPointIfNeeded({
            lat: originCoords.lat,
            lng: originCoords.lng,
            type: "origin",
            label: "起点",
            address: route?.origin,
            displayMode: routeInputMode.value === "coordinate" ? "coordinate-only" : "full",
          });

          pushPointIfNeeded({
            lat: destinationCoords.lat,
            lng: destinationCoords.lng,
            type: "destination",
            failed: true,
            label: "终点",
            address: route?.destination,
            displayMode: routeInputMode.value === "coordinate" ? "coordinate-only" : "full",
          });

          pushRouteLineIfNeeded({
            distanceKm: "",
            durationMin: "",
            failed: true,
            geometry: {
              type: "LineString",
              coordinates: [
                [originCoords.lng, originCoords.lat],
                [destinationCoords.lng, destinationCoords.lat],
              ],
            },
          });

          failedRouteResult = {
            ...failedRouteResult,
            failed: true,
            distanceKm: "",
            durationMin: "",
            origin: { lat: originCoords.lat, lng: originCoords.lng },
            destination: { lat: destinationCoords.lat, lng: destinationCoords.lng },
            line: {
              type: "LineString",
              coordinates: [
                [originCoords.lng, originCoords.lat],
                [destinationCoords.lng, destinationCoords.lat],
              ],
            },
          };

          if (mapRealtimeUpdate.value) {
            scheduleRealtimeRefresh({ fitBounds: false });
          }
        }
        if (routeKey) {
          routeCache.set(routeKey, failedRouteResult);
        }
        logs.value.push({
          address,
          type: payload.errorType || "network_error",
          request: payload.request || "custom",
          response: payload.response || "请求失败",
        });
      }
      });
    }

    if (message.type === "complete") {
      geocodeState.running = false;
      geocodeState.current = "";
      flushAllPersistentCaches();
      closeCustomSocket();
      if (mapRealtimeUpdate.value) {
        refreshMarkers();
      }
    }
  };

  socket.onerror = () => {
    logs.value.push({
      address: "-",
      type: "network_error",
      request: customWebSocketUrl.value,
      response: "WebSocket 连接异常",
    });
  };

  socket.onclose = () => {
    if (geocodeState.running) {
      geocodeState.running = false;
      geocodeState.current = "";
      flushAllPersistentCaches();
      if (mapRealtimeUpdate.value) {
        refreshMarkers();
      }
    }
    flushAllPersistentCaches();
    closeCustomSocket();
  };
};

const startGeocode = async () => {
  if (!canStart.value) return;
  logs.value = [];
  points.value = [];
  routeLines.value = [];
  renderedPointKeys.clear();
  renderedRouteKeys.clear();
  geocodeState.running = true;
  geocodeState.processed = 0;
  geocodeState.current = "";

  const addressMap = buildAddressMap();
  geocodeState.total = addressMap.size;

  for (const [address, indices] of addressMap.entries()) {
    geocodeState.current = address;
    let result = geocodeCache.get(address);
    if (!result) {
      result = await geocodeAddress(address);
      geocodeCache.set(address, result);
      setPersistentCacheValue("geocode", address, result);
    }
    geocodeState.processed += 1;

    if (result.success) {
      const lat = normalizeCoordinate(result.lat);
      const lng = normalizeCoordinate(result.lng);
      indices.forEach((rowIndex) => {
        rows.value[rowIndex].纬度 = lat;
        rows.value[rowIndex].经度 = lng;
      });
      pushPointIfNeeded({ lat, lng, address });
    } else {
      logs.value.push({
        address,
        type: result.type,
        request: result.request,
        response: result.response,
      });
    }
  }

  geocodeState.running = false;
  geocodeState.current = "";
  flushAllPersistentCaches();
  refreshMarkers();
};

const startReverseGeocode = async () => {
  if (!canStart.value) return;
  logs.value = [];
  points.value = [];
  routeLines.value = [];
  renderedPointKeys.clear();
  renderedRouteKeys.clear();
  geocodeState.running = true;
  geocodeState.processed = 0;
  geocodeState.current = "";
  geocodeState.total = rows.value.length;

  for (const row of rows.value) {
    const parsed = parseReverseCoordinates(row);
    geocodeState.current = parsed.key;
    if (!parsed.success) {
      logs.value.push({
        address: parsed.key,
        type: "invalid",
        request: "输入格式错误",
        response: parsed.message,
      });
      geocodeState.processed += 1;
      continue;
    }
    const { lat, lng } = parsed;
    let result = reverseCache.get(parsed.key);
    if (!result) {
      result = await reverseGeocode(lat, lng);
      reverseCache.set(parsed.key, result);
      setPersistentCacheValue("reverse", parsed.key, result);
    }
    geocodeState.processed += 1;
    if (result.success) {
      row.解析地址 = result.address;
      row.一级行政区 = result.admin1;
      row.二级行政区 = result.admin2;
      row.三级行政区 = result.admin3;
      pushPointIfNeeded({
        lat: normalizeCoordinate(lat),
        lng: normalizeCoordinate(lng),
        type: "point",
        address: result.address,
        admin1: result.admin1,
        admin2: result.admin2,
        admin3: result.admin3,
      });
    } else {
      logs.value.push({
        address: parsed.key,
        type: result.type,
        request: result.request,
        response: result.response,
      });
    }
  }

  geocodeState.running = false;
  geocodeState.current = "";
  flushAllPersistentCaches();
  refreshMarkers();
};

const parseReverseCoordinates = (row) => {
  if (reverseColumnMode.value === "single") {
    const raw = String(row[reverseColumnName.value] ?? "").trim();
    if (!raw) {
      return { success: false, key: "-", message: "经纬度为空" };
    }
    let delimiter = reverseDelimiter.value;
    if (reverseDelimiterMode.value === "auto") {
      delimiter = raw.includes(",") ? "," : raw.includes("，") ? "，" : "";
    }
    if (!delimiter) {
      return { success: false, key: raw, message: "无法识别分隔符" };
    }
    const parts = raw.split(delimiter).map((item) => item.trim());
    if (parts.length < 2) {
      return { success: false, key: raw, message: "经纬度格式不完整" };
    }
    const lat = normalizeCoordinate(parts[0]);
    const lng = normalizeCoordinate(parts[1]);
    if (!Number.isFinite(lat) || !Number.isFinite(lng)) {
      return { success: false, key: raw, message: "纬度或经度不是有效数字" };
    }
    return {
      success: true,
      key: coordPairKey(lat, lng),
      lat,
      lng,
    };
  }

  const lat = normalizeCoordinate(row[latColumnName.value]);
  const lng = normalizeCoordinate(row[lngColumnName.value]);
  const key =
    Number.isFinite(lat) && Number.isFinite(lng)
      ? coordPairKey(lat, lng)
      : `${row[latColumnName.value]},${row[lngColumnName.value]}`;

  if (!Number.isFinite(lat) || !Number.isFinite(lng)) {
    return { success: false, key, message: "纬度或经度不是有效数字" };
  }
  return { success: true, key, lat, lng };
};

const startRoute = async () => {
  if (!canStart.value) return;
  logs.value = [];
  points.value = [];
  routeLines.value = [];
  renderedPointKeys.clear();
  renderedRouteKeys.clear();
  geocodeState.running = true;
  geocodeState.processed = 0;
  geocodeState.current = "";
  geocodeState.total = rows.value.length;

  for (const row of rows.value) {
    const origin = String(row[startColumnName.value] ?? "").trim();
    const destination = String(row[endColumnName.value] ?? "").trim();
    const routeKey = `${origin}=>${destination}`;
    geocodeState.current = routeKey;
    if (!origin || !destination) {
      logs.value.push({
        address: routeKey,
        type: "invalid",
        request: "输入格式错误",
        response: "起始地或目的地为空",
      });
      geocodeState.processed += 1;
      continue;
    }

    if (routeInputMode.value === "coordinate") {
      const parsedOrigin = parseRouteCoordinate(origin);
      const parsedDestination = parseRouteCoordinate(destination);
      if (!parsedOrigin.success || !parsedDestination.success) {
        logs.value.push({
          address: routeKey,
          type: "invalid",
          request: "输入格式错误",
          response: `${parsedOrigin.message || ""} ${parsedDestination.message || ""}`.trim(),
        });
        geocodeState.processed += 1;
        continue;
      }
      let result = routeCache.get(routeKey);
      const pairKey = routePairKey(
        parsedOrigin.lat,
        parsedOrigin.lng,
        parsedDestination.lat,
        parsedDestination.lng
      );
      if (!result) {
        result = await fetchRoute(
          parsedOrigin.lat,
          parsedOrigin.lng,
          parsedDestination.lat,
          parsedDestination.lng
        );
        routeCache.set(routeKey, result);
        if (result.success) {
          setPersistentCacheValue("route", pairKey, result);
        }
      }
      geocodeState.processed += 1;
      if (result.success) {
        row["导航距离(km)"] = result.distanceKm;
        row["导航时间(min)"] = result.durationMin;

        pushPointIfNeeded({
          lat: normalizeCoordinate(parsedOrigin.lat),
          lng: normalizeCoordinate(parsedOrigin.lng),
          type: "origin",
          label: "起点",
          displayMode: "coordinate-only",
        });

        pushPointIfNeeded({
          lat: normalizeCoordinate(parsedDestination.lat),
          lng: normalizeCoordinate(parsedDestination.lng),
          type: "destination",
          failed: false,
          label: "终点",
          displayMode: "coordinate-only",
        });

        pushRouteLineIfNeeded({
          distanceKm: result.distanceKm,
          durationMin: result.durationMin,
          failed: false,
          geometry: result.line,
        });
      } else {
        pushPointIfNeeded({
          lat: normalizeCoordinate(parsedOrigin.lat),
          lng: normalizeCoordinate(parsedOrigin.lng),
          type: "origin",
          label: "起点",
          displayMode: "coordinate-only",
        });

        pushPointIfNeeded({
          lat: normalizeCoordinate(parsedDestination.lat),
          lng: normalizeCoordinate(parsedDestination.lng),
          type: "destination",
          failed: true,
          label: "终点",
          displayMode: "coordinate-only",
        });

        pushRouteLineIfNeeded({
          distanceKm: "",
          durationMin: "",
          failed: true,
          geometry: {
            type: "LineString",
            coordinates: [
              [normalizeCoordinate(parsedOrigin.lng), normalizeCoordinate(parsedOrigin.lat)],
              [
                normalizeCoordinate(parsedDestination.lng),
                normalizeCoordinate(parsedDestination.lat),
              ],
            ],
          },
        });

        logs.value.push({
          address: routeKey,
          type: result.type,
          request: result.request,
          response: result.response,
        });
      }
      continue;
    }

    let result = routeCache.get(routeKey);
    if (!result) {
      const originResult = geocodeCache.get(origin) || (await geocodeAddress(origin));
      geocodeCache.set(origin, originResult);
      setPersistentCacheValue("geocode", origin, originResult);
      const destinationResult =
        geocodeCache.get(destination) || (await geocodeAddress(destination));
      geocodeCache.set(destination, destinationResult);
      setPersistentCacheValue("geocode", destination, destinationResult);
      const pairKey =
        originResult.success && destinationResult.success
          ? routePairKey(
              originResult.lat,
              originResult.lng,
              destinationResult.lat,
              destinationResult.lng
            )
          : "";
      if (!originResult.success || !destinationResult.success) {
        const failure = !originResult.success ? originResult : destinationResult;
        result = {
          success: false,
          type: failure.type,
          request: failure.request,
          response: failure.response,
        };
      } else {
        result = await fetchRoute(
          originResult.lat,
          originResult.lng,
          destinationResult.lat,
          destinationResult.lng
        );
      }
      routeCache.set(routeKey, result);
      if (result.success) {
        setPersistentCacheValue("route", pairKey, result);
      }
    }
    geocodeState.processed += 1;

    if (result.success) {
      row["导航距离(km)"] = result.distanceKm;
      row["导航时间(min)"] = result.durationMin;

      pushPointIfNeeded({
        lat: normalizeCoordinate(result.origin.lat),
        lng: normalizeCoordinate(result.origin.lng),
        type: "origin",
        label: "起点",
        address: origin,
        displayMode: "full",
      });

      pushPointIfNeeded({
        lat: normalizeCoordinate(result.destination.lat),
        lng: normalizeCoordinate(result.destination.lng),
        type: "destination",
        failed: false,
        label: "终点",
        address: destination,
        displayMode: "full",
      });

      pushRouteLineIfNeeded({
        distanceKm: result.distanceKm,
        durationMin: result.durationMin,
        failed: false,
        geometry: result.line,
      });
    } else {
      if (routeInputMode.value === "address") {
        const originResult = geocodeCache.get(origin);
        const destinationResult = geocodeCache.get(destination);
        if (originResult?.success && destinationResult?.success) {
          pushPointIfNeeded({
            lat: normalizeCoordinate(originResult.lat),
            lng: normalizeCoordinate(originResult.lng),
            type: "origin",
            label: "起点",
            address: origin,
            displayMode: "full",
          });

          pushPointIfNeeded({
            lat: normalizeCoordinate(destinationResult.lat),
            lng: normalizeCoordinate(destinationResult.lng),
            type: "destination",
            failed: true,
            label: "终点",
            address: destination,
            displayMode: "full",
          });

          pushRouteLineIfNeeded({
            distanceKm: "",
            durationMin: "",
            failed: true,
            geometry: {
              type: "LineString",
              coordinates: [
                [normalizeCoordinate(originResult.lng), normalizeCoordinate(originResult.lat)],
                [
                  normalizeCoordinate(destinationResult.lng),
                  normalizeCoordinate(destinationResult.lat),
                ],
              ],
            },
          });
        }
      }

      logs.value.push({
        address: routeKey,
        type: result.type,
        request: result.request,
        response: result.response,
      });
    }
  }

  geocodeState.running = false;
  geocodeState.current = "";
  flushAllPersistentCaches();
  refreshMarkers();
};

const handleStart = () => {
  if (mode.value === "reverse") {
    startReverseGeocode();
  } else if (mode.value === "route") {
    if (provider.value === "custom") {
      startCustomRoute();
    } else {
      startRoute();
    }
  } else {
    if (provider.value === "custom") {
      startCustomGeocode();
    } else {
      startGeocode();
    }
  }
};

const geocodeAddress = async (address) => {
  const requestKey = String(address ?? "").trim();
  const persistentCached = getPersistentCacheValue("geocode", requestKey);
  if (persistentCached) {
    return persistentCached;
  }

  const encoded = encodeURIComponent(address);
  if (provider.value === "custom") {
    const token = await fetchCustomToken();
    if (!token) {
      return {
        success: false,
        type: "auth_error",
        request: customTokenUrl.value || "getResAppDynamicToken",
        response: "无法获取自定义接口 Token",
      };
    }
    const url = customGeocodeUrl.value || "geographicSearch";
    try {
      const response = await fetch(url, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: token,
        },
        body: JSON.stringify({
          address,
          language: "en",
          coordType: "wgs84",
        }),
      });
      const body = await response.json();
      if (!response.ok || body?.status !== "OK") {
        return {
          success: false,
          type: "network_error",
          request: url,
          response: JSON.stringify(body),
        };
      }
      const location = body?.result?.geometry?.location;
      if (!location || location.lat == null || location.lng == null) {
        return {
          success: false,
          type: "no_result",
          request: url,
          response: JSON.stringify(body),
        };
      }
      const lat = normalizeCoordinate(location.lat);
      const lng = normalizeCoordinate(location.lng);
      return cacheAndReturn("geocode", requestKey, {
        success: true,
        lat,
        lng,
        key: coordPairKey(lat, lng),
      });
    } catch (error) {
      return {
        success: false,
        type: "network_error",
        request: url,
        response: String(error),
      };
    }
  }
  if (provider.value === "mapbox") {
    const url = `https://api.mapbox.com/geocoding/v5/mapbox.places/${encoded}.json?access_token=${providerApiKey.value}`;
    try {
      const response = await fetch(url);
      const body = await response.json();
      if (!response.ok) {
        return {
          success: false,
          type: "network_error",
          request: url,
          response: JSON.stringify(body),
        };
      }
      if (!body.features || body.features.length === 0) {
        return {
          success: false,
          type: "no_result",
          request: url,
          response: JSON.stringify(body),
        };
      }
      const [lngRaw, latRaw] = body.features[0].center || [];
      const lat = normalizeCoordinate(latRaw);
      const lng = normalizeCoordinate(lngRaw);
      if (!Number.isFinite(lat) || !Number.isFinite(lng)) {
        return {
          success: false,
          type: "no_result",
          request: url,
          response: JSON.stringify(body),
        };
      }
      return cacheAndReturn("geocode", requestKey, {
        success: true,
        lat,
        lng,
        key: coordPairKey(lat, lng),
      });
    } catch (error) {
      return {
        success: false,
        type: "network_error",
        request: url,
        response: String(error),
      };
    }
  }

  const url = `https://geocode.search.hereapi.com/v1/geocode?q=${encoded}&apiKey=${providerApiKey.value}`;
  try {
    const response = await fetch(url);
    const body = await response.json();
    if (!response.ok) {
      return {
        success: false,
        type: "network_error",
        request: url,
        response: JSON.stringify(body),
      };
    }
    if (!body.items || body.items.length === 0) {
      return {
        success: false,
        type: "no_result",
        request: url,
        response: JSON.stringify(body),
      };
    }
    const { lat: latRaw, lng: lngRaw } = body.items[0].position || {};
    const lat = normalizeCoordinate(latRaw);
    const lng = normalizeCoordinate(lngRaw);
    if (!Number.isFinite(lat) || !Number.isFinite(lng)) {
      return {
        success: false,
        type: "no_result",
        request: url,
        response: JSON.stringify(body),
      };
    }
    return cacheAndReturn("geocode", requestKey, {
      success: true,
      lat,
      lng,
      key: coordPairKey(lat, lng),
    });
  } catch (error) {
    return {
      success: false,
      type: "network_error",
      request: url,
      response: String(error),
    };
  }
};

const fetchCustomToken = async () => {
  if (customToken.value) {
    return customToken.value;
  }
  const url = customTokenUrl.value || "getResAppDynamicToken";
  try {
    const response = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        appId: customAppId.value,
        credential: customCredential.value,
      }),
    });
    const body = await response.json();
    if (!response.ok || body?.status?.statusCode !== "SUCCESS" || !body?.result) {
      return "";
    }
    customToken.value = body.result;
    return customToken.value;
  } catch (error) {
    return "";
  }
};

const reverseGeocode = async (lat, lng) => {
  const normalizedLat = normalizeCoordinate(lat);
  const normalizedLng = normalizeCoordinate(lng);
  const requestKey = coordPairKey(normalizedLat, normalizedLng);
  const persistentCached = requestKey
    ? getPersistentCacheValue("reverse", requestKey)
    : null;
  if (persistentCached) {
    return persistentCached;
  }

  if (provider.value === "mapbox") {
    const url = `https://api.mapbox.com/geocoding/v5/mapbox.places/${normalizedLng},${normalizedLat}.json?access_token=${providerApiKey.value}`;
    try {
      const response = await fetch(url);
      const body = await response.json();
      if (!response.ok) {
        return {
          success: false,
          type: "network_error",
          request: url,
          response: JSON.stringify(body),
        };
      }
      if (!body.features || body.features.length === 0) {
        return {
          success: false,
          type: "no_result",
          request: url,
          response: JSON.stringify(body),
        };
      }
      const feature = body.features[0];
      const { admin1, admin2, admin3 } = extractMapboxAdmin(feature);
      return cacheAndReturn("reverse", requestKey, {
        success: true,
        address: feature.place_name,
        admin1,
        admin2,
        admin3,
      });
    } catch (error) {
      return {
        success: false,
        type: "network_error",
        request: url,
        response: String(error),
      };
    }
  }

  const url = `https://revgeocode.search.hereapi.com/v1/revgeocode?at=${normalizedLat},${normalizedLng}&lang=zh-CN&apiKey=${providerApiKey.value}`;
  try {
    const response = await fetch(url);
    const body = await response.json();
    if (!response.ok) {
      return {
        success: false,
        type: "network_error",
        request: url,
        response: JSON.stringify(body),
      };
    }
    if (!body.items || body.items.length === 0) {
      return {
        success: false,
        type: "no_result",
        request: url,
        response: JSON.stringify(body),
      };
    }
    const address = body.items[0].address || {};
    return cacheAndReturn("reverse", requestKey, {
      success: true,
      address: body.items[0].title || "",
      admin1: address.state || address.province || "",
      admin2: address.city || address.county || "",
      admin3: address.district || address.subdistrict || address.county || "",
    });
  } catch (error) {
    return {
      success: false,
      type: "network_error",
      request: url,
      response: String(error),
    };
  }
};

const fetchRoute = async (originLat, originLng, destLat, destLng) => {
  const normalizedOriginLat = normalizeCoordinate(originLat);
  const normalizedOriginLng = normalizeCoordinate(originLng);
  const normalizedDestLat = normalizeCoordinate(destLat);
  const normalizedDestLng = normalizeCoordinate(destLng);
  const pairKey = routePairKey(
    normalizedOriginLat,
    normalizedOriginLng,
    normalizedDestLat,
    normalizedDestLng
  );
  const persistentCached = pairKey ? getPersistentCacheValue("route", pairKey) : null;
  if (persistentCached) {
    return persistentCached;
  }

  if (provider.value === "mapbox") {
    const url = `https://api.mapbox.com/directions/v5/mapbox/driving/${normalizedOriginLng},${normalizedOriginLat};${normalizedDestLng},${normalizedDestLat}?geometries=geojson&overview=full&access_token=${providerApiKey.value}`;
    try {
      const response = await fetch(url);
      const body = await response.json();
      if (!response.ok) {
        return {
          success: false,
          type: "network_error",
          request: url,
          response: JSON.stringify(body),
        };
      }
      if (!body.routes || body.routes.length === 0) {
        return {
          success: false,
          type: "no_result",
          request: url,
          response: JSON.stringify(body),
        };
      }
      const route = body.routes[0];
      const geometry = route.geometry
        ? {
            ...route.geometry,
            coordinates: (route.geometry.coordinates || []).map((coord) => [
              normalizeCoordinate(coord?.[0]),
              normalizeCoordinate(coord?.[1]),
            ]),
          }
        : null;

      return cacheAndReturn("route", pairKey, {
        success: true,
        distanceKm: (route.distance / 1000).toFixed(2),
        durationMin: Math.round(route.duration / 60),
        line: geometry,
        origin: { lat: normalizedOriginLat, lng: normalizedOriginLng },
        destination: { lat: normalizedDestLat, lng: normalizedDestLng },
        key: pairKey,
      });
    } catch (error) {
      return {
        success: false,
        type: "network_error",
        request: url,
        response: String(error),
      };
    }
  }

  const url = `https://router.hereapi.com/v8/routes?transportMode=car&origin=${normalizedOriginLat},${normalizedOriginLng}&destination=${normalizedDestLat},${normalizedDestLng}&return=summary,polyline&apiKey=${providerApiKey.value}`;
  try {
    const response = await fetch(url);
    const body = await response.json();
    if (!response.ok) {
      return {
        success: false,
        type: "network_error",
        request: url,
        response: JSON.stringify(body),
      };
    }
    if (!body.routes || body.routes.length === 0) {
      return {
        success: false,
        type: "no_result",
        request: url,
        response: JSON.stringify(body),
      };
    }
    const route = body.routes[0];
    const summary = route.sections?.[0]?.summary;
    const polyline = route.sections?.[0]?.polyline;
    const geometry = polyline ? decodeHerePolyline(polyline) : null;
    return cacheAndReturn("route", pairKey, {
      success: true,
      distanceKm: summary ? (summary.length / 1000).toFixed(2) : "",
      durationMin: summary ? Math.round(summary.duration / 60) : "",
      line: geometry,
      origin: { lat: normalizedOriginLat, lng: normalizedOriginLng },
      destination: { lat: normalizedDestLat, lng: normalizedDestLng },
      key: pairKey,
    });
  } catch (error) {
    return {
      success: false,
      type: "network_error",
      request: url,
      response: String(error),
    };
  }
};

const extractMapboxAdmin = (feature) => {
  const context = feature.context || [];
  const place = context.find((item) => item.id?.startsWith("place"))?.text || "";
  const district = context.find((item) => item.id?.startsWith("district"))?.text || "";
  const region = context.find((item) => item.id?.startsWith("region"))?.text || "";
  const locality = context.find((item) => item.id?.startsWith("locality"))?.text || "";
  return {
    admin1: region || place || "",
    admin2: place || locality || "",
    admin3: district || locality || "",
  };
};

const decodeHerePolyline = (polyline) => {
  const decoder = new HerePolylineDecoder(polyline);
  const coordinates = [];
  while (decoder.hasNext()) {
    const { lat, lng } = decoder.next();
    coordinates.push([normalizeCoordinate(lng), normalizeCoordinate(lat)]);
  }
  return {
    type: "LineString",
    coordinates,
  };
};

class HerePolylineDecoder {
  constructor(encoded) {
    this.encoded = encoded;
    this.index = 0;
    this.lat = 0;
    this.lng = 0;
    this.z = 0;
    this.precision = 5;
    this.thirdDim = 0;
    this.thirdDimPrecision = 0;
    this.headerDecoded = false;
  }

  hasNext() {
    if (!this.headerDecoded) {
      this.decodeHeader();
    }
    return this.index < this.encoded.length;
  }

  next() {
    if (!this.headerDecoded) {
      this.decodeHeader();
    }
    this.lat += this.decodeSigned();
    this.lng += this.decodeSigned();
    if (this.thirdDim) {
      this.z += this.decodeSigned();
    }
    return {
      lat: this.lat / Math.pow(10, this.precision),
      lng: this.lng / Math.pow(10, this.precision),
    };
  }

  decodeHeader() {
    const header = this.decodeUnsigned();
    this.precision = header & 15;
    this.thirdDim = (header >> 4) & 7;
    this.thirdDimPrecision = (header >> 7) & 15;
    this.headerDecoded = true;
  }

  decodeUnsigned() {
    let result = 0;
    let shift = 0;
    while (this.index < this.encoded.length) {
      const value = this.encoded.charCodeAt(this.index++) - 63;
      result |= (value & 31) << shift;
      if (value < 32) {
        return result;
      }
      shift += 5;
    }
    return result;
  }

  decodeSigned() {
    const result = this.decodeUnsigned();
    return result & 1 ? ~(result >> 1) : result >> 1;
  }
}

const downloadExcel = () => {
  const outputHeaders = getOutputHeaders();
  const data = [outputHeaders];
  rows.value.forEach((row) => {
    const rowData = headers.value.map((header) => row[header] ?? "");
    if (mode.value === "geocode") {
      rowData.push(row.纬度 ?? "", row.经度 ?? "");
    } else if (mode.value === "reverse") {
      rowData.push(
        row.解析地址 ?? "",
        row.一级行政区 ?? "",
        row.二级行政区 ?? "",
        row.三级行政区 ?? ""
      );
    } else {
      rowData.push(row["导航距离(km)"] ?? "", row["导航时间(min)"] ?? "");
    }
    data.push(rowData);
  });
  const worksheet = XLSX.utils.aoa_to_sheet(data);
  const workbook = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(workbook, worksheet, "Geocode");
  XLSX.writeFile(workbook, `geocode_${fileName.value || "result.xlsx"}`);
};

const getOutputHeaders = () => {
  if (mode.value === "reverse") {
    return [...headers.value, "解析地址", "一级行政区", "二级行政区", "三级行政区"];
  }
  if (mode.value === "route") {
    return [...headers.value, "导航距离(km)", "导航时间(min)"];
  }
  return [...headers.value, "纬度", "经度"];
};

const initMap = () => {
  if (!mapContainer.value || !mapApiKey.value) return;
  mapboxgl.accessToken = mapApiKey.value;
  mapLoaded.value = false;
  if (mapInstance) {
    mapInstance.remove();
    mapInstance = null;
  }
  routeHoverHandlers = null;
  routePopup = null;
  mapInstance = new mapboxgl.Map({
    container: mapContainer.value,
    style: "mapbox://styles/mapbox/streets-v12",
    projection: "mercator",
    center: [116.397389, 39.908722],
    zoom: 3,
  });
  mapInstance.addControl(new mapboxgl.NavigationControl(), "top-right");
  mapInstance.on("load", () => {
    mapInstance.setProjection("mercator");
    mapLoaded.value = true;
    refreshMarkers();
  });
};

const destroyMap = () => {
  if (realtimeRefreshTimer) {
    clearTimeout(realtimeRefreshTimer);
    realtimeRefreshTimer = null;
  }
  realtimeRefreshPendingFitBounds = false;
  if (mapInstance) {
    mapInstance.remove();
    mapInstance = null;
  }
  mapLoaded.value = false;
  mapMarkers = [];
  routeHoverHandlers = null;
  if (routePopup) {
    routePopup.remove();
    routePopup = null;
  }
};

const scheduleRealtimeRefresh = ({ fitBounds = false } = {}) => {
  if (!mapInstance) return;
  realtimeRefreshPendingFitBounds = realtimeRefreshPendingFitBounds || fitBounds;
  if (realtimeRefreshTimer) {
    return;
  }
  realtimeRefreshTimer = setTimeout(() => {
    realtimeRefreshTimer = null;
    const shouldFitBounds = realtimeRefreshPendingFitBounds;
    realtimeRefreshPendingFitBounds = false;
    refreshMarkers({ fitBounds: shouldFitBounds });
  }, REALTIME_REFRESH_INTERVAL_MS);
};

const refreshMarkers = ({ fitBounds = true } = {}) => {
  if (!mapInstance) return;
  mapMarkers.forEach((marker) => marker.remove());
  mapMarkers = [];
  updateRouteLayer();
  if (!points.value.length) return;
  const bounds = new mapboxgl.LngLatBounds();
  points.value.forEach((point) => {
    const markerElement = buildPointMarkerElement(point);
    const marker = markerElement
      ? new mapboxgl.Marker({ element: markerElement })
      : new mapboxgl.Marker({
          color:
            point.type === "origin"
              ? "#16a34a"
              : point.type === "destination"
                ? point.failed
                  ? "#dc2626"
                  : "#7c3aed"
                : "#2563eb",
        });
    marker.setLngLat([point.lng, point.lat]).addTo(mapInstance);
    const popup = new mapboxgl.Popup({ closeButton: true, closeOnClick: false, offset: 12 })
      .setLngLat([point.lng, point.lat])
      .setHTML(buildPointPopupContent(point));
    const markerDomElement = marker.getElement();
    markerDomElement.addEventListener("mouseenter", () => {
      popup.addTo(mapInstance);
    });
    markerDomElement.addEventListener("mouseleave", () => {
      popup.remove();
    });
    mapMarkers.push(marker);
    bounds.extend([point.lng, point.lat]);
  });
  routeLines.value.forEach((line) => {
    if (line.geometry?.coordinates?.length) {
      line.geometry.coordinates.forEach((coord) => bounds.extend(coord));
    }
  });
  if (fitBounds && !bounds.isEmpty()) {
    mapInstance.fitBounds(bounds, { padding: 80, maxZoom: 13 });
  }
};

const buildRouteFeatureCollection = () => ({
  type: "FeatureCollection",
  features: routeLines.value.map((line) => ({
    type: "Feature",
    properties: {
      distanceKm: line.distanceKm ?? "",
      durationMin: line.durationMin ?? "",
      failed: Boolean(line.failed),
    },
    geometry: line.geometry,
  })),
});

const updateRouteLayer = () => {
  if (!mapInstance) return;
  const source = mapInstance.getSource(routeSourceId);
  const data = buildRouteFeatureCollection();

  if (!source) {
    mapInstance.addSource(routeSourceId, {
      type: "geojson",
      data,
    });
  } else {
    source.setData(data);
  }

  if (!mapInstance.getLayer(routeLayerId)) {
    mapInstance.addLayer({
      id: routeLayerId,
      type: "line",
      source: routeSourceId,
      layout: {
        "line-join": "round",
        "line-cap": "round",
      },
      paint: {
        "line-color": ["case", ["==", ["get", "failed"], true], "#dc2626", "#0ea5e9"],
        "line-width": 1,
        "line-dasharray": [2, 2],
      },
    });
    attachRouteHover(routeLayerId);
  }
};

const attachRouteHover = (layerId) => {
  if (!mapInstance || routeHoverHandlers) return;
  routePopup = new mapboxgl.Popup({ closeButton: true, closeOnClick: false, offset: 12 });
  const buildRouteContent = (feature) => {
    const distanceKm = feature?.properties?.distanceKm;
    const durationMin = feature?.properties?.durationMin;
    if (!distanceKm && !durationMin) {
      return '<div class="map-popup"><p>暂无可用路线信息</p></div>';
    }
    return `
      <div class="map-popup">
        <p><strong>导航距离：</strong>${distanceKm} km</p>
        <p><strong>导航时间：</strong>${durationMin} min</p>
      </div>
    `;
  };
  const enter = (event) => {
    mapInstance.getCanvas().style.cursor = "pointer";
    routePopup
      .setLngLat(event.lngLat)
      .setHTML(buildRouteContent(event.features?.[0]))
      .addTo(mapInstance);
  };
  const move = (event) => {
    routePopup.setLngLat(event.lngLat);
  };
  const leave = () => {
    mapInstance.getCanvas().style.cursor = "";
    routePopup.remove();
  };
  routeHoverHandlers = { enter, leave, move };
  mapInstance.on("mouseenter", layerId, enter);
  mapInstance.on("mousemove", layerId, move);
  mapInstance.on("mouseleave", layerId, leave);
};

const buildPointMarkerElement = (point) => {
  if (mode.value === "route" && (point.type === "origin" || point.type === "destination")) {
    const el = document.createElement("div");
    if (point.type === "origin") {
      el.className = "route-origin-circle-marker";
    } else if (point.failed) {
      el.className = "route-destination-circle-marker-failed";
    } else {
      el.className = "route-destination-circle-marker";
    }
    return el;
  }
  return null;
};

const formatCoordinate = (value) => {
  if (!Number.isFinite(value)) return "-";
  return Number(value).toFixed(6);
};

const buildPointPopupContent = (point) => {
  if (point.displayMode === "coordinate-only") {
    return `
      <div class="map-popup">
        <p><strong>经纬度：</strong>${formatCoordinate(point.lat)}, ${formatCoordinate(point.lng)}</p>
      </div>
    `;
  }
  const title = point.label || point.address || "位置点";
  const addressLine = point.address ? `<p><strong>地址：</strong>${point.address}</p>` : "";
  const adminParts = [point.admin1, point.admin2, point.admin3].filter(Boolean);
  const adminLine = adminParts.length
    ? `<p><strong>行政区：</strong>${adminParts.join(" / ")}</p>`
    : "";
  return `
    <div class="map-popup">
      <p><strong>${title}</strong></p>
      ${addressLine}
      ${adminLine}
      <p><strong>经纬度：</strong>${formatCoordinate(point.lat)}, ${formatCoordinate(point.lng)}</p>
    </div>
  `;
};

const exportSettings = () => {
  const payload = {
    version: 1,
    data: {
      mapboxGeocodeApiKey: mapboxGeocodeApiKey.value,
      hereGeocodeApiKey: hereGeocodeApiKey.value,
      customAppId: customAppId.value,
      customCredential: customCredential.value,
      customTokenUrl: customTokenUrl.value,
      customGeocodeUrl: customGeocodeUrl.value,
      customRouteUrl: customRouteUrl.value,
      customWebSocketUrl: customWebSocketUrl.value,
      mapApiKey: mapApiKey.value,
    },
  };
  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = "network-tools-config.json";
  document.body.appendChild(anchor);
  anchor.click();
  document.body.removeChild(anchor);
  URL.revokeObjectURL(url);
};

const triggerConfigImport = () => {
  settingsNotice.value = "";
  configFileInput.value?.click();
};

const applyConfigValue = (value, setter) => {
  if (typeof value === "string") {
    setter(value);
  }
};

const handleConfigFileChange = async (event) => {
  const file = event.target.files?.[0];
  if (!file) return;
  settingsNotice.value = "";
  try {
    const content = await file.text();
    const parsed = JSON.parse(content);
    const config = parsed?.data && typeof parsed.data === "object" ? parsed.data : parsed;
    if (!config || typeof config !== "object") {
      throw new Error("配置格式不正确");
    }
    applyConfigValue(config.mapboxGeocodeApiKey, (value) => {
      mapboxGeocodeApiKey.value = value;
    });
    applyConfigValue(config.hereGeocodeApiKey, (value) => {
      hereGeocodeApiKey.value = value;
    });
    applyConfigValue(config.customAppId, (value) => {
      customAppId.value = value;
    });
    applyConfigValue(config.customCredential, (value) => {
      customCredential.value = value;
    });
    applyConfigValue(config.customTokenUrl, (value) => {
      customTokenUrl.value = value;
    });
    applyConfigValue(config.customGeocodeUrl, (value) => {
      customGeocodeUrl.value = value;
    });
    applyConfigValue(config.customRouteUrl, (value) => {
      customRouteUrl.value = value;
    });
    applyConfigValue(config.customWebSocketUrl, (value) => {
      customWebSocketUrl.value = value;
    });
    applyConfigValue(config.mapApiKey, (value) => {
      mapApiKey.value = value;
      localStorage.setItem(storageKeys.mapboxMap, value);
      initMap();
    });
    settingsNotice.value = `配置已导入：${file.name}`;
  } catch (error) {
    settingsNotice.value = `导入失败：${error.message || "配置解析异常"}`;
  } finally {
    event.target.value = "";
  }
};

onMounted(() => {
  mode.value = "visualize";
  const savedProvider = localStorage.getItem(storageKeys.provider);
  if (savedProvider === "mapbox" || savedProvider === "here" || savedProvider === "custom") {
    provider.value = savedProvider;
  }
  if (provider.value === "custom") {
    const savedAppId = localStorage.getItem(storageKeys.customAppId);
    const savedCredential = localStorage.getItem(storageKeys.customCredential);
    const savedTokenUrl = localStorage.getItem(storageKeys.customTokenUrl);
    const savedGeocodeUrl = localStorage.getItem(storageKeys.customGeocodeUrl);
    const savedRouteUrl = localStorage.getItem(storageKeys.customRouteUrl);
    const savedWebSocketUrl = localStorage.getItem(storageKeys.customWebSocketUrl);
    if (savedAppId) {
      customAppId.value = savedAppId;
    }
    if (savedCredential) {
      customCredential.value = savedCredential;
    }
    if (savedTokenUrl) {
      customTokenUrl.value = savedTokenUrl;
    }
    if (savedGeocodeUrl) {
      customGeocodeUrl.value = savedGeocodeUrl;
    }
    if (savedRouteUrl) {
      customRouteUrl.value = savedRouteUrl;
    }
    if (savedWebSocketUrl) {
      customWebSocketUrl.value = savedWebSocketUrl;
    }
  } else {
    const savedProviderKey = localStorage.getItem(getProviderStorageKey(provider.value));
    if (savedProviderKey) {
      providerApiKey.value = savedProviderKey;
    }
  }
  const savedMapboxKey = localStorage.getItem(storageKeys.mapboxGeocode);
  if (savedMapboxKey) {
    mapboxGeocodeApiKey.value = savedMapboxKey;
  }
  const savedHereKey = localStorage.getItem(storageKeys.hereGeocode);
  if (savedHereKey) {
    hereGeocodeApiKey.value = savedHereKey;
  }
  if (provider.value !== "custom") {
    providerApiKey.value =
      provider.value === "mapbox" ? mapboxGeocodeApiKey.value : hereGeocodeApiKey.value;
  }
  const savedReverseMode = localStorage.getItem(storageKeys.reverseColumnMode);
  if (savedReverseMode === "single" || savedReverseMode === "separate") {
    reverseColumnMode.value = savedReverseMode;
  }
  const savedReverseColumn = localStorage.getItem(storageKeys.reverseColumnName);
  if (savedReverseColumn) {
    reverseColumnName.value = savedReverseColumn;
  }
  const savedDelimiterMode = localStorage.getItem(storageKeys.reverseDelimiterMode);
  if (savedDelimiterMode === "auto" || savedDelimiterMode === "custom") {
    reverseDelimiterMode.value = savedDelimiterMode;
  }
  const savedDelimiter = localStorage.getItem(storageKeys.reverseDelimiter);
  if (savedDelimiter) {
    reverseDelimiter.value = savedDelimiter;
  }
  const savedRouteInputMode = localStorage.getItem(storageKeys.routeInputMode);
  if (savedRouteInputMode === "address" || savedRouteInputMode === "coordinate") {
    routeInputMode.value = savedRouteInputMode;
  }
  const savedMapRealtimeUpdate = localStorage.getItem(storageKeys.mapRealtimeUpdate);
  if (savedMapRealtimeUpdate === "0") {
    mapRealtimeUpdate.value = false;
  }
  const savedKey = localStorage.getItem(storageKeys.mapboxMap);
  if (savedKey) {
    mapApiKey.value = savedKey;
  }
  if (mapApiKey.value) {
    initMap();
  }
});

watch(provider, (value) => {
  localStorage.setItem(storageKeys.provider, value);
  if (value === "custom") {
    providerApiKey.value = "";
  } else {
    providerApiKey.value =
      value === "mapbox" ? mapboxGeocodeApiKey.value || "" : hereGeocodeApiKey.value || "";
  }
});

watch(mapboxGeocodeApiKey, (value) => {
  if (value) {
    localStorage.setItem(storageKeys.mapboxGeocode, value);
  } else {
    localStorage.removeItem(storageKeys.mapboxGeocode);
  }
  if (provider.value === "mapbox") {
    providerApiKey.value = value || "";
  }
});

watch(hereGeocodeApiKey, (value) => {
  if (value) {
    localStorage.setItem(storageKeys.hereGeocode, value);
  } else {
    localStorage.removeItem(storageKeys.hereGeocode);
  }
  if (provider.value === "here") {
    providerApiKey.value = value || "";
  }
});

watch(customAppId, (value) => {
  customToken.value = "";
  if (value) {
    localStorage.setItem(storageKeys.customAppId, value);
  } else {
    localStorage.removeItem(storageKeys.customAppId);
  }
});

watch(customCredential, (value) => {
  customToken.value = "";
  if (value) {
    localStorage.setItem(storageKeys.customCredential, value);
  } else {
    localStorage.removeItem(storageKeys.customCredential);
  }
});

watch(customTokenUrl, (value) => {
  customToken.value = "";
  if (value) {
    localStorage.setItem(storageKeys.customTokenUrl, value);
  } else {
    localStorage.removeItem(storageKeys.customTokenUrl);
  }
});

watch(customGeocodeUrl, (value) => {
  if (value) {
    localStorage.setItem(storageKeys.customGeocodeUrl, value);
  } else {
    localStorage.removeItem(storageKeys.customGeocodeUrl);
  }
});

watch(customRouteUrl, (value) => {
  if (value) {
    localStorage.setItem(storageKeys.customRouteUrl, value);
  } else {
    localStorage.removeItem(storageKeys.customRouteUrl);
  }
});

watch(customWebSocketUrl, (value) => {
  if (value) {
    localStorage.setItem(storageKeys.customWebSocketUrl, value);
  } else {
    localStorage.removeItem(storageKeys.customWebSocketUrl);
  }
});

watch(columnName, (value) => {
  if (value) {
    localStorage.setItem(storageKeys.columnName, value);
  } else {
    localStorage.removeItem(storageKeys.columnName);
  }
});

watch(latColumnName, (value) => {
  if (value) {
    localStorage.setItem(storageKeys.latColumnName, value);
  } else {
    localStorage.removeItem(storageKeys.latColumnName);
  }
});

watch(lngColumnName, (value) => {
  if (value) {
    localStorage.setItem(storageKeys.lngColumnName, value);
  } else {
    localStorage.removeItem(storageKeys.lngColumnName);
  }
});

watch(reverseColumnMode, (value) => {
  if (value) {
    localStorage.setItem(storageKeys.reverseColumnMode, value);
  } else {
    localStorage.removeItem(storageKeys.reverseColumnMode);
  }
});

watch(reverseColumnName, (value) => {
  if (value) {
    localStorage.setItem(storageKeys.reverseColumnName, value);
  } else {
    localStorage.removeItem(storageKeys.reverseColumnName);
  }
});

watch(reverseDelimiterMode, (value) => {
  if (value) {
    localStorage.setItem(storageKeys.reverseDelimiterMode, value);
  } else {
    localStorage.removeItem(storageKeys.reverseDelimiterMode);
  }
});

watch(reverseDelimiter, (value) => {
  if (value) {
    localStorage.setItem(storageKeys.reverseDelimiter, value);
  } else {
    localStorage.removeItem(storageKeys.reverseDelimiter);
  }
});

watch(startColumnName, (value) => {
  if (value) {
    localStorage.setItem(storageKeys.startColumnName, value);
  } else {
    localStorage.removeItem(storageKeys.startColumnName);
  }
});

watch(endColumnName, (value) => {
  if (value) {
    localStorage.setItem(storageKeys.endColumnName, value);
  } else {
    localStorage.removeItem(storageKeys.endColumnName);
  }
});

watch(routeInputMode, (value) => {
  if (value) {
    localStorage.setItem(storageKeys.routeInputMode, value);
  } else {
    localStorage.removeItem(storageKeys.routeInputMode);
  }
});

watch(mapRealtimeUpdate, (value, oldValue) => {
  localStorage.setItem(storageKeys.mapRealtimeUpdate, value ? "1" : "0");
  if (value && oldValue === false) {
    refreshMarkers();
  }
});

watch(mode, (value) => {
  localStorage.setItem(storageKeys.mode, value);
  if (value === "reverse" && provider.value === "custom") {
    provider.value = "mapbox";
  }

  if (value === "visualize") {
    destroyMap();
  }

  resetFileData();
  resetResults();

  if (value !== "visualize" && mapApiKey.value) {
    nextTick(() => {
      initMap();
    });
  }
});

  return {
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
    providerApiKey,
    mapboxGeocodeApiKey,
    hereGeocodeApiKey,
    customAppId,
    customCredential,
    customTokenUrl,
    customGeocodeUrl,
    customRouteUrl,
    customToken,
    customWebSocketUrl,
    customSocket,
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
    points,
    routeLines,
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
    closeCustomSocket
  };
}
