import { Component } from '@angular/core';
import { FormControl, ReactiveFormsModule } from '@angular/forms';
import { ButtonModule } from 'primeng/button';
import { InputTextModule } from 'primeng/inputtext';
import { TabsModule } from 'primeng/tabs';
import { DynamicDialogRef } from 'primeng/dynamicdialog';

@Component({
  selector: 'app-healthwatch-upload-modal',
  imports: [ButtonModule, ReactiveFormsModule, TabsModule, InputTextModule],
  standalone: true,
  templateUrl: './healthwatch-upload-modal.component.html',
  styleUrl: './healthwatch-upload-modal.component.scss',
})
export class HealthwatchUploadModalComponent {
  linkInput = new FormControl('');
  selectedTab = 'whoop';

  constructor(private ref: DynamicDialogRef) {}

  onUploadFileSelected(e: Event): void {
    const target = e.target as HTMLInputElement;
    const files = target.files as FileList;

    if (files[0]) {
      const reader = new FileReader();

      reader.onloadend = () => {
        const formData: FormData = new FormData();
        formData.append('file', files[0]);
        this.close(formData);
      };
      reader.readAsText(files[0]);
    }
  }

  linkConfirm() {
    if (this.linkInput.value) {
      const formData: FormData = new FormData();
      formData.append('link', this.linkInput.value);
      this.close(formData);
    }
  }

  close(data: FormData) {
    this.ref.close({ tab: this.selectedTab, fd: data });
  }
}
