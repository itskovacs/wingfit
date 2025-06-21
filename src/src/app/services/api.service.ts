import { Injectable } from '@angular/core';
import { UtilsService } from './utils.service';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Bloc, BlocCategory, BlocResult, StashBloc } from '../types/bloc';
import { BehaviorSubject, map, Observable, shareReplay, tap } from 'rxjs';
import { PR, PRvalue } from '../types/personal-record';
import { Program, ProgramBloc, ProgramStep } from '../types/program';
import { User } from '../types/user';
import { Info } from '../types/info';
import {
  BlocsByCategory,
  WeeklyDuration,
  HealthWatchData,
  WeeklyDurationTotal,
} from '../types/stats';

@Injectable({
  providedIn: 'root',
})
export class ApiService {
  public apiBaseUrl: string = '/api';
  public assetsBaseUrl: string = '/api/assets';

  private categoriesSubject = new BehaviorSubject<BlocCategory[] | null>(null);
  public categories$: Observable<BlocCategory[] | null> =
    this.categoriesSubject.asObservable();

  constructor(
    private httpClient: HttpClient,
    private utilsService: UtilsService,
  ) {}

  getInfo(): Observable<Info> {
    return this.httpClient.get<Info>(this.apiBaseUrl + '/info');
  }

  // User endpoints
  getSettings(): Observable<User> {
    return this.httpClient.get<User>(this.apiBaseUrl + '/settings');
  }

  enableAccessToken(): Observable<string> {
    return this.httpClient.put<string>(
      this.apiBaseUrl + '/settings/api_token',
      {},
    );
  }

  disableAccessToken(): Observable<{}> {
    return this.httpClient.delete<{}>(this.apiBaseUrl + '/settings/api_token');
  }

  enableMFA(): Observable<{ secret: string }> {
    return this.httpClient.post<{ secret: string }>(
      this.apiBaseUrl + '/settings/mfa/enable',
      {},
    );
  }

  verifyMFA(code: string): Observable<any> {
    return this.httpClient.post<any>(this.apiBaseUrl + '/settings/mfa/verify', {
      code,
    });
  }

  disableMFA(code: string): Observable<{}> {
    return this.httpClient.post<{}>(this.apiBaseUrl + '/settings/mfa/disable', {
      code,
    });
  }

  checkVersion(): Observable<string> {
    return this.httpClient.get<string>(
      this.apiBaseUrl + '/settings/checkversion',
    );
  }

  exportData(code: string): Observable<any> {
    return this.httpClient.put<any>(this.apiBaseUrl + '/settings/export', {
      code: code,
    });
  }

  // Category endpoints
  getCategories(): Observable<BlocCategory[]> {
    if (!this.categoriesSubject.value) {
      return this.httpClient
        .get<BlocCategory[]>(this.apiBaseUrl + '/categories')
        .pipe(
          map((categories) =>
            categories.sort(
              (categoryA: BlocCategory, categoryB: BlocCategory) =>
                (categoryA.weight || 99) - (categoryB.weight || 99),
            ),
          ),
          tap((categories) => this.categoriesSubject.next(categories)),
          shareReplay(1),
        );
    }
    return this.categories$ as Observable<BlocCategory[]>;
  }

  getCategoryBlocsCount(category_id: number): Observable<number> {
    return this.httpClient.get<number>(
      this.apiBaseUrl + `/categories/${category_id}/count`,
    );
  }

  postCategory(category: BlocCategory): Observable<BlocCategory> {
    return this.httpClient
      .post<BlocCategory>(this.apiBaseUrl + '/categories', category)
      .pipe(
        tap((category) => {
          let categories = this.categoriesSubject.value || [];
          categories.push(category);
          this.categoriesSubject.next(
            categories.sort(
              (categoryA: BlocCategory, categoryB: BlocCategory) =>
                (categoryA.weight || 99) - (categoryB.weight || 99),
            ),
          );
        }),
      );
  }

