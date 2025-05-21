import { Injectable, inject } from '@angular/core';
import { Router } from '@angular/router';
import { Observable, of, from } from 'rxjs';
import { switchMap, take, map } from 'rxjs/operators';

import { Auth, User as FirebaseUser, createUserWithEmailAndPassword, signInWithEmailAndPassword, signOut } from '@angular/fire/auth';
import { Firestore, docData, setDoc, doc } from '@angular/fire/firestore';
import { authState } from '@angular/fire/auth';

export interface User {
  uid: string;
  email: string | null;
  displayName?: string;
  role: 'user' | 'admin';
}

@Injectable({
  providedIn: 'root'
})
export class AuthService {
  private auth: Auth = inject(Auth);
  private firestore: Firestore = inject(Firestore);
  private router: Router = inject(Router);

  user$: Observable<User | null> = authState(this.auth).pipe(
    switchMap(firebaseUser => {
      if (firebaseUser) {
        return docData(doc(this.firestore, `users/${firebaseUser.uid}`)) as Observable<User>;
      } else {
        return of(null);
      }
    })
  );

  async signUp(email: string, password: string, displayName: string): Promise<void> {
    try {
      const credential = await createUserWithEmailAndPassword(this.auth, email, password);
      await this.updateUserData({
        uid: credential.user.uid,
        email: credential.user.email,
        displayName: displayName,
        role: 'user'
      });
      this.router.navigate(['/home']);
    } catch (error) {
      console.error('Error during signup:', error);
      throw error;
    }
  }

  async signIn(email: string, password: string): Promise<void> {
    try {
      await signInWithEmailAndPassword(this.auth, email, password);
      this.user$.pipe(take(1)).subscribe(user => {
        if (user?.role === 'admin') {
          this.router.navigate(['/admin']);
        } else {
          this.router.navigate(['/home']);
        }
      });
    } catch (error) {
      console.error('Error during signin:', error);
      throw error;
    }
  }

  async signOut(): Promise<void> {
    await signOut(this.auth);
    this.router.navigate(['/auth/signin']);
  }

  private async updateUserData(user: User): Promise<void> {
    const userRef = doc(this.firestore, `users/${user.uid}`);
    return setDoc(userRef, user, { merge: true });
  }

  // Auth guard helper methods
  canAccessAdmin(): Observable<boolean> {
    return this.user$.pipe(
      take(1),
      map(user => !!user && user.role === 'admin')
    );
  }

  isLoggedIn(): Observable<boolean> {
    return this.user$.pipe(
      take(1),
      map(user => !!user)
    );
  }
}