import { Component, DestroyRef, ElementRef, computed, inject, input, output, signal, viewChild } from '@angular/core';
import type { FaceLandmarker, FaceLandmarkerResult } from '@mediapipe/tasks-vision';
import type { Vec2 } from 'manifold-3d';

import { FacePlacement, placeOnFace } from '../core/face-fit';
import { MessageKey } from '../core/i18n/fr';
import { I18n } from '../core/i18n/i18n';

type Mode = 'idle' | 'loading' | 'live' | 'photo';

/** Smoothing of the live placement: the landmarks jitter by a pixel or two from frame to frame. */
const SMOOTHING = 0.4;

/**
 * Frame tried on the face, at true size: live from the front camera, or on an imported selfie. The face is tracked
 * in the browser (MediaPipe Face Landmarker, loaded on first use); the image never leaves the phone.
 */
@Component({
  selector: 'app-face-preview',
  template: `
    <div class="actions">
      <button class="button primary" [disabled]="mode() === 'loading'" (click)="startCamera()">{{ i18n.t('face.tryOn') }}</button>
      <label class="button" [class.disabled]="mode() === 'loading'">
        {{ i18n.t('face.importSelfie') }}
        <input type="file" accept="image/*" (change)="onPhoto($event)" [disabled]="mode() === 'loading'" hidden />
      </label>
    </div>
    <p class="status">{{ i18n.t('face.privacy') }}</p>
    @if (mode() === 'loading') {
      <p class="status">{{ i18n.t('face.loading') }}</p>
    }
    @if (error(); as key) {
      <p class="error" role="alert">{{ i18n.t(key) }}</p>
    }

    <div class="stage" [class.mirror]="mode() === 'live'" [hidden]="mode() !== 'live' && mode() !== 'photo'">
      <video #video playsinline muted [hidden]="mode() !== 'live'"></video>
      @if (photoUrl(); as url) {
        <img #photo [src]="url" [alt]="i18n.t('face.selfieAlt')" (load)="detectPhoto()" />
      }
      @if (placement(); as p) {
        <svg [attr.viewBox]="'0 0 ' + size().w + ' ' + size().h" preserveAspectRatio="none" aria-hidden="true">
          <g [attr.transform]="transform()">
            <path [attr.d]="outlinePath()" fill-rule="evenodd" />
          </g>
        </svg>
      }
    </div>

    @if (mode() === 'live' || mode() === 'photo') {
      @if (placement(); as p) {
        <p class="status">
          {{ i18n.t('face.scale', { pd: i18n.num(p.pdMm, '1.0-0') }) }}
          @if (pdMm(); as pd) {
            {{ i18n.t('face.framePd', { pd: i18n.num(pd) }) }}
          }
          <button class="link" (click)="usePd.emit(p.pdMm)">{{ i18n.t('face.usePd') }}</button>
        </p>
      } @else if (mode() === 'live') {
        <p class="status">{{ i18n.t('face.position') }}</p>
      }
      @if (mode() === 'live') {
        <button class="button wide" (click)="stop()">{{ i18n.t('face.stop') }}</button>
      }
    }
  `,
  styles: `
    .stage { position: relative; border-radius: 12px; overflow: hidden; margin: 8px 0; background: #000; }
    .stage.mirror { transform: scaleX(-1); }
    .stage[hidden] { display: none; }
    video, img { display: block; width: 100%; height: auto; }
    video[hidden] { display: none; }
    svg { position: absolute; inset: 0; width: 100%; height: 100%; }
    path { fill: #1d2b3a; fill-opacity: 0.9; stroke: #0b1218; stroke-width: 0.3; }
  `,
})
export class FacePreview {
  /** Front silhouette of the frame, model coordinates (mm, x right, y up, seen from the front). */
  readonly outline = input.required<Vec2[][]>();
  /** PD used for the frame, for comparison with the one estimated on the face. */
  readonly pdMm = input<number | null>(null);
  readonly usePd = output<number>();

  protected readonly mode = signal<Mode>('idle');
  protected readonly i18n = inject(I18n);
  protected readonly error = signal<MessageKey | null>(null);
  protected readonly photoUrl = signal<string | null>(null);
  protected readonly placement = signal<FacePlacement | null>(null);
  protected readonly size = signal({ w: 1, h: 1 });

  private readonly video = viewChild.required<ElementRef<HTMLVideoElement>>('video');
  private readonly photo = viewChild<ElementRef<HTMLImageElement>>('photo');
  private landmarker?: Promise<FaceLandmarker>;
  private stream?: MediaStream;
  private frameRequest = 0;

  protected readonly outlinePath = computed(() =>
    this.outline()
      .map((poly) => poly.map(([x, y], i) => `${i ? 'L' : 'M'}${x.toFixed(2)} ${y.toFixed(2)}`).join(' ') + ' Z')
      .join(' '),
  );

