import { Trend } from '../../types/stats';

export function calculateTrend(data: number[], prev: number[]): Trend {
  const avg = (arr: number[]) =>
    arr.length ? arr.reduce((sum, v) => sum + v, 0) / arr.length : 0;

  const prevAvg = avg(prev);
  const currAvg = avg(data);
  const change = currAvg - prevAvg;

  return {
    current: currAvg,
    previous: prevAvg,
    direction: change > 0 ? 'up' : change < 0 ? 'down' : '',
    change,
  };
}

export function getQuartile(q: number, arr: Float64Array): number {
  const pos = q * (arr.length - 1);
  const lower = Math.floor(pos);
  const upper = Math.ceil(pos);

  return lower === upper
    ? arr[lower]
    : arr[lower] + (arr[upper] - arr[lower]) * (pos - lower);
}

export function normalizeSleepStr(
  time: string | undefined,
  referenceHour: number = 18,
): number {
  if (!time) return 0;

  // time = "HH:MM:SS"
  const [h, m, s] = time.split(':').map(Number);
  if (h >= referenceHour) return (h - referenceHour) * 60 + m + s / 60;
  return (h + 24 - referenceHour) * 60 + m + s / 60;
}

export function SleepStrMinToTime(
  minutes: number,
  referenceHour: number = 18,
): string {
  let totalMinutes = Math.round(minutes);
  let hours = Math.floor(totalMinutes / 60) + referenceHour;
  let mins = totalMinutes % 60;
  if (hours >= 24) hours -= 24;
  return `${hours.toString().padStart(2, '0')}:${mins.toString().padStart(2, '0')}`;
}
