<script setup>
import { computed, ref } from "vue";

const props = defineProps([
	"chart_config",
	"activeChart",
	"series",
	"map_config",
	"map_filter",
	"map_filter_on",
]);

const emits = defineEmits([
	"filterByParam",
	"filterByLayer",
	"clearByParamFilter",
	"clearByLayerFilter",
	"fly"
]);

const lineOrder = ["文湖線", "淡水信義線", "松山新店線", "中和新蘆線", "板南線"];
const lineColors = {
	"文湖線": "#c48c31",
	"淡水信義線": "#e3002c",
	"松山新店線": "#008659",
	"中和新蘆線": "#f8b61c",
	"板南線": "#0070bd",
};

const selectedLine = ref(lineOrder[0]);

const rows = computed(() => {
	const rawRows = props.series?.[0]?.data || [];
	return rawRows
		.map((row) => {
			const [lineName, stationName] = `${row.x}`.split("｜");
			return {
				lineName,
				stationName,
				value: Number(row.y) || 0,
			};
		})
		.filter((row) => row.lineName && row.stationName);
});

const lines = computed(() => {
	const existing = new Set(rows.value.map((row) => row.lineName));
	const ordered = lineOrder.filter((line) => existing.has(line));
	const rest = [...existing].filter((line) => !lineOrder.includes(line)).sort();
	return [...ordered, ...rest];
});

const activeLine = computed(() => {
	return lines.value.includes(selectedLine.value)
		? selectedLine.value
		: lines.value[0];
});

const selectedRows = computed(() => {
	return rows.value
		.filter((row) => row.lineName === activeLine.value)
		.sort((a, b) => b.value - a.value || a.stationName.localeCompare(b.stationName));
});

const lineAverage = computed(() => {
	if (selectedRows.value.length === 0) return 0;
	const sum = selectedRows.value.reduce((total, row) => total + row.value, 0);
	return Math.round((sum / selectedRows.value.length) * 10) / 10;
});

function colorForValue(value) {
	if (value >= 80) return props.chart_config.color?.[0] || "#39c5bb";
	if (value >= 65) return props.chart_config.color?.[1] || "#7ea1ff";
	if (value >= 50) return props.chart_config.color?.[2] || "#f4b942";
	return props.chart_config.color?.[3] || "#ef6f6c";
}

function selectLine(lineName) {
	selectedLine.value = lineName;
	if (props.map_filter_on && props.map_filter?.mode === "byLayer") {
		emits("filterByLayer", props.map_config, lineName);
	}
}
</script>

<template>
  <div
    v-if="activeChart === 'MetroLastMileLineChart'"
    class="metrolastmile"
  >
    <div class="metrolastmile-lines">
      <button
        v-for="line in lines"
        :key="line"
        :class="{
          'metrolastmile-line': true,
          'metrolastmile-line-active': activeLine === line,
        }"
        :style="{
          '--line-color': lineColors[line] || '#5a9cf8',
        }"
        @click="selectLine(line)"
      >
        {{ line }}
      </button>
    </div>

    <div class="metrolastmile-summary">
      <h5>{{ activeLine }}</h5>
      <span>{{ lineAverage }} {{ chart_config.unit }}</span>
    </div>

    <div class="metrolastmile-bars">
      <div
        v-for="row in selectedRows"
        :key="`${row.lineName}-${row.stationName}`"
        class="metrolastmile-row"
      >
        <p :title="row.stationName">
          {{ row.stationName }}
        </p>
        <div class="metrolastmile-track">
          <div
            class="metrolastmile-bar"
            :style="{
              width: `${Math.max(row.value, 2)}%`,
              backgroundColor: colorForValue(row.value),
            }"
          />
        </div>
        <strong>{{ row.value }}</strong>
      </div>
    </div>
  </div>
</template>

<style scoped lang="scss">
* {
	margin: 0;
	padding: 0;
	font-family: "微軟正黑體", "Microsoft JhengHei", "Droid Sans", "Open Sans",
		"Helvetica";
	box-sizing: border-box;
}

button {
	border: none;
	background: transparent;
	color: inherit;
}

.metrolastmile {
	width: 100%;
	height: 100%;
	display: grid;
	grid-template-rows: auto auto 1fr;
	row-gap: 0.6rem;
	padding: 0 0.25rem;
	overflow: hidden;

	&-lines {
		display: flex;
		gap: 0.4rem;
		overflow-x: auto;
		padding-bottom: 0.15rem;
	}

	&-line {
		height: 1.9rem;
		padding: 0 0.65rem;
		border-radius: 5px;
		background-color: #3d3f42;
		color: var(--color-complement-text);
		font-size: var(--font-s);
		font-weight: 700;
		white-space: nowrap;
		cursor: pointer;
		border-bottom: 2px solid transparent;
		transition: background-color 0.15s ease, color 0.15s ease;

		&-active {
			background-color: color-mix(in srgb, var(--line-color) 35%, #3d3f42);
			color: white;
			border-bottom-color: var(--line-color);
		}
	}

	&-summary {
		display: flex;
		align-items: baseline;
		justify-content: space-between;
		gap: 0.75rem;

		h5 {
			color: white;
			font-size: var(--font-m);
			line-height: 1.2;
		}

		span {
			color: var(--color-highlight);
			font-size: var(--font-ms);
			font-weight: 800;
			white-space: nowrap;
		}
	}

	&-bars {
		min-height: 0;
		overflow-y: auto;
		display: flex;
		flex-direction: column;
		gap: 0.48rem;
		padding-right: 0.25rem;
	}

	&-row {
		display: grid;
		grid-template-columns: minmax(4rem, 5.5rem) minmax(0, 1fr) 2.75rem;
		align-items: center;
		column-gap: 0.55rem;
		min-height: 1.25rem;

		p {
			color: var(--color-complement-text);
			font-size: var(--font-s);
			font-weight: 700;
			white-space: nowrap;
			text-overflow: ellipsis;
			overflow: hidden;
		}

		strong {
			color: white;
			font-size: var(--font-ms);
			line-height: 1;
			text-align: right;
		}
	}

	&-track {
		height: 1rem;
		background-color: rgba(255, 255, 255, 0.08);
		border-radius: 3px;
		overflow: hidden;
	}

	&-bar {
		height: 100%;
		min-width: 0.25rem;
		border-radius: 3px;
	}
}
</style>

