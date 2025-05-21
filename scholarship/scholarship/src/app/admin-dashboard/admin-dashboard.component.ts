import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ReactiveFormsModule, FormBuilder, FormGroup, Validators, FormArray } from '@angular/forms';
import { HttpClient, HttpClientModule } from '@angular/common/http';
import { Observable } from 'rxjs';

interface Scholarship {
  id: string;
  title: string;
  provider: string;
  amount: string;
  deadline: string;
  category: string;
  description: string;
  age_range: string;
  income_range: string;
  required_documents: string[];
  created_at?: string;
}

interface Application {
  id: string;
  scholarship_id: string;
  user_id: string;
  student_name: string;
  student_email: string;
  status: string;
  submitted_at: string;
  bank_account_number: string,  
  ifsc_code: string,  
  bank_name: string, 
  documents: { name: string; file_id: string }[];
  verification_result: { documentValid: boolean; reasonForRejection: string[] };
  remarks: string[];
  payment_status?: string;
  payment_date?: string;
  payment_reference?: string;
}

@Component({
  selector: 'app-admin-dashboard',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, HttpClientModule],
  templateUrl: './admin-dashboard.component.html',
  styleUrls: ['./admin-dashboard.component.css']
})
export class AdminDashboardComponent implements OnInit {
  activeTab = 'scholarships';
  scholarshipForm!: FormGroup;
  scholarships: Scholarship[] = [];
  applications: Application[] = [];
  approvedApplications: Application[] = [];
  selectedScholarship: Scholarship | null = null;
  scholarshipApplications: Application[] = [];
  categories = ['Undergraduate', 'Graduate', 'International', 'Merit-based', 'Need-based'];
  isEditMode = false;
  editingScholarshipId: string | null = null;
  showPaymentModal: boolean = false;
  selectedApplication: Application | null = null;

  constructor(
    private fb: FormBuilder,
    private http: HttpClient
  ) {
    this.scholarshipForm = this.fb.group({
      title: ['', Validators.required],
      provider: ['', Validators.required],
      amount: ['', Validators.required],
      deadline: ['', Validators.required],
      category: ['', Validators.required],
      description: ['', Validators.required],
      age_range: [''],
      income_range: [''],
      required_documents: this.fb.array([])
    });
  }

  ngOnInit(): void {
    this.loadScholarships();
    this.loadAllApplications();
    this.loadApprovedApplications();
  }

  get requiredDocuments(): FormArray {
    return this.scholarshipForm.get('required_documents') as FormArray;
  }

  addDocument(): void {
    this.requiredDocuments.push(this.fb.control('', Validators.required));
  }

  removeDocument(index: number): void {
    this.requiredDocuments.removeAt(index);
  }

  loadScholarships(): void {
    this.http.get<Scholarship[]>('https://astute-catcher-456320-g9.el.r.appspot.com/api/scholarships')
      .subscribe({
        next: (data) => {
          this.scholarships = data;
        },
        error: (err) => {
          console.error('Error loading scholarships:', err);
        }
      });
  }

  loadAllApplications(): void {
    this.http.get<Application[]>('https://astute-catcher-456320-g9.el.r.appspot.com/api/applications')
      .subscribe({
        next: (data) => {
          this.applications = data;
        },
        error: (err) => {
          console.error('Error loading applications:', err);
          this.applications = [];
        }
      });
  }

  loadApprovedApplications(): void {
    this.http.get<Application[]>('https://astute-catcher-456320-g9.el.r.appspot.com/api/applications')
      .subscribe({
        next: (data) => {
          this.approvedApplications = data.filter(app => app.status === 'approved');
        },
        error: (err) => {
          console.error('Error loading applications for finance tab:', err);
          this.approvedApplications = [];
          alert('Failed to load approved applications. Please try again later.');
        }
      });
  }

  getScholarshipTitle(scholarshipId: string): string {
    const scholarship = this.scholarships.find(s => s.id === scholarshipId);
    return scholarship ? scholarship.title : 'Unknown';
  }

  getScholarshipAmount(scholarshipId: string): string {
    const scholarship = this.scholarships.find(s => s.id === scholarshipId);
    return scholarship ? scholarship.amount : 'Unknown';
  }

  submitScholarship(): void {
    if (this.scholarshipForm.invalid) {
      this.markFormGroupTouched(this.scholarshipForm);
      return;
    }

    const scholarshipData: Scholarship = {
      ...this.scholarshipForm.value
    };

    let request: Observable<any>;
    if (this.isEditMode && this.editingScholarshipId) {
      request = this.http.put(
        `https://astute-catcher-456320-g9.el.r.appspot.com/api/scholarships/${this.editingScholarshipId}`,
        scholarshipData
      );
    } else {
      request = this.http.post(
        'https://astute-catcher-456320-g9.el.r.appspot.com/api/scholarships',
        scholarshipData
      );
    }

    request.subscribe({
      next: () => {
        this.loadScholarships();
        this.resetForm();
        this.activeTab = 'scholarships';
      },
      error: (err) => {
        console.error('Error saving scholarship:', err);
      }
    });
  }

  onStatusChange(event: Event, application: Application): void {
    const status = (event.target as HTMLSelectElement).value;
    this.updateApplicationStatus(application, status);
  }

  resetForm(): void {
    this.scholarshipForm.reset();
    this.requiredDocuments.clear();
    this.isEditMode = false;
    this.editingScholarshipId = null;
  }

