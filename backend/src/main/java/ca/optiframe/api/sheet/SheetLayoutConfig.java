package ca.optiframe.api.sheet;

import java.io.IOException;
import java.io.InputStream;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.core.io.ClassPathResource;

import ca.optiframe.api.config.OptiframeProperties;
import tools.jackson.databind.ObjectMapper;

@Configuration
public class SheetLayoutConfig {

	@Bean
	SheetLayout sheetLayout(ObjectMapper mapper, OptiframeProperties props) throws IOException {
		try (InputStream in = new ClassPathResource(props.sheetLayout()).getInputStream()) {
			return mapper.readValue(in, SheetLayout.class);
		}
	}

}
