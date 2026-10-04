package ca.optiframe.api.sheet;

import java.util.List;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;

/**
 * Geometry of the printed reference sheet, in mm, y down. Two kinds of sheet:
 * <ul>
 * <li>ArUco ({@code sheet-layout.json}): separate markers, origin at the top-left corner of the paper;</li>
 * <li>ChArUco ({@code sheet-layout-charuco.json}, {@code charuco} set): one board, origin at the top-left corner of
 * the board, so the same layout works on any paper size.</li>
 * </ul>
 * Also read by {@code training/make_sheet.py} and {@code training/make_charuco_sheet.py}.
 */
@JsonIgnoreProperties(ignoreUnknown = true)
public record SheetLayout(
		String name,
		Paper paper,
		String dictionary,
		Double markerSizeMm,
		List<Marker> markers,
		Rect lensWindow,
		Ruler checkRuler,
		Charuco charuco) {

	public SheetLayout {
		markers = markers == null ? List.of() : List.copyOf(markers);
	}

	public record Paper(double widthMm, double heightMm) {
	}

	/** Top-left corner of the marker. */
	public record Marker(int id, double xMm, double yMm) {
	}

	public record Rect(double xMm, double yMm, double widthMm, double heightMm) {

		/** True if the point lies inside the rectangle grown by {@code marginMm} on each side. */
		public boolean contains(double x, double y, double marginMm) {
			return x >= xMm - marginMm && x <= xMm + widthMm + marginMm
					&& y >= yMm - marginMm && y <= yMm + heightMm + marginMm;
		}

	}

	public record Ruler(double x1Mm, double x2Mm, double yMm) {
	}

	public record Charuco(int squaresX, int squaresY, double squareMm, double markerMm, boolean legacyPattern) {
	}

	/** Area shown in the rectified image: the paper of an ArUco sheet, the board of a ChArUco sheet. */
	public Paper rectifiedArea() {
		if (charuco == null) {
			return paper;
		}
		return new Paper(charuco.squaresX() * charuco.squareMm(), charuco.squaresY() * charuco.squareMm());
	}

}
