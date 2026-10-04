import {
  Component,
  DestroyRef,
  ElementRef,
  afterNextRender,
  effect,
  inject,
  input,
  viewChild,
} from '@angular/core';
import {
  AmbientLight,
  BufferGeometry,
  DirectionalLight,
  Mesh,
  MeshStandardMaterial,
  PerspectiveCamera,
  Scene,
  WebGLRenderer,
} from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';

import { Theme } from '../core/theme';

/** 3D preview, seen from the front of the glasses (+z). */
@Component({
  selector: 'app-frame-viewer',
  template: '<canvas #canvas></canvas>',
  styles: `
    :host {
      display: block;
      aspect-ratio: 4 / 3;
      border-radius: 4px;
      overflow: hidden;
      background: var(--panel-2);
    }
    canvas {
      width: 100%;
      height: 100%;
      display: block;
      touch-action: none;
    }
  `,
})
export class FrameViewer {
  readonly geometry = input.required<BufferGeometry>();

  private readonly canvas = viewChild.required<ElementRef<HTMLCanvasElement>>('canvas');
  private readonly scene = new Scene();
  private readonly camera = new PerspectiveCamera(35, 4 / 3, 1, 2000);
  private readonly material = new MeshStandardMaterial({ roughness: 0.55 });
  private readonly mesh = new Mesh(new BufferGeometry(), this.material);
  private readonly theme = inject(Theme);
  private renderer?: WebGLRenderer;
  private controls?: OrbitControls;

  constructor() {
    // Filament colour: dark on the light panel, pale in the dark room. The canvas is transparent over the panel.
    effect(() => this.material.color.set(this.theme.dark() ? 0xd6d9d3 : 0x2a2f34));
    this.scene.add(new AmbientLight(0xffffff, 1.2), this.mesh);
    const sun = new DirectionalLight(0xffffff, 2);
    sun.position.set(80, 120, 200);
    this.scene.add(sun);
    // Three-quarter view: the temples go 140 mm back, they would be hidden seen from straight ahead.
    this.camera.position.set(170, 60, 190);

    afterNextRender(() => this.init());
    effect(() => {
      this.mesh.geometry.dispose();
      this.mesh.geometry = this.geometry();
      this.mesh.geometry.computeBoundingSphere();
    });
    inject(DestroyRef).onDestroy(() => {
      this.renderer?.setAnimationLoop(null);
      this.controls?.dispose();
      this.renderer?.dispose();
    });
  }

  private init(): void {
    const canvas = this.canvas().nativeElement;
    this.renderer = new WebGLRenderer({ canvas, antialias: true, alpha: true });
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    this.controls = new OrbitControls(this.camera, canvas);
    this.controls.enableDamping = true;
    this.controls.target.set(0, 0, -45);
    this.renderer.setAnimationLoop(() => {
      const { clientWidth: w, clientHeight: h } = canvas;
      if (canvas.width !== Math.round(w * this.renderer!.getPixelRatio())) {
        this.renderer!.setSize(w, h, false);
        this.camera.aspect = w / h;
        this.camera.updateProjectionMatrix();
      }
      this.controls!.update();
      this.renderer!.render(this.scene, this.camera);
    });
  }
}
