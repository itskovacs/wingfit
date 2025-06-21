import { Component, ViewChild } from '@angular/core';
import {
  DragDropModule,
  CdkDragDrop,
  transferArrayItem,
} from '@angular/cdk/drag-drop';
import { FormsModule } from '@angular/forms';
import { ButtonModule } from 'primeng/button';
import { ToolbarModule } from 'primeng/toolbar';
import { TooltipModule } from 'primeng/tooltip';
import { CardModule } from 'primeng/card';
import { SkeletonModule } from 'primeng/skeleton';
import { UtilsService } from '../../services/utils.service';
import { DatePipe } from '@angular/common';
import { BlocComponent } from '../../shared/bloc/bloc.component';
import { Bloc, BlocResult } from '../../types/bloc';
import { ApiService } from '../../services/api.service';
import { forkJoin, Observable } from 'rxjs';
import { MinutesToHoursPipe } from '../../shared/minutesToHour.pipe';
import { MenuModule } from 'primeng/menu';
import { MenuItem } from 'primeng/api';
import { DialogService, DynamicDialogRef } from 'primeng/dynamicdialog';
import { BlocCreateModalComponent } from '../../modals/bloc-create-modal/bloc-create-modal.component';
import { ToDateModalComponent } from '../../modals/to-date-modal.component/to-date-modal.component';
import { YesNoModalComponent } from '../../modals/yes-no-modal/yes-no-modal.component';
import { BadgeModule } from 'primeng/badge';
import { OverlayBadgeModule } from 'primeng/overlaybadge';
import { BlocResultCreateModalComponent } from '../../modals/bloc-result-create-modal/bloc-result-create-modal.component';
import { SelectRangeDateModalComponent } from '../../modals/select-range-date-modal/select-range-date-modal.component';
import { Popover, PopoverModule } from 'primeng/popover';

@Component({
  selector: 'app-dashboard',
  imports: [
    ToolbarModule,
    ButtonModule,
    TooltipModule,
    SkeletonModule,
    PopoverModule,
    MenuModule,
    FormsModule,
    BadgeModule,
    OverlayBadgeModule,
    CardModule,
    DragDropModule,
    DatePipe,
    BlocComponent,
    MinutesToHoursPipe,
  ],
  standalone: true,
  templateUrl: './dashboard.component.html',
  styleUrl: './dashboard.component.scss',
})
export class DashboardComponent {
  @ViewChild('op') op?: Popover;
  todayDate: Date;
  selectedDate: Date;
  selectedDate_firstDayOfWeek: Date;
  selectedDate_lastDayOfWeek: Date;
  datesOfWeek_array: Date[];
  weekDays = Array.from({ length: 7 }, (_, i) =>
    new Intl.DateTimeFormat('en-US', { weekday: 'long' }).format(
      new Date(1970, 0, i + 5),
    ),
  );
  weekIsEmpty = true;
  clickedBloc: Bloc | undefined;

  displayedBlocs: { [key: string]: Bloc[] } = {};
  displayedBlocsDuration: { [key: string]: number } = {};

  selectionMode: boolean = false;
  selectedBlocs: Bloc[] = []; // Used on functions
  selectedBlocsID: number[] = []; // Used on html for checks

  blocClickActions: { text: string; icon: string; action: string }[] = [
    { text: 'Result', icon: 'pi pi-crown', action: 'result' },
    { text: 'Edit', icon: 'pi pi-file-edit', action: 'edit' },
    { text: 'Copy', icon: 'pi pi-copy', action: 'copy' },
    { text: 'Move', icon: 'pi pi-file-export', action: 'move' },
    { text: 'Delete', icon: 'pi pi-trash', action: 'delete' },
  ];
  toolbarMenuItems: MenuItem[] | undefined;

