package ca.optiframe.api.vision;

import java.util.List;

import org.opencv.core.Mat;
import org.opencv.core.MatOfPoint;

import ca.optiframe.api.sheet.SheetLayout;

/**
 * Top-down view of the sheet at {@code pxPerMm}.
 *
 * @param image rectified BGR image, pixel (0, 0) is the origin of the layout (paper or board top-left corner)
 * @param markerIds ids of the detected markers of the sheet
 * @param markerQuads detected marker corners in the original photo, for the control image
 * @param markerAreasMm squares of the detected markers in the rectified image, in mm, for the sharpness check
 * @param pointsUsed point correspondences that fit the homography (marker corners or ChArUco corners)
 */
public record RectifiedSheet(
		Mat image,
		double pxPerMm,
		List<Integer> markerIds,
		List<MatOfPoint> markerQuads,
		List<SheetLayout.Rect> markerAreasMm,
		int pointsUsed,
		double reprojectionErrorMm) {
}
