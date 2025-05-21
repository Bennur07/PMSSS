import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { HttpClient, HttpClientModule } from '@angular/common/http';
import { AuthService } from '../auth/auth-service.service';
import { Subscription, forkJoin, of } from 'rxjs';
import { switchMap, map, catchError } from 'rxjs/operators';

interface ApplicationStatus {
  status: 'pending' | 'approved' | 'rejected';
  date: string;
  notes?: string;
}

interface ScholarshipApplication {
  id: string;
  title: string;
  provider: string;
  amount: string;
  deadline: string;
  submittedDate: string;
  currentStatus: ApplicationStatus['status'];
  statusHistory: ApplicationStatus[];
  remarks: string[];
}

interface BackendApplication {
  id: string;
  scholarship_id: string;
  user_id: string;
  student_name: string;
  student_email: string;
  status: 'pending' | 'approved' | 'rejected';
  submitted_at: string;
  documents: { name: string; file_id: string }[];
  remarks: string[];
}

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
  created_at: string;
}

@Component({
  selector: 'app-live-status',
  standalone: true,
  imports: [CommonModule, RouterModule, HttpClientModule],
  templateUrl: './live-status.component.html',
  styleUrls: ['./live-status.component.css']
})
export class LiveStatusComponent implements OnInit, OnDestroy {
  applications: ScholarshipApplication[] = [];
  selectedApplication: ScholarshipApplication | null = null;
  showDetailView: boolean = false;
  totalApplications: number = 0;
  awardedCount: number = 0;
  inProgressCount: number = 0;
  userName: string = 'User';
  loading: boolean = true;
  error: string | null = null;
  private userSubscription: Subscription | undefined;

  constructor(
    private authService: AuthService,
    private http: HttpClient
  ) {}

  ngOnInit(): void {
    console.log('LiveStatusComponent: Initializing');
    this.userSubscription = this.authService.user$.pipe(
      switchMap(user => {
        console.log('LiveStatusComponent: User received', user);
        if (!user?.uid) {
          console.warn('LiveStatusComponent: No authenticated user');
          this.loading = false;
          this.error = 'User not authenticated. Please sign in.';
          return [];
        }
        this.userName = user.displayName || 'User';
        this.loading = true;
        this.error = null;
        console.log('LiveStatusComponent: Fetching applications for user', user.uid);
        return this.http.get<BackendApplication[]>(`https://astute-catcher-456320-g9.el.r.appspot.com/api/applications/user/${user.uid}`).pipe(
          switchMap(applications => {
            console.log('LiveStatusComponent: Applications received', applications);
            if (!applications || applications.length === 0) {
              console.log('LiveStatusComponent: No applications found');
              return [[]]; 
            }
            
            const scholarshipRequests = applications.map(app =>
              this.http.get<Scholarship>(`https://astute-catcher-456320-g9.el.r.appspot.com/api/scholarships/${app.scholarship_id}`)
                .pipe(
                  map(scholarship => ({ app, scholarship })),
            
                  catchError(error => {
                    console.error(`LiveStatusComponent: Error fetching scholarship ${app.scholarship_id}`, error);
                    return of({ app, scholarship: null });
                  })
                )
            );
            console.log('LiveStatusComponent: Fetching scholarships', scholarshipRequests.length);
            return forkJoin(scholarshipRequests).pipe(
              map(results => {
                console.log('LiveStatusComponent: Scholarships fetched', results);
                return this.mapToScholarshipApplications(applications, results);
              })
            );
          })
        );
      })
    ).subscribe({
      next: (apps) => {
        console.log('LiveStatusComponent: Applications mapped', apps);
        this.applications = apps;
        this.calculateStatistics();
        this.loading = false;
        this.error = null;
      },
      error: (err) => {
        console.error('LiveStatusComponent: Error in subscription', err);
        this.error = 'Failed to load applications. Please try again later.';
        this.loading = false;
      },
      complete: () => {
        console.log('LiveStatusComponent: Subscription completed');
        this.loading = false;
      }
    });
  }

