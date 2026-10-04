package ca.optiframe.api.vision;

import org.opencv.core.Core;
import org.opencv.core.CvType;
import org.opencv.core.Mat;
import org.opencv.core.Point;
import org.opencv.core.Size;
import org.opencv.imgproc.Imgproc;
import org.springframework.stereotype.Component;

/**
 * Baseline for a backlit lens: the lens edge refracts the light and shows up as a dark rim with strong gradients.
 * Edges and dark pixels are merged, closed into a ring, and the largest plausible blob is filled.
 * Thresholds are starting points: tune them on real photos of the capture rig.
 */
@Component
public class ClassicalSegmenter implements LensSegmenter {

	/** Smallest lens considered, about 15 x 15 mm. */
	private static final double MIN_LENS_AREA_MM2 = 225;
	/**
	 * The lens casts a soft shadow on the paper, 15-30 grey levels darker than its surroundings, while the lens edge
	 * drops 80+ levels within a few pixels. These thresholds keep the edge and reject the shadow (tuned on real
	 * photos of a lens on the ChArUco sheet, lit from below and from the room).
	 */
	private static final double CANNY_LOW = 40;
	private static final double CANNY_HIGH = 100;
	private static final double DARKER_THAN_LOCAL_MEAN = 25;

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
		Mat gray = new Mat();
		Imgproc.cvtColor(window, gray, Imgproc.COLOR_BGR2GRAY);
		Imgproc.GaussianBlur(gray, gray, new Size(5, 5), 0);

		Mat edges = new Mat();
		Imgproc.Canny(gray, edges, CANNY_LOW, CANNY_HIGH);

		Mat dark = new Mat();
		int block = ((int) Math.round(pxPerMm * 3)) | 1;
		Imgproc.adaptiveThreshold(gray, dark, 255, Imgproc.ADAPTIVE_THRESH_MEAN_C, Imgproc.THRESH_BINARY_INV, block,
				DARKER_THAN_LOCAL_MEAN);
		Imgproc.morphologyEx(dark, dark, Imgproc.MORPH_OPEN, Masks.disk(1));

		Core.bitwise_or(edges, dark, edges);
		Imgproc.morphologyEx(edges, edges, Imgproc.MORPH_CLOSE, Masks.disk((int) Math.round(pxPerMm * 0.4)), new Point(-1, -1), 2);

		double minArea = MIN_LENS_AREA_MM2 * pxPerMm * pxPerMm;
		double maxArea = 0.8 * window.rows() * window.cols();
		return Masks.largest(Masks.externalContours(edges), minArea, maxArea)
				.map(c -> Masks.filled(c, window.size()))
				.orElseGet(() -> Mat.zeros(window.size(), CvType.CV_8UC1));
	}

}
