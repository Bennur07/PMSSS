import { ApplicationConfig } from '@angular/core';
import { provideRouter, withComponentInputBinding } from '@angular/router';
import { routes } from './app.routes';
import { provideClientHydration } from '@angular/platform-browser';
import { provideAnimations } from '@angular/platform-browser/animations';
import { provideHttpClient, withFetch } from '@angular/common/http';

import { provideFirebaseApp, initializeApp } from '@angular/fire/app';
import { getFirestore, provideFirestore } from '@angular/fire/firestore';
import { getAuth, provideAuth } from '@angular/fire/auth';

const firebaseConfig = {
  apiKey: "AIzaSyDR4u1jzOOwLK2WFJwYLe4EC8qbIRksW7s",
  authDomain: "scolarship-2526b.firebaseapp.com",
  projectId: "scolarship-2526b",
  storageBucket: "scolarship-2526b.firebasestorage.app",
  messagingSenderId: "780945630843",
  appId: "1:780945630843:web:f5703f4fa788462d9724de",
  measurementId: "G-24C5J1PDRF"
};

export const appConfig: ApplicationConfig = {
  providers: [
    provideRouter(routes, withComponentInputBinding()),
    provideClientHydration(),
    provideAnimations(),
    provideHttpClient(withFetch()),
    provideFirebaseApp(() => initializeApp(firebaseConfig)),
    provideFirestore(() => getFirestore()),
    provideAuth(() => getAuth())
  ]
};
