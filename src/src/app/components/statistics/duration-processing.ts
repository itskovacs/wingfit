import { WeeklyDuration } from '../../types/stats';
import { getQuartile, minutesToHour } from './stats-utils';

export function processWeeklyDurationsData(data: WeeklyDuration[]) {
  if (!data.length)
    return {
      durationsByCategory: { labels: [], datasets: [] },
      categoryDurationPerWeek: { labels: [], datasets: [] },
    };

  return {
    durationsByCategory: {
      labels: data.map((c) => c.label),
      datasets: [
        {
          data: data.map((c) => c.data.reduce((sum, value) => sum + value, 0)),
          borderColor: data.map((c) => c.backgroundColor),
          backgroundColor: data.map((c) => c.backgroundColor),
        },
      ],
    },
    categoryDurationPerWeek: {
      labels: Array.from({ length: 52 }, (_, i) => i + 1),
      datasets: data.map((d) => ({
        ...d,
        type: 'bar',
        order: data.length - d.order, //ChartJS stacks from bottom to top, we reverse to keep the order
        borderColor: d.backgroundColor,
      })),
    },
  };
}

export function processWeekdayDurationsData(
  data: { [week: number]: number[][] },
  month: number,
  yearlyView: boolean,
) {
  if (!yearlyView && (!data[month] || !data[month].length))
    return { labels: [], datasets: [] };

  const labels = [
    'Monday',
    'Tuesday',
    'Wednesday',
    'Thursday',
    'Friday',
    'Saturday',
    'Sunday',
  ];
  const durationsByDay: number[][] = Array.from({ length: 7 }, () => []);

  let weeks: number[][];
  if (yearlyView) weeks = Object.values(data).flat();
  else weeks = data[month];

  weeks.forEach((weekArr: number[]) => {
    weekArr.forEach((val, idx) => {
      if (val && val > 0) durationsByDay[idx].push(val);
    });
  });

  let q: number[][] = [];
  let avgs: number[] = [];

  durationsByDay.forEach((_, index) => {
    let data = durationsByDay[index];
    const sorted = new Float64Array(data).sort();

    avgs.push(Math.round(data.reduce((a, b) => a + b, 0) / data.length));
    q.push([
      Math.round(getQuartile(0.25, sorted) || 0),
      Math.round(getQuartile(0.75, sorted) || 0),
    ]);
  });

  const weekdayComboGraph = {
    labels,
    datasets: [
      {
        label: 'Quartiles',
        type: 'bar',
        data: q.map((qArray, index) => ({
          x: qArray,
          y: index,
          dValue: `${minutesToHour(qArray[0])}h - ${minutesToHour(qArray[1])}h`,
        })),
        borderColor: '#6495ED',
        backgroundColor: '#6495ED',
        borderRadius: 8,
        borderSkipped: false,
        barPercentage: 0.5,
        order: 2,
      },
      {
        label: 'Average',
        type: 'scatter',
        data: avgs.map((avg, index) => ({
          x: avg,
          y: index,
          dValue: minutesToHour(avg),
          unit: 'h',
        })),
        borderColor: '#FACC15',
        backgroundColor: '#FACC15',
        pointStyle: 'rectRounded',
        borderWidth: 0, // no outline
        pointRadius: 9,
        pointHoverRadius: 10,
        showLine: false,
        order: 1,
      },
    ],
  };

  return weekdayComboGraph;
}
