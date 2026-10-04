package ca.optiframe.api.api.dto;

import java.util.List;

/**
 * @param printScale printed size / nominal size of the sheet used for this measurement (1.0 = true size)
 * @param rotatedAMm length of the minimum-area rectangle around the lens, independent of how it was placed
 * @param steps control images for the step-by-step page
 */
public record MeasureResponse(
		LensContour contour,
		String method,
		double pxPerMm,
		double printScale,
		int markersFound,
		double reprojectionErrorMm,
		double sharpness,
		double rotatedAMm,
		double rotatedBMm,
		List<Step> steps,
		long elapsedMs) {

	public record Step(String label, String imageDataUrl) {
	}

}
