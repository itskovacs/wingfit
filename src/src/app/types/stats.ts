import { BlocCategory } from './bloc';

export interface HealthWatchData {
  id: number;
  cdate: string;

  steps?: number;
  stand_time?: number;

  hr_min?: number;
  hr_max?: number;
  hr_avg?: number;
  hr_resting?: number;
  hrv?: number;

  whoop_recovery?: number;
  whoop_strain?: number;
  whoop_sleepscore?: number;

  sleep_asleep?: number;
  sleep_start?: string;
  sleep_end?: string;
  sleep_total?: number;
}

export interface BlocsByCategory extends BlocCategory {
  count: number;
}

export interface WeeklyDurationTotal {
  week: number;
  duration: number; //minutes
}

export interface WeeklyDuration {
  // Basically chartjs data interface
  label: string;
  order: number;
  backgroundColor: string;
  data: number[];
}

export interface StatGauge {
  first: number;
  last: number;
  average_pct: number;
  q_start_pct: number;
  q_end_pct: number;
}

export interface Trend {
  current: number;
  previous: number;
  direction: 'up' | 'down' | '';
  change: number;
}