  constructor(
    private utilsService: UtilsService,
    private apiService: ApiService,
    private dialogService: DialogService,
  ) {
    this.selectedDate = this.utilsService.setHoursNoon();
    this.todayDate = this.utilsService.setHoursNoon();

    [this.selectedDate_firstDayOfWeek, this.selectedDate_lastDayOfWeek] =
      this.utilsService.getFirstAndLastDaysOfWeek(this.selectedDate);
    this.datesOfWeek_array = this.utilsService.getDatesOfWeek(
      this.selectedDate_firstDayOfWeek,
    );
    this.retrieveAndParseBlocs();

    this.toolbarMenuItems = [
      {
        label: 'Multiselect',
        icon: 'pi pi-th-large',
        command: () => {
          if (this.selectionMode) this.disableSelectionMode();
          else this.enableSelectionMode();
        },
      },
      {
        label: 'Copy next week',
        icon: 'pi pi-clone',
        command: () => {
          this.copyNextWeek();
        },
      },
    ];
  }

  createBloc(useSelectedDate: boolean = false): void {
    const modal: DynamicDialogRef = this.dialogService.open(
      BlocCreateModalComponent,
      {
        header: 'Create Bloc',
        modal: true,
        appendTo: 'body',
        closable: true,
        dismissableMask: true,
        width: '40vw',
        breakpoints: {
          '960px': '60vw',
          '640px': '90vw',
        },
        data: {
          date: useSelectedDate ? this.selectedDate : this.todayDate,
        },
      },
    );

    modal.onClose.subscribe({
      next: (bloc: Bloc | null) => {
        if (bloc) {
          this.apiService.postBloc(bloc).subscribe({
            next: (bloc: Bloc) => this.displayedBlocInteraction('create', bloc),
          });
        }
      },
    });
  }

  displayedBlocInteraction(type: string, blocs: Bloc | Bloc[]) {
    // Create, Delete, Edit or Move the Bloc in place of displayedBlocs object
    // Move is an exception because we have to iterate on all displayed blocs to find it, and modify it (delete if another date, create on another date)

    // Handle multiple Blocs (only for multiple selection 'copy'), cast to list if not
    if (!Array.isArray(blocs)) {
      blocs = [blocs];
    }

    // Maps the blocs actually displayed, to interact with the object and modify blocs in place
    let _displayedBlocs: Bloc[] = blocs.filter((bloc) =>
      this.datesOfWeek_array.some(
        (weekDate) => this.utilsService.Iso8601ToStr(weekDate) == bloc.cdate,
      ),
    );

    if (_displayedBlocs.length || type === 'move') {
      switch (type) {
        case 'create':
          _displayedBlocs.forEach((bloc) => {
            this.displayedBlocs[bloc.cdate].push(bloc);
            this.displayedBlocsDuration[bloc.cdate] += bloc.duration || 0;
          });
          this.sortDisplayedBlocs();
          break;

        case 'delete':
          _displayedBlocs.forEach((bloc) => {
            this.displayedBlocs[bloc.cdate].splice(
              this.displayedBlocs[bloc.cdate].findIndex((b) => b.id == bloc.id),
              1,
            );
            this.displayedBlocsDuration[bloc.cdate] -= bloc.duration || 0;
          });
          break;

        case 'edit':
          // Delete previous and insert the Bloc, that will be sorted afterwards
          _displayedBlocs.forEach((bloc) => {
            let editedBlocIndex = this.displayedBlocs[bloc.cdate].findIndex(
              (b) => b.id == bloc.id,
            );
            this.displayedBlocsDuration[bloc.cdate] -=
              this.displayedBlocs[bloc.cdate][editedBlocIndex].duration || 0; // Substract the bloc before edit duration
            this.displayedBlocs[bloc.cdate].splice(editedBlocIndex, 1, bloc);
            this.displayedBlocsDuration[bloc.cdate] += bloc.duration || 0; // Add the edited bloc duration
            this.sortDisplayedBlocs();
          });
          break;

        case 'move':
          blocs.forEach((bloc) => {
            if (!(bloc.cdate in this.displayedBlocs)) {
              // Bloc moved out of current week, delete the previous bloc in week
              Object.keys(this.displayedBlocs).some((weekdate) => {
                const index = this.displayedBlocs[weekdate].findIndex(
                  (b) => b.id === bloc.id,
                );
                if (index !== -1) {
                  this.displayedBlocs[weekdate].splice(index, 1);
                  return true;
                }
                return false;
              });
            } else {
              // Bloc moved in current week, delete the previous bloc in week
              Object.keys(this.displayedBlocs).some((weekdate) => {
                const index = this.displayedBlocs[weekdate].findIndex(
                  (b) => b.id === bloc.id,
                );
                if (index !== -1) {
                  this.displayedBlocs[weekdate].splice(index, 1);
                  return true;
                }
                return false;
              });

              // recreate it afterwards
              this.displayedBlocs[bloc.cdate].push(bloc);
              this.displayedBlocsDuration[bloc.cdate] += bloc.duration || 0;
            }
          });

          // Calculate displayedBlocsDuration from displayedBlocs, as the previous Bloc's date would have its duration
          Object.keys(this.displayedBlocs).forEach((weekdate) => {
            this.displayedBlocsDuration[weekdate] = this.displayedBlocs[
              weekdate
            ].reduce((acc, bloc) => acc + (bloc.duration || 0), 0);
          });

          this.sortDisplayedBlocs();
          break;
      }
    }
  }

