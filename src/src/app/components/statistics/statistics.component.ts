import { Component } from '@angular/core';
import { ApiService } from '../../services/api.service';
import { CardModule } from 'primeng/card';
import { ButtonModule } from 'primeng/button';
import { SkeletonModule } from 'primeng/skeleton';
import { ToolbarModule } from 'primeng/toolbar';
import { ChartModule } from 'primeng/chart';
import { ToggleButtonModule } from 'primeng/togglebutton';
import { MinutesToHoursPipe } from '../../shared/minutesToHour.pipe';
import { DialogService, DynamicDialogRef } from 'primeng/dynamicdialog';
import { HealthwatchUploadModalComponent } from '../../modals/healthwatch-upload-modal/healthwatch-upload-modal.component';
import { UtilsService } from '../../services/utils.service';
import { FormsModule } from '@angular/forms';
import { forkJoin, map, Observable, tap } from 'rxjs';
import { processHealthData } from './health-processing';
import {
  processWeeklyDurationsData,
  processWeekdayDurationsData,
} from './duration-processing';
import { HealthWatchData, StatGauge, Trend } from '../../types/stats';
import { AsyncPipe, CommonModule } from '@angular/common';
import { Bloc, BlocCategory } from '../../types/bloc';
import { TooltipModule } from 'primeng/tooltip';
import { AccordionModule } from 'primeng/accordion';

@Component({
  selector: 'app-statistics',
  imports: [
    FormsModule,
    CardModule,
    ButtonModule,
    MinutesToHoursPipe,
    SkeletonModule,
    ChartModule,
    ToolbarModule,
    ToggleButtonModule,
    AccordionModule,
    CommonModule,
    AsyncPipe,
    TooltipModule,
  ],
  standalone: true,
  templateUrl: './statistics.component.html',
  styleUrl: './statistics.component.scss',
})
export class StatisticsComponent {
  today: Date = new Date();
  selectedMonth: { year: number; month: number } = {
    year: this.today.getFullYear(),
    month: this.today.getMonth() + 1,
  };
  yearlyView = false;
  sliceLength: number | undefined;

  healthDataCache: { [year: number]: HealthWatchData[] } = {};

  isMobile =
    window.screen.width < 768 || navigator.userAgent.indexOf('Mobi') > -1;

  categories$: Observable<BlocCategory[]>;

  categoryDurationPerWeek: any;
  durationsByCategory: any;
  strainRecoveryComboGraph: any;
  sleepRecoveryComboGraph: any;
  sleepEfficiencyComboGraph: any;
  weekdayComboGraph: any;

  averageSleepDuration = 0;
  averageStrain = 0;
  averageRecovery = 0;
  averageHRV = 0;
  averageRestingHR = 0;
  totalWorkoutsHours = 0;

  cacheWeekdays = {};

  strainGauge: StatGauge | undefined;
  recoveryGauge: StatGauge | undefined;
  hrvGauge: StatGauge | undefined;

  latestOnly = true;

  sleepTrend: Trend | undefined;
  restingHRTrend: Trend | undefined;
  hrvTrend: Trend | undefined;
  strainTrend: Trend | undefined;
  recoveryTrend: Trend | undefined;

  notes: Bloc[] = [];

  pieGraphOptions = {
    maintainAspectRatio: false,
    responsive: true,
    animation: false,
    plugins: {
      tooltip: {
        enabled: false,
        callbacks: {
          label: (tooltipItem: any) => {
            const value = tooltipItem.raw;
            return (
              `${tooltipItem.label}: ` +
              `${(value / 60) ^ 0}`.slice(-2) +
              'h' +
              ('0' + (value % 60)).slice(-2)
            );
          },
        },
        external: this.customChartTooltip.bind(this),
      },
      legend: { display: false },
    },
  };

