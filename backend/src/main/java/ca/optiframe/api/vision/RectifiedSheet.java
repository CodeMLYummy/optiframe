package ca.optiframe.api.vision;

import java.util.List;

import org.opencv.core.Mat;
import org.opencv.core.MatOfPoint;

/**
 * Top-down view of the whole sheet at {@code pxPerMm}.
 *
 * @param image rectified BGR image, pixel (0, 0) is the top-left corner of the paper
 * @param markerIds ids of the markers used for the homography
 * @param markerQuads detected marker corners in the original photo, for the control image
 */
public record RectifiedSheet(
		Mat image,
		double pxPerMm,
		List<Integer> markerIds,
		List<MatOfPoint> markerQuads,
		double reprojectionErrorMm) {
}