  private mapToScholarshipApplications(
    backendApps: BackendApplication[],
    results: { app: BackendApplication; scholarship: Scholarship | null }[]
  ): ScholarshipApplication[] {
    return backendApps.map(backendApp => {
      const result = results.find(r => r.app.id === backendApp.id);
      const scholarship = result?.scholarship;
      const currentStatus = backendApp.status;
      let notes: string | undefined;
      switch (currentStatus) {
        case 'pending':
          notes = 'Application submitted successfully';
          break;
        case 'approved':
          notes = 'Your application has been accepted';
          break;
        case 'rejected':
          notes = 'We regret to inform you that your application was not selected';
          break;
      }

      const statusHistory: ApplicationStatus[] = [
        {
          status: 'pending',
          date: new Date(backendApp.submitted_at).toLocaleString('en-US', {
            year: 'numeric',
            month: 'long',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
          }),
          notes: 'Application submitted successfully'
        }
      ];
      if (backendApp.status !== 'pending') {
        statusHistory.push({
          status: currentStatus,
          date: new Date().toLocaleString('en-US', {
            year: 'numeric',
            month: 'long',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
          }),
          notes: backendApp.remarks.length > 0 && currentStatus === 'rejected'
            ? `${notes}. Reasons: ${backendApp.remarks.join('; ')}`
            : notes
        });
      }

      return {
        id: backendApp.id,
        title: scholarship?.title || 'Unknown Scholarship',
        provider: scholarship?.provider || 'Unknown Provider',
        amount: scholarship?.amount || 'N/A',
        deadline: scholarship?.deadline || 'N/A',
        submittedDate: new Date(backendApp.submitted_at).toLocaleDateString('en-US', {
          year: 'numeric',
          month: 'long',
          day: 'numeric'
        }),
        currentStatus,
        statusHistory,
        remarks: backendApp.remarks || []
      };
    });
  }

  withdrawApplication(application: ScholarshipApplication): void {
    if (!confirm('Are you sure you want to withdraw this application? This action cannot be undone.')) {
      return;
    }

    this.http.delete(`https://astute-catcher-456320-g9.el.r.appspot.com/api/applications/${application.id}`).subscribe({
      next: () => {
        console.log(`Application ${application.id} withdrawn successfully`);
        this.applications = this.applications.filter(app => app.id !== application.id);
        this.calculateStatistics();
        if (this.showDetailView && this.selectedApplication?.id === application.id) {
          this.closeDetailView();
        }
        alert('Application withdrawn successfully.');
      },
      error: (error) => {
        console.error('Error withdrawing application:', error);
        alert('Failed to withdraw application: ' + (error.error?.error || 'Unknown error'));
      }
    });
  }

  calculateStatistics(): void {
    this.totalApplications = this.applications.length;
    this.awardedCount = this.applications.filter(app => app.currentStatus === 'approved').length;
    this.inProgressCount = this.applications.filter(
      app => app.currentStatus === 'pending'
    ).length;
  }

  viewApplicationDetails(application: ScholarshipApplication): void {
    this.selectedApplication = application;
    this.showDetailView = true;
  }

  closeDetailView(): void {
    this.showDetailView = false;
    this.selectedApplication = null;
  }

  getStatusClass(status: ApplicationStatus['status']): string {
    switch (status) {
      case 'pending':
        return 'status-pending';
      case 'approved':
        return 'status-accepted';
      case 'rejected':
        return 'status-rejected';
      default:
        return '';
    }
  }

  ngOnDestroy(): void {
    if (this.userSubscription) {
      this.userSubscription.unsubscribe();
    }
  }

  logout(): void {
    this.authService.signOut().catch(error => {
      console.error('Logout error:', error);
      alert('Failed to log out. Please try again.');
    });
  }
}