  stackedGraphOptions = {
    maintainAspectRatio: false,
    aspectRatio: 0.75,
    responsive: true,
    animation: false,
    indexAxis: 'x',
    scales: {
      x: {
        stacked: true,
        grid: {
          display: false,
        },
      },
      y: {
        stacked: true,
        ticks: {
          callback: (value: number) =>
            `${(value / 60) ^ 0}`.slice(-2) +
            'h' +
            ('0' + (value % 60)).slice(-2),
        },
      },
    },
    plugins: {
      legend: { display: false },
      tooltip: {
        enabled: false,
        mode: 'index',
        itemSort: function (a: any, b: any) {
          return b.dataset.order - a.dataset.order;
        },
        callbacks: {
          title: (tooltipItems: any) => {
            return tooltipItems.length
              ? this.getWeekRange(tooltipItems[0].label)
              : '';
          },
          label: (tooltipItem: any) => {
            const value = tooltipItem.raw;
            return value !== 0
              ? `${tooltipItem.dataset.label}: ${value}min`
              : '';
          },
        },
        filter: (tooltipItem: any) => tooltipItem.raw !== 0,
        external: this.customChartTooltip.bind(this),
      },
    },
  };

  strainRecoveryComboGraphOptions = {
    maintainAspectRatio: false,
    aspectRatio: 0.75,
    responsive: true,
    animation: false,
    interaction: {
      mode: 'index',
      intersect: false,
    },
    plugins: {
      tooltip: {
        enabled: false,
        external: this.customChartTooltip.bind(this),
      },
      legend: { display: false },
    },
    scales: {
      x: {
        grid: {
          display: false,
        },
      },
      yStrain: {
        grid: {
          display: false,
        },
        min: 0,
        display: true,
        position: 'left',
      },
      yNotes: {
        display: false,
        min: 0,
      },
      yHRV: {
        display: false,
        min: 0,
      },
      yRecovery: {
        display: true,
        position: 'right',
      },
    },
  };

  sleepRecoveryComboGraphOptions = {
    maintainAspectRatio: false,
    aspectRatio: 0.75,
    responsive: true,
    animation: false,
    interaction: {
      mode: 'index',
      intersect: false,
    },
    plugins: {
      tooltip: {
        enabled: false,
        external: this.customChartTooltip.bind(this),
      },
      legend: { display: false },
    },
    scales: {
      x: {
        grid: {
          display: false,
        },
      },
      yHRV: {
        grid: {
          display: false,
        },
        min: 0,
        display: true,
        position: 'left',
      },
      ySleep: {
        display: false,
      },
      ySleepAsleep: {
        display: false,
      },
      yRHR: {
        display: true,
        position: 'right',
      },
    },
  };

  weekdayComboGraphOptions = {
    indexAxis: 'y',
    maintainAspectRatio: false,
    aspectRatio: 1,
    responsive: true,
    animation: false,
    interaction: {
      mode: 'index',
      axis: 'y',
      intersect: false,
    },
    plugins: {
      tooltip: {
        enabled: false,
        external: this.customChartTooltip.bind(this),
      },
      legend: { display: false },
    },
    scales: {
      x: {
        grid: {
          display: false,
        },
      },
    },
  };

  sleepEfficiencyComboGraphOptions = {
    maintainAspectRatio: false,
    aspectRatio: 0.75,
    responsive: true,
    animation: false,
    interaction: {
      mode: 'index',
      intersect: false,
    },
    plugins: {
      tooltip: {
        enabled: false,
        external: this.customChartTooltip.bind(this),
      },
      legend: { display: false },
    },
    scales: {
      x: {
        grid: {
          display: false,
        },
      },
      ySleep: {
        display: false,
      },
      ySleepTotal: {
        grid: {
          display: false,
        },
        display: true,
        position: 'left',
      },
      ySleepAsleep: {
        display: false,
      },
      yBedtime: {
        display: false,
      },
      yWaketime: {
        display: false,
      },
      yEfficiency: {
        display: true,
        position: 'right',
        min: 0,
        max: 100,
      },
    },
  };

  getMonthName(): string {
    return new Date(0, this.selectedMonth.month - 1).toLocaleString('en-US', {
      month: 'long',
    });
  }