  editScholarship(scholarship: Scholarship): void {
    this.isEditMode = true;
    this.editingScholarshipId = scholarship.id;
    while (this.requiredDocuments.length) {
      this.requiredDocuments.removeAt(0);
    }
    if (scholarship.required_documents && scholarship.required_documents.length) {
      scholarship.required_documents.forEach(doc => {
        this.requiredDocuments.push(this.fb.control(doc, Validators.required));
      });
    }
    this.scholarshipForm.patchValue({
      title: scholarship.title,
      provider: scholarship.provider,
      amount: scholarship.amount,
      deadline: scholarship.deadline,
      category: scholarship.category,
      description: scholarship.description,
      age_range: scholarship.age_range || '',
      income_range: scholarship.income_range || ''
    });
    this.activeTab = 'add-scholarship';
  }

  deleteScholarship(id: string): void {
    if (confirm('Are you sure you want to delete this scholarship?')) {
      this.http.delete(`https://astute-catcher-456320-g9.el.r.appspot.com/api/scholarships/${id}`)
        .subscribe({
          next: () => {
            this.loadScholarships();
          },
          error: (err) => {
            console.error('Error deleting scholarship:', err);
          }
        });
    }
  }

  viewApplications(scholarship: Scholarship): void {
    this.selectedScholarship = scholarship;
    this.http.get<Application[]>(`https://astute-catcher-456320-g9.el.r.appspot.com/api/applications/scholarship/${scholarship.id}`)
      .subscribe({
        next: (data) => {
          this.scholarshipApplications = data;
          this.activeTab = 'applications-detail';
        },
        error: (err) => {
          console.error('Error loading scholarship applications:', err);
          this.scholarshipApplications = [];
          this.activeTab = 'applications-detail';
        }
      });
  }

  updateApplicationStatus(application: Application, status: string): void {
    let updateData: { status: string; remarks?: string[] } = { status };
    if (status === 'Rejected') {
      const remarksInput = prompt('Enter rejection reasons (one per line):');
      if (remarksInput) {
        updateData.remarks = remarksInput.split('\n').filter(r => r.trim());
      }
    }

    this.http.put(`https://astute-catcher-456320-g9.el.r.appspot.com/api/applications/${application.id}`, updateData)
      .subscribe({
        next: () => {
          application.status = status;
          if (updateData.remarks) {
            application.remarks = updateData.remarks;
          }
          console.log('Application status updated');
          this.loadAllApplications();
          this.loadApprovedApplications();
          if (this.activeTab === 'applications-detail' && this.selectedScholarship) {
            this.viewApplications(this.selectedScholarship);
          }
        },
        error: (err) => {
          console.error('Error updating application status:', err);
        }
      });
  }

  makePayment(application: Application): void {
    this.selectedApplication = application;
    this.showPaymentModal = true;
  }

  viewDocument(fileId: string): void {
    this.http.get(`https://astute-catcher-456320-g9.el.r.appspot.com/api/documents/${fileId}`, { responseType: 'blob' })
      .subscribe({
        next: (blob) => {
          const url = window.URL.createObjectURL(blob);
          const a = document.createElement('a');
          a.href = url;
          a.download = `document-${fileId}.pdf`; 
          document.body.appendChild(a);
          a.click();
          document.body.removeChild(a);
          window.URL.revokeObjectURL(url);
          console.log(`Document download initiated for file_id: ${fileId}`);
        },
        error: (err) => {
          console.error('Error downloading document:', err);
          alert('Failed to download document: ' + (err.error?.error || 'Unknown error'));
        }
      });
  }

  backToScholarships(): void {
    this.activeTab = 'scholarships';
    this.selectedScholarship = null;
    this.scholarshipApplications = [];
  }

  closePaymentModal(): void {
    this.showPaymentModal = false;
    this.selectedApplication = null;
  }

  confirmPayment(): void {
    if (!this.selectedApplication) return;
  
    const paymentData = {
      status: 'approved',
      payment_info: {
        payment_status: 'completed',
        payment_date: new Date().toISOString(),
        payment_reference: `PAY-${new Date().getFullYear()}-${Math.floor(Math.random() * 1000).toString().padStart(3, '0')}`
      }
    };
  
    this.http.put(`https://astute-catcher-456320-g9.el.r.appspot.com/api/applications/${this.selectedApplication.id}`, paymentData)
      .subscribe({
        next: (updatedApp: any) => {
          if (this.selectedApplication && updatedApp.payment_info) {
            this.selectedApplication.status = updatedApp.status;
            this.selectedApplication.payment_status = updatedApp.payment_info.payment_status;
            this.selectedApplication.payment_date = updatedApp.payment_info.payment_date;
            this.selectedApplication.payment_reference = updatedApp.payment_info.payment_reference;
          }
          console.log('Payment processed successfully');
          this.loadApprovedApplications();
          this.closePaymentModal();
        },
        error: (err) => {
          console.error('Error processing payment:', err);
          alert('Failed to process payment: ' + (err.error?.error || 'Unknown error'));
          this.closePaymentModal();
        }
      });
  }

  changeTab(tab: string): void {
    this.activeTab = tab;
    if (tab === 'scholarships') {
      this.loadScholarships();
    } else if (tab === 'applications') {
      this.loadAllApplications();
    } else if (tab === 'add-scholarship') {
      this.resetForm();
    } else if (tab === 'finance') {
      this.loadApprovedApplications();
    }
  }

  private markFormGroupTouched(formGroup: FormGroup): void {
    Object.keys(formGroup.controls).forEach(key => {
      const control = formGroup.get(key);
      control?.markAsTouched();
    });
  }
}