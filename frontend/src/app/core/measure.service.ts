import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { firstValueFrom } from 'rxjs';

import { environment } from '../../environments/environment';
import { AppError, isMessageKey } from './i18n/i18n';
import { ApiError, Eye, MeasureResponse } from './lens';

/** Longest side sent to the server: enough for about 10 px/mm on the A4 sheet, light enough for mobile data. */
const MAX_SIDE_PX = 4000;

@Injectable({ providedIn: 'root' })
export class MeasureService {
  private readonly http = inject(HttpClient);

  /** @param printScale printed size / nominal size of the reference sheet, from the user's settings */
  async measure(file: File, eye: Eye, printScale: number): Promise<MeasureResponse> {
    const form = new FormData();
    form.append('image', await prepareImage(file), 'photo.jpg');
    form.append('eye', eye);
    form.append('printScale', String(printScale));
    try {
      return await firstValueFrom(this.http.post<MeasureResponse>(`${environment.apiUrl}/api/measure`, form));
    } catch (e) {
      throw toAppError(e);
    }
  }
}

/** Applies the EXIF rotation and caps the size, so every phone sends the same kind of JPEG. */
async function prepareImage(file: File): Promise<Blob> {
  const bitmap = await createImageBitmap(file, { imageOrientation: 'from-image' });
  const scale = Math.min(1, MAX_SIDE_PX / Math.max(bitmap.width, bitmap.height));
  const canvas = document.createElement('canvas');
  canvas.width = Math.round(bitmap.width * scale);
  canvas.height = Math.round(bitmap.height * scale);
  canvas.getContext('2d')!.drawImage(bitmap, 0, 0, canvas.width, canvas.height);
  bitmap.close();
  return new Promise((resolve, reject) =>
    canvas.toBlob((b) => (b ? resolve(b) : reject(new AppError('error.unreadableImage'))), 'image/jpeg', 0.92),
  );
}

/** The server's error code picks the translated message; its own (French) message is kept for French. */
function toAppError(e: unknown): AppError {
  if (e instanceof HttpErrorResponse) {
    if (e.status === 0) {
      return new AppError('error.unreachable');
    }
    const body = e.error as Partial<ApiError> | null;
    const key = `error.${body?.code}`;
    return new AppError(isMessageKey(key) ? key : 'error.unexpected', body?.message);
  }
  return e instanceof AppError ? e : new AppError('error.unexpected');
}
