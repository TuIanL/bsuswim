<script setup lang="ts">
import type { ReportChart as ReportChartType } from '../../../types/report'

defineProps<{
  chart: ReportChartType
}>()
</script>

<template>
  <div class="report-chart-card">
    <h3 class="chart-title">{{ chart.title }}</h3>

    <table class="chart-fallback-table">
      <thead>
        <tr>
          <th>序列</th>
          <th v-for="x in chart.x_axis" :key="x">{{ x }}</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="series in chart.series" :key="series.name">
          <td>{{ series.name }}</td>
          <td v-for="(value, index) in series.data" :key="index">
            {{ value }}{{ series.unit ?? chart.y_axis_unit ?? '' }}
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<style scoped>
.report-chart-card {
  border: 1px solid #e6edf3;
  border-radius: 14px;
  padding: 16px;
  background: #fff;
}

.chart-title {
  font-size: 15px;
  font-weight: 700;
  margin: 0 0 12px;
}

.chart-fallback-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.chart-fallback-table th,
.chart-fallback-table td {
  padding: 8px 10px;
  border: 1px solid #e6edf3;
  text-align: center;
}

.chart-fallback-table th {
  background: #f7f9fb;
  font-weight: 600;
  color: #5f6b7a;
}
</style>