  constructDisplayedBlocs(blocs: Bloc[]): void {
    this.weekIsEmpty = true;

    this.displayedBlocs = {};
    this.datesOfWeek_array.forEach((date) => {
      this.displayedBlocs[this.utilsService.Iso8601ToStr(date)] = [];
      this.displayedBlocsDuration[this.utilsService.Iso8601ToStr(date)] = 0;
    });

    blocs.forEach((bloc) => {
      this.weekIsEmpty = false;
      this.displayedBlocs[bloc.cdate].push(bloc);
      this.displayedBlocsDuration[bloc.cdate] =
        this.displayedBlocsDuration[bloc.cdate] + (bloc.duration || 0);
    });

    this.sortDisplayedBlocs();
  }

  sortDisplayedBlocs() {
    if (!this.weekIsEmpty) {
      Object.keys(this.displayedBlocs).forEach((d: string) => {
        this.displayedBlocs[d].sort((a: Bloc, b: Bloc) =>
          (a.category?.weight || -1) > (b.category?.weight || -1) ? 1 : -1,
        );
      });
    }
  }

  retrieveAndParseBlocs() {
    this.apiService
      .getBlocs(
        this.selectedDate_firstDayOfWeek,
        this.selectedDate_lastDayOfWeek,
      )
      .subscribe({
        next: (blocs) => {
          this.constructDisplayedBlocs(blocs);
        },
        error: () => {
          this.weekIsEmpty = true;
        },
      });
  }

  updateDateBlocs(): void {
    // This IF allows the mobile part to not GET again the blocs, as we are the same week
    if (
      this.selectedDate.getTime() <
        this.selectedDate_firstDayOfWeek.getTime() ||
      this.selectedDate.getTime() > this.selectedDate_lastDayOfWeek.getTime()
    ) {
      [this.selectedDate_firstDayOfWeek, this.selectedDate_lastDayOfWeek] =
        this.utilsService.getFirstAndLastDaysOfWeek(this.selectedDate);
      this.datesOfWeek_array = this.utilsService.getDatesOfWeek(
        this.selectedDate_firstDayOfWeek,
      );
      this.retrieveAndParseBlocs();
    }
  }

  datepickerOpen(): void {
    let modal = this.dialogService.open(SelectRangeDateModalComponent, {
      header: 'Select range',
      modal: true,
      appendTo: 'body',
      closable: true,
      dismissableMask: true,
      width: '20vw',
      breakpoints: {
        '960px': '50vw',
        '640px': '90vw',
      },
      data: this.selectedDate,
    });

    modal.onClose.subscribe({
      next: (date: Date | null) => {
        if (date) {
          this.selectedDate = new Date(this.utilsService.setHoursNoon(date));
          this.updateDateBlocs();
        }
      },
    });
  }

