import { Bloc } from '../../types/bloc';
import { HealthWatchData, StatGauge, Trend } from '../../types/stats';
import {
  calculateTrend,
  getQuartile,
  normalizeSleepStr,
  SleepStrMinToTime,
} from './stats-utils';

export function minutesToHour(value: number) {
  const hours = Math.floor(value / 60);
  const minutes = Math.round(value % 60); // Ensure proper rounding

  const formattedHours = String(hours);
  const formattedMinutes = String(minutes).padStart(2, '0');

  return `${formattedHours}h${formattedMinutes}`;
}

export function processHealthData(
  data: HealthWatchData[],
  latestOnly: boolean,
  notes: Bloc[],
) {
  let ret = {
    averages: {
      sleep_asleep: 0,
      sleep_start: 0,
      hrv: 0,
      strain: 0,
      recovery: 0,
      restingHR: 0,
    },
    trends: {
      sleep_asleep: undefined,
      hrv: undefined,
      strain: undefined,
      recovery: undefined,
      restingHR: undefined,
    },
    strainRecoveryComboGraph: { labels: [], datasets: [] },
    sleepRecoveryComboGraph: { labels: [], datasets: [] },
    sleepEfficiencyComboGraph: { labels: [], datasets: [] },
    gauges: {
      strain: undefined,
      recovery: undefined,
      hrv: undefined,
    },
  };

  if (!data.length) return ret;
  const LATEST_COUNT = 30;

  const sorted = data.sort(
    (a, b) => new Date(a.cdate).getTime() - new Date(b.cdate).getTime(),
  );
  const slice = latestOnly ? sorted.slice(-LATEST_COUNT) : sorted;

  const sleep_asleep = slice
    .map((d) => d.sleep_asleep)
    .filter((n): n is number => n !== undefined);
  const sleep_start = slice
    .map((d) => normalizeSleepStr(d.sleep_start))
    .filter((n): n is number => n !== undefined);
  const whoop_sleepscore = slice
    .map((d) => d.whoop_sleepscore)
    .filter((n): n is number => n !== undefined);
  const sleep_end = slice
    .map((d) => normalizeSleepStr(d.sleep_end, 0))
    .filter((n): n is number => n !== undefined);
  const sleep_total = slice
    .map((d) => d.sleep_total)
    .filter((n): n is number => n !== undefined);
  const hrv = slice
    .map((d) => d.hrv)
    .filter((n): n is number => n !== undefined);
  const strain = slice
    .map((d) => d.whoop_strain)
    .filter((n): n is number => n !== undefined);
  const recovery = slice
    .map((d) => d.whoop_recovery)
    .filter((n): n is number => n !== undefined);
  const restingHR = slice
    .map((d) => d.hr_resting)
    .filter((n): n is number => n !== undefined);

  const avg = (arr: number[]) => arr.reduce((a, b) => a + b, 0) / arr.length;

  const averages = {
    sleep_asleep: avg(sleep_asleep),
    sleep_total: avg(sleep_total),
    hrv: Math.round(avg(hrv)),
    strain: +avg(strain).toFixed(1),
    recovery: Math.round(avg(recovery)),
    restingHR: Math.round(avg(restingHR)),
  };

  let trends: {
    sleep_asleep: Trend | undefined;
    hrv: Trend | undefined;
    strain: Trend | undefined;
    recovery: Trend | undefined;
    restingHR: Trend | undefined;
  } = {
    sleep_asleep: undefined,
    hrv: undefined,
    strain: undefined,
    recovery: undefined,
    restingHR: undefined,
  };

  //Trends only for latestOnly option, if 2x LATEST_COUNT(30d) sample size
  if (latestOnly && sorted.length > 2 * LATEST_COUNT) {
    const previous_data = sorted.slice(-LATEST_COUNT * 2, -LATEST_COUNT);
    const previous_sleep_total = previous_data
      .map((d) => d.sleep_total)
      .filter((n): n is number => n !== undefined);
    const previoushrv = previous_data
      .map((d) => d.hrv)
      .filter((n): n is number => n !== undefined);
    const previousstrain = previous_data
      .map((d) => d.whoop_strain)
      .filter((n): n is number => n !== undefined);
    const previousrecovery = previous_data
      .map((d) => d.whoop_recovery)
      .filter((n): n is number => n !== undefined);
    const previousrestingHR = previous_data
      .map((d) => d.hr_resting)
      .filter((n): n is number => n !== undefined);

    trends = {
      sleep_asleep: calculateTrend(sleep_total, previous_sleep_total),
      hrv: calculateTrend(hrv, previoushrv),
      strain: calculateTrend(strain, previousstrain),
      recovery: calculateTrend(recovery, previousrecovery),
      restingHR: calculateTrend(restingHR, previousrestingHR),
    };
  }

  // Normalize labels
  const labels = slice.map((d) =>
    new Date(d.cdate).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: '2-digit',
    }),
  );

  // Parse notes to dict with key being cdate, append duplicates
  const parsedNotes = notes.reduce(
    (acc, note) => {
      if (acc[note.cdate]) acc[note.cdate] += '\n' + note.content;
      else acc[note.cdate] = note.content;
      return acc;
    },
    {} as { [date: string]: string },
  );

  const strainRecoveryComboGraph = {
    labels,
    datasets: [
      {
        label: 'Notes',
        data: slice.map((obj, index) => {
          if (!(obj.cdate in parsedNotes)) return { x: index, y: null };
          return {
            x: index,
            y: 0,
            content: parsedNotes[obj.cdate],
          };
        }),
        pointBackgroundColor: '#909090',
        pointRadius: 10,
        showLine: false,
        yAxisID: 'yNotes',
      },
      {
        label: 'HRV',
        data: hrv.map((hrv, index) => ({
          x: index,
          y: hrv,
          unit: 'ms',
        })),
        yAxisID: 'yHRV',
        borderColor: '#b78bc9',
        backgroundColor: '#b78bc91A',
        tension: 0.4,
        fill: false,
        pointRadius: 0,
        borderWidth: 1,
      },
      {
        label: 'Whoop Strain™',
        data: strain,
        yAxisID: 'yStrain',
        borderColor: '#3b82f6',
        backgroundColor: '#3b82f61A',
        tension: 0.4,
        fill: true,
        pointRadius: 0,
        borderWidth: 0,
      },
      {
        label: 'Whoop Recovery™',
        data: recovery,
        yAxisID: 'yRecovery',
        borderColor: '#15803d',
        tension: 0.4,
        fill: false,
        pointRadius: 0,
        borderWidth: 2,
        segment: {
          borderColor: (ctx: any) => {
            const value = ctx.p0.parsed.y;
            return value >= 66
              ? '#15803d'
              : value >= 33
                ? '#facc15'
                : '#dc2626';
          },
        },
      },
    ],
  };

  const sleepRecoveryComboGraph = {
    labels,
    datasets: [
      {
        label: 'Sleep (asleep)',
        data: sleep_asleep.map((sleep, index) => ({
          x: index,
          y: sleep,
          dValue: minutesToHour(sleep),
          unit: 'h',
        })),
        yAxisID: 'ySleepAsleep',
        borderColor: '#1f9250',
        backgroundColor: '#1f92501A',
        tension: 0.4,
        fill: true,
        pointRadius: 0,
        borderWidth: 0,
      },
      {
        label: 'SleepBaseHeight', // Basic 8hour y-axis line
        data: sleep_asleep.map((_, index) => ({
          x: index,
          y: 8 * 60,
          unit: 'min',
          hide: true,
        })),
        yAxisID: 'ySleep',
        borderColor: '#1f9250',
        backgroundColor: '#1f92501A',
        tension: 0.4,
        borderDash: [3, 6],
        fill: false,
        pointRadius: 0,
        hoverRadius: 0,
        borderWidth: 1,
      },
      {
        label: 'HRV',
        data: hrv.map((hrv, index) => ({
          x: index,
          y: hrv,
          unit: 'ms',
        })),
        yAxisID: 'yHRV',
        borderColor: '#b78bc9',
        backgroundColor: '#b78bc91A',
        tension: 0.4,
        fill: false,
        pointRadius: 0,
        borderWidth: 1,
      },
      {
        label: 'Resting HR',
        data: restingHR.map((rhr, index) => ({
          x: index,
          y: rhr,
          unit: 'bpm',
        })),
        yAxisID: 'yRHR',
        borderColor: '#a52a2a',
        backgroundColor: '#a52a2a1A',
        tension: 0.4,
        fill: false,
        pointRadius: 0,
        borderWidth: 1,
      },
    ],
  };

  const sleepEfficiencyComboGraph = {
    labels,
    datasets: [
      {
        label: whoop_sleepscore ? 'Whoop Score™' : 'Efficiency',
        data: whoop_sleepscore
          ? whoop_sleepscore.map((score, index) => ({
              x: index,
              y: score,
              unit: '%',
            }))
          : sleep_total.map((sleep_t, index) => ({
              x: index,
              y: Math.round((100 * sleep_asleep[index]) / sleep_t),
              unit: '%',
            })),
        yAxisID: 'yEfficiency',
        borderColor: '#B6BCC4',
        backgroundColor: '#B6BCC41A',
        tension: 0.4,
        fill: false,
        pointRadius: 0,
        borderWidth: 2,
      },
      {
        label: 'Sleep (asleep)',
        data: sleep_asleep.map((sleep, index) => ({
          x: index,
          y: sleep,
          dValue: minutesToHour(sleep),
          unit: 'h',
        })),
        yAxisID: 'ySleepAsleep',
        borderColor: '#1f9250',
        backgroundColor: '#1f92501A',
        tension: 0.4,
        fill: true,
        pointRadius: 0,
        borderWidth: 0,
      },
      {
        label: 'Sleep (total)',
        data: sleep_total.map((sleep, index) => ({
          x: index,
          y: sleep,
          dValue: minutesToHour(sleep),
          unit: 'h',
        })),
        yAxisID: 'ySleepTotal',
        borderColor: '#1f9250',
        backgroundColor: '#1f92501A',
        tension: 0.4,
        fill: true,
        pointRadius: 0,
        borderWidth: 0,
      },
      {
        label: 'SleepBaseHeight', // Basic 8hour y-axis line
        data: sleep_asleep.map((_, index) => ({
          x: index,
          y: 8 * 60,
          unit: 'min',
          hide: true,
        })),
        yAxisID: 'ySleep',
        borderColor: '#1f9250',
        backgroundColor: '#1f92501A',
        tension: 0.4,
        borderDash: [3, 6],
        fill: false,
        pointRadius: 0,
        hoverRadius: 0,
        borderWidth: 1,
      },
      {
        label: 'Bed Time',
        data: sleep_start.map((sleep, index) => ({
          x: index,
          y: sleep,
          dValue: SleepStrMinToTime(sleep),
        })),
        yAxisID: 'yBedtime',
        borderColor: '#bedbed',
        backgroundColor: '#bedbed1A',
        tension: 0.4,
        fill: false,
        pointRadius: 0,
        borderWidth: 2,
      },
      {
        label: 'Wake Time',
        data: sleep_end.map((sleep, index) => ({
          x: index,
          y: sleep,
          dValue: SleepStrMinToTime(sleep, 0),
        })),
        yAxisID: 'yWaketime',
        borderColor: '#F9D976',
        backgroundColor: '#F9D9761A',
        tension: 0.4,
        fill: false,
        pointRadius: 0,
        borderWidth: 2,
      },
    ],
  };

  const gauge = (arr: number[], avgValue: number): StatGauge => {
    const sorted = new Float64Array(arr).sort();
    const max = sorted[sorted.length - 1] || 1;
    return {
      first: sorted[0],
      last: max,
      average_pct: (100 * avgValue) / max,
      q_start_pct: (100 * getQuartile(0.25, sorted)) / max,
      q_end_pct: (100 * getQuartile(0.75, sorted)) / max,
    };
  };

  return {
    averages,
    trends: trends,
    strainRecoveryComboGraph,
    sleepRecoveryComboGraph,
    sleepEfficiencyComboGraph,
    gauges: {
      strain: gauge(strain, averages.strain),
      recovery: gauge(recovery, averages.recovery),
      hrv: gauge(hrv, averages.hrv),
    },
  };
}