  putCategory(
    category_id: number,
    category: Partial<BlocCategory>,
  ): Observable<BlocCategory> {
    return this.httpClient
      .put<BlocCategory>(
        this.apiBaseUrl + `/categories/${category_id}`,
        category,
      )
      .pipe(
        tap((category) => {
          let categories = this.categoriesSubject.value || [];
          let categoryIndex =
            categories?.findIndex((c) => c.id == category_id) || -1;
          if (categoryIndex > -1) {
            categories[categoryIndex] = category;
            this.categoriesSubject.next(
              categories.sort(
                (categoryA: BlocCategory, categoryB: BlocCategory) =>
                  (categoryA.weight || 99) - (categoryB.weight || 99),
              ),
            );
          }
        }),
      );
  }

  deleteCategory(category_id: number): Observable<{}> {
    return this.httpClient
      .delete<{}>(this.apiBaseUrl + `/categories/${category_id}`)
      .pipe(
        tap((_) => {
          let categories = this.categoriesSubject.value || [];
          let categoryIndex =
            categories?.findIndex((c) => c.id == category_id) || -1;
          if (categoryIndex > -1) {
            categories.splice(categoryIndex, 1);
            this.categoriesSubject.next(
              categories.sort(
                (categoryA: BlocCategory, categoryB: BlocCategory) =>
                  (categoryA.weight || 99) - (categoryB.weight || 99),
              ),
            );
          }
        }),
      );
  }

  // Stash endpoints
  getStash(): Observable<StashBloc[]> {
    return this.httpClient.get<StashBloc[]>(this.apiBaseUrl + '/stash');
  }

  removeAllStash(): Observable<{}> {
    return this.httpClient.delete<{}>(this.apiBaseUrl + '/stash');
  }

  deleteStash(stash_id: number): Observable<{}> {
    return this.httpClient.delete<{}>(this.apiBaseUrl + `/stash/${stash_id}`);
  }
  // Blocs endpoints
  getBlocs(
    startDate?: Date,
    endDate?: Date,
    limit?: number,
    offset?: number,
  ): Observable<Bloc[]> {
    //TODO: Mettre un genre de *kwargs et params.set(x, *kwargs[x])
    let params = new HttpParams();
    if (startDate)
      params = params.set(
        'startdate',
        this.utilsService.Iso8601ToStr(startDate),
      );
    if (endDate)
      params = params.set('enddate', this.utilsService.Iso8601ToStr(endDate));
    if (limit) params = params.set('limit', limit);
    if (offset) params = params.set('offset', offset);

    return this.httpClient.get<Bloc[]>(this.apiBaseUrl + '/blocs', { params });
  }

  postBloc(bloc: Bloc): Observable<Bloc> {
    return this.httpClient.post<Bloc>(this.apiBaseUrl + '/blocs', bloc);
  }

  postBlocs(blocs: Bloc[]): Observable<Bloc[]> {
    return this.httpClient.post<Bloc[]>(this.apiBaseUrl + '/blocs', blocs);
  }

  putBloc(bloc_id: number, bloc: Partial<Bloc>): Observable<Bloc> {
    return this.httpClient.put<Bloc>(
      this.apiBaseUrl + `/blocs/${bloc_id}`,
      bloc,
    );
  }

  deleteBloc(bloc_id: number): Observable<{}> {
    return this.httpClient.delete<{}>(this.apiBaseUrl + `/blocs/${bloc_id}`);
  }

  // Bloc result endpoints
  putBlocResult(bloc_id: number, result: BlocResult): Observable<BlocResult> {
    return this.httpClient.put<BlocResult>(
      this.apiBaseUrl + `/blocs/${bloc_id}/result`,
      result,
    );
  }

  deleteBlocResult(bloc_id: number): Observable<{}> {
    return this.httpClient.delete<{}>(
      this.apiBaseUrl + `/blocs/${bloc_id}/result`,
    );
  }

  // PR endpoints
  getPR(): Observable<PR[]> {
    return this.httpClient.get<PR[]>(this.apiBaseUrl + '/pr');
  }

  postPR(pr: PR): Observable<PR> {
    return this.httpClient.post<PR>(this.apiBaseUrl + '/pr', pr);
  }

  putPR(pr_id: number, pr: Partial<PR>): Observable<PR> {
    return this.httpClient.put<PR>(this.apiBaseUrl + `/pr/${pr_id}`, pr);
  }