  /** Model mm to image pixels: centre of the frame on the midpoint between the pupils, y up to y down. */
  protected readonly transform = computed(() => {
    const p = this.placement();
    return p ? `translate(${p.x} ${p.y}) rotate(${p.rollDeg}) scale(${p.pxPerMm} ${-p.pxPerMm})` : '';
  });

  constructor() {
    inject(DestroyRef).onDestroy(() => {
      this.stop();
      this.revokePhoto();
    });
  }

  protected async startCamera(): Promise<void> {
    this.error.set(null);
    this.revokePhoto();
    this.placement.set(null);
    this.mode.set('loading');
    let stream: MediaStream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'user' }, audio: false });
    } catch {
      this.mode.set('idle');
      this.error.set('face.cameraDenied');
      return;
    }
    this.stream = stream;
    const landmarker = await this.load();
    if (!landmarker) {
      this.stop();
      return;
    }
    await landmarker.setOptions({ runningMode: 'VIDEO' });
    const video = this.video().nativeElement;
    video.srcObject = stream;
    await video.play();
    this.size.set({ w: video.videoWidth, h: video.videoHeight });
    this.mode.set('live');
    let last = -1;
    const tick = () => {
      if (this.mode() !== 'live') {
        return;
      }
      if (video.currentTime !== last) {
        last = video.currentTime;
        this.update(landmarker.detectForVideo(video, performance.now()), video.videoWidth, video.videoHeight, true);
      }
      this.frameRequest = requestAnimationFrame(tick);
    };
    tick();
  }

  protected stop(): void {
    cancelAnimationFrame(this.frameRequest);
    this.stream?.getTracks().forEach((t) => t.stop());
    this.stream = undefined;
    if (this.mode() === 'live' || this.mode() === 'loading') {
      this.mode.set('idle');
      this.placement.set(null);
    }
  }

  protected onPhoto(event: Event): void {
    const inputEl = event.target as HTMLInputElement;
    const file = inputEl.files?.[0];
    inputEl.value = '';
    if (!file) {
      return;
    }
    this.stop();
    this.revokePhoto();
    this.error.set(null);
    this.placement.set(null);
    this.photoUrl.set(URL.createObjectURL(file));
    this.mode.set('photo');
  }

  protected async detectPhoto(): Promise<void> {
    const img = this.photo()?.nativeElement;
    if (!img) {
      return;
    }
    const landmarker = await this.load();
    if (!landmarker) {
      return;
    }
    await landmarker.setOptions({ runningMode: 'IMAGE' });
    this.size.set({ w: img.naturalWidth, h: img.naturalHeight });
    this.update(landmarker.detect(img), img.naturalWidth, img.naturalHeight, false);
    if (!this.placement()) {
      this.error.set('face.noFace');
    }
  }

  private update(result: FaceLandmarkerResult, w: number, h: number, smooth: boolean): void {
    const face = result.faceLandmarks[0];
    const next = face ? placeOnFace(face, w, h) : null;
    const prev = this.placement();
    if (!next || !prev || !smooth) {
      this.placement.set(next);
      return;
    }
    const mix = (a: number, b: number) => a + (b - a) * SMOOTHING;
    this.placement.set({
      x: mix(prev.x, next.x),
      y: mix(prev.y, next.y),
      rollDeg: mix(prev.rollDeg, next.rollDeg),
      pxPerMm: mix(prev.pxPerMm, next.pxPerMm),
      pdMm: mix(prev.pdMm, next.pdMm),
    });
  }

  /** Face Landmarker, served with the app (no third-party request); GPU when available. Null after an error. */
  private async load(): Promise<FaceLandmarker | null> {
    this.landmarker ??= (async () => {
      const { FaceLandmarker, FilesetResolver } = await import('@mediapipe/tasks-vision');
      const files = await FilesetResolver.forVisionTasks(new URL('face/wasm', document.baseURI).href);
      const options = (delegate: 'GPU' | 'CPU') => ({
        baseOptions: { modelAssetPath: new URL('face/face_landmarker.task', document.baseURI).href, delegate },
        runningMode: 'VIDEO' as const,
        numFaces: 1,
      });
      try {
        return await FaceLandmarker.createFromOptions(files, options('GPU'));
      } catch {
        return await FaceLandmarker.createFromOptions(files, options('CPU'));
      }
    })();
    try {
      return await this.landmarker;
    } catch (e) {
      console.error(e);
      this.landmarker = undefined;
      this.mode.set('idle');
      this.error.set('face.unsupported');
      return null;
    }
  }

  private revokePhoto(): void {
    const url = this.photoUrl();
    if (url) {
      URL.revokeObjectURL(url);
      this.photoUrl.set(null);
    }
  }
}
