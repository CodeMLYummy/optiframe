package ca.optiframe.api.vision;

import java.util.ArrayList;
import java.util.List;

import org.opencv.core.Mat;
import org.opencv.core.MatOfPoint;
import org.opencv.core.MatOfPoint2f;
import org.opencv.core.Point;
import org.opencv.core.RotatedRect;
import org.opencv.imgproc.Imgproc;
import org.springframework.stereotype.Component;

import ca.optiframe.api.api.dto.Eye;
import ca.optiframe.api.api.dto.LensContour;

/** Turns a lens mask into a smoothed polygon in mm with its boxing dimensions. */
@Component
public class ContourMeasurer {

	/** Enough points for the frame generator and the SVG, small enough for a light JSON. */
	private static final int OUTPUT_POINTS = 360;

	public record Measurement(LensContour contour, double rotatedAMm, double rotatedBMm, MatOfPoint pixelContour) {
	}

	/**
	 * @param edgeBiasMm signed correction of the outline, positive grows the lens
	 */
	public Measurement measure(Mat mask, double pxPerMm, Eye eye, double edgeBiasMm) {
		Mat corrected = mask.clone();
		int biasPx = (int) Math.round(Math.abs(edgeBiasMm) * pxPerMm);
		if (biasPx > 0) {
			int op = edgeBiasMm > 0 ? Imgproc.MORPH_DILATE : Imgproc.MORPH_ERODE;
			Imgproc.morphologyEx(corrected, corrected, op, Masks.disk(biasPx));
		}
		MatOfPoint contour = Masks.largest(Masks.externalContours(corrected), 1, Double.MAX_VALUE)
				.orElseThrow(() -> new MeasurementException(MeasurementException.Code.LENS_NOT_FOUND,
						"Verre introuvable. Placez-le au centre du cadre, sur le fond éclairé."));

		Point[] px = smooth(contour.toArray(), Math.max(1, (int) Math.round(pxPerMm * 0.5)));

		// Pixel centers lie half a pixel inside the true boundary on each side.
		double minX = Double.MAX_VALUE, maxX = -Double.MAX_VALUE, minY = Double.MAX_VALUE, maxY = -Double.MAX_VALUE;
		for (Point p : px) {
			minX = Math.min(minX, p.x);
			maxX = Math.max(maxX, p.x);
			minY = Math.min(minY, p.y);
			maxY = Math.max(maxY, p.y);
		}
		double aMm = (maxX - minX + 1) / pxPerMm;
		double bMm = (maxY - minY + 1) / pxPerMm;
		double cx = (minX + maxX) / 2;
		double cy = (minY + maxY) / 2;

		double perimeterPx = 0;
		for (int i = 0; i < px.length; i++) {
			Point a = px[i];
			Point b = px[(i + 1) % px.length];
			perimeterPx += Math.hypot(b.x - a.x, b.y - a.y);
		}

		// Image y points down; the contract wants y up and counter-clockwise.
		List<double[]> points = new ArrayList<>(OUTPUT_POINTS);
		int step = Math.max(1, px.length / OUTPUT_POINTS);
		for (int i = 0; i < px.length; i += step) {
			points.add(new double[] { (px[i].x - cx) / pxPerMm, -(px[i].y - cy) / pxPerMm });
		}
		if (signedArea(points) < 0) {
			points = points.reversed();
		}

		RotatedRect box = Imgproc.minAreaRect(new MatOfPoint2f(px));
		double w = (box.size.width + 1) / pxPerMm;
		double h = (box.size.height + 1) / pxPerMm;

		LensContour lens = new LensContour(eye, points, aMm, bMm, perimeterPx / pxPerMm);
		return new Measurement(lens, Math.max(w, h), Math.min(w, h), new MatOfPoint(px));
	}

	/** Circular moving average, removes the pixel staircase that would inflate the perimeter. */
	private static Point[] smooth(Point[] pts, int halfWindow) {
		int n = pts.length;
		Point[] out = new Point[n];
		for (int i = 0; i < n; i++) {
			double sx = 0, sy = 0;
			for (int k = -halfWindow; k <= halfWindow; k++) {
				Point p = pts[Math.floorMod(i + k, n)];
				sx += p.x;
				sy += p.y;
			}
			int count = 2 * halfWindow + 1;
			out[i] = new Point(sx / count, sy / count);
		}
		return out;
	}

	private static double signedArea(List<double[]> pts) {
		double s = 0;
		for (int i = 0; i < pts.size(); i++) {
			double[] a = pts.get(i);
			double[] b = pts.get((i + 1) % pts.size());
			s += a[0] * b[1] - b[0] * a[1];
		}
		return s / 2;
	}

}
