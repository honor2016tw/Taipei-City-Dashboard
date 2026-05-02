<!-- YouBike Peak Pressure Segment Chart
     Displays a DonutChart for the selected time segment.
     Data arrives as three_d series: each series.name is a segment key,
     series.data is [借車壓力站_count, 平衡站_count, 還車壓力站_count].
     Categories come from chart_config.categories (sorted alphabetically by backend). -->
<script setup>
import { computed, ref } from "vue";
import VueApexCharts from "vue3-apexcharts";

const props = defineProps([
	"chart_config",
	"activeChart",
	"series",
	"map_config",
	"map_filter",
	"map_filter_on",
]);

defineEmits([
	"filterByParam",
	"filterByLayer",
	"clearByParamFilter",
	"clearByLayerFilter",
	"fly",
]);

const SEGMENTS = [
	{ key: "weekday_am", label: "平日早高峰", sub: "07:00–09:00" },
	{ key: "weekday_pm", label: "平日晚高峰", sub: "17:00–19:00" },
	{ key: "weekend_am", label: "週末上午", sub: "07:00–09:00" },
	{ key: "weekend_pm", label: "週末傍晚", sub: "17:00–19:00" },
];
const DEFAULT_COLORS = ["#E25555", "#18B7A7", "#F2A93B"];

function firstAvailableSegment() {
	if (!props.series || props.series.length === 0) return "weekend_pm";
	const preferred = props.series.find((s) => s.name === "weekend_pm");
	if (preferred) return "weekend_pm";
	return props.series[0].name;
}

const selectedSegment = ref(firstAvailableSegment());

const currentSeries = computed(() =>
	(props.series || []).find((s) => s.name === selectedSegment.value),
);

const hasData = computed(
	() => currentSeries.value && currentSeries.value.data.some((v) => v > 0),
);

const donutSeries = computed(() => currentSeries.value?.data ?? []);

const donutOptions = computed(() => ({
	chart: {
		type: "donut",
		toolbar: { show: false },
		animations: { enabled: true, speed: 300 },
	},
	labels: props.chart_config?.categories ?? [],
	colors: props.chart_config?.color ?? DEFAULT_COLORS,
	legend: {
		show: true,
		position: "bottom",
		fontSize: "12px",
		labels: { colors: "#d8e2ef" },
	},
	dataLabels: {
		enabled: true,
		style: {
			fontSize: "12px",
			fontWeight: 700,
			colors: ["#ffffff"],
		},
		dropShadow: {
			enabled: true,
			top: 1,
			left: 0,
			blur: 2,
			opacity: 0.45,
		},
		formatter: (val) => `${Math.round(val)}%`,
	},
	tooltip: {
		y: {
			formatter: (v) =>
				`${v.toLocaleString()} ${props.chart_config?.unit ?? "站"}`,
		},
	},
	plotOptions: {
		pie: {
			donut: {
				size: "60%",
				labels: {
					show: true,
					name: {
						color: "#d8e2ef",
					},
					value: {
						color: "#f8fafc",
					},
					total: {
						show: true,
						label: "合計",
						color: "#d8e2ef",
						fontSize: "13px",
						formatter: (w) =>
							w.globals.seriesTotals
								.reduce((a, b) => a + b, 0)
								.toLocaleString() +
							` ${props.chart_config?.unit ?? "站"}`,
					},
				},
			},
		},
	},
	stroke: { width: 2, colors: ["#1a1d28"] },
}));
</script>

<template>
	<div class="youbike-peak-chart">
		<!-- Segment selector -->
		<div class="segment-tabs">
			<button
				v-for="seg in SEGMENTS"
				:key="seg.key"
				:class="[
					'segment-tab',
					{ active: selectedSegment === seg.key },
				]"
				@click="selectedSegment = seg.key"
			>
				<span class="seg-label">{{ seg.label }}</span>
				<span class="seg-sub">{{ seg.sub }}</span>
			</button>
		</div>

		<!-- Chart -->
		<VueApexCharts
			v-if="hasData"
			type="donut"
			height="240"
			:options="donutOptions"
			:series="donutSeries"
		/>

		<!-- No data -->
		<div v-else class="no-data">
			<span class="material-icons">hourglass_empty</span>
			<p>此時段尚無快照資料</p>
		</div>
	</div>
</template>

<style scoped>
.youbike-peak-chart {
	display: flex;
	flex-direction: column;
	height: 100%;
}

.segment-tabs {
	display: flex;
	gap: 4px;
	padding: 4px 0 8px;
	flex-shrink: 0;
}

.segment-tab {
	flex: 1;
	display: flex;
	flex-direction: column;
	align-items: center;
	padding: 5px 4px;
	border: 1px solid #3d4251;
	background: transparent;
	color: #8a94a6;
	border-radius: 4px;
	cursor: pointer;
	transition:
		background 0.15s,
		color 0.15s,
		border-color 0.15s;
	line-height: 1.2;
}

.segment-tab:hover {
	border-color: #5a6275;
	color: #cfd8e3;
}

.segment-tab.active {
	background: #18b7a722;
	border-color: #18b7a7;
	color: #5ee5d8;
}

.seg-label {
	font-size: 11px;
	font-weight: 600;
}

.seg-sub {
	font-size: 9px;
	opacity: 0.75;
}

.no-data {
	display: flex;
	flex-direction: column;
	align-items: center;
	justify-content: center;
	flex: 1;
	gap: 8px;
	color: #5a6275;
}

.no-data .material-icons {
	font-size: 36px;
}

.no-data p {
	font-size: 13px;
	margin: 0;
}
</style>