  constructor(
    private apiService: ApiService,
    private utilsService: UtilsService,
    private dialogService: DialogService,
  ) {
    if (this.isMobile) {
      let options: any = {};
      options.indexAxis = 'y';
      options.aspectRatio = 0.3;
      options.scales = {
        x: {
          stacked: true,
          grid: {
            display: false,
          },
          ticks: {
            callback: (value: number) =>
              `${(value / 60) ^ 0}`.slice(-2) +
              'h' +
              ('0' + (value % 60)).slice(-2),
          },
        },
        y: {
          stacked: true,
          ticks: {},
        },
      };

      this.stackedGraphOptions = { ...this.stackedGraphOptions, ...options };
    }

    this.categories$ = this.apiService.getCategories();
    this.getYearlyData();
  }

  sliceHealthData(hwdata: HealthWatchData[]): {
    current: HealthWatchData[];
    prev: HealthWatchData[];
  } {
    if (this.yearlyView) {
      const current = hwdata.filter(
        (d) => new Date(d.cdate).getFullYear() === this.selectedMonth.year,
      );
      return { current, prev: [] };
    }

    const { year, month } = this.selectedMonth;
    const current = hwdata.filter((d) => {
      const date = new Date(d.cdate);
      return date.getFullYear() === year && date.getMonth() + 1 === month;
    });
    let prev: HealthWatchData[] = [];
    const { year: prevYear, month: prevMonth } = this.getPrevMonth(
      this.selectedMonth,
    );

    this.sliceLength = current.length;
    if (!current.length) return { current, prev };

    prev = hwdata.filter((d) => {
      const date = new Date(d.cdate);
      return (
        date.getFullYear() === prevYear && date.getMonth() + 1 === prevMonth
      );
    });

    return { current, prev };
  }

  customChartTooltip(context: any) {
    const { chart, tooltip } = context;

    let tooltipEl = document.getElementById(
      'chartjs-tooltip',
    ) as HTMLDivElement;

    if (!tooltipEl) {
      tooltipEl = document.createElement('div');
      tooltipEl.id = 'chartjs-tooltip';
      tooltipEl.className = 'chartjs-tooltip';
      document.body.appendChild(tooltipEl);
    }

    if (tooltip.opacity === 0) {
      tooltipEl.style.opacity = '0';
      tooltipEl.style.pointerEvents = 'none';
      return;
    }

    const title = tooltip.title?.[0] ?? '';
    const items = tooltip.dataPoints ?? [];

    let innerHtml = `<div class="tooltip-container">
      <div class="tooltip-header">${title}</div>`;

    let itemNotes: any = undefined;
    items.map((item: any, index: number) => {
      if (item.raw?.hide) return;
      if (item.raw?.content) {
        itemNotes = item;
        return;
      }

      innerHtml += `
        <div class="tooltip-row">
          <span class="tooltip-color" style="background:${item.element.options.borderColor}"></span>
          <span class="tooltip-label">${tooltip.body[index].lines.flat()[0].split(':')[0]}</span>
          <span class="tooltip-value">${item.raw?.dValue || tooltip.body[index].lines.flat()[0].split(':')[1]}<span style="font-size: 0.75rem; color: #777;">${item.raw?.unit || ''}</span></span>
        </div>
      `;
    });

    // Append the note
    if (itemNotes) {
      innerHtml += `<div class="tooltip-row tooltip-row-border" style="border-color: ${itemNotes.element.options.borderColor}">${itemNotes.raw?.content}</div>`;
    }

    tooltipEl.innerHTML = innerHtml;
    tooltipEl.style.opacity = '1';
    tooltipEl.style.position = 'absolute';

    const canvasRect = chart.canvas.getBoundingClientRect();
    const tooltipRect = tooltipEl.getBoundingClientRect();

    const tooltipPositionX = canvasRect.left + window.scrollX + tooltip.caretX;
    const tooltipPositionY = canvasRect.top + window.scrollY + tooltip.caretY;

    const overflowRight =
      tooltipPositionX + tooltipRect.width >
      canvasRect.left + canvasRect.width + window.scrollX;
    if (overflowRight) {
      tooltipEl.style.left = `${tooltipPositionX - tooltipRect.width}px`;
    } else {
      tooltipEl.style.left = `${tooltipPositionX}px`;
    }
    tooltipEl.style.top = `${tooltipPositionY}px`;
    tooltipEl.style.pointerEvents = 'none';
  }