  deletePR(pr_id: number): Observable<{}> {
    return this.httpClient.delete<{}>(this.apiBaseUrl + `/pr/${pr_id}`);
  }

  postPRvalues(pr_id: number, prvalues: PRvalue[]): Observable<PRvalue[]> {
    //Backend accepts PRvalue or a list of PRvalue, so we send by default a list it's easier for frontend
    return this.httpClient.post<PRvalue[]>(
      this.apiBaseUrl + `/pr/${pr_id}/values`,
      prvalues,
    );
  }

  putPRValue(pr_id: number, value: PRvalue): Observable<PRvalue> {
    return this.httpClient.put<PRvalue>(
      this.apiBaseUrl + `/pr/${pr_id}/value/${value.id}`,
      value,
    );
  }

  deletePRValue(pr_id: number, value_id: number): Observable<{}> {
    return this.httpClient.delete<{}>(
      this.apiBaseUrl + `/pr/${pr_id}/value/${value_id}`,
    );
  }

  // Programs endpoints
  getPrograms(): Observable<Program[]> {
    return this.httpClient.get<Program[]>(this.apiBaseUrl + '/programs').pipe(
      map((programs) =>
        programs.map((program) => {
          return {
            ...program,
            image: program.image
              ? `${this.assetsBaseUrl}/${program.image}`
              : '',
          };
        }),
      ),
    );
  }

  postProgram(program: Program): Observable<Program> {
    return this.httpClient
      .post<Program>(this.apiBaseUrl + '/programs', program)
      .pipe(
        map((program) => {
          return {
            ...program,
            image: program.image
              ? `${this.assetsBaseUrl}/${program.image}`
              : '',
          };
        }),
      );
  }

  exportProgram(p_id: number): Observable<any> {
    return this.httpClient.get<any>(
      this.apiBaseUrl + `/programs/${p_id}/export`,
    );
  }

  uploadProgram(data: FormData): Observable<Program> {
    return this.httpClient
      .post<Program>(this.apiBaseUrl + '/programs/upload', data, {
        headers: { enctype: 'multipart/form-data' },
      })
      .pipe(
        map((program) => {
          return {
            ...program,
            image: program.image
              ? `${this.assetsBaseUrl}/${program.image}`
              : '',
          };
        }),
      );
  }

  putProgram(
    program_id: number,
    program: Partial<Program>,
  ): Observable<Program> {
    return this.httpClient.put<Program>(
      this.apiBaseUrl + `/programs/${program_id}`,
      program,
    );
  }

  deleteProgram(program_id: number): Observable<{}> {
    return this.httpClient.delete<{}>(
      this.apiBaseUrl + `/programs/${program_id}`,
    );
  }

  // Program endpoints
  getProgram(program_id: number): Observable<Program> {
    return this.httpClient.get<Program>(
      this.apiBaseUrl + `/programs/${program_id}`,
    );
  }

  // Program Step endpoints
  postProgramStep(
    program_id: number,
    step: ProgramStep,
  ): Observable<ProgramStep> {
    return this.httpClient.post<ProgramStep>(
      this.apiBaseUrl + `/programs/${program_id}/steps`,
      step,
    );
  }

  putProgramStep(
    program_id: number,
    step_id: number,
    step: Partial<ProgramStep>,
  ): Observable<ProgramStep> {
    return this.httpClient.put<ProgramStep>(
      this.apiBaseUrl + `/programs/${program_id}/steps/${step_id}`,
      step,
    );
  }

  deleteProgramStep(program_id: number, step_id: number): Observable<{}> {
    return this.httpClient.delete<{}>(
      this.apiBaseUrl + `/programs/${program_id}/steps/${step_id}`,
    );
  }

  // Program Step Blocs endpoints
  postProgramStepBloc(
    program_id: number,
    step_id: number,
    bloc: ProgramBloc,
  ): Observable<ProgramBloc> {
    return this.httpClient.post<ProgramBloc>(
      this.apiBaseUrl + `/programs/${program_id}/steps/${step_id}/blocs`,
      bloc,
    );
  }

