package ca.optiframe.api.vision;

import java.util.Arrays;
import java.util.List;

import org.opencv.core.Core;
import org.opencv.core.CvType;
import org.opencv.core.Mat;
import org.opencv.core.MatOfFloat;
import org.opencv.core.MatOfInt;
import org.opencv.core.MatOfPoint;
import org.opencv.core.MatOfPoint2f;
import org.opencv.core.Point;
import org.opencv.core.Scalar;
import org.opencv.core.Size;
import org.opencv.imgproc.Imgproc;
import org.opencv.imgproc.Moments;
import org.springframework.stereotype.Component;

/**
 * Finds the lens outline as the best closed path around its centre ("polar contour", prototype v5 in
 * {@code lensDetection/prototypes/v5_polar_contour/}).
 * <ol>
 * <li>Rim map: black-hat + top-hat about 1.6 mm wide. The rim of a lens, clear or tinted, is a thin line; the lens's
 * shadow, cable shadows and lighting gradients are wide soft bands and barely answer. The map is divided by the
 * photo's own background level, so backlit paper texture and smooth paper are judged alike.</li>
 * <li>The map is unrolled around the lens centre (angle x radius) and dynamic programming picks the closed path
 * r(theta) with the most rim evidence, moving at most 0.4 mm per 0.5 degree and paying for every jump: it bridges
 * the gaps of a faint rim and does not follow a cable.</li>
 * <li>The jump cost that keeps the path on the right loop also flattens it (it cuts the ends of the long axis), so
 * each point is then snapped to the strongest rim response within 0.6 mm, and the loop is filled.</li>
 * </ol>
 * The result is refused (empty mask) when the path lies on rim evidence along less than half of its length.
 * Lenses must be star-shaped around their centre, which spectacle lenses are. Tuned on real rims, which are thin
 * lines (0.3-0.5 mm); an edge seen as a thick dark band (over ~1 mm) can be under-measured on the long axis.
 */
@Component
public class ClassicalSegmenter implements LensSegmenter {

	/** Half-width of the thin-line filter: lines up to ~1.6 mm wide answer, wider bands do not. */
	private static final double LINE_RADIUS_MM = 0.8;
	/** Ignored band along the window edge: the printed window outline and its axis ticks. */
	private static final double BORDER_MM = 2;
	private static final int ANGLES = 720;
	private static final double MIN_RADIUS_MM = 8;
	private static final double MAX_RADIUS_MM = 45;
	/** Largest radius change between neighbouring angles (0.5 degree). */
	private static final double MAX_STEP_MM = 0.4;
	/** Cost per pixel of radius change: a detour (to a cable, a glare) must be worth it. */
	private static final double JUMP_COST = 0.4;
	/** Rim strength cap, in units of background level: one glare spot cannot outweigh a whole faint rim. */
	private static final float RESPONSE_CAP = 6;
	/** Rim strength that counts as evidence when checking the path. */
	private static final float EVIDENCE = 2;
	/** Minimum share of the path lying on rim evidence; below it the lens is reported as not found. */
	private static final double MIN_RIM_COVERAGE = 0.5;
	/** Band around the path where each point snaps to the strongest rim response; a cable further away cannot. */
	private static final double SNAP_MM = 0.6;

	@Override
	public String name() {
		return "classical";
	}

	@Override
	public boolean available() {
		return true;
	}

	@Override
	public Mat segment(Mat window, double pxPerMm) {
		Mat response = rimResponse(window, pxPerMm);
		Point center = seed(response);
		Path path = null;
		// The seed is rough; one re-centring on the found loop is enough.
		for (int i = 0; i < 2; i++) {
			path = polarPath(response, center, pxPerMm);
			Point centroid = centroid(path.points());
			if (centroid == null) {
				break;
			}
			center = centroid;
		}
		Mat mask = Mat.zeros(window.size(), CvType.CV_8UC1);
		if (path != null && path.coverage() >= MIN_RIM_COVERAGE) {
			Point[] rounded = Arrays.stream(path.points())
					.map(p -> new Point(Math.round(p.x), Math.round(p.y)))
					.toArray(Point[]::new);
			Imgproc.fillPoly(mask, List.of(new MatOfPoint(rounded)), new Scalar(255));
		}
		return mask;
	}

	/** Thin-line strength (dark or bright line), divided by the background level; zero on the window border. */
	static Mat rimResponse(Mat window, double pxPerMm) {
		Mat gray = new Mat();
		Imgproc.cvtColor(window, gray, Imgproc.COLOR_BGR2GRAY);
		Imgproc.GaussianBlur(gray, gray, new Size(3, 3), 0);
		Mat kernel = Masks.disk((int) Math.round(LINE_RADIUS_MM * pxPerMm));
		Mat dark = new Mat();
		Mat bright = new Mat();
		Imgproc.morphologyEx(gray, dark, Imgproc.MORPH_BLACKHAT, kernel);
		Imgproc.morphologyEx(gray, bright, Imgproc.MORPH_TOPHAT, kernel);
		Mat line = new Mat();
		Core.add(dark, bright, line);

		double noise = Math.max(5, percentile(line, 90));
		Mat response = new Mat();
		line.convertTo(response, CvType.CV_32F, 1 / noise);
		int m = (int) (BORDER_MM * pxPerMm);
		int h = response.rows(), w = response.cols();
		response.rowRange(0, Math.min(m, h)).setTo(Scalar.all(0));
		response.rowRange(Math.max(0, h - m), h).setTo(Scalar.all(0));
		response.colRange(0, Math.min(m, w)).setTo(Scalar.all(0));
		response.colRange(Math.max(0, w - m), w).setTo(Scalar.all(0));
		return response;
	}

