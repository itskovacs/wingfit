import { Component } from '@angular/core';

import { FloatLabelModule } from 'primeng/floatlabel';
import {
  FormBuilder,
  FormGroup,
  FormsModule,
  ReactiveFormsModule,
  Validators,
} from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { InputTextModule } from 'primeng/inputtext';
import { ButtonModule } from 'primeng/button';
import { FocusTrapModule } from 'primeng/focustrap';
import {
  AuthParams,
  AuthService,
  MFARequired,
  Token,
} from '../../services/auth.service';
import { MessageModule } from 'primeng/message';
import { HttpErrorResponse } from '@angular/common/http';
import { SkeletonModule } from 'primeng/skeleton';
import { InputOtpModule } from 'primeng/inputotp';

@Component({
  selector: 'app-auth',
  standalone: true,
  imports: [
    FloatLabelModule,
    ReactiveFormsModule,
    ButtonModule,
    FormsModule,
    InputTextModule,
    FocusTrapModule,
    SkeletonModule,
    MessageModule,
    InputOtpModule,
  ],
  templateUrl: './auth.component.html',
  styleUrl: './auth.component.scss',
})
export class AuthComponent {
  private redirectURL: string;
  authParams: AuthParams | undefined;
  authForm: FormGroup;
  error: string = '';
  isRegistering: boolean = false;

  pendingOTP: string = '';
  otp = '';
  username: string = '';

  constructor(
    private authService: AuthService,
    private router: Router,
    private route: ActivatedRoute,
    private fb: FormBuilder,
  ) {
    this.route.queryParams.subscribe((params) => {
      const code = params['code'];
      if (code) {
        this.authService.verifyCodeOauth(code).subscribe({
          next: (data) => {
            if (!data) return;
            this.router.navigateByUrl(this.redirectURL);
          },
        });
      }
    });

    this.authService.authParams().subscribe({
      next: (params) => (this.authParams = params),
    });

    this.redirectURL =
      this.route.snapshot.queryParams['redirectURL'] || '/home';

    this.authForm = this.fb.group({
      username: [
        '',
        {
          validators: Validators.compose([
            Validators.pattern(/^[a-zA-Z0-9_-]{1,19}$/),
            Validators.required,
          ]),
        },
      ],
      password: ['', { validators: Validators.required }],
    });
  }

  auth_or_register() {
    if (this.isRegistering) this.register();
    else this.authenticate();
  }

  register(): void {
    this.error = '';
    if (this.authForm.valid) {
      this.authService.register(this.authForm.value).subscribe({
        next: () => {
          this.router.navigateByUrl(this.redirectURL);
        },
        error: (err: HttpErrorResponse) => {
          this.authForm.reset();
          this.error = err.error.detail;
        },
      });
    }
  }

  authenticate(): void {
    this.error = '';
    if (this.authParams?.oidc) {
      window.location.replace(encodeURI(this.authParams.oidc));
    }

    this.authService.login(this.authForm.value).subscribe({
      next: (data) => {
        if ((data as Token)?.access_token)
          this.router.navigateByUrl(this.redirectURL);

        // If we're here, it means it's OTP time
        this.username = (data as MFARequired).username;
        this.pendingOTP = (data as MFARequired).pending_code;
        this.authForm.reset();
      },
      error: () => {
        this.authForm.reset();
      },
    });
  }

  verifyMFA(): void {
    this.error = '';
    this.authService
      .verify_mfa(this.username, this.pendingOTP, this.otp)
      .subscribe({
        next: (token) => {
          if (token) this.router.navigateByUrl(this.redirectURL);
        },
        error: () => {
          this.otp = '';
          this.pendingOTP = '';
          this.username = '';
        },
      });
  }
}
