<template>
  <div class="card">
    <div class="card-header log-card-header">
      <h2>4. 日志</h2>
      <div class="log-toolbar" v-if="logs.length">
        <label class="page-size-control">
          每页
          <select v-model.number="pageSize">
            <option v-for="size in pageSizeOptions" :key="size" :value="size">{{ size }}</option>
          </select>
          条
        </label>
        <button class="secondary-button" type="button" @click="exportToExcel">导出 Excel</button>
      </div>
    </div>

    <div class="log" v-if="logs.length">
      <div v-for="(item, index) in paginatedLogs" :key="`${item.address}-${index}`" class="log-item">
        <div class="log-title">
          <strong>{{ item.address }}</strong>
          <span class="tag">{{ item.type }}</span>
        </div>
        <div class="log-body">
          <p><span>请求</span> {{ item.request }}</p>
          <p><span>返回</span> {{ item.response }}</p>
        </div>
      </div>
    </div>

    <div class="log-pagination" v-if="logs.length">
      <span>第 {{ currentPage }} / {{ totalPages }} 页，共 {{ logs.length }} 条</span>
      <div class="pagination-actions">
        <button type="button" class="secondary-button" :disabled="currentPage === 1" @click="goToPreviousPage">上一页</button>
        <button type="button" class="secondary-button" :disabled="currentPage === totalPages" @click="goToNextPage">下一页</button>
      </div>
    </div>

    <p v-else class="hint">暂无错误日志。</p>
  </div>
</template>

<script setup>
import { computed, ref, watch } from "vue";
import * as XLSX from "xlsx";

const props = defineProps({ logs: { type: Array, required: true } });

const pageSizeOptions = [10, 20, 50, 100, 200];
const pageSize = ref(pageSizeOptions[0]);
const currentPage = ref(1);

const totalPages = computed(() => {
  if (!props.logs.length) {
    return 1;
  }
  return Math.ceil(props.logs.length / pageSize.value);
});

const paginatedLogs = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value;
  const end = start + pageSize.value;
  return props.logs.slice(start, end);
});

watch([() => props.logs.length, pageSize], () => {
  currentPage.value = 1;
});

const goToPreviousPage = () => {
  if (currentPage.value > 1) {
    currentPage.value -= 1;
  }
};

const goToNextPage = () => {
  if (currentPage.value < totalPages.value) {
    currentPage.value += 1;
  }
};

const exportToExcel = () => {
  const rows = props.logs.map((item, index) => ({
    序号: index + 1,
    地址: item.address,
    类型: item.type,
    请求: item.request,
    返回: item.response,
  }));

  const worksheet = XLSX.utils.json_to_sheet(rows);
  const workbook = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(workbook, worksheet, "日志");
  XLSX.writeFile(workbook, "logs.xlsx");
};
</script>
