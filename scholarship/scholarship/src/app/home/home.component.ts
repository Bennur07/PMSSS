import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule, ActivatedRoute } from '@angular/router';
import { HttpClient, HttpClientModule } from '@angular/common/http';
import { forkJoin, map, Observable, of, shareReplay, Subscription, switchMap } from 'rxjs';
import { AuthService } from '../auth/auth-service.service';
import { ScholarshipService, Scholarship } from '../services/scholarship.service';

@Component({
  selector: 'app-home',
  standalone: true,
  imports: [CommonModule, RouterModule, HttpClientModule],
  templateUrl: './home.component.html',
  styleUrls: ['./home.component.css']
})
export class HomeComponent implements OnInit, OnDestroy {
  scholarships: Scholarship[] = [];
  filteredScholarships: Scholarship[] = [];
  categories: string[] = ['All', 'Undergraduate', 'Graduate', 'International', 'Merit-based', 'Need-based'];
  selectedCategory: string = 'All';
  userName: string = 'User';
  private fragmentSubscription: Subscription | undefined;
  private userSubscription: Subscription | undefined;
  private hasAppliedCache: { [scholarshipId: string]: Observable<boolean> } = {};
  hasAppliedStatuses: { [scholarshipId: string]: boolean } = {};

  constructor(
    private route: ActivatedRoute,
    private authService: AuthService,
    private scholarshipService: ScholarshipService,
    private http: HttpClient
  ) {}

  ngOnInit(): void {
    this.userSubscription = this.authService.user$.subscribe(user => {
      this.userName = user?.displayName || 'User';
      this.loadScholarshipsAndApplications(user?.uid);
    });

    this.fragmentSubscription = this.route.fragment.subscribe(fragment => {
      if (fragment) {
        setTimeout(() => this.scrollToSection(fragment), 0);
      }
    });
  }

  private loadScholarshipsAndApplications(userId: string | undefined): void {
    this.scholarshipService.getScholarships().subscribe({
      next: (scholarships: any) => {
        this.scholarships = scholarships;
        this.filteredScholarships = [...this.scholarships];
        if (userId) {
          this.preloadHasAppliedStatuses(userId);
        } else {
          this.scholarships.forEach(scholarship => {
            this.hasAppliedStatuses[scholarship.id] = false;
          });
        }
      },
      error: (error: any) => {
        console.error('Failed to load scholarships:', error);
        alert('Could not load scholarships. Please try again later.');
      }
    });
  }

  private preloadHasAppliedStatuses(userId: string): void {
    const requests = this.scholarships.map(scholarship =>
      this.http.get<{ hasApplied: boolean }>(
        `https://astute-catcher-456320-g9.el.r.appspot.com/api/applications/user/${userId}/scholarship/${scholarship.id}`
      ).pipe(
        map(response => ({ scholarshipId: scholarship.id, hasApplied: response.hasApplied })),
        shareReplay(1)
      )
    );

    forkJoin(requests).subscribe({
      next: (results) => {
        results.forEach(result => {
          this.hasAppliedStatuses[result.scholarshipId] = result.hasApplied;
          this.hasAppliedCache[result.scholarshipId] = of(result.hasApplied);
        });
      },
      error: (error:any) => {
        console.error('Failed to preload hasApplied statuses:', error);
        this.scholarships.forEach(scholarship => {
          this.hasAppliedStatuses[scholarship.id] = false;
          this.hasAppliedCache[scholarship.id] = of(false);
        });
      }
    });
  }

  scrollTo(fragment: string): void {
    const element = document.getElementById(fragment);
    if (element) {
      element.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  }

  ngOnDestroy(): void {
    if (this.fragmentSubscription) {
      this.fragmentSubscription.unsubscribe();
    }
    if (this.userSubscription) {
      this.userSubscription.unsubscribe();
    }
  }

  filterByCategory(category: string): void {
    this.selectedCategory = category;
    if (category === 'All') {
      this.filteredScholarships = [...this.scholarships];
    } else {
      this.filteredScholarships = this.scholarships.filter(
        scholarship => scholarship.category === category
      );
    }
  }

  hasApplied(scholarshipId: string): Observable<boolean> {
    return this.authService.user$.pipe(
      switchMap(user => {
        if (!user?.uid) {
          return of(false);
        }
        return this.http.get<{ hasApplied: boolean }>(
          `https://astute-catcher-456320-g9.el.r.appspot.com/api/applications/user/${user.uid}/scholarship/${scholarshipId}`
        ).pipe(map(response => response.hasApplied));
      })
    );
  }

  private scrollToSection(fragment: string): void {
    const element = document.getElementById(fragment);
    if (element) {
      element.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  }

  logout(): void {
    this.authService.signOut().catch(error => {
      console.error('Logout error:', error);
      alert('Failed to log out. Please try again.');
    });
  }
}