  prevWeek(): void {
    this.selectedDate = new Date(
      this.utilsService
        .setHoursNoon(this.selectedDate)
        .setDate(this.selectedDate.getDate() - 7),
    );
    this.updateDateBlocs();
  }

  prevDay(): void {
    this.selectedDate = new Date(
      this.utilsService
        .setHoursNoon(this.selectedDate)
        .setDate(this.selectedDate.getDate() - 1),
    );
    this.updateDateBlocs();
  }

  nextDay(): void {
    this.selectedDate = new Date(
      this.utilsService
        .setHoursNoon(this.selectedDate)
        .setDate(this.selectedDate.getDate() + 1),
    );
    this.updateDateBlocs();
  }

  nextWeek(): void {
    this.selectedDate = new Date(
      this.utilsService
        .setHoursNoon(this.selectedDate)
        .setDate(this.selectedDate.getDate() + 7),
    );
    this.updateDateBlocs();
  }

  copyNextWeek(): void {
    let bloc_count = Object.values(this.displayedBlocs).reduce(
      (sum, blocArray) => sum + blocArray.length,
      0,
    );
    if (bloc_count == 0) {
      this.utilsService.toast('warn', 'Empty week', 'Nothing to duplicate');
      return;
    }

    const modal: DynamicDialogRef = this.dialogService.open(
      YesNoModalComponent,
      {
        header: 'Confirm',
        modal: true,
        closable: true,
        dismissableMask: true,
        breakpoints: {
          '640px': '90vw',
        },
        data: `Duplicate this week's Blocs (${bloc_count}) to next week ?`,
      },
    );

    modal.onClose.subscribe({
      next: (bool) => {
        if (bool) {
          let POST_blocs$: Observable<Bloc>[] = Object.values(
            this.displayedBlocs,
          )
            .flatMap((blocs_by_date) => blocs_by_date) // Retrieve blocs displayed in week and convert it to Array of Blocs
            .map((bloc: any) => {
              let _bloc = { ...bloc };
              let blocDate = new Date(_bloc.cdate);
              blocDate.setDate(blocDate.getDate() + 7);
              return this.apiService.postBloc({
                ..._bloc,
                cdate: this.utilsService.Iso8601ToStr(blocDate),
              });
            });

          forkJoin(POST_blocs$).subscribe({
            next: (_) => {
              this.utilsService.toast(
                'success',
                'Success',
                'Blocs were copied to next week',
              );
            },
            error: (_) => {
              this.utilsService.toast(
                'error',
                'Error during copy',
                'An error occured during the blocs copy',
              );
            },
          });
        }
      },
    });
  }

  blocClicked(ev: any, bloc: Bloc) {
    if (!this.selectionMode) {
      this.clickedBloc = bloc;
      this.op?.toggle(ev);
      return;
    }

    // If it exists in selectedBlocs, it exists in selectedBlocsID as it's consistent, else we push it to both
    if (this.selectedBlocs.some((selected) => selected.id == bloc.id)) {
      this.selectedBlocs.splice(
        this.selectedBlocs.findIndex((selected) => selected.id == bloc.id),
        1,
      );
      this.selectedBlocsID.splice(this.selectedBlocsID.indexOf(bloc.id), 1);
    } else {
      this.selectedBlocs.push(bloc);
      this.selectedBlocsID.push(bloc.id);
    }
  }

  blocDbClicked(bloc: Bloc) {
    this.op?.hide();
    const modal = this.dialogService.open(BlocCreateModalComponent, {
      header: 'Edit Bloc',
      modal: true,
      appendTo: 'body',
      closable: true,
      dismissableMask: true,
      width: '40vw',
      breakpoints: {
        '960px': '60vw',
        '640px': '90vw',
      },
      data: { bloc: { ...bloc } },
    });

    modal.onClose.subscribe({
      next: (editedBloc: Bloc | null) => {
        if (editedBloc) {
          let blocModifiedKeysOnly: Partial<Bloc> =
            this.utilsService.getModifiedFields(bloc, editedBloc);

          if (Object.keys(blocModifiedKeysOnly).length) {
            this.apiService.putBloc(bloc.id, blocModifiedKeysOnly).subscribe({
              next: (bloc) => this.displayedBlocInteraction('edit', bloc),
            });
          }
        }
      },
    });
  }

