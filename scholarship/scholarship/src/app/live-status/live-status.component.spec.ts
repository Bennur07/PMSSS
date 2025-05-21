import { ComponentFixture, TestBed } from '@angular/core/testing';

import { LiveStatusComponent } from './live-status.component';

describe('LiveStatusComponent', () => {
  let component: LiveStatusComponent;
  let fixture: ComponentFixture<LiveStatusComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [LiveStatusComponent]
    })
    .compileComponents();

    fixture = TestBed.createComponent(LiveStatusComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
