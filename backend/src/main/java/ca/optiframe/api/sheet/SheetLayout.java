package ca.optiframe.api.sheet;

import java.util.List;

/**
 * Geometry of the printed reference sheet, in mm, origin at the top-left corner of the paper, y down.
 * Loaded from {@code sheet-layout.json}, which is also read by {@code training/make_sheet.py}.
 */
public record SheetLayout(
		String name,
		Paper paper,
		String dictionary,
		double markerSizeMm,
		List<Marker> markers,
		Rect lensWindow,
		Ruler checkRuler) {

	public record Paper(double widthMm, double heightMm) {
	}

	/** Top-left corner of the marker. */
	public record Marker(int id, double xMm, double yMm) {
	}

	public record Rect(double xMm, double yMm, double widthMm, double heightMm) {
	}

	public record Ruler(double x1Mm, double x2Mm, double yMm) {
	}

}
