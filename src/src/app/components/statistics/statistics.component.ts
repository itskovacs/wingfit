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
import { processDurationsData } from './duration-processing';
import { StatGauge, Trend } from '../../types/stats';
import { AsyncPipe, CommonModule } from '@angular/common';
import { Bloc, BlocCategory } from '../../types/bloc';

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
    CommonModule,
    AsyncPipe,
  ],
  standalone: true,
  templateUrl: './statistics.component.html',
  styleUrl: './statistics.component.scss',
})
export class StatisticsComponent {
  year: number = new Date().getFullYear();
  today: Date = new Date();
  isMobile =
    window.screen.width < 768 || navigator.userAgent.indexOf('Mobi') > -1;

  categories$: Observable<BlocCategory[]>;

  categoryDurationPerWeek: any;
  durationsByCategory: any;
  strainRecoveryComboGraph: any;
  sleepRecoveryComboGraph: any;
  sleepEfficiencyComboGraph: any;

  averageSleepDuration = 0;
  averageStrain = 0;
  averageRecovery = 0;
  averageHRV = 0;
  averageRestingHR = 0;
  totalWorkoutsHours = 0;

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

  comboGraphOptions = {
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
    this.getData();
  }

  loadHealthData() {
    this.apiService.getHealthWatchData(this.year).subscribe((data) => {
      const result = processHealthData(data, this.latestOnly, this.notes);

      this.averageSleepDuration = result.averages.sleep_asleep;
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

  getData() {
    forkJoin({
      total: this.apiService.getWeeklyDurationTotal(this.year),
      health: this.apiService.getHealthWatchData(this.year),
      durations: this.apiService.getWeeklyDuration(this.year),
      notes: this.apiService.getNoteBlocs(),
    })
      .pipe(
        tap(({ total, notes }) => {
          this.totalWorkoutsHours = total.reduce(
            (sum, e) => sum + e.duration,
            0,
          );
          this.notes = notes;
        }),
        map(({ health, durations }) => {
          return {
            healthResult: processHealthData(
              health,
              this.latestOnly,
              this.notes,
            ),
            durationsResult: processDurationsData(durations),
          };
        }),
        tap(({ healthResult, durationsResult }) => {
          Object.assign(this, durationsResult);

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

  toggleDataRange() {
    this.latestOnly = !this.latestOnly;
    this.loadHealthData();
  }

  nextYear() {
    this.year = this.year + 1;
    this.latestOnly = this.year == this.today.getFullYear();
    this.getData();
  }

  previousYear() {
    this.year = this.year - 1;
    this.latestOnly = this.year == this.today.getFullYear();
    this.getData();
  }

  getWeekRange(weekNumber: number): string {
    const firstDayOfYear = new Date(this.year, 0, 1);
    const daysOffset = (weekNumber - 1) * 7;
    const firstWeekStart =
      firstDayOfYear.getDate() - firstDayOfYear.getDay() + 1;

    const fromDate = new Date(this.year, 0, firstWeekStart + daysOffset);
    const toDate = new Date(fromDate);
    toDate.setDate(fromDate.getDate() + 6);

    const formatDate = (date: Date) =>
      date.toLocaleDateString('en-GB', { day: '2-digit', month: 'short' });

    return `${formatDate(fromDate)} - ${formatDate(toDate)}`;
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
              if (count) this.getData();
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
              if (count) this.getData();
            },
          });
        }
      },
    });
  }
}