  putProgramStepBloc(
    program_id: number,
    step_id: number,
    bloc_id: number,
    bloc: Partial<ProgramBloc>,
  ): Observable<ProgramBloc> {
    return this.httpClient.put<ProgramBloc>(
      this.apiBaseUrl +
        `/programs/${program_id}/steps/${step_id}/blocs/${bloc_id}`,
      bloc,
    );
  }

  deleteProgramStepBloc(
    program_id: number,
    step_id: number,
    bloc_id: number,
  ): Observable<{}> {
    return this.httpClient.delete<{}>(
      this.apiBaseUrl +
        `/programs/${program_id}/steps/${step_id}/blocs/${bloc_id}`,
    );
  }

  updatePassword(current: string, _new: string): Observable<{}> {
    return this.httpClient.post<{}>(this.apiBaseUrl + `/auth/update_password`, {
      current: current,
      new: _new,
    });
  }

  // Admin P endpoints
  getUsers(): Observable<User[]> {
    return this.httpClient.get<User[]>(this.apiBaseUrl + '/admin/users');
  }

  adminExportData(code: string): Observable<any> {
    return this.httpClient.put<any>(this.apiBaseUrl + '/admin/export', {
      code: code,
    });
  }

  adminRestoreData(data: FormData): Observable<Program> {
    return this.httpClient.put<Program>(
      this.apiBaseUrl + '/admin/import',
      data,
      {
        headers: { enctype: 'multipart/form-data' },
      },
    );
  }

  deleteUser(username: string, code: string): Observable<{}> {
    return this.httpClient.put(
      this.apiBaseUrl + `/admin/users/${username}/delete`,
      {
        code: code,
      },
    );
  }

  adminResetMFA(username: string, code: string): Observable<User> {
    return this.httpClient.put<User>(
      this.apiBaseUrl + `/admin/users/${username}/reset_mfa`,
      {
        code: code,
      },
    );
  }

  addUser(data: {
    username: string;
    password: string;
    code: string;
  }): Observable<User> {
    return this.httpClient.post<User>(this.apiBaseUrl + '/admin/users', data);
  }

  resetUserPassword(
    username: string,
    _new: string,
    code: string,
  ): Observable<{}> {
    return this.httpClient.put(
      this.apiBaseUrl + `/admin/users/${username}/reset`,
      {
        new: _new,
        code: code,
      },
    );
  }

  toggleUserActive(username: string, code: string): Observable<User> {
    return this.httpClient.put<User>(
      this.apiBaseUrl + `/admin/users/${username}/toggle_active`,
      { code: code },
    );
  }

  // Stats endpoints
  getNoteBlocs(): Observable<Bloc[]> {
    return this.httpClient.get<Bloc[]>(this.apiBaseUrl + '/stats/notes');
  }

  getWeeklyDurationTotal(year: number): Observable<WeeklyDurationTotal[]> {
    let params = new HttpParams();
    params = params.set('year', year);

    return this.httpClient.get<WeeklyDurationTotal[]>(
      this.apiBaseUrl + '/stats/week_duration_total',
      { params },
    );
  }

  getWeeklyDuration(year: number): Observable<WeeklyDuration[]> {
    let params = new HttpParams();
    params = params.set('year', year);

    return this.httpClient.get<WeeklyDuration[]>(
      this.apiBaseUrl + '/stats/week_duration',
      { params },
    );
  }

  getHealthWatchData(year: number): Observable<HealthWatchData[]> {
    let params = new HttpParams();
    params = params.set('year', year);

    return this.httpClient.get<HealthWatchData[]>(
      this.apiBaseUrl + '/stats/healthwatch',
      { params },
    );
  }

  postWhoopData(data: FormData): Observable<{ count: number }> {
    // data is either a link:str or file: File
    return this.httpClient.post<{ count: number }>(
      this.apiBaseUrl + '/stats/whoop_archive',
      data,
      { headers: { enctype: 'multipart/form-data' } },
    );
  }

  postAppleWatchData(data: FormData): Observable<{ count: number }> {
    // data is file: File
    return this.httpClient.post<{ count: number }>(
      this.apiBaseUrl + '/stats/applewatch_archive',
      data,
      { headers: { enctype: 'multipart/form-data' } },
    );
  }
}