	/** Median position of the strongest 0.5 % line pixels: inside the lens rim; window centre if there are none. */
	static Point seed(Mat response) {
		int h = response.rows(), w = response.cols();
		float[] values = new float[h * w];
		response.get(0, 0, values);
		float[] sorted = values.clone();
		Arrays.sort(sorted);
		float threshold = sorted[(int) Math.min(sorted.length - 1, Math.floor(0.995 * (sorted.length - 1)))];
		int count = 0;
		for (float v : values) {
			if (v > threshold) {
				count++;
			}
		}
		if (count == 0) {
			return new Point(w / 2.0, h / 2.0);
		}
		int[] xs = new int[count];
		int[] ys = new int[count];
		int k = 0;
		for (int i = 0; i < values.length; i++) {
			if (values[i] > threshold) {
				xs[k] = i % w;
				ys[k] = i / w;
				k++;
			}
		}
		Arrays.sort(xs);
		Arrays.sort(ys);
		return new Point(xs[count / 2], ys[count / 2]);
	}

	record Path(Point[] points, double coverage) {
	}

	/** Closed path r(theta) with the most rim evidence around {@code center}, by dynamic programming. */
	static Path polarPath(Mat response, Point center, double pxPerMm) {
		int radii = (int) (MAX_RADIUS_MM * pxPerMm);
		Mat polar = new Mat();
		Imgproc.warpPolar(response, polar, new Size(radii, ANGLES), center, radii, Imgproc.WARP_POLAR_LINEAR);
		float[] raw = new float[ANGLES * radii];
		polar.get(0, 0, raw);
		int minRadius = (int) (MIN_RADIUS_MM * pxPerMm);
		float[] score = new float[ANGLES * radii];
		for (int t = 0; t < ANGLES; t++) {
			for (int r = minRadius; r < radii; r++) {
				score[t * radii + r] = Math.min(raw[t * radii + r], RESPONSE_CAP);
			}
		}

		int step = Math.max(1, (int) Math.round(MAX_STEP_MM * pxPerMm));
		// Two turns, so that the path closes on itself; the second turn is kept.
		int rows = 2 * ANGLES;
		int[] back = new int[rows * radii];
		double[] acc = new double[radii];
		for (int r = 0; r < radii; r++) {
			acc[r] = score[r];
		}
		double[] next = new double[radii];
		for (int t = 1; t < rows; t++) {
			int row = (t % ANGLES) * radii;
			for (int r = 0; r < radii; r++) {
				double best = Double.NEGATIVE_INFINITY;
				int arg = r;
				for (int d = -step; d <= step; d++) {
					int from = r - d;
					if (from < 0 || from >= radii) {
						continue;
					}
					double v = acc[from] - JUMP_COST * Math.abs(d);
					if (v > best) {
						best = v;
						arg = from;
					}
				}
				next[r] = best + score[row + r];
				back[t * radii + r] = arg;
			}
			double[] swap = acc;
			acc = next;
			next = swap;
		}
		int[] path = new int[rows];
		int bestEnd = 0;
		for (int r = 1; r < radii; r++) {
			if (acc[r] > acc[bestEnd]) {
				bestEnd = r;
			}
		}
		path[rows - 1] = bestEnd;
		for (int t = rows - 1; t > 0; t--) {
			path[t - 1] = back[t * radii + path[t]];
		}

		int snap = (int) Math.round(SNAP_MM * pxPerMm);
		Point[] points = new Point[ANGLES];
		int onRim = 0;
		for (int t = 0; t < ANGLES; t++) {
			int r = path[ANGLES + t];
			if (score[t * radii + r] > EVIDENCE) {
				onRim++;
			}
			int best = r;
			for (int s = Math.max(0, r - snap); s <= Math.min(radii - 1, r + snap); s++) {
				if (raw[t * radii + s] > raw[t * radii + best]) {
					best = s;
				}
			}
			double theta = 2 * Math.PI * t / ANGLES;
			double radius = best + 0.5;
			points[t] = new Point(center.x + radius * Math.cos(theta), center.y + radius * Math.sin(theta));
		}
		return new Path(points, (double) onRim / ANGLES);
	}

	private static Point centroid(Point[] points) {
		Moments m = Imgproc.moments(new MatOfPoint2f(points));
		return m.m00 == 0 ? null : new Point(m.m10 / m.m00, m.m01 / m.m00);
	}

	/** Value below which {@code percent} % of the 8-bit image's pixels fall. */
	private static double percentile(Mat image8u, double percent) {
		Mat hist = new Mat();
		Imgproc.calcHist(List.of(image8u), new MatOfInt(0), new Mat(), hist,
				new MatOfInt(256), new MatOfFloat(0, 256));
		double total = image8u.total();
		double target = percent / 100 * total;
		double cumulative = 0;
		for (int v = 0; v < 256; v++) {
			cumulative += hist.get(v, 0)[0];
			if (cumulative >= target) {
				return v;
			}
		}
		return 255;
	}

}
