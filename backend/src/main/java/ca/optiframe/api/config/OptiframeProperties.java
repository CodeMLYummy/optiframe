package ca.optiframe.api.config;

import java.util.List;

import org.springframework.boot.context.properties.ConfigurationProperties;

@ConfigurationProperties("optiframe")
public record OptiframeProperties(
		List<String> corsOrigins,
		String sheetLayout,
		double pxPerMm,
		double maxReprojectionErrorMm,
		double minSharpness,
		double edgeBiasMm,
		String modelPath,
		int modelInputSize,
		String datasetDir) {
}
