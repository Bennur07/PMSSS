import { inject } from '@angular/core';
import { Router } from '@angular/router';
import { map, tap } from 'rxjs/operators';
import { AuthService } from '../auth/auth-service.service';

export const adminGuard = () => {
  const authService = inject(AuthService);
  const router = inject(Router);

  return authService.canAccessAdmin().pipe(
    tap(isAdmin => {
      if (!isAdmin) {
        router.navigate(['/home']);
      }
    })
  );
};