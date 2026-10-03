package ca.optiframe.api.vision;

import java.util.ArrayList;
import java.util.List;
import java.util.Optional;

import org.opencv.core.CvType;
import org.opencv.core.Mat;
import org.opencv.core.MatOfPoint;
import org.opencv.core.Scalar;
import org.opencv.core.Size;
import org.opencv.imgproc.Imgproc;

final class Masks {

	private Masks() {
	}

	static List<MatOfPoint> externalContours(Mat binary) {
		List<MatOfPoint> contours = new ArrayList<>();
		Imgproc.findContours(binary.clone(), contours, new Mat(), Imgproc.RETR_EXTERNAL, Imgproc.CHAIN_APPROX_NONE);
		return contours;
	}

	static Optional<MatOfPoint> largest(List<MatOfPoint> contours, double minArea, double maxArea) {
		return contours.stream()
				.filter(c -> {
					double a = Imgproc.contourArea(c);
					return a >= minArea && a <= maxArea;
				})
				.max((x, y) -> Double.compare(Imgproc.contourArea(x), Imgproc.contourArea(y)));
	}

	static Mat filled(MatOfPoint contour, Size size) {
		Mat mask = Mat.zeros(size, CvType.CV_8UC1);
		Imgproc.drawContours(mask, List.of(contour), 0, new Scalar(255), Imgproc.FILLED);
		return mask;
	}

	static Mat disk(int radiusPx) {
		int d = 2 * Math.max(1, radiusPx) + 1;
		return Imgproc.getStructuringElement(Imgproc.MORPH_ELLIPSE, new Size(d, d));
	}

}