  handleBlocAction(action: string) {
    let bloc: Bloc | undefined = this.clickedBloc;
    this.op?.hide(); // Hide popover

    if (bloc) {
      let modal: DynamicDialogRef;
      switch (action) {
        case 'result':
          modal = this.dialogService.open(BlocResultCreateModalComponent, {
            header: 'Result',
            modal: true,
            appendTo: 'body',
            closable: true,
            dismissableMask: true,
            width: '40vw',
            breakpoints: {
              '960px': '60vw',
              '640px': '90vw',
            },
            data: {
              bloc_id: bloc.id,
              result: bloc.result,
            },
          });

          modal.onClose.subscribe({
            next: (result: BlocResult | boolean | null) => {
              if (result === true) {
                // True is returned if the delete is done
                bloc.result = undefined;
                return;
              }

              if (result) {
                // BlocResult | null otherwise, so we check
                this.apiService.putBlocResult(bloc.id, result).subscribe({
                  next: (result) => (bloc.result = result),
                });
              }
            },
          });
          break;

        case 'edit':
          modal = this.dialogService.open(BlocCreateModalComponent, {
            header: 'Edit Bloc',
            modal: true,
            appendTo: 'body',
            closable: true,
            dismissableMask: true,
            width: '40vw',
            breakpoints: {
              '960px': '60vw',
              '640px': '90vw',
            },
            data: { bloc: { ...bloc } },
          });

          modal.onClose.subscribe({
            next: (editedBloc: Bloc | null) => {
              if (editedBloc) {
                let blocModifiedKeysOnly: Partial<Bloc> =
                  this.utilsService.getModifiedFields(bloc, editedBloc);

                if (Object.keys(blocModifiedKeysOnly).length) {
                  this.apiService
                    .putBloc(bloc.id, blocModifiedKeysOnly)
                    .subscribe({
                      next: (bloc) =>
                        this.displayedBlocInteraction('edit', bloc),
                    });
                }
              }
            },
          });
          break;

        case 'copy':
          modal = this.dialogService.open(ToDateModalComponent, {
            header: 'Copy to',
            modal: true,
            closable: true,
            focusOnShow: false,
            dismissableMask: true,
            data: { ...bloc },
          });

          modal.onClose.subscribe({
            next: (date: Date | null) => {
              if (date) {
                this.apiService
                  .postBloc({
                    ...bloc,
                    cdate: this.utilsService.Iso8601ToStr(date),
                  })
                  .subscribe({
                    next: (bloc) =>
                      this.displayedBlocInteraction('create', bloc),
                  });
              }
            },
          });
          break;

        case 'move':
          modal = this.dialogService.open(ToDateModalComponent, {
            header: 'Move to',
            modal: true,
            closable: true,
            focusOnShow: false,
            dismissableMask: true,
            data: { ...bloc },
          });

          modal.onClose.subscribe({
            next: (date: Date | null) => {
              if (date) {
                this.apiService
                  .putBloc(bloc.id, {
                    cdate: this.utilsService.Iso8601ToStr(date),
                  })
                  .subscribe({
                    next: (bloc) => this.displayedBlocInteraction('move', bloc),
                  });
              }
            },
          });
          break;

        case 'delete':
          modal = this.dialogService.open(YesNoModalComponent, {
            header: 'Confirm',
            modal: true,
            closable: true,
            dismissableMask: true,
            breakpoints: {
              '640px': '90vw',
            },
            data: `Delete the ${bloc.category.name} Bloc ?`,
          });

          modal.onClose.subscribe({
            next: (bool) => {
              if (bool) {
                this.apiService.deleteBloc(bloc.id).subscribe({
                  next: (_) => this.displayedBlocInteraction('delete', bloc),
                });
              }
            },
          });
          break;

        default:
          this.utilsService.toast(
            'warn',
            'Unhandled event',
            'This Bloc Action is not handled',
          );
          break;
      }
    }
  }