  getYearlyData() {
    forkJoin({
      hwdata: this.apiService.getHealthWatchData(this.selectedMonth.year),
      durations: this.apiService.getWeeklyDuration(this.selectedMonth.year),
      weekday: this.apiService.getWeekdayDuration(this.selectedMonth.year),
      notes: this.apiService.getNoteBlocs(),
    })
      .pipe(
        tap(({ durations, notes }) => {
          this.totalWorkoutsHours = durations.reduce(
            (sum, item) => sum + item.data.reduce((a, b) => a + b, 0),
            0,
          );
          this.notes = notes;
        }),
        map(({ hwdata, durations, weekday }) => {
          this.cacheWeekdays = weekday;
          const { current, prev } = this.sliceHealthData(hwdata);

          return {
            healthResult: processHealthData(current, this.notes, prev),
            durationsResult: processWeeklyDurationsData(durations),
            weekdayResult: processWeekdayDurationsData(
              this.cacheWeekdays,
              this.selectedMonth.month,
              this.yearlyView,
            ),
          };
        }),
        tap(({ healthResult, durationsResult, weekdayResult }) => {
          Object.assign(this, durationsResult);
          this.weekdayComboGraph = weekdayResult;

          this.averageSleepDuration = healthResult.averages.sleep_asleep;
          this.averageStrain = healthResult.averages.strain;
          this.averageRecovery = healthResult.averages.recovery;
          this.averageHRV = healthResult.averages.hrv;
          this.averageRestingHR = healthResult.averages.restingHR;

          this.strainRecoveryComboGraph = healthResult.strainRecoveryComboGraph;
          this.sleepRecoveryComboGraph = healthResult.sleepRecoveryComboGraph;
          this.sleepEfficiencyComboGraph =
            healthResult.sleepEfficiencyComboGraph;

          this.strainGauge = healthResult.gauges.strain;
          this.recoveryGauge = healthResult.gauges.recovery;
          this.hrvGauge = healthResult.gauges.hrv;

          if (healthResult.trends) {
            this.sleepTrend = healthResult.trends.sleep_asleep;
            this.strainTrend = healthResult.trends.strain;
            this.recoveryTrend = healthResult.trends.recovery;
            this.hrvTrend = healthResult.trends.hrv;
            this.restingHRTrend = healthResult.trends.restingHR;
          }
        }),
      )
      .subscribe();
  }

  loadHealthData() {
    this.apiService
      .getHealthWatchData(this.selectedMonth.year)
      .subscribe((data) => {
        const { current, prev } = this.sliceHealthData(data);

        const result = processHealthData(current, this.notes, prev);
        (this.weekdayComboGraph = processWeekdayDurationsData(
          this.cacheWeekdays,
          this.selectedMonth.month,
          this.yearlyView,
        )),
          (this.averageSleepDuration = result.averages.sleep_asleep);
        this.averageStrain = result.averages.strain;
        this.averageRecovery = result.averages.recovery;
        this.averageHRV = result.averages.hrv;
        this.averageRestingHR = result.averages.restingHR;

        this.strainRecoveryComboGraph = result.strainRecoveryComboGraph;
        this.sleepRecoveryComboGraph = result.sleepRecoveryComboGraph;
        this.sleepEfficiencyComboGraph = result.sleepEfficiencyComboGraph;

        this.strainGauge = result.gauges.strain;
        this.recoveryGauge = result.gauges.recovery;
        this.hrvGauge = result.gauges.hrv;

        if (result.trends) {
          this.sleepTrend = result.trends.sleep_asleep;
          this.strainTrend = result.trends.strain;
          this.recoveryTrend = result.trends.recovery;
          this.hrvTrend = result.trends.hrv;
          this.restingHRTrend = result.trends.restingHR;
        }
      });
  }

  getPrevMonth({ year, month }: { year: number; month: number }) {
    return month === 1
      ? { year: year - 1, month: 12 }
      : { year, month: month - 1 };
  }

