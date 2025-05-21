import { Injectable } from '@angular/core';
import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Observable, throwError } from 'rxjs';
import { catchError, map } from 'rxjs/operators';

export interface Scholarship {
  id: string;
  title: string;
  provider: string;
  amount: string;
  deadline: string;
  category: string;
  description: string;
  age_range: string;
  income_range: string;
  created_at?: string;
  required_documents?: string[];
}

export interface Application {
  id: string;
  scholarship_id: string;
  student_name: string;
  student_email: string;
  status: string;
  submitted_at: string;
  documents: {
    name: string;
    url: string;
  }[];
}

@Injectable({
  providedIn: 'root'
})
export class ScholarshipService {
  private apiUrl = 'https://astute-catcher-456320-g9.el.r.appspot.com/api/scholarships';

  constructor(private http: HttpClient) {}

  addScholarship(scholarship: Omit<Scholarship, 'id' | 'created_at'>): Observable<Scholarship> {
    return this.http.post<Scholarship>(this.apiUrl, scholarship).pipe(
      catchError(this.handleError)
    );
  }

  getScholarships(): Observable<Scholarship[]> {
    return this.http.get<Scholarship[]>(this.apiUrl).pipe(
      catchError(this.handleError)
    );
  }

  getScholarship(id: string): Observable<Scholarship> {
    return this.http.get<Scholarship>(`${this.apiUrl}/${id}`).pipe(
      catchError(this.handleError)
    );
  }

  updateScholarship(id: string, scholarship: Scholarship): Observable<Scholarship> {
    return this.http.put<Scholarship>(`${this.apiUrl}/scholarships/${id}`, scholarship);
  }

  deleteScholarship(id: string): Observable<any> {
    return this.http.delete(`${this.apiUrl}/scholarships/${id}`);
  }

  private handleError(error: HttpErrorResponse): Observable<never> {
    let errorMessage = 'An unknown error occurred!';
    if (error.error instanceof ErrorEvent) {
      errorMessage = `Error: ${error.error.message}`;
    } else {
      errorMessage = `Error Code: ${error.status}\nMessage: ${error.error.error || error.message}`;
    }
    console.error(errorMessage);
    return throwError(() => new Error(errorMessage));
  }

  getApplications(): Observable<Application[]> {
    return this.http.get<Application[]>(`${this.apiUrl}/applications`);
  }

  getApplicationsByScholarship(scholarshipId: string): Observable<Application[]> {
    return this.http.get<Application[]>(`${this.apiUrl}/applications/scholarship/${scholarshipId}`);
  }

  updateApplicationStatus(id: string, status: string): Observable<any> {
    return this.http.put(`${this.apiUrl}/applications/${id}`, { status });
  }
}