  resetDateToToday(): void {
    this.selectedDate = this.utilsService.setHoursNoon(this.todayDate);
    this.updateDateBlocs();
  }

  dateToStr(date: Date): string {
    return this.utilsService.Iso8601ToStr(date);
  }

  dayClicked(date: Date): void {
    this.selectedDate = new Date(this.utilsService.setHoursNoon(date));
  }

  // Selection Mode
  selectionModeCopy(): void {
    let modal = this.dialogService.open(ToDateModalComponent, {
      header: 'Copy selected to',
      modal: true,
      closable: true,
      focusOnShow: false,
      dismissableMask: true,
    });

    modal.onClose.subscribe({
      next: (date: Date | null) => {
        if (date) {
          let _date: string = this.utilsService.Iso8601ToStr(date); //To not call everytime the fn

          this.apiService
            .postBlocs(
              // POST every blocs at once
              this.selectedBlocs.map((bloc: Bloc) => {
                return { ...bloc, cdate: _date };
              }),
            )
            .subscribe({
              next: (blocs: Bloc[]) => {
                this.displayedBlocInteraction('create', blocs);
              },
              error: () => {
                this.utilsService.toast(
                  'error',
                  'Error',
                  'Error while copying blocs',
                );
                this.disableSelectionMode();
              },
            });
        }
        this.disableSelectionMode();
      },
    });
  }

  selectionModeMove(): void {
    let modal = this.dialogService.open(ToDateModalComponent, {
      header: 'Move selected to',
      modal: true,
      closable: true,
      focusOnShow: false,
      dismissableMask: true,
    });

    modal.onClose.subscribe({
      next: (date: Date | null) => {
        if (date) {
          let _date: string = this.utilsService.Iso8601ToStr(date); //To not call everytime the fn
          this.selectedBlocs.forEach((bloc: Bloc) => {
            this.apiService
              .putBloc(bloc.id, { ...bloc, cdate: _date })
              .subscribe({
                error: () => {
                  this.utilsService.toast(
                    'error',
                    'Error',
                    'Error while moving blocs',
                  );
                  this.disableSelectionMode();
                },
                complete: () => {
                  this.displayedBlocInteraction('edit', bloc);
                },
              });
          });
        }
        this.disableSelectionMode();
      },
    });
  }

  selectionModeDelete(): void {
    let modal = this.dialogService.open(YesNoModalComponent, {
      header: 'Confirm',
      modal: true,
      closable: true,
      focusOnShow: false,
      dismissableMask: true,
      breakpoints: {
        '640px': '90vw',
      },
      data: `Delete ${this.selectedBlocs.length} bloc${this.selectedBlocs.length ? 's' : ''} ?`,
    });

    modal.onClose.subscribe({
      next: (bool: boolean | null) => {
        if (bool) {
          this.selectedBlocs.forEach((bloc: Bloc) => {
            this.apiService.deleteBloc(bloc.id).subscribe({
              error: () => {
                this.utilsService.toast(
                  'error',
                  'Error',
                  'Error while deleting blocs',
                );
                this.disableSelectionMode();
              },
              complete: () => {
                this.displayedBlocInteraction('delete', bloc);
              },
            });
          });
        }
        this.disableSelectionMode();
      },
    });
  }

  enableSelectionMode(): void {
    this.selectionMode = true;
  }

  disableSelectionMode(): void {
    this.selectionMode = false;
    this.selectedBlocs = [];
    this.selectedBlocsID = [];
  }

  blocDrop(event: CdkDragDrop<Bloc[]>, newDate: Date) {
    if (event.previousContainer !== event.container) {
      transferArrayItem(
        event.previousContainer.data,
        event.container.data,
        event.previousIndex,
        event.currentIndex,
      );

      this.apiService
        .putBloc(event.item.data, {
          cdate: this.dateToStr(newDate),
        })
        .subscribe({
          next: (bloc) => this.displayedBlocInteraction('move', bloc),
        });
    }
  }
}