  nextMonth() {
    let { year, month } = this.selectedMonth;
    let yearUpdated = false;
    month += 1;
    if (month > 12) {
      month = 1;
      year += 1;
      yearUpdated = true;
    }
    this.selectedMonth = { year, month };
    yearUpdated ? this.getYearlyData() : this.loadHealthData();
  }

  previousMonth() {
    let { year, month } = this.selectedMonth;
    let yearUpdated = false;
    month -= 1;
    if (month < 1) {
      month = 12;
      year -= 1;
      yearUpdated = true;
    }
    this.selectedMonth = { year, month };
    yearUpdated ? this.getYearlyData() : this.loadHealthData();
  }

  nextYear() {
    this.selectedMonth = {
      year: this.selectedMonth.year + 1,
      month: this.selectedMonth.month,
    };
    this.getYearlyData();
  }

  previousYear() {
    this.selectedMonth = {
      year: this.selectedMonth.year - 1,
      month: this.selectedMonth.month,
    };
    this.getYearlyData();
  }

  toggleYearView() {
    this.yearlyView = !this.yearlyView;
    this.getYearlyData();
  }

  resetSelectedMonthToday() {
    this.selectedMonth = {
      year: this.today.getFullYear(),
      month: this.today.getMonth() + 1,
    };
    this.getYearlyData();
  }

  getWeekRange(weekNumber: number): string {
    const firstDayOfYear = new Date(this.selectedMonth.year, 0, 1);
    const daysOffset = (weekNumber - 1) * 7;
    const firstWeekStart =
      firstDayOfYear.getDate() - firstDayOfYear.getDay() + 1;

    const fromDate = new Date(
      this.selectedMonth.year,
      0,
      firstWeekStart + daysOffset,
    );
    const toDate = new Date(fromDate);
    toDate.setDate(fromDate.getDate() + 6);

    const formatDate = (date: Date) =>
      date.toLocaleDateString('en-GB', { day: '2-digit', month: 'short' });

    return `${formatDate(fromDate)} - ${formatDate(toDate)}`;
  }

  getMonthsWithData(
    healthData: HealthWatchData[],
  ): { year: number; month: number; label: string }[] {
    // map {"YYYY-MM": [data]}
    const monthMap: { [k: string]: HealthWatchData[] } = {};
    healthData.forEach((d) => {
      const date = new Date(d.cdate);
      const y = date.getFullYear();
      const m = date.getMonth();
      const key = `${y}-${m + 1}`;
      if (!monthMap[key]) monthMap[key] = [];
      monthMap[key].push(d);
    });

    return Object.entries(monthMap)
      .map(([k, v]) => {
        const [year, month] = k.split('-').map(Number);
        return {
          year,
          month,
          label: new Date(year, month - 1).toLocaleDateString('en-US', {
            month: 'long',
            year: 'numeric',
          }),
        };
      })
      .sort((a, b) =>
        a.year !== b.year ? a.year - b.year : a.month - b.month,
      );
  }

  healthWatchUpload() {
    const modal: DynamicDialogRef = this.dialogService.open(
      HealthwatchUploadModalComponent,
      {
        header: 'Import data',
        modal: true,
        appendTo: 'body',
        closable: true,
        dismissableMask: true,
        width: '30vw',
        breakpoints: {
          '960px': '60vw',
          '640px': '90vw',
        },
      },
    );

    modal.onClose.subscribe({
      next: (data: { tab: string; fd: FormData } | null) => {
        if (!data) return;

        if (data.tab === 'whoop') {
          this.apiService.postWhoopData(data.fd).subscribe({
            next: (resp) => {
              const count = resp.count;
              this.utilsService.toast(
                'info',
                'Success',
                `${count} entr${count > 1 ? 'ies' : 'y'} imported`,
              );
              if (count) this.getYearlyData();
            },
          });
        } else if (data.tab === 'applewatch') {
          this.apiService.postAppleWatchData(data.fd).subscribe({
            next: (resp) => {
              const count = resp.count;
              this.utilsService.toast(
                'info',
                'Success',
                `${count} entr${count > 1 ? 'ies' : 'y'} imported`,
              );
              if (count) this.getYearlyData();
            },
          });
        }
      },
    });
  }
}
