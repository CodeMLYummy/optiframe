package ca.optiframe.api.api.dto;

import java.util.List;

/**
 * Lens outline as photographed with its front (convex) face up, i.e. as seen from the front of the frame.
 * Points are in mm, origin at the center of the boxing rectangle, x to the right, y up, counter-clockwise.
 * Same shape as {@code LensContour} in the Angular app.
 */
public record LensContour(Eye eye, List<double[]> pointsMm, double aMm, double bMm, double perimeterMm) {
}
